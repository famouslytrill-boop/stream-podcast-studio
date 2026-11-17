"""Private platform handoff files. No provider credentials, delivery or scheduling API."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import zipfile
from urllib.parse import urlsplit

from hub.core import canonical, digest
from hub.projects import title
from hub.speech import text
from tools.studio_tools import StudioError

PLATFORMS = [
    {"id":"youtube","name":"YouTube Studio","url":"https://studio.youtube.com/","use":"Live, video, Shorts and audience research","api":"not_configured"},
    {"id":"twitch","name":"Twitch Creator Dashboard","url":"https://dashboard.twitch.tv/","use":"Gaming and live conversation","api":"not_configured"},
    {"id":"spotify","name":"Spotify for Creators","url":"https://creators.spotify.com/","use":"Podcast hosting, video and analytics","api":"not_configured"},
    {"id":"tiktok","name":"TikTok Studio","url":"https://www.tiktok.com/tiktokstudio","use":"Short video, account-specific live eligibility","api":"not_configured"},
    {"id":"apple","name":"Apple Podcasts Connect","url":"https://podcastsconnect.apple.com/","use":"Podcast feed submission and management","api":"not_configured"},
]


def catalog():
    return {"platforms":PLATFORMS,"mode":"manual_browser_handoff","automatic_upload":False,"automatic_messages":False,
            "concurrency":{"heavy_workers":1,"external_browsers":"independent","obs":"independent; benchmark only while not recording/live",
                           "simulcast":"not_configured; policy, upload and encoder acceptance required"},
            "generation":{"local":"Windows installed speech voices and procedural scene renderer",
                          "remote":"No paid provider, voice cloning or external model adapter configured"}}


def timestamp(value):
    if value in (None,""):return None
    if not isinstance(value,str):raise StudioError("Calendar start needs an ISO timestamp with a timezone")
    try:result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:raise StudioError("Calendar start needs an ISO timestamp with a timezone") from None
    if result.tzinfo is None or not 2020<=result.year<=2100:raise StudioError("Calendar start needs a timezone and a year from 2020 to 2100")
    return result.astimezone(timezone.utc).isoformat()


def prepare(data):
    selected=data.get("platforms",[])
    if not isinstance(selected,list) or not 1<=len(selected)<=5 or any(not isinstance(p,str) or p not in {p['id'] for p in PLATFORMS} for p in selected):
        raise StudioError("Choose one to five listed platform destinations")
    duration=data.get("duration_minutes",60)
    if type(duration) is not int or not 15<=duration<=240:raise StudioError("Calendar length must be 15–240 minutes")
    sources=data.get("sources",[])
    if not isinstance(sources,list) or len(sources)>10:raise StudioError("Use up to ten reviewed source links")
    clean_sources=[]
    for source in sources:
        if not isinstance(source,dict):raise StudioError("Source links need a label and HTTPS URL")
        label=title(source.get("label"),150);url=source.get("url","")
        if not isinstance(url,str) or len(url)>2000 or any(ord(c)<32 for c in url):raise StudioError("Source URL is invalid")
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:raise StudioError("Use public HTTPS source links without credentials")
        clean_sources.append({"label":label,"url":url})
    if data.get("content_reviewed") is not True:raise StudioError("Review the topic, rights, claims and source dates before preparing a handoff")
    return {"title":title(data.get("title"),100),"topic":text(data.get("topic"),1000),
            "description":text(data.get("description"),4000),"platforms":list(dict.fromkeys(selected)),
            "start_at":timestamp(data.get("start_at")),"duration_minutes":duration,"sources":clean_sources,"content_reviewed":True}


def ics_text(value):
    return str(value).replace("\\","\\\\").replace("\r\n","\n").replace("\r","\n").replace("\n","\\n").replace(";","\\;").replace(",","\\,")


def fold(line):
    # RFC 5545 limits physical lines to 75 octets, never split a UTF-8 code point.
    lines=[];current=""
    for char in line:
        if len((current+char).encode("utf-8"))>75:lines.append(current);current=" "+char
        else:current+=char
    return "\r\n".join(lines+[current])


def render(ws,job_id,data):
    directory=ws.root/"exports"/job_id;directory.mkdir(exist_ok=False)
    ws.progress(job_id,"Writing reviewed platform drafts",1,2)
    destinations=[p for p in PLATFORMS if p["id"] in data["platforms"]]
    script=(f"{data['title']}\nMusic. Games. Stories.\n\nOPEN — 0:00–0:30\n"
            f"Clock out. Queue up. Pull up a chair. Today: {data['topic']}\n"
            "Give the audience one specific reason to stay, then deliver the first example.\n\n"
            "CONVERSATION — repeat as useful\n1. State one clear point.\n2. Show an example or gameplay moment.\n"
            "3. Explain your own experience; label opinion and uncertainty.\n4. Ask one answerable audience question.\n"
            "5. Sum up the useful part before moving on.\n\nCLOSE\n"
            "Recap the best moment. Invite one action: follow OR comment OR watch the next episode.\n"
            "Music and clips need permission. Verify current-event claims and event dates before recording.\n")
    notes={p['id']:{"title":data['title'],"description":data['description'],"portal":p['url'],"status":"draft_only"} for p in destinations}
    checklist=("PRIVATE HANDOFF — nothing uploaded or scheduled\n\n"
               "1. Watch/listen to the entire exported file and confirm words, cuts, chapters and captions.\n"
               "2. Verify artwork, music, game and guest permissions; remove personal details.\n"
               "3. Check source publication dates AND the dates of events discussed.\n"
               "4. Open the selected platform's official portal and sign in yourself.\n"
               "5. Set visibility to private/unlisted or draft for the first acceptance test where supported.\n"
               "6. Review title, audience designation, disclosures, thumbnail, audio and timestamps.\n"
               "7. Publish or schedule only after your own final review. Check the public result.\n\n"
               "A calendar file is a reminder draft. It does not start OBS, message people or schedule a platform upload.\n"
               "Twitch simulcasting has specific conditions: verify the current Terms of Service before enabling it.\n")
    messages=f"MESSAGE DRAFT — not sent\n\n{data['title']}\n{data['description']}\n\nAdd the actual episode link after publication. Do not invent a live URL.\n"
    files={"script-draft.txt":script,"message-draft.txt":messages,"handoff-checklist.txt":checklist,
           "platform-metadata.json":json.dumps(notes,indent=2,ensure_ascii=False),"reviewed-sources.json":json.dumps(data['sources'],indent=2,ensure_ascii=False),
           "recipe.json":json.dumps(data,indent=2,ensure_ascii=False)}
    if data['start_at']:
        start=datetime.fromisoformat(data['start_at']);end=start+timedelta(minutes=data['duration_minutes'])
        date=lambda d:d.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//EmberBanter//Private Handoff//EN","CALSCALE:GREGORIAN","BEGIN:VEVENT",
               f"UID:{job_id}@emberbanter.local",f"DTSTAMP:{date(datetime.now(timezone.utc))}",f"DTSTART:{date(start)}",f"DTEND:{date(end)}",
               "SUMMARY:"+ics_text(data['title']),"DESCRIPTION:"+ics_text("Review and prepare: "+data['topic']+"\nReminder only; no platform broadcast or upload scheduled."),"END:VEVENT","END:VCALENDAR"]
        files['review-reminder.ics']="\r\n".join(fold(l) for l in lines)+"\r\n"
    for name,content in files.items():(directory/name).write_text(content,encoding="utf-8",newline="")
    receipt={"job_id":job_id,"plan_sha256":hashlib.sha256(canonical(data).encode()).hexdigest(),"draft_only":True,"published":False,
             "messages_sent":0,"platform_api_calls":0,"calendar_events_created":0,
             "files":[{"name":name,"sha256":digest(directory/name)} for name in files]}
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    with zipfile.ZipFile(directory/'platform-handoff.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in list(files)+['receipt.json']:archive.write(directory/name,name)
    ws.progress(job_id,"Private handoff ready",2,2)
    return {**receipt,"downloads":['platform-handoff.zip']+list(files)+['receipt.json']}
