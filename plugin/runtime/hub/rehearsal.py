"""Append-only owner reports linked to protected recordings; no automatic hardware approval."""
import time
import uuid

from hub.core import canonical,digest,identifier
from hub.projects import title
from tools.studio_tools import StudioError,finite

COMMON={"audio_clean":"I heard clear speech without clipping","no_duplicate_audio":"I checked for echo and duplicated audio",
        "recording_reviewed":"I listened to the saved recording","guest_consent":"Recorded participants agreed, or I recorded alone",
        "rights_checked":"I reviewed music, footage and private details"}
GAMING={"game_capture_ok":"I saw the intended game picture and heard its sound","sync_ok":"Picture and sound were in sync",
        "brb_silent":"BRB audio behaved as intended","obs_stats_checked":"I checked OBS Stats under representative load"}


def requirements(kind):
    if kind not in {"podcast","gaming"}:raise StudioError("Choose a podcast or gaming rehearsal")
    return {**COMMON,**(GAMING if kind=="gaming" else {})}


def save(ws,data):
    if not isinstance(data,dict):raise StudioError("Rehearsal needs an owner review record")
    kind=data.get("kind","gaming");required=requirements(kind)
    if data.get("owner_reviewed") is not True:raise StudioError("Personally review the saved recording before saving this owner report")
    media=ws.get("media",identifier(data.get("media_id")))
    if not media.get("audio_tracks") or (kind=="gaming" and not media.get("video")):
        raise StudioError("Link an imported recording with audio and, for gaming, actual video")
    checks=data.get("checks")
    if not isinstance(checks,dict) or set(checks)!=set(required) or any(type(v) is not bool for v in checks.values()):
        raise StudioError("Record every applicable rehearsal check explicitly as true or false")
    notes=data.get("notes","")
    if not isinstance(notes,str) or len(notes)>1200 or any(ord(c)<32 and c not in "\r\n\t" for c in notes):raise StudioError("Use plain rehearsal notes under 1200 characters")
    upload=data.get("measured_upload_mbps")
    upload=None if upload is None else finite(upload,"measured upload Mbps",.01,100000)
    source=ws.media_path(media["id"])
    if digest(source)!=media["sha256"]:raise StudioError("Recording checksum changed. Preserve and import the intended recording again")
    report={"id":uuid.uuid4().hex,"title":title(data.get("title"),100),"kind":kind,"media_id":media["id"],"media_name":media["name"],
            "source_sha256":media["sha256"],"source_integrity_verified_at_save":True,"created":time.time(),"basis":"owner_reported",
            "checks":checks,"check_labels":required,"notes":notes.strip(),"measured_upload_mbps":upload,
            "upload_basis":"owner_supplied_measurement" if upload is not None else "not_measured",
            "status":"owner_reported_pass" if all(checks.values()) else "owner_reported_attention",
            "unconfirmed":[name for name,value in checks.items() if not value],"automatic_hardware_verification":False,
            "public_delivery_verified":False,"phone_pairing_verified":False,"actions_executed":0}
    with ws.db() as db:db.execute("INSERT INTO rehearsals VALUES(?,?)",(report["id"],canonical(report)))
    ws.log("rehearsal.owner_reported",report["id"])
    return report


def listing(ws):
    return {"rehearsals":ws.listing("rehearsals"),"basis":"owner_reported","automatic_hardware_verification":False,
            "requirements":{kind:requirements(kind) for kind in ("gaming","podcast")}}
