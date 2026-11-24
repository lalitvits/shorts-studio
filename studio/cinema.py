"""The cinematic look for flat cartoon scenes: a warm colour grade, soft sun glow, vignette and film grain;
a hazy background; soft-focus grass in the foreground. All the heavy pictures are made once per frame size.

Used by flat.FlatComposer when the project's "cinematic" option is on (not for stickman scenes on white paper).
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HAZE = (252, 214, 168)                 # warm late-afternoon air
OUTDOOR = {"flat_village", "flat_chai_tapri", "flat_park", "flat_sabzi_mandi", "flat_bus_stop", "flat_city_street",
           "flat_market"}
NO_GRADE = {"flat_white", "flat_doodle"}


@lru_cache(maxsize=1)
def _lut():
    """Warm grade: reds up, blues down, gently lifted shadows and a soft S-curve."""
    def curve(v):
        return 0.5 + (v / 255 - 0.5) * 1.06

    def ch(v, k, lift):
        return max(0, min(255, int(curve(v) * 255 * k + lift * (1 - v / 255))))
    r = [ch(v, 1.03, 8) for v in range(256)]
    g = [ch(v, 0.995, 4) for v in range(256)]
    b = [ch(v, 0.93, 6) for v in range(256)]
    return r + g + b


@lru_cache(maxsize=4)
def _vignette(w, h):
    sw, sh = 96, round(96 * h / w)
    m = Image.new("L", (sw, sh))
    px = m.load()
    for y in range(sh):
        for x in range(sw):
            dx, dy = (x + 0.5) / sw - 0.5, (y + 0.5) / sh - 0.5
            d = math.hypot(dx * 1.6, dy * 1.15)
            px[x, y] = int(255 * (1 - 0.3 * min(1.0, d) ** 2.6))
    return m.resize((w, h), Image.BICUBIC).convert("RGB")


@lru_cache(maxsize=4)
def _glow(w, h):
    """Soft warm sunlight from the top right."""
    sw, sh = 96, round(96 * h / w)
    a = Image.new("L", (sw, sh))
    px = a.load()
    for y in range(sh):
        for x in range(sw):
            d = math.hypot((x / sw - 0.88) * 1.0, (y / sh - 0.04) * 0.7)
            px[x, y] = int(64 * max(0.0, 1 - d / 0.85) ** 1.8)
    a = a.resize((w, h), Image.BICUBIC)
    col = Image.new("RGB", (w, h), (255, 214, 150))
    return col, a


@lru_cache(maxsize=4)
def _grains(w, h):
    out = []
    for i in range(6):
        n = Image.effect_noise((w // 2, h // 2), 5).resize((w, h), Image.NEAREST)
        out.append(n.convert("RGB"))
    return out


def grade(im: Image.Image, t: float) -> Image.Image:
    """The finished look of one frame: colour, light, vignette, grain."""
    w, h = im.size
    im = im.point(_lut())
    col, a = _glow(w, h)
    im.paste(col, (0, 0), a)
    im = ImageChops.multiply(im, _vignette(w, h))
    g = _grains(w, h)[int(t * 24) % 6]
    return ImageChops.overlay(im, g)


def haze(im: Image.Image, amount: float = 0.12) -> Image.Image:
    """Push a background back: warm air in front of it, a little less colour."""
    return Image.blend(im, Image.new("RGB", im.size, HAZE), amount)


@lru_cache(maxsize=8)
def _grass_clump(wpx: int, hpx: int, seed: int, blur: float):
    """A tuft of tall grass / a small plant, drawn big and out of focus (it is very close to the camera)."""
    im = Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    cols = [(96, 130, 52), (124, 150, 60), (80, 112, 46), (150, 160, 70)]
    for _ in range(16):
        bx = rnd.uniform(0.2, 0.8) * wpx
        top = (rnd.uniform(-0.4, 0.4) * wpx + bx, rnd.uniform(0.0, 0.45) * hpx)
        wd = rnd.uniform(0.025, 0.06) * wpx
        d.polygon([(bx - wd, hpx), (bx + wd, hpx), top], fill=rnd.choice(cols) + (235,))
    return im.filter(ImageFilter.GaussianBlur(blur))


def foreground(im: Image.Image, seed: int, side: int):
    """Out-of-focus grass in a bottom corner (side -1 left, 1 right, 0 both), in front of everyone."""
    w, h = im.size
    cw, ch = round(w * 0.42), round(h * 0.24)
    for s_ in ((-1, 1) if side == 0 else (side,)):
        clump = _grass_clump(cw, ch, seed + (7 if s_ > 0 else 0), max(2.0, w * 0.008))
        x = round(-cw * 0.35) if s_ < 0 else round(w - cw * 0.65)
        im.paste(clump, (x, h - ch + round(h * 0.02)), clump)
