"""Package the prepared EmberBanter identity assets without touching owner media."""
import io
from pathlib import Path
import zipfile


def archive():
    root = Path(__file__).parent / "web" / "brand"
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as package:
        for path in sorted(root.iterdir()):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in {".png", ".jpg", ".svg", ".json", ".wav", ".html", ".css", ".md"}:
                package.write(path, path.name)
    return target.getvalue()
