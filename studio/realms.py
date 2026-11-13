"""Swarg (heaven) and Nark (hell): two flat-cartoon backgrounds that move.

draw_static() paints the wide picture once (sky, palace or Yama's gate, cloud floor or rock and lava);
animate() draws the moving parts on every frame (sun rays, drifting clouds, sparkles, falling petals and
doves in Swarg; flickering flames, lava bubbles, rising embers, glowing cracks, steam and bats in Nark).
All positions are in world units of the wide picture (2600 x 1920); the caller gives the mapping to pixels.
"""
from __future__ import annotations

import math
import random
import zlib
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

REALMS = ("flat_swarg", "flat_nark")
OUT = (36, 31, 32)


def _h(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def _sky(d, W, ps, stops):
    H = round(1920 * ps)
    for y in range(H):
        fu = y / ps
        for i in range(len(stops) - 1):
            (ya, ca), (yb, cb) = stops[i], stops[i + 1]
            if fu <= yb or i == len(stops) - 2:
                u = max(0.0, min(1.0, (fu - ya) / max(1, yb - ya)))
                d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(ca, cb)))
                break


def _glow(im, cx, cy, r, color, ps, strength=150):
    """Soft round light pasted onto the picture."""
    size = round(r * 2 * ps)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([size * 0.2, size * 0.2, size * 0.8, size * 0.8], fill=strength)
    m = m.filter(ImageFilter.GaussianBlur(size * 0.14))
    im.paste(color, (round((cx - r) * ps), round((cy - r) * ps)), m)


# ===================================================================== static pictures
def draw_static(bid: str, im: Image.Image, ps: float, PW: int):
    d = ImageDraw.Draw(im)
    P = lambda *v: [x * ps for x in v]     # noqa: E731
    L = lambda w: max(1, round(w * ps))     # noqa: E731
    rnd = random.Random(_h(bid))
    if bid == "flat_swarg":
        _swarg(im, d, P, L, PW, ps, rnd)
    else:
        _nark(im, d, P, L, PW, ps, rnd)


def _cloud_row(d, P, L, x0, x1, y, rmin, rmax, rnd, fill=(255, 255, 255), line=(196, 208, 236)):
    x = x0
    while x < x1:
        r = rnd.uniform(rmin, rmax)
        d.ellipse(P(x - r, y - r, x + r, y + r), fill=fill, outline=line, width=L(4))
        x += r * rnd.uniform(0.9, 1.3)


def _swarg(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (246, 190, 128)), (520, (255, 222, 182)), (1000, (255, 242, 226)), (1300, (214, 230, 252))])
    C = 1300
    _glow(im, C, 560, 620, (255, 250, 214), ps, 190)
    d = ImageDraw.Draw(im)
    d.ellipse(P(C - 120, 440, C + 120, 680), fill=(255, 238, 160))
    # rainbow on the left
    rb = Image.new("RGBA", im.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rb)
    for i, c in enumerate([(232, 70, 70), (244, 150, 60), (246, 220, 80), (110, 196, 100), (80, 150, 230), (120, 100, 200), (170, 100, 200)]):
        r = 760 - i * 30
        rd.arc(P(380 - r, 1330 - r, 380 + r, 1330 + r), 180, 360, fill=c + (130,), width=L(30))
    im.paste(rb, (0, 0), rb)
    d = ImageDraw.Draw(im)
    # far clouds along the horizon
    _cloud_row(d, P, L, -60, PW + 80, 1225, 70, 140, rnd, (255, 255, 255), (214, 222, 244))
    # palace
    gold, gold_d, white = (240, 196, 80), (176, 128, 52), (252, 249, 240)
    for i, (a, b, y) in enumerate(((960, 1640, 1210), (1000, 1600, 1170), (1040, 1560, 1132))):   # steps
        d.rectangle(P(a, y, b, y + 42), fill=white, outline=gold_d, width=L(4))
    d.ellipse(P(C - 170, 600, C + 170, 940), fill=gold, outline=gold_d, width=L(6))               # main dome
    d.rectangle(P(C - 190, 760, C + 190, 800), fill=gold, outline=gold_d, width=L(5))
    for sx in (C - 230, C + 230):                                                                  # side domes
        d.ellipse(P(sx - 80, 700, sx + 80, 860), fill=gold, outline=gold_d, width=L(5))
        d.polygon([tuple(P(sx - 8, 700)), tuple(P(sx + 8, 700)), tuple(P(sx, 640))], fill=gold_d)
    d.rectangle(P(1000, 790, 1600, 846), fill=gold, outline=gold_d, width=L(5))                     # roof beam
    for i in range(8):                                                                              # pillars
        px = 1040 + i * 74
        d.rectangle(P(px, 846, px + 40, 1132), fill=white, outline=gold_d, width=L(4))
        d.rectangle(P(px - 8, 846, px + 48, 868), fill=gold, outline=gold_d, width=L(3))
        d.rectangle(P(px - 8, 1112, px + 48, 1132), fill=gold, outline=gold_d, width=L(3))
    d.polygon([tuple(P(C - 12, 610)), tuple(P(C + 12, 610)), tuple(P(C, 500))], fill=gold_d)        # spire (kalash)
    for r, y in ((22, 590), (16, 560)):
        d.ellipse(P(C - r, y - r, C + r, y + r), fill=gold, outline=gold_d, width=L(3))
    # small pavilions on clouds
    for px in (420, 2230):
        d.rectangle(P(px - 120, 1150, px + 120, 1180), fill=white, outline=gold_d, width=L(4))
        for cx in (px - 100, px + 70):
            d.rectangle(P(cx, 980, cx + 30, 1150), fill=white, outline=gold_d, width=L(4))
        d.pieslice(P(px - 130, 880, px + 130, 1060), 180, 360, fill=gold, outline=gold_d, width=L(5))
        d.rectangle(P(px - 135, 965, px + 135, 985), fill=gold, outline=gold_d, width=L(4))
    # wish trees (kalpavriksha): golden trunk, pink and gold blossoms
    for tx in (760, 1880):
        d.rectangle(P(tx - 14, 900, tx + 14, 1250), fill=(196, 150, 70), outline=gold_d, width=L(4))
        for _ in range(16):
            ax, ay, r = tx + rnd.uniform(-150, 150), rnd.uniform(760, 960), rnd.uniform(45, 75)
            c = rnd.choice([(250, 168, 200), (255, 206, 220), (250, 214, 110)])
            d.ellipse(P(ax - r, ay - r, ax + r, ay + r), fill=c, outline=(214, 130, 160), width=L(3))
    # cloud floor
    H = im.height
    for y in range(round(1290 * ps), H):
        u = (y / ps - 1290) / (1920 - 1290)
        d.line([(0, y), (im.width, y)], fill=(int(255 - 30 * u), int(255 - 22 * u), int(255 - 6 * u)))
    _cloud_row(d, P, L, -80, PW + 100, 1300, 60, 120, rnd)
    for _ in range(22):                                                         # soft puffs on the floor
        x, y, r = rnd.uniform(0, PW), rnd.uniform(1420, 1880), rnd.uniform(50, 110)
        d.ellipse(P(x - r * 1.6, y - r * 0.5, x + r * 1.6, y + r * 0.5), fill=(234, 240, 252))
        d.arc(P(x - r * 1.6, y - r * 0.5, x + r * 1.6, y + r * 0.5), 200, 340, fill=(255, 255, 255), width=L(8))


def _nark(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (24, 6, 10)), (560, (78, 14, 16)), (1100, (168, 44, 20)), (1290, (236, 104, 30))])
    # mountains: far and near jagged ridges
    for base_y, lo, hi, col in ((1290, 760, 1060, (66, 20, 24)), (1300, 960, 1200, (42, 12, 16))):
        pts = [(0, 1300)]
        x = -40
        while x < PW + 80:
            pts.append((x, rnd.uniform(lo, hi)))
            x += rnd.uniform(60, 150)
            pts.append((x, rnd.uniform(hi, base_y - 20)))
            x += rnd.uniform(40, 110)
        pts.append((PW + 80, 1300))
        d.polygon([tuple(P(*p)) for p in pts], fill=col)
        d.line([tuple(P(*p)) for p in pts], fill=OUT, width=L(5), joint="curve")
    _glow(im, 1300, 1010, 520, (255, 120, 40), ps, 120)
    d = ImageDraw.Draw(im)
    # Yama's gate
    C, stone, stone_d = 1300, (60, 46, 52), (38, 28, 34)
    for tx in (C - 300, C + 230):                                               # towers with spikes
        d.rectangle(P(tx, 700, tx + 70, 1290), fill=stone_d, outline=OUT, width=L(5))
        for k in range(3):
            sx = tx + k * 24
            d.polygon([tuple(P(sx, 700)), tuple(P(sx + 22, 700)), tuple(P(sx + 11, 630))], fill=stone_d, outline=OUT)
    d.rectangle(P(C - 240, 780, C + 240, 1290), fill=stone, outline=OUT, width=L(6))
    for row in range(7):                                                        # stone blocks
        y = 820 + row * 66
        d.line(P(C - 240, y, C + 240, y), fill=stone_d, width=L(3))
    d.rectangle(P(C - 120, 960, C + 120, 1290), fill=(255, 140, 40))            # glowing doorway
    d.pieslice(P(C - 120, 860, C + 120, 1060), 180, 360, fill=(255, 140, 40))
    d.rectangle(P(C - 80, 1010, C + 80, 1290), fill=(255, 200, 80))
    d.pieslice(P(C - 80, 940, C + 80, 1080), 180, 360, fill=(255, 200, 80))
    sk = (232, 222, 200)                                                        # skull over the door
    d.ellipse(P(C - 54, 790, C + 54, 880), fill=sk, outline=OUT, width=L(4))
    d.rectangle(P(C - 30, 862, C + 30, 896), fill=sk, outline=OUT, width=L(4))
    for ex in (-24, 24):
        d.ellipse(P(C + ex - 15, 820, C + ex + 15, 852), fill=(30, 10, 10))
    d.polygon([tuple(P(C - 7, 870)), tuple(P(C + 7, 870)), tuple(P(C, 858))], fill=(30, 10, 10))
    for tx in (C - 330, C + 330):                                               # torch poles (flames move)
        d.rectangle(P(tx - 8, 930, tx + 8, 1290), fill=(30, 24, 26), outline=OUT, width=L(3))
        d.polygon([tuple(P(tx - 30, 930)), tuple(P(tx + 30, 930)), tuple(P(tx + 14, 960)), tuple(P(tx - 14, 960))],
                  fill=(70, 60, 60), outline=OUT)
    # lava river
    for y in range(round(1290 * ps), round(1395 * ps)):
        u = (y / ps - 1290) / 105
        d.line([(0, y), (im.width, y)], fill=(255, int(190 - 120 * u), int(60 - 40 * u)))
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(6))
    # rock ground
    for y in range(round(1395 * ps), im.height):
        u = (y / ps - 1395) / (1920 - 1395)
        d.line([(0, y), (im.width, y)], fill=(int(86 - 36 * u), int(38 - 16 * u), int(32 - 12 * u)))
    d.line(P(0, 1395, PW, 1395), fill=OUT, width=L(6))
    for pts in _cracks(PW):
        d.line([tuple(P(*p)) for p in pts], fill=(28, 8, 8), width=L(9), joint="curve")
    # cauldrons (kadhai) on stands
    for cx in _CAULDRONS:
        for lx in (cx - 120, cx + 100):
            d.rectangle(P(lx, 1560, lx + 20, 1660), fill=(30, 26, 28), outline=OUT, width=L(3))
        d.chord(P(cx - 190, 1380, cx + 190, 1620), 0, 180, fill=(44, 40, 46), outline=OUT, width=L(6))
        d.ellipse(P(cx - 190, 1462, cx + 190, 1520), fill=(240, 120, 30), outline=OUT, width=L(6))
        d.ellipse(P(cx - 160, 1472, cx + 160, 1510), fill=(255, 176, 60))
    # bones and skulls on the ground
    for _ in range(10):
        x, y = rnd.uniform(0, PW), rnd.uniform(1760, 1890)
        if rnd.random() < 0.5:
            d.ellipse(P(x - 22, y - 20, x + 22, y + 14), fill=sk, outline=OUT, width=L(3))
            for ex in (-8, 8):
                d.ellipse(P(x + ex - 5, y - 8, x + ex + 5, y + 2), fill=(30, 10, 10))
        else:
            d.line(P(x - 40, y, x + 40, y - 10), fill=sk, width=L(10))
            for ex, ey in ((-40, 0), (40, -10)):
                d.ellipse(P(x + ex - 9, y + ey - 9, x + ex + 9, y + ey + 9), fill=sk)


_CAULDRONS = (720, 1880)
_TORCHES = (970, 1630)


@lru_cache(maxsize=2)
def _cracks(PW):
    rnd = random.Random(7)
    out = []
    for _ in range(14):
        x, y = rnd.uniform(0, PW), rnd.uniform(1420, 1900)
        pts = [(x, y)]
        for _ in range(rnd.randint(3, 6)):
            x += rnd.uniform(-70, 90)
            y += rnd.uniform(-25, 25)
            pts.append((x, y))
        out.append(tuple(pts))
    return tuple(out)


# ===================================================================== moving parts
@lru_cache(maxsize=4)
def _items(bid, PW):
    rnd = random.Random(_h(bid, "anim"))
    if bid == "flat_swarg":
        return dict(
            clouds=[(rnd.uniform(0, PW), rnd.uniform(180, 1000), rnd.uniform(0.6, 1.3), rnd.uniform(10, 28)) for _ in range(9)],
            mist=[(rnd.uniform(0, PW), rnd.uniform(1330, 1560), rnd.uniform(0.8, 1.5), rnd.uniform(14, 30)) for _ in range(7)],
            sparkles=[(rnd.uniform(0, PW), rnd.uniform(120, 1250), rnd.uniform(0, 6.28), rnd.uniform(9, 20)) for _ in range(70)],
            petals=[(rnd.uniform(0, PW), rnd.uniform(0, 1), rnd.uniform(60, 120), rnd.uniform(0, 6.28)) for _ in range(40)],
        )
    flames = []
    x = -20
    while x < PW + 40:                                   # flames along the lava river
        flames.append((x, 1292, rnd.uniform(40, 70), rnd.uniform(90, 190), rnd.uniform(0, 6.28)))
        x += rnd.uniform(70, 140)
    for cx in _CAULDRONS:                                 # fire under the cauldrons
        for fx in (-70, -20, 30, 80):
            flames.append((cx + fx, 1660, 46, rnd.uniform(110, 150), rnd.uniform(0, 6.28)))
    for tx in _TORCHES:
        flames.append((tx, 932, 52, 120, rnd.uniform(0, 6.28)))
    return dict(
        flames=flames,
        embers=[(rnd.uniform(0, PW), rnd.uniform(0, 1), rnd.uniform(70, 160), rnd.uniform(0, 6.28)) for _ in range(90)],
        bubbles=[(rnd.uniform(0, PW), rnd.uniform(1305, 1385), rnd.uniform(0, 1), rnd.uniform(0.7, 1.6)) for _ in range(45)],
        pot_bubbles=[(cx + rnd.uniform(-130, 130), rnd.uniform(0, 1), rnd.uniform(1.0, 1.8)) for cx in _CAULDRONS for _ in range(8)],
    )


@lru_cache(maxsize=48)
def _cloud_sprite(sq):
    s = sq / 100
    W, H = round(420 * s) + 4, round(190 * s) + 4
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = max(1, round(4 * s))
    for cx, cy, r in ((110, 120, 70), (200, 90, 90), (300, 115, 72), (160, 135, 55), (250, 135, 60)):
        d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=(255, 255, 255, 240),
                  outline=(206, 216, 240, 255), width=w)
    for cx, cy, r in ((110, 120, 70), (200, 90, 90), (300, 115, 72)):
        r -= 5
        d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=(255, 255, 255, 255))
    d.rectangle([60 * s, 135 * s, 360 * s, 182 * s], fill=(255, 255, 255, 255))
    return im


def _flame(d, cx, cy, w, h, t, ph, sc):
    flick = 0.8 + 0.22 * math.sin(t * 11 + ph) + 0.1 * math.sin(t * 23 + ph * 1.7)
    sway = 0.28 * w * math.sin(t * 6.5 + ph)
    for k, col in ((1.0, (226, 56, 22, 230)), (0.7, (255, 138, 30, 240)), (0.42, (255, 226, 96, 250))):
        ww, hh = w * k, h * k * flick
        pts = []
        for i in range(17):
            u = i / 16                                  # 0 at the left of the base, 1 at the right
            a = math.pi * u
            bx = cx - math.cos(a) * ww / 2
            rise = math.sin(a)
            pts.append((bx + sway * rise ** 2, cy - (hh * rise ** 0.6 if 0.15 < u < 0.85 else hh * rise * 0.5)))
        pts.insert(9, (cx + sway, cy - hh))
        pts.append((cx + ww * 0.35, cy + ww * 0.2))
        pts.append((cx - ww * 0.35, cy + ww * 0.2))
        d.polygon([(x * sc[0] + sc[1], y * sc[0] + sc[2]) for x, y in pts], fill=col)


def animate(im: Image.Image, bid: str, t: float, x0: float, y0: float, z: float, k: float, PW: int, blur: bool):
    """Draw this frame's moving parts onto im (the background already cropped to the frame)."""
    vw = 1080 / z
    s = z * k
    tx = (s, -x0 * s, -y0 * s)            # world -> pixels: x * s + tx[1]

    def px(X, Y):
        return X * s + tx[1], Y * s + tx[2]

    def visible(X, margin=200):
        return x0 - margin < X < x0 + vw + margin

    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    it = _items(bid, PW)
    if bid == "flat_swarg":
        # slow turning sun rays
        cx, cy = px(1300, 560)
        for i in range(16):
            a = t * 0.12 + i * math.pi / 8
            r0, r1, wa = 160 * s, 1500 * s, 0.07
            d.polygon([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                       (cx + r1 * math.cos(a - wa), cy + r1 * math.sin(a - wa)),
                       (cx + r1 * math.cos(a + wa), cy + r1 * math.sin(a + wa))], fill=(255, 246, 200, 34))
        # drifting clouds (sky) and mist on the cloud floor
        for group in ("clouds", "mist"):
            for X, Y, sc, spd in it[group]:
                X = (X + t * spd) % (PW + 600) - 300
                if not visible(X, 500):
                    continue
                spr = _cloud_sprite(round(sc * s * 100))
                p = px(X - 210 * sc, Y - 95 * sc)
                ov.paste(spr, (round(p[0]), round(p[1])), spr)
        # twinkling sparkles
        for X, Y, ph, size in it["sparkles"]:
            if not visible(X):
                continue
            a = max(0.0, math.sin(t * 2.6 + ph))
            if a < 0.15:
                continue
            x, y = px(X, Y)
            r, q = size * s * a, size * s * a * 0.22
            col = (255, 250, 210, int(230 * a))
            d.polygon([(x, y - r), (x + q, y - q), (x + r, y), (x + q, y + q), (x, y + r), (x - q, y + q), (x - r, y), (x - q, y - q)], fill=col)
        # falling flower petals
        for X, ph, spd, sw in it["petals"]:
            Y = ((ph * 1700 + t * spd) % 1700) + 100
            X = X + 50 * math.sin(t * 1.4 + sw)
            if not visible(X):
                continue
            x, y = px(X, Y)
            r = 9 * s
            ang = t * 3 + sw
            dx, dy = math.cos(ang) * r, math.sin(ang) * r * 0.5
            d.ellipse([x - abs(dx) - r * 0.4, y - abs(dy) - r * 0.4, x + abs(dx) + r * 0.4, y + abs(dy) + r * 0.4],
                      fill=(250, 150, 190, 230))
        # doves
        for j in range(3):
            X = x0 - 100 + ((t * 55 + j * 90) % (vw + 260))
            Y = 300 + j * 40 + 14 * math.sin(t * 1.5 + j)
            x, y = px(X, Y)
            flap, ws = math.sin(t * 8 + j), 26 * s
            d.ellipse([x - ws * 0.45, y - ws * 0.2, x + ws * 0.45, y + ws * 0.2], fill=(255, 255, 255, 255))
            d.line([(x - ws, y - ws * 0.6 * flap), (x, y), (x + ws, y - ws * 0.6 * flap)], fill=(255, 255, 255, 255),
                   width=max(2, round(7 * s)))
    else:
        pulse = 0.55 + 0.45 * math.sin(t * 3.2)
        for pts in _cracks(PW):                                # glowing cracks in the rock
            if not any(visible(p[0]) for p in pts):
                continue
            q = [px(*p) for p in pts]
            d.line(q, fill=(255, 110, 30, int(110 + 120 * pulse)), width=max(1, round(5 * s)), joint="curve")
            d.line(q, fill=(255, 220, 100, int(80 + 150 * pulse)), width=max(1, round(2 * s)))
        for X, Y, ph, size in it["bubbles"]:                   # lava bubbles that grow and pop
            if not visible(X):
                continue
            u = (t * 0.6 * size + ph) % 1.0
            x, y = px(X, Y)
            r = (6 + 22 * u) * s * size * 0.7
            a = int(255 * (1 - u ** 3))
            d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(255, 210, 90, a), outline=(200, 60, 20, a),
                      width=max(1, round(3 * s)))
        for X, ph, spd in it["pot_bubbles"]:                   # boiling cauldrons
            if not visible(X):
                continue
            u = (t * 0.9 * spd + ph) % 1.0
            x, y = px(X, 1492)
            r = (8 + 18 * u) * s
            d.ellipse([x - r, y - r * 1.4, x + r, y + r * 0.4], fill=(255, 196, 80, int(255 * (1 - u))),
                      outline=(170, 60, 20, int(255 * (1 - u))), width=max(1, round(3 * s)))
        for cx in _CAULDRONS:                                  # steam
            if not visible(cx, 400):
                continue
            for j in range(4):
                u = (t * 0.35 + j / 4) % 1.0
                x, y = px(cx - 60 + j * 40 + 30 * math.sin(t + j), 1450 - 380 * u)
                r = (30 + 60 * u) * s
                d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 200, 200, int(90 * (1 - u))))
        for X, Y, w, h, ph in it["flames"]:                    # flickering fire
            if visible(X):
                _flame(d, X, Y, w, h, t, ph, (s, tx[1], tx[2]))
        for X, ph, spd, sw in it["embers"]:                    # embers rising
            u = (ph + t * spd / 1300) % 1.0
            Xe = X + 40 * math.sin(t * 2 + sw)
            if not visible(Xe):
                continue
            x, y = px(Xe, 1500 - 1300 * u)
            r = (3 + 4 * (1 - u)) * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, int(180 - 80 * u), 50, int(255 * (1 - u))))
        for j in range(3):                                     # bats
            X = x0 + vw + 100 - ((t * 70 + j * 120) % (vw + 260))
            Y = 380 + j * 60 + 30 * math.sin(t * 2 + j)
            x, y = px(X, Y)
            f, ws = math.sin(t * 13 + j), 30 * s
            col = (18, 8, 12, 255)
            d.polygon([(x, y), (x - ws, y - ws * 0.6 * f), (x - ws * 0.6, y + ws * 0.1), (x - ws * 0.3, y - ws * 0.1)], fill=col)
            d.polygon([(x, y), (x + ws, y - ws * 0.6 * f), (x + ws * 0.6, y + ws * 0.1), (x + ws * 0.3, y - ws * 0.1)], fill=col)
            d.ellipse([x - ws * 0.18, y - ws * 0.2, x + ws * 0.18, y + ws * 0.2], fill=col)
    if blur:
        ov = ov.filter(ImageFilter.GaussianBlur(max(1, 2.5 * s)))
    im.paste(ov, (0, 0), ov)
