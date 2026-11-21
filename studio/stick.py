"""Stickman comedy: stick-figure characters, slapstick moves and cartoon effects.

Stickmen use the same poses as the flat cartoon people (every action works for them), drawn as thick lines
with a big round head and big expressive eyes.

Slapstick moves (also for the flat cartoon people): slip and fall, trip on the face, get up, get hit and fly off
the screen, bonk on the head, freeze in shock, double-take, faint, a dust-cloud fight, crash into a wall, dizzy,
shiver, cartoon run, run across / chase, sneak on tiptoe, roll on the floor laughing, kick, jaw drop.
A move can turn, squash or throw the whole character: the pose gets "rot" (degrees, around "piv"), "tx"/"ty"
(a shift after turning), "sq" (squash x, y) and "move" (a big shift done by the camera, in character units).

Cartoon effects drawn around a character (a line's "effect", and automatically with the moves):
dizzy stars, impact burst, speed lines, dust puffs, flying sweat, "!" and "?" above the head, angry steam,
floating hearts, shivering lines, a rain cloud over the head, eyes popping out, an idea bulb, and the fight cloud.
"""
from __future__ import annotations

import math
import random

STICK_BOX = (-620, -1480, 700, 60)         # a stickman with room for effects above the head
TURN_BOX = (-1350, -1550, 1350, 120)        # room to fall over / roll

# ------------------------------------------------------------------ catalogue
from .catalog import EFFECT_LABELS, SLAPSTICK_LABELS as SLAPSTICK  # noqa: E402

# moves that leave the character where the move ended (lying down) until their next action
STAYS = {"slip_fall", "fall_face", "faint", "crash_wall"}
# moves that keep going (still animated) until the character's next action
LOOPS = {"lie_sleep", "sleep_stand"}
TWO_PERSON = {"poke", "shake_awake"}      # they walk up to the nearest person first
# moves the camera must show in full (a reaction like a jaw drop can still get a close-up)
NEED_WIDE = set(SLAPSTICK) - {"jaw_drop", "double_take", "freeze", "shiver", "dizzy"}
EFFECTS = {k for k in EFFECT_LABELS if k}
# how long a silent line with a move lasts when no seconds are given
MOVE_HOLD = {"slip_fall": 2.0, "fall_face": 1.8, "get_up": 1.3, "fly_away": 1.4, "hit_head": 1.8, "freeze": 1.6,
             "double_take": 2.0, "faint": 2.0, "fight_cloud": 2.4, "crash_wall": 2.2, "dizzy": 2.0, "shiver": 1.6,
             "cartoon_run": 1.4, "run_across": 1.5, "chase": 1.8, "sneak_in": 2.8, "tiptoe": 2.0,
             "laugh_floor": 2.2, "kick": 1.2, "jaw_drop": 1.6, "lie_sleep": 2.2, "sleep_stand": 2.2,
             "wake_jolt": 1.4, "poke": 1.6, "shake_awake": 1.6, "disappointed": 2.2}


HIP_L = ("ik", 126, -520)       # a hand on the hip


def _sm(v):
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


LIE = 315          # how far a body turned flat around the hips (pivot -450) drops to lie on the ground


def slapstick_pose(p: dict, action: str, emotion: str, t: float):
    """Fills in the pose of a slapstick move, t seconds after it started."""
    s = math.sin
    fx = set()
    if action == "slip_fall":
        if t < 0.22:                                      # feet slip out, arms fly up
            e = _sm(t / 0.22)
            p.update(rot=28 * e, piv=-450, tx=120 * e, ty=-50 * s(math.pi * e), kick=0.7 * e)
            p["L"] = p["R"] = ("fk", 150 + 20 * s(t * 40), 30)
            p["emo"] = "shocked"
            fx.add("exclaim")
        elif t < 0.45:                                    # falls flat on the back
            e = _sm((t - 0.22) / 0.23)
            p.update(rot=28 + 62 * e, piv=-450, tx=120, ty=LIE * e * e, kick=0.7 * (1 - e))
            p["L"] = p["R"] = ("fk", 150, 30)
            p["emo"] = "shocked"
        else:                                             # lying there, seeing stars
            b = max(0.0, 1 - (t - 0.45) / 0.25)
            p.update(rot=90 - 4 * b * s((t - 0.45) * 40), piv=-450, tx=120, ty=LIE - 20 * b)
            p["L"], p["R"] = ("fk", 40, 20), ("fk", 70, 10)
            p["eyes"] = "spiral"
            fx.add("dizzy")
            if t < 0.75:
                fx.add("impact")
    elif action == "fall_face":
        if t < 0.18:                                      # trips: leans forward, arms out
            e = _sm(t / 0.18)
            p.update(rot=-25 * e, piv=-450, kick=0.0)
            p["L"] = p["R"] = ("fk", 110, 20)
            p["emo"] = "shocked"
            fx.add("exclaim")
        elif t < 0.4:
            e = _sm((t - 0.18) / 0.22)
            p.update(rot=-25 - 65 * e, piv=-450, ty=LIE * e * e)
            p["L"] = p["R"] = ("fk", 140, 10)
            p["emo"] = "shocked"
        else:
            b = max(0.0, 1 - (t - 0.4) / 0.25)
            p.update(rot=-90 + 4 * b * s((t - 0.4) * 40), piv=-450, ty=LIE - 20 * b)
            p["L"] = p["R"] = ("fk", 150, 0)
            p["eyes"] = "spiral"
            fx.add("dizzy")
            if t < 0.7:
                fx.add("impact")
    elif action == "get_up":
        e = _sm(t / 0.7)
        p.update(rot=90 * (1 - e), piv=-450, ty=LIE * (1 - e) ** 2)
        if e >= 1:                                        # shakes it off
            p["dx"] = 6 * s(t * 30) * max(0.0, 1 - (t - 0.7) / 0.4)
        p["L"], p["R"] = ("fk", 40 + 50 * (1 - e), 30), ("fk", 40 + 50 * (1 - e), 30)
        if t < 0.5:
            p["eyes"] = "spiral"
            fx.add("dizzy")
    elif action == "fly_away":
        if t < 0.12:                                      # the hit: squashed
            p.update(sq=(1.18, 0.82))
            p["emo"] = "shocked"
            fx.add("impact")
        else:
            u = t - 0.12
            p.update(move=(-1700 * u ** 1.2, -1100 * u + 500 * u * u), rot=760 * u, piv=-520)
            p["L"] = p["R"] = ("fk", 160, 20)
            p["kick"] = 0.8
            p["eyes"] = "x"
            fx.add("speed")
    elif action == "hit_head":
        if t < 0.1:
            p.update(sq=(1.2, 0.78))
            fx.add("impact")
        elif t < 0.4:
            e = (t - 0.1) / 0.3
            k = 1 + 0.12 * math.exp(-e * 4) * s(e * 18)
            p.update(sq=(2 - k, k))
        else:
            p.update(rot=7 * s(t * 6), piv=-20)
            p["dx"] = 10 * s(t * 3)
        p["eyes"] = "spiral" if t >= 0.1 else "closed"
        p["L"] = p["R"] = ("fk", 25, 15)
        fx.add("dizzy")
    elif action == "freeze":
        j = -40 * math.exp(-t * 9) * abs(s(t * 30))
        p.update(dy=j, dx=4 * s(t * 70))
        p["L"] = p["R"] = ("fk", 55, -2)
        p["emo"] = "shocked"
        fx |= {"exclaim", "shiver"}
    elif action == "double_take":
        if t < 0.55:                                      # sees it, calmly looks away
            p["eyes_dir"] = 0.0 if t < 0.25 else -1.0
            p["head_dx"] = 0 if t < 0.25 else -14
            p["emo"] = "neutral"
        elif t < 0.75:
            p["eyes_dir"] = 1.0
            p["head_dx"] = 14
            p["emo"] = "neutral"
        else:                                             # ...WHAT?! jumps, eyes pop out
            u = t - 0.75
            p["dy"] = -90 * math.exp(-u * 7) * abs(s(u * 14))
            p["L"] = p["R"] = ("fk", 70, 80)
            p["emo"] = "shocked"
            fx.add("exclaim")
            if u < 0.9:
                fx.add("eyes_pop")
    elif action == "faint":
        if t < 0.5:                                       # sways, eyes rolling
            p.update(rot=8 * s(t * 9), piv=-20)
            p["eyes"] = "spiral"
            p["L"] = p["R"] = ("fk", 20, -5)
        elif t < 0.9:                                     # falls back, stiff as a plank
            e = _sm((t - 0.5) / 0.4)
            p.update(rot=90 * e * e, piv=-450, ty=LIE * e ** 3)
            p["eyes"] = "x"
            p["L"] = p["R"] = ("fk", 8, 0)
        else:
            b = max(0.0, 1 - (t - 0.9) / 0.25)
            p.update(rot=90 - 3 * b * s((t - 0.9) * 40), piv=-450, ty=LIE - 16 * b)
            p["eyes"] = "x"
            p["L"] = p["R"] = ("fk", 8, 0)
            p["kick"] = 0.0
        if emotion == "sleepy":                           # dozes off and topples over, still asleep
            p["eyes"] = "closed"
            fx.add("snore")
        else:
            p["emo"] = "shocked"
    elif action == "lie_sleep":                           # asleep on the floor: breathing, snot bubble
        p.update(rot=90, piv=-450, ty=LIE)
        p["L"] = p["R"] = ("ik", 30, -560 + 8 * s(t * 1.6))
        p["kick"] = 0.15
        p["emo"] = "sleepy"
        p["eyes"] = "closed"
        fx.add("snore")
    elif action == "sleep_stand":                         # nods off standing up, swaying
        p.update(rot=5 * s(t * 1.4), piv=-20)
        p["head_dy"] = 18
        p["crouch"] = 0.15
        p["L"] = p["R"] = ("fk", 10, -4)
        p["emo"] = "sleepy"
        p["eyes"] = "closed"
        fx.add("snore")
    elif action == "wake_jolt":                           # from lying asleep: shoots up, eyes popping
        e = _sm(t / 0.22)
        p.update(rot=90 * (1 - e), piv=-450, ty=LIE * (1 - e) ** 2)
        if t >= 0.22:
            u = t - 0.22
            p["dy"] = -140 * math.exp(-u * 5) * abs(s(u * 9))
        p["L"] = p["R"] = ("fk", 150, 20)
        p["emo"] = "shocked"
        fx.add("exclaim")
        if t < 1.0:
            fx.add("eyes_pop")
    elif action == "poke":                                # poke ... poke ... poke
        u = (t % 0.5) / 0.5
        jab = max(0.0, s(math.pi * min(1.0, u * 2)))
        p["R"] = ("fk", 88, -2)
        p["L"] = HIP_L
        p["dx"] = 26 * jab
        p["eyes_dir"] = 0.6
    elif action == "shake_awake":                         # grabs the shoulders and shakes
        p["L"] = p["R"] = ("fk", 84, -4)
        p["dx"] = 16 * s(t * 26)
        p["emo"] = p.get("emo") or emotion
    elif action == "disappointed":                        # slumps: head down, arms dangling, rain cloud
        e = _sm(t / 0.5)
        p.update(rot=-7 * e, piv=-20)
        p["head_dy"] = 26 * e
        p["crouch"] = 0.22 * e
        p["L"] = p["R"] = ("fk", 4, 0)
        p["emo"] = "sad"
        fx.add("rain_cloud")
    elif action == "fight_cloud":
        p["cloud"] = True
        fx.add("cloud")
    elif action == "crash_wall":
        if t < 0.4:                                       # runs at the wall
            p.update(move=(260 * t / 0.4, 0), rot=-12)
            p["walk"] = t * 4
            p["L"] = ("fk", 60 + 50 * s(t * 30), 60)
            p["R"] = ("fk", 60 - 50 * s(t * 30), 60)
            p["emo"] = "excited"
            fx |= {"speed", "dust"}
        elif t < 0.95:                                    # SPLAT: flat against it
            p.update(move=(260, 0), sq=(0.55, 1.04))
            p["L"] = p["R"] = ("fk", 90, 0)
            p["eyes"] = "x"
            if t < 0.7:
                fx.add("impact")
        else:                                             # peels off, falls back
            e = _sm((t - 0.95) / 0.4)
            p.update(move=(260 - 60 * e, 0), rot=90 * e * e, piv=-450, ty=LIE * e ** 3)
            p["eyes"] = "spiral"
            fx.add("dizzy")
    elif action == "dizzy":
        p.update(rot=7 * s(t * 5), piv=-20)
        p["dx"] = 14 * s(t * 2.5)
        p["eyes"] = "spiral"
        p["L"], p["R"] = ("fk", 40 + 10 * s(t * 4), 30), ("fk", 40 - 10 * s(t * 4), 30)
        fx.add("dizzy")
    elif action == "shiver":
        p["dx"] = 5 * s(t * 55)
        p["L"] = ("ik", -50, -640)
        p["R"] = ("ik", -40, -660)
        p["emo"] = "scared"
        fx |= {"shiver", "sweat"}
    elif action == "cartoon_run":
        p["walk"] = t * 4
        p["rot"], p["piv"] = -12, -20
        p["L"] = ("fk", 60 + 50 * s(t * 30), 60)
        p["R"] = ("fk", 60 - 50 * s(t * 30), 60)
        p["dy"] = -10 * abs(s(t * 30))
        fx |= {"speed", "dust"}
    elif action == "tiptoe":
        p["walk"] = t * 0.45
        p["crouch"] = 0.55
        p["tiptoe"] = True
        p["L"] = ("fk", 75, 70 + 6 * s(t * 3))
        p["R"] = ("fk", 85, 60 + 6 * s(t * 3 + 1))
        p["eyes_dir"] = s(t * 1.6)
        p["dy"] = -8 * abs(s(t * 3.6))
    elif action == "laugh_floor":
        p.update(rot=90 + 16 * s(t * 7), piv=-450, ty=LIE)
        p["L"] = p["R"] = ("ik", 40, -560)
        p["kick"] = 0.4 + 0.3 * abs(s(t * 7))
        p["emo"] = "laughing"
    elif action == "kick":
        if t < 0.2:
            p["kick"] = -0.3 * _sm(t / 0.2)
        elif t < 0.38:
            p["kick"] = -0.3 + 1.3 * _sm((t - 0.2) / 0.18)
            if t < 0.3:
                fx.add("speed")
        else:
            p["kick"] = max(0.0, 1.0 - (t - 0.38) / 0.4)
            if t < 0.6:
                fx.add("impact_foot")
        p["L"], p["R"] = ("fk", 60, 40), ("fk", 40, 30)
        p["rot"], p["piv"] = 8 * max(0.0, p["kick"]), -20
        p["emo"] = "angry"
    elif action == "jaw_drop":
        p["emo"] = "shocked"
        p["jaw"] = min(1.0, t / 0.2)
        fx.add("eyes_pop")
        p["L"] = p["R"] = ("fk", 12, -6)
    p["fx"] = set(p.get("fx", ())) | fx


def impact_times(sched) -> list:
    """When a slapstick move lands (a small camera shake)."""
    at = {"slip_fall": 0.45, "fall_face": 0.4, "fly_away": 0.03, "hit_head": 0.03, "faint": 0.9, "crash_wall": 0.4,
          "kick": 0.32}
    out = []
    for sc in sched:
        for ln in sc.lines:
            for a in (ln.action, getattr(ln, "actor_action", "")):
                if a in at and ln.start + at[a] < ln.end + 0.6:
                    out.append(ln.start + at[a])
    return sorted(out)


# sounds that go with each move: (seconds after the line starts, sound, volume)
MOVE_SOUNDS = {
    "slip_fall": ((0.0, "slip", 0.9), (0.44, "thud", 1.0), (0.6, "tweet", 0.55)),
    "fall_face": ((0.0, "slide_down", 0.6), (0.38, "thud", 1.0), (0.55, "tweet", 0.5)),
    "get_up": ((0.0, "slide_up", 0.5),),
    "fly_away": ((0.0, "punch", 1.0), (0.1, "slide_up", 0.7), (0.15, "whoosh", 0.7)),
    "hit_head": ((0.0, "bonk", 1.0), (0.3, "tweet", 0.6)),
    "freeze": ((0.0, "dun_dun", 0.7),),
    "double_take": ((0.72, "spring", 0.9), (0.76, "awooga", 0.7)),
    "faint": ((0.2, "slide_down", 0.8), (0.88, "thud", 1.0)),
    "fight_cloud": ((0.0, "fight", 1.0),),
    "crash_wall": ((0.0, "zip", 0.8), (0.4, "crash", 1.0), (0.95, "slide_down", 0.6)),
    "run_across": ((0.0, "zip", 0.9),),
    "chase": ((0.3, "zip", 0.7),),
    "cartoon_run": ((0.0, "zip", 0.7),),
    "sneak_in": ((0.0, "tiptoe", 0.8),),
    "tiptoe": ((0.0, "tiptoe", 0.8),),
    "kick": ((0.2, "whoosh", 0.6), (0.32, "punch", 1.0)),
    "jaw_drop": ((0.0, "awooga", 0.9),),
    "lie_sleep": ((0.1, "snore", 0.7), (2.1, "snore", 0.7), (4.1, "snore", 0.7)),
    "sleep_stand": ((0.3, "snore", 0.7), (2.3, "snore", 0.7), (4.3, "snore", 0.7)),
    "wake_jolt": ((0.0, "spring", 0.9), (0.05, "awooga", 0.7)),
    "poke": ((0.14, "boop", 0.9), (0.64, "boop", 0.9), (1.14, "boop", 0.9), (1.64, "boop", 0.9), (2.14, "boop", 0.9)),
    "shake_awake": ((0.0, "boing", 0.6),),
    "disappointed": ((0.0, "wah_wah", 0.9),),
}
EFFECT_SOUNDS = {"alarm": "alarm", "fly": "buzz"}     # a line's effect that makes a sound


def sound_events(sched) -> list:
    out = []
    for sc in sched:
        for ln in sc.lines:
            for a in {ln.action, getattr(ln, "actor_action", "")}:
                for dt, snd, vol in MOVE_SOUNDS.get(a, ()):
                    if ln.start + dt < ln.end + 0.3:
                        out.append((ln.start + dt, snd, vol))
            if getattr(ln, "effect", "") in EFFECT_SOUNDS:
                out.append((ln.start + 0.02, EFFECT_SOUNDS[ln.effect], 0.8))
    return out


# ------------------------------------------------------------------ drawing helpers
def _star(pen, cx, cy, r, fill, n=5, inner=0.45, rot=0.0, ol=4):
    pts = []
    for i in range(n * 2):
        a = rot - math.pi / 2 + math.pi * i / n
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pen.poly(pts, fill, ol)


def _heart(pen, cx, cy, r, fill):
    pen.circle(cx - r * 0.5, cy - r * 0.2, r * 0.55, fill, 0)
    pen.circle(cx + r * 0.5, cy - r * 0.2, r * 0.55, fill, 0)
    pen.poly([(cx - r * 1.02, cy - 0.05 * r), (cx + r * 1.02, cy - 0.05 * r), (cx, cy + r * 1.05)], fill, 0)


def _puff(pen, cx, cy, r, fill, ol=4):
    for dx, dy, k in ((-0.55, 0.1, 0.62), (0.55, 0.1, 0.62), (0, -0.25, 0.75), (-0.2, 0.25, 0.6), (0.25, 0.28, 0.6)):
        pen.circle(cx + dx * r, cy + dy * r, k * r, fill, ol)
    for dx, dy, k in ((-0.55, 0.1, 0.62), (0.55, 0.1, 0.62), (0, -0.25, 0.75), (-0.2, 0.25, 0.6), (0.25, 0.28, 0.6)):
        pen.circle(cx + dx * r, cy + dy * r, k * r - 5, fill, 0)


def cartoon_fx(pen, fxs, hx, hy, r, t, color=(30, 30, 34), feet_y=0.0):
    """The cartoon effects around a character (character units; the character faces +x)."""
    from .flat import OUT
    s = math.sin
    if "speed" in fxs:
        for i in range(6):
            y = -1050 + i * 170 + 20 * s(i * 2.1)
            ph = (t * 6 + i * 0.37) % 1.0
            x0 = -240 - 80 * ph
            ln = 220 + 140 * ((i * 37) % 5) / 5
            pen.line([(x0, y), (x0 - ln, y)], (90, 90, 100), 9)
    if "dust" in fxs:
        for i in range(3):
            ph = (t * 2.2 + i / 3) % 1.0
            pen.circle(-130 - 260 * ph, feet_y - 50 - 40 * ph, 40 + 50 * ph, (205, 196, 180), 3, (150, 140, 128))
    if "shiver" in fxs:
        for side in (-1, 1):
            for j in range(3):
                x = side * (190 + j * 40) + 6 * s(t * 50 + j)
                y = -760 + j * 150
                pen.arc(x - 30, y - 60, x + 30, y + 60, 300 if side > 0 else 120, 60 if side > 0 else 240, 7)
    if "dizzy" in fxs:
        cy = hy - r - 25
        for i in range(3):
            a = t * 4.5 + i * 2 * math.pi / 3
            x, y = hx + 170 * math.cos(a), cy + 42 * math.sin(a)
            _star(pen, x, y, 30, (255, 214, 50), rot=t * 3)
    if "impact" in fxs:
        k = 1 + 0.15 * s(t * 30)
        cx, cy = hx + r * 0.9, hy - r * 0.8
        _star(pen, cx, cy, 130 * k, (255, 220, 40), n=10, inner=0.55, rot=0.2)
        _star(pen, cx, cy, 70 * k, (255, 255, 255), n=8, inner=0.55, rot=0.5, ol=0)
    if "impact_foot" in fxs:
        _star(pen, 380, -420, 110, (255, 220, 40), n=10, inner=0.55, rot=0.2)
        _star(pen, 380, -420, 58, (255, 255, 255), n=8, inner=0.55, rot=0.5, ol=0)
    if "sweat" in fxs:
        for i in range(4):
            ph = (t * 1.8 + i / 4) % 1.0
            side = 1 if i % 2 else -1
            x = hx + side * (r * 0.9 + 140 * ph)
            y = hy - r * 0.7 - 120 * ph + 260 * ph * ph
            pen.circle(x, y, 15, (150, 205, 245), 3, (60, 120, 190))
    if "exclaim" in fxs:
        b = -18 * abs(s(t * 8))
        top = hy - r - 260 + b
        pen.poly([(hx - 22, top), (hx + 22, top), (hx + 12, top + 140), (hx - 12, top + 140)], (230, 40, 40), 5)
        pen.circle(hx, top + 182, 18, (230, 40, 40), 5)
    if "question" in fxs:
        b = -14 * abs(s(t * 5))
        top = hy - r - 270 + b
        pen.arc(hx - 60, top, hx + 60, top + 120, 180, 90, 34, OUT)
        pen.arc(hx - 60, top, hx + 60, top + 120, 180, 90, 22, (60, 120, 230))
        pen.line([(hx, top + 120), (hx, top + 160)], OUT, 34)
        pen.line([(hx, top + 120), (hx, top + 160)], (60, 120, 230), 22)
        pen.circle(hx, top + 210, 20, (60, 120, 230), 5)
    if "steam" in fxs:
        for side in (-1, 1):
            for i in range(3):
                ph = (t * 1.6 + i / 3) % 1.0
                pen.circle(hx + side * (r + 30 + 70 * ph), hy - 20 - 160 * ph, 24 + 40 * ph, (246, 246, 246), 3,
                           (170, 170, 180))
    if "hearts" in fxs:
        for i in range(3):
            ph = (t * 0.7 + i / 3) % 1.0
            _heart(pen, hx + (i - 1) * 130 + 25 * s(t * 3 + i), hy - r - 40 - 260 * ph, 34 * (1 - 0.4 * ph),
                   (232, 50, 80))
    if "rain_cloud" in fxs:
        cy = hy - r - 230
        for i in range(7):
            ph = (t * 2.4 + i * 0.29) % 1.0
            x = hx - 130 + i * 44
            pen.line([(x, cy + 60 + 200 * ph), (x - 8, cy + 100 + 200 * ph)], (90, 150, 230), 7)
        _puff(pen, hx, cy, 170, (150, 156, 170))
    if "idea" in fxs:
        cy = hy - r - 200 - 10 * abs(s(t * 4))
        for i in range(8):
            a = i * math.pi / 4 + 0.2
            pen.line([(hx + 95 * math.cos(a), cy + 95 * math.sin(a)), (hx + 135 * math.cos(a), cy + 135 * math.sin(a))],
                     (255, 196, 40), 9)
        pen.circle(hx, cy, 62, (255, 236, 110), 5)
        pen.d.rectangle(pen.box(hx - 26, cy + 56, hx + 26, cy + 96), fill=(150, 150, 160), outline=OUT,
                        width=pen.wd(4))
    if "sparkle" in fxs:
        for i in range(4):
            ph = (t * 1.3 + i / 4) % 1.0
            k = s(math.pi * ph)
            x, y = hx + (-220, 230, -170, 200)[i], hy + (-120, -60, 260, 360)[i]
            _star(pen, x, y, 40 * k + 1, (255, 240, 140), n=4, inner=0.3, ol=3)
    if "snore" in fxs:                                     # a snot bubble growing and shrinking at the nose
        g = 0.5 + 0.5 * s(t * 1.6)
        rr = 8 + 34 * g
        pen.circle(hx + 64 + rr * 0.6, hy + 40, rr, (200, 230, 250), 3, (110, 160, 200))
        pen.circle(hx + 64 + rr * 0.35, hy + 40 - rr * 0.4, rr * 0.22, (255, 255, 255), 0)
        for k in range(2):                                 # z z
            ph = (t * 0.5 + k / 2) % 1.0
            x, y, z = hx + r * 0.7 + 70 * ph, hy - r - 60 - 120 * ph, 12 + 10 * ph
            pen.line([(x - z, y - z), (x + z, y - z), (x - z, y + z), (x + z, y + z)], (60, 60, 90), 6)
    if "fly" in fxs:                                       # a fly buzzing in loops around the head
        a = t * 5.5
        x, y = hx + 190 * math.sin(a), hy - 40 + 90 * math.sin(2 * a)
        for k in range(1, 7):                              # dotted trail
            b = a - k * 0.12
            pen.circle(hx + 190 * math.sin(b), hy - 40 + 90 * math.sin(2 * b), 3, (90, 90, 100), 0)
        flap = 12 * abs(s(t * 60))
        pen.ellipse(x - 22, y - 26 - flap, x + 2, y - 6, (220, 236, 250), 2)
        pen.ellipse(x - 2, y - 26 - flap, x + 22, y - 6, (220, 236, 250), 2)
        pen.circle(x, y, 13, (30, 30, 34), 0)
    if "cloud" in fxs:                                     # the fight: a dust cloud with fists, feet and stars
        rnd = random.Random(int(t * 9))
        for _ in range(4):                                  # arms and legs poking out
            a = rnd.uniform(0, 2 * math.pi)
            x0, y0 = 300 * math.cos(a), -560 + 260 * math.sin(a)
            x1, y1 = 470 * math.cos(a), -560 + 400 * math.sin(a)
            pen.line([(x0, y0), (x1, y1)], color, 24)
            pen.circle(x1, y1, 26, color, 0)
        for i in range(9):
            a = i * 2 * math.pi / 9 + t * 3
            jx, jy = rnd.uniform(-30, 30), rnd.uniform(-30, 30)
            pen.circle(260 * math.cos(a) + jx, -560 + 230 * math.sin(a) + jy, 150, (226, 220, 206), 5, (120, 112, 100))
        pen.circle(0, -560, 260, (226, 220, 206), 0)
        for i in range(3):
            _star(pen, rnd.uniform(-220, 220), rnd.uniform(-800, -320), rnd.uniform(28, 46), (255, 214, 50),
                  rot=rnd.uniform(0, 3))
        if rnd.random() < 0.5:
            _star(pen, rnd.uniform(-150, 150), rnd.uniform(-700, -420), 90, (255, 240, 120), n=9, inner=0.55)


def eye_extra(pen, x, y, kind, t, color=(28, 24, 24)):
    """Comedy eyes: spiral (dizzy) and X (knocked out). Returns False for any other kind."""
    if kind == "spiral":
        pts = []
        for i in range(40):
            a = i * 0.45 + t * 9
            rr = 2 + i * 0.5
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        pen.line(pts, color, 4.5)
        return True
    if kind == "x":
        pen.line([(x - 14, y - 14), (x + 14, y + 14)], color, 7)
        pen.line([(x - 14, y + 14), (x + 14, y - 14)], color, 7)
        return True
    return False


def eyes_pop(pen, fx_, ey, t):
    """Eyeballs shooting out on springs."""
    from .flat import OUT
    ext = 110 + 30 * math.sin(t * 22) * math.exp(-t * 2)
    for side in (-1, 1):
        x0 = fx_ + side * 42
        x1, y1 = x0 + side * 30 + 20, ey - ext
        pts = [(x0 + (x1 - x0) * i / 10 + (12 if i % 2 else -12), ey + (y1 - ey) * i / 10) for i in range(11)]
        pen.line(pts, OUT, 5)
        pen.circle(x1, y1, 46, (255, 255, 255), 5)
        pen.circle(x1 + 6, y1 + 4, 18, (28, 24, 24), 0)
        pen.line([(x1 - 30, y1 + 10), (x1 - 12, y1 + 22)], (220, 60, 60), 3)


# ------------------------------------------------------------------ the stickman
def draw_stick(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t):
    from .flat import Pen, _brows, _cycle, _effects, _eye, _face_cfg, _fk, _ik, _mouth, _prop, _scaled, OUT
    C = sp.get("color", (30, 30, 34))
    bw = sp.get("build", 1.0)
    LW = 26 * (0.85 + 0.15 * bw) * (1 + 0.6 * max(0.0, bw - 1))
    head_fill = sp.get("head", (255, 255, 255))
    acc = sp.get("accent", (230, 60, 60))
    back = view == "back"
    fxs = set(pose.get("fx", ()))
    if pose.get("cloud"):                                  # fighting inside the dust cloud: only the cloud shows
        cartoon_fx(Pen(im, ox, oy, s), fxs, 0, -905, 135, t, C)
        return
    if pose.get("cycle") and not back:
        _cycle(Pen(im, ox + pose["dx"] * s, oy, s), 300, -1, t, 0.0, sp.get("cycle_color", (214, 60, 52)))
    if pose.get("ride") is not None:
        _cycle(Pen(im, ox + pose["dx"] * s, oy, s), 0, 1, t, pose["ride"] * 7, sp.get("cycle_color", (214, 60, 52)))
    U = 120 * pose.get("crouch", 0.0)                       # knees bent: the upper body comes down
    pen = Pen(im, ox + pose["dx"] * s, oy + pose["dy"] * s, s)            # legs (feet on the ground)
    up = Pen(im, ox + pose["dx"] * s, oy + (pose["dy"] + U) * s, s)        # body, arms and head
    hx, hy, r = pose["head_dx"] * 0.8, -905 + pose["head_dy"], 135
    hip = (0, -400 + U)

    # legs
    wk = pose["walk"]
    sit = pose.get("sit")
    kick = pose.get("kick", 0.0)
    feet = []
    if sit:                                                # a simple stool under them
        pen.d.rounded_rectangle(pen.box(-130, -400 + U + 20, 120, -370 + U + 40), radius=8 * s, fill=(196, 140, 84),
                                outline=OUT, width=pen.wd(4))
        for lx in (-110, 90):
            pen.line([(lx, -340 + U), (lx + 10 * (1 if lx > 0 else -1), -10)], (140, 96, 56), 14)
    for side in (-1, 1):
        if pose.get("ride") is not None:
            a = pose["ride"] * 7 * 1.4 + (0 if side > 0 else math.pi)
            foot = (10 + 46 * math.cos(a), -130 + 46 * math.sin(a) - pose["dy"])
            h0 = (side * 8, -300)
        elif sit:
            h0 = (side * 8, hip[1])
            foot = (side * 8 + 210, -14)
        elif side > 0 and kick:
            h0 = (6, hip[1])
            a = math.radians(-8 + 100 * kick)
            foot = (h0[0] + 395 * math.sin(a), h0[1] + 395 * math.cos(a))
        else:
            h0 = (side * 8, hip[1])
            ph = wk * 8
            fx_ = side * 45 + (150 * math.sin(ph) * side if wk else 0)
            lift = 50 * max(0.0, math.cos(ph) * side) if wk else 0
            foot = (fx_, -14 - lift - (24 if pose.get("tiptoe") else 0))
            if pose.get("dy", 0) < -20 and not wk:         # in the air: knees tucked
                foot = (side * 40 + 30, -60)
        knee, foot = _ik(h0[0], h0[1], foot[0], foot[1], 197, 196, 1)
        pen.line([h0, knee, foot], C, LW)
        feet.append(foot)
        fy = foot[1]
        if pose.get("tiptoe"):
            pen.ellipse(foot[0] - 6, fy - 12, foot[0] + 34, fy + 10, C, 0)
        else:
            pen.ellipse(foot[0] - 12, fy - 13, foot[0] + 46, fy + 13, C, 0)

    # body, skirt, tie
    neck = (hx * 0.3, -768)
    up.line([neck, hip], C, LW)
    if sp.get("skirt") and not sit:
        up.poly([(0, -560), (105, -320), (-105, -320)], acc, 5, C)
    if sp.get("tie") and not back:
        up.poly([(neck[0] - 16, -752), (neck[0] + 16, -752), (neck[0] + 26, -560), (neck[0], -520),
                 (neck[0] - 26, -560)], acc, 4, C)

    # head and face
    def _head():
        if sp.get("hair") == "spiky":                      # spikes behind the head
            for i in range(6):
                a = math.pi * (1.08 + 0.84 * i / 5)
                ca, sa = math.cos(a), math.sin(a)
                tip = (hx + (r + 70) * ca, hy + (r + 70) * sa)
                b1 = (hx + (r - 20) * math.cos(a - 0.26), hy + (r - 20) * math.sin(a - 0.26))
                b2 = (hx + (r - 20) * math.cos(a + 0.26), hy + (r - 20) * math.sin(a + 0.26))
                up.poly([b1, tip, b2], C, 0)
        up.circle(hx, hy, r, head_fill, 9, C)
        hair = sp.get("hair")
        if hair == "tuft":
            for dx, a in ((-30, -0.35), (0, 0.0), (30, 0.35)):
                x0, y0 = hx + dx * 0.6, hy - r + 4
                up.line([(x0, y0), (x0 + 60 * math.sin(a) + 14, y0 - 60 * math.cos(a))], C, 9)
        elif hair == "spiky":                           # drawn behind the head (see below)
            pass
        elif hair == "messy":
            for i in range(6):
                a = math.pi * (1.15 + 0.7 * i / 5)
                x0, y0 = hx + (r - 4) * math.cos(a), hy + (r - 4) * math.sin(a)
                up.arc(x0 - 26, y0 - 40, x0 + 26, y0 + 12, 180, 330, 8, C)
        if sp.get("band") and not back:                    # headband with tails
            up.arc(hx - r, hy - r, hx + r, hy + r, 200, 340, 22, acc)
            up.line([(hx - r * 0.95, hy - 40), (hx - r - 70, hy - 10)], acc, 16)
            up.line([(hx - r * 0.95, hy - 40), (hx - r - 60, hy + 40)], acc, 16)
        if sp.get("cap"):                                  # cap worn backwards
            up.pie(hx - r * 0.98, hy - r * 1.04, hx + r * 0.98, hy + r * 0.6, 180, 360, acc, 6)
            up.poly([(hx - r * 0.9, hy - r * 0.32), (hx - r * 1.45, hy - r * 0.2), (hx - r * 1.4, hy - r * 0.05),
                     (hx - r * 0.85, hy - r * 0.14)], acc, 5)
        if sp.get("bow"):
            bx, by = hx + r * 0.62, hy - r * 0.86
            for side in (-1, 1):
                up.poly([(bx, by), (bx + side * 70, by - 46), (bx + side * 70, by + 46)], acc, 5)
            up.circle(bx, by, 18, acc, 5)
        if back:
            return
        cfg = _face_cfg(pose.get("emo") or emotion)
        if pose.get("eyes"):
            cfg["eyes"] = pose["eyes"]
        look = pose.get("eyes_dir", 0.0)
        fx_, ey = hx + 10, hy - 6
        for side in (-1, 1):
            ex = fx_ + side * 48
            q = _scaled(up, ex, ey, 1.5)
            if "eyes_pop" in fxs:
                q.circle(ex, ey, 14, (40, 30, 30), 0)
            elif not eye_extra(q, ex, ey, cfg["eyes"], t):
                _eye(q, ex, ey, cfg["eyes"], blink, look)
            if sp.get("lashes") and cfg["eyes"] in ("open", "up", "wide", "half"):
                for k in (-1, 0, 1):
                    up.line([(ex + k * 9, ey - 20), (ex + k * 14, ey - 34)], OUT, 4)
        _brows(_scaled(up, fx_, ey - 44, 1.05), fx_, ey - 44 - (8 if cfg["eyes"] == "wide" else 0), cfg["brow"])
        if sp.get("glasses"):
            for side in (-1, 1):
                up.circle(fx_ + side * 46, ey, 40, None, 6, (40, 40, 48))
            up.line([(fx_ - 8, ey - 4), (fx_ + 8, ey - 4)], (40, 40, 48), 6)
        m = pose["chew"] if pose.get("chew") is not None and mouth < 0.05 else mouth
        jaw = pose.get("jaw", 0.0)
        if jaw:                                            # jaw drop: a huge open mouth with a tongue
            h = 30 + 90 * jaw
            up.ellipse(fx_ - 46, hy + 40, fx_ + 46, hy + 40 + h, (110, 26, 34), 5)
            up.ellipse(fx_ - 26, hy + 40 + h * 0.55, fx_ + 26, hy + 40 + h * 0.95, (232, 110, 120), 0)
        else:
            _mouth(_scaled(up, fx_, hy + 66, 1.1), fx_, hy + 66, cfg["mouth"], m, t)
        if sp.get("mustache"):
            up.poly([(fx_ - 46, hy + 50), (fx_ - 26, hy + 34), (fx_, hy + 40), (fx_ + 26, hy + 34), (fx_ + 46, hy + 50),
                     (fx_ + 26, hy + 48), (fx_, hy + 52), (fx_ - 26, hy + 48)], C, 0)
        _effects(up, cfg["fx"], fx_, hy, r, t)
        if "eyes_pop" in fxs:
            eyes_pop(up, fx_, ey, t)

    # arms
    def _arms():
        hands = {}
        for side, key in ((-1, "L"), (1, "R")):
            spec = pose[key]
            sx, sy = side * 14, -735
            if spec[0] in ("ik", "ikd"):
                elbow, hand = _ik(sx, sy, side * spec[1], spec[2] + 10, 155, 150, side, down=spec[0] == "ikd")
            else:                                          # a raised arm goes out to the side, clear of the head
                a_ = max(24, spec[1]) if spec[1] <= 95 else 95 + (spec[1] - 95) * 0.5
                elbow, hand = _fk(sx, sy, a_, spec[2], 170, 160, side)
            up.line([(sx, sy), elbow, hand], C, LW)
            up.circle(hand[0], hand[1], 19, C, 0)
            hands[key] = hand
            if key == "R" and (sp.get("holds") == "lathi" or pose.get("lathi")) and not pose["prop"]:
                from .flat import _lathi
                _lathi(up, elbow, hand)
            if key == "R" and not back and pose["prop"]:
                _prop(up, pose["prop"], hand, hands.get("L"), C, pose.get("bite", 0))

    # arms go behind the big head, unless a hand reaches the face (eating, facepalm, phone at the ear...)
    to_face = any(pose[k][0] in ("ik", "ikd") and pose[k][2] < -760 for k in ("L", "R"))
    if pose.get("arms_behind") or not to_face:
        _arms()
        _head()
    else:
        _head()
        _arms()
    if pose.get("bag") and not back:
        up.line([(-20, -760), (90, -470)], (110, 70, 40), 12)
        up.d.rounded_rectangle(up.box(-150, -520, -50, -410), radius=12 * up.s, fill=(150, 96, 56), outline=OUT,
                               width=up.wd(4))
    cartoon_fx(up, fxs, hx, hy, r, t, C, feet_y=-U)


def draw_wall(im, x, ground, k, face):
    """A brick wall standing on the ground at frame pixel x (its front side), going away from the character."""
    from PIL import ImageDraw
    from .flat import OUT
    d = ImageDraw.Draw(im)
    w, h = 120 * k, 1350 * k
    x0, x1 = (x, x + w) if face > 0 else (x - w, x)
    top = ground - h
    d.rectangle([x0, top, x1, ground], fill=(196, 96, 70), outline=OUT, width=max(1, round(5 * k)))
    bh = 70 * k
    row = 0
    y = ground - bh
    while y > top:
        d.line([(x0, y), (x1, y)], fill=(150, 66, 48), width=max(1, round(4 * k)))
        bx = x0 + (w / 2 if row % 2 else 0)
        if x0 < bx < x1:
            d.line([(bx, y), (bx, y + bh)], fill=(150, 66, 48), width=max(1, round(4 * k)))
        y -= bh
        row += 1


def draw_alarm(im, x, ground, k, t):
    """An alarm clock on the floor at frame pixel x, ringing: it shakes and hops, with ring lines."""
    from .flat import OUT, Pen
    hop = abs(math.sin(t * 22)) * 10
    pen = Pen(im, x, ground - hop * k, k)
    w = 7 * math.sin(t * 44)
    for side in (-1, 1):                                    # bells
        pen.pie(side * 52 - 30 + w, -230, side * 52 + 30 + w, -170, 180, 360, (230, 60, 60), 4)
    pen.line([(-46 + w, -150), (46 + w, -150)], OUT, 6)
    for side in (-1, 1):
        pen.line([(side * 40, -40), (side * 56, 0)], OUT, 9)  # legs
    pen.circle(w, -110, 82, (230, 60, 60), 5)
    pen.circle(w, -110, 64, (255, 255, 250), 4)
    pen.line([(w, -110), (w, -158)], OUT, 6)
    pen.line([(w, -110), (w + 34, -110)], OUT, 6)
    for i in range(3):                                      # ring lines
        for side in (-1, 1):
            rr = 110 + i * 34 + 10 * math.sin(t * 30)
            pen.arc(-rr, -110 - rr, rr, -110 + rr, (300 if side > 0 else 210), (330 if side > 0 else 240), 6)


def draw_peel(im, x, ground, k, face, t):
    """The banana peel that made them slip: under the front foot, then shooting out and landing."""
    from .flat import OUT, Pen
    if t < 0.12:
        px, py, rot = 140, 0, 0.0
    else:
        u = min(1.0, (t - 0.12) / 0.6)
        px, py, rot = 140 + 380 * u, -360 * 4 * u * (1 - u), 9 * u
    pen = Pen(im, x + face * px * k, ground + py * k, k)
    yel, dark = (250, 214, 70), (196, 150, 40)
    for i, a in enumerate((-0.9, 0.0, 0.9)):               # three flaps of peel
        aa = a + rot
        tip = (90 * math.sin(aa) + 40 * (i - 1), -10 - 60 * math.cos(aa) * 0.5)
        pen.poly([(-26, 0), tip, (26, 0)], yel, 4)
    pen.ellipse(-34, -22, 34, 6, yel, 4)
    pen.line([(-6, -18), (8, -34)], dark, 7)
