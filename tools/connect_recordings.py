"""Configure one local capture folder; never scan arbitrary browser-supplied paths."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from hub.capture import validate_root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace",default=str(Path.home()/"Documents/EmberBanterHub"))
    parser.add_argument("--root",required=True,help="Owner-selected existing OBS recordings folder")
    args = parser.parse_args(argv)
    root = validate_root(args.root)
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=workspace,encoding="utf-8",delete=False) as out:
        os.chmod(out.name,0o600)
        json.dump({"recordings_root":str(root)},out)
        temporary = out.name
    os.replace(temporary,workspace/"connections.json")
    print(json.dumps({"configured":True,"restart_hub_required":True,"recursive":False,"automatic_import":False}))


if __name__=="__main__":main()
