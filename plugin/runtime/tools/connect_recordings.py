"""Configure one local capture folder; never scan arbitrary browser-supplied paths."""
import argparse
import json
from pathlib import Path

from hub.capture import validate_root
from hub.connection_settings import update


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace",default=str(Path.home()/"Documents/EmberBanterHub"))
    parser.add_argument("--root",required=True,help="Owner-selected existing OBS recordings folder")
    args = parser.parse_args(argv)
    root = validate_root(args.root)
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True,exist_ok=True)
    def change(config):
        config["recordings_root"]=str(root);return config
    update(workspace,change)
    print(json.dumps({"configured":True,"restart_hub_required":True,"recursive":False,"automatic_import":False}))


if __name__=="__main__":main()
