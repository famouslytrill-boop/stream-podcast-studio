import http.client
import json
import os
from pathlib import Path
import platform
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from hub.connection_settings import read,update
from hub.core import Workspace
from hub.credentials import port,profile,protect,resolve,save as save_secret,unprotect
from hub.mcp import Client,TOOLS
from hub.obs import OBS,OBSConnectionError,perform
from hub.readiness import frame_ratio,snapshot
from hub.rehearsal import requirements,save as save_rehearsal
from hub.server import StudioServer
from tests.test_hub import HubFixture
from tools.connect_obs import existing_obs
from tools.studio_tools import StudioError,obs_auth


SECRET="synthetic-only-test-secret"


class SocketFixture:
    def __init__(self,hello=None,identified=None):
        self.messages=[hello or {"op":0,"d":{"authentication":{"salt":"test-salt","challenge":"test-challenge"}}},
                       identified or {"op":2,"d":{"negotiatedRpcVersion":1}}]
        self.sent=[];self.closed=False
    def recv(self,timeout=None):return json.dumps(self.messages.pop(0))
    def send(self,message):self.sent.append(json.loads(message))
    def close(self):self.closed=True


class ConnectionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_atomic_settings_preserve_other_connections_and_bound_size(self):
        update(self.root,lambda d:{**d,"recordings_root":"existing-root"})
        update(self.root,lambda d:{**d,"obs":{"port":4456}})
        self.assertEqual(read(self.root)["recordings_root"],"existing-root")
        with self.assertRaises(StudioError):update(self.root,lambda d:{"oversized":"x"*9000})
        self.assertEqual(read(self.root)["obs"]["port"],4456)
        with self.assertRaises(StudioError):update(self.root,lambda d:None)

    def test_settings_writers_serialize_without_lost_updates(self):
        errors=[]
        def increment():
            def change(d):time.sleep(.002);return {**d,"count":d.get("count",0)+1}
            try:
                for _ in range(10):update(self.root,change)
            except Exception as error:errors.append(error)
        threads=[threading.Thread(target=increment) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=8)
        self.assertFalse(errors);self.assertEqual(read(self.root)["count"],20)

    def test_linked_and_malformed_settings_are_not_followed_or_overwritten(self):
        (self.root/"connections.json").write_text("[]")
        with self.assertRaises(StudioError):read(self.root)
        (self.root/"connections.json").unlink()
        target=self.root/"outside.json";target.write_text('{"untouched":true}')
        try:(self.root/"connections.json").symlink_to(target)
        except OSError:self.skipTest("Local symlinks unavailable")
        with self.assertRaises(StudioError):update(self.root,lambda d:{})
        self.assertEqual(json.loads(target.read_text()),{"untouched":True})

    def test_protected_profile_metadata_rotation_and_failed_commit_rollback(self):
        update(self.root,lambda d:{"recordings_root":"keep-this"})
        with patch.dict(os.environ,{},clear=True),patch('hub.credentials.protect',return_value=b'sealed-fixture'),patch('hub.credentials.unprotect',return_value=SECRET):
            first=save_secret(self.root,SECRET,4456);old=read(self.root)['obs']['credential_file']
            self.assertTrue(first['credential_roundtrip_verified'])
            self.assertNotIn(SECRET,json.dumps(read(self.root)))
            self.assertNotIn(SECRET,(self.root/old).read_text())
            self.assertEqual(resolve(self.root)['password'],SECRET)
            with patch('hub.credentials.update',side_effect=StudioError('Write failed')):
                with self.assertRaises(StudioError):save_secret(self.root,SECRET,4457)
            self.assertEqual(read(self.root)['obs']['credential_file'],old)
            self.assertEqual(len(list(self.root.glob('*.dpapi'))),1)
            save_secret(self.root,SECRET,4457)
            self.assertFalse((self.root/old).exists());self.assertEqual(read(self.root)['recordings_root'],'keep-this')
            with patch('hub.credentials.unprotect',return_value=SECRET+' é'):
                self.assertTrue(save_secret(self.root,SECRET+' é',4457)['credential_roundtrip_verified'])

    def test_failed_native_roundtrip_does_not_create_profile(self):
        with patch('hub.credentials.protect',return_value=b'sealed'),patch('hub.credentials.unprotect',return_value='different'):
            with self.assertRaisesRegex(StudioError,'round-trip'):save_secret(self.root,SECRET)
        self.assertFalse((self.root/'connections.json').exists());self.assertFalse(list(self.root.glob('*.dpapi')))

    def test_actual_windows_dpapi_roundtrip(self):
        if platform.system()!='Windows':self.skipTest('Native DPAPI acceptance requires Windows')
        encrypted=protect(SECRET+' é')
        self.assertNotIn(SECRET.encode(),encrypted);self.assertEqual(unprotect(encrypted),SECRET+' é')

    def test_non_windows_does_not_claim_native_credential_storage(self):
        with patch('hub.credentials.platform.system',return_value='Linux'):
            with self.assertRaisesRegex(StudioError,'Windows account'):protect(SECRET)

    def test_public_profile_is_redacted_and_ports_are_local_numbers(self):
        with patch.dict(os.environ,{'EMBERBANTER_OBS_PASSWORD':SECRET,'EMBERBANTER_OBS_PORT':'4456'},clear=True):
            self.assertNotIn(SECRET,json.dumps(profile(self.root)))
            self.assertEqual(resolve(self.root)['port'],4456)
            with self.assertRaisesRegex(StudioError,'changed'):resolve(self.root,expected='old-profile')
        for value in [True,80,65536,'4455','ws://remote.example:4455']:
            with self.subTest(value=value),self.assertRaises(StudioError):port(value)

    def test_existing_obs_import_requires_authentication_and_enabled_server(self):
        p=self.root/'obs.json'
        base={'auth_required':True,'server_enabled':True,'server_port':4456,'server_password':SECRET}
        for changed in ({'auth_required':False},{'server_enabled':False},{'server_port':True}):
            p.write_text(json.dumps({**base,**changed}))
            with self.assertRaises(StudioError):existing_obs(p)
        p.write_text(json.dumps(base));before=p.read_bytes()
        self.assertEqual(existing_obs(p)['port'],4456);self.assertEqual(p.read_bytes(),before)

    def test_obs_real_client_protocol_is_authenticated_and_loopback_only(self):
        wire=SocketFixture()
        with patch('websockets.sync.client.connect',return_value=wire) as connect:
            with OBS(settings={'password':SECRET,'port':4456}) as obs:
                self.assertEqual(wire.sent[0]['d']['authentication'],obs_auth(SECRET,'test-salt','test-challenge'))
                self.assertEqual(wire.sent[0]['d']['eventSubscriptions'],0)
                with self.assertRaises(StudioError):obs.request('StartStream')
            self.assertEqual(connect.call_args.args[0],'ws://127.0.0.1:4456')
            self.assertIsNone(connect.call_args.kwargs['proxy'])
        self.assertNotIn(SECRET,json.dumps(wire.sent));self.assertEqual(len(wire.sent),1);self.assertTrue(wire.closed)

    def test_obs_refuses_unprotected_and_unacknowledged_authentication(self):
        for hello,identified,expected in [({'op':0,'d':{}},None,'authentication_required'),(None,{'op':7,'d':{}},'authentication_failed')]:
            wire=SocketFixture(hello,identified)
            with patch('websockets.sync.client.connect',return_value=wire),self.assertRaises(OBSConnectionError) as error:
                with OBS(settings={'password':SECRET,'port':4455}):pass
            self.assertEqual(error.exception.code,expected);self.assertTrue(wire.closed)

    def test_obs_wrong_request_acknowledgement_is_not_retried(self):
        wire=SocketFixture();wire.messages.append({'op':7,'d':{'requestId':'wrong','requestType':'SetInputMute','requestStatus':{'result':True}}})
        with patch('websockets.sync.client.connect',return_value=wire):
            with OBS(settings={'password':SECRET,'port':4455}) as obs:
                with self.assertRaises(StudioError):obs.request('SetInputMute',{'inputName':'synthetic','inputMuted':True})
        self.assertEqual(len(wire.sent),2)

    def test_ambiguous_send_error_is_scrubbed_and_never_retried(self):
        wire=SocketFixture()
        with patch('websockets.sync.client.connect',return_value=wire),patch.object(wire,'send',side_effect=[None,OSError(SECRET)]) as send:
            with OBS(settings={'password':SECRET,'port':4455}) as obs:
                with self.assertRaisesRegex(StudioError,'Check OBS') as error:obs.request('StopRecord')
        self.assertNotIn(SECRET,str(error.exception));self.assertEqual(send.call_count,2)

    def test_unknown_zero_and_invalid_frame_denominators_remain_unknown(self):
        for total,skipped in [(0,0),(None,0),(2,3),(10,-1),(True,0)]:
            self.assertIsNone(frame_ratio({'s':skipped,'t':total},'s','t')['percent'])
        self.assertEqual(frame_ratio({'s':2,'t':100},'s','t')['percent'],2)

    def test_incomplete_obs_state_never_becomes_an_idle_or_completed_control_claim(self):
        from hub.obs import status
        with patch('hub.obs.OBS') as connection:
            obs=connection.return_value.__enter__.return_value
            obs.request.side_effect=[{'obsVersion':'fixture'},{},{'outputActive':False},{},{'scenes':[]},{'inputs':[]}]
            with self.assertRaises(OBSConnectionError) as error:status()
            self.assertEqual(error.exception.code,'protocol_error')
        with patch('hub.obs.OBS') as connection:
            obs=connection.return_value.__enter__.return_value;obs.request.side_effect=[{},{}]
            with self.assertRaisesRegex(StudioError,'acknowledged.*unknown'):perform({'action':'record_stop'})
            self.assertEqual(obs.request.call_count,2)


class LauncherTests(unittest.TestCase):
    def test_old_version_and_other_service_do_not_receive_pairing_or_spawn_servers(self):
        from io import BytesIO
        from tools.open_hub import main
        for health in [{'service':'emberbanter-studio','version':'0.7.0'},{'service':'other','version':'0.8.0'}]:
            with patch('tools.open_hub.build_opener') as opener,patch('tools.open_hub.notify') as notify,patch('tools.open_hub.subprocess.Popen') as start,patch('tools.open_hub.webbrowser.open') as browser:
                opener.return_value.open.return_value.__enter__.return_value=BytesIO(json.dumps(health).encode())
                self.assertEqual(main(),2);notify.assert_called_once();start.assert_not_called();browser.assert_not_called()

    def test_a_refused_connection_starts_the_service_but_timeout_does_not(self):
        from urllib.error import URLError
        from tools.open_hub import main
        for reason,expected in [(ConnectionRefusedError(111,'fixture'),0),(TimeoutError('fixture'),2)]:
            with patch('tools.open_hub.build_opener') as opener,patch('tools.open_hub.notify'),patch('tools.open_hub.subprocess.Popen') as start:
                opener.return_value.open.side_effect=URLError(reason)
                self.assertEqual(main(),expected);self.assertEqual(start.call_count,1 if expected==0 else 0)

    def test_matching_service_pairs_only_with_a_valid_local_file(self):
        from io import BytesIO
        from hub import VERSION
        from tools.open_hub import main
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);workspace=root/'Documents/EmberBanterHub';workspace.mkdir(parents=True)
            key='synthetic-owner-pairing-key-for-test-only-123456789'
            (workspace/'.pairing-key').write_text(key)
            with patch('tools.open_hub.Path.home',return_value=root),patch('tools.open_hub.build_opener') as opener,patch('tools.open_hub.webbrowser.open') as browser,patch('tools.open_hub.subprocess.Popen') as start:
                opener.return_value.open.return_value.__enter__.return_value=BytesIO(json.dumps({'service':'emberbanter-studio','version':VERSION}).encode())
                self.assertEqual(main(),0);browser.assert_called_once_with('http://127.0.0.1:8765/#pair='+key);start.assert_not_called()


class RehearsalTests(HubFixture):
    def data(self,**changes):
        return {'title':'Synthetic rehearsal','kind':'gaming','media_id':self.item['id'],
                'checks':{k:False for k in requirements('gaming')},'owner_reviewed':True,**changes}

    def test_saved_missing_capture_folder_does_not_disable_entire_workspace(self):
        root=Path(self.tmp.name)/'other-workspace';root.mkdir()
        missing=str(Path(self.tmp.name)/'disconnected-capture-folder')
        (root/'connections.json').write_text(json.dumps({'recordings_root':missing}))
        ws=Workspace(root)
        try:
            self.assertIsNone(ws.recordings_root);self.assertIn('unavailable',ws.recordings_issue)
            result=snapshot(ws);self.assertEqual(result['capture_folder']['state'],'unavailable')
            self.assertNotIn(missing,json.dumps(result));self.assertEqual(read(root)['recordings_root'],missing)
        finally:ws.close()
        with self.assertRaises(StudioError):Workspace(root,recordings_root=missing)

    def test_rehearsal_attestation_has_no_automatic_hardware_or_public_promotion(self):
        first=save_rehearsal(self.ws,self.data())
        self.assertEqual(first['status'],'owner_reported_attention');self.assertIsNone(first['measured_upload_mbps'])
        second=save_rehearsal(self.ws,self.data(checks={k:True for k in requirements('gaming')},notes='Reviewed synthetic source'))
        self.assertEqual(second['status'],'owner_reported_pass');self.assertNotEqual(first['id'],second['id'])
        for key in ['automatic_hardware_verification','public_delivery_verified','phone_pairing_verified']:self.assertFalse(second[key])
        self.assertEqual(self.ws.get('rehearsals',first['id'])['status'],'owner_reported_attention')
        self.assertEqual(len(self.ws.listing('jobs')),0)

    def test_rehearsal_requires_owner_review_explicit_checks_and_actual_source(self):
        for changes in [{'owner_reviewed':False},{'checks':{}},{'checks':{**self.data()['checks'],'invented':True}},
                        {'measured_upload_mbps':0},{'kind':'unknown'},{'media_id':'0'*32}]:
            with self.subTest(changes=changes),self.assertRaises(StudioError):save_rehearsal(self.ws,self.data(**changes))
        self.ws.media_path(self.item['id']).write_bytes(b'changed')
        with self.assertRaisesRegex(StudioError,'checksum'):save_rehearsal(self.ws,self.data())

    def test_connection_retarget_invalidates_pending_approval_and_worker_target(self):
        with patch.dict(os.environ,{'EMBERBANTER_OBS_PASSWORD':SECRET,'EMBERBANTER_OBS_PORT':'4455'}):
            action=self.ws.propose('obs',{'action':'record_stop'})
            os.environ['EMBERBANTER_OBS_PORT']='4456'
            with self.assertRaisesRegex(StudioError,'changed after'):self.ws.approve(action['id'],action['plan_sha256'])
            with patch('websockets.sync.client.connect') as connect,self.assertRaisesRegex(StudioError,'changed after'):
                perform(action['params'],self.ws)
            connect.assert_not_called()
        self.assertFalse(self.ws.listing('jobs'))

    def test_readiness_is_redacted_read_only_and_explicit_about_unknown_hardware(self):
        live={'version':'test','recording':{'outputActive':False},'stream':{'outputActive':False},'stats':{'renderSkippedFrames':0,'renderTotalFrames':0}}
        with patch.dict(os.environ,{'EMBERBANTER_OBS_PASSWORD':SECRET}),patch('hub.readiness.status',return_value=live) as status:
            result=snapshot(self.ws,phone_origin='https://private.example')
            status.assert_called_once_with(self.ws)
        self.assertEqual(result['obs']['state'],'connected');self.assertNotIn(SECRET,json.dumps(result))
        self.assertFalse(result['phone']['verified']);self.assertEqual(result['actions_executed'],0)
        self.assertEqual(result['hardware_acceptance'],'requires_owner_rehearsal');self.assertFalse(self.ws.listing('jobs'))

    def test_real_loopback_websocket_fixture_and_reviewed_control(self):
        from websockets.sync.server import serve
        from hub.obs import status
        requests=[];errors=[]
        def handler(wire):
            try:
                wire.send(json.dumps({'op':0,'d':{'rpcVersion':1,'authentication':{'salt':'fixture-salt','challenge':'fixture-challenge'}}}))
                identify=json.loads(wire.recv(timeout=3))
                self.assertEqual(identify['d']['authentication'],obs_auth(SECRET,'fixture-salt','fixture-challenge'))
                wire.send(json.dumps({'op':2,'d':{'negotiatedRpcVersion':1}}))
                for raw in wire:
                    request=json.loads(raw)['d'];name=request['requestType'];requests.append(name)
                    result={'GetVersion':{'obsVersion':'synthetic-protocol-fixture'},'GetStats':{},
                            'GetStreamStatus':{'outputActive':False},'GetRecordStatus':{'outputActive':False},
                            'GetSceneList':{'currentProgramSceneName':'Fixture','scenes':[{'sceneName':'Fixture'}]},
                            'GetInputList':{'inputs':[{'inputName':'Fixture mic'}]},'StopRecord':{'outputPath':r'C:\private\fixture.mkv'}}[name]
                    wire.send(json.dumps({'op':7,'d':{'requestId':request['requestId'],'requestType':name,'requestStatus':{'result':True},'responseData':result}}))
            except Exception as error:errors.append(error)
        server=serve(handler,'127.0.0.1',0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            p=server.socket.getsockname()[1]
            with patch.dict(os.environ,{'EMBERBANTER_OBS_PASSWORD':SECRET,'EMBERBANTER_OBS_PORT':str(p)}):
                live=status(self.ws);self.assertTrue(live['connected'])
                self.assertEqual(live['scenes'],['Fixture']);self.assertFalse(live['recording']['outputActive'])
                action=self.ws.propose('obs',{'action':'record_stop'})
                job=self.wait_job(self.ws.approve(action['id'],action['plan_sha256']))
                self.assertEqual(job['state'],'completed',job)
                self.assertEqual(job['result']['details'],{'saved_name':'fixture.mkv'})
                self.assertFalse(job['result']['broadcast_started_by_hub'])
            self.assertEqual(requests.count('StopRecord'),1);self.assertNotIn('StartStream',requests);self.assertFalse(errors)
        finally:server.shutdown();thread.join(timeout=5)


class SetupHTTPTests(HubFixture):
    def setUp(self):
        super().setUp();self.server=StudioServer(self.ws,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.origin='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();super().tearDown()
    def request(self,method,path,data=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        connection.request(method,path,json.dumps(data) if data is not None else None,{'Origin':self.origin,'Content-Type':'application/json',**(headers or {})})
        r=connection.getresponse();result=(r.status,dict(r.getheaders()),r.read());connection.close();return result
    def pair(self):
        status,headers,raw=self.request('POST','/api/pair',{'key':self.ws.pairing_key});self.assertEqual(status,200)
        return {'Cookie':headers['Set-Cookie'].split(';')[0],'X-Studio-CSRF':json.loads(raw)['csrf']}

    def test_agent_cannot_create_owner_evidence_but_owner_can_download_it(self):
        data={'title':'Owner-reviewed synthetic fixture','kind':'podcast','media_id':self.item['id'],'checks':{k:True for k in requirements('podcast')},'owner_reviewed':True}
        agent={'Authorization':'Bearer '+self.ws.pairing_key}
        self.assertEqual(self.request('POST','/api/rehearsals',data,agent)[0],401)
        self.assertFalse(self.ws.listing('rehearsals'))
        status,_,raw=self.request('POST','/api/rehearsals',data,self.pair());self.assertEqual(status,201)
        report=json.loads(raw)
        status,headers,raw=self.request('GET','/api/rehearsal?id='+report['id']+'&download=1',headers=agent)
        self.assertEqual(status,200);self.assertIn('attachment',headers['Content-Disposition'])
        self.assertEqual(json.loads(raw)['basis'],'owner_reported')

    def test_readiness_tools_assets_and_reports_require_pairing(self):
        self.assertEqual(self.request('GET','/api/readiness')[0],401)
        client=Client(self.ws.root,self.server.server_port)
        with patch.dict(os.environ,{},clear=True):
            self.assertTrue(client.call('studio_readiness',{})['read_checks_only'])
            self.assertFalse(client.call('studio_rehearsals',{})['automatic_hardware_verification'])
        names=[t['name'] for t in TOOLS]
        self.assertNotIn('studio_rehearsal_save',names);self.assertNotIn('studio_approve',names)
        for path in ['/setup.js','/setup.css']:self.assertEqual(self.request('GET',path)[0],200)
        self.assertEqual(self.request('GET','/api/readiness-report',headers=self.pair())[0],200)

    def test_new_tools_explain_an_older_hub_without_claiming_connection(self):
        from urllib.error import HTTPError
        from io import BytesIO
        client=Client(self.ws.root,self.server.server_port)
        error=HTTPError(self.origin+'/api/readiness',404,'Not found',{},BytesIO(b'{"error":"Unknown studio route"}'))
        with patch('urllib.request.OpenerDirector.open',side_effect=error),self.assertRaisesRegex(ValueError,'require Creator Hub 0.8.0'):
            client.call('studio_readiness',{})
