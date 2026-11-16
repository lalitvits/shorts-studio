"""Kitchen action: a kadhai on the gas stove that fries, catches fire, is covered with a steel thali and smokes;
the warm flicker of the fire on everything; and a full-screen explainer animation (why water on an oil fire
explodes, and why covering it works).

Lines drive it. A line's "kadhai" field changes the kadhai when the line starts:
  fry      oil frying (puris, bubbles), gas on
  fire     the oil catches fire (flames shoot up, the camera shakes)
  cover    a thali is put on the kadhai: the flames die out, then smoke
  gas_off  the gas knob is turned off (the burner flame goes out; a burning oil fire keeps burning)
Some actions do it by themselves: "cook" starts frying, "turn_off_gas" turns off the gas, "cover_kadhai" covers it.
The state carries on across scenes, so a later kitchen scene still shows the smoke or the covered kadhai.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

KADHAI_STATES = ("fry", "fire", "cover", "gas_off")
KX, KY = 1820, 1128          # the kadhai's rim centre on the kitchen panorama (it sits on the left burner)
RIM_W, DEPTH = 135, 70
OUT = (36, 31, 32)
STOVE_ACTIONS = {"cook", "turn_off_gas", "cover_kadhai"}
EXPLAINERS = {"oil_fire": "Explainer: water on an oil fire / cover it"}


def broll_span(ln) -> tuple:
    """When a line's cut-away shows: after the first moment of the line (you see who speaks), to its end."""
    d = ln.end - ln.start
    return ln.start + min(1.5, d * 0.2), ln.end


# ----------------------------------------------------------------- what happens when
def _acts(ln):
    """(action, who) pairs of a line: the speaker's own, and the on-screen actor's during a narrator line."""
    out = [ln.action]
    if getattr(ln, "actor", ""):
        out.append(getattr(ln, "actor_action", ""))
    return out


def events(sched) -> list:
    """[(time, state)] of the kadhai over the whole video, in time order."""
    ev = []
    for sc in sched:
        for ln in sc.lines:
            k = getattr(ln, "kadhai", "")
            acts = _acts(ln)
            if k == "fire" and "cook" in acts:         # frying first, then the fire part-way through the line
                ev.append((ln.start, "fry"))
                ev.append((ln.start + min(2.5, (ln.end - ln.start) * 0.4), "fire"))
                continue
            if k:
                ev.append((ln.start + (0.7 if k == "cover" and "cover_kadhai" in acts else 0.0), k))
            if "cover_kadhai" in acts and k != "cover":
                ev.append((ln.start + 0.7, "cover"))
            if "turn_off_gas" in acts and k != "gas_off":
                ev.append((ln.start + 0.5, "gas_off"))
            if "cook" in acts and not ev:
                ev.append((ln.start, "fry"))
    return sorted(ev)


def state_at(ev: list, t: float) -> dict | None:
    """The kadhai at time t, or None when nothing has happened to it yet (then the kitchen looks as usual)."""
    st = None
    for when, kind in ev:
        if when > t:
            break
        st = dict(st or dict(gas=False, fry=False, fire=None, cover=None))
        if kind == "fry":
            st.update(gas=True, fry=True, fire=None, cover=None)
        elif kind == "fire":
            st.update(fire=when, cover=None)
        elif kind == "cover":
            st["cover"] = when
        elif kind == "gas_off":
            st["gas"] = False
    return st


def fire_level(st: dict | None, t: float) -> float:
    """How big the fire is (0..1; a little over 1 for a moment when it flares up)."""
    if not st or st["fire"] is None:
        return 0.0
    u = t - st["fire"]
    lvl = min(1.0, u / 0.3) * (1 + 0.25 * math.exp(-max(0.0, u - 0.3) * 3))
    if st["cover"] is not None:
        c = t - st["cover"]
        lvl *= max(0.0, 1 - c / 1.4) ** 2 if c > 0 else 1.0
    return lvl


def sound_events(sched) -> list:
    """[(time, fx id, volume)] that go with the kadhai and with kitchen actions."""
    out = []
    for when, kind in events(sched):
        out.append((when, {"fry": "sizzle", "fire": "fire", "cover": "clang", "gas_off": "click"}[kind],
                    0.9 if kind != "fry" else 0.7))
        if kind == "fire":
            out.append((when - 0.05, "whoosh", 0.9))
    for sc in sched:
        for ln in sc.lines:
            acts = _acts(ln)
            if "run_in" in acts:
                out.append((ln.start, "footsteps", 0.8))
            if "lower_jug" in acts:
                out.append((ln.start + 0.35, "splash", 0.8))
    return out


def shake_times(sched) -> list:
    return [w for w, k in events(sched) if k == "fire"]


# ----------------------------------------------------------------- drawing on the kitchen
def _flame(d, cx, base, w, h, t, seed, cols, alpha=225):
    """A flickering fire: tongues of flame, in layers (red outside, yellow inside)."""
    if h < 4:
        return
    rnd = random.Random(seed)
    phases = [rnd.uniform(0, 6.28) for _ in range(9)]
    for li, (col, kw, kh) in enumerate(cols):
        ww, hh = w * kw, h * kh
        n = 7
        pts = [(cx - ww / 2, base)]
        for i in range(n):
            u = (i + 0.5) / n
            x = cx - ww / 2 + ww * u + ww * 0.04 * math.sin(t * 9 + phases[i])
            tip = hh * (0.55 + 0.45 * abs(math.sin(t * (5 + i % 3) + phases[i] + li))) * (1 - 0.55 * abs(u - 0.5) * 2)
            pts.append((x - ww / n * 0.35, base - tip * 0.35))
            pts.append((x + ww * 0.03 * math.sin(t * 13 + i), base - tip))
            pts.append((x + ww / n * 0.35, base - tip * 0.35))
        pts.append((cx + ww / 2, base))
        d.polygon(pts, fill=col + (alpha,))


FIRE_COLS = (((226, 52, 26), 1.0, 1.0), ((250, 136, 30), 0.78, 0.74), ((255, 222, 90), 0.5, 0.44))


def _tile_patch(d, px, s, x0w, y0w, x1w, y1w):
    """Kitchen wall tiles over the old pot (the kadhai stands there instead)."""
    a, b = px(x0w, y0w), px(x1w, y1w)
    d.rectangle([a[0], a[1], b[0], b[1]], fill=(236, 246, 244, 255))
    for x in range(int(x0w // 90 * 90), int(x1w) + 1, 90):
        if x0w <= x <= x1w:
            p, q = px(x, y0w), px(x, y1w)
            d.line([p, q], fill=(200, 214, 212, 255), width=max(1, round(3 * s)))
    for y in range(900, int(y1w) + 1, 90):
        if y0w <= y <= y1w:
            p, q = px(x0w, y), px(x1w, y)
            d.line([p, q], fill=(200, 214, 212, 255), width=max(1, round(3 * s)))


def draw(im: Image.Image, st: dict, t: float, x0: float, y0: float, z: float, k: float):
    """Draw the kadhai (and its fire, thali, smoke) on a kitchen frame. Coordinates are kitchen-panorama units."""
    s = z * k

    def px(X, Y):
        return ((X - x0) * s, (Y - y0) * s)

    if not -400 < (KX - x0) * z < 1080 + 400:
        return
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    W = lambda v: max(1, round(v * s))      # noqa: E731
    _tile_patch(d, px, s, 1722, 1040, 1915, 1197)
    # burner flame (blue), licking around the kadhai's bottom
    if st["gas"]:
        for j in range(7):
            fx = KX - 90 + j * 30
            h = 24 + 9 * math.sin(t * 17 + j * 2)
            x, y = px(fx, 1199)
            d.polygon([(x - 8 * s, y), (x + 8 * s, y), (x, y - h * s)], fill=(80, 140, 255, 235))
    # bowl, rim, oil
    bowl = [px(KX + RIM_W * math.cos(a), KY + DEPTH * math.sin(a)) for a in [i * math.pi / 24 for i in range(25)]]
    d.polygon(bowl, fill=(56, 52, 54, 255))
    d.line(bowl, fill=OUT + (255,), width=W(5))
    for side in (-1, 1):                                   # handles
        hx = KX + side * (RIM_W + 14)
        a, b = px(hx - 18, KY - 14), px(hx + 18, KY + 22)
        d.arc([a[0], a[1], b[0], b[1]], 0, 360, fill=OUT + (255,), width=W(7))
    a, b = px(KX - RIM_W, KY - 20), px(KX + RIM_W, KY + 20)
    d.ellipse([a[0], a[1], b[0], b[1]], fill=(44, 40, 42, 255), outline=OUT + (255,), width=W(5))
    lvl = fire_level(st, t)
    oil = (226, 170, 58) if (st["fry"] or lvl > 0) else (176, 126, 44)
    a, b = px(KX - RIM_W + 14, KY - 13), px(KX + RIM_W - 14, KY + 15)
    d.ellipse([a[0], a[1], b[0], b[1]], fill=oil + (255,))
    covered = st["cover"] is not None and t >= st["cover"]
    if st["fry"] and lvl <= 0 and not covered:            # puris puffing up, bubbles
        rnd = random.Random(3)
        for j, (dx, dy) in enumerate(((-60, 0), (8, 4), (66, -2))):
            puff = 1 + 0.12 * math.sin(t * 3 + j * 2)
            r = 30 * puff
            x, y = px(KX + dx, KY + dy - 4)
            d.ellipse([x - r * s, y - r * 0.45 * s, x + r * s, y + r * 0.45 * s], fill=(236, 182, 86, 255),
                      outline=(170, 110, 40, 255), width=W(3))
        for j in range(10):
            u = (t * 2.2 + j * 0.37) % 1
            bx = KX - 100 + rnd.uniform(0, 200)
            x, y = px(bx, KY + 6 - 4 * u)
            r = (3 + 4 * u) * s
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 240, 200, int(220 * (1 - u))), width=W(2))
    # fire
    if lvl > 0.01:
        bx, by = px(KX, KY + 6)
        _flame(d, bx, by, 250 * s * (0.8 + 0.2 * min(1, lvl)), 440 * s * lvl, t, 11, FIRE_COLS)
        rnd = random.Random(int(t * 12))
        for j in range(int(10 * min(1.0, lvl))):           # sparks
            u = (t * 1.5 + j * 0.19) % 1
            x, y = px(KX - 120 + (j * 37 % 240) + 30 * math.sin(t * 4 + j), KY - 80 - 460 * u * lvl)
            r = (4 + 3 * rnd.random()) * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 200, 80, int(230 * (1 - u))))
    # thali (steel plate) put on the kadhai
    if st["cover"] is not None and t >= st["cover"] - 0.3:
        u = min(1.0, (t - (st["cover"] - 0.3)) / 0.3)
        drop = (1 - u * u) * 170
        cx, cy = KX, KY - 8 - drop
        a, b = px(cx - 156, cy - 26), px(cx + 156, cy + 26)
        d.ellipse([a[0], a[1], b[0], b[1]], fill=(196, 202, 212, 255), outline=OUT + (255,), width=W(5))
        a, b = px(cx - 118, cy - 17), px(cx + 118, cy + 17)
        d.ellipse([a[0], a[1], b[0], b[1]], fill=(222, 228, 236, 255), outline=(160, 166, 178, 255), width=W(3))
        a, b = px(cx - 80, cy - 10), px(cx - 20, cy - 2)
        d.ellipse([a[0], a[1], b[0], b[1]], fill=(250, 252, 255, 255))
        if covered:                                        # last flames squeezed out at the edges, then smoke
            c = t - st["cover"]
            if c < 1.4:
                for side in (-1, 1):
                    x, y = px(KX + side * 150, KY - 4)
                    _flame(d, x, y, 70 * s, 150 * s * (1 - c / 1.4), t, 20 + side, FIRE_COLS, 210)
            if 0.2 < c < 9:
                for j in range(9):
                    u2 = ((c - 0.2) * 0.35 + j / 9) % 1
                    fade = min(1.0, (c - 0.2) / 0.6) * max(0.0, 1 - (c - 6) / 3) if c > 6 else min(1.0, (c - 0.2) / 0.6)
                    sx = KX + (j % 3 - 1) * 130 + 50 * math.sin(c * 0.9 + j) * u2
                    x, y = px(sx, KY - 30 - 520 * u2)
                    r = (24 + 70 * u2) * s
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(118, 118, 124, int(150 * (1 - u2) * fade)))
    im.paste(ov, (0, 0), ov)


def glow(im: Image.Image, st: dict, t: float, x0: float, y0: float, z: float, k: float) -> Image.Image:
    """The fire's warm, flickering light on the whole frame."""
    lvl = fire_level(st, t)
    if lvl <= 0.02:
        return im
    s = z * k
    w, h = im.size
    q = 4
    lm = Image.new("RGB", (w // q + 1, h // q + 1), (0, 0, 0))
    d = ImageDraw.Draw(lm)
    gx, gy = (KX - x0) * s / q, (KY - 160 - y0) * s / q
    fl = min(1.2, lvl) * (0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7.3))
    for r, col in ((1300, (34, 12, 0)), (800, (70, 26, 2)), (460, (110, 46, 6)), (230, (150, 70, 14))):
        rr = r * s / q
        d.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], fill=tuple(int(c * fl) for c in col))
    lm = lm.filter(ImageFilter.GaussianBlur(40 * k)).resize((w, h), Image.BILINEAR)
    return ImageChops.screen(im, lm)


# ----------------------------------------------------------------- explainer (B-roll)
EXPLAIN_LABELS = {
    "oil_fire": {
        "hi": [(0.0, 0.3, "गर्म तेल में पानी नीचे बैठ जाता है"), (0.3, 0.45, "पानी तुरंत भाप बन जाता है"),
               (0.45, 0.64, "भाप फटती है - आग का गोला!"), (0.64, 0.82, "थाली से ढकें"),
               (0.82, 1.0, "ऑक्सीजन बंद = आग बुझी")],
        "en": [(0.0, 0.3, "Water sinks under the hot oil"), (0.3, 0.45, "It turns to steam instantly"),
               (0.45, 0.64, "The steam bursts - a fireball!"), (0.64, 0.82, "Cover it with a plate"),
               (0.82, 1.0, "No oxygen = fire out")],
    }
}


def explain_labels(kind: str, language: str) -> list:
    lab = EXPLAIN_LABELS.get(kind, {})
    return lab.get("en" if language == "en" else "hi", lab.get("hi", []))


def _font(size):
    try:
        return ImageFont.load_default(size)
    except TypeError:                                     # old Pillow
        return ImageFont.load_default()


def draw_explainer(w: int, h: int, u: float, t: float, kind: str = "oil_fire") -> Image.Image:
    """One frame of the explainer animation (u: 0..1 through it). Words are added as subtitles (Hindi shaping)."""
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(0, h, 4):                              # dark blue board
        v = y / h
        d.rectangle([0, y, w, y + 4], fill=(int(18 + 14 * v), int(30 + 20 * v), int(58 + 30 * v)))
    s = w / 1080
    cx, rim = 540 * s, 1180 * s                           # a big kadhai seen cut in half
    rw, dp = 380 * s, 300 * s
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    o = ImageDraw.Draw(ov)
    oil_top = rim + 40 * s
    # the kadhai's cut: a thick dark bowl, golden oil inside
    bowl = [(cx + rw * math.cos(a), rim + dp * math.sin(a)) for a in [i * math.pi / 40 for i in range(41)]]
    inner = [(cx + (rw - 26 * s) * math.cos(a), rim + (dp - 26 * s) * math.sin(a)) for a in [i * math.pi / 40 for i in range(41)]]
    d.polygon(bowl, fill=(60, 56, 58))
    d.polygon(inner, fill=(26, 34, 60))
    oil = [(x, max(y, oil_top)) for x, y in inner if y >= oil_top]
    if len(oil) > 2:
        d.polygon([(oil[0][0], oil_top)] + oil + [(oil[-1][0], oil_top)], fill=(226, 168, 48))
    d.line([(cx - rw, rim), (cx + rw, rim)], fill=(90, 86, 88), width=max(2, int(10 * s)))
    small = _font(int(40 * s))
    # flames on top of the oil (until the thali is on)
    if u < 0.45 or 0.58 <= u < 0.72:
        rise = min(1.0, (u - 0.58) / 0.04) if u >= 0.58 else 1.0
        _flame(o, cx, oil_top, 560 * s, 520 * s * rise, t, 7, FIRE_COLS)
    lid_y = oil_top - 30 * s
    if u >= 0.74:                                          # under the thali the fire dies: a little smoke
        g = (u - 0.74) / 0.26
        for j in range(8):
            v = (g * 1.6 + j / 8) % 1
            x = cx + (-1 if j % 2 else 1) * (rw + 30 * s) + 40 * s * math.sin(t + j)
            y = lid_y - 380 * s * v
            r = (20 + 50 * v) * s
            o.ellipse([x - r, y - r, x + r, y + r], fill=(150, 150, 160, int(150 * (1 - v) * (1 - g * 0.6))))
    # water drop sinking, then steam bubbles
    if 0.12 <= u < 0.45:
        v = min(1.0, (u - 0.12) / 0.16)
        dy = -500 * s + (rim + dp - 70 * s + 500 * s) * v if v < 1 else rim + dp - 70 * s
        dy = min(dy, rim + dp - 70 * s)
        if u < 0.32:
            r = 34 * s
            o.ellipse([cx - r, dy - r, cx + r, dy + r], fill=(80, 170, 255, 255), outline=(220, 240, 255, 255), width=3)
            o.polygon([(cx - r * 0.7, dy - r * 0.6), (cx, dy - r * 2), (cx + r * 0.7, dy - r * 0.6)], fill=(80, 170, 255, 255))
            o.text((cx + 50 * s, dy - 20 * s), "H2O", font=small, fill=(200, 230, 255, 255))
        if u >= 0.3:
            g = (u - 0.3) / 0.15
            rnd = random.Random(5)
            for j in range(14):
                bx = cx + rnd.uniform(-160, 160) * s * (0.4 + g)
                by = rim + dp - 70 * s - rnd.uniform(0, 260) * s * g
                r = (14 + 40 * g * rnd.random()) * s
                o.ellipse([bx - r, by - r, bx + r, by + r], fill=(240, 244, 255, 200), outline=(255, 255, 255, 255), width=2)
    # the burst: a fireball and drops of burning oil flying everywhere
    if 0.45 <= u < 0.62:
        g = (u - 0.45) / 0.17
        R = (200 + 900 * g) * s
        for r_, col in ((R, (226, 52, 26)), (R * 0.75, (250, 136, 30)), (R * 0.45, (255, 230, 120))):
            o.ellipse([cx - r_, oil_top - r_ * 1.15, cx + r_, oil_top + r_ * 0.6], fill=col + (int(235 * (1 - g * 0.5)),))
        rnd = random.Random(9)
        for j in range(26):
            a = rnd.uniform(math.pi * 1.05, math.pi * 1.95)
            dist = (300 + rnd.uniform(0, 700)) * s * g
            x, y = cx + math.cos(a) * dist, oil_top + math.sin(a) * dist * 1.1
            r = 12 * s
            o.ellipse([x - r, y - r, x + r, y + r], fill=(255, 170, 40, 255))
        o.text((cx - 60 * s, 300 * s), "X", font=_font(int(220 * s)), fill=(255, 60, 60, 255))
    # the thali coming down, oxygen arrows blocked
    if u >= 0.64:
        v = min(1.0, (u - 0.64) / 0.08)
        ly = lid_y - (1 - v) * 600 * s
        o.ellipse([cx - rw - 40 * s, ly - 34 * s, cx + rw + 40 * s, ly + 34 * s], fill=(200, 206, 216, 255),
                  outline=(250, 252, 255, 255), width=max(2, int(5 * s)))
        o.ellipse([cx - 60 * s, ly - 50 * s, cx + 60 * s, ly - 20 * s], fill=(170, 176, 188, 255))
        if u >= 0.78:
            for j, ax in enumerate((-280, 0, 280)):
                x, y = cx + ax * s, ly - 330 * s
                o.line([(x, y), (x, ly - 90 * s)], fill=(140, 220, 255, 255), width=max(3, int(10 * s)))
                o.polygon([(x - 26 * s, ly - 120 * s), (x + 26 * s, ly - 120 * s), (x, ly - 80 * s)], fill=(140, 220, 255, 255))
                o.text((x + 20 * s, y - 10 * s), "O2", font=small, fill=(180, 235, 255, 255))
                o.line([(x - 40 * s, ly - 230 * s), (x + 40 * s, ly - 150 * s)], fill=(255, 70, 70, 255), width=max(3, int(12 * s)))
                o.line([(x + 40 * s, ly - 230 * s), (x - 40 * s, ly - 150 * s)], fill=(255, 70, 70, 255), width=max(3, int(12 * s)))
        if u >= 0.88:                                      # a big green tick
            g = min(1.0, (u - 0.88) / 0.06)
            pts = [(cx - 120 * s, 1650 * s), (cx - 30 * s, 1740 * s), (cx + 150 * s, 1540 * s)]
            o.line(pts[:2] if g < 0.5 else pts, fill=(80, 220, 110, 255), width=max(4, int(30 * s)), joint="curve")
    im.paste(ov, (0, 0), ov)
    return im
