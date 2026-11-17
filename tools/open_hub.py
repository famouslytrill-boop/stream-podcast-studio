"""Open the local hub; start its server only if it is not already running."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen
import webbrowser


def main():
    origin = "http://127.0.0.1:8765"
    workspace = Path.home() / "Documents" / "EmberBanterHub"
    try:
        with urlopen(origin + "/api/health", timeout=2) as r:
            if json.load(r).get("service") != "emberbanter-studio":
                raise ValueError("Another service is using the studio port")
        key = (workspace / ".pairing-key").read_text(encoding="ascii").strip()
        webbrowser.open(origin + "/#pair=" + key)
    except OSError:
        subprocess.Popen([sys.executable, "-m", "hub.server", "--workspace", str(workspace), "--open"],
                         cwd=Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    main()
