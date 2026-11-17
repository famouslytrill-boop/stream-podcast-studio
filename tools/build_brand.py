"""Build exact editable EmberBanter layouts; rendered derivatives use Sharp at build time."""
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hub/web/brand"


def svg(name, width, height, body):
    text = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><style>text{{font-family:DejaVu Sans,Arial,sans-serif}}</style>{body}</svg>'
    (OUT/(name+".svg")).write_text(text, encoding="utf-8")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/"plugin/assets/emberbanter-badge.png", OUT/"badge.png")
    for name, headline, supporting in [("starting","STARTING SOON","Music. Games. Stories."),("brb","BE RIGHT BACK","Take a breath. We will be right here."),("ending","THAT'S A WRAP","Clock out. Queue up.")]:
        svg(name,1920,1080,f'<image href="room.jpg" width="1920" height="1080"/><image href="badge.png" x="80" y="75" width="190" height="190"/><text x="290" y="175" fill="#F4F1E8" font-size="60" font-weight="700">EmberBanter Studio</text><rect x="100" y="350" width="90" height="7" fill="#FF6A3D"/><text x="100" y="510" fill="#F4F1E8" font-size="104" font-weight="800">{escape(headline)}</text><text x="105" y="595" fill="#F4F1E8" font-size="36">{escape(supporting)}</text><path d="M106 650h38l-18 35H88Zm57 0h38l-18 35h-38Zm57 0h38l-18 35h-38Z" fill="#8EF2CE"/>')
    svg("podcast-cover",3000,3000,'<rect width="3000" height="3000" fill="#101216"/><path d="M0 0h650L0 650ZM3000 3000h-650l650-650Z" fill="#FF6A3D"/><image href="badge.png" x="730" y="230" width="1540" height="1540"/><text x="1500" y="1970" fill="#F4F1E8" font-size="245" text-anchor="middle" font-weight="800">EMBERBANTER</text><rect x="420" y="2110" width="2160" height="280" fill="#FF6A3D"/><text x="1500" y="2300" fill="#101216" font-size="140" text-anchor="middle" font-weight="700" letter-spacing="18">THE COOLDOWN</text><path d="M1270 2580v100m90-170v240m90-270v300m90-230v160m90-210v260m90-160v60" stroke="#8EF2CE" stroke-width="35" stroke-linecap="round"/>')
    svg("clip-frame",1080,1920,'<path d="M42 160V42h160M878 1878h160v-118" stroke="#8EF2CE" stroke-width="8" fill="none"/><image href="badge.png" x="60" y="55" width="120" height="120"/><text x="200" y="135" fill="#F4F1E8" font-size="56" font-weight="700">EmberBanter</text><rect x="68" y="1530" width="944" height="160" rx="10" fill="#101216" fill-opacity="0.82"/><rect x="68" y="1690" width="170" height="8" fill="#FF6A3D"/>')
    svg("lower-third",1920,1080,'<rect x="80" y="820" width="900" height="160" rx="12" fill="#101216" fill-opacity="0.92"/><rect x="80" y="820" width="8" height="160" fill="#FF6A3D"/><image href="badge.png" x="105" y="835" width="130" height="130"/><text x="260" y="890" fill="#F4F1E8" font-size="46" font-weight="700">DAM</text><text x="260" y="944" fill="#8EF2CE" font-size="32">EMBERBANTER STUDIO</text>')
    svg("channel-banner",2560,1440,'<rect width="2560" height="1440" fill="#101216"/><rect x="0" y="0" width="2560" height="12" fill="#FF6A3D"/><image href="badge.png" x="490" y="530" width="330" height="330"/><text x="870" y="690" fill="#F4F1E8" font-size="115" font-weight="800">EmberBanter</text><text x="875" y="780" fill="#8EF2CE" font-size="48">Music. Games. Stories.</text><text x="875" y="855" fill="#F4F1E8" font-size="34">Clock out. Queue up.</text>')
    svg("thumbnail-template",1280,720,'<image href="room.jpg" width="1280" height="720"/><image href="badge.png" x="55" y="45" width="130" height="130"/><text x="65" y="330" fill="#F4F1E8" font-size="86" font-weight="800">TONIGHT’S</text><text x="65" y="435" fill="#F4F1E8" font-size="86" font-weight="800">CHALLENGE</text><rect x="65" y="480" width="430" height="12" fill="#FF6A3D"/>')
    svg("wordmark",1600,400,'<rect width="1600" height="400" rx="24" fill="#101216"/><image href="badge.png" x="45" y="40" width="310" height="310"/><text x="395" y="177" fill="#F4F1E8" font-size="104" font-weight="800">EmberBanter</text><text x="402" y="254" fill="#8EF2CE" font-size="42" letter-spacing="7">MUSIC. GAMES. STORIES.</text>')
    svg("avatar",800,800,'<rect width="800" height="800" rx="160" fill="#101216"/><image href="badge.png" x="70" y="70" width="660" height="660"/>')
    config={"focus":["Gaming","Streaming","Podcasts"],"brand":"EmberBanter Studio","chosen_by_owner":"2026-11-17","descriptor":"Music. Games. Stories.","tagline":"Clock out. Queue up.","welcome_line":"Pull up a chair.",
            "palette":{"charcoal":"#101216","surface":"#191D22","ember":"#FF6A3D","mint":"#8EF2CE","bone":"#F4F1E8"},
            "fonts":{"headings":"DejaVu Sans bold / system sans fallback","body":"Segoe UI, system-ui, sans-serif","timecode":"ui-monospace, monospace"},
            "masters":{"scenes":[1920,1080],"podcast":[3000,3000],"vertical":[1080,1920],"banner":[2560,1440],"thumbnail":[1280,720]},
            "motion_ms":250,"reduced_motion":True,"logo":"Existing owner badge; not a trademark clearance claim", "templates_require_editorial_review":True}
    (OUT/"kit.json").write_text(json.dumps(config,indent=2),encoding="utf-8")
    (OUT/"START_HERE.md").write_text('''# EmberBanter Studio brand kit

EmberBanter is the chosen name. Music. Games. Stories. Community tagline: Clock out. Queue up.

This kit presents gaming, streaming and podcasts. Use the current identity board and episode graphics across the brand.

Use the existing badge. Keep clear space around it; test the name at phone size. Orange buttons use dark text. Bone copy on charcoal is the default; mint highlights stay restrained.

Starting, BRB and Ending masters are 1920×1080. Add their rendered images to an OBS scene; no audio or recording starts automatically. The browser scene uses relative assets and supports reduced motion. Confirm actual source routing separately.

The 1080×1920 clip frame and 1920×1080 lower third have transparent PNG derivatives. Supply real corrected captions in the media editor. The square cover is a 3000×3000 master for the proposed The Cooldown series. Change that subtitle before using it for another show. The thumbnail is a template: replace its wording so it accurately describes your episode. The banner is a master, not evidence that a platform accepted it.

SVG source layouts reference badge.png and room.jpg in this folder; keep them together. PNG/JPEG derivatives are standalone. No font files, accounts, handles, domain ownership or trademark clearance are included. The room is original generated artwork; the mark is the existing owner badge. Numerical colors in kit.json are authoritative.

The short WAV motif is an original synthesized E4–G4–B4 cue. It is optional; no sound plays automatically. Review final levels in your show.
''',encoding="utf-8")
    (OUT/"scene.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>EmberBanter starting scene</title><style>html,body{margin:0;background:#101216;color:#F4F1E8;width:100%;height:100%;overflow:hidden;font-family:system-ui,sans-serif}body{background:url(room.jpg) center/cover no-repeat}main{position:absolute;left:5.2%;top:8%;width:65%}img{width:10vw;vertical-align:middle}strong{font-size:3.1vw;margin-left:1vw}h1{margin-top:9vh;font-size:5.4vw;letter-spacing:-.04em}p{font-size:1.9vw}.rule{width:5vw;height:.4vw;background:#FF6A3D;animation:arrive .25s ease-out}@keyframes arrive{from{transform:translateX(-30px);opacity:0}to{transform:none;opacity:1}}@media(prefers-reduced-motion:reduce){.rule{animation:none}}</style><main><img src="badge.png" alt="EmberBanter"><strong>EmberBanter Studio</strong><h1>STARTING SOON</h1><div class="rule"></div><p>Music. Games. Stories.</p></main></html>''',encoding="utf-8")
    from hub.render import stinger
    stinger(OUT/"original-stinger.wav")


if __name__=="__main__":build()
