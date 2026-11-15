"""On-screen extras drawn over the video: phone-notification banners and pop-up stickers.

A line can have `popup` (a notification text, shown in a banner that slides down from the top, with a ping) and
`sticker` (an icon that pops up next to the action, with a pop). The banner's box is drawn here; its words are drawn
by the subtitle renderer (see popup_ass_events) so that Hindi letters are shaped correctly.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

OUT = (36, 31, 32)
SLIDE = 0.3           # seconds the banner takes to slide in
STICKER_KINDS = ("pizza", "burger", "money", "heart", "idea", "angry", "laugh", "question", "exclaim", "sleep", "fire")
SHOW = 3.0            # longest time a banner / sticker stays
BANNER = (50, 70, 1030, 240)     # frame units (1080 x 1920): x0, y0, x1, y1 when fully in
STICKER_AT = (800, 520)          # frame units: centre of a sticker


def _span(ln):
    return ln.start, min(ln.end + 0.4, ln.start + SHOW)


# ----------------------------------------------------------------- notification banner
def banner_y(t: float, a: float) -> float:
    """How far down (0 hidden .. 1 fully in) the banner is at time t (it slides in at a)."""
    u = (t - a) / SLIDE
    return max(0.0, min(1.0, 1 - (1 - u) ** 3)) if u >= 0 else 0.0


@lru_cache(maxsize=8)
def _banner_card(w: int, h: int):
    k = w / 1080
    x0, y0, x1, y1 = [v * k for v in BANNER]
    W, H = int(x1 - x0 + 40 * k), int(y1 - y0 + 40 * k)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([20 * k, 26 * k, W - 20 * k, H - 14 * k], radius=36 * k, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12 * k))
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card.paste((0, 0, 0, 255), (0, 0), shadow)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([20 * k, 20 * k, W - 20 * k, H - 20 * k], radius=36 * k, fill=(250, 250, 252, 255),
                        outline=(210, 214, 222, 255), width=max(1, int(2 * k)))
    ix, iy, s = 52 * k, 52 * k, 92 * k                                                # app icon
    d.rounded_rectangle([ix, iy, ix + s, iy + s], radius=22 * k, fill=(252, 98, 44, 255))
    _pizza(d, ix + s / 2, iy + s / 2 + 4 * k, s * 0.36, k)
    return card


def _pizza(d, cx, cy, r, k):
    d.polygon([(cx - r, cy - r * 0.7), (cx + r, cy - r * 0.7), (cx, cy + r)], fill=(255, 210, 90, 255))
    d.line([(cx - r, cy - r * 0.7), (cx + r, cy - r * 0.7)], fill=(190, 110, 40, 255), width=max(2, int(6 * k)))
    for px, py in ((cx - r * 0.3, cy - r * 0.25), (cx + r * 0.25, cy - r * 0.3), (cx, cy + r * 0.25)):
        d.ellipse([px - r * 0.14, py - r * 0.14, px + r * 0.14, py + r * 0.14], fill=(214, 50, 40, 255))


def draw_popup(im: Image.Image, t: float, ln, w: int, h: int):
    a, b = _span(ln)
    if not (a <= t < b):
        return
    k = w / 1080
    y = banner_y(t, a)
    fade = max(0.0, min(1.0, (b - t) / 0.25))
    card = _banner_card(w, h)
    if fade < 1:
        card = card.copy()
        card.putalpha(card.getchannel("A").point(lambda v: int(v * fade)))
    top = BANNER[1] * k - (1 - y) * (BANNER[3] - BANNER[1] + 120) * k - 20 * k
    im.paste(card, (int(BANNER[0] * k - 20 * k), int(top)), card)


def popup_ass_events(sched, w: int, h: int, ass_time) -> list:
    """Banner words, moving with the banner (title line + the notification text)."""
    out = []
    k = w / 1080
    for sc in sched:
        for ln in sc.lines:
            if not getattr(ln, "popup", ""):
                continue
            a, b = _span(ln)
            x = int(170 * k)
            dy = int((BANNER[3] - BANNER[1] + 120) * k)
            ms = int(SLIDE * 1000)
            body = re.sub(r"[\U00010000-\U0010FFFF️‍]", "", ln.popup)   # no colour emoji in subtitles
            body = body.replace("{", "").replace("}", "").strip()
            for txt, y, style in (("FoodieApp  ·  अभी", 84, "PopTitle"), (body, 128, "Pop")):
                yy = int(y * k)
                out.append(f"Dialogue: 3,{ass_time(a)},{ass_time(b)},{style},,0,0,0,,"
                           f"{{\\move({x},{yy - dy},{x},{yy},0,{ms})\\fad(0,250)}}{txt}")
    return out


def popup_ass_styles(w: int, h: int, family: str) -> str:
    k = w / 1080
    ml, mr = int(170 * k), int(w - 1000 * k)          # wrap the text inside the banner
    return (f"Style: PopTitle,{family},{int(36 * k)},&H00707070,&H00707070,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,"
            f"0,0,7,{ml},{mr},0,1\n"
            f"Style: Pop,{family},{int(54 * k)},&H00201818,&H00201818,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,"
            f"0,0,7,{ml},{mr},0,1\n")


# ----------------------------------------------------------------- flying chappal (the "throw" action)
THROW_RELEASE, THROW_HIT = 0.5, 0.95       # seconds after the line starts


@lru_cache(maxsize=48)
def chappal_image(size: int, ang10: int) -> Image.Image:
    S = size * 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = S / 2
    ang = ang10 / 10
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda px, py: (cx + (px * ca - py * sa) * S / 170, cy + (px * sa + py * ca) * S / 170)   # noqa: E731
    sole = [rot(30 * math.cos(u) * (1 + 0.15 * math.sin(u)), 72 * math.sin(u)) for u in
            [i * 2 * math.pi / 28 for i in range(28)]]
    d.polygon(sole, fill=(60, 120, 210, 255))
    d.line(sole + [sole[0]], fill=OUT + (255,), width=max(2, S // 40), joint="curve")
    for sx in (-1, 1):
        d.line([rot(0, -42), rot(sx * 25, 12)], fill=(240, 240, 240, 255), width=max(3, S // 22))
    return im.resize((size, size), Image.LANCZOS)


def draw_throw(im: Image.Image, t: float, ln, w: int, h: int):
    u = t - ln.start
    if not (THROW_RELEASE <= u < THROW_HIT + 0.08):
        return
    p = min(1.0, (u - THROW_RELEASE) / (THROW_HIT - THROW_RELEASE))
    size = int(w * (0.12 + 1.25 * p ** 2.2))                  # flies towards the camera
    spr = chappal_image(max(8, size), int(((u * 22) % 6.283) * 10))
    cx = w * (0.62 - 0.12 * p)
    cy = h * (0.42 + 0.06 * p) - h * 0.12 * math.sin(math.pi * p)
    im.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)
    if u >= THROW_HIT:                                         # the hit: a white flash
        im.paste(Image.new("RGB", im.size, (255, 255, 255)), (0, 0),
                 Image.new("L", im.size, int(150 * (1 - (u - THROW_HIT) / 0.08))))


def throw_hits(sched) -> list:
    return [ln.start + THROW_HIT for sc in sched for ln in sc.lines if ln.action == "throw"]


# ----------------------------------------------------------------- stickers
@lru_cache(maxsize=32)
def sticker_image(kind: str, size: int) -> Image.Image:
    """A flat, outlined sticker icon (drawn at 2x and reduced)."""
    S = size * 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, r = S / 2, S * 0.42
    lw = max(2, int(S * 0.025))
    d.ellipse([c - r * 1.08, c - r * 1.08, c + r * 1.08, c + r * 1.08], fill=(255, 255, 255, 235))   # sticker base
    if kind == "pizza":
        d.polygon([(c - r * 0.8, c - r * 0.6), (c + r * 0.8, c - r * 0.6), (c, c + r * 0.85)], fill=(255, 205, 90),
                  outline=OUT, width=lw)
        d.rounded_rectangle([c - r * 0.88, c - r * 0.78, c + r * 0.88, c - r * 0.5], radius=r * 0.14,
                            fill=(205, 130, 60), outline=OUT, width=lw)
        for px, py in ((c - r * 0.3, c - r * 0.25), (c + r * 0.25, c - r * 0.3), (c, c + r * 0.25)):
            d.ellipse([px - r * 0.12, py - r * 0.12, px + r * 0.12, py + r * 0.12], fill=(214, 50, 40))
    elif kind == "burger":
        d.pieslice([c - r * 0.8, c - r * 0.75, c + r * 0.8, c + r * 0.25], 180, 360, fill=(230, 160, 70), outline=OUT, width=lw)
        d.rectangle([c - r * 0.82, c - r * 0.25, c + r * 0.82, c - r * 0.08], fill=(90, 190, 80), outline=OUT, width=lw)
        d.rounded_rectangle([c - r * 0.78, c - r * 0.08, c + r * 0.78, c + r * 0.18], radius=r * 0.1, fill=(120, 60, 40), outline=OUT, width=lw)
        d.rounded_rectangle([c - r * 0.8, c + r * 0.18, c + r * 0.8, c + r * 0.5], radius=r * 0.16, fill=(230, 160, 70), outline=OUT, width=lw)
    elif kind == "money":
        for i, off in enumerate((-0.12, 0.0, 0.12)):
            d.rounded_rectangle([c - r * 0.85 + off * r, c - r * 0.45 + off * r, c + r * 0.85 + off * r, c + r * 0.45 + off * r],
                                radius=r * 0.08, fill=(130, 200, 120), outline=OUT, width=lw)
        d.ellipse([c - r * 0.25 + 0.12 * r, c - r * 0.25 + 0.12 * r, c + r * 0.25 + 0.12 * r, c + r * 0.25 + 0.12 * r],
                  fill=(90, 160, 90), outline=OUT, width=lw)
    elif kind == "heart":
        d.ellipse([c - r * 0.8, c - r * 0.6, c, c + r * 0.15], fill=(235, 60, 80))
        d.ellipse([c, c - r * 0.6, c + r * 0.8, c + r * 0.15], fill=(235, 60, 80))
        d.polygon([(c - r * 0.78, c - r * 0.12), (c + r * 0.78, c - r * 0.12), (c, c + r * 0.8)], fill=(235, 60, 80))
    elif kind == "idea":
        d.ellipse([c - r * 0.55, c - r * 0.8, c + r * 0.55, c + r * 0.3], fill=(255, 225, 80), outline=OUT, width=lw)
        d.rectangle([c - r * 0.28, c + r * 0.3, c + r * 0.28, c + r * 0.62], fill=(170, 170, 180), outline=OUT, width=lw)
        for a in range(-2, 3):
            ang = -math.pi / 2 + a * 0.5
            d.line([(c + math.cos(ang) * r * 0.75, c - r * 0.25 + math.sin(ang) * r * 0.75),
                    (c + math.cos(ang) * r * 0.98, c - r * 0.25 + math.sin(ang) * r * 0.98)], fill=(255, 190, 40), width=lw * 2)
    elif kind == "angry":
        red = (225, 40, 40)
        for ax, ay in ((-1, -1), (1, -1), (-1, 1), (1, 1)):          # the manga anger mark, big
            x0, y0 = c + ax * r * 0.62, c + ay * r * 0.62
            box = [x0 - r * 0.62, y0 - r * 0.62, x0 + r * 0.62, y0 + r * 0.62]
            st = {(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(ax, ay)]
            d.arc(box, st, st + 90, fill=red, width=lw * 5)
    elif kind == "laugh":
        d.ellipse([c - r * 0.85, c - r * 0.85, c + r * 0.85, c + r * 0.85], fill=(255, 210, 60), outline=OUT, width=lw)
        for sx in (-1, 1):
            d.arc([c + sx * r * 0.35 - r * 0.2, c - r * 0.35, c + sx * r * 0.35 + r * 0.2, c - r * 0.05], 200, 340, fill=OUT, width=lw * 2)
            d.ellipse([c + sx * r * 0.62 - r * 0.12, c - r * 0.15, c + sx * r * 0.62 + r * 0.12, c + r * 0.2], fill=(110, 190, 245))
        d.chord([c - r * 0.5, c - r * 0.1, c + r * 0.5, c + r * 0.6], 0, 180, fill=(140, 30, 40), outline=OUT, width=lw)
    elif kind in ("question", "exclaim"):
        col = (60, 120, 230) if kind == "question" else (235, 60, 50)
        if kind == "question":
            d.arc([c - r * 0.45, c - r * 0.8, c + r * 0.45, c + r * 0.1], 180, 90, fill=col, width=lw * 4)
            d.line([(c, c + r * 0.1), (c, c + r * 0.35)], fill=col, width=lw * 4)
        else:
            d.polygon([(c - r * 0.2, c - r * 0.8), (c + r * 0.2, c - r * 0.8), (c + r * 0.09, c + r * 0.35),
                       (c - r * 0.09, c + r * 0.35)], fill=col)
        d.ellipse([c - r * 0.14, c + r * 0.52, c + r * 0.14, c + r * 0.8], fill=col)
    elif kind == "sleep":
        for i, (dx, dy, z) in enumerate(((-0.35, 0.3, 0.32), (0.05, -0.05, 0.25), (0.35, -0.4, 0.18))):
            x0, y0, zz = c + dx * r, c + dy * r, z * r
            d.line([(x0 - zz, y0 - zz), (x0 + zz, y0 - zz), (x0 - zz, y0 + zz), (x0 + zz, y0 + zz)], fill=(80, 90, 160), width=lw * 2)
    elif kind == "fire":
        d.polygon([(c - r * 0.6, c + r * 0.6), (c - r * 0.7, c - r * 0.1), (c - r * 0.35, c + r * 0.05), (c - r * 0.3, c - r * 0.7),
                   (c, c - r * 0.25), (c + r * 0.2, c - r * 0.9), (c + r * 0.65, c - r * 0.1), (c + r * 0.6, c + r * 0.6)],
                  fill=(250, 110, 40), outline=OUT)
        d.polygon([(c - r * 0.3, c + r * 0.6), (c - r * 0.25, c + r * 0.1), (c, c + r * 0.25), (c + r * 0.15, c - r * 0.15),
                   (c + r * 0.32, c + r * 0.6)], fill=(255, 220, 80))
    return im.resize((size, size), Image.LANCZOS)


def draw_sticker(im: Image.Image, t: float, ln, w: int, h: int):
    a, b = _span(ln)
    kind = getattr(ln, "sticker", "")
    if not kind or not (a <= t < b):
        return
    k = w / 1080
    u = t - a
    pop = min(1.0, u / 0.18)
    scale = (0.3 + 0.9 * pop) if u < 0.18 else 1.0 + 0.08 * math.exp(-(u - 0.18) * 8) * math.sin((u - 0.18) * 30)
    fade = max(0.0, min(1.0, (b - t) / 0.25))
    size = max(8, int(230 * k * scale))
    spr = sticker_image(kind, size)
    ang = 10 * math.sin(u * 5)
    spr = spr.rotate(ang, resample=Image.BICUBIC, expand=True)
    if fade < 1:
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * fade)))
    cx, cy = STICKER_AT[0] * k, STICKER_AT[1] * k + 10 * k * math.sin(u * 3)
    im.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)
