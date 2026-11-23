"""Hindi (Devanagari) text as a picture, for signboards in the backgrounds.

The picture library here cannot join Devanagari letters (no Raqm), so the text is drawn by libass through FFmpeg
(the same engine as the captions, which joins them correctly): once in white on black for the letters, once with a
thick border for the outline. Those two masks are then painted in the wanted colours. Results are cached on disk.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageFont

from .config import CACHE_DIR, find_devanagari_font, find_ffmpeg

CACHE = CACHE_DIR / "hindi_text"
VERSION = "v1"


def _ass(text: str, w: int, h: int, size: int, family: str, border: int) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: S,{family},{size},&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,{border},0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,S,,0,0,0,,{{\\pos({w // 2},{h // 2})}}{text}
"""


def _mask(text, w, h, size, family, font, border, work: Path, name: str) -> Image.Image | None:
    (work / f"{name}.ass").write_text(_ass(text, w, h, size, family, border), encoding="utf-8")
    out = work / f"{name}.png"
    cmd = [find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=1",
           "-vf", f"ass={name}.ass:fontsdir=fonts", "-frames:v", "1", f"{name}.png"]
    try:
        subprocess.run(cmd, cwd=work, check=True, capture_output=True, timeout=30)
        return Image.open(out).convert("L")
    except Exception:  # noqa: BLE001
        return None


def text_image(text: str, size_px: int, fill, outline=None, outline_px: int = 0) -> Image.Image | None:
    """An RGBA picture of the text (trimmed), or None when it cannot be made (no FFmpeg / no Devanagari font)."""
    font = find_devanagari_font()
    if not font or not find_ffmpeg():
        return None
    key = hashlib.md5(repr((VERSION, text, size_px, fill, outline, outline_px, str(font))).encode()).hexdigest()
    path = CACHE / f"{key}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    try:
        family = ImageFont.truetype(str(font), 20).getname()[0]
    except Exception:  # noqa: BLE001
        family = "Nirmala UI"
    pad = outline_px + size_px // 3
    w = max(16, int(len(text) * size_px * 0.9) + 2 * pad) // 2 * 2
    h = max(16, int(size_px * 1.9) + 2 * pad) // 2 * 2
    work = Path(tempfile.mkdtemp(prefix="hindi_"))
    try:
        (work / "fonts").mkdir()
        shutil.copy(font, work / "fonts" / font.name)
        letters = _mask(text, w, h, size_px, family, font, 0, work, "a")
        if letters is None:
            return None
        edge = _mask(text, w, h, size_px, family, font, outline_px, work, "b") if outline and outline_px else None
    finally:
        shutil.rmtree(work, ignore_errors=True)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if edge is not None:
        layer = Image.new("RGBA", (w, h), tuple(outline) + (255,))
        layer.putalpha(edge)
        im = Image.alpha_composite(im, layer)
    layer = Image.new("RGBA", (w, h), tuple(fill) + (255,))
    layer.putalpha(letters)
    im = Image.alpha_composite(im, layer)
    bb = ImageChops.lighter(letters, edge if edge is not None else letters).getbbox()
    if bb:
        im = im.crop(bb)
    CACHE.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return im
