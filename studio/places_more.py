"""More everyday flat-cartoon places: chai ki tapri, sabzi mandi, airport and bus stop.

Same idea as places.py: draw() paints the wide picture once (2600 x 1920 units); animate() adds the moving parts.
Chai tapri:  steam and bubbles, the chaiwala pouring chai from high up, swinging chips packets, a diya,
             a sleeping dog breathing and wagging, leaves drifting down, birds.
Sabzi mandi: shoppers walking behind the thelas, the hanging scale swinging, birds.
Airport:     a plane taking off past the big windows, the departure board blinking "BOARDING".
Bus stop:    a bus driving past now and then, birds.
Signs are in English letters (the picture library cannot join Hindi letters correctly).
"""
from __future__ import annotations

import math
import random

from PIL import ImageFont

from .realms import OUT, _sky

MORE = ("flat_chai_tapri", "flat_sabzi_mandi", "flat_airport", "flat_bus_stop", "flat_white", "flat_doodle")


def _mix(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _font(px: int):
    from .config import find_devanagari_font
    fp = find_devanagari_font()
    try:
        return ImageFont.truetype(str(fp), max(8, px)) if fp else ImageFont.load_default(max(8, px))
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _text(d, P, ps, x, y, s, size, fill, stroke=None):
    """Text centred at (x, y) in picture units."""
    f = _font(round(size * ps))
    w = d.textlength(s, font=f)
    cx, cy = P(x, y)
    d.text((cx - w / 2, cy - size * ps * 0.6), s, font=f, fill=fill,
           stroke_width=max(1, round(size * ps * 0.08)) if stroke else 0, stroke_fill=stroke)


def _ground(d, im, ps, y0, top, bottom):
    for y in range(round(y0 * ps), im.height):
        u = (y / ps - y0) / (1920 - y0)
        d.line([(0, y), (im.width, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bottom)))


def _buildings(d, P, L, PW, rnd, y_top=560, y_bot=1000):
    for x in range(0, PW, 430):
        h = rnd.choice((0, 60, 120))
        col = rnd.choice([(224, 170, 130), (200, 160, 150), (230, 206, 150), (180, 196, 170)])
        d.rectangle(P(x, y_top + h, x + 410, y_bot), fill=col, outline=OUT, width=L(5))
        for wy in range(y_top + h + 50, y_bot - 60, 120):
            for wx in range(x + 40, x + 380, 110):
                d.rectangle(P(wx, wy, wx + 60, wy + 70), fill=_mix(col, 0.7), outline=OUT, width=L(3))


def _veg_pile(d, P, L, x, y, kind, w=300, rows=3):
    """A heap of vegetables / fruit on a cart, centred at x, bottom at y."""
    look = {"tomato": ((214, 52, 44), 22, "round"), "onion": ((176, 80, 120), 22, "round"),
            "potato": ((176, 130, 80), 22, "oval"), "carrot": ((240, 130, 40), 0, "carrot"),
            "brinjal": ((110, 60, 140), 0, "brinjal"), "cabbage": ((120, 190, 90), 30, "round"),
            "banana": ((246, 206, 60), 0, "banana"), "orange": ((246, 150, 40), 22, "round"),
            "cucumber": ((60, 140, 60), 0, "cucumber"), "lemon": ((246, 226, 70), 16, "round"),
            "cauliflower": ((246, 242, 226), 28, "round"),
            "apple": ((200, 40, 50), 22, "round"), "chilli": ((60, 160, 60), 0, "chilli")}[kind]
    col, r, shape = look
    for row in range(rows):
        n = max(1, int(w / 48) - row)
        for k in range(n):
            cx = x - (n - 1) * 24 + k * 48
            cy = y - 22 - row * 34
            c = _mix(col, 0.92 + 0.08 * ((k + row) % 2))
            if shape == "round":
                d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=c, outline=OUT, width=L(2.5))
                if kind == "tomato":
                    d.ellipse(P(cx - 6, cy - r - 2, cx + 6, cy - r + 8), fill=(70, 140, 60))
            elif shape == "oval":
                d.ellipse(P(cx - 26, cy - 18, cx + 26, cy + 18), fill=c, outline=OUT, width=L(2.5))
            elif shape == "carrot":
                d.polygon([tuple(P(cx - 30, cy - 10)), tuple(P(cx + 34, cy)), tuple(P(cx - 30, cy + 10))], fill=c,
                          outline=OUT)
                d.line(P(cx - 30, cy, cx - 46, cy - 12), fill=(70, 150, 60), width=L(5))
            elif shape == "brinjal":
                d.ellipse(P(cx - 30, cy - 16, cx + 26, cy + 16), fill=c, outline=OUT, width=L(2.5))
                d.ellipse(P(cx + 16, cy - 10, cx + 34, cy + 10), fill=(80, 140, 60))
            elif shape == "banana":
                d.arc(P(cx - 34, cy - 30, cx + 34, cy + 20), 20, 160, fill=c, width=L(14))
            elif shape == "cucumber":
                d.ellipse(P(cx - 34, cy - 12, cx + 34, cy + 12), fill=c, outline=OUT, width=L(2.5))
                d.line(P(cx - 24, cy - 3, cx + 24, cy - 3), fill=(130, 196, 110), width=L(3))
            elif shape == "chilli":
                d.arc(P(cx - 30, cy - 20, cx + 30, cy + 14), 10, 170, fill=c, width=L(8))


def _thela(d, P, L, x, kinds, rnd):
    """A vegetable hand-cart (thela) with two big wheels and heaps on top."""
    d.rectangle(P(x, 1160, x + 520, 1200), fill=(150, 100, 60), outline=OUT, width=L(5))          # platform
    d.line(P(x + 520, 1180, x + 640, 1150), fill=(120, 80, 50), width=L(10))                      # handles
    for wx in (x + 120, x + 400):
        d.ellipse(P(wx - 70, 1180, wx + 70, 1320), fill=None, outline=(50, 44, 40), width=L(12))
        for k in range(6):
            a = k * math.pi / 6
            d.line(P(wx - 60 * math.cos(a), 1250 - 60 * math.sin(a), wx + 60 * math.cos(a), 1250 + 60 * math.sin(a)),
                   fill=(110, 90, 70), width=L(3))
    for i, kind in enumerate(kinds):
        _veg_pile(d, P, L, x + 90 + i * 170, 1160, kind, 170, 3)
    d.rectangle(P(x + 200, 1040, x + 320, 1090), fill=(250, 246, 230), outline=OUT, width=L(3))    # price tag
    d.line(P(x + 260, 1090, x + 260, 1120), fill=OUT, width=L(3))


def _chai_tapri(im, d, P, L, PW, ps, rnd):
    """A busy, colourful chai ki tapri under a big neem tree, in front of a street of painted houses."""
    from PIL import Image, ImageDraw
    _sky(d, im.width, ps, [(0, (64, 156, 238)), (520, (130, 200, 246)), (1000, (255, 214, 170))])
    d.ellipse(P(2140, 170, 2330, 360), fill=(255, 236, 140))                                       # sun
    for cx, cy, w in ((420, 260, 160), (1500, 200, 200), (2450, 330, 130)):                        # clouds
        for dx, r in ((-w * 0.6, w * 0.45), (0, w * 0.6), (w * 0.6, w * 0.42)):
            d.ellipse(P(cx + dx - r, cy - r * 0.7, cx + dx + r, cy + r * 0.7), fill=(255, 255, 255))
    # a street of painted houses with balconies and water tanks
    houses = [(214, 74, 120), (40, 170, 170), (250, 196, 50), (130, 190, 70), (240, 120, 60), (110, 120, 220)]
    for i, x in enumerate(range(-60, PW, 330)):
        col = houses[i % len(houses)]
        top = 520 + (i * 53 % 4) * 45
        d.rectangle(P(x, top, x + 320, 1180), fill=col, outline=OUT, width=L(5))
        d.rectangle(P(x - 10, top - 18, x + 330, top), fill=_mix(col, 0.75), outline=OUT, width=L(4))
        for wy in range(top + 50, 1100, 170):
            for wx in (x + 40, x + 190):
                d.rectangle(P(wx, wy, wx + 90, wy + 100), fill=(255, 240, 200), outline=OUT, width=L(4))
                d.line(P(wx + 45, wy, wx + 45, wy + 100), fill=OUT, width=L(3))
                d.rectangle(P(wx - 8, wy + 100, wx + 98, wy + 112), fill=_mix(col, 0.7), outline=OUT, width=L(3))
        if i % 2 == 0:                                                                                  # water tank
            d.rounded_rectangle(P(x + 200, top - 90, x + 290, top - 18), radius=L(14), fill=(40, 40, 50),
                                outline=OUT, width=L(4))
    d.line(P(0, 640, PW, 600), fill=(40, 40, 46), width=L(3))                                         # cable wires
    d.line(P(0, 690, PW, 660), fill=(40, 40, 46), width=L(3))
    _ground(d, im, ps, 1180, (246, 196, 130), (226, 162, 98))                                         # warm dusty ground
    d.line(P(0, 1180, PW, 1180), fill=OUT, width=L(5))
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))                                                    # leaf shadows
    o = ImageDraw.Draw(ov)
    for _ in range(70):
        x, y = rnd.uniform(0, 1100), rnd.uniform(1220, 1900)
        r = rnd.uniform(20, 60)
        o.ellipse(P(x - r * 1.6, y - r * 0.5, x + r * 1.6, y + r * 0.5), fill=(120, 70, 30, 60))
    im.paste(ov, (0, 0), ov)
    # the big neem tree on the left
    d.polygon([tuple(P(150, 1300)), tuple(P(300, 1300)), tuple(P(270, 700)), tuple(P(330, 520)), tuple(P(250, 560)),
               tuple(P(200, 700))], fill=(130, 84, 50), outline=OUT)
    d.line(P(260, 760, 470, 600), fill=(130, 84, 50), width=L(36))
    for cx, cy, r, col in ((120, 470, 230, (40, 140, 60)), (380, 420, 220, (60, 170, 70)), (230, 300, 200, (80, 190, 80)),
                           (520, 560, 170, (50, 156, 64)), (40, 650, 150, (60, 170, 70))):
        d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=col, outline=OUT, width=L(5))
    for _ in range(40):
        x, y = rnd.uniform(-60, 680), rnd.uniform(200, 760)
        d.ellipse(P(x - 18, y - 9, x + 18, y + 9), fill=(150, 220, 110))
    # ---------------------------------------------------------------- the tapri
    x0, x1 = 820, 1880
    d.rectangle(P(x0, 720, x1, 1300), fill=(26, 150, 166), outline=OUT, width=L(7))                  # turquoise stall
    for x in range(x0 + 40, x1, 60):
        d.line(P(x, 720, x, 1300), fill=(20, 126, 140), width=L(4))
    d.rectangle(P(x0 + 40, 760, x1 - 40, 1060), fill=(20, 90, 110), outline=OUT, width=L(5))          # inside, darker
    for y in (850, 960):                                                                              # shelves + jars
        d.rectangle(P(x0 + 50, y + 70, x1 - 50, y + 84), fill=(176, 116, 64), outline=OUT, width=L(3))
        for k, xx in enumerate(range(x0 + 80, x1 - 120, 92)):
            lid = [(240, 70, 60), (250, 200, 40), (70, 180, 90), (60, 140, 230), (220, 90, 200)][k % 5]
            fill = [(236, 180, 90), (250, 222, 140), (210, 140, 70), (246, 200, 110)][k % 4]
            d.rounded_rectangle(P(xx, y, xx + 70, y + 70), radius=L(12), fill=(214, 236, 246), outline=OUT, width=L(3))
            d.rectangle(P(xx + 7, y + 24, xx + 63, y + 64), fill=fill)
            d.rounded_rectangle(P(xx + 8, y - 12, xx + 62, y + 4), radius=L(4), fill=lid, outline=OUT, width=L(2))
    # god's picture with a marigold garland (a diya flickers in the animation)
    gx = x1 - 120
    d.rectangle(P(gx - 50, 770, gx + 50, 840), fill=(250, 220, 120), outline=OUT, width=L(4))
    d.ellipse(P(gx - 26, 778, gx + 26, 832), fill=(240, 120, 40))
    for k in range(9):
        a = math.pi * k / 8
        d.ellipse(P(gx - 50 + 100 * k / 8 - 9, 840 + 18 * math.sin(a) - 9, gx - 50 + 100 * k / 8 + 9, 840 + 18 * math.sin(a) + 9),
                  fill=(255, 150, 20) if k % 2 else (255, 200, 30))
    # the chaiwala behind the counter (his pouring arm moves: animate)
    cx = 1140
    d.rounded_rectangle(P(cx - 95, 900, cx + 95, 1100), radius=L(50), fill=(250, 250, 244), outline=OUT, width=L(5))
    d.ellipse(P(cx - 62, 760, cx + 62, 890), fill=(232, 182, 138), outline=OUT, width=L(5))           # head
    d.pieslice(P(cx - 66, 740, cx + 66, 840), 180, 360, fill=(40, 30, 28), outline=OUT, width=L(4))   # hair
    d.ellipse(P(cx - 30, 806, cx - 14, 822), fill=(30, 26, 26))
    d.ellipse(P(cx + 14, 806, cx + 30, 822), fill=(30, 26, 26))
    d.polygon([tuple(P(cx - 36, 846)), tuple(P(cx, 834)), tuple(P(cx + 36, 846)), tuple(P(cx, 852))], fill=(40, 30, 28))
    d.arc(P(cx - 22, 846, cx + 22, 872), 20, 160, fill=OUT, width=L(4))
    d.rectangle(P(cx - 110, 930, cx - 80, 960), fill=(240, 70, 60))                                   # red gamchha
    d.line(P(cx - 95, 905, cx + 70, 1000), fill=(240, 70, 60), width=L(14))
    # counter
    d.rectangle(P(x0 - 40, 1080, x1 + 40, 1110), fill=(186, 120, 62), outline=OUT, width=L(5))
    d.rectangle(P(x0, 1110, x1, 1300), fill=(240, 120, 40), outline=OUT, width=L(6))                 # orange front
    for x in range(x0, x1, 106):
        d.rectangle(P(x + 8, 1124, x + 98, 1286), fill=(250, 150, 60), outline=OUT, width=L(3))
    _text(d, P, ps, (x0 + x1) / 2, 1200, "MASALA CHAI  Rs 10", 54, (255, 255, 255), (150, 50, 20))
    d.rectangle(P(x0 + 280, 1040, x0 + 520, 1080), fill=(50, 50, 56), outline=OUT, width=L(4))       # stove
    d.polygon([tuple(P(x0 + 300, 960)), tuple(P(x0 + 500, 960)), tuple(P(x0 + 488, 1040)), tuple(P(x0 + 312, 1040))],
              fill=(210, 214, 224), outline=OUT)                                                      # chai pateela
    d.ellipse(P(x0 + 300, 942, x0 + 500, 978), fill=(176, 104, 50), outline=OUT, width=L(4))
    tx = x0 + 600                                                                                     # tray of glasses
    d.rectangle(P(tx, 1068, tx + 330, 1080), fill=(200, 204, 214), outline=OUT, width=L(2))
    for k in range(7):
        gx_ = tx + 25 + k * 46
        d.polygon([tuple(P(gx_ - 16, 1010)), tuple(P(gx_ + 16, 1010)), tuple(P(gx_ + 12, 1068)), tuple(P(gx_ - 12, 1068))],
                  fill=(236, 246, 250), outline=OUT)
        d.polygon([tuple(P(gx_ - 14, 1026)), tuple(P(gx_ + 14, 1026)), tuple(P(gx_ + 11, 1066)), tuple(P(gx_ - 11, 1066))],
                  fill=(186, 112, 52))
    px_ = x1 - 200                                                                                    # samosa plate
    d.ellipse(P(px_ - 110, 1052, px_ + 110, 1082), fill=(240, 242, 246), outline=OUT, width=L(3))
    for dx, dy in ((-55, 0), (0, -8), (55, 0), (-28, -38), (28, -38)):
        sx, sy = px_ + dx, 1058 + dy
        d.polygon([tuple(P(sx - 34, sy)), tuple(P(sx + 34, sy)), tuple(P(sx, sy - 50))], fill=(236, 176, 80), outline=OUT)
    for k in range(5):                                                                                # kulhads
        kx = x0 + 60 + k * 44
        d.polygon([tuple(P(kx - 18, 1030)), tuple(P(kx + 18, 1030)), tuple(P(kx + 12, 1078)), tuple(P(kx - 12, 1078))],
                  fill=(190, 96, 58), outline=OUT)
    # striped awning with a scalloped edge, and the signboard
    stripes = [(240, 60, 60), (255, 250, 240)]
    d.polygon([tuple(P(x0 - 120, 640)), tuple(P(x1 + 120, 640)), tuple(P(x1 + 80, 740)), tuple(P(x0 - 80, 740))],
              fill=stripes[0], outline=OUT)
    for k in range(14):
        xa = x0 - 120 + k * (x1 - x0 + 240) / 14
        xb = xa + (x1 - x0 + 240) / 28
        d.polygon([tuple(P(xa + 3, 642)), tuple(P(xb, 642)), tuple(P(xb - 3, 738)), tuple(P(xa + 6, 738))], fill=stripes[1])
    for k in range(14):
        xa = x0 - 80 + k * (x1 - x0 + 160) / 14
        d.pieslice(P(xa, 712, xa + (x1 - x0 + 160) / 14, 776), 0, 180, fill=stripes[k % 2], outline=OUT, width=L(3))
    d.line(P(x0 - 120, 640, x1 + 120, 640), fill=OUT, width=L(6))
    d.rounded_rectangle(P(x0 + 90, 470, x1 - 90, 630), radius=L(22), fill=(255, 214, 40), outline=OUT, width=L(7))
    _text(d, P, ps, (x0 + x1) / 2, 530, "CHAI  KI  TAPRI", 76, (220, 40, 40), (255, 250, 230))
    _text(d, P, ps, (x0 + x1) / 2, 598, "CHAI - SAMOSA - BUN MASKA", 32, (90, 40, 20))
    for x in range(x0 - 70, x1 + 80, 9):                                                              # string for packets
        d.ellipse(P(x - 2, 778, x + 2, 782), fill=(60, 50, 40))
    for k, (bx, by) in enumerate(((x0 + 60, 800), (x0 + 90, 806), (x0 + 120, 800))):                  # banana bunch
        d.arc(P(bx - 30, by - 10, bx + 30, by + 70), 200, 340, fill=(250, 210, 40), width=L(16))
    # bench on the left, red plastic stools on the right
    bx = 360
    d.rectangle(P(bx, 1330, bx + 420, 1368), fill=(176, 110, 56), outline=OUT, width=L(5))
    for lx in (bx + 26, bx + 370):
        d.rectangle(P(lx, 1368, lx + 26, 1450), fill=(140, 86, 44), outline=OUT, width=L(3))
    for sx in (2020, 2210):
        d.polygon([tuple(P(sx - 60, 1300)), tuple(P(sx + 60, 1300)), tuple(P(sx + 46, 1420)), tuple(P(sx - 46, 1420))],
                  fill=(226, 40, 40), outline=OUT)
        d.ellipse(P(sx - 66, 1286, sx + 66, 1316), fill=(246, 70, 60), outline=OUT, width=L(4))
    d.rectangle(P(2380, 1150, 2520, 1300), fill=(60, 150, 220), outline=OUT, width=L(5))              # water drum
    d.ellipse(P(2380, 1130, 2520, 1170), fill=(100, 180, 236), outline=OUT, width=L(4))


def _tapri_animate(d, t, px, s, visible, x0, vw, PW, birds):
    """Steam, the chaiwala pouring chai from high up, swinging packets, a flickering diya, a sleeping dog, birds."""
    import random as _r
    if visible(1050):
        for j in range(7):                                                               # steam from the pateela
            u = (t * 0.5 + j / 7) % 1
            x, y = px(1020 + 40 * math.sin(t * 1.4 + j) + 25 * u, 940 - 360 * u)
            r = (18 + 46 * u) * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(150 * (1 - u))))
        for j in range(4):                                                               # bubbles on the boil
            u = (t * 3 + j * 0.27) % 1
            x, y = px(1080 + j * 40, 958 - 8 * u)
            r = (4 + 6 * u) * s
            d.ellipse([x - r, y - r, x + r, y + r], outline=(240, 214, 170, int(255 * (1 - u))), width=max(1, round(2 * s)))
    if visible(1140):                                                                    # pouring chai from high up
        ph = (t % 3.2) / 3.2
        lift = math.sin(math.pi * min(1.0, ph / 0.8)) if ph < 0.8 else 0.0
        hx, hy = 1240, 960 - 150 * lift                                                  # the hand with the kettle
        sx_, sy_ = px(1160, 930)
        ex, ey = px(hx, hy)
        d.line([(sx_, sy_), (ex, ey)], fill=(232, 182, 138, 255), width=max(2, round(26 * s)))
        d.ellipse([ex - 18 * s, ey - 18 * s, ex + 18 * s, ey + 18 * s], fill=(232, 182, 138, 255))
        k = s
        kx, ky = ex + 10 * k, ey - 10 * k
        d.polygon([(kx - 34 * k, ky - 40 * k), (kx + 34 * k, ky - 40 * k), (kx + 40 * k, ky + 20 * k), (kx - 40 * k, ky + 20 * k)],
                  fill=(206, 210, 222, 255), outline=(36, 31, 32, 255))
        d.line([(kx + 36 * k, ky), (kx + 70 * k, ky - 22 * k)], fill=(170, 174, 186, 255), width=max(2, round(9 * k)))
        if lift > 0.15:                                                                  # the stream of chai
            gx_, gy_ = px(1290, 1020)
            pts = []
            for i in range(9):
                v = i / 8
                pts.append((kx + 70 * k + (gx_ - kx - 70 * k) * v, ky - 22 * k + (gy_ - ky + 22 * k) * v * v + 4 * math.sin(t * 30 + i) * k))
            d.line(pts, fill=(186, 112, 52, 240), width=max(2, round(7 * k)))
        gx_, gy_ = px(1290, 1050)                                                        # the glass under it
        d.polygon([(gx_ - 16 * s, gy_ - 30 * s), (gx_ + 16 * s, gy_ - 30 * s), (gx_ + 12 * s, gy_ + 28 * s),
                   (gx_ - 12 * s, gy_ + 28 * s)], fill=(236, 246, 250, 255), outline=(36, 31, 32, 255))
        lvl = min(1.0, (t % 3.2) / 2.6)
        d.polygon([(gx_ - 14 * s + 2 * s * (1 - lvl), gy_ + 26 * s - 52 * s * lvl), (gx_ + 14 * s - 2 * s * (1 - lvl), gy_ + 26 * s - 52 * s * lvl),
                   (gx_ + 11 * s, gy_ + 26 * s), (gx_ - 11 * s, gy_ + 26 * s)], fill=(186, 112, 52, 255))
    cols = [(240, 70, 60), (250, 200, 40), (40, 160, 230), (120, 200, 80), (230, 110, 210), (250, 130, 40)]
    for k, X in enumerate(range(760, 1960, 64)):                                         # chips packets swinging
        if not visible(X) or 1030 < X < 1350:                                            # (not in front of the chaiwala)
            continue
        a = 0.14 * math.sin(t * 2.4 + k * 0.8)
        x, y = px(X, 782)
        w, h = 24 * s, 76 * s
        pts = [(x - w, y), (x + w, y), (x + w + h * math.sin(a), y + h), (x - w + h * math.sin(a), y + h)]
        d.polygon(pts, fill=cols[k % 6] + (255,), outline=(36, 31, 32, 255))
        d.line([(x - w * 0.6 + h * 0.5 * math.sin(a), y + h * 0.5), (x + w * 0.6 + h * 0.5 * math.sin(a), y + h * 0.5)],
               fill=(255, 255, 255, 220), width=max(1, round(4 * s)))
    if visible(1760):                                                                    # diya flame under the picture
        x, y = px(1760, 862)
        f = 1 + 0.25 * math.sin(t * 17) + 0.15 * math.sin(t * 29)
        d.ellipse([x - 26 * s * f, y - 30 * s * f, x + 26 * s * f, y + 10 * s], fill=(255, 200, 80, 80))
        d.polygon([(x - 7 * s, y), (x + 7 * s, y), (x, y - 26 * s * f)], fill=(255, 170, 40, 255))
    if visible(2250):                                                                    # a dog sleeping, breathing, tail wagging
        x, y = px(2250, 1520)
        b = 1 + 0.04 * math.sin(t * 2.2)
        d.ellipse([x - 110 * s, y - 50 * s * b, x + 90 * s, y + 30 * s], fill=(196, 140, 84, 255), outline=(36, 31, 32, 255),
                  width=max(1, round(4 * s)))
        d.ellipse([x + 60 * s, y - 40 * s, x + 140 * s, y + 20 * s], fill=(196, 140, 84, 255), outline=(36, 31, 32, 255),
                  width=max(1, round(4 * s)))
        d.polygon([(x + 120 * s, y - 34 * s), (x + 150 * s, y - 20 * s), (x + 118 * s, y - 6 * s)], fill=(150, 100, 60, 255))
        d.line([(x + 100 * s, y - 12 * s), (x + 112 * s, y - 12 * s)], fill=(36, 31, 32, 255), width=max(1, round(3 * s)))
        wag = 0.5 * math.sin(t * 5)
        d.line([(x - 104 * s, y - 10 * s), (x - 150 * s, y - 40 * s - 30 * s * wag)], fill=(196, 140, 84, 255),
               width=max(2, round(12 * s)))
    rnd = _r.Random(int(t // 6))                                                         # leaves drifting down
    for j in range(3):
        u = ((t + j * 2.1) % 6) / 6
        X = 150 + j * 230 + 60 * math.sin(t * 1.3 + j) + 200 * u
        if not visible(X):
            continue
        x, y = px(X, 500 + 1100 * u)
        a = t * 3 + j
        d.ellipse([x - 14 * s, y - 6 * s, x + 14 * s, y + 6 * s], fill=(110, 190, 80, 230))
    birds(d, x0, vw, t, px, s, 3, 300)


def _sabzi_mandi(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (120, 184, 236)), (1000, (220, 236, 246))])
    _buildings(d, P, L, PW, rnd, 520, 980)
    _ground(d, im, ps, 1290, (200, 186, 160), (170, 152, 124))
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
    tarps = [(40, 140, 220), (240, 140, 40), (60, 170, 120), (220, 70, 80)]
    for i, x in enumerate(range(0, PW, 650)):                                                     # tarpaulin shades
        col = tarps[i % 4]
        d.polygon([tuple(P(x - 20, 820)), tuple(P(x + 630, 800)), tuple(P(x + 610, 900)), tuple(P(x, 920))],
                  fill=col, outline=OUT)
        for k in range(4):
            d.line(P(x + 40 + k * 150, 818, x + 30 + k * 150, 912), fill=_mix(col, 0.8), width=L(4))
        for px_ in (x + 10, x + 600):
            d.rectangle(P(px_, 900, px_ + 14, 1290), fill=(110, 80, 50))
    kinds = [("tomato", "onion", "potato"), ("carrot", "brinjal", "cabbage"), ("banana", "orange", "apple"),
             ("cucumber", "lemon", "cauliflower")]
    for i, x in enumerate((60, 700, 1340, 1980)):
        _thela(d, P, L, x, kinds[i], rnd)
    for x, col in ((620, (180, 150, 100)), (1270, (176, 140, 96)), (1920, (186, 156, 110))):      # gunny sacks
        d.rounded_rectangle(P(x - 70, 1180, x + 50, 1300), radius=L(30), fill=col, outline=OUT, width=L(4))
        d.ellipse(P(x - 60, 1160, x + 40, 1200), fill=(176, 130, 80), outline=OUT, width=L(3))
    _text(d, P, ps, 1300, 760, "SABZI  MANDI", 64, (255, 255, 255), (60, 40, 30))


def _airport(im, d, P, L, PW, ps, rnd):
    d.rectangle(P(0, 0, PW, 1920), fill=(228, 232, 238))                                          # hall wall
    d.rectangle(P(0, 0, PW, 120), fill=(200, 206, 216))
    for x in range(0, PW, 200):                                                                    # ceiling lights
        d.rectangle(P(x + 60, 120, x + 140, 134), fill=(255, 250, 220))
    _sky(d, im.width, ps, [(0, (228, 232, 238)), (300, (228, 232, 238)), (301, (150, 200, 240)), (900, (210, 232, 248)),
                          (901, (228, 232, 238))])                                                # (sky only in the windows)
    d.rectangle(P(0, 0, PW, 300), fill=(228, 232, 238))
    d.rectangle(P(0, 900, PW, 1300), fill=(228, 232, 238))
    d.rectangle(P(0, 760, PW, 900), fill=(120, 130, 120))                                          # runway seen outside
    d.rectangle(P(0, 820, PW, 836), fill=(240, 240, 240))
    for x in range(0, PW, 140):
        d.rectangle(P(x, 860, x + 70, 868), fill=(250, 250, 250))
    for x, y in ((300, 700), (1900, 690)):                                                        # parked planes
        d.ellipse(P(x - 220, y - 30, x + 220, y + 30), fill=(250, 250, 252), outline=OUT, width=L(3))
        d.polygon([tuple(P(x - 40, y)), tuple(P(x + 60, y)), tuple(P(x - 10, y + 70))], fill=(220, 226, 236), outline=OUT)
        d.polygon([tuple(P(x - 200, y - 20)), tuple(P(x - 170, y - 20)), tuple(P(x - 215, y - 100))], fill=(40, 90, 180), outline=OUT)
    for x in range(0, PW + 1, 260):                                                               # window frames
        d.rectangle(P(x - 10, 300, x + 10, 900), fill=(140, 150, 166))
    d.rectangle(P(0, 290, PW, 310), fill=(140, 150, 166))
    d.rectangle(P(0, 890, PW, 910), fill=(140, 150, 166))
    bx0, bx1 = 900, 1700                                                                          # departure board
    d.rectangle(P(bx0, 960, bx1, 1240), fill=(24, 26, 34), outline=OUT, width=L(6))
    _text(d, P, ps, (bx0 + bx1) / 2, 995, "DEPARTURES", 40, (255, 210, 60))
    for k, (city, tm, st) in enumerate((("GOA", "10:30", ""), ("DELHI", "11:05", "ON TIME"), ("MUMBAI", "11:40", "ON TIME"),
                                         ("JAIPUR", "12:15", "DELAYED"))):
        y = 1050 + k * 50
        f = _font(round(30 * ps))
        d.text(tuple(P(bx0 + 40, y)), city, font=f, fill=(255, 220, 90))
        d.text(tuple(P(bx0 + 330, y)), tm, font=f, fill=(255, 220, 90))
        d.text(tuple(P(bx0 + 520, y)), st, font=f, fill=(120, 230, 120) if st == "ON TIME" else (255, 120, 90))
    d.rectangle(P(200, 980, 700, 1060), fill=(40, 90, 180), outline=OUT, width=L(4))              # signs
    _text(d, P, ps, 450, 1020, "GATE 7", 40, (255, 255, 255))
    d.rectangle(P(1900, 980, 2400, 1060), fill=(250, 200, 50), outline=OUT, width=L(4))
    _text(d, P, ps, 2150, 1020, "CHECK-IN", 40, (30, 30, 40))
    _ground(d, im, ps, 1300, (210, 214, 222), (176, 182, 194))                                   # shiny floor
    d.line(P(0, 1300, PW, 1300), fill=OUT, width=L(5))
    for x in range(-200, PW + 200, 220):
        d.line(P(x, 1300, x - 180, 1920), fill=(196, 200, 210), width=L(3))
    for gx in (120, 1960):                                                                        # rows of seats
        for k in range(5):
            sx = gx + k * 100
            d.rounded_rectangle(P(sx, 1200, sx + 86, 1300), radius=L(14), fill=(40, 110, 200), outline=OUT, width=L(4))
            d.rectangle(P(sx, 1270, sx + 86, 1300), fill=(30, 90, 170), outline=OUT, width=L(3))
        d.rectangle(P(gx, 1300, gx + 500, 1320), fill=(120, 126, 140), outline=OUT, width=L(3))


def _bus_stop(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (110, 176, 230)), (1000, (214, 234, 246))])
    _buildings(d, P, L, PW, rnd, 540, 1000)
    d.rectangle(P(0, 1000, PW, 1180), fill=(196, 190, 180), outline=OUT, width=L(4))             # pavement (back)
    d.rectangle(P(0, 1180, PW, 1440), fill=(70, 72, 80))                                          # road
    for x in range(0, PW, 220):
        d.rectangle(P(x, 1300, x + 120, 1316), fill=(240, 220, 90))
    _ground(d, im, ps, 1440, (206, 200, 190), (180, 174, 164))                                    # pavement (front)
    d.line(P(0, 1440, PW, 1440), fill=OUT, width=L(6))
    x0, x1 = 900, 1700                                                                            # shelter
    d.polygon([tuple(P(x0 - 60, 700)), tuple(P(x1 + 60, 700)), tuple(P(x1 + 30, 760)), tuple(P(x0 - 30, 760))],
              fill=(220, 60, 50), outline=OUT)
    for px_ in (x0, x1 - 20):
        d.rectangle(P(px_, 760, px_ + 20, 1180), fill=(120, 126, 140), outline=OUT, width=L(3))
    d.rectangle(P(x0 + 40, 780, x0 + 360, 1080), fill=(250, 240, 220), outline=OUT, width=L(4))   # ad poster
    d.ellipse(P(x0 + 120, 820, x0 + 280, 980), fill=(250, 180, 60))
    _text(d, P, ps, x0 + 200, 1030, "SALE 50%", 34, (200, 40, 40))
    d.rectangle(P(x0 + 420, 1090, x1 - 60, 1120), fill=(150, 100, 60), outline=OUT, width=L(4))   # bench
    for lx in (x0 + 440, x1 - 100):
        d.rectangle(P(lx, 1120, lx + 20, 1180), fill=(110, 80, 50))
    d.rectangle(P(2150, 640, 2170, 1180), fill=(120, 126, 140), outline=OUT, width=L(3))          # stop sign
    d.rounded_rectangle(P(2050, 560, 2270, 660), radius=L(16), fill=(40, 120, 200), outline=OUT, width=L(5))
    _text(d, P, ps, 2160, 610, "BUS STOP", 38, (255, 255, 255))


def _white(im, d, P, L, PW, ps, rnd):
    """Plain white, the classic stickman look: only a faint floor line."""
    d.rectangle(P(0, 0, PW, 1920), fill=(252, 252, 250))
    d.rectangle(P(0, 1700, PW, 1920), fill=(244, 244, 240))
    d.line(P(0, 1700, PW, 1700), fill=(206, 206, 200), width=L(4))


def _wobbly(d, P, L, pts, width=6, color=OUT):
    d.line([tuple(P(x, y)) for x, y in pts], fill=color, width=L(width), joint="curve")


def _doodle(im, d, P, L, PW, ps, rnd):
    """Doodle paper: notebook lines, hand-drawn hills, a sun, clouds, a tree and grass."""
    d.rectangle(P(0, 0, PW, 1920), fill=(253, 249, 236))
    for y in range(160, 1920, 90):                                   # notebook lines
        d.line(P(0, y, PW, y), fill=(214, 228, 244), width=L(3))
    d.line(P(150, 0, 150, 1920), fill=(244, 190, 190), width=L(3))   # margin
    # sun with rays
    cx, cy = 2250, 330
    d.ellipse(P(cx - 110, cy - 110, cx + 110, cy + 110), fill=(255, 226, 120), outline=OUT, width=L(6))
    for i in range(12):
        a = i * math.pi / 6
        _wobbly(d, P, L, [(cx + 150 * math.cos(a), cy + 150 * math.sin(a)), (cx + 215 * math.cos(a), cy + 215 * math.sin(a))])
    # hills
    for x0, w, h, col in ((-200, 1300, 380, (196, 230, 170)), (900, 1500, 300, (176, 220, 160)), (2000, 1000, 360, (196, 230, 170))):
        pts = [(x0 + w * i / 30, 1450 - h * math.sin(math.pi * i / 30) + 8 * math.sin(i * 1.7)) for i in range(31)]
        d.polygon([tuple(P(x, y)) for x, y in pts + [(x0 + w, 1460), (x0, 1460)]], fill=col)
        _wobbly(d, P, L, pts)
    # ground
    d.rectangle(P(0, 1450, PW, 1920), fill=(232, 244, 214))
    _wobbly(d, P, L, [(x, 1450 + 6 * math.sin(x / 70)) for x in range(0, PW + 40, 40)])
    for _ in range(90):                                              # grass ticks
        x, y = rnd.uniform(0, PW), rnd.uniform(1480, 1900)
        _wobbly(d, P, L, [(x - 10, y), (x, y - 26), (x + 8, y - 4), (x + 18, y - 22)], 4, (90, 150, 80))
    # tree and a flower or two
    for tx in (480, 1750):
        d.rectangle(P(tx - 22, 1100, tx + 22, 1460), fill=(196, 150, 104), outline=OUT, width=L(6))
        for dx, dy, r in ((-90, -40, 120), (90, -40, 120), (0, -130, 140), (0, 20, 120)):
            d.ellipse(P(tx + dx - r, 1080 + dy - r, tx + dx + r, 1080 + dy + r), fill=(150, 210, 120), outline=OUT,
                      width=L(6))
        for dx, dy, r in ((-90, -40, 114), (90, -40, 114), (0, -130, 134), (0, 20, 114)):
            d.ellipse(P(tx + dx - r, 1080 + dy - r, tx + dx + r, 1080 + dy + r), fill=(150, 210, 120))
    for fx_ in (900, 1300, 2300):
        d.line(P(fx_, 1500, fx_, 1420), fill=(90, 150, 80), width=L(6))
        for i in range(5):
            a = i * 2 * math.pi / 5
            d.ellipse(P(fx_ + 22 * math.cos(a) - 16, 1410 + 22 * math.sin(a) - 16, fx_ + 22 * math.cos(a) + 16,
                        1410 + 22 * math.sin(a) + 16), fill=(250, 150, 180), outline=OUT, width=L(3))
        d.ellipse(P(fx_ - 12, 1398, fx_ + 12, 1422), fill=(255, 220, 90), outline=OUT, width=L(3))


DRAW = {"flat_chai_tapri": _chai_tapri, "flat_sabzi_mandi": _sabzi_mandi, "flat_airport": _airport,
        "flat_bus_stop": _bus_stop, "flat_white": _white, "flat_doodle": _doodle}


def draw(bid, im, d, P, L, PW, ps, rnd):
    DRAW[bid](im, d, P, L, PW, ps, rnd)


# ===================================================================== moving parts
def animate(d, bid: str, t: float, px, s: float, visible, x0: float, vw: float, PW: int, birds, items):
    if bid == "flat_chai_tapri":
        _tapri_animate(d, t, px, s, visible, x0, vw, PW, birds)
    elif bid == "flat_sabzi_mandi":
        for X, spd, col in items["walkers"]:                                             # shoppers behind the carts
            Xw = (X + t * spd) % (PW + 400) - 200
            if not visible(Xw):
                continue
            x, y = px(Xw, 1060)
            bob = abs(math.sin(t * 7 + X)) * 6 * s
            d.ellipse([x - 26 * s, y - 210 * s - bob, x + 26 * s, y - 158 * s - bob], fill=col + (255,))
            d.rounded_rectangle([x - 40 * s, y - 160 * s - bob, x + 40 * s, y - bob], radius=20 * s, fill=col + (255,))
        if visible(860):                                                                  # hanging scale (taraju)
            a = 0.18 * math.sin(t * 1.8)
            hx, hy = px(860, 930)
            ex, ey = hx + math.sin(a) * 120 * s, hy + math.cos(a) * 120 * s
            d.line([(hx, hy), (ex, ey)], fill=(60, 60, 60, 255), width=max(1, round(4 * s)))
            d.line([(ex - 70 * s, ey), (ex + 70 * s, ey)], fill=(90, 90, 96, 255), width=max(1, round(6 * s)))
            for sx in (-1, 1):
                d.line([(ex + sx * 70 * s, ey), (ex + sx * 70 * s, ey + 40 * s)], fill=(90, 90, 96, 255), width=max(1, round(2 * s)))
                d.pieslice([ex + sx * 70 * s - 40 * s, ey + 20 * s, ex + sx * 70 * s + 40 * s, ey + 60 * s], 0, 180,
                           fill=(200, 170, 80, 255), outline=OUT + (255,))
        birds(d, x0, vw, t, px, s, 2, 280)
    elif bid == "flat_airport":
        u = (t % 14) / 14                                                                # a plane taking off
        X, Y = -400 + u * (PW + 800), 720 - 380 * u
        if 0 < u < 0.95 and visible(X, 500):
            x, y = px(X, Y)
            k = s
            tilt = -0.18
            def rp(dx, dy):
                return (x + (dx * math.cos(tilt) - dy * math.sin(tilt)) * k, y + (dx * math.sin(tilt) + dy * math.cos(tilt)) * k)
            body = [rp(-170, -18), rp(150, -18), rp(190, 0), rp(150, 18), rp(-170, 18)]
            d.polygon(body, fill=(250, 250, 252, 255), outline=OUT + (255,))
            d.polygon([rp(-20, 0), rp(50, 0), rp(-30, 80)], fill=(220, 226, 236, 255), outline=OUT + (255,))
            d.polygon([rp(-160, -10), rp(-130, -10), rp(-175, -80)], fill=(40, 90, 180, 255), outline=OUT + (255,))
        if visible(1300):                                                                # GOA: BOARDING blinks
            if int(t * 2) % 2 == 0:
                x, y = px(1420, 1050)
                d.rectangle([x, y + 4 * s, x + 170 * s, y + 34 * s], fill=(60, 200, 90, 255))
                d.text((x + 10 * s, y + 4 * s), "BOARDING", fill=(255, 255, 255, 255))
    elif bid == "flat_doodle":
        for j, (X, Y, sp) in enumerate(((300, 330, 22), (1200, 250, 16), (2000, 420, 19))):   # doodle clouds
            Xc = (X + t * sp) % (PW + 600) - 300
            if not visible(Xc, 400):
                continue
            x, y = px(Xc, Y)
            for dx, dy, r in ((-90, 10, 70), (0, -30, 95), (95, 10, 70), (0, 30, 70)):
                d.ellipse([x + (dx - r) * s, y + (dy - r) * s, x + (dx + r) * s, y + (dy + r) * s],
                          fill=(255, 255, 255, 255), outline=OUT + (255,), width=max(1, round(5 * s)))
            for dx, dy, r in ((-90, 10, 64), (0, -30, 89), (95, 10, 64), (0, 30, 64)):
                d.ellipse([x + (dx - r) * s, y + (dy - r) * s, x + (dx + r) * s, y + (dy + r) * s],
                          fill=(255, 255, 255, 255))
        birds(d, x0, vw, t, px, s, 2, 560)
    elif bid == "flat_bus_stop":
        u = (t % 11) / 11                                                                # a bus driving past
        X = PW + 600 - u * (PW + 1400)
        if visible(X, 700):
            x, y = px(X, 1180)
            w, h = 620 * s, 300 * s
            d.rounded_rectangle([x - w / 2, y - h, x + w / 2, y], radius=30 * s, fill=(40, 150, 90, 255),
                                outline=OUT + (255,), width=max(1, round(5 * s)))
            for k in range(5):
                wx = x - w / 2 + 40 * s + k * 112 * s
                d.rectangle([wx, y - h + 40 * s, wx + 90 * s, y - h + 140 * s], fill=(180, 220, 240, 255),
                            outline=OUT + (255,))
            d.rectangle([x - w / 2, y - 120 * s, x + w / 2, y - 100 * s], fill=(250, 210, 60, 255))
            for wx in (x - w / 3, x + w / 3):
                d.ellipse([wx - 50 * s, y - 50 * s, wx + 50 * s, y + 50 * s], fill=(40, 40, 46, 255))
                d.ellipse([wx - 20 * s, y - 20 * s, wx + 20 * s, y + 20 * s], fill=(160, 160, 170, 255))
        birds(d, x0, vw, t, px, s, 3, 280)
