"""Backgrounds.

Every picture in assets/backgrounds/ (PNG, JPG or WebP) is a background. The file name is its id and its label in
the dropdown ("village_tea_stall.jpg" -> "Village tea stall"). To add one, drop a picture in that folder and restart.
To remove one, delete its file. Vertical pictures (9:16, like 1080 x 1920) fit best; any other shape is cropped from
the centre to fill the frame. Characters stand with their feet about 78% of the way down the picture.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image

from .catalog import FLAT_BACKGROUNDS
from .config import ASSETS_DIR
from .shading import depth_background

# ids used by older projects -> the closest picture that exists now
ALIASES = {"room": "living_room", "room_night": "living_room", "street": "street_market",
           "street_night": "street_market", "classroom_night": "classroom", "park": "garden_park",
           "park_night": "garden_park", "village": "village_tea_stall", "village_night": "village_tea_stall"}


def _files() -> dict[str, Path]:
    out = {}
    for p in sorted((ASSETS_DIR / "backgrounds").iterdir()):
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            out[p.stem] = p
    return out


def list_backgrounds() -> list[dict]:
    flat = [{"id": k, "label": v} for k, v in FLAT_BACKGROUNDS.items()]
    return flat + [{"id": i, "label": i.replace("_", " ").capitalize()} for i in _files()]


def resolve(bid: str | None) -> str | None:
    """The id of a picture that exists: the same id, or an older id's replacement, or the first picture."""
    files = _files()
    if bid in files:
        return bid
    if ALIASES.get(bid) in files:
        return ALIASES[bid]
    return "living_room" if "living_room" in files else (next(iter(files)) if files else None)


@lru_cache(maxsize=24)
def get_background(bid: str, w: int, h: int) -> Image.Image:
    files = _files()
    rid = resolve(bid)
    if rid is None:                                    # no pictures at all: plain colour so the app still works
        return Image.new("RGB", (w, h), (206, 216, 226))
    im = Image.open(files[rid]).convert("RGB")
    scale = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * scale)), max(h, round(im.height * scale))), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


@lru_cache(maxsize=24)
def get_background_3d(bid: str, w: int, h: int) -> Image.Image:
    """The background with a slight depth-of-field blur and vignette (the 3D-like look)."""
    return depth_background(get_background(bid, w, h))
