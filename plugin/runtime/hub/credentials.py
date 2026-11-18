"""User-scoped Windows DPAPI storage; never browser-readable or stored in Git."""
import ctypes
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import re
import secrets

from hub.connection_settings import read, update
from tools.studio_tools import StudioError

SECRET_NAME=re.compile(r"\.obs-secret-[a-f0-9]{32}\.dpapi\Z")


def port(value):
    if type(value) is not int or not 1024<=value<=65535:raise StudioError("OBS port must be an integer from 1024 to 65535")
    return value


def password(value):
    if not isinstance(value,str) or not 1<=len(value)<=1024 or any(c in value for c in "\0\r\n"):
        raise StudioError("Use the existing OBS password, entered privately on this computer")
    return value


def _dpapi(raw,*,decrypt=False):
    if platform.system()!="Windows":raise StudioError("Stored OBS credentials require the Windows account that saved them; use a private environment password on this host")
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_ubyte))]
    crypt=ctypes.WinDLL("crypt32",use_last_error=True)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL
    buffer=ctypes.create_string_buffer(raw);entropy_buffer=ctypes.create_string_buffer(b"EmberBanter:OBS:1")
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    entropy=Blob(len(entropy_buffer.raw)-1,ctypes.cast(entropy_buffer,ctypes.POINTER(ctypes.c_ubyte)))
    output=Blob()
    try:
        # User scope only: LOCAL_MACHINE is deliberately absent. No UI prompt.
        if not function(ctypes.byref(source),None,ctypes.byref(entropy),None,None,1,ctypes.byref(output)):
            raise StudioError("Windows could not unlock this credential. Connect OBS again under your own Windows account")
        if not 0<output.cbData<=65536:raise StudioError("Invalid protected credential size")
        return ctypes.string_at(output.pbData,output.cbData)
    finally:
        ctypes.memset(buffer,0,ctypes.sizeof(buffer))
        if output.pbData:
            ctypes.memset(output.pbData,0,output.cbData);kernel.LocalFree(ctypes.cast(output.pbData,ctypes.c_void_p))


def protect(value):
    value=password(value);nonce=secrets.token_hex(16)
    raw=json.dumps({"schema":"emberbanter.obs-secret.v1","password":value,"nonce":nonce,
                    "check":hashlib.sha256((nonce+value).encode()).hexdigest()},ensure_ascii=False).encode()
    return _dpapi(raw)


def unprotect(raw):
    try:
        data=json.loads(_dpapi(raw,decrypt=True).decode("utf-8"));value=password(data["password"]);nonce=data["nonce"]
        if data["schema"]!="emberbanter.obs-secret.v1" or not isinstance(nonce,str) or len(nonce)!=32:
            raise ValueError("Invalid envelope")
        if not hmac.compare_digest(data["check"],hashlib.sha256((nonce+value).encode()).hexdigest()):raise ValueError("Invalid envelope")
        return value
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise StudioError("Stored OBS credential could not be validated. Connect it again locally") from None


def profile(root=None):
    if os.environ.get("EMBERBANTER_OBS_PASSWORD"):
        try:p=int(os.environ.get("EMBERBANTER_OBS_PORT","4455"))
        except ValueError:raise StudioError("Private OBS environment port is invalid") from None
        return {"configured":True,"source":"process_environment","port":port(p),"revision":"environment:"+str(p)}
    data=read(root).get("obs") if root is not None else None
    if data is None:return {"configured":False,"source":"not_configured","port":4455,"revision":"unconfigured"}
    if not isinstance(data,dict) or not isinstance(data.get("credential_file"),str) or not SECRET_NAME.fullmatch(data["credential_file"]):
        raise StudioError("Stored OBS connection profile is invalid")
    p=port(data.get("port"));path=Path(root)/data["credential_file"]
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=65536:
        raise StudioError("Stored OBS credential is missing or moved. Connect it again locally")
    return {"configured":True,"source":"windows_dpapi","port":p,"revision":data["credential_file"],"credential_file":data["credential_file"]}


def revision(root=None):return profile(root)["revision"]


def resolve(root=None,*,expected=None):
    data=profile(root)
    if expected is not None and data["revision"]!=expected:raise StudioError("OBS connection changed after review. Review a new action")
    if not data["configured"]:raise StudioError("Connect OBS privately on the laptop before using its controls")
    value=os.environ["EMBERBANTER_OBS_PASSWORD"] if data["source"]=="process_environment" else unprotect((Path(root)/data["credential_file"]).read_bytes())
    return {"password":password(value),"port":data["port"],"revision":data["revision"]}


def save(root,value,p=4455):
    """Called only by explicit local setup, after a real authenticated read check."""
    p=port(p);raw=protect(value)
    if not hmac.compare_digest(unprotect(raw).encode("utf-8"),value.encode("utf-8")):raise StudioError("Protected credential did not pass its local round-trip check")
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    name=".obs-secret-"+secrets.token_hex(16)+".dpapi";path=root/name
    try:
        with path.open("xb") as out:
            os.chmod(path,0o600);out.write(raw);out.flush();os.fsync(out.fileno())
        previous=[]
        def change(current):
            old=current.get("obs")
            if isinstance(old,dict):previous.append(old.get("credential_file"))
            current["obs"]={"port":p,"credential_file":name};return current
        update(root,change)
    except Exception:
        path.unlink(missing_ok=True);raise
    for old in previous:
        if isinstance(old,str) and SECRET_NAME.fullmatch(old) and old!=name:
            target=root/old
            if not target.is_symlink():
                try:target.unlink(missing_ok=True)
                except OSError:pass
    return {"configured":True,"source":"windows_dpapi","port":p,"restart_required":False,"credential_roundtrip_verified":True}
