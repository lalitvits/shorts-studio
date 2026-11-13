"""A simple 3D-looking clay-toy character, built from shapes (not a sculpted model).

Every part is a lit sphere or a smooth chain of overlapping spheres (a "capsule"): round head, bean-shaped body, thick
arms and legs, mitten hands, round shoes. Light comes from the top left, so each part is bright on that side and soft
and dark on the other, with no outlines, like a clay toy. The face (eyes, brows, mouth, blush) is painted on the head.
It uses the same skeleton as the other characters, so every action, emotion, prop and the lip-sync work the same way.

Choose it with a look that has style="clay" (see catalog.py). It looks simpler than the character sheets: it is a toy
made of shapes, not a detailed 3D render.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw, ImageOps

from . import rig

_TILES: dict = {}


def _lighter(c, f):
    return tuple(int(v + (255 - v) * f) for v in c)


def _darker(c, f):
    return tuple(int(v * f) for v in c)


def _tile(r: int, color: tuple) -> Image.Image:
    """A lit sphere of radius r pixels (RGBA): bright top left, soft shadow bottom right."""
    key = (r, color)
    if key in _TILES:
        return _TILES[key]
    d = 2 * r
    g = Image.radial_gradient("L").resize((4 * r, 4 * r), Image.BILINEAR)      # 0 in the middle, 255 at distance 2r
    hx, hy = int(r - 0.38 * r), int(r - 0.42 * r)                              # where the brightest spot sits in the tile
    g = g.crop((2 * r - hx, 2 * r - hy, 2 * r - hx + d, 2 * r - hy + d))
    lo = (int(color[0] * 0.50), int(color[1] * 0.47), min(255, int(color[2] * 0.55) + 8))
    col = ImageOps.colorize(g, black=_lighter(color, 0.42), white=lo, mid=color, blackpoint=0, whitepoint=185, midpoint=70)
    m = Image.new("L", (d * 3, d * 3), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d * 3 - 1, d * 3 - 1], fill=255)
    t = col.convert("RGBA")
    t.putalpha(m.resize((d, d), Image.LANCZOS))
    if len(_TILES) > 400:
        _TILES.pop(next(iter(_TILES)))
    _TILES[key] = t
    return t


def _spheres(im: Image.Image, items: list):
    """Draw spheres (cx, cy, r, colour). Lower-right ones go on top, so every pixel is shaded as if lit from the top left."""
    for cx, cy, r, col in sorted(items, key=lambda s: s[1] + 0.5 * s[0]):
        t = _tile(max(2, int(round(r))), col)
        im.paste(t, (int(cx - t.width / 2), int(cy - t.height / 2)), t)


_COLS: dict = {}
_LIGHT = (-0.62, -0.78)          # direction toward the light on the screen (top left)


def _column(r: int, color: tuple, c: float) -> Image.Image:
    """Shading across a cylinder of radius r: one column of pixels from its top side to its bottom side.
    c = how much the top side faces the light (1 lit, -1 in shadow)."""
    key = (r, color, round(c * 10))
    if key in _COLS:
        return _COLS[key]
    n, lz = 2 * r, 0.55
    sl = math.sqrt(1 - lz * lz)
    vals = []
    for i in range(n):
        v = -1 + (i + 0.5) / n * 2
        vals.append(max(0.0, -v * c * sl + math.sqrt(max(0.0, 1 - v * v)) * lz))
    mx = max(vals) or 1.0
    hi, lo = _lighter(color, 0.40), (int(color[0] * 0.50), int(color[1] * 0.47), min(255, int(color[2] * 0.55) + 8))
    cols = []
    for b in vals:
        t = max(0.10, b / mx)
        if t < 0.6:
            f, a_, b_ = t / 0.6, lo, color
        else:
            f, a_, b_ = (t - 0.6) / 0.4, color, hi
        cols.append(tuple(int(a_[i] + (b_[i] - a_[i]) * f) for i in range(3)))
    img = Image.new("RGB", (1, n))
    img.putdata(cols)
    if len(_COLS) > 600:
        _COLS.pop(next(iter(_COLS)))
    _COLS[key] = img
    return img


def _cyl(im: Image.Image, a, b, r: float, color: tuple):
    """A smooth lit cylinder from a to b (the round ends are added with spheres by the caller)."""
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    if length < 2:
        return
    r = max(2, int(round(r)))
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    ang = math.degrees(math.atan2(-dy, dx))
    c = 0.62 * math.sin(math.radians(ang)) + 0.78 * math.cos(math.radians(ang))      # how much the top side faces the light
    tile = _column(r, color, c).resize((max(1, int(length)), 2 * r), Image.NEAREST).convert("RGBA")
    rot = tile.rotate(ang, resample=Image.BICUBIC, expand=True)
    im.paste(rot, (int((a[0] + b[0]) / 2 - rot.width / 2), int((a[1] + b[1]) / 2 - rot.height / 2)), rot)


def _line(out: list, a, b, ra, rb, color, color2=None, split=1.0, step=0.14):
    """Spheres along a segment from a to b with radii ra to rb (colour changes to color2 after `split` of the way)."""
    dist = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(dist / max(2.0, step * min(ra, rb))))
    for i in range(n + 1):
        u = i / n
        out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, ra + (rb - ra) * u,
                    color if (color2 is None or u <= split) else color2))


def _hand(im, kind, wr, el, S, color):
    """Mitten hands: a round palm, plus a thumb or a finger for the gestures."""
    fx, fy = wr[0] - el[0], wr[1] - el[1]
    n = math.hypot(fx, fy) or 1.0
    fx, fy = fx / n, fy / n
    nx, ny = -fy, fx

    def at(a, b):
        return (wr[0] + (fx * a + nx * b) * S, wr[1] + (fy * a + ny * b) * S)
    items: list = []
    if kind == "thumb_up":
        c = at(6, 0)
        items.append((c[0], c[1], 21 * S, color))
        _line(items, (wr[0] + 4 * S, wr[1] - 10 * S), (wr[0] + 8 * S, wr[1] - 52 * S), 11 * S, 10 * S, color)
    elif kind == "point":
        c = at(6, 0)
        items.append((c[0], c[1], 20 * S, color))
        _line(items, at(14, 0), at(56, 0), 10 * S, 8 * S, color)
    elif kind == "open":
        c = at(16, 0)
        items.append((c[0], c[1], 23 * S, color))
        for off in (-14, -5, 5, 14):
            p = at(36, off)
            items.append((p[0], p[1], 8.5 * S, color))
        p = at(14, 24)
        items.append((p[0], p[1], 10 * S, color))
    elif kind == "ok":
        c = at(8, 0)
        items.append((c[0], c[1], 19 * S, color))
        for off in (4, 13, 21):
            p = at(28, off - 8)
            items.append((p[0], p[1], 8.5 * S, color))
    else:
        c = at(6, 0)
        items.append((c[0], c[1], (20 if kind == "fist" else 19) * S, color))
    _spheres(im, items)


def draw_clay(look: dict, pose: dict, emotion: str, mouth: float, blink: float, k: float, scale: float,
              ss: int = 2, t: float = 0.0, lipsync: bool = False, ground_shadow: bool = True, viseme=None) -> Image.Image:
    S = scale * look.get("scale", 1.0) * k * ss
    W, H = int(rig.BOX_W * k * ss), int(rig.BOX_H * k * ss)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = rig.ORG_X * k * ss, rig.ORG_Y * k * ss

    def P(pt):
        return (ox + pt[0] * S, oy + pt[1] * S)

    J = rig.solve(pose)
    skin, shirt, pants, hair, shoe = look["skin"], look["shirt"], look["pants"], look["hair"], look.get("shoe", (226, 72, 62))
    sit = bool(pose.get("sit"))
    if ground_shadow:
        d.ellipse([ox - 150 * S, oy - 10 * S, ox + 150 * S, oy + 16 * S], fill=(0, 0, 0, 55))

    # legs and round shoes: round end caps go underneath, joints (matched to the limb) cover the bends
    for n in ("l", "r"):
        hp, kn, an, ft = (P(J[x + n]) for x in ("hp_", "kn_", "an_", "ft_"))
        _spheres(im, [(hp[0], hp[1], 25.5 * S, pants), (ft[0], ft[1], 21.5 * S, shoe)])
        _cyl(im, hp, kn, 25.5 * S, pants)
        _cyl(im, kn, an, 22.5 * S, pants)
        _cyl(im, an, ft, 21.5 * S, shoe)
        _spheres(im, [(kn[0], kn[1], 24 * S, pants), (an[0], an[1], 22 * S, shoe)])

    # body: a bean shape, trousers at the bottom, shirt above
    hip, top = J["hip"], J["top"]
    mid = (hip[0] + (top[0] - hip[0]) * 0.26, hip[1] + (top[1] - hip[1]) * 0.26)
    _spheres(im, [(*P(hip), 50 * S, pants), (*P(top), 52 * S, shirt)])
    _cyl(im, P(hip), P(mid), 50 * S, pants)
    _cyl(im, P(mid), P(top), 52 * S, shirt)
    u = 0.58
    badge = P((hip[0] + (top[0] - hip[0]) * u, hip[1] + (top[1] - hip[1]) * u))
    _spheres(im, [(badge[0] + 6 * S, badge[1], 14 * S, (255, 206, 70))])            # a little yellow badge on the chest

    # neck, ears, head, hair
    hc = P(J["head"])
    r = rig.HEAD_R * S
    th = -J["head_tilt"]

    def HL(lx, ly):
        x, y = lx * r, ly * r
        return (hc[0] + x * math.cos(th) - y * math.sin(th), hc[1] + x * math.sin(th) + y * math.cos(th))
    _spheres(im, [(*P(J["top"]), 21 * S, skin)])
    items = [(*HL(sx * 1.0, 0.14), 0.24 * r, _darker(skin, 0.96)) for sx in (-1, 1)]
    _spheres(im, items)
    _spheres(im, [(hc[0], hc[1], r, skin)])
    # hair: the same round shape as the head, shown above a face-shaped opening
    pad = int(r * 1.3)
    layer = Image.new("RGBA", (2 * pad, 2 * pad), (0, 0, 0, 0))
    tile = _tile(max(2, int(round(r))), hair)
    layer.paste(tile, (pad - tile.width // 2, pad - tile.height // 2), tile)
    sc = 2
    fm = Image.new("L", (2 * pad * sc, 2 * pad * sc), 0)
    pts = []
    for a in range(0, 360, 8):
        lx, ly = 0.88 * math.cos(math.radians(a)), 0.26 + 0.80 * math.sin(math.radians(a))
        pts.append(((pad + lx * r * math.cos(th) - ly * r * math.sin(th)) * sc, (pad + lx * r * math.sin(th) + ly * r * math.cos(th)) * sc))
    ImageDraw.Draw(fm).polygon(pts, fill=255)
    fm = fm.resize((2 * pad, 2 * pad), Image.LANCZOS)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), ImageOps.invert(fm)))
    im.paste(layer, (int(hc[0] - pad), int(hc[1] - pad)), layer)
    _spheres(im, [(*HL(0.14, -1.03), 0.21 * r, hair), (*HL(-0.06, -1.13), 0.15 * r, hair)])   # a little tuft
    _spheres(im, [(*HL(0.0, 0.25), 0.10 * r, _lighter(skin, 0.06))])                           # nose

    # the face is painted on (eyes, brows, mouth, blush); mouth shapes follow the words
    ow = max(1.5, 2.6 * S)
    rig._draw_face(d, HL, r, ow, hair, skin, emotion, mouth, blink, pose, t, False,
                   viseme=viseme if lipsync else None)

    # arms: short sleeves, then bare arms and mitten hands
    for n in ("l", "r"):
        sh, el, wr = P(J["sh_" + n]), P(J["el_" + n]), P(J["wr_" + n])
        cuff = (sh[0] + (el[0] - sh[0]) * 0.55, sh[1] + (el[1] - sh[1]) * 0.55)
        _spheres(im, [(sh[0], sh[1], 22 * S, shirt), (wr[0], wr[1], 16.5 * S, skin)])
        _cyl(im, sh, cuff, 20.5 * S, shirt)
        _cyl(im, cuff, el, 19 * S, skin)
        _cyl(im, el, wr, 16.5 * S, skin)
        _spheres(im, [(el[0], el[1], 18 * S, skin)])
    prop = pose.get("prop")
    if prop:
        rig._draw_prop(d, prop, J, S, P, pose, t)
    for n in ("l", "r"):
        _hand(im, pose.get("hand_" + n, "relaxed"), P(J["wr_" + n]), P(J["el_" + n]), S, skin)
    rig._draw_fx(d, HL, r, ow, emotion, pose, t)

    return im.resize((int(rig.BOX_W * k), int(rig.BOX_H * k)), Image.LANCZOS)
