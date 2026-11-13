"""Paths, quality presets and font discovery."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"
DATA_DIR = ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CACHE_DIR = DATA_DIR / "cache"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = ROOT / "output"

for _d in (PROJECTS_DIR, CACHE_DIR / "tts", UPLOADS_DIR, OUTPUT_DIR,
           ASSETS_DIR / "backgrounds", ASSETS_DIR / "fonts", ASSETS_DIR / "sounds"):
    _d.mkdir(parents=True, exist_ok=True)

# All drawing code works in a 1080x1920 "world" and scales to the output size.
WORLD_W, WORLD_H = 1080, 1920
GROUND_Y = 1500  # where characters' feet touch the floor

QUALITY = {
    "low": dict(w=270, h=480, fps=15, crf=30, preset="ultrafast", ss=2),
    "preview": dict(w=540, h=960, fps=20, crf=27, preset="ultrafast", ss=2),
    "final": dict(w=1080, h=1920, fps=30, crf=20, preset="veryfast", ss=2),
}

FONT_CANDIDATES = [
    # Windows
    "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/Nirmala.ttc",
    "C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/Kokila.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
    "/System/Library/Fonts/Kohinoor.ttc",
    # Linux
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
]


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def find_devanagari_font() -> Path | None:
    """Prefer a font the user dropped into assets/fonts, then common system fonts."""
    own = sorted(p for p in (ASSETS_DIR / "fonts").iterdir()
                 if p.suffix.lower() in (".ttf", ".otf", ".ttc"))
    for p in own:
        if "devanagari" in p.name.lower():
            return p
    if own:
        return own[0]
    for c in FONT_CANDIDATES:
        if Path(c).exists():
            return Path(c)
    return None
