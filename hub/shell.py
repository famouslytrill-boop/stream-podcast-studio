"""Interactive studio command language: no OS shell, arbitrary paths or eval."""
import shlex

from hub.apps import APPS, inventory
from hub.projects import read_document, save_document, save_project
from hub.workflows import RECIPES
from tools.studio_tools import StudioError

HELP = """EmberBanter studio commands
help                         Show commands
status                       Show actual workspace counts
apps                         List installed studio tools
recordings                   List snapshots in the configured capture folder
open <app-id>                 Prepare a reviewed app launch
projects                     List creative projects
project <type> <title>        Create music, music_video, gaming, streaming or podcast project
files                        List versioned studio text files
new <title>                  Write a new empty studio text file
read <document-id>            Read the current file revision
write <id> <revision> <text>  Write a new revision; preserve the old file
workflows                    List deterministic recipes
history                      Show persisted jobs and repair guidance
replay <job-id>              Prepare a fresh review of an eligible file job
voices                       List actually installed local narration voices
platforms                    List official manual handoff destinations
check                        Prepare local engineering checks
run <recipe> <json>           Prepare an exact reviewed workflow
No command starts a public stream, publishes, installs packages or runs arbitrary OS code."""


def run(ws, command):
    if not isinstance(command, str) or not command.strip() or len(command) > 100_000:
        raise StudioError("Enter a studio command under 100 KB")
    verb, _, rest = command.strip().partition(" ")
    if verb == "help":
        return {"text": HELP}
    if verb == "status":
        return {"text": "Connected to your local workspace.", "counts": {k:len(ws.listing(k)) for k in ("projects","media","documents","jobs")}}
    if verb == "recordings":
        from hub.capture import scan
        return scan(ws)
    if verb == "voices":
        from hub.speech import voices
        return {"voices":voices()}
    if verb == "platforms":
        from hub.distribution import catalog
        return catalog()
    if verb == "history":
        from hub.recovery import history
        return history(ws)
    if verb == "replay":
        from hub.recovery import replay
        return {"proposal":replay(ws,rest.strip())}
    if verb == "apps":
        return {"apps": inventory()}
    if verb == "projects":
        return {"projects": ws.listing("projects")}
    if verb == "files":
        return {"files": ws.listing("documents")}
    if verb == "read":
        return {"document": read_document(ws, rest.strip())}
    if verb == "new":
        return {"document": save_document(ws, {"title":rest,"content":""})}
    if verb == "write":
        parts = rest.split(" ", 2)
        if len(parts) != 3 or not parts[1].isdigit():
            raise StudioError("Use write <document-id> <revision> <text>")
        old = read_document(ws, parts[0])
        return {"document":save_document(ws,{**old,"revision":int(parts[1]),"content":parts[2]})}
    if verb == "project":
        kind, _, name = rest.partition(" ")
        return {"project":save_project(ws,{"kind":kind,"title":name})}
    if verb == "workflows":
        return {"workflows":RECIPES}
    if verb == "check":
        return {"proposal":ws.propose("engineering",{})}
    if verb == "open":
        return {"proposal":ws.propose("launch_app",{"app":rest.strip()})}
    if verb == "run":
        import json
        recipe, _, config = rest.partition(" ")
        if recipe not in {r["id"] for r in RECIPES}:
            raise StudioError("Use a named recipe from workflows")
        try:
            params = json.loads(config or "{}")
        except ValueError:
            raise StudioError("Workflow settings need a JSON object") from None
        return {"proposal":ws.propose(recipe,params)}
    raise StudioError("Unknown studio command. Type help for the supported commands")
