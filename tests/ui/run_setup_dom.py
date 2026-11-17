"""Exercise setup DOM handlers against a real, isolated HTTP hub; no owner workspace."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from hub.core import Workspace
from hub.server import StudioServer
from tools.studio_tools import executable


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Optional non-sensitive JSON test proof')
    args=parser.parse_args()
    # No real OBS credentials or owner workspace are used by this fixture.
    for name in ('EMBERBANTER_OBS_PASSWORD','EMBERBANTER_OBS_PORT'):os.environ.pop(name,None)
    with tempfile.TemporaryDirectory(prefix='emberbanter-ui-fixture-') as temp:
        base=Path(temp);video=base/'fixture.mp4';audio=base/'fixture.wav'
        for target,options in [(video,['-f','lavfi','-i','testsrc2=size=320x180:rate=30:duration=2','-f','lavfi','-i','sine=frequency=500:duration=2','-c:v','libx264','-threads','2','-c:a','aac']),
                               (audio,['-f','lavfi','-i','sine=frequency=600:duration=2'])]:
            subprocess.run([executable('ffmpeg'),'-nostdin','-v','error','-n',*options,str(target)],check=True)
        ws=Workspace(base/'workspace');server=None
        try:
            ws.import_media(video,'Synthetic rehearsal.mp4');ws.import_media(audio,'Synthetic microphone.wav')
            server=StudioServer(ws,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            env={**os.environ,'STUDIO_QA_ORIGIN':'http://127.0.0.1:'+str(server.server_port),'STUDIO_QA_WORKSPACE':str(ws.root)}
            if args.output:env['STUDIO_QA_OUTPUT']=str(args.output.resolve())
            result=subprocess.run(['node',str(Path(__file__).with_name('setup-dom.mjs'))],env=env,cwd=ROOT,capture_output=True,text=True,timeout=40)
            print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
            return result.returncode
        finally:
            if server:server.shutdown();server.server_close();thread.join()
            ws.close()


if __name__=='__main__':raise SystemExit(main())
