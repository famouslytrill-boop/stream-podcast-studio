#!/usr/bin/env python3
"""Open the verified user-folder Shotcut build; no capture, exports or publishing."""
import os
from pathlib import Path
import platform
import subprocess
import sys


def main():
    if platform.system() != "Windows" or not os.environ.get("LOCALAPPDATA"):
        print("This launcher needs the verified Windows editing computer.", file=sys.stderr)
        return 2
    exe = Path(os.environ["LOCALAPPDATA"]) / "EmberBanter/apps/shotcut-26.9.27/Shotcut/shotcut.exe"
    if not exe.is_file():
        print("Prepared Shotcut copy is missing; recheck its verified installation path.", file=sys.stderr)
        return 2
    subprocess.Popen([str(exe)], cwd=exe.parent)
    print("Opened the prepared Shotcut editor. No recording, export or publish command was sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
