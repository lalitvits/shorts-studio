"""More everyday flat-cartoon places: chai ki tapri, sabzi mandi, airport and bus stop.

Same idea as places.py: draw() paints the wide picture once (2600 x 1920 units); animate() adds the moving parts.
Chai tapri:  steam from the chai pot, swinging chips packets, birds.
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

MORE = ("flat_chai_tapri", "flat_sabzi_mandi", "flat_airport", "flat_bus_stop")


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
    _sky(d, im.width, ps, [(0, (150, 196, 236)), (1000, (250, 226, 196))])
    d.ellipse(P(2200, 220, 2360, 380), fill=(255, 222, 120))                                      # morning sun
    _buildings(d, P, L, PW, rnd)
    _ground(d, im, ps, 1290, (214, 196, 166), (186, 166, 136))                                    # dusty road
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
    d.rectangle(P(160, 620, 230, 1300), fill=(120, 84, 56), outline=OUT, width=L(5))              # neem tree
    for cx, cy, r in ((120, 560, 190), (300, 520, 170), (200, 420, 160)):
        d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=(80, 150, 80), outline=OUT, width=L(5))
    x0, x1 = 980, 1780                                                                            # the tapri
    d.rectangle(P(x0, 760, x1, 1300), fill=(120, 150, 170), outline=OUT, width=L(6))              # tin back wall
    for x in range(x0, x1, 40):
        d.line(P(x, 760, x, 1300), fill=(100, 128, 148), width=L(3))
    for y, row in ((830, ((236, 200, 90), (220, 90, 70), (120, 180, 90))), (930, ((240, 170, 60), (180, 120, 200), (90, 160, 220)))):
        d.rectangle(P(x0 + 60, y + 70, x1 - 60, y + 82), fill=(150, 100, 60), outline=OUT, width=L(3))   # shelves
        for k, xx in enumerate(range(x0 + 90, x1 - 100, 95)):                                      # biscuit jars
            col = row[k % 3]
            d.rounded_rectangle(P(xx, y, xx + 70, y + 70), radius=L(10), fill=(230, 240, 246), outline=OUT, width=L(3))
            d.rectangle(P(xx + 6, y + 26, xx + 64, y + 66), fill=col)
            d.rectangle(P(xx + 10, y - 10, xx + 60, y + 4), fill=(200, 60, 50), outline=OUT, width=L(2))
    d.polygon([tuple(P(x0 - 100, 700)), tuple(P(x1 + 100, 700)), tuple(P(x1 + 60, 770)), tuple(P(x0 - 60, 770))],
              fill=(150, 170, 190), outline=OUT)                                                  # tin roof
    for x in range(x0 - 90, x1 + 90, 34):
        d.line(P(x, 702, x + 4, 768), fill=(120, 140, 160), width=L(3))
    d.rectangle(P(x0 + 100, 560, x1 - 100, 700), fill=(250, 210, 60), outline=OUT, width=L(6))    # signboard
    _text(d, P, ps, (x0 + x1) / 2, 615, "CHAI  TAPRI", 70, (200, 40, 30), (255, 250, 230))
    _text(d, P, ps, (x0 + x1) / 2, 672, "TEA  -  SAMOSA  -  BUN", 30, (60, 40, 30))
    d.rectangle(P(x0 - 40, 1090, x1 + 40, 1300), fill=(170, 116, 70), outline=OUT, width=L(6))    # counter
    for x in range(x0, x1 + 40, 120):
        d.line(P(x, 1100, x, 1290), fill=(140, 96, 58), width=L(3))
    d.rectangle(P(x0 + 60, 1050, x0 + 300, 1090), fill=(60, 60, 66), outline=OUT, width=L(4))     # stove
    d.polygon([tuple(P(x0 + 80, 950)), tuple(P(x0 + 280, 950)), tuple(P(x0 + 270, 1050)), tuple(P(x0 + 90, 1050))],
              fill=(196, 200, 210), outline=OUT)                                                  # chai pateela
    d.ellipse(P(x0 + 80, 930, x0 + 280, 970), fill=(150, 90, 50), outline=OUT, width=L(4))
    d.line(P(x0 + 280, 990, x0 + 340, 970), fill=(150, 150, 160), width=L(8))
    tx = x0 + 380                                                                                 # tray of glasses
    d.rectangle(P(tx, 1078, tx + 300, 1090), fill=(180, 184, 196), outline=OUT, width=L(2))
    for k in range(6):
        gx = tx + 25 + k * 46
        d.polygon([tuple(P(gx - 16, 1020)), tuple(P(gx + 16, 1020)), tuple(P(gx + 12, 1078)), tuple(P(gx - 12, 1078))],
                  fill=(236, 244, 248), outline=OUT)
        d.polygon([tuple(P(gx - 14, 1036)), tuple(P(gx + 14, 1036)), tuple(P(gx + 11, 1076)), tuple(P(gx - 11, 1076))],
                  fill=(176, 110, 56))
    px_ = x1 - 260                                                                                # samosa plate
    d.ellipse(P(px_ - 120, 1062, px_ + 120, 1092), fill=(230, 232, 236), outline=OUT, width=L(3))
    for k, (dx, dy) in enumerate(((-60, 0), (0, -10), (60, 0), (-30, -40), (30, -40))):
        cx, cy = px_ + dx, 1066 + dy
        d.polygon([tuple(P(cx - 36, cy)), tuple(P(cx + 36, cy)), tuple(P(cx, cy - 52))], fill=(226, 172, 84), outline=OUT)
    for x in range(x0 - 60, x1 + 60, 9):                                                          # string for packets
        d.ellipse(P(x - 2, 776, x + 2, 780), fill=(60, 50, 40))
    bx = 300                                                                                      # bench
    d.rectangle(P(bx, 1360, bx + 560, 1395), fill=(150, 100, 60), outline=OUT, width=L(5))
    for lx in (bx + 30, bx + 500):
        d.rectangle(P(lx, 1395, lx + 26, 1480), fill=(120, 80, 50), outline=OUT, width=L(3))
    d.rectangle(P(2050, 1180, 2200, 1300), fill=(80, 140, 200), outline=OUT, width=L(5))          # water drum
    d.ellipse(P(2050, 1160, 2200, 1200), fill=(110, 170, 220), outline=OUT, width=L(4))


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
             ("chilli", "tomato", "onion")]
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


DRAW = {"flat_chai_tapri": _chai_tapri, "flat_sabzi_mandi": _sabzi_mandi, "flat_airport": _airport,
        "flat_bus_stop": _bus_stop}


def draw(bid, im, d, P, L, PW, ps, rnd):
    DRAW[bid](im, d, P, L, PW, ps, rnd)


# ===================================================================== moving parts
def animate(d, bid: str, t: float, px, s: float, visible, x0: float, vw: float, PW: int, birds, items):
    if bid == "flat_chai_tapri":
        if visible(1160):
            for j in range(6):                                                           # steam from the chai
                u = (t * 0.45 + j / 6) % 1
                x, y = px(1160 + 30 * math.sin(t * 1.3 + j) + 20 * u, 930 - 330 * u)
                r = (16 + 40 * u) * s
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(140 * (1 - u))))
        cols = [(240, 80, 60), (250, 200, 50), (60, 160, 220), (120, 200, 90), (230, 120, 200)]
        for k, X in enumerate(range(940, 1840, 70)):                                     # chips packets swinging
            if not visible(X):
                continue
            a = 0.12 * math.sin(t * 2.2 + k * 0.9)
            x, y = px(X, 780)
            w, h = 22 * s, 70 * s
            pts = [(x - w, y), (x + w, y), (x + w + h * math.sin(a), y + h), (x - w + h * math.sin(a), y + h)]
            d.polygon(pts, fill=cols[k % 5] + (255,), outline=OUT + (255,))
        birds(d, x0, vw, t, px, s, 3, 300)
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
