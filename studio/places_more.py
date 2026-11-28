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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .realms import OUT, _sky

MORE = ("flat_chai_tapri", "flat_sabzi_mandi", "flat_airport", "flat_bus_stop", "flat_white", "flat_doodle",
        "flat_highway", "flat_bathroom", "flat_home", "flat_fridge", "flat_rooftop",
        "flat_bonfire")


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


def _hindi(im, P, ps, x, y, text, size, fill, outline, ow, fallback):
    """Hindi text centred at (x, y) in picture units, drawn by libass (hindi_text.py); English if that fails."""
    from .hindi_text import text_image
    pic = text_image(text, max(8, round(size * ps)), fill, outline, max(1, round(ow * ps)))
    if pic is None:
        d = ImageDraw.Draw(im)
        return _text(d, P, ps, x, y, fallback, size * 0.6, fill, outline)
    cx, cy = P(x, y)
    im.paste(pic, (round(cx - pic.width / 2), round(cy - pic.height / 2)), pic)


def _flower(d, P, L, x, y, r, petal, centre=(255, 220, 60)):
    for i in range(6):
        a = i * math.pi / 3
        d.ellipse(P(x + r * math.cos(a) - r * 0.62, y + r * math.sin(a) - r * 0.62, x + r * math.cos(a) + r * 0.62,
                    y + r * math.sin(a) + r * 0.62), fill=petal, outline=OUT, width=L(2))
    d.ellipse(P(x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55), fill=centre, outline=OUT, width=L(2))


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
    _sky(d, im.width, ps, [(0, (40, 150, 245)), (520, (110, 200, 255)), (1000, (255, 206, 150))])
    d.ellipse(P(2140, 170, 2330, 360), fill=(255, 236, 140))                                       # sun
    for cx, cy, w in ((420, 260, 160), (1500, 200, 200), (2450, 330, 130)):                        # clouds
        for dx, r in ((-w * 0.6, w * 0.45), (0, w * 0.6), (w * 0.6, w * 0.42)):
            d.ellipse(P(cx + dx - r, cy - r * 0.7, cx + dx + r, cy + r * 0.7), fill=(255, 255, 255))
    # a street of painted houses with balconies and water tanks
    houses = [(236, 64, 130), (20, 186, 186), (255, 200, 30), (120, 204, 60), (255, 120, 40), (120, 100, 240)]
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
    d.rectangle(P(x0, 720, x1, 1300), fill=(0, 170, 190), outline=OUT, width=L(7))                   # turquoise stall
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
    # (the chaiwala is drawn in _tapri_animate, as a full cartoon person behind the counter)
    # counter
    d.rectangle(P(x0 - 40, 1080, x1 + 40, 1110), fill=(186, 120, 62), outline=OUT, width=L(5))
    d.rectangle(P(x0, 1110, x1, 1300), fill=(240, 120, 40), outline=OUT, width=L(6))                 # orange front
    panel_cols = [(255, 70, 120), (40, 190, 220), (255, 200, 30), (120, 210, 70), (170, 90, 240)]
    for k, x in enumerate(range(x0, x1, 106)):                                        # truck-art painted panels
        d.rectangle(P(x + 8, 1124, x + 98, 1286), fill=(255, 150, 50), outline=OUT, width=L(3))
        _flower(d, P, L, x + 53, 1250, 16, panel_cols[k % 5])
    for k, x in enumerate(range(x0, x1, 40)):                                         # zigzag band on top
        d.polygon([tuple(P(x, 1112)), tuple(P(x + 40, 1112)), tuple(P(x + 20, 1136))], fill=panel_cols[k % 5],
                  outline=OUT)
    d.rounded_rectangle(P((x0 + x1) / 2 - 300, 1150, (x0 + x1) / 2 + 300, 1228), radius=L(18), fill=(200, 30, 60),
                        outline=OUT, width=L(5))
    _hindi(im, P, ps, (x0 + x1) / 2, 1189, "मसाला चाय ₹10", 52, (255, 255, 255), (120, 20, 40), 5,
           "MASALA CHAI Rs 10")
    d = ImageDraw.Draw(im)
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
    stripes = [(240, 30, 90), (255, 214, 30)]
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
    for k in range(8):                                                                # marigold garlands (swags)
        xa = x0 - 80 + k * (x1 - x0 + 160) / 8
        span = (x1 - x0 + 160) / 8
        for j in range(15):
            u = j / 14
            gx_, gy_ = xa + span * u, 744 + 40 * math.sin(math.pi * u)
            d.ellipse(P(gx_ - 11, gy_ - 11, gx_ + 11, gy_ + 11), fill=(255, 140, 0) if j % 2 else (255, 200, 20),
                      outline=(170, 80, 0), width=L(1))
        d.polygon([tuple(P(xa - 8, 744)), tuple(P(xa + 8, 744)), tuple(P(xa, 784))], fill=(60, 170, 70))  # mango leaf
    bx0, bx1, by0, by1 = x0 + 40, x1 - 40, 410, 636                                   # the signboard
    d.rounded_rectangle(P(bx0 - 18, by0 - 18, bx1 + 18, by1 + 18), radius=L(34), fill=(230, 20, 110), outline=OUT,
                        width=L(7))
    d.rounded_rectangle(P(bx0, by0, bx1, by1), radius=L(24), fill=(255, 222, 40), outline=OUT, width=L(5))
    _flower(d, P, L, bx0 + 52, by0 + 52, 22, (40, 190, 220))
    _flower(d, P, L, bx1 - 52, by0 + 52, 22, (120, 210, 70))
    _flower(d, P, L, bx0 + 52, by1 - 52, 22, (170, 90, 240))
    _flower(d, P, L, bx1 - 52, by1 - 52, 22, (255, 120, 40))
    _hindi(im, P, ps, (bx0 + bx1) / 2, 498, "चाचा की चाय", 128, (214, 20, 40), (255, 252, 236), 10, "CHACHA KI CHAI")
    _hindi(im, P, ps, (bx0 + bx1) / 2, 590, "चाय • समोसा • बन मस्का", 44, (120, 40, 20), (255, 245, 210), 4,
           "CHAI - SAMOSA - BUN MASKA")
    d = ImageDraw.Draw(im)
    for x in range(x0 - 70, x1 + 80, 9):                                                              # string for packets
        d.ellipse(P(x - 2, 778, x + 2, 782), fill=(60, 50, 40))
    for k, (bx, by) in enumerate(((x0 + 60, 800), (x0 + 90, 806), (x0 + 120, 800))):                  # banana bunch
        d.arc(P(bx - 30, by - 10, bx + 30, by + 70), 200, 340, fill=(250, 210, 40), width=L(16))
    flag_cols = [(240, 30, 90), (255, 200, 20), (20, 180, 220), (120, 210, 60), (255, 120, 30), (160, 90, 240)]
    for row, (ya, yb) in enumerate(((330, 300), (395, 372))):                       # bunting across the street
        d.line(P(560, ya, PW, yb), fill=(60, 50, 40), width=L(3))
        for k, x in enumerate(range(600 + row * 30, PW, 62)):
            y = ya + (yb - ya) * (x - 560) / (PW - 560)
            d.polygon([tuple(P(x - 24, y)), tuple(P(x + 24, y)), tuple(P(x, y + 52))], fill=flag_cols[(k + row) % 6],
                      outline=OUT)
    rx, ry = 1350, 1450                                                               # rangoli in front of the stall
    for r, col in ((230, (240, 30, 90)), (180, (255, 200, 20)), (130, (20, 180, 220)), (80, (120, 210, 60)),
                   (36, (255, 255, 255))):
        d.ellipse(P(rx - r, ry - r * 0.32, rx + r, ry + r * 0.32), fill=col)
    for i in range(12):
        a = i * math.pi / 6
        px_, py_ = rx + 205 * math.cos(a), ry + 205 * 0.32 * math.sin(a)
        d.ellipse(P(px_ - 18, py_ - 8, px_ + 18, py_ + 8), fill=(255, 140, 0))
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


CHAIWALA = dict(kind="human", skin=(236, 188, 146), top="vest", top_color=(252, 252, 246), bottom="pants",
                bottom_color=(70, 70, 82), hat=None, hair="short", hair_color=(36, 28, 26), mustache=True,
                stubble=True, female=False, height=1.0, build=1.16)
CHAI_X, CHAI_FEET, CHAI_K = 1140, 1357, 0.62          # where he stands (feet hidden behind the counter), his size


def _chaiwala(d, t, px, s, hand_x, hand_y):
    """The chaiwala: a full flat-cartoon person behind the counter (same drawing as the story characters),
    pouring with his right hand at (hand_x, hand_y), blinking, looking at the glass he fills."""
    from .flat import pose_for, render_sprite
    im = d._image
    tq = round(t * 12) / 12
    pose = pose_for("idle", "happy", tq, False, "chaiwala")
    pose["R"] = ("ik", (hand_x - CHAI_X) / CHAI_K, (hand_y - CHAI_FEET) / CHAI_K)
    pose["L"] = ("ik", 126, -520)
    pose["eyes_dir"] = 0.7
    pose["head_dx"] = 6
    blink = 1.0 if (t % 3.4) > 3.27 else 0.0
    spr, (ax, ay) = render_sprite(CHAIWALA, "front", 1, s * CHAI_K, pose, "happy", 0.0, blink, tq, False)
    X, Y = px(CHAI_X, CHAI_FEET)
    left, top = round(X - ax), round(Y - ay)
    keep = round(px(0, 1080)[1]) - top                                             # hidden below the counter
    if keep > 0:
        part = spr.crop((0, 0, spr.width, min(spr.height, keep)))
        im.paste(part, (left, top), part)
    g = lambda x, y: px(CHAI_X + x * CHAI_K, CHAI_FEET + y * CHAI_K)              # noqa: E731
    w = max(2, round(26 * s * CHAI_K))                                             # red gamchha on the shoulder
    d.line([g(-100, -770), g(-40, -700), g(50, -610), g(118, -540)], fill=(220, 40, 40, 255), width=w)
    d.polygon([g(-128, -790), g(-84, -786), g(-92, -620), g(-124, -626)], fill=(220, 40, 40, 255),
              outline=(36, 31, 32, 255))                                           # the end hanging in front
    for yy in (-750, -705, -660):                                                  # its checks
        d.line([g(-126, yy), g(-88, yy)], fill=(250, 220, 220, 255), width=max(1, round(4 * s * CHAI_K)))
    # the stove and the pot of chai stand in front of him
    P = lambda *v: [px(v[i], v[i + 1])[j] for i in range(0, len(v), 2) for j in (0, 1)]   # noqa: E731
    OUTA = (36, 31, 32, 255)
    d.rectangle(P(1100, 1040, 1340, 1080), fill=(50, 50, 56, 255), outline=OUTA, width=max(1, round(4 * s)))
    pts = [px(1120, 960), px(1320, 960), px(1308, 1040), px(1132, 1040)]
    d.polygon(pts, fill=(210, 214, 224, 255), outline=OUTA)
    d.ellipse(P(1120, 942, 1320, 978), fill=(176, 104, 50, 255), outline=OUTA, width=max(1, round(4 * s)))


def _tapri_animate(d, t, px, s, visible, x0, vw, PW, birds):
    """Steam, the chaiwala pouring chai from high up, swinging packets, a flickering diya, a sleeping dog, birds."""
    import random as _r
    if visible(1140):                                                                    # the chaiwala, behind the pot
        ph = (t % 3.2) / 3.2
        lift = math.sin(math.pi * min(1.0, ph / 0.8)) if ph < 0.8 else 0.0
        _chaiwala(d, t, px, s, 1240, 960 - 150 * lift)
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
        ex, ey = px(hx, hy)
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
    for k in range(26):                                                                  # chasing bulbs round the sign
        u = k / 26
        per = 2 * (1016 + 262)
        dist = u * per
        if dist < 1016:
            X, Y = 842 + dist, 392
        elif dist < 1278:
            X, Y = 1858, 392 + (dist - 1016)
        elif dist < 2294:
            X, Y = 1858 - (dist - 1278), 654
        else:
            X, Y = 842, 654 - (dist - 2294)
        if not visible(X):
            continue
        x, y = px(X, Y)
        lit = (k + int(t * 6)) % 3 == 0
        d.ellipse([x - 9 * s, y - 9 * s, x + 9 * s, y + 9 * s],
                  fill=((255, 250, 200, 255) if lit else (200, 150, 60, 255)), outline=(36, 31, 32, 255))
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


def _highway(im, d, P, L, PW, ps, rnd):
    """A country highway at golden hour running straight into the distance, trees on both sides, red-and-white
    marker posts, and a speed breaker (yellow and white strips) across the road just behind the characters."""
    _sky(d, im.width, ps, [(0, (246, 204, 120)), (520, (250, 226, 160)), (820, (252, 238, 196))])
    vx, vy = PW / 2, 820                                                     # vanishing point on the horizon
    d.ellipse(P(PW * 0.72 - 120, 250, PW * 0.72 + 120, 490), fill=(255, 236, 170))           # low sun
    d.ellipse(P(PW * 0.72 - 90, 280, PW * 0.72 + 90, 460), fill=(255, 246, 210))
    d.rectangle(P(0, vy, PW, 1920), fill=(214, 188, 120))                    # dry ground / fields
    for i in range(7):                                                       # field bands toward the horizon
        y = vy + 30 + i * i * 22
        d.line(P(0, y, PW, y), fill=(200, 172, 104), width=L(3))

    def edge(side, y):                                                       # road edge x at height y
        u = (y - vy) / (1920 - vy)
        return vx + side * (40 + u * (PW * 0.40))

    def poly(pts, fill, w=0):
        d.polygon([tuple(P(*p)) for p in pts], fill=fill, outline=OUT if w else None, width=L(w) if w else 0)

    for side in (-1, 1):                                                     # grass verges
        poly([(edge(side, vy), vy), (edge(side, vy) + side * 160, vy), (edge(side, 1920) + side * 700, 1920),
              (edge(side, 1920), 1920)], (150, 176, 86))
    poly([(edge(-1, vy), vy), (edge(1, vy), vy), (edge(1, 1920), 1920), (edge(-1, 1920), 1920)], (92, 96, 108))
    for side in (-1, 1):                                                     # white edge lines
        poly([(edge(side, vy) - side * 4, vy), (edge(side, vy) - side * 8, vy),
              (edge(side, 1920) - side * 60, 1920), (edge(side, 1920) - side * 22, 1920)], (236, 232, 220))
    y = vy + 6                                                               # centre dashes, longer when near
    while y < 1920:
        u = (y - vy) / (1920 - vy)
        ln, gap, w = 20 + 260 * u, 16 + 200 * u, 3 + 26 * u
        poly([(vx - w / 2, y), (vx + w / 2, y), (vx + w * 0.6, min(1920, y + ln)), (vx - w * 0.6, min(1920, y + ln))],
             (240, 236, 224))
        y += ln + gap

    def bump(y0, y1):                                                        # one speed breaker band
        xl0, xr0, xl1, xr1 = edge(-1, y0), edge(1, y0), edge(-1, y1), edge(1, y1)
        n = 14
        for i in range(n):
            a, b = i / n, (i + 1) / n
            col = (246, 196, 40) if i % 2 == 0 else (244, 242, 234)
            poly([(xl0 + (xr0 - xl0) * a, y0), (xl0 + (xr0 - xl0) * b, y0),
                  (xl1 + (xr1 - xl1) * b, y1), (xl1 + (xr1 - xl1) * a, y1)], col)
        poly([(xl1, y1), (xr1, y1), (xr1, y1 + (y1 - y0) * 0.35), (xl1, y1 + (y1 - y0) * 0.35)], (60, 62, 70))
        d.line(P(xl0, y0, xr0, y0), fill=OUT, width=L(3))
        d.line(P(xl1, y1, xr1, y1), fill=OUT, width=L(3))
    for y0 in (1300, 1352, 1404):                                            # three strips, like the real ones
        bump(y0, y0 + 30)
    for side in (-1, 1):                                                     # trees and marker posts, far to near
        for i in range(10, -1, -1):
            u = (i / 10) ** 1.8
            y = vy + 12 + u * (1500 - vy)
            k = 0.12 + 0.9 * (y - vy) / (1920 - vy)
            x = edge(side, y) + side * (120 + 260 * k)
            tw = 22 * k * 3
            d.rectangle(P(x - tw / 2, y - 260 * k * 2.2, x + tw / 2, y), fill=(120, 80, 46), outline=OUT,
                        width=L(max(1, 4 * k)))
            for dx, dy, r in ((0, -720, 190), (-140, -600, 150), (140, -600, 150), (0, -560, 170)):
                d.ellipse(P(x + dx * k - r * k, y + dy * k - r * k, x + dx * k + r * k, y + dy * k + r * k),
                          fill=(84, 150, 70) if dx else (96, 164, 78), outline=OUT, width=L(max(1, 5 * k)))
            px_ = edge(side, y) + side * 40 * k                              # red and white marker post
            ph = 150 * k
            d.rectangle(P(px_ - 12 * k, y - ph, px_ + 12 * k, y), fill=(246, 244, 236), outline=OUT,
                        width=L(max(1, 3 * k)))
            d.rectangle(P(px_ - 12 * k, y - ph, px_ + 12 * k, y - ph * 0.7), fill=(210, 50, 44))


def _bathroom(im, d, P, L, PW, ps, rnd):
    """An Indian bathroom: tiled walls, a shower curtain, a mirror over the basin, a blue bucket and mug, a towel on
    a hook, a small exhaust window, and a wooden door on the right (the one someone bangs on)."""
    d.rectangle(P(0, 0, PW, 1300), fill=(196, 222, 222))                                     # wall
    for y in range(0, 1300, 110):                                                            # wall tiles
        d.line(P(0, y, PW, y), fill=(168, 198, 198), width=L(4))
    for x in range(0, PW, 110):
        d.line(P(x, 0, x, 1300), fill=(168, 198, 198), width=L(4))
    d.rectangle(P(0, 1180, PW, 1240), fill=(92, 140, 150))                                   # border tiles
    _ground(d, im, ps, 1300, (214, 210, 200), (176, 170, 160))                               # floor
    for x in range(-400, PW + 400, 180):
        d.line(P(x, 1300, x + (x - PW / 2) * 0.6, 1920), fill=(190, 184, 172), width=L(4))
    d.line(P(0, 1300, PW, 1300), fill=OUT, width=L(6))
    # shower corner with a curtain on the left
    d.rectangle(P(60, 160, 560, 180), fill=(170, 170, 180), outline=OUT, width=L(4))           # rod
    for i in range(8):
        x0 = 70 + i * 60
        col = (120, 170, 220) if i % 2 == 0 else (150, 196, 236)
        d.polygon([tuple(P(x0, 180)), tuple(P(x0 + 60, 180)), tuple(P(x0 + 70 + 8 * (i % 3), 1260)),
                   tuple(P(x0 - 6, 1260))], fill=col, outline=OUT)
        d.ellipse(P(x0 + 20, 160, x0 + 40, 180), outline=(140, 140, 150), width=L(4))
    d.ellipse(P(600, 220, 700, 270), fill=(200, 200, 210), outline=OUT, width=L(4))           # shower head
    d.line(P(650, 270, 650, 160), fill=(170, 170, 180), width=L(10))
    # small exhaust window, high up
    d.rectangle(P(820, 140, 1060, 300), fill=(60, 70, 90), outline=OUT, width=L(6))
    for k in range(4):
        d.line(P(830, 170 + k * 36, 1050, 170 + k * 36), fill=(150, 160, 170), width=L(10))
    # mirror and basin
    d.rounded_rectangle(P(1000, 420, 1360, 820), radius=L(30), fill=(214, 236, 246), outline=OUT, width=L(8))
    d.line(P(1060, 480, 1160, 580), fill=(255, 255, 255), width=L(12))
    d.line(P(1060, 560, 1120, 620), fill=(255, 255, 255), width=L(8))
    d.rectangle(P(1150, 940, 1210, 1300), fill=(236, 236, 240), outline=OUT, width=L(5))       # basin stand
    d.chord(P(1020, 860, 1340, 1040), 0, 180, fill=(246, 246, 250), outline=OUT, width=L(6))   # basin
    d.rectangle(P(1020, 900, 1340, 950), fill=(246, 246, 250), outline=OUT, width=L(6))
    d.rectangle(P(1170, 860, 1190, 900), fill=(180, 180, 190), outline=OUT, width=L(3))       # tap
    # blue bucket and mug on the floor
    d.polygon([tuple(P(560, 1330)), tuple(P(780, 1330)), tuple(P(750, 1560)), tuple(P(590, 1560))],
              fill=(40, 110, 210), outline=OUT)
    d.ellipse(P(560, 1305, 780, 1355), fill=(30, 90, 180), outline=OUT, width=L(5))
    d.ellipse(P(580, 1315, 760, 1345), fill=(150, 200, 236))
    d.arc(P(580, 1220, 760, 1360), 200, 340, fill=(30, 80, 160), width=L(8))                 # handle
    d.rounded_rectangle(P(820, 1470, 920, 1580), radius=L(10), fill=(230, 60, 60), outline=OUT, width=L(5))   # mug
    d.arc(P(900, 1490, 960, 1550), 270, 90, fill=(230, 60, 60), width=L(12))
    # towel on a hook
    d.ellipse(P(1520, 520, 1550, 550), fill=(170, 170, 180), outline=OUT, width=L(3))
    d.polygon([tuple(P(1470, 545)), tuple(P(1600, 545)), tuple(P(1620, 900)), tuple(P(1450, 900))],
              fill=(250, 196, 70), outline=OUT)
    for y in (820, 850):
        d.line(P(1455, y, 1615, y), fill=(220, 110, 60), width=L(10))
    # the wooden door on the right
    d.rectangle(P(1820, 260, 2300, 1300), fill=(118, 72, 40), outline=OUT, width=L(8))         # frame
    d.rectangle(P(1860, 300, 2260, 1300), fill=(156, 98, 56), outline=OUT, width=L(6))
    for y0, y1 in ((360, 760), (840, 1240)):                                                  # panels
        d.rectangle(P(1910, y0, 2210, y1), fill=(146, 90, 50), outline=(110, 66, 34), width=L(6))
    d.rounded_rectangle(P(1890, 760, 1950, 800), radius=L(8), fill=(220, 190, 90), outline=OUT, width=L(4))  # handle
    d.rectangle(P(1905, 820, 1925, 870), fill=(70, 50, 30))                                   # keyhole
    d.rectangle(P(1860, 1290, 2260, 1300), fill=(255, 236, 170))                              # light under the door


HOME_TV = (1700, 640, 2160, 900)        # the TV screen in flat_home (picture units)
HOME_FAN = (1300, 120)
HOME_WIN = (300, 300, 760, 860)


def _home(im, d, P, L, PW, ps, rnd):
    """A sunny Indian living room that moves: ceiling fan, a TV playing, curtains in the breeze (see animate)."""
    d.rectangle(P(0, 0, PW, 1300), fill=(250, 226, 196))                                      # walls
    d.rectangle(P(0, 1080, PW, 1300), fill=(236, 206, 172))                                   # lower wall
    d.line(P(0, 1080, PW, 1080), fill=(206, 170, 130), width=L(8))
    _ground(d, im, ps, 1300, (196, 150, 104), (168, 122, 82))                                  # wooden floor
    for x in range(-600, PW + 600, 160):
        d.line(P(x, 1300, x + (x - PW / 2) * 0.8, 1920), fill=(178, 132, 90), width=L(4))
    d.line(P(0, 1300, PW, 1300), fill=OUT, width=L(6))
    x0, y0, x1, y1 = HOME_WIN                                                                 # window, blue sky
    d.rectangle(P(x0, y0, x1, y1), fill=(150, 206, 246), outline=OUT, width=L(8))
    d.ellipse(P(x0 + 260, y0 + 60, x0 + 380, y0 + 180), fill=(255, 236, 140))
    for cx, cy in ((x0 + 110, y0 + 330), (x0 + 330, y0 + 420)):
        d.ellipse(P(cx - 70, cy - 30, cx + 70, cy + 30), fill=(255, 255, 255))
    d.line(P((x0 + x1) / 2, y0, (x0 + x1) / 2, y1), fill=(240, 240, 240), width=L(10))
    d.line(P(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2), fill=(240, 240, 240), width=L(10))
    d.rectangle(P(x0 - 80, y0 - 50, x1 + 80, y0 - 30), fill=(150, 100, 60))                   # curtain rod
    d.rectangle(P(980, 360, 1220, 560), fill=(244, 236, 220), outline=OUT, width=L(8))        # family photo
    for i, col in enumerate(((210, 120, 90), (120, 150, 210), (230, 180, 90))):
        cx = 1030 + i * 70
        d.ellipse(P(cx - 24, 400, cx + 24, 448), fill=(236, 190, 150))
        d.rectangle(P(cx - 26, 452, cx + 26, 540), fill=col)
    d.ellipse(P(1460, 260, 1600, 400), fill=(255, 255, 255), outline=OUT, width=L(6))          # wall clock
    d.line(P(1530, 330, 1530, 285), fill=OUT, width=L(5))
    d.line(P(1530, 330, 1565, 340), fill=OUT, width=L(5))
    tx0, ty0, tx1, ty1 = HOME_TV                                                              # TV on a cabinet
    d.rounded_rectangle(P(tx0 - 24, ty0 - 24, tx1 + 24, ty1 + 24), radius=L(14), fill=(30, 30, 36))
    d.rectangle(P(tx0 - 120, 960, tx1 + 120, 1230), fill=(150, 96, 56), outline=OUT, width=L(6))
    for k in range(3):
        x = tx0 - 100 + k * 240
        d.rectangle(P(x, 990, x + 200, 1200), fill=(130, 82, 46), outline=(100, 62, 34), width=L(4))
    d.rectangle(P(tx0 + 180, 924, tx1 - 180, 960), fill=(40, 40, 46))
    d.polygon([tuple(P(2320, 1230)), tuple(P(2420, 1230)), tuple(P(2400, 1080)), tuple(P(2340, 1080))],
              fill=(190, 100, 60), outline=OUT)                                                 # plant pot
    for a in range(-60, 70, 20):
        import math as _m
        d.line(P(2370, 1080, 2370 + 160 * _m.sin(_m.radians(a)), 1080 - 220 * _m.cos(_m.radians(a))),
               fill=(70, 150, 80), width=L(14))
    d.ellipse(P(160, 1500, 1100, 1760), fill=(176, 60, 70))                                     # rug
    d.ellipse(P(230, 1540, 1030, 1720), outline=(236, 190, 110), width=L(10))


def _home_animate(d, t, px, s, visible):
    """flat_home: the fan turns, the TV plays (changing colours and a bouncing shape), the curtains sway."""
    tx0, ty0, tx1, ty1 = HOME_TV
    if visible((tx0 + tx1) / 2, 400):
        k = int(t * 1.4)
        cols = ((70, 140, 230), (230, 110, 60), (90, 190, 120), (200, 80, 160))
        a, b = px(tx0, ty0), px(tx1, ty1)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=cols[k % 4] + (255,))
        bx = tx0 + 60 + (tx1 - tx0 - 120) * (0.5 + 0.5 * math.sin(t * 2.1))
        by = ty0 + 60 + (ty1 - ty0 - 120) * abs(math.sin(t * 3.3))
        c = px(bx, by)
        r = 34 * s
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(255, 255, 255, 230))
        a2, b2 = px(tx0, ty1 - 50), px(tx1, ty1)
        d.rectangle([a2[0], a2[1], b2[0], b2[1]], fill=(20, 20, 30, 160))
    fx, fy = HOME_FAN
    if visible(fx, 400):
        c = px(fx, fy)
        rod = px(fx, 0)
        d.line([rod, c], fill=(90, 70, 56, 255), width=max(1, round(10 * s)))
        for i in range(3):
            ang = t * 9 + i * 2 * math.pi / 3
            dx, dy = math.cos(ang) * 260 * s, math.sin(ang) * 38 * s
            d.polygon([c, (c[0] + dx - dy * 0.3, c[1] + dy - 14 * s), (c[0] + dx + dy * 0.3, c[1] + dy + 14 * s)],
                      fill=(130, 96, 70, 255))
        r = 34 * s
        d.ellipse([c[0] - r, c[1] - 0.7 * r, c[0] + r, c[1] + 0.7 * r], fill=(96, 72, 56, 255))
    x0, y0, x1, y1 = HOME_WIN
    if visible((x0 + x1) / 2, 500):
        for side, xa in ((-1, x0 - 70), (1, x1 + 70)):                                         # swaying curtains
            sway = 26 * math.sin(t * 1.3 + side)
            inner = xa + (-side) * 170
            pts = [px(xa, y0 - 40), px(inner, y0 - 40), px(inner + sway * 0.6, (y0 + y1) / 2),
                   px(inner + sway, y1 + 120), px(xa, y1 + 120)]
            d.polygon(pts, fill=(236, 150, 60, 255), outline=OUT + (255,))
            for k in (0.33, 0.66):
                xx = xa + (inner - xa) * k
                d.line([px(xx, y0 - 30), px(xx + sway * k, y1 + 110)], fill=(210, 120, 40, 255), width=max(1, round(5 * s)))


def _fridge(im, d, P, L, PW, ps, rnd):
    """Inside a real fridge: a white moulded plastic liner lit by an LED strip at the top (brighter at the top, cooler
    and darker lower down), shelf-support ridges on the side walls, thick glass shelves with silver front trims,
    everyday things on the shelves (milk packet, ketchup, jars, a covered bowl, eggs), clear crisper drawers with
    vegetables at the bottom, and a little frost. The fruits stand on the middle glass shelf."""
    W = im.width
    for y in range(im.height):                                    # liner: warm-white near the light, cooler below
        u = y / im.height
        c = (int(246 - 40 * u), int(248 - 30 * u), int(250 - 16 * u))
        d.line([(0, y), (W, y)], fill=c)
    for x0, x1, sgn in ((0, 330, 1), (PW - 330, PW, -1)):        # side walls in perspective, with support ridges
        xa, xb = (x0, x1) if sgn > 0 else (x1, x0)
        d.polygon([tuple(P(xa, 0)), tuple(P(xb, 140)), tuple(P(xb, 1660)), tuple(P(xa, 1920))], fill=(214, 224, 232))
        for yy in range(260, 1600, 120):
            d.line(P(xa, yy - 40 * (1 if sgn > 0 else 1), xb, yy), fill=(194, 206, 216), width=L(8))
            d.line(P(xa, yy - 34, xb, yy + 6), fill=(236, 242, 246), width=L(3))
    d.rounded_rectangle(P(900, 30, 1700, 110), radius=L(30), fill=(255, 255, 246))                   # LED strip
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a_ in ((900, 40), (600, 50), (350, 60)):
        cx, cy = P(1300, 80)
        gd.ellipse([cx - r * ps, cy - r * 0.5 * ps, cx + r * ps, cy + r * 0.5 * ps], fill=(255, 255, 235, a_))
    im.paste(Image.alpha_composite(im.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(40 * ps))).convert(im.mode))
    d = ImageDraw.Draw(im)

    def shelf(y):                                                 # thick glass shelf with a silver front trim
        d.polygon([tuple(P(330, y - 30)), tuple(P(PW - 330, y - 30)), tuple(P(PW - 250, y + 10)),
                   tuple(P(250, y + 10))], fill=(214, 236, 242))
        d.rectangle(P(250, y + 10, PW - 250, y + 34), fill=(176, 186, 196), outline=OUT, width=L(3))
        d.line(P(260, y + 16, PW - 260, y + 16), fill=(240, 244, 248), width=L(4))                  # trim shine
        d.line(P(380, y - 22, 900, y - 22), fill=(250, 255, 255), width=L(5))                       # glass glint
    # top shelf: milk packet, ketchup, a jar of pickle, butter
    d.polygon([tuple(P(470, 560)), tuple(P(620, 560)), tuple(P(620, 300)), tuple(P(545, 250)), tuple(P(470, 300))],
              fill=(250, 250, 250), outline=OUT)
    d.rectangle(P(470, 380, 620, 470), fill=(60, 120, 210))                                                      # milk
    d.rounded_rectangle(P(700, 300, 790, 560), radius=L(30), fill=(200, 30, 30), outline=OUT, width=L(5))        # ketchup
    d.rectangle(P(725, 250, 765, 305), fill=(240, 240, 240), outline=OUT, width=L(4))
    d.rounded_rectangle(P(860, 380, 1040, 560), radius=L(20), fill=(206, 150, 60), outline=OUT, width=L(5))      # pickle
    d.rectangle(P(850, 350, 1050, 390), fill=(230, 60, 50), outline=OUT, width=L(4))
    d.rounded_rectangle(P(1700, 470, 1960, 560), radius=L(14), fill=(250, 220, 90), outline=OUT, width=L(5))     # butter
    for k in range(6):                                                                                             # eggs
        cx = 1160 + k * 85
        d.ellipse(P(cx - 34, 450, cx + 34, 545), fill=(250, 240, 222), outline=OUT, width=L(3))
    shelf(580)
    # second shelf: a covered steel bowl, a tiffin, a bottle of water
    d.chord(P(420, 960, 720, 1140), 180, 360, fill=(196, 200, 210), outline=OUT, width=L(5))
    d.rectangle(P(420, 1045, 720, 1070), fill=(220, 224, 232), outline=OUT, width=L(4))
    d.rounded_rectangle(P(1900, 940, 2140, 1110), radius=L(18), fill=(120, 190, 220), outline=OUT, width=L(5))
    d.rectangle(P(1940, 915, 2100, 950), fill=(90, 150, 190), outline=OUT, width=L(4))
    d.rounded_rectangle(P(1130, 800, 1220, 1110), radius=L(26), fill=(170, 214, 240), outline=OUT, width=L(5))
    d.rectangle(P(1150, 760, 1200, 805), fill=(40, 90, 200), outline=OUT, width=L(4))
    shelf(1130)
    shelf(1700)                                                   # the fruits stand on this one
    # crisper drawers: clear plastic with vegetables inside
    for x0, x1 in ((300, 1280), (1320, PW - 300)):
        d.rounded_rectangle(P(x0, 1750, x1, 2000), radius=L(24), fill=(206, 226, 222), outline=OUT, width=L(5))
        rr = random.Random(x0)
        for _ in range(9):
            cx, cy = rr.uniform(x0 + 80, x1 - 80), rr.uniform(1830, 1900)
            col = rr.choice(((90, 160, 70), (230, 120, 40), (200, 40, 40), (120, 180, 80)))
            d.ellipse(P(cx - 60, cy - 40, cx + 60, cy + 40), fill=col)
        d.rectangle(P(x0 + 10, 1760, x1 - 10, 2000), fill=None, outline=(240, 248, 248), width=L(3))
        d.rounded_rectangle(P((x0 + x1) / 2 - 120, 1770, (x0 + x1) / 2 + 120, 1806), radius=L(16),
                            fill=(236, 244, 244), outline=OUT, width=L(4))                     # drawer handle
    for _ in range(40):                                                                         # frost specks
        x, y = rnd.uniform(330, PW - 330), rnd.uniform(140, 300)
        d.ellipse(P(x - 6, y - 6, x + 6, y + 6), fill=(255, 255, 255))

def _night_sky(d, im, ps, top=(16, 26, 62), bottom=(54, 72, 120), y1=1100):
    _sky(d, im.width, ps, [(0, top), (y1, bottom)])


def _rooftop(im, d, P, L, PW, ps, rnd):
    """A rooftop terrace at night: moon and stars, houses with lit windows behind, the terrace wall with damp
    patches, a clothes line with a dupatta, a potted plant, a steel bucket and a water tank."""
    _night_sky(d, im, ps)
    d.ellipse(P(1900, 120, 2040, 260), fill=(250, 250, 240))                                    # moon
    for _ in range(50):
        x, y = rnd.uniform(0, PW), rnd.uniform(20, 600)
        d.ellipse(P(x - 4, y - 4, x + 4, y + 4), fill=(240, 240, 255))
    x = 0
    while x < PW:                                                                               # houses behind
        w, h = rnd.uniform(220, 380), rnd.uniform(380, 760)
        col = rnd.choice(((40, 52, 86), (52, 60, 96), (34, 44, 74)))
        d.rectangle(P(x, 1100 - h, x + w, 1100), fill=col)
        for wy in range(int(1100 - h + 60), 1060, 120):
            for wx in range(int(x + 40), int(x + w - 60), 110):
                if rnd.random() < 0.55:
                    d.rectangle(P(wx, wy, wx + 50, wy + 60), fill=(250, 210, 110))
        x += w + rnd.uniform(10, 40)
    d.rectangle(P(0, 1050, PW, 1460), fill=(222, 170, 126))                                     # terrace wall
    d.rectangle(P(0, 1030, PW, 1060), fill=(236, 190, 146), outline=OUT, width=L(5))
    for _ in range(14):                                                                         # damp patches
        x, y = rnd.uniform(0, PW), rnd.uniform(1100, 1420)
        d.ellipse(P(x - 70, y - 30, x + 70, y + 30), fill=(206, 152, 110))
    _ground(d, im, ps, 1460, (196, 150, 112), (170, 124, 90))                                   # terrace floor
    d.line(P(0, 1460, PW, 1460), fill=OUT, width=L(6))
    d.line(P(0, 260, 900, 300), fill=(60, 60, 60), width=L(4))                                  # clothes line
    d.polygon([tuple(P(250, 270)), tuple(P(380, 276)), tuple(P(400, 640)), tuple(P(230, 620))], fill=(236, 110, 150))
    d.rectangle(P(560, 280, 700, 520), fill=(240, 240, 230), outline=OUT, width=L(3))
    d.rectangle(P(80, 0, 130, 1460), fill=(200, 150, 110), outline=OUT, width=L(4))             # a pillar
    d.polygon([tuple(P(340, 1440)), tuple(P(520, 1440)), tuple(P(490, 1640)), tuple(P(370, 1640))],
              fill=(200, 100, 50), outline=OUT)                                                 # plant pot
    for a in range(-70, 80, 18):
        d.line(P(430, 1440, 430 + 200 * math.sin(math.radians(a)), 1440 - 240 * math.cos(math.radians(a))),
               fill=(70, 140, 70), width=L(14))
    d.polygon([tuple(P(600, 1520)), tuple(P(740, 1520)), tuple(P(720, 1660)), tuple(P(620, 1660))],
              fill=(180, 186, 196), outline=OUT)                                                # bucket
    d.rounded_rectangle(P(2150, 820, 2500, 1100), radius=L(40), fill=(40, 40, 46), outline=OUT, width=L(5))   # tank


FIRE_X = 1300                         # where the bonfire burns in flat_bonfire (picture units)


def _bonfire(im, d, P, L, PW, ps, rnd):
    """A village lane at night in winter: lime-washed houses, a little shop with a string of bulbs and jars of
    sweets, a motorbike parked, a street lamp, a dusty ground; the bonfire burns in the middle (see animate)."""
    _night_sky(d, im, ps, (14, 22, 52), (40, 52, 92), 700)
    for x0, x1, h, col in ((0, 700, 700, (226, 196, 150)), (700, 1150, 560, (214, 178, 132)),
                           (1500, 2000, 620, (230, 202, 160)), (2000, PW, 760, (208, 172, 128))):
        d.rectangle(P(x0, 1250 - h, x1, 1250), fill=col, outline=OUT, width=L(4))
        d.rectangle(P(x0 + 60, 1250 - h + 120, x0 + 200, 1250 - h + 260), fill=(250, 200, 100), outline=OUT, width=L(4))
    d.rectangle(P(1150, 760, 1500, 1250), fill=(120, 70, 40), outline=OUT, width=L(5))          # shop
    d.polygon([tuple(P(1110, 760)), tuple(P(1540, 760)), tuple(P(1500, 680)), tuple(P(1150, 680))], fill=(200, 80, 40),
              outline=OUT)
    for k in range(6):                                                                          # jars of sweets
        x = 1180 + k * 52
        d.rounded_rectangle(P(x, 1100, x + 40, 1170), radius=L(8), fill=(250, 170, 60), outline=OUT, width=L(3))
    d.rectangle(P(1150, 1170, 1500, 1250), fill=(150, 96, 56), outline=OUT, width=L(4))
    d.line(P(1100, 790, 1560, 800), fill=(60, 50, 40), width=L(3))                              # bulb string
    for k in range(9):
        x = 1110 + k * 55
        d.ellipse(P(x - 12, 792, x + 12, 820), fill=(255, 220, 120))
    d.rectangle(P(2300, 400, 2320, 1250), fill=(70, 70, 76))                                    # street lamp
    d.polygon([tuple(P(2250, 400)), tuple(P(2370, 400)), tuple(P(2340, 440)), tuple(P(2280, 440))], fill=(70, 70, 76))
    d.ellipse(P(2280, 430, 2340, 470), fill=(255, 230, 150))
    bx = 1850                                                                                   # motorbike
    for wx in (bx, bx + 300):
        d.ellipse(P(wx - 70, 1130, wx + 70, 1270), fill=(30, 30, 34), outline=OUT, width=L(4))
    d.polygon([tuple(P(bx, 1180)), tuple(P(bx + 300, 1180)), tuple(P(bx + 230, 1100)), tuple(P(bx + 60, 1100))],
              fill=(40, 40, 46), outline=OUT)
    _ground(d, im, ps, 1250, (150, 108, 70), (118, 80, 50))                                     # dusty ground
    d.line(P(0, 1250, PW, 1250), fill=OUT, width=L(5))
    for _ in range(60):
        x, y = rnd.uniform(0, PW), rnd.uniform(1270, 1900)
        d.ellipse(P(x - 6, y - 3, x + 6, y + 3), fill=(130, 92, 60))


def _bonfire_animate(d, t, px, s, visible):
    """The bonfire: logs, flickering flames in three layers, rising sparks, and a warm glow on the ground."""
    X, Y = FIRE_X, 1780
    if not visible(X, 600):
        return
    cx, cy = px(X, Y)
    for r, a_ in ((520, 50), (360, 70), (220, 90)):                                              # warm glow
        d.ellipse([cx - r * s, cy - r * 0.45 * s, cx + r * s, cy + r * 0.45 * s], fill=(255, 150, 60, a_))
    for ang in (-25, 25, 0):                                                                    # logs
        a = math.radians(ang)
        dx, dy = 170 * math.cos(a) * s, 30 * math.sin(a) * s
        d.line([(cx - dx, cy + 20 * s - dy), (cx + dx, cy + 20 * s + dy)], fill=(90, 56, 30, 255), width=max(2, round(36 * s)))
    for layer, (col, scale) in enumerate((((240, 80, 30), 1.0), ((255, 150, 40), 0.72), ((255, 230, 120), 0.42))):
        pts = []
        n = 9
        for i in range(n + 1):
            u = i / n
            x = (u - 0.5) * 300 * scale
            h = (330 * scale) * (0.35 + 0.65 * math.sin(math.pi * u)) * (0.8 + 0.25 * math.sin(t * 9 + i * 1.7 + layer))
            pts.append((cx + x * s, cy - h * s))
        pts += [(cx + 150 * scale * s, cy + 10 * s), (cx - 150 * scale * s, cy + 10 * s)]
        d.polygon(pts, fill=col + (255,))
    for k in range(8):                                                                          # sparks
        u = (t * 0.7 + k / 8) % 1.0
        x = cx + (60 * math.sin(k * 2.3 + t * 2) + (k - 4) * 14) * s
        y = cy - (300 + 500 * u) * s
        r = 6 * s * (1 - u)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 200, 90, int(255 * (1 - u))))


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
        "flat_bus_stop": _bus_stop, "flat_white": _white, "flat_doodle": _doodle, "flat_highway": _highway,
        "flat_bathroom": _bathroom, "flat_home": _home, "flat_fridge": _fridge,
        "flat_rooftop": _rooftop, "flat_bonfire": _bonfire}


def draw(bid, im, d, P, L, PW, ps, rnd):
    DRAW[bid](im, d, P, L, PW, ps, rnd)


# ===================================================================== moving parts
def _bathroom_door(d, px, s, t, shake: float, open_: float):
    """The bathroom door when something happens to it: it rattles in its frame when banged on (shake 0..1), and
    swings open toward us, letting the light in (open_ 0..1)."""
    x0, x1, y0, y1 = 1860, 2260, 300, 1300
    if open_ > 0:
        a, b = px(x0, y0), px(x1, y1)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(255, 242, 200, 255))                     # light from outside
        a, b = px(x0, y1 - 40), px(x1, y1)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(240, 220, 170, 255))
        w = (x1 - x0) * (1 - 0.82 * open_)                                                   # swung toward the hinge
        bulge = 70 * open_
        pts = [px(x1 - w, y0 - bulge), px(x1, y0), px(x1, y1), px(x1 - w, y1 + bulge)]
        d.polygon(pts, fill=(156, 98, 56, 255), outline=OUT + (255,))
        hx = x1 - w + 30
        a, b = px(hx, 760), px(hx + 40 * (1 - open_) + 12, 800)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(220, 190, 90, 255))
        return
    jit = shake * 14 * math.sin(t * 90)                                                         # rattling
    a, b = px(x0 + jit, y0 + abs(jit) * 0.3), px(x1 + jit, y1)
    d.rectangle([a[0], a[1], b[0], b[1]], fill=(156, 98, 56, 255), outline=OUT + (255,), width=max(1, round(6 * s)))
    for p0, p1 in ((360, 760), (840, 1240)):
        a, b = px(x0 + 50 + jit, p0), px(x1 - 50 + jit, p1)
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(146, 90, 50, 255), outline=(110, 66, 34, 255),
                    width=max(1, round(6 * s)))
    a, b = px(x0 + 30 + jit, 760), px(x0 + 90 + jit, 800)
    d.rounded_rectangle([a[0], a[1], b[0], b[1]], radius=8 * s, fill=(220, 190, 90, 255), outline=OUT + (255,))
    for k in range(3):                                                                         # dust shaken off
        u = (t * 3 + k / 3) % 1
        a = px(x0 - 30 + k * 220, y0 - 20 + 300 * u)
        r = 6 * s
        d.ellipse([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=(220, 210, 190, int(200 * shake * (1 - u))))


def animate(d, bid: str, t: float, px, s: float, visible, x0: float, vw: float, PW: int, birds, items, door=None):
    if bid == "flat_bathroom" and door and (door[0] > 0.02 or door[1] > 0):
        _bathroom_door(d, px, s, t, *door)
    if bid == "flat_home":
        _home_animate(d, t, px, s, visible)
    if bid == "flat_bonfire":
        _bonfire_animate(d, t, px, s, visible)
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
