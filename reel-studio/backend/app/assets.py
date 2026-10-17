"""User-facing assets: caption fonts (built-in + uploaded) and logos."""
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageFont

from . import config

FONT_EXT = {".ttf", ".otf"}
LABELS = {"FreeSans": "FreeSans (supports Hindi)", "Liberation Sans": "Liberation Sans (Arial-like)",
          "Carlito": "Carlito (Calibri-like)", "Caladea": "Caladea (Cambria-like)"}


def _family(path: Path) -> Optional[str]:
    try:
        return ImageFont.truetype(str(path), 20).getname()[0]
    except Exception:
        return None


def list_fonts() -> List[Dict]:
    """One entry per family (prefers the Bold file). Built-ins first, then uploads."""
    out: Dict[str, Dict] = {}
    for builtin, folder in ((True, config.FONTS_DIR), (False, config.USER_FONT_DIR)):
        for f in sorted(folder.glob("*")):
            if f.suffix.lower() not in FONT_EXT:
                continue
            fam = _family(f)
            if not fam:
                continue
            better = "bold" in f.stem.lower() and "extra" not in f.stem.lower()
            if fam not in out or (better and "bold" not in out[fam]["file"].lower()):
                out[fam] = {"family": fam, "label": LABELS.get(fam, fam), "builtin": builtin, "file": f.name,
                            "url": f"/api/fonts/file/{f.name}"}
    return list(out.values())


def font_families() -> List[str]:
    return [f["family"] for f in list_fonts()]


def is_builtin(family: str) -> bool:
    return any(f["family"] == family and f["builtin"] for f in list_fonts())


def font_path(filename: str) -> Optional[Path]:
    name = Path(filename).name
    for folder in (config.FONTS_DIR, config.USER_FONT_DIR):
        if (folder / name).exists():
            return folder / name
    return None


def save_font(filename: str, data: bytes) -> Dict:
    ext = Path(filename).suffix.lower()
    if ext not in FONT_EXT:
        raise ValueError("Fonts must be .ttf or .otf files")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).stem)[:40]
    dest = config.USER_FONT_DIR / f"{safe}_{uuid.uuid4().hex[:6]}{ext}"
    dest.write_bytes(data)
    fam = _family(dest)
    if not fam:
        dest.unlink(missing_ok=True)
        raise ValueError("That file is not a valid font")
    return next(f for f in list_fonts() if f["family"] == fam)


def delete_font(filename: str) -> bool:
    p = config.USER_FONT_DIR / Path(filename).name
    if p.exists():
        p.unlink()
        return True
    return False


def font_dir_for_render(work: Path) -> Path:
    """A folder with every font (built-in + uploaded) for libass; relative path keeps ffmpeg args simple."""
    import shutil
    target = work / "fonts"
    target.mkdir(parents=True, exist_ok=True)
    for folder in (config.FONTS_DIR, config.USER_FONT_DIR):
        for f in folder.glob("*"):
            if f.suffix.lower() in FONT_EXT and not (target / f.name).exists():
                shutil.copy(f, target / f.name)
    return target


# ---------------------------------------------------------------- logos
def list_logos() -> List[Dict]:
    out = []
    for f in sorted(config.LOGO_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        name_file = f.with_suffix(".txt")
        out.append({"id": f.stem, "name": name_file.read_text(encoding="utf-8") if name_file.exists() else f.stem,
                    "url": f"/api/logos/{f.stem}/file"})
    return out


def logo_path(logo_id: Optional[str]) -> Optional[Path]:
    if not logo_id or not re.fullmatch(r"[a-f0-9]{12}", logo_id):
        return None
    p = config.LOGO_DIR / f"{logo_id}.png"
    return p if p.exists() else None


def save_logo(filename: str, data: bytes) -> Dict:
    import io
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise ValueError("That file is not a valid image (use PNG, JPG, WebP or GIF)")
    img = img.convert("RGBA")
    if img.width > 1024:
        img = img.resize((1024, max(1, int(img.height * 1024 / img.width))), Image.LANCZOS)
    logo_id = uuid.uuid4().hex[:12]
    img.save(config.LOGO_DIR / f"{logo_id}.png")
    (config.LOGO_DIR / f"{logo_id}.txt").write_text(Path(filename).stem[:60], encoding="utf-8")
    return {"id": logo_id, "name": Path(filename).stem[:60], "url": f"/api/logos/{logo_id}/file"}


def delete_logo(logo_id: str) -> bool:
    p = logo_path(logo_id)
    if not p:
        return False
    p.unlink()
    p.with_suffix(".txt").unlink(missing_ok=True)
    return True
