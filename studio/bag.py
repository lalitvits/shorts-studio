"""The mystery bag: a travel bag lying on the floor of a scene that can shake by itself, pop open, and let a photo
fly out (shown big in front of the camera).

A line's "bag" sets what happens from that line on: here (it lies there), shake (shakes during the line), open
(pops open and stays open), photo (a photo flies out and is held up big during the line, then lies next to the bag),
gone (it is taken away). The bag stays in the following scenes with the same background, as it was left.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

BAG_LABELS = {"": "Bag: no change", "here": "Bag: lies on the floor", "shake": "Bag: shakes by itself",
              "open": "Bag: pops open", "photo": "Bag: a photo flies out (shown big)", "gone": "Bag: taken away"}
BAG_STATES = [k for k in BAG_LABELS if k]
BAG_DX = 380            # where the bag lies: this far right of the middle of the scene's wide shot (picture units)
OUT = (36, 31, 32)
LEATHER, DARK, STRAP, BRASS = (138, 84, 46), (104, 60, 32), (90, 52, 28), (226, 180, 70)


# ------------------------------------------------------------------ what the bag does when
def plan(sched) -> dict:
    """id(scene) -> [(start, end, state while active, state afterwards)] for scenes that have the bag."""
    out, rest, last_bg = {}, None, None
    for sc in sched:
        if sc.card is not None:
            continue
        evs = [(ln.start, ln.end, ln.bag) for ln in sc.lines if getattr(ln, "bag", "")]
        start = rest if rest and sc.bg == last_bg else None
        if start is None and not evs:
            continue
        start = start or "here"
        lst, cur = [(sc.start, sc.start, start, start)], start
        for a, b, s in evs:
            if s == "shake":
                after = cur if cur in ("open", "opened") else "here"
            elif s == "photo":
                after = "opened"
            elif s == "gone":
                after = None
            else:
                after = s
            lst.append((a, b, s, after))
            cur = after
        out[id(sc)] = lst
        rest, last_bg = cur, sc.bg
    return out


def state_at(entries: list, t: float):
    """(mode, seconds into it, line length) at time t: mode is here / shake / open / photo / opened, or None."""
    cur = None
    for a, b, active, after in entries:
        if a > t:
            break
        cur = (active, t - a, max(0.3, b - a)) if t < b and active in ("shake", "open", "photo") else (after, t - a, 1.0)
    if cur is None or cur[0] in (None, "gone"):
        return None
    return cur


def sound_events(sched) -> list:
    out = []
    for sc in sched:
        for ln in sc.lines:
            s = getattr(ln, "bag", "")
            if s == "shake":
                k = 0.0
                while k < min(2.4, ln.end - ln.start):
                    out.append((ln.start + k, "rustle", 0.9))
                    k += 0.7
            elif s == "open":
                out += [(ln.start + 0.05, "pop", 0.9), (ln.start + 0.08, "spring", 0.5)]
            elif s == "photo":
                out += [(ln.start + 0.05, "pop", 0.7), (ln.start + 0.12, "whoosh", 0.8)]
    return out


# ------------------------------------------------------------------ drawing
class _P:
    def __init__(self, d, ox, oy, s):
        self.d, self.ox, self.oy, self.s = d, ox, oy, s

    def p(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def w(self, v):
        return max(1, round(v * self.s))


def _bag_image(mode: str, tt: float, s: float):
    """The bag on its own canvas (origin at the middle of its bottom)."""
    W, H = round(520 * s), round(420 * s)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = _P(d, W / 2, H - 20 * s, s)
    pop = 1.0
    if mode == "open" and tt < 0.35:                       # pops open with a bounce
        pop = 1 + 0.12 * math.sin(math.pi * tt / 0.35)
    P.s = s * pop
    is_open = mode in ("open", "photo", "opened")
    d.rounded_rectangle(P.box(-150, -175, 150, 0), radius=P.w(58), fill=LEATHER, outline=OUT, width=P.w(6))
    d.rounded_rectangle(P.box(-150, -50, 150, 0), radius=P.w(30), fill=DARK)          # bottom band
    d.rounded_rectangle(P.box(-150, -175, 150, 0), radius=P.w(58), outline=OUT, width=P.w(6))
    for sx in (-78, 78):                                   # straps and buckles
        d.rectangle(P.box(sx - 16, -175, sx + 16, 0), fill=STRAP, outline=OUT, width=P.w(3))
        d.rectangle(P.box(sx - 20, -120, sx + 20, -90), fill=BRASS, outline=OUT, width=P.w(3))
        d.rectangle(P.box(sx - 9, -112, sx + 9, -98), fill=STRAP)
    if is_open:                                            # the top gapes open: dark inside, flaps out
        d.ellipse(P.box(-122, -205, 122, -140), fill=(46, 30, 20), outline=OUT, width=P.w(5))
        d.polygon([P.p(-122, -172), P.p(-175, -232), P.p(-40, -205)], fill=LEATHER, outline=OUT)
        d.polygon([P.p(122, -172), P.p(175, -232), P.p(40, -205)], fill=LEATHER, outline=OUT)
        if mode == "open" and tt < 1.2:                    # a puff of dust
            r = 40 + 120 * min(1.0, tt / 1.2)
            a = round(170 * (1 - min(1.0, tt / 1.2)))
            for dx in (-90, 0, 90):
                d.ellipse(P.box(dx - r * 0.5, -230 - r * 0.6, dx + r * 0.5, -230 + r * 0.2), fill=(220, 210, 190, a))
    else:
        d.line([P.p(-125, -160), P.p(125, -160)], fill=OUT, width=P.w(5))             # zip
        d.rectangle(P.box(88, -168, 104, -138), fill=BRASS, outline=OUT, width=P.w(2))
        d.arc(P.box(-75, -250, 75, -130), 180, 360, fill=OUT, width=P.w(26))           # handle
        d.arc(P.box(-75, -250, 75, -130), 180, 360, fill=STRAP, width=P.w(16))
    if mode == "shake":                                    # rustle lines
        for side in (-1, 1):
            for j in range(3):
                x, y = side * (185 + 22 * j), -150 + 40 * j + 10 * math.sin(tt * 30 + j)
                d.arc(P.box(x - 24, y - 30, x + 24, y + 30), 300 if side > 0 else 120, 60 if side > 0 else 240,
                      fill=OUT, width=P.w(5))
    if mode == "opened":                                   # the photo lies next to it
        d.polygon([P.p(170, 0), P.p(260, -12), P.p(270, 50 - 50), P.p(178, 10)], fill=(250, 248, 240))
        d.rectangle(P.box(185, -60, 255, 0), fill=(250, 248, 240), outline=OUT, width=P.w(3))
        d.rectangle(P.box(193, -52, 247, -8), fill=(170, 130, 90))
    return im


def draw_bag(im: Image.Image, px: float, py: float, s: float, mode: str, tt: float):
    """The bag lying on the floor with its bottom middle at pixel (px, py); s = pixels per picture unit."""
    spr = _bag_image(mode, tt, s)
    hop = 0.0
    if mode == "shake":
        spr = spr.rotate(9 * math.sin(tt * 24), resample=Image.BICUBIC, center=(spr.width / 2, spr.height - 20 * s))
        hop = abs(math.sin(tt * 12)) * 14 * s
    sh = Image.new("RGBA", (round(360 * s), round(40 * s)), (0, 0, 0, 0))            # shadow
    ImageDraw.Draw(sh).ellipse([0, 0, sh.width - 1, sh.height - 1], fill=(20, 18, 30, 70))
    im.paste(sh, (round(px - sh.width / 2), round(py - sh.height / 2)), sh)
    im.paste(spr, (round(px - spr.width / 2), round(py - spr.height + 20 * s - hop)), spr)


def _photo_card(size: int) -> Image.Image:
    """An old sepia photograph of a man with a big mustache, in a white border."""
    W, H = size, round(size * 1.25)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = W / 600
    P = _P(d, 0, 0, s)
    d.rectangle(P.box(0, 0, 600, 750), fill=(250, 247, 238), outline=(120, 110, 96), width=P.w(6))
    for y in range(round(50 * s), round(640 * s)):                                     # sepia background
        u = (y / s - 50) / 590
        c = (int(196 - 50 * u), int(164 - 48 * u), int(120 - 40 * u))
        d.line([(50 * s, y), (550 * s, y)], fill=c)
    sep = lambda v: (int(v * 0.95), int(v * 0.78), int(v * 0.56))                     # noqa: E731
    d.pieslice(P.box(110, 470, 490, 860), 180, 360, fill=sep(70), outline=sep(40), width=P.w(5))   # coat
    d.polygon([P.p(250, 480), P.p(300, 560), P.p(350, 480)], fill=sep(230))                       # collar
    d.rectangle(P.box(262, 430, 338, 500), fill=sep(190))                                          # neck
    d.ellipse(P.box(185, 170, 415, 450), fill=sep(205), outline=sep(60), width=P.w(5))             # face
    d.pieslice(P.box(175, 140, 425, 330), 180, 360, fill=sep(120))                                 # hair
    d.ellipse(P.box(165, 280, 205, 350), fill=sep(195), outline=sep(60), width=P.w(4))             # ears
    d.ellipse(P.box(395, 280, 435, 350), fill=sep(195), outline=sep(60), width=P.w(4))
    for ex in (255, 345):
        d.line([P.p(ex - 34, 288), P.p(ex + 30, 280)], fill=sep(50), width=P.w(12))                 # bushy brows
        d.ellipse(P.box(ex - 10, 305, ex + 10, 327), fill=sep(40))
    d.line([P.p(300, 320), P.p(292, 370), P.p(310, 372)], fill=sep(90), width=P.w(5))               # nose
    d.polygon([P.p(220, 405), P.p(262, 382), P.p(300, 392), P.p(338, 382), P.p(380, 405), P.p(352, 412),
               P.p(300, 404), P.p(248, 412)], fill=sep(45))                                          # big mustache
    for k in range(260):                                                                             # old-photo specks
        x, y = (k * 97) % 500 + 50, (k * 61) % 590 + 50
        if k % 3 == 0:
            d.point(P.p(x, y), fill=sep(250))
    d.rectangle(P.box(240, -12, 360, 28), fill=(236, 226, 180, 220))                               # tape
    return im


_CARD: dict = {}


def draw_photo(im: Image.Image, from_xy, u: float, t: float):
    """The photo flying out of the bag (u = seconds into the line) and held up big in the middle of the frame."""
    w, h = im.size
    size = round(w * 0.62)
    if size not in _CARD:
        _CARD[size] = _photo_card(size)
    e = min(1.0, u / 0.45)
    e = 1 - (1 - e) ** 3
    k = 0.12 + 0.88 * e
    ang = 30 * (1 - e) - 4 + 1.5 * math.sin(t * 2.2) * e
    tx, ty = w / 2, h * 0.42
    fx, fy = from_xy if from_xy else (w * 0.8, h * 0.85)
    cx, cy = fx + (tx - fx) * e, fy + (ty - fy) * e - math.sin(math.pi * e) * h * 0.08
    card = _CARD[size].resize((max(2, round(size * k)), max(2, round(size * 1.25 * k))), Image.BILINEAR)
    card = card.rotate(ang, resample=Image.BICUBIC, expand=True)
    if e >= 1:                                                 # a soft shadow behind it
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        sh.putalpha(card.getchannel("A").point(lambda v: int(v * 0.35)))
        im.paste(sh, (round(cx - card.width / 2 + 14), round(cy - card.height / 2 + 18)), sh)
    im.paste(card, (round(cx - card.width / 2), round(cy - card.height / 2)), card)
