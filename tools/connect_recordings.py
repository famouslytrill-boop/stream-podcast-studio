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
    config_path = workspace/"connections.json"
    config = {}
    if config_path.exists():
        if config_path.is_symlink() or config_path.stat().st_size > 8192:
            raise ValueError("Invalid existing studio connection settings")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config,dict):
            raise ValueError("Studio connection settings must be an object")
    config["recordings_root"] = str(root)
    with tempfile.NamedTemporaryFile(mode="w",dir=workspace,encoding="utf-8",delete=False) as out:
        os.chmod(out.name,0o600)
        json.dump(config,out)
        temporary = out.name
    os.replace(temporary,config_path)
    print(json.dumps({"configured":True,"restart_hub_required":True,"recursive":False,"automatic_import":False}))


if __name__=="__main__":main()
