"""A rigged 2D character, drawn in the style of the character sheet.

The character is a tree of bones (hips -> torso -> head, torso -> arms,
hips -> legs). A *pose* is a dict of joint angles plus a few flags (sitting,
which prop is held, which hand shape). Actions (wave, drink tea, ...) are small
functions that turn time into a pose, and the renderer draws the skeleton with
outlined shapes (hoodie, jeans, sneakers, hair, glossy eyes, effect marks).

The shapes are drawn in code so the app works with no art files. To use your
own artwork later, replace the `_shapes(...)` calls in `draw_character` with
sprite drawing that rotates each part image around the same joint positions.

Angle convention: 0 points straight down, positive swings toward screen-right.
Local units are pixels at scale 1.0, origin at the feet, y pointing down.
"""
from __future__ import annotations

import json
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat

from .config import ASSETS_DIR

THIGH, SHIN, FOOT, FOOT_H = 122, 120, 46, 12
TORSO, NECK, HEAD_R = 200, 16, 74
SHOULDER_W, HIP_W, UA, FA = 46, 28, 104, 98
SEAT = SHIN + FOOT_H + 10          # hip height when sitting

# Layer box (world px) the character is drawn into, and where the feet sit in it.
BOX_W, BOX_H, ORG_X, ORG_Y = 800, 1120, 400, 1070

BASE = dict(hips_dx=0.0, hips_dy=0.0, torso=0.0, head=0.0,
            arm_l=-0.12, fore_l=0.10, arm_r=0.12, fore_r=-0.10,
            thigh_l=0.04, shin_l=0.0, thigh_r=-0.04, shin_r=0.0,
            look_x=0.0, look_y=0.0, ua_fs_l=1.0, ua_fs_r=1.0, sit=0, prop=None, bite=0, eyes_closed=0.0,
            mouth_force=0.0, z=0, hand_l="relaxed", hand_r="relaxed", fx=())

SIT_ACTIONS = {"sit", "sit_phone", "sit_tea", "sit_read", "sit_eat", "sit_sleep"}
# Activities the character keeps doing while someone else is talking.
PERSISTENT = SIT_ACTIONS | {"use_phone", "phone_call", "drink_tea", "read_book", "eat", "arms_crossed"}
# Actions that make sense while sitting; anything else falls back to talking.
SEATED_OK = SIT_ACTIONS | {"talk", "idle", "wave", "point", "think", "explain", "thumbs_up", "ok_sign", "stop",
                           "arms_crossed", "shrug", "look_around", "cheer", "clap", "facepalm", "use_phone", "phone_call",
                           "drink_tea", "read_book", "eat"}
KEEP_EMOTION = {"sleepy", "crying", "in_love", "bored", "scared", "proud", "disgusted"}


def _d(a: float) -> tuple[float, float]:
    return math.sin(a), math.cos(a)


def _lerp(a, b, t):
    return a + (b - a) * t


def _bump(x: float, up=0.25, top=0.45, hold=0.65, down=0.8) -> float:
    """0 -> 1 -> hold -> 0 over x in [0,1): the 'raise to mouth and lower' cycle."""
    if x < up:
        return 0.0
    if x < top:
        return (x - up) / (top - up)
    if x < hold:
        return 1.0
    if x < down:
        return 1 - (x - hold) / (down - hold)
    return 0.0


# --------------------------------------------------------------------------
# Poses and actions
# --------------------------------------------------------------------------
def pose_for(action: str | None, emotion: str, t: float, speaking: bool, phase: float,
             seated: bool = False) -> dict:
    p = dict(BASE)
    w = t + phase
    br = math.sin(w * 2.2)
    p["hips_dy"] = 3.0 * br
    p["torso"] = 0.012 * br
    p["arm_l"] += 0.02 * math.sin(w * 1.7)
    p["arm_r"] -= 0.02 * math.sin(w * 1.9)

    act = action or "talk"
    act = {"punch": "point", "slap": "wave"}.get(act, act)      # 3D-character actions, nearest gesture here
    if seated and act not in SEATED_OK:
        act = "talk"
    if act == "sit":
        act = "talk" if speaking else "idle"
    elif act.startswith("sit_"):
        act = {"phone": "use_phone", "tea": "drink_tea", "read": "read_book", "eat": "eat",
               "sleep": "sleep"}[act[4:]]
    if seated:
        p["sit"] = 1
        p["hips_dy"] = 1.5 * br
        p["shin_r"] = -0.10 * max(0.0, math.sin(w * 6)) if act in ("idle", "talk") and not speaking else 0.0

    free = act in ("talk", "idle")
    if speaking and act == "talk":
        p["arm_r"] = 0.55 + 0.35 * math.sin(w * 3.1)
        p["fore_r"] = -0.7 + 0.45 * math.sin(w * 4.3 + 1.0)
        p["arm_l"] = -0.25 + 0.10 * math.sin(w * 2.3)
        p["head"] = 0.05 * math.sin(w * 2.6)
        p["hand_r"] = "open"
    elif act == "wave":
        p["arm_r"] = 2.45 + 0.08 * math.sin(w * 3)
        p["fore_r"] = 0.55 * math.sin(w * 9)
        p["head"] = 0.06
        p["hand_r"] = "open"
    elif act == "point":
        p["arm_r"] = 1.50 + 0.04 * math.sin(w * 2)
        p["fore_r"] = 0.0
        p["torso"] += 0.05
        p["head"] = 0.07
        p["hand_r"] = "point"
    elif act == "think":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 0.37, 0.25, -3.09
        p["head"] = 0.10 * math.sin(w * 0.9) - 0.06
        p["look_y"] = -0.5
        p["hand_r"] = "fist"
    elif act == "explain":
        s = math.sin(w * 3)
        p["arm_l"], p["fore_l"] = -0.2, -2.2 - 0.12 * s
        p["arm_r"], p["fore_r"] = 0.2, 2.2 + 0.12 * math.sin(w * 3 + 1)
        p["hand_l"] = p["hand_r"] = "open"
    elif act == "thumbs_up":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 0.5, 0.7, -2.35
        p["hand_r"] = "thumb_up"
        p["hips_dy"] -= 3 * abs(math.sin(w * 3))
    elif act == "ok_sign":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 0.5, 0.7, -2.35
        p["hand_r"] = "ok"
    elif act == "stop":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 1.3, 0.85, 1.84
        p["hand_r"] = "open"
        p["head"] = 0.04
    elif act == "arms_crossed":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 0.15, 0.9, -1.65
        p["arm_l"], p["ua_fs_l"], p["fore_l"] = -0.15, 0.9, 1.65
        p["hand_l"] = p["hand_r"] = "fist"
        p["torso"] = 0.0
    elif act == "shrug":
        k = 0.5 + 0.5 * math.sin(w * 3)
        p["arm_l"], p["fore_l"] = -0.7, -1.9 - 0.1 * k
        p["arm_r"], p["fore_r"] = 0.7, 1.9 + 0.1 * k
        p["hips_dy"] -= 6 * k
        p["head"] = 0.10 * math.sin(w * 2)
        p["hand_l"] = p["hand_r"] = "open"
    elif act == "walk":
        s = math.sin(w * 6)
        p["thigh_l"], p["thigh_r"] = 0.55 * s, -0.55 * s
        p["shin_l"] = 0.55 * max(0.0, -math.sin(w * 6 + 0.6))
        p["shin_r"] = -0.55 * max(0.0, math.sin(w * 6 + 0.6))
        p["arm_l"] = -0.22 - 0.28 * s
        p["arm_r"] = 0.22 - 0.28 * s
        p["hips_dy"] = -10 * abs(s)
    elif act == "jump":
        j = abs(math.sin(w * 5))
        p["hips_dy"] = -110 * j
        p["arm_l"], p["arm_r"] = -2.3, 2.3
        p["fore_l"], p["fore_r"] = 0.25, -0.25
        p["thigh_l"], p["thigh_r"] = -0.22 * (1 - j), 0.22 * (1 - j)
        p["shin_l"], p["shin_r"] = 0.45 * j, -0.45 * j
        p["hand_l"] = p["hand_r"] = "open"
    elif act == "look_around":
        p["head"] = 0.16 * math.sin(w * 1.6)
        p["look_x"] = math.sin(w * 1.6)
    elif act == "cheer":
        p["arm_l"] = -2.6 + 0.2 * math.sin(w * 8)
        p["arm_r"] = 2.6 - 0.2 * math.sin(w * 8 + 1)
        p["fore_l"], p["fore_r"] = 0.3 * math.sin(w * 8), -0.3 * math.sin(w * 8 + 1)
        p["hips_dy"] -= 0 if seated else 30 * abs(math.sin(w * 4))
        p["hand_l"] = p["hand_r"] = "fist"
        p["fx"] = ("confetti",)
    elif act == "clap":
        s = 0.5 + 0.5 * math.sin(w * 11)
        p["arm_l"], p["arm_r"] = -0.15, 0.15
        p["fore_l"] = 2.58 + 0.45 * (1 - s)
        p["fore_r"] = -2.58 - 0.45 * (1 - s)
        p["hips_dy"] -= 0 if seated else 5 * abs(math.sin(w * 5.5))
        p["hand_l"] = p["hand_r"] = "open"
    elif act == "dance":
        s = math.sin(w * 4)
        p["hips_dx"] = 20 * s
        p["torso"] = 0.05 * s
        p["arm_l"] = -1.0 - 0.8 * max(0.0, s)
        p["arm_r"] = 1.0 + 0.8 * max(0.0, -s)
        p["fore_l"], p["fore_r"] = 0.5 * math.sin(w * 8), -0.5 * math.sin(w * 8 + 1)
        p["thigh_l"], p["thigh_r"] = 0.18 * s + 0.04, 0.18 * s - 0.04
        p["hips_dy"] = -12 * abs(math.sin(w * 8))
        p["head"] = 0.10 * s
        p["hand_l"] = p["hand_r"] = "open"
    elif act == "facepalm":
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 3.0, 0.4, 0.59
        p["head"] = 0.14
        p["look_y"] = 0.8
        p["eyes_closed"] = 1.0
        p["hand_r"] = "open"
    elif act == "phone_call":          # phone held to the right ear: lift the arm, tilt the head toward it
        p["arm_r"], p["ua_fs_r"], p["fore_r"] = 1.55, 0.9, 2.05
        p["head"] = -0.09
        p["prop"] = "phone_ear"
        p["hand_r"] = "fist"
    elif act == "use_phone":
        p["arm_r"], p["ua_fs_r"] = 0.30, 0.8
        p["fore_r"] = -2.2 + 0.04 * math.sin(w * 6)
        p["head"] = 0.06
        p["look_y"] = 0.9
        p["prop"] = "phone"
        p["hand_r"] = "fist"
    elif act == "drink_tea":
        lift = _bump((w % 5.0) / 5.0)
        p["arm_r"] = _lerp(0.26, 0.37, lift)
        p["ua_fs_r"] = _lerp(1.0, 0.25, lift)
        p["fore_r"] = _lerp(-1.55, -3.09, lift)
        p["look_y"] = 0.4 * lift
        p["eyes_closed"] = 1.0 if lift > 0.85 else 0.0
        p["prop"] = "mug"
        p["lift"] = lift
        p["hand_r"] = "fist"
    elif act == "eat":
        lift = _bump((w % 3.6) / 3.6, 0.15, 0.4, 0.55, 0.7)
        p["arm_r"] = _lerp(0.26, 0.37, lift)
        p["ua_fs_r"] = _lerp(1.0, 0.25, lift)
        p["fore_r"] = _lerp(-1.55, -3.09, lift)
        p["prop"] = "samosa"
        p["lift"] = lift
        p["hand_r"] = "fist"
        p["bite"] = 1 if (w % 3.6) / 3.6 > 0.45 else 0
        chewing = 0.55 < (w % 3.6) / 3.6 < 1.0
        p["mouth_force"] = (0.18 + 0.16 * math.sin(w * 13)) if chewing and not speaking else 0.0
    elif act == "read_book":
        p["arm_l"], p["fore_l"] = -0.12, 2.62
        p["arm_r"], p["fore_r"] = 0.12, -2.62
        p["head"] = 0.05
        p["look_y"] = 1.0
        p["prop"] = "book"
        p["hand_l"] = p["hand_r"] = "fist"
    elif act == "sleep":
        p["head"] = 0.22 + 0.08 * math.sin(w * 0.9)
        p["torso"] = 0.08
        p["eyes_closed"] = 1.0
        p["z"] = 1
        p["arm_l"] += 0.05

    if free:  # emotion adds body language only when no explicit activity is set
        e = emotion
        if e == "sad":
            p["torso"] += 0.06; p["head"] += 0.16; p["arm_l"] += 0.1; p["arm_r"] -= 0.1
        elif e == "surprised":
            p["arm_l"] -= 0.30; p["arm_r"] += 0.30; p["hips_dy"] -= 0 if seated else 8
            p["hand_l"] = p["hand_r"] = "open"
        elif e == "worried":
            p["head"] += 0.10
        elif e == "angry":
            p["torso"] += 0.04; p["arm_l"] -= 0.12; p["arm_r"] += 0.12
            p["hand_l"] = p["hand_r"] = "fist"
        elif e == "happy":
            p["hips_dy"] -= 0 if seated else 4 * abs(math.sin(w * 3))
        elif e == "laughing":
            p["hips_dy"] -= (2 if seated else 7) * abs(math.sin(w * 9))
            p["torso"] += 0.03 * math.sin(w * 18); p["head"] -= 0.12
            p["arm_l"], p["fore_l"] = -0.35, 0.9
            p["arm_r"], p["fore_r"] = 0.35, -0.9
        elif e == "crying":
            p["head"] += 0.20; p["torso"] += 0.05 + 0.015 * math.sin(w * 14)
            p["arm_r"], p["ua_fs_r"], p["fore_r"] = 2.6, 0.45, 0.94 + 0.08 * math.sin(w * 9)
            p["hand_r"] = "fist"
        elif e == "scared":
            p["torso"] -= 0.06 - 0.02 * math.sin(w * 25)
            p["arm_l"], p["fore_l"] = -0.55, 2.1
            p["arm_r"], p["fore_r"] = 0.55, -2.1
            p["hips_dx"] += 3 * math.sin(w * 30)
            p["hand_l"] = p["hand_r"] = "open"
        elif e == "excited":
            p["arm_l"], p["arm_r"] = -1.2, 1.2
            p["fore_l"], p["fore_r"] = 0.5 * math.sin(w * 7), -0.5 * math.sin(w * 7 + 1)
            p["hips_dy"] -= (3 if seated else 14) * abs(math.sin(w * 6))
            p["hand_l"] = p["hand_r"] = "open"
        elif e == "sleepy":
            p["head"] += 0.18 + 0.05 * math.sin(w * 0.8); p["torso"] += 0.07
        elif e == "embarrassed":
            p["arm_r"], p["fore_r"] = 2.35, 1.53
            p["head"] += 0.15
            p["look_x"] = 0.8
            p["hand_r"] = "open"
        elif e == "confused":
            p["head"] += 0.18
            p["arm_r"], p["fore_r"] = 0.9, -1.3
            p["look_x"] = 0.4 * math.sin(w * 1.2)
            p["hand_r"] = "open"
        elif e == "bored":
            p["torso"] += 0.06; p["head"] += 0.2; p["look_x"] = -0.6
        elif e == "in_love":
            p["torso"] += 0.05 * math.sin(w * 1.5); p["head"] += 0.10 * math.sin(w * 1.5)
            p["arm_l"], p["fore_l"] = -0.20, 2.9
            p["arm_r"], p["fore_r"] = 0.20, -2.9
            p["hand_l"] = p["hand_r"] = "fist"
        elif e == "proud":  # chest out, fists on hips
            p["torso"] -= 0.03; p["head"] -= 0.08
            p["arm_l"], p["fore_l"] = -0.5, 0.95
            p["arm_r"], p["fore_r"] = 0.5, -0.95
            p["hand_l"] = p["hand_r"] = "fist"
        elif e == "disgusted":
            p["torso"] -= 0.05; p["head"] += 0.10; p["look_x"] = -0.8
            p["arm_r"] += 0.25; p["hand_r"] = "open"
        elif e == "thinking":
            p["arm_r"], p["ua_fs_r"], p["fore_r"] = 0.37, 0.25, -3.09
            p["head"] += 0.08; p["look_y"] = -0.7; p["look_x"] = 0.5
            p["hand_r"] = "fist"
        elif e == "shocked":
            p["arm_r"], p["ua_fs_r"], p["fore_r"] = 2.5, 0.5, 1.1
            p["arm_l"], p["ua_fs_l"], p["fore_l"] = -2.5, 0.5, -1.1
            p["hips_dx"] += 2 * math.sin(w * 28)
            p["hand_l"] = p["hand_r"] = "open"
        elif e == "relieved":  # wipes the forehead
            s = 0.5 + 0.5 * math.sin(w * 4)
            p["arm_r"], p["ua_fs_r"], p["fore_r"] = 3.0, 0.4, 0.59 + 0.12 * s
            p["head"] -= 0.08; p["torso"] -= 0.03
            p["hand_r"] = "open"
    return p


def blink_amount(t: float, phase: float) -> float:
    """0 = eyes open, 1 = closed. A quick blink every ~3.4 seconds."""
    tt = (t + phase) % 3.4
    if 3.25 < tt < 3.4:
        return 1 - abs((tt - 3.325) / 0.075)
    return 0.0


# --------------------------------------------------------------------------
# Skeleton
# --------------------------------------------------------------------------
def solve(p: dict) -> dict:
    """Forward kinematics: joint angles -> joint positions (local units)."""
    J: dict = {}
    sit = bool(p.get("sit"))
    hip = (p["hips_dx"], -(SEAT if sit else (THIGH + SHIN + FOOT_H)) + p["hips_dy"])
    J["hip"] = hip
    at = math.pi + p["torso"]
    ut = _d(at)
    J["up"] = ut
    top = (hip[0] + ut[0] * TORSO, hip[1] + ut[1] * TORSO)
    J["top"] = top
    ah = at + p["head"]
    uh = _d(ah)
    J["head"] = (top[0] + uh[0] * (NECK + HEAD_R), top[1] + uh[1] * (NECK + HEAD_R))
    J["head_tilt"] = p["head"] + p["torso"]
    perp = (-math.cos(at), math.sin(at))
    J["perp"] = perp
    for side, n in ((-1, "l"), (1, "r")):
        sh = (hip[0] + ut[0] * TORSO * 0.9 + perp[0] * side * SHOULDER_W,
              hip[1] + ut[1] * TORSO * 0.9 + perp[1] * side * SHOULDER_W)
        a1 = at + math.pi + p["arm_" + n]
        u = _d(a1)
        fs = p.get("ua_fs_" + n, 1.0)
        el = (sh[0] + u[0] * UA * fs, sh[1] + u[1] * UA * fs)
        a2 = a1 + p["fore_" + n]
        v = _d(a2)
        wr = (el[0] + v[0] * FA, el[1] + v[1] * FA)
        hp = (hip[0] + side * HIP_W, hip[1])
        if sit:  # thighs point at the viewer, so they are drawn short and wide apart
            kn = (hp[0] + side * 54, hp[1] + 12)
            b2 = p["shin_" + n]
            v = _d(b2)
            an = (kn[0] + side * 8 + v[0] * SHIN, kn[1] + v[1] * SHIN)
        else:
            b1 = p["thigh_" + n]
            u = _d(b1)
            kn = (hp[0] + u[0] * THIGH, hp[1] + u[1] * THIGH)
            b2 = b1 + p["shin_" + n]
            v = _d(b2)
            an = (kn[0] + v[0] * SHIN, kn[1] + v[1] * SHIN)
        b3 = b2 + side * math.pi / 2
        w = _d(b3)
        ft = (an[0] + w[0] * FOOT, an[1] + w[1] * FOOT)
        J.update({"sh_" + n: sh, "el_" + n: el, "wr_" + n: wr,
                  "hp_" + n: hp, "kn_" + n: kn, "an_" + n: an, "ft_" + n: ft})
    return J


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
OL = (92, 46, 30)            # warm brown outline, like the character sheet
MOUTH_LINE = (122, 52, 42)
MOUTH_DARK = (112, 28, 34)
MOUTH_TONGUE = (238, 112, 118)
INK = (52, 30, 22)           # pupils
SHOE = (240, 242, 246)
SOLE = (170, 176, 188)


def _dark(c, f=0.78):
    return tuple(int(v * f) for v in c)


def _mix(a, b, t):
    return tuple(int(_lerp(x, y, t)) for x, y in zip(a, b))


def _shapes(d, shapes, fill, ow):
    """Draw capsules/circles with one clean outline (outline pass, then fill pass) so joints have no seams."""
    for kind, *a in shapes:
        if kind == "cap":
            p0, p1, w = a
            _cap(d, p0, p1, w + 2 * ow, OL)
        else:
            c, r = a
            d.ellipse([c[0] - r - ow, c[1] - r - ow, c[0] + r + ow, c[1] + r + ow], fill=OL)
    for kind, *a in shapes:
        if kind == "cap":
            p0, p1, w = a
            _cap(d, p0, p1, w, fill)
        else:
            c, r = a
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)


def _cap(d, a, b, w, fill):
    d.line([a, b], fill=fill, width=max(1, int(w)))
    r = w / 2
    for c in (a, b):
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)


def _poly(d, pts, fill, ow):
    """Filled polygon with a rounded outline."""
    d.polygon(pts, fill=fill)
    d.line(list(pts) + [pts[0]], fill=OL, width=max(1, int(ow)), joint="curve")
    r = ow / 2
    for c in pts:
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=OL)


def _blob(d, polys, circles, fill, ow):
    """Union of polygons and circles with a single outline."""
    for pts in polys:
        d.polygon(pts, fill=OL)
        d.line(list(pts) + [pts[0]], fill=OL, width=int(2 * ow), joint="curve")
    for c, r in circles:
        d.ellipse([c[0] - r - ow, c[1] - r - ow, c[0] + r + ow, c[1] + r + ow], fill=OL)
    for pts in polys:
        d.polygon(pts, fill=fill)
    for c, r in circles:
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)


def _heart(d, cx, cy, s, color):
    d.ellipse([cx - 1.05 * s, cy - 0.85 * s, cx, cy + 0.2 * s], fill=color)
    d.ellipse([cx, cy - 0.85 * s, cx + 1.05 * s, cy + 0.2 * s], fill=color)
    d.polygon([(cx - 1.0 * s, cy - 0.1 * s), (cx + 1.0 * s, cy - 0.1 * s), (cx, cy + 1.1 * s)], fill=color)


def _drop(d, cx, cy, s, color):
    d.ellipse([cx - s * 0.7, cy - s * 0.2, cx + s * 0.7, cy + s * 1.2], fill=color)
    d.polygon([(cx - s * 0.62, cy + s * 0.25), (cx + s * 0.62, cy + s * 0.25), (cx, cy - s * 1.1)], fill=color)


def _star(d, cx, cy, s, fill):
    pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        rr = s if i % 2 == 0 else s * 0.34
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _burst(d, cx, cy, s, color, n, a0, spread, w):
    for i in range(n):
        a = a0 + (i - (n - 1) / 2) * spread
        d.line([(cx + math.cos(a) * s * 0.55, cy + math.sin(a) * s * 0.55), (cx + math.cos(a) * s, cy + math.sin(a) * s)],
               fill=color, width=max(2, int(w)))


def _rot(pts, c, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def _octagon(c, ux, uy, hl, hw, cr):
    def pt(a, b):
        return (c[0] + ux[0] * a + uy[0] * b, c[1] + ux[1] * a + uy[1] * b)
    return [pt(-hl + cr, -hw), pt(hl - cr, -hw), pt(hl, -hw + cr), pt(hl, hw - cr),
            pt(hl - cr, hw), pt(-hl + cr, hw), pt(-hl, hw - cr), pt(-hl, -hw + cr)]


def _font(size: float):
    try:
        return ImageFont.load_default(size=max(8, int(size)))
    except TypeError:
        return ImageFont.load_default()


def _B(i, o, arch=0.06):
    return ((i, o, arch), (i, o, arch))


# eyes: open | wide | squint | soft | heart | half | sparkle ; mouth: line | smile | frown | wavy | O | D | tongue
FACE = {
    "neutral":     dict(brow=_B(-0.44, -0.44), eyes="open", mouth="smile", sag=0.07, fx=()),
    "happy":       dict(brow=_B(-0.52, -0.52, 0.09), eyes="open", mouth="D", mw=0.34, mh=0.26, blush=0.3, fx=("burst_y",)),
    "sad":         dict(brow=_B(-0.60, -0.40, 0.0), eyes="open", mouth="frown", sag=-0.11, fx=("tear_small",)),
    "worried":     dict(brow=_B(-0.62, -0.42, 0.0), eyes="open", mouth="wavy", fx=("squiggle", "sweat")),
    "angry":       dict(brow=_B(-0.32, -0.56, 0.0), eyes="open", mouth="gritted", blush=0.6, red=True, fx=("anger", "burst_r")),
    "surprised":   dict(brow=_B(-0.66, -0.66, 0.1), eyes="wide", mouth="O", mw=0.17, mh=0.22, fx=("excl",)),
    "laughing":    dict(brow=_B(-0.54, -0.54, 0.09), eyes="squint", mouth="D", mw=0.42, mh=0.32, blush=0.35, fx=("burst_y", "tears_fly")),
    "crying":      dict(brow=_B(-0.62, -0.38, 0.0), eyes="open", mouth="Ocry", mw=0.26, mh=0.20, tears=True, fx=("tears_fly",)),
    "scared":      dict(brow=_B(-0.68, -0.48, 0.05), eyes="wide", mouth="Ocry", mw=0.22, mh=0.2, small_pupil=True, fx=("sweat2", "vibes")),
    "excited":     dict(brow=_B(-0.58, -0.58, 0.1), eyes="sparkle", mouth="D", mw=0.38, mh=0.28, blush=0.25, fx=("sparkles",)),
    "sleepy":      dict(brow=_B(-0.38, -0.38, 0.0), eyes="half", lid=0.30, mouth="yawn", fx=("zzz",)),
    "embarrassed": dict(brow=_B(-0.54, -0.40, 0.02), eyes="open", mouth="smile", sag=0.05, blush=1.0, fx=("burst_r_small", "sweat")),
    "confused":    dict(brow=((-0.60, -0.52, 0.04), (-0.34, -0.46, 0.0)), eyes="open", mouth="wavy", fx=("ques",)),
    "bored":       dict(brow=_B(-0.38, -0.38, 0.0), eyes="half", lid=0.55, mouth="frown", sag=-0.03, fx=("puff",)),
    "in_love":     dict(brow=_B(-0.52, -0.52, 0.09), eyes="heart", mouth="D", mw=0.26, mh=0.20, blush=0.7, fx=("hearts",)),
    "proud":       dict(brow=_B(-0.56, -0.56, 0.10), eyes="soft", mouth="smile", sag=0.16, blush=0.35, fx=("sparkles",)),
    "disgusted":   dict(brow=_B(-0.34, -0.52, 0.0), eyes="half", lid=0.45, mouth="tongue", fx=("squiggle_g",)),
    "thinking":    dict(brow=((-0.62, -0.50, 0.05), (-0.40, -0.44, 0.0)), eyes="open", mouth="line", sag=0.0, fx=("dots",)),
    "shocked":     dict(brow=_B(-0.70, -0.70, 0.1), eyes="wide", mouth="O", mw=0.24, mh=0.34, small_pupil=True, fx=("excl", "burst_r")),
    "relieved":    dict(brow=_B(-0.54, -0.50, 0.06), eyes="soft", mouth="smile", sag=0.12, blush=0.3, fx=("puff", "sweat")),
}


def _draw_face(d, HL, r, ow, hair, skin, emotion, mouth, blink, pose, t, female, viseme=None):
    f = FACE.get(emotion, FACE["neutral"])
    if f.get("blush"):
        col = _mix(skin, (255, 90, 110) if f.get("red") else (255, 120, 140), 0.55 * min(1, f["blush"] + 0.1))
        for sx in (-1, 1):
            bx, by = HL(sx * 0.64, 0.30)
            d.ellipse([bx - 0.2 * r, by - 0.11 * r, bx + 0.2 * r, by + 0.11 * r], fill=col)

    closed = max(blink, pose.get("eyes_closed", 0.0))
    kind = f["eyes"]
    lw = max(2, int(0.065 * r))
    olw = max(1, int(ow * 0.6))
    for idx, sx in enumerate((-1, 1)):
        cx, cy = HL(sx * 0.38, 0.02)
        if kind == "squint":
            pts = [HL(sx * 0.38 + 0.2 * x / 4, 0.04 - 0.18 * (1 - (x / 4) ** 2)) for x in range(-4, 5)]
            d.line(pts, fill=INK, width=lw + 1, joint="curve")
        elif kind == "soft" or closed > 0.6:
            pts = [HL(sx * 0.38 + 0.2 * x / 4, -0.02 + 0.11 * (1 - (x / 4) ** 2)) for x in range(-4, 5)]
            d.line(pts, fill=INK, width=lw + 1, joint="curve")
        elif kind == "heart":
            _heart(d, cx, cy, 0.17 * r * (1 + 0.08 * math.sin(t * 6)), (232, 56, 100))
        else:
            open_h = max(0.05, 1 - max(blink, closed))
            height = {"wide": 0.56, "sparkle": 0.52, "half": 0.80 * f.get("lid", 0.5)}.get(kind, 0.50)
            rx = (0.22 if kind in ("wide", "sparkle") else 0.2) * r
            ry = height * 0.5 * r * open_h
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(255, 255, 255), outline=OL, width=olw)
            if open_h > 0.3:
                pr = (0.07 if f.get("small_pupil") else 0.125 if kind == "sparkle" else 0.115) * r
                px = cx + pose["look_x"] * 0.08 * r
                py = cy + pose["look_y"] * 0.07 * r
                pry = min(pr * 1.15, ry * 0.95)
                d.ellipse([px - pr, py - pry, px + pr, py + pry], fill=INK)
                hr = max(1.0, 0.045 * r)
                d.ellipse([px - pr * 0.55 - hr, py - pry * 0.5 - hr, px - pr * 0.55 + hr, py - pry * 0.5 + hr],
                          fill=(255, 255, 255))
            if kind == "half":
                lid_y = -0.02 - ry / r
                d.line([HL(sx * 0.38 - 0.22, lid_y), HL(sx * 0.38 + 0.22, lid_y)], fill=OL, width=lw)
            if female and kind != "half":
                for ex, ey in ((0.70, -0.22), (0.75, -0.11), (0.72, 0.0)):
                    d.line([HL(sx * 0.55, -0.06), HL(sx * ex, ey)], fill=OL, width=max(1, lw // 2))
        ib, ob, arch = f["brow"][idx]
        mid = (ib + ob) / 2 - arch
        d.line([HL(sx * 0.17, ib), HL(sx * 0.38, mid), HL(sx * 0.60, ob)], fill=OL if emotion != "neutral" else hair,
               width=max(3, int(0.09 * r)), joint="curve")

    # nose
    d.line([HL(-0.05, 0.24), HL(0.0, 0.29), HL(0.07, 0.25)], fill=_mix(skin, OL, 0.5), width=max(1, int(0.04 * r)), joint="curve")

    # mouth
    kindm = f["mouth"]
    m = max(mouth, pose.get("mouth_force", 0.0))
    wscale = 1.0
    if viseme is not None:                                  # mouth shapes that follow the words (see visemes.py)
        lv, wd, rd = _cartoon_state(viseme, emotion)
        m = lv / 6.0
        wscale = (0.8, 1.0, 1.3)[wd] * (0.8 if rd else 1.0)
        kindm = "open" if lv > 0 else "line"
    ml = max(2, int(0.06 * r))

    def blob(pts, fill):
        d.polygon(pts, fill=fill)
        d.line(pts + [pts[0]], fill=OL, width=max(1, int(ow * 0.7)), joint="curve")

    if kindm in ("D", "O", "Ocry", "yawn") or m > 0.08:
        if kindm == "D":
            mw, mh = f["mw"], f["mh"]
        elif kindm in ("O", "Ocry"):
            mw, mh = f["mw"], f["mh"]
        elif kindm == "yawn":
            mw, mh = 0.20, 0.28 + 0.08 * math.sin(t * 2)
        else:
            mw, mh = 0.28, 0.1
        wob = 1 + 0.12 * math.sin(t * 14) if emotion in ("laughing", "scared", "crying") else 1.0
        mh = max(mh * wob, 0.06 + 0.30 * m)
        mw = (max(mw, 0.2 + 0.1 * m) if m > 0.08 else mw) * wscale
        if kindm == "D":
            pts = [HL(-mw, 0.42)] + [HL(mw * math.cos(a * math.pi / 12), 0.42 + mh * math.sin(a * math.pi / 12))
                                     for a in range(0, 13)][::-1]
            blob(pts, MOUTH_DARK)
            tp = [HL(mw * 0.66 * math.cos(a * math.pi / 12), 0.42 + mh * (0.66 + 0.30 * math.sin(a * math.pi / 12)))
                  for a in range(0, 13)]
            d.polygon(tp, fill=MOUTH_TONGUE)
            d.polygon([HL(-mw * 0.9, 0.43), HL(mw * 0.9, 0.43), HL(mw * 0.82, 0.43 + mh * 0.3), HL(-mw * 0.82, 0.43 + mh * 0.3)],
                      fill=(255, 255, 255))
        else:
            cyy = 0.52
            pts = [HL(mw * math.cos(a * math.pi / 12), cyy + mh * math.sin(a * math.pi / 12)) for a in range(24)]
            blob(pts, MOUTH_DARK)
            if mh > 0.2:
                tp = [HL(mw * 0.6 * math.cos(a * math.pi / 12), cyy + mh * (0.55 + 0.38 * math.sin(a * math.pi / 12)))
                      for a in range(0, 13)]
                d.polygon(tp, fill=MOUTH_TONGUE)
    elif kindm == "gritted":
        pts = [HL(-0.30, 0.46), HL(0.30, 0.46), HL(0.27, 0.62), HL(-0.27, 0.62)]
        blob(pts, (255, 255, 255))
        for x in (-0.15, 0.0, 0.15):
            d.line([HL(x, 0.46), HL(x, 0.62)], fill=OL, width=max(1, ml // 2))
    elif kindm == "tongue":
        d.line([HL(-0.28, 0.50), HL(0.28, 0.54)], fill=MOUTH_LINE, width=ml)
        d.polygon([HL(-0.14, 0.52), HL(0.18, 0.55), HL(0.14, 0.90), HL(-0.10, 0.88)], fill=MOUTH_TONGUE)
        d.line([HL(-0.14, 0.52), HL(-0.10, 0.88), HL(0.14, 0.90), HL(0.18, 0.55)], fill=OL, width=max(1, ml // 2), joint="curve")
    elif kindm == "wavy":
        pts = [HL(0.3 * x / 8, 0.52 + 0.05 * math.sin(x * 1.3)) for x in range(-8, 9)]
        d.line(pts, fill=MOUTH_LINE, width=ml, joint="curve")
    else:
        sag = f.get("sag", 0.03)
        base = 0.45 if sag >= 0 else 0.56
        pts = [HL(0.30 * x / 8, base + sag * (1 - (x / 8) ** 2)) for x in range(-8, 9)]
        d.line(pts, fill=MOUTH_LINE, width=ml, joint="curve")


def _draw_fx(d, HL, r, ow, emotion, pose, t):
    f = FACE.get(emotion, FACE["neutral"])
    names = set(f.get("fx", ())) | set(pose.get("fx", ()))
    if f.get("tears"):
        names.add("tears_run")
    pulse = 1 + 0.12 * math.sin(t * 7)
    w = max(2, int(0.07 * r))
    for n in names:
        if n == "burst_y":
            for sx in (-1, 1):
                x, y = HL(sx * 1.45, -0.55)
                _burst(d, x, y, 0.5 * r * pulse, (250, 190, 40), 3, 0 if sx > 0 else math.pi, 0.6, w)
        elif n in ("burst_r", "burst_r_small"):
            sc = 0.7 if n == "burst_r" else 0.45
            for sx in (-1, 1):
                x, y = HL(sx * 1.55, -0.1)
                _burst(d, x, y, sc * r * pulse, (232, 52, 40), 3, 0 if sx > 0 else math.pi, 0.6, w)
        elif n == "anger":
            x, y = HL(1.2, -1.4)
            s = 0.34 * r * pulse
            for sx in (-1, 1):
                for sy in (-1, 1):
                    d.line([(x + sx * s * 0.25, y + sy * s * 0.95), (x + sx * s * 0.25, y + sy * s * 0.25), (x + sx * s * 0.95, y + sy * s * 0.25)],
                           fill=(226, 40, 36), width=max(3, int(0.09 * r)), joint="curve")
        elif n == "excl":
            x, y = HL(1.35, -1.3)
            d.text((x, y), "!!", font=_font(0.95 * r * pulse), fill=(244, 150, 20), anchor="mm", stroke_width=max(1, int(0.04 * r)), stroke_fill=OL)
        elif n == "ques":
            x, y = HL(1.1, -1.45)
            d.text((x, y), "??", font=_font(0.95 * r), fill=(120, 60, 200), anchor="mm", stroke_width=max(1, int(0.04 * r)), stroke_fill=(70, 30, 130))
        elif n in ("squiggle", "squiggle_g"):
            col = (40, 56, 90) if n == "squiggle" else (96, 170, 60)
            for sx, y0 in ((-1, -1.35),):
                pts = [HL(sx * (1.2 + 0.1 * math.sin(i * 1.4 + t * 5)), y0 + i * 0.12) for i in range(6)]
                d.line(pts, fill=col, width=w, joint="curve")
        elif n == "sweat":
            _drop(d, *HL(1.0, -0.62 + 0.05 * math.sin(t * 5)), 0.13 * r, (130, 200, 255))
        elif n == "sweat2":
            for i in range(2):
                fr = (t * 1.2 + i * 0.5) % 1
                _drop(d, *HL(1.25 + 0.25 * i, -0.95 + 0.5 * fr), 0.12 * r, (130, 200, 255))
        elif n == "vibes":
            for sx in (-1, 1):
                for k in range(3):
                    pts = [HL(sx * (1.6 + 0.16 * k + 0.05 * math.sin(i * 2 + t * 25)), 0.9 + i * 0.12) for i in range(6)]
                    d.line(pts, fill=(60, 70, 100), width=max(2, w // 2), joint="curve")
        elif n == "tear_small":
            for sx in (-1, 1):
                _drop(d, *HL(sx * 0.5, 0.45), 0.09 * r, (130, 200, 255))
        elif n == "tears_run":
            for sx in (-1, 1):
                d.line([HL(sx * 0.42, 0.15), HL(sx * 0.48, 0.70)], fill=(120, 190, 255), width=max(2, int(0.1 * r)))
        elif n == "tears_fly":
            for sx in (-1, 1):
                for i in range(2):
                    fr = (t * 1.1 + i * 0.5 + (0.3 if sx > 0 else 0)) % 1
                    _drop(d, *HL(sx * (1.15 + 0.55 * fr), 0.2 + 0.1 * i - 0.2 * fr + 0.6 * fr * fr), (0.15 - 0.05 * fr) * r, (120, 190, 255))
        elif n == "sparkles":
            for i, (xx, yy, s) in enumerate(((-1.5, -0.9, 0.34), (1.5, -0.7, 0.4), (1.2, -1.5, 0.22))):
                sc = 1 + 0.25 * math.sin(t * 6 + i * 2)
                _star(d, *HL(xx, yy), s * r * sc, (250, 196, 40))
        elif n == "zzz":
            for i in range(3):
                fr = (t * 0.6 + i * 0.33) % 1
                x, y = HL(1.0 + 0.5 * fr + i * 0.1, -0.9 - 1.0 * fr)
                d.text((x, y), "z", font=_font((0.6 + 0.3 * fr) * r), fill=(110, 70, 210), anchor="mm", stroke_width=max(1, int(0.03 * r)), stroke_fill=(70, 40, 150))
        elif n == "hearts":
            for i in range(3):
                fr = (t * 0.7 + i * 0.33) % 1
                x, y = HL(1.1 + 0.35 * math.sin(fr * 6 + i) + i * 0.1, -1.0 - 1.1 * fr)
                _heart(d, x, y, (0.18 - 0.06 * fr) * r, (240, 90, 140))
        elif n == "puff":
            x, y = HL(-1.45, 0.75)
            for dx, dy, rr in ((0, 0, 0.26), (0.24, -0.1, 0.22), (0.18, 0.18, 0.2), (-0.1, 0.14, 0.2)):
                cx, cy = x + dx * r, y + dy * r
                d.ellipse([cx - rr * r, cy - rr * r, cx + rr * r, cy + rr * r], fill=(250, 250, 252), outline=(150, 156, 170), width=max(1, int(ow * 0.5)))
        elif n == "dots":
            for i, (xx, yy, s) in enumerate(((1.15, -0.95, 0.09), (1.4, -1.2, 0.13), (1.75, -1.55, 0.2))):
                x, y = HL(xx, yy)
                d.ellipse([x - s * r, y - s * r, x + s * r, y + s * r], fill=(255, 255, 255), outline=(120, 126, 150), width=max(1, int(ow * 0.5)))
        elif n == "confetti":
            cols = [(240, 80, 80), (250, 190, 40), (60, 170, 240), (80, 200, 120), (190, 90, 220)]
            for i in range(16):
                a = i * 2.4 + 0.5
                fr = (t * 0.9 + i * 0.173) % 1
                x, y = HL(math.cos(a) * (1.7 + 0.3 * math.sin(i)) * (0.9 + 0.2 * fr), -1.2 - 0.6 * math.sin(a) * 0.5 + 1.3 * fr * fr - 0.5 * fr)
                sz = 0.07 * r
                d.rectangle([x - sz, y - sz * 0.6, x + sz, y + sz * 0.6], fill=cols[i % 5])
    if pose.get("z") and "zzz" not in names:
        for i in range(3):
            fr = (t * 0.6 + i * 0.33) % 1
            x, y = HL(1.0 + 0.5 * fr + i * 0.1, -0.9 - 1.0 * fr)
            d.text((x, y), "z", font=_font((0.6 + 0.3 * fr) * r), fill=(110, 70, 210), anchor="mm", stroke_width=max(1, int(0.03 * r)), stroke_fill=(70, 40, 150))


def _hair_polys(style, HL):
    """Hair shapes in head-local units (head circle radius 1, y down). Returns (back, front)."""
    def arc(a0, a1, rad):
        return [HL(rad * math.cos(math.radians(a)), rad * math.sin(math.radians(a))) for a in range(a0, a1 + 1, 10)]

    def fr(pts):
        return [HL(x, y) for x, y in pts]
    back, front = [], []
    if style == "spiky":
        front.append(arc(185, 355, 1.10) + fr([(1.04, 0.12), (1.0, -0.30), (0.80, -0.22), (0.64, -0.52), (0.42, -0.34), (0.22, -0.60), (0.0, -0.38),
                                               (-0.26, -0.60), (-0.46, -0.36), (-0.72, -0.50), (-0.92, -0.18), (-1.04, 0.12)]))
        front.append(fr([(0.35, -1.02), (0.62, -1.46), (0.84, -0.98)]))
        front.append(fr([(-0.05, -1.08), (0.14, -1.40), (0.32, -1.06)]))
    elif style == "swoop":
        front.append(arc(185, 355, 1.10) + fr([(1.04, 0.12), (0.98, -0.28), (0.74, -0.42), (0.40, -0.56), (0.0, -0.62), (-0.38, -0.46),
                                               (-0.70, -0.28), (-0.92, -0.10), (-1.04, 0.12)]))
        front.append(fr([(0.0, -1.04), (0.3, -1.46), (0.58, -1.02)]))
        front.append(fr([(-0.45, -1.0), (-0.32, -1.32), (-0.05, -1.05)]))
    elif style == "long":
        back.append([HL(1.20 * math.cos(math.radians(a)), 1.20 * math.sin(math.radians(a))) for a in range(180, 361, 12)]
                    + fr([(1.26, 0.5), (1.30, 1.3), (1.22, 2.0), (1.0, 2.5), (-1.0, 2.5), (-1.22, 2.0), (-1.30, 1.3), (-1.26, 0.5)]))
        front.append(arc(185, 355, 1.10) + fr([(1.04, 0.3), (1.0, -0.2), (0.7, -0.45), (0.3, -0.60), (-0.1, -0.56), (-0.55, -0.36), (-0.9, 0.0), (-1.04, 0.3)]))
        front.append(fr([(1.0, -0.1), (1.14, 1.0), (1.06, 1.6), (0.88, 1.6), (0.92, 0.2)]))
        front.append(fr([(-1.0, -0.1), (-1.14, 1.0), (-1.06, 1.6), (-0.88, 1.6), (-0.92, 0.2)]))
    return back, front


# --------------------------------------------------------------------------
# Hands
# --------------------------------------------------------------------------
def _hand(d, kind, wr, el, S, skin, ow):
    fx, fy = wr[0] - el[0], wr[1] - el[1]
    n = math.hypot(fx, fy) or 1.0
    fx, fy = fx / n, fy / n
    nx, ny = -fy, fx
    c = wr

    def at(a, b):
        return (c[0] + fx * a * S + nx * b * S, c[1] + fy * a * S + ny * b * S)
    shapes = []
    if kind in ("relaxed", "fist"):
        shapes.append(("circ", at(6, 0), (19 if kind == "fist" else 18) * S))
    elif kind == "thumb_up":
        shapes += [("circ", at(6, 0), 20 * S), ("cap", (c[0] + 4 * S, c[1] - 8 * S), (c[0] + 8 * S, c[1] - 56 * S), 18 * S)]
    elif kind == "point":
        shapes += [("circ", at(6, 0), 19 * S), ("cap", at(6, 0), at(56, 0), 12 * S)]
    elif kind == "open":
        shapes.append(("circ", at(16, 0), 21 * S))
        for off, ang, ln in ((-13, -0.30, 28), (-4.5, -0.10, 32), (4.5, 0.10, 32), (13, 0.30, 28)):
            ca, sa = math.cos(ang), math.sin(ang)
            dx, dy = fx * ca - fy * sa, fx * sa + fy * ca
            s0 = at(28, off)
            shapes.append(("cap", s0, (s0[0] + dx * ln * S, s0[1] + dy * ln * S), 9 * S))
        shapes.append(("cap", at(10, 18), at(26, 38), 10 * S))
    elif kind == "ok":
        shapes.append(("circ", at(8, 0), 18 * S))
        for off, ang, ln in ((4, 0.05, 30), (13, 0.25, 27), (21, 0.45, 23)):
            ca, sa = math.cos(ang), math.sin(ang)
            dx, dy = fx * ca - fy * sa, fx * sa + fy * ca
            s0 = at(18, off - 8)
            shapes.append(("cap", s0, (s0[0] + dx * ln * S, s0[1] + dy * ln * S), 9 * S))
    _shapes(d, shapes, skin, ow)
    if kind == "ok":  # ring made by thumb and index finger
        rc = at(32, -10)
        d.ellipse([rc[0] - 11 * S, rc[1] - 11 * S, rc[0] + 11 * S, rc[1] + 11 * S], outline=OL, width=int(7 * S))
        d.ellipse([rc[0] - 11 * S, rc[1] - 11 * S, rc[0] + 11 * S, rc[1] + 11 * S], outline=skin, width=int(3.5 * S))


def _draw_prop(d, kind, J, S, P, pose, t):
    wr = P(J["wr_r"])
    lift = pose.get("lift", 0.0)
    ow = max(2, 3.5 * S)
    if kind == "phone_ear":
        c = (wr[0] - 6 * S, wr[1] - 22 * S)                   # the phone stands at the ear, the hand around it
        ux, uy = (0.17, -0.985), (0.985, 0.17)
        _poly(d, _octagon(c, ux, uy, 50 * S, 26 * S, 9 * S), (36, 40, 58), ow)
        d.polygon(_octagon(c, ux, uy, 44 * S, 20 * S, 7 * S), fill=(54, 60, 88))
        for off in (0, 1):
            cc = (c[0] + ux[0] * 28 * S + uy[0] * (-9 + 11 * off) * S, c[1] + ux[1] * 28 * S + uy[1] * (-9 + 11 * off) * S)
            d.ellipse([cc[0] - 4.5 * S, cc[1] - 4.5 * S, cc[0] + 4.5 * S, cc[1] + 4.5 * S], fill=(16, 18, 30))
    elif kind == "phone":
        c = (wr[0] - 6 * S, wr[1] - 28 * S)          # held upright above the hand
        ux, uy = (-0.199, -0.980), (0.980, -0.199)
        _poly(d, _octagon(c, ux, uy, 52 * S, 28 * S, 9 * S), (36, 40, 58), ow)
        d.polygon(_octagon(c, ux, uy, 46 * S, 22 * S, 7 * S), fill=(54, 60, 88))
        cam = (c[0] + ux[0] * 30 * S - uy[0] * 11 * S, c[1] + ux[1] * 30 * S - uy[1] * 11 * S)
        for off in (0, 1):
            cc = (cam[0] + uy[0] * 12 * S * off, cam[1] + uy[1] * 12 * S * off)
            d.ellipse([cc[0] - 5 * S, cc[1] - 5 * S, cc[0] + 5 * S, cc[1] + 5 * S], fill=(16, 18, 30))
    elif kind in ("mug", "samosa"):
        tilt = -0.75 * lift
        pivot = (wr[0], wr[1])
        cx, cy = wr[0] - 4 * S, wr[1] - 22 * S
        if kind == "mug":
            body = [(cx - 24 * S, cy - 26 * S), (cx + 24 * S, cy - 26 * S), (cx + 20 * S, cy + 26 * S), (cx - 20 * S, cy + 26 * S)]
            band = [(cx - 23 * S, cy - 4 * S), (cx + 23 * S, cy - 4 * S), (cx + 22 * S, cy + 8 * S), (cx - 22 * S, cy + 8 * S)]
            tea = [(cx - 22 * S, cy - 26 * S), (cx + 22 * S, cy - 26 * S), (cx + 22 * S, cy - 19 * S), (cx - 22 * S, cy - 19 * S)]
            body, band, tea = (_rot(x, pivot, tilt) for x in (body, band, tea))
            hc_ = _rot([(cx + 30 * S, cy - 2 * S)], pivot, tilt)[0]
            d.ellipse([hc_[0] - 14 * S, hc_[1] - 16 * S, hc_[0] + 14 * S, hc_[1] + 16 * S], outline=OL, width=max(2, int(9 * S)))
            d.ellipse([hc_[0] - 14 * S, hc_[1] - 16 * S, hc_[0] + 14 * S, hc_[1] + 16 * S], outline=(245, 245, 240), width=max(2, int(5 * S)))
            _poly(d, body, (245, 245, 240), ow)
            d.polygon(band, fill=(216, 90, 48))
            d.polygon(tea, fill=(172, 106, 52))
            if lift < 0.7:
                for i in (-1, 0, 1):
                    pts = [(cx + i * 12 * S + 6 * S * math.sin(t * 3 + yy * 0.8 + i), cy - 34 * S - yy * 7 * S) for yy in range(0, 6)]
                    d.line(pts, fill=(226, 229, 238), width=max(2, int(3 * S)), joint="curve")
        else:
            tri = [(cx, cy - 36 * S), (cx - 36 * S, cy + 24 * S), (cx + 36 * S, cy + 24 * S)]
            tri = _rot(tri, pivot, tilt)
            _poly(d, tri, (222, 156, 62), ow)
            for dx, dy in ((-8, 6), (10, 12), (0, -8)):
                q = _rot([(cx + dx * S, cy + dy * S)], pivot, tilt)[0]
                d.ellipse([q[0] - 3 * S, q[1] - 3 * S, q[0] + 3 * S, q[1] + 3 * S], fill=(160, 100, 30))
            if pose.get("bite"):
                q = _rot([(cx - 24 * S, cy - 8 * S)], pivot, tilt)[0]
                d.ellipse([q[0] - 15 * S, q[1] - 15 * S, q[0] + 15 * S, q[1] + 15 * S], fill=(0, 0, 0, 0))
    elif kind == "book":
        wl, wrr = P(J["wr_l"]), P(J["wr_r"])
        c = ((wl[0] + wrr[0]) / 2, (wl[1] + wrr[1]) / 2 - 20 * S)
        cover = (83, 74, 183)
        pg = (250, 246, 232)
        for sx in (-1, 1):
            _poly(d, [(c[0] + sx * 3 * S, c[1] - 52 * S), (c[0] + sx * 84 * S, c[1] - 58 * S),
                      (c[0] + sx * 84 * S, c[1] + 62 * S), (c[0] + sx * 3 * S, c[1] + 56 * S)], cover, ow)
            d.polygon([(c[0] + sx * 4 * S, c[1] - 47 * S), (c[0] + sx * 78 * S, c[1] - 53 * S),
                       (c[0] + sx * 78 * S, c[1] + 56 * S), (c[0] + sx * 4 * S, c[1] + 51 * S)], fill=pg)
            for i in range(4):
                yy = c[1] - 30 * S + i * 18 * S
                d.line([(c[0] + sx * 14 * S, yy), (c[0] + sx * 66 * S, yy - 2 * S)], fill=(190, 186, 170), width=max(1, int(3 * S)))
        d.line([(c[0], c[1] - 52 * S), (c[0], c[1] + 56 * S)], fill=_dark(cover, 0.7), width=max(2, int(5 * S)))


_SPRITES: dict = {}


def _smooth_up(src: Image.Image) -> Image.Image:
    """Enlarge a tiny picture 4x with smooth edges (plain resizing looks blocky). Big pictures are left alone."""
    if src.width >= 200:
        return src
    rgb, a = src.convert("RGB"), src.split()[3]
    for _ in range(2):
        rgb = rgb.resize((rgb.width * 2, rgb.height * 2), Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.9))
        a = a.resize((a.width * 2, a.height * 2), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=3, percent=150, threshold=2))
    out = rgb.convert("RGBA")
    out.putalpha(a)
    return out


_MAPS: dict = {}


def _face_name(look_id: str, emotion: str) -> str:
    """Characters like Maa have fewer faces than emotions: map.json says which face an emotion uses."""
    if look_id not in _MAPS:
        path = ASSETS_DIR / "characters" / look_id / "map.json"
        _MAPS[look_id] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    m = _MAPS[look_id]
    if emotion.endswith("_nomouth"):
        base = emotion[: -len("_nomouth")]
        return m.get(base, base) + "_nomouth"
    return m.get(emotion, emotion)


def _load_sprite(look_id: str, emotion: str):
    """Head picture convention: head centred left-to-right, face centre 57% down the picture, and the picture
    about 1.55x as wide as the head. Any size works (the sheet faces are 62 px; sharper ones can be 600+ px)."""
    key = (look_id, emotion)
    if key not in _SPRITES:
        path = ASSETS_DIR / "characters" / look_id / "heads" / f"{_face_name(look_id, emotion)}.png"
        _SPRITES[key] = _smooth_up(Image.open(path).convert("RGBA")) if path.exists() else None
    return _SPRITES[key]


# ---- lip-sync: while someone talks, the picture's own (fixed) mouth is painted over and a mouth that opens and
# ---- closes with the sound is drawn in its place. All sizes are in "skull widths" (the framing convention).
MOUTH_SAG = {"neutral": .07, "happy": .15, "sad": -.11, "worried": -.05, "angry": -.06, "surprised": 0.0,
             "laughing": .15, "crying": -.10, "scared": -.05, "excited": .13, "sleepy": 0.0, "embarrassed": .05,
             "confused": 0.0, "bored": -.03, "in_love": .15, "proud": .15, "disgusted": -.08, "thinking": 0.0,
             "shocked": 0.0, "relieved": .10}
ROUND_MOUTH = {"surprised", "shocked", "scared"}                 # rounder and taller when open
NO_LIPSYNC = {"sleepy", "bored", "thinking"}                      # a hand covers the mouth in these pictures
NO_LIPSYNC_BY_LOOK = {"rahul": {"confused"}, "maa": {"thinking", "confused", "sad"}}
# the twelve mouth shapes of the lip-sync reference, drawn for the cartoon faces: (opening 0..6, width 0..2, rounded lips)
CARTOON = {"rest": (0, 1, False), "ba": (0, 0, False), "aa": (6, 1, False), "ah": (3, 1, False), "ee": (2, 2, False),
           "eh": (3, 2, False), "oo": (2, 0, True), "oh": (4, 0, True), "fa": (1, 1, False), "th": (2, 1, False),
           "ta": (2, 1, False), "la": (3, 1, False), "ra": (2, 0, False)}
EMO_OPEN = {"happy": 1.1, "excited": 1.15, "laughing": 1.1, "angry": 1.05, "sad": 0.8, "crying": 0.85, "sleepy": 0.7,
            "bored": 0.8, "worried": 0.9, "thinking": 0.9}       # happy = brighter, sad = softer
_LIPS: dict = {}
_META: dict = {}


def _meta(look_id: str) -> dict:
    """Mouth positions measured on the face pictures of a character (mouths.json), if there are any."""
    if look_id not in _META:
        path = ASSETS_DIR / "characters" / look_id / "mouths.json"
        _META[look_id] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _META[look_id]


def _mouth_layer(sk: float, level: int, wide: int, sag: float, rounder: bool, soft: bool = False) -> Image.Image:
    """The mouth alone, drawn 3x bigger and shrunk for smooth edges. Anchor = middle of a closed mouth."""
    SS = 3
    w, h = int(0.66 * sk), int(0.46 * sk)
    W, H = w * SS, h * SS
    m = level / 6.0
    wf = (0.88, 1.0, 1.14)[wide]
    a = (0.115 + 0.075 * m) * sk * SS * wf * (0.82 if rounder else 1.0)
    hh = (0.03 + 0.16 * m) * sk * SS * (1.2 if rounder else 1.0)
    c = sag * 0.30 * sk * SS
    y0 = 0.35 * H - 0.07 * sk * SS * m                   # the upper lip rises a little as the mouth opens
    xs = [a * (i / 24 - 1) for i in range(49)]
    top = [(W / 2 + x, y0 + c * (1 - (x / a) ** 2)) for x in xs]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lw = max(2, int(0.022 * sk * SS))
    if soft:                                                # realistic faces: soft lips, no outline
        c_line, c_dark, c_tongue, c_teeth, c_lip = (150, 80, 72), (66, 22, 24), (158, 76, 76), (232, 224, 208), (172, 96, 88)
        lw = max(2, int(0.016 * sk * SS))
        a *= 0.95
    else:
        c_line, c_dark, c_tongue, c_teeth, c_lip = MOUTH_LINE, MOUTH_DARK, MOUTH_TONGUE, (255, 255, 255), None
    if level == 0:                                         # closed: a smile / frown line
        d.line(top, fill=c_line + (255,), width=lw, joint="curve")
    else:
        bot = [(W / 2 + x, y0 + c * (1 - (x / a) ** 2) + hh * math.sqrt(max(0.0, 1 - (x / a) ** 2))) for x in xs]
        pts = top + bot[::-1]
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        if c_lip:                                          # lips: a thin band around the opening
            gap = 0.014 * sk * SS
            ImageDraw.Draw(lay).polygon([(x, y - gap) for x, y in top] + [(x, y + gap) for x, y in bot[::-1]], fill=c_lip + (255,))
        body = Image.new("RGBA", (W, H), c_dark + (255,))
        if level >= 3:                                     # tongue
            tm = Image.new("L", (W, H), 0)
            cy = y0 + c + hh * 0.80
            ImageDraw.Draw(tm).ellipse([W / 2 - a * 0.5, cy - hh * 0.28, W / 2 + a * 0.5, cy + hh * 0.28], fill=255)
            body.paste(c_tongue + (255,), (0, 0), ImageChops.multiply(mask, tm))
        if level >= 2:                                     # upper teeth
            th = min(hh * 0.45, (0.032 if soft else 0.05) * sk * SS)
            tm = Image.new("L", (W, H), 0)
            ImageDraw.Draw(tm).polygon([(x * 0.86 + W / 2, y) for x, y in [(px - W / 2, py) for px, py in top]] +
                                       [(x * 0.86 + W / 2, y + th) for x, y in [(px - W / 2, py) for px, py in top]][::-1], fill=255)
            body.paste(c_teeth + (255,), (0, 0), ImageChops.multiply(mask, tm))
        lay.paste(body, (0, 0), mask)
        if not soft:
            d.line(pts + [pts[0]], fill=OL + (255,), width=lw, joint="curve")
    if soft:
        lay = lay.filter(ImageFilter.GaussianBlur(0.7 * SS))
    return lay.resize((w, h), Image.LANCZOS)


def _cartoon_state(vis, emotion: str):
    """(opening, width, rounded) for a drawn mouth from a (shape, next shape, blend, loudness) moment."""
    va, vb, bl, amp = vis
    la, wa, ra_ = CARTOON[va]
    lb, wb, rb = CARTOON[vb]
    level = (la + (lb - la) * bl) * (0.7 + 0.3 * amp) * EMO_OPEN.get(emotion, 1.0)
    lv = max(0, min(6, int(round(level))))
    if level > 0.3 and lv == 0:
        lv = 1
    return lv, max(0, min(2, int(round(wa + (wb - wa) * bl)))), (ra_ if bl < 0.5 else rb)


def _lipsync_sprite(look_id: str, emotion: str, base: Image.Image, level: int, wide: int, rounder=None) -> Image.Image:
    key = (look_id, emotion, level, wide, rounder)
    if key in _LIPS:
        return _LIPS[key]
    meta = _meta(look_id).get(_face_name(look_id, emotion))
    nomouth = _load_sprite(look_id, emotion + "_nomouth") if meta else None
    if meta and nomouth is not None:        # realistic face: its mouth was removed; draw a soft mouth where it was
        img = nomouth.copy()
        lay = _mouth_layer(meta["sk"], level, wide, MOUTH_SAG.get(emotion, 0.05), bool(rounder) or emotion in ROUND_MOUTH, soft=True)
        img.alpha_composite(lay, (int(meta["cx"] - lay.width / 2), int(meta["cy"] - 0.35 * lay.height)))
        _LIPS[key] = img
        return img
    W, H = base.size
    sk, fx, fy = 0.55 * W, 0.5 * W, 0.57 * H
    px = base.load()
    cand = [(sx * u, v) for sx in (-1, 1) for u, v in ((0.30, 0.28), (0.27, 0.36), (0.22, 0.43), (0.12, 0.47), (0.33, 0.33))]
    ok = []
    for u, v in cand:                                        # only real skin colours (not tears, blush or outlines)
        r_, g_, b_, a_ = px[int(fx + u * sk), int(fy + v * sk)]
        if a_ > 200 and r_ > 205 and g_ > 150 and b_ > 90 and 45 < r_ - b_ < 150:
            ok.append((r_, g_, b_))
    skin = tuple(sorted(c)[len(c) // 2] for c in zip(*ok)) if ok else (252, 206, 153)
    img = base.copy()
    ImageDraw.Draw(img).rounded_rectangle([fx - 0.31 * sk, fy + 0.19 * sk, fx + 0.31 * sk, fy + 0.47 * sk],
                                          radius=int(0.08 * sk), fill=skin + (255,))
    img.putalpha(base.split()[3])                          # never paint outside the face
    lay = _mouth_layer(sk, level, wide, MOUTH_SAG.get(emotion, 0.05), bool(rounder) or emotion in ROUND_MOUTH)
    img.alpha_composite(lay, (int(fx - lay.width / 2), int(fy + 0.32 * sk - 0.35 * lay.height)))
    _LIPS[key] = img
    return img


# ---- photo mouths: a character with a visemes/ folder (Maa) gets real mouth pictures pasted on while she talks
EMOTION_MOUTHS = {"happy", "worried", "sad", "crying", "surprised", "thinking", "affectionate"}
EMO_REST = {"worried": "worried", "scared": "worried", "angry": "worried", "disgusted": "worried", "sad": "sad",
            "sleepy": "sad", "bored": "sad", "crying": "crying", "surprised": "surprised", "shocked": "surprised",
            "in_love": "affectionate"}                   # at rest her mouth matches her mood (the others use the plain rest mouth)
_PHOTO_OK: dict = {}
_CROPS: dict = {}
_PATCHES: dict = {}


def _has_photos(look_id: str) -> bool:
    if look_id not in _PHOTO_OK:
        _PHOTO_OK[look_id] = (ASSETS_DIR / "characters" / look_id / "visemes" / "aa.png").exists()
    return _PHOTO_OK[look_id]


def _photo_patch(look_id: str, face: str, name: str, meta: dict, nm: Image.Image):
    """(RGBA mouth patch matched to this face's skin, (dx, dy) from the mouth centre), or None."""
    key = (look_id, face, name)
    if key in _PATCHES:
        return _PATCHES[key]
    if name == "ah":                                      # half open: halfway between the plain rest mouth and "aa"
        a, b = _photo_patch(look_id, face, "rest", meta, nm), _photo_patch(look_id, face, "aa", meta, nm)
        res = (Image.blend(a[0], b[0], 0.5), a[1]) if a and b else None
        _PATCHES[key] = res
        return res
    if (look_id, name) not in _CROPS:
        path = ASSETS_DIR / "characters" / look_id / "visemes" / f"{name}.png"
        _CROPS[(look_id, name)] = Image.open(path).convert("RGB") if path.exists() else None
    crop = _CROPS[(look_id, name)]
    if crop is None:
        _PATCHES[key] = None
        return None
    emo = name in EMOTION_MOUTHS
    w = max(8, int((0.615 if emo else 0.57) * meta["skull"]))
    h = max(8, int(crop.height * w / crop.width))
    rgb = crop.resize((w, h), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse([0.05 * w, 0.14 * h, 0.95 * w, 0.86 * h] if emo else [0, 0.25 * h, w, 0.91 * h], fill=255)
    m = m.filter(ImageFilter.GaussianBlur((0.10 if emo else 0.07) * w))
    dy = -(0.5 if emo else 0.52) * h
    # match the skin colour of the picture to the face it is pasted on
    cx, cy = meta["cx"], meta["cy"]
    try:
        tgt = [ImageStat.Stat(nm.crop((int(cx + sx * 0.5 * w - 5), int(cy - 5), int(cx + sx * 0.5 * w + 5), int(cy + 5))).convert("RGB")).mean
               for sx in (-1, 1)]
        src = [ImageStat.Stat(rgb.crop((int(a * w), int(0.40 * h), int(b * w), int(0.70 * h)))).mean for a, b in ((0.02, 0.10), (0.90, 0.98))]
        shift = [max(-45, min(45, (tgt[0][i] + tgt[1][i] - src[0][i] - src[1][i]) / 2)) for i in range(3)]
    except Exception:
        shift = [0, 0, 0]
    bands = [b.point(lambda v, sh=sh: max(0, min(255, int(v + sh)))) for b, sh in zip(rgb.split(), shift)]
    patch = Image.merge("RGBA", (*bands, m))
    res = (patch, (-w / 2, dy))
    _PATCHES[key] = res
    return res


def _photo_mouth_sprite(look_id: str, emotion: str, vis):
    face = _face_name(look_id, emotion)
    meta = _meta(look_id).get(face)
    nm = _load_sprite(look_id, emotion + "_nomouth")
    if not meta or nm is None or "skull" not in meta:
        return None
    va, vb, bl, _amp = vis

    def nm_of(v):
        return EMO_REST.get(emotion, "rest") if v == "rest" else v
    pa = _photo_patch(look_id, face, nm_of(va), meta, nm)
    pb = _photo_patch(look_id, face, nm_of(vb), meta, nm)
    if pa is None or pb is None:
        return None
    img = nm.copy()
    if bl < 0.17 or va == vb:
        patch, (dx, dy) = pa
    elif bl > 0.83:
        patch, (dx, dy) = pb
    elif pa[0].size == pb[0].size:                         # same size and shape: a real crossfade
        patch, (dx, dy) = Image.blend(pa[0], pb[0], bl), pa[1]
    else:
        patch, (dx, dy) = pa if bl < 0.5 else pb
    img.alpha_composite(patch, (int(meta["cx"] + dx), int(meta["cy"] + dy)))
    img.putalpha(nm.getchannel("A"))                      # never outside the face
    return img


def _pick_sprite(look: dict, emotion: str, pose: dict, mouth: float, lipsync: bool = False, t: float = 0.0, viseme=None):
    """Choose the face picture for this moment. Returns (picture or None, True if its mouth is lip-synced)."""
    lid = look.get("id")
    if not lid:
        return None, False
    emo = emotion
    if pose.get("eyes_closed", 0) > 0.6 and emotion in ("neutral", "happy"):
        emo = "proud"                      # closed eyes while sipping tea, wiping, sleeping...
    elif pose.get("z"):
        emo = "sleepy"
    base = _load_sprite(lid, emo) or _load_sprite(lid, "neutral")
    if base is None:
        return None, False
    m = max(mouth, pose.get("mouth_force", 0.0))
    if (lipsync or pose.get("mouth_force", 0.0) > 0.05) and emo not in NO_LIPSYNC \
            and emo not in NO_LIPSYNC_BY_LOOK.get(lid, ()):
        if viseme is not None:                              # mouth shapes that follow the words (see visemes.py)
            if _has_photos(lid):
                sp = _photo_mouth_sprite(lid, emo, viseme)
                if sp is not None:
                    return sp, True
            lv, wd, rd = _cartoon_state(viseme, emo)
            return _lipsync_sprite(lid, emo, base, lv, wd, rd), True
        level = max(0, min(6, int(round(min(1.0, m * 1.25) * 6))))     # a little gain so speech opens the mouth clearly
        return _lipsync_sprite(lid, emo, base, level, int(t * 9) % 3 if level else 1), True
    return base, False


# ---- Maa's saree: fabrics cut from her character sheet (assets/characters/maa/*.png)
_FAB: dict = {}
_FAB_SCALE = {"saree_floral": 0.34, "blouse": 0.5}
GOLD = (214, 164, 44)


def _fabric(name: str, size: tuple, S: float, fallback: tuple) -> Image.Image:
    """The fabric picture repeated (mirrored, so no seams show) over a layer of `size` pixels."""
    key = (name, size, round(S, 2))
    if key not in _FAB:
        path = ASSETS_DIR / "characters" / "maa" / f"{name}.png"
        if not path.exists():
            _FAB[key] = Image.new("RGB", size, fallback)
        else:
            tex = Image.open(path).convert("RGB")
            sc = _FAB_SCALE[name] * S
            t = tex.resize((max(6, int(tex.width * sc)), max(6, int(tex.height * sc))), Image.LANCZOS)
            flips = [t, t.transpose(Image.FLIP_LEFT_RIGHT), t.transpose(Image.FLIP_TOP_BOTTOM),
                     t.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)]
            canvas = Image.new("RGB", size)
            for iy, y in enumerate(range(0, size[1], t.height)):
                for ix, x in enumerate(range(0, size[0], t.width)):
                    canvas.paste(flips[(ix % 2) + 2 * (iy % 2)], (x, y))
            _FAB[key] = canvas
        if len(_FAB) > 10:
            _FAB.pop(next(iter(_FAB)))
    return _FAB[key]


def _border_band(w: int, h: int, fallback: tuple) -> Image.Image:
    key = ("border", w, h)
    if key not in _FAB:
        path = ASSETS_DIR / "characters" / "maa" / "saree_border.png"
        if not path.exists():
            _FAB[key] = Image.new("RGB", (w, h), fallback)
        else:
            t = Image.open(path).convert("RGB")
            t = t.resize((max(4, int(t.width * h / t.height)), h), Image.LANCZOS)
            out, x, i = Image.new("RGB", (w, h)), 0, 0
            while x < w:
                out.paste(t if i % 2 == 0 else t.transpose(Image.FLIP_LEFT_RIGHT), (x, 0))
                x += t.width
                i += 1
            _FAB[key] = out
    return _FAB[key]


def _paste_fabric(im: Image.Image, polys, circles, fabric: Image.Image, origin=(0, 0)):
    """Paste `fabric` inside the union of polygons and circles (layer pixel coordinates)."""
    xs = [x for pts in polys for x, _ in pts] + [c[0] + r for c, r in circles] + [c[0] - r for c, r in circles]
    ys = [y for pts in polys for _, y in pts] + [c[1] + r for c, r in circles] + [c[1] - r for c, r in circles]
    x0, y0, x1, y1 = max(0, int(min(xs))), max(0, int(min(ys))), min(im.width, int(max(xs)) + 1), min(im.height, int(max(ys)) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    md = ImageDraw.Draw(mask)
    for pts in polys:
        md.polygon([(x - x0, y - y0) for x, y in pts], fill=255)
    for (cx, cy), r in circles:
        md.ellipse([cx - r - x0, cy - r - y0, cx + r - x0, cy + r - y0], fill=255)
    im.paste(fabric.crop((x0 - origin[0], y0 - origin[1], x1 - origin[0], y1 - origin[1])), (x0, y0), mask)


def _draw_saree_lower(im, d, J, P, S, look, sit, ow, skin):
    """Feet, and the saree wrapped around the legs (to the ankles when standing, to the knees when sitting)."""
    cream = look["pants"]
    hip = J["hip"]
    fab = _fabric("saree_floral", im.size, S, cream)
    if sit:                                                   # legs under the cloth: lower legs only
        for n in ("l", "r"):
            _shapes(d, [("cap", P(J["kn_" + n]), P(J["an_" + n]), 40 * S)], cream, ow)
            _paste_fabric(im, [], [(P(J["an_" + n]), 14 * S)], fab)
    for n in ("l", "r"):
        an, ft = P(J["an_" + n]), P(J["ft_" + n])
        _shapes(d, [("cap", an, ft, 26 * S)], skin, ow)
        d.line([(an[0], an[1] + 11 * S), (ft[0], ft[1] + 11 * S)], fill=(96, 56, 34), width=max(2, int(6 * S)))
        d.line([(an[0], an[1] - 4 * S), (ft[0], ft[1] - 4 * S)], fill=GOLD, width=max(2, int(4 * S)))
    hx, hy = hip
    hem = hy + 66 if sit else -26
    wl, wr = 60, 60
    hl = 122 if sit else 98
    pts = [P((hx - wl, hy - 24)), P((hx + wr, hy - 24)), P((hx + hl, hem)), P((hx - hl, hem))]
    d.polygon(pts, fill=cream)
    _paste_fabric(im, [pts], [], fab)
    for i in range(-3, 4):                                    # drape folds
        x0, x1 = hx + i * 17, hx + i * (24 if sit else 27)
        d.line([P((x0, hy - 20)), P(((x0 + x1) / 2 + 4 * (i % 2 or -1), (hy + hem) / 2)), P((x1, hem - 4))],
               fill=_mix(cream, (120, 70, 50), 0.28), width=max(1, int(3 * S)), joint="curve")
    d.line(pts + [pts[0]], fill=OL, width=max(1, int(ow * 0.9)), joint="curve")
    # border along the hem
    bh = 30
    xl, xr = hl - (hl - wl) * bh / (hem - (hy - 24)), hl - (hl - wr) * bh / (hem - (hy - 24))
    band = [P((hx - xl, hem - bh)), P((hx + xr, hem - bh)), P((hx + hl, hem)), P((hx - hl, hem))]
    bx0, by0 = int(min(x for x, _ in band)), int(min(y for _, y in band))
    bw, bhp = int(max(x for x, _ in band)) - bx0 + 2, int(max(y for _, y in band)) - by0 + 2
    _paste_fabric(im, [band], [], _border_band(bw, bhp, (150, 40, 50)), (bx0, by0))
    d.line(band[:2], fill=GOLD, width=max(1, int(3 * S)))
    d.line(band + [band[0]], fill=OL, width=max(1, int(ow * 0.8)), joint="curve")


def _draw_saree_upper(im, d, J, P, S, look, ow, skin):
    """Blouse, the saree across the chest with its border, and the loose end (pallu) over one shoulder."""
    blouse, cream = look["shirt"], look["pants"]
    hip, top, shl, shr = J["hip"], J["top"], J["sh_l"], J["sh_r"]
    size = im.size
    # blouse
    polys = [[P(shl), P(shr), P((hip[0] + 46, hip[1] + 8)), P((hip[0] - 46, hip[1] + 8))]]
    circles = [(P(shl), 31 * S), (P(shr), 31 * S)]
    _blob(d, polys, circles, blouse, ow)
    _paste_fabric(im, polys, circles, _fabric("blouse", size, S, blouse))
    fab = _fabric("saree_floral", size, S, cream)
    # the loose end hanging from the shoulder on the viewer's right
    pal = [P((shr[0] - 16, shr[1] - 8)), P((shr[0] + 34, shr[1] + 6)), P((shr[0] + 44, hip[1] + 150)), P((shr[0] - 6, hip[1] + 138))]
    d.polygon(pal, fill=cream)
    _paste_fabric(im, [pal], [], fab)
    d.line([pal[1], pal[2]], fill=(120, 26, 40), width=max(2, int(13 * S)))
    d.line([pal[1], pal[2]], fill=GOLD, width=max(1, int(2.5 * S)))
    d.line(pal + [pal[0]], fill=OL, width=max(1, int(ow * 0.8)), joint="curve")
    # the cloth across the chest, from the right shoulder down to the left hip
    A, B = (top[0] - 8, top[1] + 40), (shr[0] + 12, shr[1] - 6)
    C, D = (hip[0] + 54, hip[1] + 14), (hip[0] - 54, hip[1] + 14)
    chest = [P(A), P(B), P(C), P(D)]
    d.polygon(chest, fill=cream)
    _paste_fabric(im, [chest], [], fab)
    d.line([P(A), P(D)], fill=(120, 26, 40), width=max(2, int(17 * S)), joint="curve")      # the border
    d.line([P((A[0] + 5, A[1] + 3)), P((D[0] + 5, D[1] - 1))], fill=GOLD, width=max(1, int(2.5 * S)))
    for f in (0.2, 0.4, 0.6, 0.8):                                                          # small flowers on it
        x, y = A[0] + (D[0] - A[0]) * f, A[1] + (D[1] - A[1]) * f
        c = P((x + 2, y))
        d.ellipse([c[0] - 4 * S, c[1] - 4 * S, c[0] + 4 * S, c[1] + 4 * S], fill=(232, 196, 120))
    d.line(chest + [chest[0]], fill=OL, width=max(1, int(ow * 0.8)), joint="curve")
    # round neckline
    n = P((top[0], top[1] + 16))
    d.ellipse([n[0] - 30 * S, n[1] - 24 * S, n[0] + 30 * S, n[1] + 24 * S], fill=skin, outline=OL, width=max(1, int(ow * 0.8)))


def draw_sofa(im: Image.Image, k: float, ground: float, x0: float, x1: float, scale: float):
    """Draw a sofa spanning world x0..x1 behind the characters sitting on it."""
    s = scale
    pad = 40
    bx0, by0 = x0 - pad, ground - 420 * s
    layer_w, layer_h = int((x1 - x0 + 2 * pad) * k), int((420 * s + 30) * k)
    layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def R(a, b, c, e, fill, r=0, outline=None, w=0):
        box = [(a - bx0) * k, (b - by0) * k, (c - bx0) * k, (e - by0) * k]
        d.rounded_rectangle(box, radius=r * k, fill=fill, outline=outline, width=int(w * k))

    g = ground
    d.ellipse([(x0 - 10 - bx0) * k, (g - 16 * s - by0) * k, (x1 + 10 - bx0) * k, (g + 14 * s - by0) * k], fill=(0, 0, 0, 55))
    main, dark, light = (238, 222, 182), (226, 206, 160), (250, 238, 206)    # cream cushions
    wood, edge = (150, 88, 40), (104, 60, 26)                                 # wooden frame, like the living room
    R(x0 + 20 * s, g - 30 * s, x0 + 50 * s, g, wood, 0, edge, 3 * s)
    R(x1 - 50 * s, g - 30 * s, x1 - 20 * s, g, wood, 0, edge, 3 * s)
    R(x0, g - 400 * s, x1, g - 100 * s, main, 44 * s, edge, 4 * s)
    R(x0 + 60 * s, g - 125 * s, x1 - 60 * s, g - 28 * s, dark, 16 * s, edge, 4 * s)
    R(x0 + 52 * s, g - 150 * s, x1 - 52 * s, g - 104 * s, light, 18 * s, edge, 4 * s)
    for ax in (x0, x1 - 72 * s):
        R(ax, g - 270 * s, ax + 72 * s, g - 28 * s, wood, 30 * s, edge, 4 * s)
    return layer, (int(bx0 * k), int(by0 * k))


# --------------------------------------------------------------------------
# Character
# --------------------------------------------------------------------------
def draw_character(look: dict, pose: dict, emotion: str, mouth: float, blink: float,
                   k: float, scale: float, ss: int = 2, t: float = 0.0, lipsync: bool = False,
                   ground_shadow: bool = True, viseme=None) -> Image.Image:
    """Return an RGBA layer (BOX_W x BOX_H world px, scaled by k) with the character."""
    if look.get("style") == "clay":                  # the clay-toy 3D character (see clay.py)
        from .clay import draw_clay
        return draw_clay(look, pose, emotion, mouth, blink, k, scale, ss, t, lipsync, ground_shadow, viseme)
    S = scale * look.get("scale", 1.0) * k * ss
    W, H = int(BOX_W * k * ss), int(BOX_H * k * ss)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = ORG_X * k * ss, ORG_Y * k * ss
    ow = max(2.0, 4.2 * S)

    def P(pt):
        return (ox + pt[0] * S, oy + pt[1] * S)

    J = solve(pose)
    sit = bool(pose.get("sit"))
    skin, shirt, pants, hair = look["skin"], look["shirt"], look["pants"], look["hair"]
    hstyle = look.get("hair_style", "spiky")
    female = bool(look.get("female"))
    saree = look.get("outfit") == "saree"
    hoodie = not saree

    if ground_shadow:
        d.ellipse([ox - 150 * S, oy - 10 * S, ox + 150 * S, oy + 16 * S], fill=(0, 0, 0, 55))

    hc = P(J["head"])
    r = HEAD_R * S
    th = -J["head_tilt"]

    def HL(lx, ly):  # head-local (units of r) -> pixels, following the head tilt
        x, y = lx * r, ly * r
        return (hc[0] + x * math.cos(th) - y * math.sin(th),
                hc[1] + x * math.sin(th) + y * math.cos(th))

    sprite, lips = _pick_sprite(look, emotion, pose, mouth, lipsync, t, viseme) if look.get("sprite") else (None, False)
    back, front = _hair_polys(hstyle, HL)
    if sprite is not None:
        front = []                      # the picture has its own front hair; keep long hair behind the head
    for poly in back:
        _poly(d, poly, hair, ow)

    # legs: jeans + sneakers (the saree covers them for Maa)
    for n in (() if saree else ("l", "r")):
        _shapes(d, [("cap", P(J["hp_" + n]), P(J["kn_" + n]), (46 if sit else 44) * S),
                    ("cap", P(J["kn_" + n]), P(J["an_" + n]), 38 * S)], pants, ow)
        an, ft = P(J["an_" + n]), P(J["ft_" + n])
        _shapes(d, [("cap", an, ft, 32 * S)], SHOE, ow)
        sole = (0, 12 * S)
        d.line([(an[0] + sole[0], an[1] + sole[1]), (ft[0] + sole[0], ft[1] + sole[1])], fill=SOLE, width=max(2, int(8 * S)))

    hip = J["hip"]
    ut, perp = J["up"], J["perp"]
    shl, shr = J["sh_l"], J["sh_r"]
    top = J["top"]
    if saree:
        _draw_saree_lower(im, d, J, P, S, look, sit, ow, skin)
        _draw_saree_upper(im, d, J, P, S, look, ow, skin)
    else:                                       # torso (hoodie) as one outlined blob
        polys = [[P(shl), P(shr), P((hip[0] + 50, hip[1] + 10)), P((hip[0] - 50, hip[1] + 10))]]
        circles = [(P(shl), 31 * S), (P(shr), 31 * S), (P((hip[0] - 36, hip[1] - 2)), 16 * S), (P((hip[0] + 36, hip[1] - 2)), 16 * S)]
        for sx in (-1, 1):
            circles.append((P((top[0] + sx * 24, top[1] + 12)), 27 * S))
        _blob(d, polys, circles, shirt, ow)
    if hoodie:
        dk = _dark(shirt, 0.72)

        def along(f, off=0.0):
            return P((hip[0] + ut[0] * TORSO * f + perp[0] * off, hip[1] + ut[1] * TORSO * f + perp[1] * off))
        d.line([along(0.97), along(0.0)], fill=dk, width=max(2, int(4 * S)))
        d.line([along(0.30, -40), along(0.50, -36), along(0.50, 36), along(0.30, 40)], fill=dk, width=max(2, int(4 * S)), joint="curve")
        d.line([along(0.50, -36), along(0.50, 36)], fill=dk, width=max(2, int(4 * S)))
        vn = [P((top[0] - 27, top[1] + 4)), P((top[0] + 27, top[1] + 4)), P((top[0], top[1] + 58))]
        d.polygon(vn, fill=skin)
        d.line(vn[:2] + [vn[2]] + [vn[0]], fill=OL, width=max(1, int(ow * 0.8)), joint="curve")
        for sx in (-1, 1):
            a, b = along(0.86, sx * 15), along(0.64, sx * 17)
            d.line([a, b], fill=(250, 250, 252), width=max(2, int(5 * S)))
    _shapes(d, [("cap", P(J["top"]), hc, 40 * S)], skin, ow)

    if sprite is None:          # fallback when a face picture is missing: draw the face in code
        for sx in (-1, 1):
            ex, ey = HL(sx * 1.0, 0.12)
            d.ellipse([ex - 0.2 * r, ey - 0.25 * r, ex + 0.2 * r, ey + 0.25 * r], fill=skin, outline=OL, width=max(1, int(ow * 0.8)))
            d.ellipse([ex - 0.08 * r, ey - 0.1 * r, ex + 0.08 * r, ey + 0.12 * r], fill=_mix(skin, OL, 0.18))
        d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=skin, outline=OL, width=max(2, int(ow)))
        for poly in front:
            _poly(d, poly, hair, ow)
        _draw_face(d, HL, r, ow, hair, skin, emotion, mouth, blink, pose, t, female)
    else:  # head picture from the character sheet, scaled to the rig's head and tilted with it
        sw, sh = sprite.size
        f = 3.84 * r / sw                       # picture width on screen = 3.84 head-radii
        squash = 1.0 if lips else 1 + 0.05 * mouth   # no lip-sync: a little stretch while sounding
        spr = sprite.resize((max(2, int(sw * f)), max(2, int(sh * f * squash))), Image.LANCZOS)
        ax, ay = spr.width * 0.5, spr.height * look.get("anchor_y", 0.57)
        pad = Image.new("RGBA", (int(2 * max(ax, spr.width - ax)) + 4, int(2 * max(ay, spr.height - ay)) + 4), (0, 0, 0, 0))
        pad.paste(spr, (int(pad.width / 2 - ax), int(pad.height / 2 - ay)))
        pad = pad.rotate(math.degrees(J["head_tilt"]), resample=Image.BICUBIC)
        im.paste(pad, (int(hc[0] - pad.width / 2), int(hc[1] + 0.05 * r - pad.height / 2)), pad)

    # arms (sleeves), props and hands go in front of the face (drinking, thinking, facepalm)
    sleeve = shirt if hoodie else skin
    for n in ("l", "r"):
        if saree:                               # short blouse sleeve, bare forearm with gold bangles
            sh_, el_, wr_ = P(J["sh_" + n]), P(J["el_" + n]), P(J["wr_" + n])
            _shapes(d, [("cap", sh_, el_, 34 * S), ("cap", el_, wr_, 28 * S)], skin, ow)
            mid = (sh_[0] + (el_[0] - sh_[0]) * 0.5, sh_[1] + (el_[1] - sh_[1]) * 0.5)
            _shapes(d, [("cap", sh_, mid, 36 * S)], shirt, ow)
            fx, fy = wr_[0] - el_[0], wr_[1] - el_[1]
            fl = math.hypot(fx, fy) or 1.0
            ux, uy = fx / fl, fy / fl
            for f in (0.18, 0.28):
                bx, by = wr_[0] - ux * f * fl * 0.6, wr_[1] - uy * f * fl * 0.6
                d.line([(bx - uy * 15 * S, by + ux * 15 * S), (bx + uy * 15 * S, by - ux * 15 * S)], fill=GOLD, width=max(2, int(5 * S)))
            continue
        _shapes(d, [("cap", P(J["sh_" + n]), P(J["el_" + n]), 34 * S), ("cap", P(J["el_" + n]), P(J["wr_" + n]), 29 * S)],
                sleeve, ow)
        if hoodie:  # cuff
            e, w_ = P(J["el_" + n]), P(J["wr_" + n])
            dx, dy = w_[0] - e[0], w_[1] - e[1]
            ln = math.hypot(dx, dy) or 1
            cf = (w_[0] - dx / ln * 9 * S, w_[1] - dy / ln * 9 * S)
            d.line([cf, w_], fill=_dark(shirt, 0.8), width=max(2, int(31 * S)))
    prop = pose.get("prop")
    if prop:
        _draw_prop(d, prop, J, S, P, pose, t)
    for n in ("l", "r"):
        _hand(d, pose.get("hand_" + n, "relaxed"), P(J["wr_" + n]), P(J["el_" + n]), S, skin, ow)

    _draw_fx(d, HL, r, ow, emotion, pose, t)

    out_w, out_h = int(BOX_W * k), int(BOX_H * k)
    return im.resize((out_w, out_h), Image.LANCZOS)
