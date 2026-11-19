"""Backgrounds.

Two folders hold picture backgrounds:
  my_backgrounds/      YOUR pictures. Drop a picture here and it appears in the Background menus within a few
                       seconds (no restart). The file name is its name in the menu ("goa airport.jpg" -> "Goa airport").
                       Your pictures stay on this computer: they are not uploaded to GitHub.
  assets/backgrounds/  the pictures that come with the app.
A picture in my_backgrounds with the same name as a built-in one replaces it.

Supported files: JPG / JPEG, PNG, WebP, BMP, GIF (its first frame) and TIFF. Vertical pictures (9:16, like
1080 x 1920) fit best; any other shape is cropped from the centre to fill the frame. Characters stand with their feet
about 78% of the way down the picture. A file that cannot be read is skipped (the app says which in the menu hint).
Changing a picture (same file name) is picked up too.
"""
from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

from PIL import Image

from .catalog import FLAT_BACKGROUNDS
from .config import ASSETS_DIR, ROOT
from .shading import depth_background

MY_DIR = ROOT / "my_backgrounds"
BUILTIN_DIR = ASSETS_DIR / "backgrounds"
SUPPORTED = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff")
SUPPORTED_TEXT = "JPG, JPEG, PNG, WebP, BMP, GIF (first frame) and TIFF"

# ids used by older projects -> the closest picture that exists now
ALIASES = {"room": "living_room", "room_night": "living_room", "street": "street_market",
           "street_night": "street_market", "classroom_night": "classroom", "park": "garden_park",
           "park_night": "garden_park", "village": "garden_park", "village_night": "garden_park"}

_SCAN = {"at": 0.0, "files": {}, "mine": set(), "bad": []}


@lru_cache(maxsize=256)
def _readable(path: str, mtime: float) -> bool:
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001  not a picture Pillow can read
        return False


def _scan(force: bool = False) -> dict:
    """The pictures in both folders (looked up again at most every 2 seconds, so new files show up quickly)."""
    if not force and time.time() - _SCAN["at"] < 2.0:
        return _SCAN
    MY_DIR.mkdir(exist_ok=True)
    files, mine, bad = {}, set(), []
    for folder in (BUILTIN_DIR, MY_DIR):                  # yours last: same name replaces the built-in one
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in SUPPORTED:
                continue
            if not _readable(str(p), p.stat().st_mtime):
                bad.append(p.name)
                continue
            files[p.stem] = p
            if folder == MY_DIR:
                mine.add(p.stem)
    _SCAN.update(at=time.time(), files=files, mine=mine, bad=bad)
    return _SCAN


def _files() -> dict[str, Path]:
    return _scan()["files"]


def _label(stem: str) -> str:
    return " ".join(stem.replace("_", " ").replace("-", " ").split()).capitalize() or stem


def list_backgrounds(force: bool = False) -> list[dict]:
    s = _scan(force)
    flat = [{"id": k, "label": v} for k, v in FLAT_BACKGROUNDS.items()]
    mine = [{"id": i, "label": "Your picture: " + _label(i), "mine": True} for i in s["files"] if i in s["mine"]]
    built = [{"id": i, "label": _label(i)} for i in s["files"] if i not in s["mine"]]
    return flat + mine + built


def folder_info() -> dict:
    """What the app tells you about your backgrounds folder."""
    s = _scan(True)
    return {"folder": str(MY_DIR), "supported": SUPPORTED_TEXT, "count": len(s["mine"]), "skipped": s["bad"]}


def resolve(bid: str | None) -> str | None:
    """The id of a picture that exists: the same id, or an older id's replacement, or the first picture."""
    files = _files()
    if bid in files:
        return bid
    if ALIASES.get(bid) in files:
        return ALIASES[bid]
    return "living_room" if "living_room" in files else (next(iter(files)) if files else None)


def stamp(bid: str) -> float:
    """Changes when the picture behind a background changes (so cached drawings are made again)."""
    if bid in FLAT_BACKGROUNDS:
        return 0.0
    p = _files().get(resolve(bid) or "")
    try:
        return p.stat().st_mtime if p else 0.0
    except OSError:
        return 0.0


def get_background(bid: str, w: int, h: int) -> Image.Image:
    rid = resolve(bid)
    if rid is None:                                    # no pictures at all: plain colour so the app still works
        return Image.new("RGB", (w, h), (206, 216, 226))
    p = _files()[rid]
    return _load(str(p), stamp(bid), w, h)


@lru_cache(maxsize=24)
def _load(path: str, mtime: float, w: int, h: int) -> Image.Image:
    with Image.open(path) as src:
        src.seek(0)                                    # GIF: the first frame
        im = src.convert("RGBA")
    if im.getextrema()[3][0] < 255:                    # see-through parts (PNG): on white, not black
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    scale = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * scale)), max(h, round(im.height * scale))), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def get_background_3d(bid: str, w: int, h: int) -> Image.Image:
    """The background with a slight depth-of-field blur and vignette (the 3D-like look)."""
    return _bg3d(bid, w, h, stamp(bid))


@lru_cache(maxsize=24)
def _bg3d(bid: str, w: int, h: int, st: float) -> Image.Image:
    return depth_background(get_background(bid, w, h))
