"""Loopback web control surface. HTTPS phone access requires a private reverse proxy."""
from __future__ import annotations
import argparse
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import socket
import tempfile
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit
import webbrowser

from hub import VERSION
from hub.core import Workspace, canonical, identifier
from tools.studio_tools import StudioError, doctor

WEB = Path(__file__).parent / "web"
MAX_UPLOAD = 2 * 1024 ** 3
MAX_JSON = 500_000


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, workspace, port=8765, public_origin=None):
        self.workspace = workspace
        self.browser_sessions = {}
        self.auth_lock = threading.Lock()
        self.pair_attempts = []
        self.public_origin = None
        if public_origin:
            url = urlsplit(public_origin)
            if (url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment
                    or url.path not in {"", "/"} or url.port not in {None, 443}):
                raise StudioError("Phone origin needs an explicit HTTPS hostname with no path or credentials")
            self.public_origin = "https://" + url.netloc.lower()
        super().__init__(("127.0.0.1", port), Handler)
        self.origins = {f"http://127.0.0.1:{self.server_port}", f"http://localhost:{self.server_port}"}
        if self.public_origin:
            self.origins.add(self.public_origin)
        self.hosts = {urlsplit(origin).netloc for origin in self.origins}


class Handler(BaseHTTPRequestHandler):
    server_version = "EmberBanter"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        # URLs and bodies may contain private titles and keys; do not log requests.
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def headers_for(self, status, length, content_type="application/json", extra=None):
        self.send_response(status)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def reply(self, status, value, extra=None):
        raw = canonical(value).encode()
        self.headers_for(status, len(raw), extra=extra)
        self.wfile.write(raw)

    def guard_host(self, write=False):
        if self.headers.get("Host", "").lower() not in self.server.hosts:
            raise PermissionError("This hostname is not paired with the studio")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise PermissionError("Cross-site requests are not allowed")
        origin = self.headers.get("Origin")
        if origin and origin not in self.server.origins:
            raise PermissionError("Use the studio's own page for this request")
        if write and not origin and not self.headers.get("Authorization"):
            raise PermissionError("A same-origin request is required")

    def authenticate(self, *, write=False, owner_only=False):
        self.guard_host(write)
        authorization = self.headers.get("Authorization", "")
        if authorization.startswith("Bearer ") and not owner_only:
            if secrets.compare_digest(authorization[7:], self.server.workspace.pairing_key):
                return "local-agent"
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            sid = cookie.get("studio_session")
            sid = sid.value if sid else ""
        except Exception:
            sid = ""
        with self.server.auth_lock:
            session = self.server.browser_sessions.get(sid)
        if not session or session["expires"] < time.time():
            raise PermissionError("Pair this browser with your laptop to continue")
        if write and not secrets.compare_digest(self.headers.get("X-Studio-CSRF", ""), session["csrf"]):
            raise PermissionError("Refresh the studio page and retry")
        return session

    def length(self, maximum):
        if self.headers.get("Transfer-Encoding"):
            raise StudioError("Use a request with a known file length")
        value = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"\d{1,12}", value) or not 0 < int(value) <= maximum:
            raise StudioError("Request is empty or exceeds its size budget")
        return int(value)

    def read_json(self):
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise StudioError("Send JSON for studio commands")
        length = self.length(MAX_JSON)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise StudioError("Request was interrupted")
        def bad_constant(value):
            raise StudioError("Numbers must be finite")
        data = json.loads(raw, parse_constant=bad_constant)
        if not isinstance(data, dict):
            raise StudioError("Request needs a JSON object")
        return data

    def do_GET(self):
        try:
            self.guard_host()
            url = urlsplit(self.path)
            path = url.path
            if path == "/api/health":
                self.reply(200, {"service": "emberbanter-studio", "version": VERSION})
                return
            if path.startswith("/api/"):
                auth = self.authenticate()
                ws = self.server.workspace
                query = parse_qs(url.query)
                if path == "/api/state":
                    binary = doctor()
                    sessions = [{k: v for k, v in s.items() if k != "captions"} for s in ws.listing("sessions")]
                    self.reply(200, {"version": VERSION, "csrf": auth.get("csrf") if isinstance(auth, dict) else None,
                                     "media": ws.listing("media"), "sessions": sessions, "jobs": ws.listing("jobs"),
                                     "actions": [a for a in ws.listing("actions") if a["state"] == "pending" and a["expires"] > time.time()],
                                     "software": {k: v["found"] for k, v in binary["binaries"].items()},
                                     "phone_origin": self.server.public_origin, "obs_password_configured": bool(os.environ.get("EMBERBANTER_OBS_PASSWORD")),
                                     "publishing_connected": False, "go_live_available": False})
                elif path == "/api/session":
                    self.reply(200, ws.get("sessions", query.get("id", [""])[0]))
                elif path == "/api/obs":
                    from hub.obs import status
                    self.reply(200, status())
                elif path == "/api/pairing-key":
                    self.authenticate(owner_only=True)
                    self.reply(200, {"key": ws.pairing_key})
                elif path.startswith("/api/media/"):
                    self.send_file(ws.media_path(identifier(path.split("/")[-1])))
                elif path.startswith("/api/download/"):
                    parts = path.split("/")
                    if len(parts) != 5:
                        raise StudioError("Invalid download")
                    job = ws.get("jobs", identifier(parts[3]))
                    name = unquote(parts[4])
                    if job["state"] != "completed" or name not in job.get("result", {}).get("downloads", []):
                        raise StudioError("This output is not ready for download")
                    file = ws.root / "exports" / job["id"] / name
                    if file.is_symlink() or file.resolve().parent != (ws.root / "exports" / job["id"]).resolve():
                        raise StudioError("Invalid output location")
                    self.send_file(file, download=True)
                else:
                    self.reply(404, {"error": "Unknown studio route"})
                return
            names = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css",
                     "/manifest.webmanifest": "manifest.webmanifest", "/sw.js": "sw.js", "/icon.svg": "icon.svg",
                     "/brand-kits.json": "brand-kits.json", "/icon-192.png": "icon-192.png", "/icon-512.png": "icon-512.png"}
            if path not in names:
                self.reply(404, {"error": "Page not found"})
            else:
                self.send_file(WEB / names[path], static=True)
        except PermissionError as error:
            self.reply(401, {"error": str(error)})
        except (StudioError, ValueError, KeyError, OSError) as error:
            self.reply(400, {"error": str(error) if isinstance(error, StudioError) else "Cannot read this workspace item"})

    def send_file(self, file, *, download=False, static=False):
        size = file.stat().st_size
        start, end, status = 0, size - 1, 200
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
            if not match or not any(match.groups()):
                self.reply(416, {"error": "Unsupported byte range"})
                return
            if match[1]:
                start = int(match[1]); end = min(int(match[2]), end) if match[2] else end
            else:
                start = max(0, size - int(match[2]))
            if not 0 <= start <= end < size:
                self.reply(416, {"error": "Range is outside this file"}, {"Content-Range": f"bytes */{size}"})
                return
            status = 206
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if file.suffix == ".webmanifest":
            mime = "application/manifest+json"
        if file.suffix in {".html", ".js", ".css", ".svg"}:
            mime += "; charset=utf-8"
        extra = {"Accept-Ranges": "bytes"}
        if status == 206:
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        if download:
            extra["Content-Disposition"] = f'attachment; filename="{file.name}"'
        self.headers_for(status, end - start + 1, mime, extra)
        with file.open("rb") as src:
            src.seek(start)
            left = end - start + 1
            while left:
                block = src.read(min(left, 1024 * 1024))
                if not block:
                    break
                self.wfile.write(block)
                left -= len(block)

    def do_POST(self):
        try:
            self.guard_host(write=True)
            path = urlsplit(self.path).path
            ws = self.server.workspace
            if path == "/api/pair":
                data = self.read_json()
                now = time.time()
                with self.server.auth_lock:
                    self.server.pair_attempts = [t for t in self.server.pair_attempts if now-t < 60]
                    if len(self.server.pair_attempts) >= 10:
                        raise StudioError("Too many pairing attempts. Wait one minute")
                    self.server.pair_attempts.append(now)
                key = data.get("key")
                if not isinstance(key, str) or not secrets.compare_digest(key, ws.pairing_key):
                    raise PermissionError("The pairing key did not match")
                sid = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                with self.server.auth_lock:
                    self.server.browser_sessions = {k:v for k,v in self.server.browser_sessions.items() if v["expires"] > now}
                    if len(self.server.browser_sessions) >= 20:
                        self.server.browser_sessions.pop(next(iter(self.server.browser_sessions)))
                    self.server.browser_sessions[sid] = {"csrf": csrf, "expires": now + 43200}
                cookie = f"studio_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200"
                if self.headers.get("Origin", "").startswith("https://"):
                    cookie += "; Secure"
                self.reply(200, {"paired": True, "csrf": csrf}, {"Set-Cookie": cookie})
                return
            self.authenticate(write=True, owner_only=path in {"/api/approve", "/api/reject", "/api/logout"})
            if path == "/api/media":
                length = self.length(MAX_UPLOAD)
                name = unquote(self.headers.get("X-File-Name", "recording.webm"))
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(dir=ws.root / "incoming", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                        left = length
                        while left:
                            block = self.rfile.read(min(1024 * 1024, left))
                            if not block:
                                raise StudioError("Upload interrupted")
                            tmp.write(block); left -= len(block)
                    item = ws.import_media(tmp_path, name)
                    self.reply(201, item)
                finally:
                    if tmp_path:
                        tmp_path.unlink(missing_ok=True)
                return
            data = self.read_json()
            if path == "/api/sessions":
                self.reply(200, ws.save_session(data))
            elif path == "/api/propose":
                self.reply(201, ws.propose(data.get("kind"), data.get("params")))
            elif path == "/api/approve":
                self.reply(202, ws.approve(data.get("id"), data.get("plan_sha256")))
            elif path == "/api/reject":
                ws.reject(data.get("id")); self.reply(200, {"rejected": True})
            elif path == "/api/logout":
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                with self.server.auth_lock:
                    self.server.browser_sessions.pop(cookie["studio_session"].value, None)
                self.reply(200, {"paired": False}, {"Set-Cookie": "studio_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            else:
                self.reply(404, {"error": "Unknown studio command"})
        except PermissionError as error:
            self.close_connection = True
            self.reply(401, {"error": str(error)})
        except (StudioError, ValueError, TypeError, KeyError, OSError) as error:
            self.close_connection = True
            self.reply(400, {"error": str(error) if isinstance(error, StudioError) else "The request could not be completed"})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path.home() / "Documents" / "EmberBanterHub"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--public-origin", help="Verified private HTTPS phone origin; does not create a tunnel")
    parser.add_argument("--open", action="store_true", help="Open and pair the laptop's browser privately")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port from 1024 to 65535")
    ws = Workspace(args.workspace)
    try:
        server = StudioServer(ws, args.port, args.public_origin)
        print(f"EmberBanter Studio {VERSION}: http://127.0.0.1:{args.port}", flush=True)
        print("Local media service; stop with Ctrl+C. No stream or recording starts automatically.", flush=True)
        if args.open:
            webbrowser.open(f"http://127.0.0.1:{args.port}/#pair={ws.pairing_key}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        ws.close()


if __name__ == "__main__":
    main()
