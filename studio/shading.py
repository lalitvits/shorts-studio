"""A 3D-like look for the flat characters: soft lighting, shading and depth. Not true 3D.

How it works (Pillow only, so nothing extra to install):
  * Every region inside the outlines (skin, hair, hoodie, sleeve, ...) is treated as a soft dome. A blurred copy of the
    "inside the outlines" picture is the height of the dome; light from the top left makes the top-left side brighter and
    the bottom-right side darker (like clay or a toy).
  * The edges of each region get a little darker (ambient occlusion) so parts look rounded and separate.
  * A soft highlight sits on the lit side of the domes (hair, face, shoulders).
  * Characters get a soft blurred shadow on the floor, and the background gets a slight depth-of-field blur and vignette.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageChops, ImageFilter


def _lut(f) -> list:
    return [max(0, min(255, int(f(i)))) for i in range(256)]


_DARK = _lut(lambda v: 255 if v < 80 else 0)
_OPAQUE = _lut(lambda v: 255 if v > 128 else 0)
_AO = _lut(lambda v: 170 + 85 * min(1.0, v / 215.0))
_SPEC = _lut(lambda v: max(0, v - 165) * 2.0)
_SPEC_SCALE = _lut(lambda v: v * 0.32)
_COMPRESS = _lut(lambda v: 128 + 0.8 * (v - 128))


def shade_3d(layer: Image.Image, strength: float = 1.0) -> Image.Image:
    """Return the RGBA character layer with soft 3D-like lighting."""
    w, h = layer.size
    work = 280.0 / w if w > 280 else 1.0
    ws, hs = max(16, int(w * work)), max(16, int(h * work))
    small = layer.resize((ws, hs), Image.BOX) if work < 1 else layer
    a = small.getchannel("A")
    dark = ImageChops.multiply(small.convert("L").point(_DARK), a.point(_OPAQUE))
    thick = dark.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))       # hair and pupils stay regions
    outline = ImageChops.subtract(dark, thick)                                          # thin lines only
    inside = ImageChops.subtract(a, outline)                                            # opaque, not an outline
    broad = inside.filter(ImageFilter.GaussianBlur(0.05 * ws))
    edge = inside.filter(ImageFilter.GaussianBlur(0.016 * ws))
    height = Image.blend(broad, edge, 0.4)
    d = max(1, int(round(0.012 * ws)))
    lit = ImageChops.subtract(ImageChops.offset(height, -d, -d), ImageChops.offset(height, d, d), scale=0.5, offset=128).point(_COMPRESS)
    ao = edge.point(_AO)
    spec = lit.point(_SPEC).filter(ImageFilter.GaussianBlur(0.012 * ws))
    spec = ImageChops.multiply(spec, inside).point(_SPEC_SCALE)

    def up(img):
        return img.resize((w, h), Image.BICUBIC) if work < 1 else img

    rgb = layer.convert("RGB")
    out = ImageChops.soft_light(rgb, Image.merge("RGB", (up(lit),) * 3))
    out = ImageChops.multiply(out, Image.merge("RGB", (up(ao),) * 3))
    out = ImageChops.screen(out, Image.merge("RGB", (up(spec),) * 3))
    if strength < 1:
        out = Image.blend(rgb, out, strength)
    res = out.convert("RGBA")
    res.putalpha(layer.getchannel("A"))
    return res


def soft_shadow(frame: Image.Image, cx: float, gy: float, rx: float, ry: float, blur: float, opacity: float = 0.38):
    """A soft blurred shadow on the floor under a character (centre cx, floor line gy, radii rx and ry)."""
    pad = int(blur * 3)
    bw, bh = int(2 * rx + 2 * pad), int(2 * ry + 2 * pad)
    if bw < 4 or bh < 4:
        return
    m = Image.new("L", (bw, bh), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(m).ellipse([pad, pad, pad + 2 * rx, pad + 2 * ry], fill=int(255 * opacity))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    frame.paste((20, 14, 12), (int(cx - rx - pad), int(gy - ry - pad)), m)


@lru_cache(maxsize=16)
def _vignette(w: int, h: int) -> Image.Image:
    g = Image.radial_gradient("L").resize((w, h), Image.BILINEAR).point(_lut(lambda v: 255 - v * 0.26))
    return Image.merge("RGB", (g, g, g))


def depth_background(bg: Image.Image) -> Image.Image:
    """Slight depth-of-field blur and a soft vignette, so the characters stand out from the picture behind them."""
    w, h = bg.size
    out = bg.filter(ImageFilter.GaussianBlur(max(0.6, 1.6 * w / 1080)))
    return ImageChops.multiply(out, _vignette(w, h))
