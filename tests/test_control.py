import json
from pathlib import Path
import platform
import subprocess
from unittest.mock import patch

from hub.core import canonical
from hub.distribution import prepare as delivery_prepare, fold, catalog
from hub.performance import plan
from hub.recovery import history, replay
from hub.storyboard import save, read
from hub.speech import voices
from tests.test_hub import HubFixture
from tools.studio_tools import StudioError


class ControlTests(HubFixture):
    def run_action(self,kind,data):
        action=self.ws.propose(kind,data)
        result=self.wait_job(self.ws.approve(action['id'],action['plan_sha256']))
        self.assertEqual(result['state'],'completed',result)
        return result

    def board(self,**changes):
        return {"title":"Scene test","format":"landscape","content_reviewed":True,
                "scenes":[{"title":"First scene","text":"One honest story.","seconds":2},{"title":"Second scene","text":"Pull up a chair.","seconds":2}],**changes}

    def delivery(self,**changes):
        return {"title":"Test episode","topic":"A game and a story","description":"A reviewed episode description.","platforms":["youtube","twitch"],"content_reviewed":True,**changes}

    def test_storyboard_revision_and_approval_conflicts(self):
        first=save(self.ws,self.board(content_reviewed=False))
        self.assertEqual(read(self.ws,first['document_id'])['revision'],1)
        action=self.ws.propose('storyboard',{**first,'content_reviewed':True})
        second=save(self.ws,{**first,'title':'Revised'})
        self.assertEqual(second['revision'],2)
        with self.assertRaisesRegex(StudioError,'changed after'):
            self.ws.approve(action['id'],action['plan_sha256'])
        with self.assertRaisesRegex(StudioError,'changed elsewhere'):
            save(self.ws,first)

    def test_storyboard_review_limits_and_short_footage(self):
        for changes in ({'content_reviewed':False},{'scenes':[]},{'scenes':[{'title':'Bad','seconds':1}]},
                        {'scenes':[{'title':'Auto','seconds':0}]},{'voice_id':'uninstalled'},
                        {'scenes':[{'title':'Too long','seconds':60}]*5}):
            with self.subTest(changes=changes),self.assertRaises(StudioError):self.ws.propose('storyboard',self.board(**changes))
        with self.assertRaisesRegex(StudioError,'looping'):
            self.ws.propose('storyboard',self.board(scenes=[{'title':'Long','seconds':9,'visual_id':self.item['id']}]))

    def test_actual_two_scene_film_and_integer_frame_timeline(self):
        job=self.run_action('storyboard',self.board())
        result=job['result'];out=self.ws.root/'exports'/job['id']
        self.assertTrue(result['files'][0]['full_decode_verified'])
        shots=json.loads((out/'shot-list.json').read_text())
        self.assertEqual(shots['frames'],120)
        self.assertEqual([(s['start_frame'],s['end_frame']) for s in shots['scenes']],[(0,60),(60,120)])
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(out/'storyboard.mp4')]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        self.assertEqual(int(video['nb_frames']),120)
        self.assertEqual(result['provider_calls'],0)
        self.assertIn('delivery.zip',result['downloads'])

    def test_storyboard_changed_source_fails_before_render(self):
        action=self.ws.propose('storyboard',self.board(scenes=[{'title':'Footage','seconds':2,'visual_id':self.item['id']}]))
        self.ws.media_path(self.item['id']).write_bytes(b'changed')
        result=self.wait_job(self.ws.approve(action['id'],action['plan_sha256']))
        self.assertEqual(result['state'],'failed');self.assertIn('checksum',result['error'])

    def test_narration_requires_real_voice_and_review(self):
        with self.assertRaisesRegex(StudioError,'installed'):
            self.ws.propose('narration',{'title':'No fake voice','text':'Hello','voice_id':'missing','content_reviewed':True})
        if platform.system()!='Windows':self.assertEqual(voices(),[])
        fake={'id':'local','name':'Test voice','language':'en-US','engine':'windows_sapi'}
        with patch('hub.speech.voices',return_value=[fake]),self.assertRaisesRegex(StudioError,'Review'):
            self.ws.propose('narration',{'title':'Review','text':'Hello','voice_id':'local'})

    def test_actual_windows_narration_when_available(self):
        if platform.system()!='Windows' or not voices():self.skipTest('Actual Windows voice acceptance runs on DTG')
        job=self.run_action('narration',{'title':'Local narration test','text':'Clock out. Queue up. Pull up a chair.',
                                      'voice_id':voices()[0]['id'],'content_reviewed':True})
        result=job['result']
        self.assertEqual(len(result['files']),2);self.assertEqual(result['provider_calls'],0)
        self.assertTrue(all(f['full_decode_verified'] for f in result['files']))

    def test_handoff_timezone_utf8_calendar_and_no_provider_calls(self):
        job=self.run_action('delivery_pack',self.delivery(title='Épisode, numéro; 1',start_at='2026-11-20T20:30:00-05:00',sources=[{'label':'Official date','url':'https://www.youtube.com/'}]))
        out=self.ws.root/'exports'/job['id'];raw=(out/'review-reminder.ics').read_bytes()
        self.assertIn(b'DTSTART:20261121T013000Z',raw)
        self.assertIn(b'DTEND:20261121T023000Z',raw)
        self.assertIn('Épisode\\, numéro\\; 1',raw.decode())
        self.assertNotIn(b'BEGIN:VALARM',raw)
        self.assertEqual(job['result']['platform_api_calls'],0)
        self.assertEqual(job['result']['calendar_events_created'],0)
        self.assertTrue(all(len(line)<=75 for line in fold('DESCRIPTION:'+'界'*100).encode().split(b'\r\n')))

    def test_handoff_unapproved_destinations_and_urls_are_rejected(self):
        for change in ({'platforms':['unknown']},{'content_reviewed':False},{'start_at':'2026-11-20T20:30:00'},
                       {'sources':[{'label':'bad','url':'file:///etc/passwd'}]},
                       {'sources':[{'label':'bad','url':'https://secret@youtube.com'}]},
                       {'title':'Injected\r\nBEGIN:VEVENT'}):
            with self.subTest(change=change),self.assertRaises(StudioError):delivery_prepare(self.delivery(**change))

    def test_replay_requires_fresh_exact_review_and_preserves_provenance(self):
        job=self.run_action('delivery_pack',self.delivery())
        candidate=replay(self.ws,job['id'])
        self.assertEqual(candidate['state'],'pending');self.assertEqual(candidate['replay_of'],job['id'])
        self.assertEqual(len(history(self.ws)['jobs']),1)
        second=self.wait_job(self.ws.approve(candidate['id'],candidate['plan_sha256']))
        self.assertNotEqual(job['id'],second['id']);self.assertEqual(second['replay_of'],job['id'])
        self.assertFalse(history(self.ws)['automatic_replay'])
        with self.assertRaises(StudioError):self.ws.approve(candidate['id'],candidate['plan_sha256'])

    def test_replay_never_repeats_external_side_effects(self):
        for kind in ['obs','launch_app','capture_import']:
            from hub.recovery import guidance
            self.assertFalse(guidance({'kind':kind,'state':'completed'})['replay_available'])

    def test_history_pagination_and_invalid_offsets(self):
        with self.ws.db() as db:
            for i in range(52):
                key=f'{i:032x}';db.execute('INSERT INTO jobs VALUES(?,?,?)',(key,canonical({'id':key,'kind':'delivery_pack','created':i}),'interrupted'))
        self.assertEqual(len(history(self.ws)['jobs']),50);self.assertEqual(history(self.ws)['next_offset'],50)
        self.assertEqual(len(history(self.ws,50)['jobs']),2)
        for value in [-1,True,1.5,100001]:
            with self.assertRaises(StudioError):history(self.ws,value)

    def test_upload_formula_units_and_missing_measurements(self):
        result=plan({'streams':[{'video_kbps':3000,'audio_kbps':160}]*2})
        self.assertAlmostEqual(result['direct_outbound_mbps'],6.32)
        self.assertAlmostEqual(result['planned_upload_with_headroom_mbps'],9.48)
        self.assertIsNone(result['headroom_met'])
        self.assertFalse(result['obs_settings_changed'])
        self.assertTrue(plan({'streams':[{'video_kbps':3000}],'measured_upload_mbps':10})['headroom_met'])
        self.assertTrue(all(p['api']=='not_configured' for p in catalog()['platforms']))

    def test_actual_cpu_encoder_probe_is_decoded_and_not_a_live_test(self):
        job=self.run_action('performance',{'not_live_confirmed':True,'attempt_gpu':False})
        report=job['result']['report'];self.assertTrue(report['results'][0]['executed'])
        self.assertTrue(report['results'][0]['full_decode_verified'])
        self.assertIsNone(report['comparable_render_eta'])
        self.assertTrue(report['not_a_game_or_stream_stability_test'])
        with self.assertRaisesRegex(StudioError,'not streaming'):
            self.ws.propose('performance',{})
