"""Persisted job history, repair guidance and explicitly reviewed file-job replay."""
import json

from hub.core import canonical, identifier
from tools.studio_tools import StudioError

REPLAYABLE={"render","bumper","music_mix","music_video","midi","engineering","episode","edit_copy","narration","storyboard","performance","delivery_pack"}


def guidance(job):
    if job["state"] in {"queued","running"}:return {"code":"active","next":"Let this job finish before preparing another run.","replay_available":False}
    message=job.get("error","").lower()
    rules=[(("checksum","provenance","source changed"),"source_changed","Preserve the changed file, import the intended source and create a new reviewed plan."),
           (("disk","space"),"disk_space","Free disk space without deleting original recordings, then review a fresh run."),
           (("voice","narration","powershell"),"voice_setup","Check the installed local voice and permitted speech runtime; select it again before review."),
           (("caption",),"caption_review","Correct the words and final timing, save the current plan and review a fresh export."),
           (("expired","elsewhere","revision"),"revision_conflict","Reload the current plan revision and review the exact new action."),
           (("codec","compressed stream","remux"),"codec_path","Use an episode render for conversion or choose a supported lossless editing-copy source.")]
    found=next(((code,next_step) for terms,code,next_step in rules if any(term in message for term in terms)),None)
    if not found:
        found=("interrupted","The service restarted. This job was not automatically replayed; inspect its inputs before a new review.") if job["state"]=="interrupted" else ("inspect_result","Inspect the output or diagnostic report and listen/watch before deciding whether another run is useful.")
    return {"code":found[0],"next":found[1],"replay_available":job["kind"] in REPLAYABLE and job["state"] in {"failed","interrupted","completed"}}


def history(ws,offset=0):
    if type(offset) is not int or not 0<=offset<=100_000:raise StudioError("History offset is invalid")
    with ws.db() as db:
        rows=db.execute("SELECT data,state FROM jobs ORDER BY rowid DESC LIMIT 51 OFFSET ?",(offset,)).fetchall()
    items=[]
    for raw,state in rows[:50]:
        job={**json.loads(raw),"state":state};job["recovery"]=guidance(job);items.append(job)
    return {"jobs":items,"next_offset":offset+50 if len(rows)>50 else None,"automatic_replay":False}


def replay(ws,key):
    job=ws.get("jobs",identifier(key))
    if not guidance(job)["replay_available"]:raise StudioError("Only finished, failed or interrupted file jobs can prepare a reviewed replay. OBS, launches and capture imports are excluded")
    action=ws.get("actions",job["action_id"])
    params=action["params"]
    if action["kind"]=="render":
        saved=ws.get("sessions",params["session"]["id"])
        if saved["revision"]!=params["session"]["revision"]:raise StudioError("The edit changed after that job. Review the current session instead of replaying history")
        params={"session_id":saved["id"]}
    candidate=ws.propose(action["kind"],params,replay_of=job["id"])
    # No silent rebase of an old intention onto changed sources or capabilities.
    if canonical(candidate["params"])!=canonical(action["params"]):
        ws.reject(candidate["id"])
        raise StudioError("Inputs or capabilities changed since that job. Build and review a new plan")
    ws.log("history.replay_proposed",job["id"])
    return candidate
