"""Five everyday flat-cartoon places that move: village, school, kitchen, office and market.

Same idea as realms.py: draw_static() paints the wide picture once; animate() adds the moving parts every frame.
Village: chimney smoke, birds, butterflies.            School: waving flag, a clock that ticks, birds.
Kitchen: gas flame, steam, pressure-cooker whistle,    Office: computer screens that scroll, a clock that ticks,
         clouds passing the window.                             clouds passing the window.
Market:  twinkling string lights, shoppers walking past behind the stalls, birds.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from .realms import OUT, _glow, _h, _sky

from . import places_more

PLACES = ("flat_village", "flat_school", "flat_kitchen", "flat_office", "flat_market", "flat_bedroom",
          "flat_kitchen_fridge") + places_more.MORE


def _mix(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ===================================================================== static pictures
def draw_static(bid: str, im: Image.Image, ps: float, PW: int):
    d = ImageDraw.Draw(im)
    P = lambda *v: [x * ps for x in v]     # noqa: E731
    L = lambda w: max(1, round(w * ps))     # noqa: E731
    rnd = random.Random(_h(bid))
    if bid in places_more.MORE:                     # chai tapri, sabzi mandi, airport, bus stop
        return places_more.draw(bid, im, d, P, L, PW, ps, rnd)
    {"flat_village": _village, "flat_school": _school, "flat_kitchen": _kitchen, "flat_kitchen_fridge": _kitchen,
     "flat_office": _office, "flat_market": _market, "flat_bedroom": _bedroom}[bid](im, d, P, L, PW, ps, rnd)


def _bedroom(im, d, P, L, PW, ps, rnd):
    """A young man's bedroom at night: bed, study table with laptop, wardrobe, door, night window, fan, clock."""
    d.rectangle(P(0, 0, PW, 1920), fill=(176, 196, 224))                                        # wall
    d.rectangle(P(0, 1180, PW, 1200), fill=(150, 168, 196))                                     # skirting
    _ground(d, im, ps, 1200, (176, 132, 92), (146, 104, 70))                                    # wooden floor
    for x in range(-300, PW + 300, 170):
        d.line(P(x, 1200, x - 260, 1920), fill=(156, 112, 76), width=L(3))
    d.line(P(0, 1200, PW, 1200), fill=OUT, width=L(5))
    wx = 1150                                                                                    # night window
    d.rectangle(P(wx, 380, wx + 520, 860), fill=(24, 32, 72), outline=OUT, width=L(8))
    for _ in range(26):
        x, y = rnd.uniform(wx + 20, wx + 500), rnd.uniform(400, 840)
        d.ellipse(P(x - 3, y - 3, x + 3, y + 3), fill=(240, 240, 220))
    d.ellipse(P(wx + 330, 430, wx + 440, 540), fill=(246, 242, 214))
    d.ellipse(P(wx + 352, 418, wx + 462, 528), fill=(24, 32, 72))
    for xx in (wx + 260,):
        d.line(P(xx, 380, xx, 860), fill=OUT, width=L(6))
    d.line(P(wx, 620, wx + 520, 620), fill=OUT, width=L(6))
    for cx, sgn in ((wx - 40, 1), (wx + 560, -1)):                                              # curtains
        d.polygon([tuple(P(cx - 70, 340)), tuple(P(cx + 70, 340)), tuple(P(cx + 70 + 30 * sgn, 900)),
                   tuple(P(cx - 70 + 30 * sgn, 900))], fill=(196, 72, 72), outline=OUT)
    d.rectangle(P(wx - 140, 330, wx + 660, 350), fill=(120, 80, 50), outline=OUT, width=L(4))
    bx = 120                                                                                      # bed
    d.rectangle(P(bx, 900, bx + 70, 1330), fill=(130, 84, 54), outline=OUT, width=L(5))          # headboard post
    d.rounded_rectangle(P(bx, 960, bx + 700, 1100), radius=L(30), fill=(140, 92, 60), outline=OUT, width=L(6))
    d.rectangle(P(bx + 40, 1100, bx + 760, 1250), fill=(226, 230, 240), outline=OUT, width=L(6))   # mattress
    d.rounded_rectangle(P(bx + 300, 1060, bx + 780, 1260), radius=L(40), fill=(70, 120, 190), outline=OUT, width=L(6))
    d.rounded_rectangle(P(bx + 80, 1040, bx + 290, 1130), radius=L(40), fill=(250, 250, 250), outline=OUT, width=L(5))
    d.rectangle(P(bx + 40, 1250, bx + 760, 1300), fill=(130, 84, 54), outline=OUT, width=L(5))
    tx = 1850                                                                                     # study table
    d.rectangle(P(tx, 1060, tx + 420, 1090), fill=(160, 110, 70), outline=OUT, width=L(5))
    for lx in (tx + 20, tx + 380):
        d.rectangle(P(lx, 1090, lx + 22, 1260), fill=(130, 88, 56), outline=OUT, width=L(3))
    d.polygon([tuple(P(tx + 120, 1060)), tuple(P(tx + 300, 1060)), tuple(P(tx + 320, 1052)), tuple(P(tx + 100, 1052))],
              fill=(60, 64, 74), outline=OUT)                                                     # laptop base
    d.polygon([tuple(P(tx + 130, 1052)), tuple(P(tx + 290, 1052)), tuple(P(tx + 300, 940)), tuple(P(tx + 120, 940))],
              fill=(50, 54, 64), outline=OUT)
    d.polygon([tuple(P(tx + 142, 1040)), tuple(P(tx + 278, 1040)), tuple(P(tx + 286, 952)), tuple(P(tx + 134, 952))],
              fill=(80, 140, 210))
    d.rectangle(P(tx + 340, 960, tx + 352, 1060), fill=(60, 60, 66))                            # desk lamp
    d.polygon([tuple(P(tx + 320, 960)), tuple(P(tx + 380, 960)), tuple(P(tx + 360, 920)), tuple(P(tx + 336, 920))],
              fill=(240, 200, 80), outline=OUT)
    d.rectangle(P(2350, 520, 2580, 1200), fill=(170, 120, 80), outline=OUT, width=L(6))         # wardrobe / door
    d.line(P(2465, 520, 2465, 1200), fill=OUT, width=L(5))
    for hx in (2445, 2485):
        d.ellipse(P(hx - 8, 850, hx + 8, 866), fill=(230, 200, 100))
    d.rectangle(P(820, 480, 1020, 760), fill=(240, 120, 60), outline=OUT, width=L(5))           # poster
    d.ellipse(P(860, 520, 980, 640), fill=(255, 220, 90))
    d.rectangle(P(860, 660, 980, 700), fill=(40, 40, 60))
    d.ellipse(P(560, 440, 700, 580), fill=(255, 255, 250), outline=OUT, width=L(6))             # wall clock


def _fan(d, cx, cy, t, s, ang0=0.0):
    """Ceiling fan seen from the side-ish: three blades turning."""
    for i in range(3):
        a = ang0 + t * 9 + i * 2 * math.pi / 3
        dx, dy = math.cos(a) * 230 * s, math.sin(a) * 34 * s
        d.polygon([(cx, cy), (cx + dx - dy * 0.3, cy + dy - 12 * s), (cx + dx + dy * 0.3, cy + dy + 12 * s)],
                  fill=(120, 90, 70, 255))
    d.ellipse([cx - 30 * s, cy - 20 * s, cx + 30 * s, cy + 20 * s], fill=(90, 70, 56, 255))


def _ground(d, im, ps, y0, top, bottom):
    for y in range(round(y0 * ps), im.height):
        u = (y / ps - y0) / (1920 - y0)
        d.line([(0, y), (im.width, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bottom)))


def _village(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (110, 176, 228)), (1150, (214, 236, 246))])
    d.ellipse(P(380, 230, 560, 410), fill=(252, 214, 104))
    for cx, w, col in ((500, 900, (128, 182, 110)), (1500, 1100, (112, 170, 98)), (2400, 800, (128, 182, 110))):
        d.ellipse(P(cx - w, 1000, cx + w, 1500), fill=col, outline=OUT, width=L(5))
    for i, col in enumerate([(206, 196, 92), (150, 190, 90), (214, 186, 96)]):       # fields
        y = 1150 + i * 45
        d.polygon([tuple(P(x, yy)) for x, yy in ((0, y), (PW, y - 20), (PW, y + 45), (0, y + 50))], fill=col)
    _ground(d, im, ps, 1290, (214, 176, 120), (180, 140, 92))
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
    for hx in (300, 1050, 1900, 2400):                                                 # mud huts
        d.rectangle(P(hx - 150, 1010, hx + 150, 1295), fill=(226, 196, 150), outline=OUT, width=L(6))
        d.polygon([tuple(P(hx - 200, 1020)), tuple(P(hx + 200, 1020)), tuple(P(hx, 840))], fill=(150, 104, 56), outline=OUT)
        d.line([tuple(P(hx - 200, 1020)), tuple(P(hx, 840)), tuple(P(hx + 200, 1020))], fill=OUT, width=L(6))
        for k in range(6):
            d.line(P(hx - 170 + k * 68, 1012, hx - 120 + k * 50, 900), fill=(124, 84, 44), width=L(3))
        d.rectangle(P(hx - 40, 1150, hx + 40, 1295), fill=(110, 74, 46), outline=OUT, width=L(4))
        d.rectangle(P(hx + 70, 1080, hx + 120, 1130), fill=(90, 130, 170), outline=OUT, width=L(4))
        d.rectangle(P(hx + 80, 850, hx + 112, 960), fill=(150, 120, 100), outline=OUT, width=L(4))   # chimney
    wx = 1480                                                                          # well
    d.ellipse(P(wx - 110, 1230, wx + 110, 1290), fill=(160, 160, 160), outline=OUT, width=L(5))
    d.rectangle(P(wx - 110, 1260, wx + 110, 1380), fill=(150, 150, 154), outline=OUT, width=L(5))
    for k in range(3):
        d.line(P(wx - 110, 1290 + k * 30, wx + 110, 1290 + k * 30), fill=(120, 120, 124), width=L(3))
    for px_ in (wx - 100, wx + 90):
        d.rectangle(P(px_, 1120, px_ + 12, 1260), fill=(110, 74, 46))
    d.polygon([tuple(P(wx - 140, 1130)), tuple(P(wx + 140, 1130)), tuple(P(wx, 1060))], fill=(170, 60, 50), outline=OUT)
    for tx in (700, 2150):                                                             # palm trees
        d.line(P(tx, 1290, tx + 30, 900), fill=(130, 92, 56), width=L(26))
        for a in range(7):
            ang = math.pi * (0.1 + a / 7)
            d.line(P(tx + 30, 900, tx + 30 + math.cos(ang) * 190, 900 - math.sin(ang) * 80 + 60), fill=(64, 140, 70), width=L(22))
    d.ellipse(P(1700, 1300, 1900, 1420), fill=(222, 190, 90), outline=OUT, width=L(5))  # haystack
    for _ in range(80):
        x, y = rnd.uniform(0, PW), rnd.uniform(1330, 1900)
        d.line(P(x, y, x - 8, y - 22), fill=(110, 150, 70), width=L(4))
        d.line(P(x, y, x + 8, y - 20), fill=(110, 150, 70), width=L(4))


def _school(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (96, 164, 222)), (1100, (208, 230, 246))])
    _ground(d, im, ps, 1290, (206, 172, 124), (176, 140, 98))
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
    d.rectangle(P(0, 1180, PW, 1290), fill=(226, 120, 90), outline=OUT, width=L(5))    # boundary wall
    for x in range(0, PW, 120):
        d.line(P(x, 1180, x, 1290), fill=(196, 100, 74), width=L(3))
    C = 1300
    d.rectangle(P(C - 650, 620, C + 650, 1180), fill=(246, 206, 110), outline=OUT, width=L(7))
    d.polygon([tuple(P(C - 700, 630)), tuple(P(C + 700, 630)), tuple(P(C + 600, 540)), tuple(P(C - 600, 540))],
              fill=(186, 72, 56), outline=OUT)
    d.rectangle(P(C - 160, 470, C + 160, 640), fill=(246, 206, 110), outline=OUT, width=L(6))   # clock tower
    d.polygon([tuple(P(C - 190, 480)), tuple(P(C + 190, 480)), tuple(P(C, 380))], fill=(186, 72, 56), outline=OUT)
    d.ellipse(P(C - 70, 490, C + 70, 630), fill=(255, 255, 250), outline=OUT, width=L(6))
    d.rectangle(P(C - 260, 660, C + 260, 730), fill=(40, 90, 150), outline=OUT, width=L(5))       # sign board
    for row, y in enumerate((780, 960)):
        for i in range(10):
            x = C - 600 + i * 122
            if abs(x + 40 - C) < 120 and row == 1:
                continue
            d.rectangle(P(x, y, x + 80, y + 120), fill=(140, 196, 230), outline=OUT, width=L(4))
            d.line(P(x + 40, y, x + 40, y + 120), fill=OUT, width=L(3))
    d.rectangle(P(C - 90, 1000, C + 90, 1180), fill=(130, 84, 50), outline=OUT, width=L(5))
    d.rectangle(P(2200, 560, 2214, 1290), fill=(160, 160, 170), outline=OUT, width=L(3))           # flag pole
    d.ellipse(P(2196, 548, 2218, 570), fill=(220, 190, 60))
    for tx in (220, 2480):
        d.rectangle(P(tx - 14, 900, tx + 14, 1290), fill=(110, 74, 46), outline=OUT, width=L(4))
        d.ellipse(P(tx - 140, 740, tx + 140, 1000), fill=(78, 150, 84), outline=OUT, width=L(6))
    d.rectangle(P(500, 1500, 520, 1690), fill=(80, 80, 90))                                         # swing frame
    d.rectangle(P(780, 1500, 800, 1690), fill=(80, 80, 90))
    d.rectangle(P(490, 1490, 810, 1510), fill=(80, 80, 90))


def _kitchen(im, d, P, L, PW, ps, rnd):
    wall, tile = (250, 236, 196), (236, 246, 244)
    d.rectangle(P(0, 0, PW, 1920), fill=wall)
    d.rectangle(P(0, 0, PW, 380), fill=(196, 124, 78), outline=OUT, width=L(6))                 # top cabinets
    for x in range(0, PW, 260):
        d.rectangle(P(x + 12, 20, x + 248, 360), fill=(214, 140, 90), outline=OUT, width=L(5))
        d.ellipse(P(x + 120, 300, x + 140, 320), fill=(240, 200, 120))
    d.rectangle(P(0, 900, PW, 1250), fill=tile)                                                     # tiles
    for x in range(0, PW, 90):
        d.line(P(x, 900, x, 1250), fill=(200, 214, 212), width=L(3))
    for y in range(900, 1250, 90):
        d.line(P(0, y, PW, y), fill=(200, 214, 212), width=L(3))
    d.rectangle(P(1050, 460, 1550, 860), fill=(150, 205, 240), outline=OUT, width=L(8))             # window
    d.line(P(1300, 460, 1300, 860), fill=OUT, width=L(6))
    d.line(P(1050, 660, 1550, 660), fill=OUT, width=L(6))
    d.rectangle(P(1030, 860, 1570, 890), fill=(214, 140, 90), outline=OUT, width=L(4))
    for i, x in enumerate(range(200, 900, 130)):                                                     # jar shelf
        d.rectangle(P(x, 700, x + 90, 830), fill=[(220, 120, 80), (240, 200, 90), (140, 190, 110)][i % 3], outline=OUT, width=L(4))
        d.rectangle(P(x - 5, 680, x + 95, 710), fill=(170, 110, 70), outline=OUT, width=L(3))
    d.rectangle(P(140, 830, 960, 860), fill=(170, 110, 70), outline=OUT, width=L(4))
    d.rectangle(P(0, 1250, PW, 1380), fill=(120, 124, 136), outline=OUT, width=L(6))                # counter
    d.rectangle(P(0, 1380, PW, 1560), fill=(196, 124, 78), outline=OUT, width=L(5))
    for x in range(0, PW, 260):
        d.rectangle(P(x + 12, 1392, x + 248, 1550), fill=(214, 140, 90), outline=OUT, width=L(4))
    d.rectangle(P(1720, 1200, 2120, 1252), fill=(60, 60, 66), outline=OUT, width=L(5))              # gas stove
    for bx in (1820, 2020):
        d.ellipse(P(bx - 50, 1185, bx + 50, 1205), fill=(40, 40, 44))
    d.ellipse(P(1730, 1050, 1910, 1110), fill=(200, 200, 206), outline=OUT, width=L(5))              # pot
    d.rectangle(P(1740, 1080, 1900, 1190), fill=(200, 200, 206), outline=OUT, width=L(5))
    d.rectangle(P(1960, 1060, 2080, 1190), fill=(190, 190, 196), outline=OUT, width=L(5))            # cooker
    d.ellipse(P(1950, 1040, 2090, 1080), fill=(170, 170, 176), outline=OUT, width=L(4))
    d.rectangle(P(2010, 1000, 2030, 1045), fill=(50, 50, 54))
    _ground(d, im, ps, 1560, (226, 210, 186), (196, 176, 150))                                      # floor
    for x in range(-200, PW + 200, 200):
        d.line(P(x, 1560, x - 160, 1920), fill=(206, 188, 160), width=L(3))


def _office(im, d, P, L, PW, ps, rnd):
    d.rectangle(P(0, 0, PW, 1920), fill=(214, 224, 232))
    d.rectangle(P(300, 300, 2300, 1000), fill=(160, 206, 240), outline=OUT, width=L(8))             # big window
    x = 300
    while x < 2300:                                                                                  # skyline
        w, top = rnd.randint(120, 220), rnd.randint(560, 860)
        d.rectangle(P(x, top, min(2300, x + w), 1000), fill=rnd.choice([(120, 146, 176), (140, 160, 190), (110, 130, 160)]))
        x += w + rnd.randint(0, 20)
    for xx in range(300, 2301, 400):
        d.line(P(xx, 300, xx, 1000), fill=OUT, width=L(6))
    d.rectangle(P(280, 1000, 2320, 1030), fill=(190, 196, 204), outline=OUT, width=L(4))
    d.ellipse(P(2420, 360, 2560, 500), fill=(255, 255, 250), outline=OUT, width=L(6))               # wall clock
    d.rectangle(P(0, 1180, PW, 1920), fill=(110, 120, 140))                                          # carpet
    _ground(d, im, ps, 1300, (122, 130, 150), (96, 104, 124))
    for dx in (180, 1000, 1820):                                                                     # desks
        d.rectangle(P(dx, 1150, dx + 600, 1190), fill=(170, 120, 80), outline=OUT, width=L(5))
        d.rectangle(P(dx + 20, 1190, dx + 50, 1330), fill=(120, 86, 60))
        d.rectangle(P(dx + 550, 1190, dx + 580, 1330), fill=(120, 86, 60))
        d.rectangle(P(dx + 200, 960, dx + 420, 1110), fill=(40, 44, 54), outline=OUT, width=L(5))    # monitor
        d.rectangle(P(dx + 290, 1110, dx + 330, 1150), fill=(60, 64, 74))
        d.rectangle(P(dx + 230, 1135, dx + 390, 1150), fill=(70, 74, 84), outline=OUT, width=L(3))
    for px_ in (60, 2520):                                                                           # plants
        d.rectangle(P(px_ - 50, 1200, px_ + 50, 1320), fill=(200, 110, 70), outline=OUT, width=L(5))
        for a in range(6):
            ang = math.pi * (0.15 + a / 7)
            d.ellipse(P(px_ + math.cos(ang) * 70 - 30, 1200 - math.sin(ang) * 120 - 50,
                        px_ + math.cos(ang) * 70 + 30, 1200 - math.sin(ang) * 120 + 50), fill=(70, 150, 80), outline=OUT, width=L(3))


def _market(im, d, P, L, PW, ps, rnd):
    _sky(d, im.width, ps, [(0, (250, 180, 120)), (700, (252, 214, 160)), (1200, (240, 226, 200))])
    _ground(d, im, ps, 1290, (150, 140, 130), (110, 104, 98))
    d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
    for x in range(0, PW, 520):                                                                      # back buildings
        d.rectangle(P(x, 560 + (x // 520 % 2) * 80, x + 500, 1000), fill=rnd.choice([(224, 170, 130), (200, 150, 150), (230, 200, 140)]),
                    outline=OUT, width=L(5))
    stripes = [((214, 60, 50), (250, 246, 236)), ((40, 140, 90), (250, 246, 236)), ((240, 170, 40), (250, 246, 236)),
               ((60, 110, 190), (250, 246, 236))]
    for i, sx in enumerate(range(40, PW, 520)):                                                       # stalls
        a, b = stripes[i % 4]
        d.rectangle(P(sx, 1050, sx + 460, 1300), fill=(170, 120, 76), outline=OUT, width=L(5))       # counter
        for k in range(6):
            d.polygon([tuple(P(sx - 20 + k * 83, 860)), tuple(P(sx + 63 + k * 83, 860)),
                       tuple(P(sx + 63 + k * 83, 960)), tuple(P(sx - 20 + k * 83, 960))], fill=a if k % 2 == 0 else b)
        d.rectangle(P(sx - 20, 860, sx + 480, 960), outline=OUT, width=L(5))
        for k in range(6):
            cx_ = sx + 22 + k * 83
            d.pieslice(P(cx_ - 42, 925, cx_ + 42, 1000), 0, 180, fill=a if k % 2 == 0 else b, outline=OUT, width=L(3))
        d.rectangle(P(sx, 960, sx + 14, 1050), fill=(110, 74, 46))
        d.rectangle(P(sx + 446, 960, sx + 460, 1050), fill=(110, 74, 46))
        fruit = [(230, 70, 60), (250, 190, 50), (110, 180, 70), (240, 130, 40), (150, 80, 160)][i % 5]
        for row in range(3):
            for k in range(8 - row):
                fx_, fy = sx + 50 + row * 25 + k * 48, 1040 - row * 38
                d.ellipse(P(fx_ - 24, fy - 24, fx_ + 24, fy + 24), fill=_mix(fruit, 0.9 + 0.1 * ((k + row) % 2)), outline=OUT, width=L(3))
    for x in range(0, PW, 9):                                                                        # light wire
        y = 790 + 40 * math.sin(x / 260 * math.pi) ** 2
        d.ellipse(P(x - 2, y - 2, x + 2, y + 2), fill=(50, 40, 40))


# ===================================================================== moving parts
@lru_cache(maxsize=8)
def _items(bid, PW):
    rnd = random.Random(_h(bid, "anim"))
    return dict(
        smoke=[(hx + 96, 850) for hx in (300, 1050, 1900, 2400)],
        flies=[(rnd.uniform(0, PW), rnd.uniform(1300, 1600), rnd.uniform(0, 6.28)) for _ in range(6)],
        bulbs=[(x, 790 + 40 * math.sin(x / 260 * math.pi) ** 2, rnd.choice([(255, 220, 90), (255, 120, 90), (120, 220, 255), (160, 255, 140)]),
                rnd.uniform(0, 6.28)) for x in range(30, PW, 70)],
        walkers=[(rnd.uniform(0, PW), rnd.uniform(50, 90) * rnd.choice([-1, 1]),
                  rnd.choice([(90, 80, 110), (120, 90, 80), (70, 100, 120), (130, 110, 90)])) for _ in range(7)],
        clouds=[(rnd.uniform(0, PW), rnd.uniform(-60, 120), rnd.uniform(12, 25)) for _ in range(4)],
    )


def _clock(d, cx, cy, r, t, s):
    """Clock hands: the minute hand turns slowly, the second hand ticks."""
    for ang, ln, w in ((-math.pi / 2 + t * 0.05, 0.55, 7), (-math.pi / 2 + math.floor(t) * math.pi / 30, 0.8, 3)):
        d.line([(cx, cy), (cx + math.cos(ang) * r * ln, cy + math.sin(ang) * r * ln)],
               fill=(30, 30, 30, 255) if w > 3 else (210, 40, 40, 255), width=max(1, round(w * s)))
    d.ellipse([cx - 5 * s, cy - 5 * s, cx + 5 * s, cy + 5 * s], fill=(30, 30, 30, 255))


def _birds(d, x0, vw, t, px, s, n=3, y=300):
    for j in range(n):
        X = x0 - 100 + ((t * 40 + j * 80) % (vw + 260))
        Y = y + j * 26 + 10 * math.sin(t * 1.3 + j)
        x, yy = px(X, Y)
        flap, ws = math.sin(t * 9 + j * 1.7), 22 * s
        d.line([(x - ws, yy - ws * 0.5 * flap), (x, yy), (x + ws, yy - ws * 0.5 * flap)], fill=(30, 30, 40, 255),
               width=max(1, round(3.5 * s)))


def animate(im: Image.Image, bid: str, t: float, x0: float, y0: float, z: float, k: float, PW: int, blur: bool,
            kadhai: bool = False, door=None):
    vw = 1080 / z
    s = z * k

    def px(X, Y):
        return (X - x0) * s, (Y - y0) * s

    def visible(X, m=250):
        return x0 - m < X < x0 + vw + m

    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    it = _items(bid, PW)
    if bid in places_more.MORE:
        places_more.animate(d, bid, t, px, s, visible, x0, vw, PW, _birds, it, door=door)
    elif bid == "flat_village":
        for cx, cy in it["smoke"]:                               # chimney smoke
            if not visible(cx):
                continue
            for j in range(5):
                u = (t * 0.25 + j / 5) % 1.0
                x, y = px(cx + 40 * math.sin(t * 0.8 + j) * u + 60 * u, cy - 420 * u)
                r = (20 + 50 * u) * s
                d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 235, 235, int(160 * (1 - u))))
        _birds(d, x0, vw, t, px, s)
        for X, Y, ph in it["flies"]:                             # butterflies
            X2, Y2 = X + 120 * math.sin(t * 0.7 + ph), Y + 40 * math.sin(t * 1.9 + ph)
            if not visible(X2):
                continue
            x, y = px(X2, Y2)
            f = abs(math.sin(t * 14 + ph)) * 14 * s + 3 * s
            for sgn in (-1, 1):
                d.ellipse([x + sgn * f - 7 * s, y - 9 * s, x + sgn * f + 7 * s, y + 9 * s], fill=(250, 170, 60, 240))
    elif bid == "flat_school":
        X, Y = 2214, 570                                          # waving flag
        if visible(X):
            pts_top, pts_bot = [], []
            for i in range(13):
                u = i / 12
                wy = 16 * math.sin(t * 6 - u * 5) * u
                pts_top.append(px(X + 220 * u, Y + wy))
                pts_bot.append(px(X + 220 * u, Y + 140 + wy))
            for band, col in enumerate([(255, 153, 51, 255), (255, 255, 255, 255), (19, 136, 8, 255)]):
                a = [(tx, ty + (by - ty) * band / 3) for (tx, ty), (bx, by) in zip(pts_top, pts_bot)]
                b = [(tx, ty + (by - ty) * (band + 1) / 3) for (tx, ty), (bx, by) in zip(pts_top, pts_bot)]
                d.polygon(a + b[::-1], fill=col)
            d.line(pts_top + pts_bot[::-1] + [pts_top[0]], fill=(40, 40, 40, 255), width=max(1, round(3 * s)))
        if visible(1300):
            cx, cy = px(1300, 560)
            _clock(d, cx, cy, 62 * s, t, s)
        _birds(d, x0, vw, t, px, s)
    elif bid in ("flat_kitchen", "flat_kitchen_fridge"):
        for X, Y, spd in it["clouds"]:                            # clouds in the window
            cxw = 1050 + ((X + t * spd) % 640) - 70
            x, y = px(cxw, 520 + Y * 0.6)
            for dx, r in ((0, 34), (36, 44), (76, 30)):
                d.ellipse([x + dx * s - r * s, y - r * s, x + dx * s + r * s, y + r * s], fill=(255, 255, 255, 230))
        if visible(1820):
            for bx in ((2020,) if kadhai else (1820, 2020)):      # gas flames (the kadhai draws its own burner)
                for j in range(5):
                    fx_ = bx - 40 + j * 20
                    h = 22 + 8 * math.sin(t * 17 + j * 2)
                    x, y = px(fx_, 1190)
                    d.polygon([(x - 7 * s, y), (x + 7 * s, y), (x, y - h * s)], fill=(80, 140, 255, 230))
            for j in range(0 if kadhai else 4):                    # steam from the pot
                u = (t * 0.4 + j / 4) % 1
                x, y = px(1820 + 30 * math.sin(t + j), 1040 - 300 * u)
                r = (18 + 40 * u) * s
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(150 * (1 - u))))
            w = (t % 6.0)                                          # cooker whistle every 6 s
            if w < 1.2:
                for j in range(3):
                    u = min(1.0, w / 1.2 + j * 0.1)
                    x, y = px(2020 + 10 * j, 995 - 260 * u)
                    r = (16 + 46 * u) * s
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(200 * (1 - u))))
    elif bid == "flat_office":
        for X, Y, spd in it["clouds"]:
            cxw = 300 + ((X + t * spd) % 2200) - 100
            if not visible(cxw):
                continue
            x, y = px(cxw, 380 + Y)
            for dx, r in ((0, 40), (44, 54), (92, 36)):
                d.ellipse([x + dx * s - r * s, y - r * s, x + dx * s + r * s, y + r * s], fill=(255, 255, 255, 220))
        for dx in (180, 1000, 1820):                              # screens with scrolling text
            if not visible(dx + 300):
                continue
            x1, y1 = px(dx + 212, 972)
            x2, y2 = px(dx + 408, 1098)
            d.rectangle([x1, y1, x2, y2], fill=(60, 120, 200, 255))
            for row in range(7):
                yy = y1 + ((row * 18 + t * 30) % 126) * s
                if yy > y2 - 6 * s:
                    continue
                ln = (0.35 + 0.55 * ((row * 37 + dx) % 10) / 10) * (x2 - x1 - 20 * s)
                d.line([(x1 + 10 * s, yy), (x1 + 10 * s + ln, yy)], fill=(220, 236, 255, 255), width=max(1, round(5 * s)))
        if visible(2490):
            cx, cy = px(2490, 430)
            _clock(d, cx, cy, 62 * s, t, s)
    elif bid == "flat_bedroom":
        if visible(630):
            cx, cy = px(630, 510)
            _clock(d, cx, cy, 62 * s, t, s)
        cx, cy = px(1300, 140)                                    # ceiling fan
        d.line([(cx, 0), (cx, cy)], fill=(80, 64, 52, 255), width=max(1, round(10 * s)))
        _fan(d, cx, cy, t, s)
        for j in range(3):                                         # twinkling stars in the window
            X, Y = 1200 + j * 140, 470 + j * 90
            if visible(X):
                a = max(0.0, math.sin(t * 3 + j * 2))
                x, y = px(X, Y)
                r = 6 * s * a
                d.polygon([(x, y - 3 * r), (x + r, y), (x, y + 3 * r), (x - r, y)], fill=(255, 255, 230, 230))
    elif bid == "flat_market":
        for X, spd, col in it["walkers"]:                         # shoppers walking behind the stalls
            Xw = (X + t * spd) % (PW + 400) - 200
            if not visible(Xw):
                continue
            x, y = px(Xw, 1050)
            bob = abs(math.sin(t * 7 + X)) * 6 * s
            d.ellipse([x - 26 * s, y - 210 * s - bob, x + 26 * s, y - 158 * s - bob], fill=col + (255,))
            d.rounded_rectangle([x - 40 * s, y - 160 * s - bob, x + 40 * s, y - bob], radius=20 * s, fill=col + (255,))
        for X, Y, col, ph in it["bulbs"]:                         # twinkling string lights
            if not visible(X):
                continue
            a = 0.55 + 0.45 * math.sin(t * 4 + ph)
            x, y = px(X, Y + 18)
            r = 11 * s
            d.ellipse([x - 2.2 * r, y - 2.2 * r, x + 2.2 * r, y + 2.2 * r], fill=col + (int(70 * a),))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(150 + 105 * a),))
        _birds(d, x0, vw, t, px, s, 2, 260)
    if blur:
        ov = ov.filter(ImageFilter.GaussianBlur(max(1, 2.5 * s)))
    bb = ov.getbbox()                       # paste only the part that has something on it
    if bb:
        part = ov.crop(bb)
        im.paste(part, bb[:2], part)
