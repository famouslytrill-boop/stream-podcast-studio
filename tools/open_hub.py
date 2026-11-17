"""Open the matching local hub; never silently reuse an older server or stop owner work."""
import errno
import json
from pathlib import Path
import platform
import subprocess
import sys
from urllib.error import URLError
from urllib.request import ProxyHandler,build_opener
import webbrowser

from hub import VERSION


def notify(message):
    if platform.system()=='Windows':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,message,'EmberBanter Studio',0x40)
            return
        except (AttributeError,OSError):pass
    print(message,file=sys.stderr)


def main():
    origin='http://127.0.0.1:8765'
    workspace=Path.home()/'Documents'/'EmberBanterHub'
    try:
        # Local pairing must not follow an inherited HTTP proxy configuration.
        with build_opener(ProxyHandler({})).open(origin+'/api/health',timeout=2) as response:
            health=json.load(response)
    except URLError as error:
        reason=error.reason
        if isinstance(reason,ConnectionRefusedError) or getattr(reason,'errno',None) in {errno.ECONNREFUSED,10061}:
            subprocess.Popen([sys.executable,'-m','hub.server','--workspace',str(workspace),'--open'],cwd=Path(__file__).resolve().parent.parent)
            return 0
        notify('The local studio did not answer. Check its existing window before starting another server. No recording or service was stopped.')
        return 2
    except (OSError,ValueError):
        notify('The studio port did not return a usable health check. Inspect the existing local service; no second server was started.')
        return 2
    if not isinstance(health,dict) or health.get('service')!='emberbanter-studio':
        notify('Another service is using the studio port. Close or reconfigure it yourself before opening EmberBanter.')
        return 2
    if health.get('version')!=VERSION:
        notify(f'This launcher needs Creator Hub {VERSION}, but another version is already running. Let its jobs finish, close that hub service, then reopen this shortcut. No existing work was stopped.')
        return 2
    try:key=(workspace/'.pairing-key').read_text(encoding='ascii').strip()
    except OSError:
        notify('The running hub and this shortcut do not have the same local pairing file. Open the launcher for the running workspace instead. No second server was started.')
        return 2
    if len(key)<40:
        notify('The local pairing file is invalid. Inspect this workspace before pairing another browser.')
        return 2
    webbrowser.open(origin+'/#pair='+key)
    return 0


if __name__=='__main__':raise SystemExit(main())
