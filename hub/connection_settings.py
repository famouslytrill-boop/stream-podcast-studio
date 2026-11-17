"""Small atomic local settings, shared by desktop setup helpers and the hub."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import time

from tools.studio_tools import StudioError


def read(root):
    path=Path(root)/"connections.json"
    if path.is_symlink():raise StudioError("Connection settings cannot be a linked file")
    if not path.exists():return {}
    if not path.is_file() or path.stat().st_size>8192:raise StudioError("Invalid local connection settings")
    try:value=json.loads(path.read_text(encoding="utf-8"))
    except (ValueError,OSError):raise StudioError("Local connection settings could not be read") from None
    if not isinstance(value,dict):raise StudioError("Connection settings need an object")
    return value


@contextmanager
def locked(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    path=root/".connections-lock"
    if path.is_symlink():raise StudioError("Connection lock cannot be a linked file")
    stream=path.open("a+b")
    stream.seek(0,2)
    if not stream.tell():stream.write(b"1");stream.flush()
    acquired=False;deadline=time.monotonic()+5
    try:
        while not acquired:
            try:
                if os.name=="nt":
                    import msvcrt
                    stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                acquired=True
            except OSError:
                if time.monotonic()>=deadline:raise StudioError("Another connection setup is in progress. Retry after it finishes") from None
                time.sleep(.05)
        yield
    finally:
        if acquired:
            if os.name=="nt":
                import msvcrt
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def update(root,change):
    """Read-modify-replace under a separate lock; preserve unrelated connection keys."""
    root=Path(root)
    with locked(root):
        current=read(root);candidate=change(dict(current))
        if not isinstance(candidate,dict):raise StudioError("Connection settings need an object")
        raw=json.dumps(candidate,ensure_ascii=False,allow_nan=False).encode("utf-8")
        if len(raw)>8192:raise StudioError("Connection settings exceed their size limit")
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=root,delete=False) as out:
                temporary=Path(out.name);os.chmod(temporary,0o600);out.write(raw);out.flush();os.fsync(out.fileno())
            os.replace(temporary,root/"connections.json")
        finally:
            if temporary:temporary.unlink(missing_ok=True)
    return candidate
