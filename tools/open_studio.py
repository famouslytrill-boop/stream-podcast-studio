#!/usr/bin/env python3
"""Open the verified system OBS installation; never starts capture or a stream."""
from pathlib import Path
import platform
import subprocess
import sys


def main():
    if platform.system() != "Windows":
        print("This launcher is for Dam's Windows streaming computer.", file=sys.stderr)
        return 2
    obs = Path("C:/Program Files/obs-studio/bin/64bit/obs64.exe")
    if not obs.is_file():
        print("Verified OBS path is missing. Recheck installations before changing the launcher.", file=sys.stderr)
        return 2
    subprocess.Popen([str(obs)], cwd=obs.parent)
    print("Opened system OBS. No recording or streaming start command was sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
