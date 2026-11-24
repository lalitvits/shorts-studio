"""Flat cartoon style: simple vector characters, animated backgrounds and an automatic camera.

Everything here is drawn from shapes (no picture files), in the style of flat 2D street cartoons:
outlined characters (uncle in a cap and vest, aunty, boy, dog, cat), a city street with cars and birds,
and a camera that cuts between wide shots, singles, over-the-shoulder shots and close-ups, with a slow
drift inside every shot.

A scene uses this style when its background is one of the flat backgrounds or when any of its characters
has a flat look. Older looks (Rahul, Priya, ...) are redrawn as flat people with their own colours.
"""
from __future__ import annotations

import math
import random
import zlib
from collections import OrderedDict
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .backgrounds import get_background, stamp as bg_stamp
from .catalog import BUILD_VALUES, FLAT_BACKGROUNDS, HEIGHT_VALUES, LOOKS, OUTFIT_COLORS
from .places import PLACES, animate as animate_place, draw_static as draw_place
from .realms import REALMS, animate as animate_realm, draw_static as draw_realm
from .rig import KEEP_EMOTION, PERSISTENT, blink_amount
from . import bag, cinema, kitchen, stick

OUT = (36, 31, 32)          # outline colour
OL = 5.5                    # outline width (world units)
FW, FH = 1080, 1920         # frame in world units
STRONG = {"angry", "shocked", "surprised", "crying", "laughing", "scared", "excited"}
SHOTS = ("auto", "wide", "single", "ots", "close")
PHONE_ACTIONS = {"use_phone", "sit_phone", "phone_call"}
# actions a character keeps doing while someone else talks (on top of the rig's long activities)
FLAT_PERSIST = PERSISTENT | {"cook", "hold_jug", "lower_jug", "hand_on_shoulder", "look_camera", "go_to_bag"} | \
    stick.STAYS | stick.LOOPS
TWO_PERSON = {"grab_hand", "hand_on_shoulder"} | stick.TWO_PERSON
# actions that need the whole body in the shot (no medium shot from the knees up)
FULL_BODY = {"walk", "walk_in", "walk_out", "run_in", "run_out", "jump", "dance", "sit", "sit_phone", "sit_tea",
             "sit_read", "sit_eat", "sit_sleep", "ride_in", "ride_out", "ride_cycle", "step_back", "appear",
             "go_to_bag", "cook", "turn_off_gas", "cover_kadhai", "hold_jug", "lower_jug", "throw"} | set(stick.SLAPSTICK)
SMOOTH_ACTIONS = {"eat", "sit_eat", "drink_tea", "sit_tea", "cook"} | set(stick.SLAPSTICK)   # drawn at 15 poses a second even when silent            # the actor walks up to the nearest other character
MOVE_S = 0.5                                              # seconds that walk-up takes


def three_d_unit():
    from .three_d import UNIT
    return UNIT


def _h(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def _mix(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ===================================================================== looks
def flat_spec(look: dict) -> dict:
    """The flat drawing recipe for any look (flat looks have their own; older looks get one from their colours)."""
    if look.get("style") in ("flat", "3d"):
        return look["flat"]
    fem = bool(look.get("female"))
    if look.get("outfit") == "saree":
        return dict(kind="human", skin=(240, 192, 152), top="kurta", top_color=(236, 222, 190), accent=(150, 40, 50),
                    bottom="dress", bottom_color=(150, 40, 50), hat=None, hair="bun", hair_color=(150, 150, 160),
                    mustache=False, female=True, height=0.95, bindi=True)
    return dict(kind="human", skin=look.get("skin", (200, 140, 95)),
                top="kurta" if fem else "tshirt", top_color=look.get("shirt", (60, 120, 200)),
                accent=_mix(look.get("shirt", (60, 120, 200)), 0.7),
                bottom="dress" if fem else "pants", bottom_color=look.get("pants", (40, 50, 70)), hat=None,
                hair="long" if fem else "short", hair_color=look.get("hair", (50, 35, 28)),
                mustache=False, female=fem, height=0.97 * look.get("scale", 1.0), bindi=fem)


def char_spec(c: dict) -> dict:
    """A character's drawing recipe with their own height, build and outfit colour on top of the look's."""
    sp = dict(flat_spec(LOOKS[c["look"]]))
    if sp.get("kind") == "3d":
        sp["fallback"] = dict(sp["fallback"])
    h, b, o = c.get("height"), c.get("build"), c.get("outfit")
    base = sp.get("height", 1.0)
    if h in HEIGHT_VALUES:
        sp["height"] = HEIGHT_VALUES[h]
    elif isinstance(h, (int, float)) and h:
        sp["height"] = base * h                       # a number: relative (1.1 = 10% taller)
    if b in BUILD_VALUES:
        sp["build"] = BUILD_VALUES[b]
    elif isinstance(b, (int, float)) and b:
        sp["build"] = b
    if o and isinstance(OUTFIT_COLORS.get(o), tuple):
        sp["top_color"] = OUTFIT_COLORS[o]
        if sp.get("kind") == "3d":
            sp["fallback"]["top_color"] = OUTFIT_COLORS[o]
    return sp


# things a character holds (PROP_LABELS): which hand pose goes with each
ONE_HAND = {"phone": ("ik", 62, -650), "glass": ("ik", 62, -640), "bottle": ("ik", 62, -640), "cup": ("ik", 50, -690),
            "flowers": ("ik", 60, -680), "thali": ("ik", 80, -690), "chappal": ("fk", 30, 20),
            "umbrella": ("ik", 36, -790), "suitcase": ("fk", 14, 4), "lathi": ("fk", 12, -6), "bag": None,
            "cutting_chai": ("ik", 56, -660), "kulhad": ("ik", 56, -660), "veg_basket": ("fk", 18, 6),
            "sabzi_bag": ("fk", 14, 4)}
FOODS = {"samosa", "jalebi", "vada_pav", "banana", "apple", "mango", "orange", "grapes", "watermelon", "tomato", "onion",
         "potato", "carrot", "brinjal", "chilli", "cabbage", "cucumber", "lemon", "cauliflower", "bhindi", "garlic", "peas",
         "bhutta", "coconut"}
for _f in FOODS:
    ONE_HAND[_f] = ("ik", 62, -660)
# (the left arm's x is mirrored: a positive x is out to the left)
TWO_HAND = {"book": (("ik", -55, -700), ("ik", 55, -700)), "newspaper": (("ik", 130, -720), ("ik", 130, -720)),
            "laptop": (("ik", 70, -690), ("ik", 70, -690)), "parcel": (("ik", -48, -610), ("ik", 48, -610)),
            "jug": (("ik", 0, -690), ("ik", 110, -720)), "plate_samosa": (("ik", 20, -640), ("ik", 80, -640))}
BUSY_HANDS = {"clap", "cry", "facepalm", "wipe_tears", "punch", "slap", "throw", "grab_hand", "cover_kadhai",
              "hold_jug", "lower_jug", "turn_off_gas", "cook", "use_phone", "sit_phone", "phone_call", "read_book",
              "sit_read", "drink_tea", "sit_tea", "eat", "sit_eat", "hold_parcel", "hide_behind", "think",
              "arms_crossed", "cheer", "dance", "jump", "stop2", "step_back", "hand_on_shoulder", "ride"}


def hold_prop(pose: dict, prop: str, action: str):
    """Put the held prop in the character's hands (keeps the action's own prop when it has one)."""
    if prop in ("glass", "bottle", "cutting_chai", "kulhad") and pose.get("prop") == "cup":   # drinking from it
        pose["prop"] = prop
        return
    if prop in FOODS and pose.get("prop") == "snack":                  # eating it
        pose["prop"] = prop
        return
    if prop == "cycle":
        if not pose.get("ride"):
            pose["cycle"] = True
            if action not in BUSY_HANDS:
                pose["R"] = ("ik", 150, -500)
        return
    if pose.get("prop") or action in BUSY_HANDS:
        if prop == "bag":
            pose["bag"] = True
        return
    if prop == "bag":
        pose["bag"] = True
    elif prop == "lathi":
        pose["lathi"] = True
    elif prop in TWO_HAND:
        pose["L"], pose["R"] = TWO_HAND[prop]
        pose["prop"] = prop
    elif ONE_HAND.get(prop):
        pose["R"] = ONE_HAND[prop]
        pose["prop"] = "phone_hand" if prop == "phone" else prop


def is_flat_look(look_id: str) -> bool:
    return LOOKS.get(look_id, {}).get("style") in ("flat", "3d")


# ===================================================================== pen
class Pen:
    """Draws in character units: origin at the feet, y up is negative. s = pixels per unit."""

    def __init__(self, im, ox, oy, s):
        self.d = ImageDraw.Draw(im)
        self.ox, self.oy, self.s = ox, oy, s

    def p(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]) + 0.01, max(a[1], b[1]) + 0.01]

    def wd(self, w):
        return max(1, round(w * self.s))

    def ellipse(self, x0, y0, x1, y1, fill, ol=OL, color=OUT):
        self.d.ellipse(self.box(x0, y0, x1, y1), fill=fill, outline=color if ol else None, width=self.wd(ol) if ol else 0)

    def circle(self, cx, cy, r, fill, ol=OL, color=OUT):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, fill, ol, color)

    def poly(self, pts, fill, ol=OL, color=OUT):
        q = [self.p(*a) for a in pts]
        self.d.polygon(q, fill=fill)
        if ol:
            self.d.line(q + [q[0], q[1]], fill=color, width=self.wd(ol), joint="curve")

    def line(self, pts, fill, w):
        q = [self.p(*a) for a in pts]
        self.d.line(q, fill=fill, width=self.wd(w), joint="curve")
        r = w * self.s / 2
        for x, y in (q[0], q[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def limb(self, pts, w, fill, ol=OL):
        """A thick outlined stroke with round ends (arms, legs, tails)."""
        self.line(pts, OUT, w + 2 * ol)
        self.line(pts, fill, w)

    def arc(self, x0, y0, x1, y1, a0, a1, w, color=OUT):
        self.d.arc(self.box(x0, y0, x1, y1), a0, a1, fill=color, width=self.wd(w))

    def pie(self, x0, y0, x1, y1, a0, a1, fill, ol=OL):
        self.d.pieslice(self.box(x0, y0, x1, y1), a0, a1, fill=fill, outline=OUT if ol else None,
                        width=self.wd(ol) if ol else 0)


def _sup(cx, cy, a, b, n=2.6, steps=56):
    pts = []
    for i in range(steps):
        th = 2 * math.pi * i / steps
        c, s = math.cos(th), math.sin(th)
        pts.append((cx + a * math.copysign(abs(c) ** (2 / n), c), cy + b * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def _ik(sx, sy, tx, ty, l1, l2, side, down=False):
    """Elbow position for a two-bone arm reaching (tx, ty); the elbow bends outward (or down, for hand-to-mouth:
    the elbow drops in front of the chest and the forearm comes up from below, not across the face)."""
    dx, dy = tx - sx, ty - sy
    d = max(abs(l1 - l2) + 1, min(l1 + l2 - 0.5, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    a = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    c1 = (sx + l1 * math.cos(base + a), sy + l1 * math.sin(base + a))
    c2 = (sx + l1 * math.cos(base - a), sy + l1 * math.sin(base - a))
    e = (c1 if c1[1] > c2[1] else c2) if down else (c1 if c1[0] * side > c2[0] * side else c2)
    k = d / max(1e-6, math.hypot(dx, dy))
    return e, (sx + dx * k, sy + dy * k)


def _fk(sx, sy, a_deg, e_deg, l1, l2, side):
    a = math.radians(a_deg)
    ex, ey = sx + l1 * side * math.sin(a), sy + l1 * math.cos(a)
    b = math.radians(a_deg + e_deg)
    return (ex, ey), (ex + l2 * side * math.sin(b), ey + l2 * math.cos(b))


# ===================================================================== poses
HIP_T = ("ik", 126, -520)


def _talk_style(key: str) -> str:
    return ["hips_point", "hips_point", "hips", "explain", "point", "hips"][_h(key) % 6]


def pose_for(action: str, emotion: str, t: float, speaking: bool, key: str = "") -> dict:
    """Arms, body offsets and prop for a flat human. Arm specs are for the right arm (side +1)."""
    s = math.sin
    p = dict(L=("fk", 12, -6), R=("fk", 12, -6), dx=0.0, dy=3 * s(t * 2.3), head_dx=0.0, head_dy=0.0,
             walk=0.0, prop=None, eyes_dir=0.0)
    if action == "talk":
        action = {"angry": "hips_point", "laughing": "hips", "crying": "cry", "scared": "stop2",
                  "proud": "hips", "thinking": "think", "confused": "shrug", "excited": "explain"}.get(
            emotion, _talk_style(key))
    elif action == "idle":
        action = {"angry": "hips", "proud": "hips", "crying": "cry", "thinking": "think", "scared": "stop2",
                  "laughing": "hips", "bored": "arms_crossed"}.get(emotion, "rest")
    if action == "rest":
        pass
    elif action == "hips":
        p["L"] = p["R"] = HIP_T
    elif action == "hips_point":
        p["L"] = HIP_T
        p["R"] = ("fk", 96 + 5 * s(t * 5), -6 + 6 * s(t * 3))
    elif action == "point":
        p["R"] = ("fk", 96 + 5 * s(t * 5), -6 + 6 * s(t * 3))
    elif action == "punch":                 # same rhythm as the 3D punch and its hit sound
        out = (t * 2.4) % 1 < 0.4
        p["R"] = ("fk", 92, -4) if out else ("fk", 50, -118)
        p["L"] = ("fk", 45, -122)
        p["dx"] = 22.0 if out else 0.0
    elif action == "slap":
        swung = (t * 1.3) % 1 >= 0.45
        p["R"] = ("fk", 72, -25) if swung else ("fk", 140, 15)
        p["L"] = HIP_T
        p["dx"] = 12.0 if swung else 0.0
    elif action == "explain":
        w = 12 * s(t * 4.5)
        p["L"] = ("fk", 40, 62 + w)
        p["R"] = ("fk", 40, 62 - w)
    elif action == "wave":
        p["R"] = ("fk", 150, 22 + 28 * s(t * 9))
        p["L"] = HIP_T
    elif action in ("think",):
        p["R"] = ("ik", 32, -812)
        p["L"] = ("ik", 60, -650)
        p["eyes_dir"] = 1.0
    elif action == "facepalm":
        p["R"] = ("ik", 18, -905)
        p["head_dy"] = 10
    elif action in ("thumbs_up", "ok_sign"):
        p["R"] = ("fk", 70, 70)
        p["L"] = HIP_T
    elif action == "stop":
        p["R"] = ("fk", 85, 70)
    elif action == "stop2":
        p["L"] = p["R"] = ("fk", 70, 80 + 5 * s(t * 14))
    elif action == "arms_crossed":
        p["L"] = ("ik", -50, -640)
        p["R"] = ("ik", -40, -660)
    elif action == "shrug":
        p["L"] = p["R"] = ("fk", 48, 85)
        p["head_dx"] = 6 * s(t * 3)
    elif action == "look_around":
        p["head_dx"] = 14 * s(t * 2.2)
        p["eyes_dir"] = s(t * 2.2)
    elif action == "walk":
        p["walk"] = t
        p["L"] = ("fk", 10 + 18 * s(t * 8), -10)
        p["R"] = ("fk", 10 - 18 * s(t * 8), -10)
        p["dy"] = -6 * abs(s(t * 8))
    elif action == "jump":
        p["dy"] = -110 * abs(s(t * 4.5))
        p["L"] = p["R"] = ("fk", 150, 10)
    elif action in ("cheer", "dance"):
        p["L"] = ("fk", 150 + 10 * s(t * 7), 15)
        p["R"] = ("fk", 150 - 10 * s(t * 7), 15)
        if action == "dance":
            p["dx"] = 22 * s(t * 5)
            p["dy"] = -18 * abs(s(t * 10))
    elif action == "clap":
        g = 18 + 24 * abs(s(t * 9))
        p["L"] = ("ik", -g, -660)
        p["R"] = ("ik", g, -660)
    elif action == "cry":
        p["L"] = ("ik", -38, -890)
        p["R"] = ("ik", 38, -890)
        p["head_dy"] = 8
        p["dy"] += 4 * s(t * 16)
    elif action in ("use_phone", "sit_phone"):
        p["sit"] = action == "sit_phone"
        p["R"] = ("ik", 30, -700)
        p["L"] = ("ik", -10, -690)
        p["prop"] = "phone"
        p["head_dy"] = 10
    elif action == "wipe_tears":            # rubbing an eye with the back of the hand
        p["R"] = ("ik", 40 + 10 * s(t * 9), -900)
        p["L"] = ("fk", 14, -8)
        p["head_dy"] = 8
    elif action == "hold_parcel":
        p["L"] = ("ik", -48, -610)
        p["R"] = ("ik", 48, -610)
        p["prop"] = "parcel"
    elif action == "hide_behind":           # hands (and the parcel) hidden behind the back
        p["L"] = ("fk", 28, -55)
        p["R"] = ("fk", 28, -55)
        p["arms_behind"] = True
        p["prop"] = "parcel_behind"
        p["dx"] = 4 * s(t * 3)
    elif action == "throw":                 # wind up with a chappal, then throw it at the camera
        if t < 0.5:
            p["R"] = ("fk", 165, 35)
            p["prop"] = "chappal"
        else:
            p["R"] = ("fk", 82, -8)
        p["L"] = HIP_T
    elif action == "phone_call":
        p["R"] = ("ik", 104, -878)
        p["L"] = HIP_T
        p["prop"] = "phone_ear"
    elif action in ("drink_tea", "sit_tea"):
        lift = 0.5 + 0.5 * s(t * 1.3)
        p["R"] = ("ikd", 40, -700 - 110 * lift ** 6)       # elbow down: the cup comes up to the mouth from below
        p["prop"] = "cup"
    elif action in ("read_book", "sit_read"):
        p["L"] = ("ik", -55, -700)
        p["R"] = ("ik", 55, -700)
        p["prop"] = "book"
        p["head_dy"] = 10
    elif action in ("eat", "sit_eat"):     # lift to the mouth, open wide, bite, lower it, chew (a 2.4 s cycle)
        per = 2.4
        u, n = (t % per) / per, int(t // per)
        sm = lambda v: v * v * (3 - 2 * v)          # noqa: E731
        if u < 0.28:
            e = sm(u / 0.28)
            x, y = 72 - 32 * e, -640 - 136 * e
        elif u < 0.48:
            x, y = 40, -776
        elif u < 0.7:
            e = sm((u - 0.48) / 0.22)
            x, y = 40 + 32 * e, -776 + 136 * e
        else:
            x, y = 72, -640
        p["R"] = ("ikd", x, y)                          # elbow down: the hand comes up to the mouth from below
        p["prop"] = "snack"
        p["bite"] = n + (1 if u >= 0.42 else 0)        # the food gets smaller with every bite
        p["chew"] = (0.62 if 0.2 <= u < 0.42 else 0.0 if u < 0.48 else 0.24 * abs(s((u - 0.48) * per * 13)))
        p["head_dy"] = 6 if 0.28 <= u < 0.48 else 0
    elif action in ("sit", "sit_sleep"):
        p["L"] = p["R"] = HIP_T if action == "sit" else ("fk", 12, -6)
        p["sit"] = True
    elif action == "cook":                  # stirring the kadhai with a jhara
        p["R"] = ("fk", 64 + 7 * s(t * 4), 28 + 8 * s(t * 4 + 1))
        p["L"] = ("fk", 16, -10)
        p["prop"] = "ladle"
        p["head_dy"] = 8
        p["eyes_dir"] = 0.6
    elif action == "step_back":             # jumps back from the fire, hands up
        e = min(1.0, t / 0.35)
        p["L"] = p["R"] = ("fk", 72, 84 + 6 * s(t * 15))
        p["dx"] = -80 * (1 - (1 - e) ** 2)
        p["dy"] = -18 * math.sin(math.pi * e)
    elif action == "hold_jug":              # a water jug lifted, about to throw it
        p["L"] = ("ik", 0, -690 - 10 * s(t * 6))
        p["R"] = ("ik", 110, -720 - 10 * s(t * 6))
        p["prop"] = "jug"
    elif action == "lower_jug":             # the jug pushed down, water slopping out
        p["L"] = ("ik", -6, -560)
        p["R"] = ("ik", 70, -560)
        p["prop"] = "jug_low"
        p["head_dy"] = 6
    elif action == "grab_hand":             # grabs someone's hand to stop them
        p["R"] = ("fk", 86, -2)
        p["L"] = ("fk", 40, 30)
        p["dx"] = 12.0
    elif action == "turn_off_gas":          # leans over and turns the knob
        p["R"] = ("fk", 58 + 4 * s(t * 6), 18)
        p["L"] = HIP_T
        p["dy"] = 10.0
        p["head_dy"] = 10
        p["eyes_dir"] = 0.6
    elif action == "cover_kadhai":          # puts a steel thali on the kadhai
        e = min(1.0, t / 0.6)
        p["R"] = ("fk", 110 - 40 * e, 20 - 10 * e)
        p["L"] = ("ik", 50, -700)
        p["prop"] = "thali" if t < 0.65 else None
        p["eyes_dir"] = 0.6
    elif action == "hand_on_shoulder":      # a calm hand on someone's shoulder
        p["R"] = ("fk", 100, -10)
        p["L"] = ("fk", 40, 55 + 6 * s(t * 3))
    elif action in ("ride", "ride_cycle"):  # on a cycle, pedalling
        p["ride"] = t
        p["dy"] = 110 + 4 * s(t * 14)
        p["R"] = ("ik", 150, -600)
        p["L"] = ("ik", -120, -590)          # (left arm: a negative x reaches across to the handlebar)
    elif action == "look_camera":           # looks straight at the camera
        p["L"] = p["R"] = ("fk", 12, -6)
        p["eyes_dir"] = 0.0
    elif action == "go_to_bag":            # walks up to the mystery bag and bends toward it
        p["R"] = ("fk", 62, 38)
        p["L"] = HIP_T
        p["head_dy"] = 12
        p["eyes_dir"] = 0.7
    elif action in stick.SLAPSTICK:         # slip, fall, fly off, faint, chase... (stick.py)
        stick.slapstick_pose(p, action, emotion, t)
    if emotion == "laughing":
        p["dy"] += 6 * s(t * 22)
    if emotion in ("sad", "bored", "sleepy"):
        p["head_dy"] += 8
    if speaking and action not in ("look_around", "dance", "jump"):
        p["head_dx"] += 3 * s(t * 3.1)
    return p


# ===================================================================== faces
def _face_cfg(emotion: str) -> dict:
    c = dict(eyes="open", brow=0, mouth="smile_s", fx=())
    m = {
        "happy": dict(eyes="open", mouth="smile"), "sad": dict(eyes="half", brow=-1, mouth="frown"),
        "worried": dict(brow=-1, mouth="flat", fx=("sweat",)), "angry": dict(brow=1.2, mouth="frown", fx=("vein",)),
        "surprised": dict(eyes="wide", brow=-1.4, mouth="o"), "shocked": dict(eyes="wide", brow=-1.6, mouth="o"),
        "laughing": dict(eyes="happy", mouth="laugh"), "crying": dict(eyes="closed", brow=-1.2, mouth="cry", fx=("tears",)),
        "scared": dict(eyes="wide", brow=-1.2, mouth="o", fx=("sweat",)), "excited": dict(eyes="wide", brow=-1, mouth="laugh"),
        "sleepy": dict(eyes="closed", mouth="flat", fx=("zzz",)), "embarrassed": dict(eyes="happy", mouth="smile_s", fx=("blush", "sweat")),
        "confused": dict(brow="confused", mouth="flat"), "bored": dict(eyes="half", mouth="flat"),
        "in_love": dict(eyes="happy", mouth="smile", fx=("blush",)), "proud": dict(eyes="happy", mouth="smile"),
        "disgusted": dict(eyes="half", brow=1, mouth="frown"), "thinking": dict(eyes="up", mouth="flat"),
        "relieved": dict(eyes="happy", mouth="smile"),
    }.get(emotion, {})
    c.update(m)
    return c


def _eye(pen, x, y, kind, blink, look):
    if blink > 0.5 and kind not in ("happy", "closed"):
        kind = "closed"
    lx = look * 5
    if kind == "open" or kind == "up":
        dy = -6 if kind == "up" else 0
        pen.ellipse(x - 9 + lx, y - 13 + dy, x + 9 + lx, y + 13 + dy, (28, 24, 24), 0)
        pen.circle(x - 3 + lx, y - 6 + dy, 3.2, (255, 255, 255), 0)
    elif kind == "wide":
        pen.circle(x, y, 17, (255, 255, 255), 4)
        pen.circle(x + lx, y + 1, 8, (28, 24, 24), 0)
    elif kind == "happy":
        pen.arc(x - 16, y - 4, x + 16, y + 22, 200, 340, 6)
    elif kind == "closed":
        pen.arc(x - 16, y - 18, x + 16, y + 6, 25, 155, 6)
    elif kind == "half":
        pen.pie(x - 10 + lx, y - 10, x + 10 + lx, y + 14, 0, 180, (28, 24, 24), 0)
        pen.line([(x - 13, y - 1), (x + 13, y - 1)], OUT, 5)


def _brows(pen, cx, y, brow):
    for side in (-1, 1):
        x = cx + side * 38
        if brow == "confused":
            d_in, d_out = (-14, -8) if side < 0 else (4, 2)
        else:
            d_in, d_out = 12 * brow, -6 * brow
        pen.line([(x + side * 20, y + d_out), (x - side * 18, y + d_in)], OUT, 8)


def _mouth(pen, cx, cy, kind, m, t):
    if kind == "laugh" and m < 0.35:
        m = 0.45 + 0.25 * abs(math.sin(t * 11))
    if kind == "cry" and m < 0.2:
        m = 0.25
    if m > 0.08:
        w = 32 + 8 * m
        h = 7 + 30 * m
        pen.ellipse(cx - w, cy - h, cx + w, cy + h, (110, 26, 34), 4.5)
        pen.ellipse(cx - w * 0.55, cy + h * 0.05, cx + w * 0.55, cy + h * 0.85, (232, 110, 120), 0)
        if h > 18:
            pen.ellipse(cx - w * 0.6, cy - h * 0.92, cx + w * 0.6, cy - h * 0.55, (250, 250, 245), 0)
        return
    if kind in ("smile", "laugh"):
        pen.arc(cx - 30, cy - 24, cx + 30, cy + 12, 25, 155, 6)
    elif kind == "smile_s":
        pen.arc(cx - 22, cy - 16, cx + 22, cy + 6, 30, 150, 5.5)
    elif kind in ("frown", "cry"):
        pen.arc(cx - 26, cy - 2, cx + 26, cy + 26, 205, 335, 6)
    elif kind == "o":
        pen.ellipse(cx - 12, cy - 14, cx + 12, cy + 14, (110, 26, 34), 4.5)
    else:
        pen.line([(cx - 20, cy), (cx + 20, cy)], OUT, 5.5)


def _effects(pen, fx, hx, hy, r, t, sides=(-1, 1)):
    if "tears" in fx:
        for side in sides:
            for k in range(2):
                ph = (t * 1.6 + k * 0.5 + (0.25 if side > 0 else 0)) % 1.0
                x, y = hx + side * (40 + 18 * ph), hy - 5 + 140 * ph
                pen.ellipse(x - 7, y - 9, x + 7, y + 9, (110, 180, 240), 2.5, (60, 120, 190))
            pen.line([(hx + side * 40, hy + 8), (hx + side * 44, hy + 50)], (140, 200, 245), 7)
    if "sweat" in fx:
        y = hy - r * 0.6 + 8 * math.sin(t * 3)
        pen.poly([(hx + r * 0.95, y - 26), (hx + r * 0.95 + 13, y + 2), (hx + r * 0.95 - 13, y + 2)], (150, 205, 245), 3)
        pen.circle(hx + r * 0.95, y + 4, 13, (150, 205, 245), 3, (60, 120, 190))
    if "vein" in fx:
        x, y = hx + r * 0.75, hy - r * 0.95
        k = 1 + 0.12 * math.sin(t * 12)
        red = (220, 40, 40)
        for ax, ay in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            pen.arc(x + ax * 14 * k - 12, y + ay * 14 * k - 12, x + ax * 14 * k + 12, y + ay * 14 * k + 12,
                    {(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(ax, ay)],
                    {(-1, -1): 90, (1, -1): 180, (-1, 1): 360, (1, 1): 270}[(ax, ay)], 6, red)
    if "blush" in fx:
        for side in (-1, 1):
            pen.ellipse(hx + side * 62 - 20, hy + 30, hx + side * 62 + 20, hy + 46, (240, 140, 140), 0)
    if "zzz" in fx:
        for k in range(3):
            ph = (t * 0.6 + k / 3) % 1.0
            x, y, z = hx + r * 0.9 + 60 * ph, hy - r - 100 * ph, 10 + 10 * ph
            pen.line([(x - z, y - z), (x + z, y - z), (x - z, y + z), (x + z, y + z)], (60, 60, 90), 5)


# ===================================================================== humans
def _hair_back(pen, sp, hx, hy, r):
    hc = sp["hair_color"]
    if sp["hair"] == "long":
        pen.ellipse(hx - r * 1.18, hy - r * 1.05, hx + r * 1.18, hy + r * 1.75, hc)
    if sp["hair"] == "bun":
        pen.circle(hx, hy - r * 1.02, r * 0.45, hc)


def _hair_front(pen, sp, hx, hy, r, back):
    hc = sp["hair_color"]
    if sp["hair"] in ("quiff", "side", "spiky"):          # young styles: short sides, styled top
        if back:
            pen.pie(hx - r * 1.02, hy - r * 1.06, hx + r * 1.02, hy + r * 0.95, 180, 360, hc)
            pen.ellipse(hx - r * 1.02, hy - r * 0.35, hx + r * 1.02, hy + r * 0.55, hc, 0)
            return
        pen.pie(hx - r * 1.04, hy - r * 1.08, hx + r * 1.04, hy + r * 0.42, 180, 360, hc)
        hl = _mix(hc, 1.6)
        if sp["hair"] == "quiff":                           # swept up and back at the front
            pen.poly([(hx - r * 0.75, hy - r * 0.62), (hx - r * 0.45, hy - r * 1.32), (hx + r * 0.1, hy - r * 1.55),
                      (hx + r * 0.7, hy - r * 1.38), (hx + r * 0.98, hy - r * 0.86), (hx + r * 0.35, hy - r * 0.95),
                      (hx - r * 0.2, hy - r * 0.78)], hc)
            pen.arc(hx - r * 0.3, hy - r * 1.5, hx + r * 0.7, hy - r * 0.9, 200, 300, 5, hl)
        elif sp["hair"] == "side":                          # a fringe swept to one side
            pen.poly([(hx - r * 1.0, hy - r * 0.42), (hx - r * 0.55, hy - r * 1.18), (hx + r * 0.3, hy - r * 1.25),
                      (hx + r * 1.0, hy - r * 0.78), (hx + r * 0.72, hy - r * 0.32), (hx + r * 0.05, hy - r * 0.58),
                      (hx - r * 0.62, hy - r * 0.2)], hc)
            pen.arc(hx - r * 0.6, hy - r * 1.15, hx + r * 0.9, hy - r * 0.4, 210, 320, 4.5, hl)
        else:                                               # spiky
            for k in range(-3, 4):
                a = math.radians(-90 + k * 24)
                bx, by = hx + r * 0.78 * math.cos(a), hy + r * 0.78 * math.sin(a)
                tx, ty = hx + r * 1.42 * math.cos(a), hy + r * 1.42 * math.sin(a)
                nx, ny = -math.sin(a) * r * 0.22, math.cos(a) * r * 0.22
                pen.poly([(bx - nx, by - ny), (tx, ty), (bx + nx, by + ny)], hc)
        return
    if sp["hair"] == "short":
        if back:
            pen.pie(hx - r * 1.02, hy - r * 1.06, hx + r * 1.02, hy + r * 0.95, 180, 360, hc)
            pen.ellipse(hx - r * 1.02, hy - r * 0.35, hx + r * 1.02, hy + r * 0.55, hc, 0)
        else:
            pen.pie(hx - r * 1.04, hy - r * 1.1, hx + r * 1.04, hy + r * 0.5, 180, 360, hc)
            for k in range(-2, 3):
                pen.poly([(hx + k * 30 - 22, hy - r * 0.32), (hx + k * 30 + 22, hy - r * 0.32),
                          (hx + k * 30 + 4, hy - r * 0.05)], hc, 0)
    elif sp["hair"] in ("long", "bun"):
        if back:
            pen.circle(hx, hy, r * 1.02, hc)
            if sp["hair"] == "bun":
                pen.circle(hx, hy - r * 0.55, r * 0.42, _mix(hc, 0.85))
        else:
            pen.pie(hx - r * 1.05, hy - r * 1.08, hx + r * 1.05, hy + r * 0.62, 180, 360, hc)


def _cap(pen, sp, hx, hy, r, back):
    c = sp.get("hat_color", (214, 60, 45))
    dark = _mix(c, 0.8)
    if back:
        pen.pie(hx - r * 1.07, hy - r * 1.18, hx + r * 1.07, hy + r * 0.38, 180, 360, c)
        pen.ellipse(hx - r * 1.12, hy - r * 0.5, hx + r * 1.12, hy - r * 0.18, dark)
        pen.poly([(hx - r * 0.38, hy - r * 0.38), (hx + r * 0.38, hy - r * 0.38), (hx + r * 0.26, hy - r * 0.05),
                  (hx - r * 0.26, hy - r * 0.05)], _mix(c, 0.62), 4)
    else:
        pen.pie(hx - r * 1.06, hy - r * 1.2, hx + r * 1.06, hy + r * 0.2, 180, 360, c)
        pen.ellipse(hx - r * 1.14, hy - r * 0.62, hx + r * 1.14, hy - r * 0.34, dark)
        pen.circle(hx, hy - r * 1.18, r * 0.08, dark, 3)


def _police_cap(pen, sp, hx, hy, r, back):
    """Peaked police cap: crown, coloured band, black visor and a badge."""
    c = sp.get("hat_color", (196, 170, 112))
    band = sp.get("band_color", (196, 40, 40))
    pen.ellipse(hx - r * 1.18, hy - r * 1.42, hx + r * 1.18, hy - r * 0.86, c)            # crown (top)
    pen.poly([(hx - r * 1.02, hy - r * 1.12), (hx + r * 1.02, hy - r * 1.12), (hx + r * 0.98, hy - r * 0.62),
              (hx - r * 0.98, hy - r * 0.62)], c)
    pen.ellipse(hx - r * 1.16, hy - r * 1.4, hx + r * 1.16, hy - r * 0.94, _mix(c, 1.06), 0)
    pen.poly([(hx - r * 1.0, hy - r * 0.9), (hx + r * 1.0, hy - r * 0.9), (hx + r * 0.99, hy - r * 0.62),
              (hx - r * 0.99, hy - r * 0.62)], band)                                          # band
    if not back:
        pen.pie(hx - r * 1.04, hy - r * 0.86, hx + r * 1.04, hy - r * 0.34, 0, 180, (34, 32, 36))   # visor
        pen.circle(hx, hy - r * 0.96, r * 0.17, (236, 196, 70), 4)                                # badge
        pen.circle(hx, hy - r * 0.96, r * 0.07, (196, 40, 40), 0)


def _beret(pen, sp, hx, hy, r, back):
    c = sp.get("hat_color", (40, 70, 150))
    pen.poly([(hx - r * 1.0, hy - r * 0.72), (hx - r * 0.9, hy - r * 1.18), (hx - r * 0.4, hy - r * 1.42),
              (hx + r * 0.3, hy - r * 1.44), (hx + r * 0.95, hy - r * 1.22), (hx + r * 1.42, hy - r * 0.9),
              (hx + r * 1.5, hy - r * 0.55), (hx + r * 1.2, hy - r * 0.5), (hx + r * 0.95, hy - r * 0.7)], c)  # floppy top
    pen.arc(hx - r * 0.2, hy - r * 1.3, hx + r * 1.3, hy - r * 0.6, 290, 20, 4, _mix(c, 0.7))            # fold
    pen.poly([(hx - r * 1.0, hy - r * 0.86), (hx + r * 1.0, hy - r * 0.86), (hx + r * 0.98, hy - r * 0.6),
              (hx - r * 0.98, hy - r * 0.6)], _mix(c, 0.65))                                  # leather rim
    if not back:
        pen.circle(hx - r * 0.5, hy - r * 0.86, r * 0.16, (236, 196, 70), 4)


def _uniform(pen, sp, back, t):
    """Khaki police shirt (tucked in), belt, pockets, badge, name tag, whistle cord; belly 0..1."""
    tc, belly = sp["top_color"], sp.get("belly", 0.0)
    slim = sp.get("slim", 0.0)                         # 0..1: narrower shirt
    a, b, cy = 135 + 62 * belly - 18 * slim, 168 + 22 * belly, -615 + 18 * belly
    body = _sup(0, cy, a, b, n=2.6 - 0.5 * belly)      # rounder with a belly
    pen.poly(body, tc)
    dark = _mix(tc, 0.78)
    if belly:                                          # the shirt stretches over the belly
        pen.arc(-a * 0.7, cy - 20, a * 0.7, cy + b * 0.98, 20, 160, 4, dark)
    if not back:
        pen.line([(0, -770), (0, -485)], dark, 6)                                           # button placket
        for y in (-730, -670, -610, -550):
            pen.circle(4 * belly * (y + 600) / 100, y, 7, (236, 196, 70), 2.5)
        for side in (-1, 1):                                                                 # collar
            pen.poly([(side * 6, -770), (side * 62, -792), (side * 52, -728)], tc, 4)
            px_ = side * 72                                                                  # chest pockets
            pen.d.rounded_rectangle(pen.box(px_ - 34, -700, px_ + 34, -628), radius=6 * pen.s, fill=tc,
                                    outline=OUT, width=pen.wd(3.5))
            pen.poly([(px_ - 36, -706), (px_ + 36, -706), (px_ + 36, -684), (px_, -676), (px_ - 36, -684)], dark, 3.5)
        pen.poly([(-86, -748), (-60, -760), (-34, -748), (-38, -724), (-60, -714), (-82, -724)], (236, 196, 70), 3)  # badge
        pen.circle(-60, -737, 6, (196, 40, 40), 0)
        pen.d.rounded_rectangle(pen.box(40, -738, 108, -718), radius=3 * pen.s, fill=(30, 30, 34),
                                outline=OUT, width=pen.wd(2))                                 # name tag
        pen.line([(48, -728), (98, -728)], (240, 240, 240), 4)
        pen.line([(-104, -744), (-94, -700), (-72, -666)], (200, 40, 40), 5)                   # whistle cord
        pen.line([(-104, -744), (-90, -704), (-70, -670)], (245, 245, 245), 2.5)
    yb = -484 + 6 * belly                                                                     # belt
    w = a * (1 - min(1.0, abs((yb - cy) / b)) ** 2.6) ** (1 / 2.6) + 2
    pen.poly([(-w, yb - 16), (w, yb - 16), (w * 0.98, yb + 14), (-w * 0.98, yb + 14)], (110, 70, 40), 4)
    if not back:
        pen.d.rounded_rectangle(pen.box(-24, yb - 20, 24, yb + 18), radius=4 * pen.s, fill=(236, 196, 70),
                                outline=OUT, width=pen.wd(3.5))


def _lathi(pen, elbow, hand):
    """The constable's bamboo stick, held in the hand and pointing along the forearm."""
    dx, dy = hand[0] - elbow[0], hand[1] - elbow[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    a = (hand[0] - ux * 60, hand[1] - uy * 60)
    b = (hand[0] + ux * 330, hand[1] + uy * 330)
    pen.limb([a, b], 18, (176, 124, 64), 4)
    for k in (0.2, 0.45, 0.7, 0.92):                                                          # bamboo rings
        x, y = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        pen.line([(x - uy * 10, y + ux * 10), (x + uy * 10, y - ux * 10)], (120, 80, 40), 4)


def _cycle(pen, bx, f, t, spin, color=(214, 60, 52)):
    """A bicycle seen from the side (f = 1: front wheel to the right), wheels turning with spin."""
    rh, fh = (bx - 170 * f, -100), (bx + 170 * f, -100)
    crank, seat, head, bar = (bx + 10 * f, -130), (bx - 40 * f, -360), (bx + 150 * f, -300), (bx + 140 * f, -480)
    for cx, cy in (rh, fh):
        pen.circle(cx, cy, 100, None, 14, (40, 40, 46))
        pen.circle(cx, cy, 86, None, 3, (170, 170, 180))
        for k in range(4):
            a = spin + k * math.pi / 4
            pen.line([(cx - 84 * math.cos(a), cy - 84 * math.sin(a)), (cx + 84 * math.cos(a), cy + 84 * math.sin(a))],
                     (170, 170, 180), 2.5)
        pen.circle(cx, cy, 10, (120, 120, 130), 2)
    for a_, b_ in ((rh, crank), (crank, seat), (seat, rh), (seat, head), (crank, head), (head, fh), (head, bar)):
        pen.limb([a_, b_], 13, color, 3)
    pen.ellipse(seat[0] - 42, seat[1] - 18, seat[0] + 36, seat[1] + 8, (40, 40, 46), 3)          # seat
    pen.limb([(bar[0] - 30 * f, bar[1] + 6), (bar[0] + 20 * f, bar[1] - 4)], 12, (40, 40, 46), 3)   # handlebar
    pen.circle(crank[0], crank[1], 22, (90, 90, 100), 3)
    for k in (0, math.pi):                                                                  # pedals
        a = spin * 1.4 + k
        px, py = crank[0] + 46 * math.cos(a), crank[1] + 46 * math.sin(a)
        pen.line([crank, (px, py)], (90, 90, 100), 6)
        pen.line([(px - 18, py), (px + 18, py)], (40, 40, 46), 9)


def draw_human(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t):
    bw = sp.get("build", 1.0)                       # 0.86 thin .. 1.5 very fat
    if pose.get("cloud"):                            # fighting inside a dust cloud: only the cloud shows
        stick.cartoon_fx(Pen(im, ox, oy, s), set(pose.get("fx", ())), 0, -890, 104, t, sp["skin"])
        return
    if pose.get("cycle") and view != "back":         # standing with a cycle: it is beside them
        _cycle(Pen(im, ox + pose["dx"] * s, oy, s), 300, -1, t, 0.0, sp.get("cycle_color", (214, 60, 52)))
    if pose.get("ride") is not None:                 # riding: the cycle under them
        _cycle(Pen(im, ox + pose["dx"] * s, oy, s), 0, 1, t, pose["ride"] * 7, sp.get("cycle_color", (214, 60, 52)))
    pen = Pen(im, ox + pose["dx"] * s, oy + pose["dy"] * s, s)
    skin, sk_d = sp["skin"], _mix(sp["skin"], 0.85)
    back = view == "back"
    female = sp.get("female")
    dress = sp["bottom"] == "dress"
    hx, hy, r = pose["head_dx"], -890 + pose["head_dy"], 104
    if back:
        hy = -890

    if not back:
        _hair_back(pen, sp, hx, hy, r)

    # legs and shoes
    hip_y = -260 if dress else -470
    wk = pose["walk"]
    lw = 1 + 0.6 * (bw - 1)                          # legs further apart on a wider body
    if pose.get("ride") is not None:                 # pedalling: feet on the pedals, knees bent forward
        for side in (-1, 1):
            a = pose["ride"] * 7 * 1.4 + (0 if side > 0 else math.pi)
            foot = (10 + 46 * math.cos(a), -130 + 46 * math.sin(a) - pose["dy"])
            hip = (side * 30, -300 if dress else hip_y)
            knee, foot = _ik(hip[0], hip[1], foot[0], foot[1], 230, 230, 1)
            col = sp["bottom_color"] if not dress else _mix(sp["bottom_color"], 1.1)
            pen.limb([hip, knee, foot], 38 * lw ** 0.5, col if sp["bottom"] != "shorts" else skin)
            pen.ellipse(foot[0] - 30, foot[1] - 18, foot[0] + 44, foot[1] + 14, sp.get("shoe", (44, 40, 42)))
    for side in ((-1, 1) if pose.get("ride") is None else ()):
        sw = 26 * math.sin(wk * 8) * side if wk else 0
        top, foot = (side * 44 * lw, hip_y), (side * 50 * lw + sw, -34)
        if side > 0 and pose.get("kick"):              # a kick: the right leg swings forward
            ka = math.radians(100 * pose["kick"])
            ll = -34 - hip_y
            foot = (top[0] + ll * math.sin(ka), hip_y + ll * math.cos(ka))
        if sp["bottom"] == "shorts":
            mid = (side * 47 + sw * 0.4, -330)
            pen.limb([mid, foot], 30, skin)
            pen.limb([top, mid], 48, sp["bottom_color"])
        else:
            pen.limb([top, foot], (36 if dress else 40) * lw ** 0.5,
                     sp["bottom_color"] if not dress else _mix(sp["bottom_color"], 1.1))
        if side > 0 and pose.get("kick"):
            pen.ellipse(foot[0] - 34, foot[1] - 20, foot[0] + 50, foot[1] + 20, sp.get("shoe", (44, 40, 42)))
            continue
        pen.ellipse(side * 50 + sw - 42 + side * 8, -46, side * 50 + sw + 42 + side * 8, -6, sp.get("shoe", (44, 40, 42)))

    def _arms():
        sleeve = sp["top"] in ("tshirt", "kurta", "uniform", "hoodie", "open_shirt", "tee_print")
        stc = sp.get("shirt_color", tc) if sp["top"] == "open_shirt" else tc      # sleeve colour
        hands = {}
        for side, key in ((-1, "L"), (1, "R")):
            spec = pose[key]
            sx, sy = side * 110 * (1 + 0.5 * (bw - 1)), -742
            if spec[0] in ("ik", "ikd"):
                elbow, hand = _ik(sx, sy, side * spec[1], spec[2], 150, 142, side, down=spec[0] == "ikd")
            else:
                elbow, hand = _fk(sx, sy, spec[1], spec[2], 150, 142, side)
            pen.limb([(sx, sy), elbow, hand], 30, skin)
            if sleeve:
                k = {"tshirt": 0.42, "uniform": 0.55, "tee_print": 0.42}.get(sp["top"], 0.95)
                mid = (sx + (elbow[0] - sx) * k, sy + (elbow[1] - sy) * k)
                pen.limb([(sx, sy), mid], 44, stc)
                if sp["top"] == "uniform":                     # folded cuff and shoulder strap
                    pen.limb([(sx + (mid[0] - sx) * 0.82, sy + (mid[1] - sy) * 0.82), mid], 46, _mix(tc, 0.85))
                    pen.d.rounded_rectangle(pen.box(sx - 30, sy - 18, sx + 30, sy + 4), radius=5 * pen.s,
                                            fill=_mix(tc, 0.78), outline=OUT, width=pen.wd(3))
                if sp["top"] in ("kurta", "hoodie", "open_shirt"):
                    f = {"hoodie": 0.8, "open_shirt": 0.45}.get(sp["top"], 0.55)       # hoodie: long; shirt: rolled up
                    pen.limb([elbow, (elbow[0] + (hand[0] - elbow[0]) * f, elbow[1] + (hand[1] - elbow[1]) * f)],
                             40 if sp["top"] != "open_shirt" else 44, stc)
                    if sp["top"] == "open_shirt":                    # the rolled cuff
                        cx_, cy_ = elbow[0] + (hand[0] - elbow[0]) * f, elbow[1] + (hand[1] - elbow[1]) * f
                        pen.circle(cx_, cy_, 23, _mix(stc, 0.8), 3)
            if key == "R" and (sp.get("holds") == "lathi" or pose.get("lathi")) and not pose["prop"]:
                _lathi(pen, elbow, hand)
            if key == "R" and not back and pose["prop"] == "phone_ear":      # the phone goes behind the hand
                _prop(pen, "phone_ear", hand)
            hands[key] = hand
            if female:
                bx, by = elbow[0] + (hand[0] - elbow[0]) * 0.8, elbow[1] + (hand[1] - elbow[1]) * 0.8
                pen.circle(bx, by, 14, (226, 180, 60), 3)
            if key == "L" and sp.get("watch"):                   # a wristwatch
                wx, wy = elbow[0] + (hand[0] - elbow[0]) * 0.8, elbow[1] + (hand[1] - elbow[1]) * 0.8
                pen.circle(wx, wy, 17, (40, 40, 48), 3)
                pen.circle(wx, wy, 9, (210, 230, 246), 0)
            pen.circle(hand[0], hand[1], 24, skin)
            if key == "R" and spec[0] == "fk" and 80 < spec[1] < 120 and spec[2] < 20 and not back:   # pointing finger
                ang = math.atan2(hand[1] - elbow[1], hand[0] - elbow[0])
                pen.limb([hand, (hand[0] + 40 * math.cos(ang), hand[1] + 40 * math.sin(ang))], 11, skin, 4)
            if key == "R" and not back and pose["prop"] and pose["prop"] != "phone_ear":
                _prop(pen, pose["prop"], hand, hands.get("L"), skin, pose.get("bite", 0))


    # body (arms hidden behind the back are drawn first)
    tc = sp["top_color"]
    if pose.get("arms_behind"):
        _arms()
        if pose.get("prop") == "parcel_behind" and not back:
            _parcel(pen, 150, -560, 0.9)
    tc = sp["top_color"]
    if sp["top"] == "kurta":
        body = [(-92, -772), (92, -772), (110, -650), (118, -520), (160, -250), (-160, -250), (-118, -520), (-110, -650)]
        body = [(x * (1 + 0.85 * (bw - 1) * (1 if y > -700 else 0.5)), y) for x, y in body]
        pen.poly(body, tc)
        if not back:
            pen.poly([(-88, -770), (-50, -770), (150, -330), (122, -300)], sp.get("accent", _mix(tc, 0.7)), 4)
            pen.line([(-150, -262), (150, -262)], sp.get("accent", _mix(tc, 0.7)), 14)
    elif sp["top"] == "uniform":
        _uniform(pen, dict(sp, belly=max(sp.get("belly", 0.0), min(1.6, (bw - 1) * 2.4)),
                           slim=max(sp.get("slim", 0.0), (1 - bw) * 5)), back, t)
    else:
        fat = max(0.0, bw - 1)
        pen.poly(_sup(0, -615 + 30 * fat, 135 * bw, 168 + 40 * fat, n=max(2.0, 2.6 - 0.9 * fat)), tc)
        if sp["top"] == "vest" and not back:
            pen.pie(-40, -812, 40, -742, 0, 180, skin, 4)
        if sp.get("stripes"):
            for yy in range(-735, -470, 52):
                half = 135 * max(0.0, 1 - abs((yy + 615) / 168) ** 2.6) ** (1 / 2.6) - 10
                if half > 20:
                    pen.line([(-half, yy), (half, yy)], sp["stripes"], 18)
        if sp["top"] == "tshirt" and not back:
            pen.pie(-38, -812, 38, -752, 0, 180, skin, 4)
        if sp["top"] == "tee_print" and not back:          # a graphic tee
            pen.pie(-38, -812, 38, -752, 0, 180, skin, 4)
            ac = sp.get("accent", (250, 250, 250))
            pen.circle(0, -640, 50 * bw, ac, 4)
            pen.poly([(-12, -676), (16, -676), (2, -646), (20, -646), (-14, -598), (-4, -634), (-20, -634)],
                     sp.get("accent2", (230, 60, 60)), 2.5)
        if sp["top"] == "hoodie":                           # hood at the neck, kangaroo pocket, strings
            hood = _mix(tc, 0.82)
            if back:
                pen.poly([(-90, -800), (90, -800), (70, -690), (0, -650), (-70, -690)], hood, 4)
            else:
                pen.ellipse(-104, -830, 104, -742, hood, 4)
                pen.pie(-50, -816, 50, -760, 0, 180, skin, 3)
                for sx_ in (-24, 24):
                    pen.line([(sx_, -770), (sx_ * 1.1, -680)], (245, 245, 245), 5)
                    pen.circle(sx_ * 1.1, -676, 6, (245, 245, 245), 2)
                pen.poly([(-86 * bw, -560), (86 * bw, -560), (104 * bw, -470), (-104 * bw, -470)], hood, 4)
        if sp["top"] == "open_shirt":                       # an open check shirt over the tee
            shc, dark = sp.get("shirt_color", (200, 50, 50)), _mix(sp.get("shirt_color", (200, 50, 50)), 0.6)
            if back:
                pen.poly(_sup(0, -615 + 30 * max(0.0, bw - 1), 138 * bw, 170, n=2.6), shc)
                for x in range(-110, 120, 44):
                    pen.line([(x, -760), (x, -470)], dark, 5)
            else:
                pen.pie(-38, -812, 38, -752, 0, 180, skin, 4)
                for side in (-1, 1):
                    ax = 138 * bw
                    panel = [(side * 60, -776), (side * (ax - 4), -742), (side * ax, -620), (side * (ax - 14), -470),
                             (side * 46, -452), (side * 40, -620)]
                    pen.poly(panel, shc, 4)
                    for x in (side * 70, side * 98):                         # checks
                        pen.line([(x, -750), (x, -470)], dark, 5)
                    for y in (-700, -640, -580, -520):
                        pen.line([(side * 44, y), (side * (ax - 10), y)], dark, 5)
                    pen.poly([(side * 30, -790), (side * 72, -800), (side * 76, -730)], shc, 4)     # collar


    # head (drawn before arms, so hands can touch the face)
    if not back:
        pen.ellipse(hx - r - 22, hy - 24, hx - r + 18, hy + 22, skin)
        pen.ellipse(hx + r - 18, hy - 24, hx + r + 22, hy + 22, skin)
    pen.circle(hx, hy, r, skin)
    if back:
        pen.ellipse(hx - r - 22, hy - 4, hx - r + 18, hy + 40, skin)
        pen.ellipse(hx + r - 18, hy - 4, hx + r + 22, hy + 40, skin)
    if sp["hair"] != "none":
        _hair_front(pen, sp, hx, hy, r, back)
    if sp.get("hat") == "cap":
        _cap(pen, sp, hx, hy, r, back)
    elif sp.get("hat") == "police_cap":
        _police_cap(pen, sp, hx, hy, r, back)
    elif sp.get("hat") == "beret":
        _beret(pen, sp, hx, hy, r, back)

    if not back and sp.get("stubble"):                      # a light beard shadow
        pen.pie(hx - r * 0.8, hy - r * 0.02, hx + r * 0.8, hy + r * 1.0, 0, 180, _mix(skin, 0.86), 0)
        pen.ellipse(hx - r * 0.5, hy + r * 0.48, hx + r * 0.5, hy + r * 0.92, _mix(skin, 0.8), 0)
    if not back:
        cfg = _face_cfg(pose.get("emo") or emotion)
        if pose.get("eyes"):
            cfg["eyes"] = pose["eyes"]
        look = pose.get("eyes_dir", 0.0)
        fx_ = hx + 6
        ey = hy - 4
        popping = "eyes_pop" in pose.get("fx", ())
        for ex in (fx_ - 38, fx_ + 38):
            if popping:
                pen.circle(ex, ey, 12, (40, 30, 30), 0)
            elif not stick.eye_extra(pen, ex, ey, cfg["eyes"], t):
                _eye(pen, ex, ey, cfg["eyes"], blink, look)
        _brows(pen, fx_, ey - 36 - (8 if cfg["eyes"] == "wide" else 0), cfg["brow"])
        pen.arc(fx_ - 12, hy + 8, fx_ + 14, hy + 34, 300, 110, 4.5, _mix(skin, 0.6))
        if sp.get("bindi"):
            pen.circle(fx_, hy - 52, 6, (200, 30, 40), 0)
        if pose.get("chew") is not None and mouth < 0.05:     # eating: open for the bite, then chewing
            mouth = pose["chew"]
        if pose.get("jaw"):                                  # jaw drop: a huge open mouth
            h = 30 + 80 * pose["jaw"]
            pen.ellipse(fx_ - 40, hy + 46, fx_ + 40, hy + 46 + h, (110, 26, 34), 4.5)
            pen.ellipse(fx_ - 22, hy + 46 + h * 0.55, fx_ + 22, hy + 46 + h * 0.95, (232, 110, 120), 0)
        else:
            _mouth(pen, fx_, hy + 72, cfg["mouth"], mouth, t)
        if sp.get("mustache"):
            mc = sp.get("hair_color", (60, 38, 30))
            pen.poly([(fx_ - 50, hy + 54), (fx_ - 30, hy + 36), (fx_, hy + 42), (fx_ + 30, hy + 36), (fx_ + 50, hy + 54),
                      (fx_ + 28, hy + 52), (fx_, hy + 56), (fx_ - 28, hy + 52)], mc, 3)
        if female and cfg["mouth"] in ("smile", "smile_s", "flat") and mouth <= 0.08:
            pass
        _effects(pen, cfg["fx"], fx_, hy, r, t)
        if popping:
            stick.eyes_pop(pen, fx_, ey, t)

    if not pose.get("arms_behind"):
        _arms()
    if pose.get("bag") and not back:                 # shoulder bag on the left hip, strap across the chest
        pen.line([(-70, -770), (110 * bw, -470)], (110, 70, 40), 12)
        pen.d.rounded_rectangle(pen.box(-170 * bw, -520, -60 * bw, -400), radius=12 * pen.s, fill=(150, 96, 56),
                                outline=OUT, width=pen.wd(4))
        pen.line([(-160 * bw, -490), (-70 * bw, -490)], (110, 70, 40), 5)
    if pose.get("fx"):
        stick.cartoon_fx(pen, set(pose["fx"]), hx, hy, r, t, sp["skin"])

PHONE_W, PHONE_H = 82, 160      # one phone size for every action (using it, holding it, a call at the ear)


def _phone_back(pen, cx, cy, w, h, skin=None):
    """A real-sized smartphone seen from the back (what you see when someone looks at their phone):
    dark body, camera module with three lenses and a flash, and the screen's light spilling around the edges."""
    pen.d.rounded_rectangle(pen.box(cx - w / 2 - 7, cy - h / 2 - 7, cx + w / 2 + 7, cy + h / 2 + 7),
                            radius=22 * pen.s, fill=(150, 200, 255))                      # screen light spill
    pen.d.rounded_rectangle(pen.box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=16 * pen.s,
                            fill=(46, 50, 62), outline=OUT, width=pen.wd(4))
    pen.d.rounded_rectangle(pen.box(cx - w / 2 + 6, cy - h / 2 + 6, cx + w / 2 - 6, cy + h / 2 - 6),
                            radius=12 * pen.s, outline=(78, 84, 100), width=pen.wd(2.5))  # edge highlight
    mx, my = cx - w / 2 + 10, cy - h / 2 + 10                                            # camera module
    pen.d.rounded_rectangle(pen.box(mx, my, mx + 40, my + 46), radius=9 * pen.s, fill=(30, 32, 40),
                            outline=(90, 96, 110), width=pen.wd(2))
    for lx, ly in ((mx + 12, my + 13), (mx + 12, my + 33), (mx + 29, my + 23)):
        pen.circle(lx, ly, 7.5, (14, 16, 22), 2, (120, 126, 140))
        pen.circle(lx - 2, ly - 2, 2, (180, 200, 240), 0)
    pen.circle(mx + 30, my + 9, 3, (250, 240, 200), 0)                                  # flash
    pen.circle(cx, cy + 6, 9, (70, 76, 90), 0)                                          # logo
    if skin:                                                                            # fingers around the sides
        for side in (-1, 1):
            for k in range(3):
                fy = cy + h * 0.05 + k * 22
                pen.ellipse(cx + side * (w / 2) - 13, fy - 9, cx + side * (w / 2) + 13, fy + 9, skin, 3)


def _parcel(pen, x, y, k=1.0):
    """A food-delivery parcel: brown box with tape and an orange label."""
    w, h = 150 * k, 110 * k
    pen.d.rounded_rectangle(pen.box(x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=8 * pen.s,
                            fill=(196, 150, 96), outline=OUT, width=pen.wd(4))
    pen.d.rectangle(pen.box(x - 10 * k, y - h / 2, x + 10 * k, y + h / 2), fill=(222, 196, 140))   # tape
    pen.d.rounded_rectangle(pen.box(x + 22 * k, y - 10 * k, x + 64 * k, y + 26 * k), radius=4 * pen.s,
                            fill=(252, 98, 44), outline=OUT, width=pen.wd(2))                   # label


def _chappal(pen, x, y, ang=0.0, k=1.0):
    """A blue rubber chappal (flip-flop) seen from above."""
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda px, py: (x + (px * ca - py * sa) * k, y + (px * sa + py * ca) * k)   # noqa: E731
    sole = [rot(28 * math.cos(u) * (1 + 0.15 * math.sin(u)), 70 * math.sin(u)) for u in
            [i * 2 * math.pi / 24 for i in range(24)]]
    q = [pen.p(*pt) for pt in sole]
    pen.d.polygon(q, fill=(60, 120, 210))
    pen.d.line(q + [q[0]], fill=OUT, width=pen.wd(4), joint="curve")
    pen.line([rot(0, -40), rot(-24, 10)], (240, 240, 240), 9)                            # strap
    pen.line([rot(0, -40), rot(24, 10)], (240, 240, 240), 9)


def _jug(pen, x, y, tilt=0.0, k=1.0):
    """A plastic water jug (blue, see-through, water inside) with a handle."""
    ca, sa = math.cos(tilt), math.sin(tilt)
    rot = lambda px, py: (x + (px * ca - py * sa) * k, y + (px * sa + py * ca) * k)   # noqa: E731
    body = [rot(-52, -70), rot(52, -70), rot(60, 70), rot(-60, 70)]
    pen.poly(body, (150, 200, 240), 4)
    pen.poly([rot(-56, -10), rot(56, -10), rot(60, 70), rot(-60, 70)], (90, 160, 230), 0)
    pen.d.line([pen.p(*rot(-52, -70)), pen.p(*rot(52, -70))], fill=OUT, width=pen.wd(6))
    pen.poly([rot(40, -70), rot(78, -96), rot(56, -60)], (150, 200, 240), 3)             # spout
    pen.arc(*[v for v in (x - 110 * k, y - 50 * k, x - 30 * k, y + 50 * k)], 90, 270, 7, OUT)


def _food(pen, kind, x, y):
    """A food / fruit / vegetable, about hand-sized, centred at (x, y)."""
    if kind == "samosa":
        pen.poly([(x - 44, y + 26), (x + 44, y + 26), (x, y - 56)], (226, 172, 84), 4)
        pen.line([(x - 30, y + 14), (x + 30, y + 14)], (196, 140, 60), 4)
        for dx, dy in ((-10, -4), (8, 4), (0, -24)):
            pen.circle(x + dx, y + dy, 3, (180, 120, 50), 0)
    elif kind == "jalebi":
        pts = [(x + (4 + 2.6 * a) * math.cos(a), y + (4 + 2.6 * a) * math.sin(a)) for a in [i * 0.35 for i in range(48)]]
        pen.line(pts, (176, 90, 20), 13)
        pen.line(pts, (246, 150, 40), 8)
    elif kind == "vada_pav":
        pen.pie(x - 46, y - 46, x + 46, y + 20, 180, 360, (214, 160, 90), 4)
        pen.ellipse(x - 44, y - 16, x + 44, y + 6, (150, 110, 40), 3)
        pen.line([(x - 40, y + 2), (x + 40, y + 2)], (90, 170, 70), 6)
        pen.ellipse(x - 46, y + 2, x + 46, y + 30, (214, 160, 90), 4)
    elif kind == "banana":
        pen.poly([(x - 50, y - 30), (x - 30, y + 10), (x + 10, y + 26), (x + 50, y + 16), (x + 52, y + 6),
                  (x + 10, y + 8), (x - 26, y - 8), (x - 40, y - 34)], (246, 208, 60), 4)
        pen.circle(x - 46, y - 34, 6, (90, 70, 40), 0)
    elif kind == "apple":
        pen.circle(x, y, 32, (204, 40, 50), 4)
        pen.line([(x, y - 30), (x + 4, y - 48)], (100, 70, 40), 5)
        pen.ellipse(x + 4, y - 50, x + 26, y - 38, (80, 160, 70), 2)
        pen.circle(x - 12, y - 10, 6, (240, 120, 120), 0)
    elif kind == "mango":
        pen.ellipse(x - 30, y - 40, x + 34, y + 34, (250, 184, 50), 4)
        pen.ellipse(x - 6, y - 46, x + 14, y - 34, (90, 160, 60), 2)
        pen.circle(x + 12, y + 10, 10, (240, 120, 50), 0)
    elif kind == "orange":
        pen.circle(x, y, 32, (246, 150, 40), 4)
        for dx, dy in ((-10, -8), (8, 4), (-4, 12), (12, -14)):
            pen.circle(x + dx, y + dy, 2.5, (220, 120, 30), 0)
        pen.ellipse(x - 4, y - 36, x + 10, y - 26, (80, 150, 60), 0)
    elif kind == "grapes":
        for k, (dx, dy) in enumerate(((-20, -24), (0, -26), (20, -24), (-12, -6), (10, -6), (0, 12), (-22, -8), (22, -8))):
            pen.circle(x + dx, y + dy, 13, (120, 60, 140), 2.5)
        pen.line([(x, y - 40), (x + 6, y - 56)], (90, 120, 50), 4)
    elif kind == "watermelon":
        pen.pie(x - 54, y - 50, x + 54, y + 58, 180, 360, (70, 150, 70), 4)
        pen.pie(x - 46, y - 42, x + 46, y + 50, 180, 360, (236, 70, 70), 0)
        for dx in (-22, 0, 22):
            pen.ellipse(x + dx - 3, y - 20, x + dx + 3, y - 10, (30, 30, 30), 0)
    elif kind == "tomato":
        pen.circle(x, y, 30, (214, 52, 44), 4)
        pen.poly([(x - 12, y - 30), (x, y - 38), (x + 12, y - 30), (x, y - 24)], (70, 150, 60), 2)
    elif kind == "onion":
        pen.poly([(x, y - 46), (x + 30, y - 4), (x + 22, y + 26), (x - 22, y + 26), (x - 30, y - 4)], (186, 90, 130), 4)
        pen.line([(x, y - 40), (x, y + 22)], (150, 60, 100), 3)
    elif kind == "potato":
        pen.ellipse(x - 36, y - 26, x + 36, y + 26, (184, 140, 86), 4)
        for dx, dy in ((-14, -6), (10, 6), (16, -10)):
            pen.circle(x + dx, y + dy, 3, (140, 100, 60), 0)
    elif kind == "carrot":
        pen.poly([(x - 18, y - 40), (x + 18, y - 40), (x + 2, y + 50)], (240, 130, 40), 4)
        for dx in (-10, 0, 10):
            pen.line([(x + dx * 0.5, y - 40), (x + dx, y - 64)], (70, 150, 60), 5)
    elif kind == "brinjal":
        pen.ellipse(x - 26, y - 34, x + 26, y + 46, (110, 60, 140), 4)
        pen.poly([(x - 18, y - 30), (x + 18, y - 30), (x, y - 48)], (80, 140, 60), 2)
    elif kind == "chilli":
        pen.line([(x - 8, y - 46), (x + 6, y - 10), (x - 2, y + 30), (x - 16, y + 44)], (60, 160, 60), 10)
        pen.line([(x - 8, y - 46), (x - 4, y - 58)], (90, 120, 50), 4)
    elif kind == "cucumber":                # kheera: long, dark green, light stripes
        pen.ellipse(x - 22, y - 62, x + 22, y + 52, (60, 140, 60), 4)
        for dx in (-9, 0, 9):
            pen.line([(x + dx, y - 44), (x + dx * 1.1, y + 36)], (130, 196, 110), 3)
        pen.ellipse(x - 8, y - 66, x + 8, y - 54, (200, 210, 120), 0)
    elif kind == "lemon":
        pen.ellipse(x - 30, y - 24, x + 30, y + 24, (246, 226, 70), 4)
        pen.circle(x + 30, y, 5, (220, 200, 50), 0)
        pen.circle(x - 30, y, 5, (220, 200, 50), 0)
    elif kind == "cauliflower":             # gobhi: white florets in green leaves
        pen.pie(x - 52, y - 30, x + 52, y + 50, 0, 180, (90, 160, 80), 4)
        for dx, dy in ((-24, -6), (0, -16), (24, -6), (-12, 10), (12, 10)):
            pen.circle(x + dx, y + dy, 18, (246, 242, 226), 3)
    elif kind == "bhindi":                  # lady finger: thin, ridged, green
        pen.poly([(x - 8, y - 58), (x + 10, y - 50), (x + 6, y + 40), (x, y + 52), (x - 6, y + 40)], (100, 170, 70), 4)
        pen.line([(x - 6, y - 60), (x - 2, y - 72)], (80, 120, 50), 5)
        pen.line([(x + 2, y - 46), (x + 1, y + 40)], (70, 140, 50), 2)
    elif kind == "garlic":
        pen.poly([(x, y - 46), (x + 30, y - 4), (x + 26, y + 24), (x - 26, y + 24), (x - 30, y - 4)], (246, 240, 226), 4)
        for dx in (-12, 0, 12):
            pen.line([(x + dx * 0.4, y - 36), (x + dx, y + 20)], (210, 200, 186), 3)
    elif kind == "peas":                    # a matar pod, opened a little
        pen.ellipse(x - 52, y - 20, x + 52, y + 20, (110, 180, 80), 4)
        for dx in (-30, -10, 10, 30):
            pen.circle(x + dx, y, 9, (150, 210, 100), 2)
    elif kind == "bhutta":                  # roasted corn on the cob
        pen.ellipse(x - 20, y - 64, x + 20, y + 44, (232, 190, 70), 4)
        for k in range(6):
            yy = y - 50 + k * 16
            pen.line([(x - 14, yy), (x + 14, yy)], (200, 150, 50), 3)
        for dx, dy in ((-6, -30), (8, -4), (-4, 20)):
            pen.circle(x + dx, y + dy, 6, (110, 70, 40), 0)                       # roasted spots
        pen.poly([(x - 20, y + 30), (x + 20, y + 30), (x + 30, y + 64), (x - 30, y + 64)], (190, 210, 120), 3)  # husk
    elif kind == "coconut":
        pen.circle(x, y, 40, (130, 90, 50), 4)
        for dx, dy in ((-10, -14), (8, -16), (0, -2)):
            pen.circle(x + dx, y + dy, 5, (70, 46, 30), 0)
    elif kind == "cabbage":
        pen.circle(x, y, 40, (130, 196, 100), 4)
        pen.arc(x - 30, y - 30, x + 30, y + 30, 200, 340, 3, (90, 150, 70))
        pen.arc(x - 20, y - 14, x + 20, y + 26, 200, 340, 3, (90, 150, 70))


def _scaled(pen, cx, cy, k):
    """The same pen drawing k times bigger around (cx, cy)."""
    q = Pen.__new__(Pen)
    q.d, q.s = pen.d, pen.s * k
    q.ox, q.oy = pen.ox + cx * pen.s * (1 - k), pen.oy + cy * pen.s * (1 - k)
    return q


def _prop(pen, kind, hand, other=None, skin=None, bite=0):
    x, y = hand
    k = max(0.45, 1 - 0.14 * bite)          # eaten a bit more with every bite
    if kind == "snack" and bite:
        pen.circle(x, y - 18, 22 * k, (230, 180, 80), 4)
        return
    if kind in FOODS:                       # held up in the fingers
        _food(_scaled(pen, x, y - 44, k) if k < 1 else pen, kind, x, y - 44)
        pen.circle(x, y, 24, skin or (200, 140, 95), 4)
        return
    if kind in ("cutting_chai", "kulhad"):
        if kind == "cutting_chai":          # a small glass of chai
            pen.poly([(x - 20, y - 60), (x + 20, y - 60), (x + 15, y + 6), (x - 15, y + 6)], (236, 244, 248), 4)
            pen.poly([(x - 17, y - 44), (x + 17, y - 44), (x + 14, y + 4), (x - 14, y + 4)], (176, 110, 56), 0)
            pen.line([(x - 16, y - 44), (x + 16, y - 44)], (236, 214, 180), 4)
        else:                               # a clay cup
            pen.poly([(x - 24, y - 56), (x + 24, y - 56), (x + 16, y + 8), (x - 16, y + 8)], (178, 92, 58), 4)
            pen.ellipse(x - 22, y - 62, x + 22, y - 50, (176, 110, 56), 2)
        pen.circle(x, y - 4, 22, skin or (200, 140, 95), 4)
        return
    if kind == "plate_samosa" and other is not None:
        cx, cy = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        pen.ellipse(cx - 110, cy - 20, cx + 110, cy + 16, (226, 230, 236), 4)
        for dx, dy in ((-50, -6), (0, -14), (50, -6), (-24, -40), (24, -40)):
            _food(pen, "samosa", cx + dx, cy + dy - 16)
        return
    if kind in ("veg_basket", "sabzi_bag"):  # carried at the side
        bx, by = x + 40, y + 70
        if kind == "veg_basket":
            pen.arc(bx - 70, by - 110, bx + 70, by + 20, 180, 360, 7, (130, 90, 50))
            for dx, dy, col in ((-40, -20, (214, 52, 44)), (0, -26, (240, 130, 40)), (40, -18, (120, 190, 90)),
                                (-18, -38, (110, 60, 140)), (22, -40, (186, 90, 130))):
                pen.circle(bx + dx, by + dy, 20, col, 2.5)
            pen.poly([(bx - 80, by - 20), (bx + 80, by - 20), (bx + 60, by + 70), (bx - 60, by + 70)], (196, 150, 90), 4)
            for k in range(4):
                pen.line([(bx - 70 + k * 46, by - 16), (bx - 50 + k * 40, by + 66)], (160, 116, 66), 3)
        else:
            pen.line([(x, y), (bx - 40, by - 20)], (120, 90, 60), 6)
            pen.line([(x, y), (bx + 40, by - 20)], (120, 90, 60), 6)
            pen.circle(bx + 30, by - 30, 18, (90, 160, 60), 2)                       # leaves sticking out
            pen.line([(bx - 20, by - 20), (bx - 30, by - 60)], (240, 130, 40), 10)    # a carrot
            pen.poly([(bx - 60, by - 20), (bx + 60, by - 20), (bx + 52, by + 90), (bx - 52, by + 90)], (226, 214, 180), 4)
        return
    if kind == "glass":                     # a glass of water
        pen.poly([(x - 26, y - 70), (x + 26, y - 70), (x + 20, y + 16), (x - 20, y + 16)], (225, 240, 250), 4)
        pen.poly([(x - 23, y - 40), (x + 23, y - 40), (x + 19, y + 12), (x - 19, y + 12)], (130, 190, 240), 0)
        pen.circle(x, y - 6, 24, skin or (200, 140, 95), 4)
        return
    if kind == "bottle":                    # a plastic water bottle
        pen.d.rounded_rectangle(pen.box(x - 22, y - 110, x + 22, y + 40), radius=12 * pen.s, fill=(150, 205, 245),
                                outline=OUT, width=pen.wd(4))
        pen.d.rectangle(pen.box(x - 21, y - 60, x + 21, y - 20), fill=(60, 130, 220))      # label
        pen.d.rounded_rectangle(pen.box(x - 12, y - 132, x + 12, y - 108), radius=4 * pen.s, fill=(40, 90, 200),
                                outline=OUT, width=pen.wd(3))
        pen.circle(x, y + 4, 24, skin or (200, 140, 95), 4)
        return
    if kind == "phone_hand":                # a mobile held in one hand: the same big phone as when using it
        _phone_back(pen, x, y - 62, PHONE_W, PHONE_H)
        pen.circle(x, y + 2, 24, skin or (200, 140, 95), 4)
        return
    if kind == "flowers":
        for k, (dx, dy, col) in enumerate(((-30, -110, (230, 70, 90)), (10, -130, (250, 200, 60)),
                                           (40, -100, (230, 110, 170)), (0, -90, (240, 240, 240)))):
            pen.line([(x, y), (x + dx * 0.6, y + dy + 30)], (70, 150, 70), 6)
            pen.circle(x + dx, y + dy, 24, col, 3)
        return
    if kind == "umbrella":                  # an open umbrella over the head
        pen.line([(x, y + 40), (x - 10, y - 380)], (60, 50, 50), 8)
        pen.arc(x - 24, y + 20, x + 24, y + 64, 0, 180, 6, (60, 50, 50))
        pen.pie(x - 250, y - 500, x + 230, y - 260, 180, 360, (40, 90, 170), 5)
        for k in range(5):
            pen.line([(x - 10, y - 390), (x - 250 + k * 120, y - 380)], (30, 70, 140), 3)
        return
    if kind == "suitcase":                  # a rolling suitcase next to the leg, pulled by the handle
        cx, top = x + 90, -330
        pen.line([(x, y), (cx, top)], (70, 70, 80), 8)
        pen.d.rounded_rectangle(pen.box(cx - 80, top, cx + 80, -40), radius=16 * pen.s, fill=(60, 120, 190),
                                outline=OUT, width=pen.wd(5))
        for dx in (-40, 0, 40):
            pen.line([(cx + dx, top + 20), (cx + dx, -60)], (40, 90, 160), 4)
        for dx in (-55, 55):
            pen.circle(cx + dx, -26, 14, (40, 40, 46), 3)
        return
    if kind == "newspaper" and other is not None:
        (x0_, y0_), (x1_, y1_) = other, hand
        pen.poly([(x0_ - 40, y0_ - 190), (x1_ + 40, y1_ - 190), (x1_ + 40, y1_ + 40), (x0_ - 40, y0_ + 40)],
                 (236, 234, 226), 4)
        pen.line([(x0_ + (x1_ - x0_) / 2, y0_ - 190), (x0_ + (x1_ - x0_) / 2, y0_ + 40)], (190, 190, 190), 3)
        for k in range(6):
            yy = y0_ - 160 + k * 32
            pen.line([(x0_ - 10, yy), (x1_ + 10, yy)], (150, 150, 150), 5)
        return
    if kind == "laptop" and other is not None:
        cx_, cy_ = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        pen.poly([(cx_ - 120, cy_ - 150), (cx_ + 120, cy_ - 150), (cx_ + 120, cy_ - 10), (cx_ - 120, cy_ - 10)],
                 (60, 64, 76), 4)
        pen.poly([(cx_ - 104, cy_ - 136), (cx_ + 104, cy_ - 136), (cx_ + 104, cy_ - 24), (cx_ - 104, cy_ - 24)],
                 (140, 190, 240), 0)
        pen.poly([(cx_ - 140, cy_ - 10), (cx_ + 140, cy_ - 10), (cx_ + 120, cy_ + 16), (cx_ - 120, cy_ + 16)],
                 (180, 184, 196), 4)
        return
    if kind == "jug" and other is not None:
        x, y = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        _jug(pen, x, y + 30, 0.25)
        return
    if kind == "ladle":                     # a jhara: long handle, round slotted end
        pen.line([(x, y), (x + 70, y + 150)], (150, 150, 160), 9)
        pen.circle(x + 82, y + 170, 30, (170, 170, 180), 4)
        for dx, dy in ((-10, -6), (8, -8), (0, 8)):
            pen.circle(x + 82 + dx, y + 170 + dy, 4, (90, 90, 100), 0)
        return
    if kind in ("jug", "jug_low"):
        if other is not None:
            x, y = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        _jug(pen, x, y + (30 if kind == "jug" else 50), 0.25 if kind == "jug" else 0.7)
        if kind == "jug_low":               # water slopping out of the spout
            for j, (dx, dy, r) in enumerate(((120, 10, 12), (150, 60, 9), (110, 90, 11), (170, 120, 7))):
                pen.circle(x + dx, y + dy, r, (110, 180, 245), 2, (60, 120, 200))
        return
    if kind == "thali":                     # a steel plate held flat
        pen.ellipse(x - 20, y - 30, x + 210, y + 14, (200, 206, 216), 4)
        pen.ellipse(x + 20, y - 20, x + 170, y + 4, (224, 230, 238), 2)
        return
    if kind == "parcel":
        if other is not None:
            x, y = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        _parcel(pen, x, y - 20)
        return
    if kind == "chappal":
        _chappal(pen, x, y - 40, 0.3)
        return
    if kind == "phone":                     # looking at it: held in front, about two-thirds of a head tall
        if other is not None:
            x, y = (hand[0] + other[0]) / 2, (hand[1] + other[1]) / 2
        _phone_back(pen, x, y + 6, PHONE_W, PHONE_H, skin)  # top of the phone just under the chin
    elif kind == "phone_ear":               # a call: the same phone pressed to the ear, the hand holds it there
        _phone_back(pen, x + 14, y - 16, PHONE_W, PHONE_H)
    elif kind == "cup":
        pen.poly([(x - 26, y - 34), (x + 26, y - 34), (x + 20, y + 22), (x - 20, y + 22)], (245, 245, 240), 4)
        pen.line([(x - 22, y - 26), (x + 22, y - 26)], (170, 110, 60), 6)
    elif kind == "book":
        pen.poly([(x - 120, y - 70), (x + 6, y - 60), (x + 6, y + 30), (x - 120, y + 20)], (200, 60, 60), 4)
    elif kind == "snack":
        pen.circle(x, y - 18, 22, (230, 180, 80), 4)


# ===================================================================== animals
def draw_animal(im, ox, oy, s, sp, pose, emotion, mouth, blink, t, speaking):
    cat = sp["kind"] == "cat"
    pen = Pen(im, ox, oy + pose["dy"] * s, s)
    col, dark, light = sp["color"], _mix(sp["color"], 0.72), sp.get("light", _mix(sp["color"], 1.25))
    walk = pose["walk"]
    happy = emotion in ("happy", "excited", "laughing", "in_love", "proud", "relieved")
    sad = emotion in ("sad", "crying", "scared", "worried")
    k = 0.8 if cat else 1.0
    by0, by1 = -265 * k, -140 * k
    # tail
    wag = math.sin(t * (14 if happy else 5)) * (0.5 if happy else 0.18)
    base = (-140 * k, -222 * k)
    up = -1 if cat or happy else (0.35 if sad else -0.4)
    pts = [base]
    for i in range(1, 6):
        u = i / 5
        a = math.pi + wag * u * 2 + up * 1.1 * u
        pts.append((base[0] + math.cos(a) * 120 * k * u, base[1] + math.sin(a) * 120 * k * u - (60 * u * u if cat else 0)))
    pen.limb(pts, 18 * k if not cat else 15, col)
    # legs (far legs first, darker)
    legs = [(-95, 0.0, True), (105, 0.5, True), (-120, 0.5, False), (82, 0.0, False)]
    for lx, ph, far in legs:
        sw = 22 * math.sin((walk * 8 + ph * math.pi * 2)) if walk else 0
        lx *= k
        top, foot = (lx, by1 + 20), (lx + sw, -24)
        pen.limb([top, foot], 22 * k, dark if far else col)
        pen.ellipse(lx + sw - 18, -34, lx + sw + 20, -8, (40, 34, 34), 3)
        if far:
            pass
    pen.ellipse(-152 * k, by0, 152 * k, by1, col)
    pen.ellipse(-60 * k, by0 + 70 * k, 90 * k, by1 - 6, light, 0)
    # head
    hb = 6 * math.sin(t * 9) if speaking else 2 * math.sin(t * 2)
    hx, hy, r = 168 * k, -292 * k + hb + (14 if sad else 0), 62 * k
    if cat:
        for ex in (-30, 25):
            pen.poly([(hx + ex - 26, hy - r * 0.6), (hx + ex + 26, hy - r * 0.6), (hx + ex + 4, hy - r * 1.55)], col)
            pen.poly([(hx + ex - 12, hy - r * 0.75), (hx + ex + 12, hy - r * 0.75), (hx + ex + 3, hy - r * 1.3)], (240, 160, 170), 0)
    pen.circle(hx, hy, r, col)
    if not cat:
        pen.ellipse(hx - 62, hy - 48, hx - 18, hy + 42, dark)
    # snout and mouth
    sx0, sy0 = hx + 18, hy - 6
    pen.ellipse(sx0, sy0 - 22, sx0 + 70 * k, sy0 + 26, light)
    if mouth > 0.08 or emotion == "laughing":
        m = max(mouth, 0.4 if emotion == "laughing" else 0)
        pen.ellipse(sx0 + 12, sy0 + 12, sx0 + 64 * k, sy0 + 24 + 34 * m, (150, 30, 40), 4)
        pen.ellipse(sx0 + 22, sy0 + 20 + 14 * m, sx0 + 52 * k, sy0 + 22 + 30 * m, (235, 110, 120), 0)
    else:
        pen.arc(sx0 + 20, sy0 + 2, sx0 + 58 * k, sy0 + 26, 20 if happy else 200, 160 if happy else 340, 4.5)
    pen.ellipse(sx0 + 54 * k, sy0 - 16, sx0 + 78 * k, sy0 + 4, (36, 30, 30), 0)
    if cat:
        for dy in (-4, 8):
            pen.line([(sx0 + 50, sy0 + dy), (sx0 + 110, sy0 + dy * 2.2)], OUT, 2.5)
    # eye and brow
    ex, ey = hx + 6, hy - 22
    cfg = _face_cfg(emotion)
    if blink > 0.5 or cfg["eyes"] in ("closed", "happy"):
        pen.arc(ex - 12, ey - 12 if cfg["eyes"] == "closed" else ey - 4, ex + 12,
                ey + 6 if cfg["eyes"] == "closed" else ey + 16, 25 if cfg["eyes"] == "closed" else 200,
                155 if cfg["eyes"] == "closed" else 340, 5)
    else:
        rr = 11 if cfg["eyes"] == "wide" else 8
        if cfg["eyes"] == "wide":
            pen.circle(ex, ey, 14, (255, 255, 255), 3)
        pen.ellipse(ex - rr * 0.8, ey - rr, ex + rr * 0.8, ey + rr, (28, 24, 24), 0)
    b = cfg["brow"]
    if isinstance(b, (int, float)) and b:
        pen.line([(ex - 16, ey - 20 - 8 * b), (ex + 16, ey - 20 + 8 * b)], OUT, 6)
    _effects(pen, tuple(f for f in cfg["fx"] if f in ("tears", "sweat", "vein")), ex - 40, ey + 5, r, t, sides=(1,))


# ===================================================================== sprites
HUMAN_BOX = (-560, -1300, 660, 40)        # wide enough for a cycle beside them and an umbrella above
BRAIN_BOX = (-330, -1130, 330, 40)


def draw_brain(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t, speaking):
    """'My brain': a floating pink cartoon brain with a face, little devil horns, tiny arms and a soft glow."""
    bob = 18 * math.sin(t * 2.4) + (6 * math.sin(t * 9) if speaking else 0)
    pen = Pen(im, ox, oy + bob * s, s)
    col, dark = sp.get("color", (244, 150, 172)), _mix(sp.get("color", (244, 150, 172)), 0.8)
    cx, cy, rx, ry = 0, -830, 205, 160               # floats at head height
    # soft glow and a faint shadow far below (it floats)
    glow = Image.new("L", im.size, 0)
    gd = ImageDraw.Draw(glow)
    gr = 290 * s
    gx, gy = ox + cx * s, oy + (cy + bob) * s
    gd.ellipse([gx - gr, gy - gr * 0.85, gx + gr, gy + gr * 0.85], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(40 * s))
    tint = Image.new("RGBA", im.size, sp.get("glow", (255, 110, 140)) + (255,))
    tint.putalpha(glow)
    im.alpha_composite(tint)
    # horns (devil)
    if sp.get("horns", True):
        for side in (-1, 1):
            pen.poly([(side * 70, cy - ry * 0.82), (side * 140, cy - ry * 0.62), (side * 150, cy - ry * 1.45)],
                     (214, 40, 40), 4.5)
    # tiny arms
    for side, key in ((-1, "L"), (1, "R")):
        spec = pose.get(key, ("fk", 20, -10))
        sx, sy = side * (rx - 10), cy + 40
        if spec[0] in ("ik", "ikd"):
            spec = ("fk", 35, 60) if speaking else ("fk", 20, -10)
        a, e = spec[1], spec[2]
        elbow, hand = _fk(sx, sy, min(150, a), e, 70, 62, side)
        pen.limb([(sx, sy), elbow, hand], 16, col, 4)
        pen.circle(hand[0], hand[1], 15, col, 4)
    # brain body: two hemispheres made of lobes
    lobes = [(-120, -40, 95), (-60, -95, 100), (40, -100, 100), (120, -45, 95), (-150, 40, 80), (150, 40, 80),
             (-70, 70, 95), (70, 70, 95), (0, 10, 120)]
    for lx, ly, r in lobes:
        pen.ellipse(cx + lx - r, cy + ly - r * 0.85, cx + lx + r, cy + ly + r * 0.85, col)
    for lx, ly, r in lobes:                                   # cover inner outlines, keep the outer edge
        r2 = r - 8
        pen.ellipse(cx + lx - r2, cy + ly - r2 * 0.85, cx + lx + r2, cy + ly + r2 * 0.85, col, 0)
    pen.line([(cx, cy - ry * 0.95), (cx + 6, cy - 60)], dark, 6)                             # middle groove
    for fx_, fy, a0, a1 in ((-130, -70, 200, 320), (-90, 20, 160, 300), (120, -60, 220, 340), (95, 30, 240, 20),
                            (-40, -120, 180, 300), (60, -125, 220, 340)):
        pen.arc(cx + fx_ - 45, cy + fy - 30, cx + fx_ + 45, cy + fy + 30, a0, a1, 5, dark)  # folds
    if view == "back":
        return
    # face
    cfg = _face_cfg(emotion)
    fy0 = cy + 30
    _eye(pen, cx - 52, fy0, cfg["eyes"], blink, pose.get("eyes_dir", 0.0) or 0.3 * math.sin(t * 0.7))
    _eye(pen, cx + 52, fy0, cfg["eyes"], blink, pose.get("eyes_dir", 0.0) or 0.3 * math.sin(t * 0.7))
    brow = cfg["brow"] if cfg["brow"] != 0 else (0.9 if sp.get("horns", True) else 0)        # sly look
    _brows(pen, cx, fy0 - 40, brow)
    mk = cfg["mouth"] if (cfg["mouth"] != "smile_s" or not sp.get("horns", True)) else "smirk"
    if mk == "smirk" and mouth <= 0.08:
        pen.arc(cx - 40, fy0 + 40, cx + 50, fy0 + 90, 10, 150, 6)
        pen.line([(cx + 40, fy0 + 66), (cx + 56, fy0 + 52)], OUT, 6)
    else:
        _mouth(pen, cx + 4, fy0 + 70, mk if mk != "smirk" else "smile", mouth, t)
    _effects(pen, cfg["fx"], cx, fy0 - 20, ry, t)
ANIMAL_BOX = (-270, -470, 330, 30)


class SpriteCache:
    def __init__(self, n=220):
        self.n, self.d = n, OrderedDict()

    def get(self, key, make):
        if key in self.d:
            self.d.move_to_end(key)
            return self.d[key]
        v = make()
        self.d[key] = v
        if len(self.d) > self.n:
            self.d.popitem(last=False)
        return v


@lru_cache(maxsize=16)
def _shade_grad(w, h):
    g = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))   # 255 at left -> 0 at right
    return g.point(lambda v: int((255 - v) * 0.16))


def render_sprite(sp, view, face_dir, scale_px, pose, emotion, mouth, blink, t, speaking, below_px=None):
    """RGBA picture of one character and the pixel position of its feet inside it.
    below_px: pixels from the feet down to the frame bottom (negative when the feet are below the frame);
    the part of the character outside the frame is not drawn."""
    ss = 2
    s = scale_px * ss * sp.get("height", 1.0)
    animal = sp["kind"] in ("dog", "cat")
    x0, y0, x1, y1 = ANIMAL_BOX if animal else BRAIN_BOX if sp["kind"] == "brain" else \
        stick.STICK_BOX if sp["kind"] == "stick" else HUMAN_BOX
    turned = any(pose.get(q) for q in ("rot", "tx", "ty", "sq"))
    if turned:                              # falling over / rolling: room all round
        x0, y0, x1, y1 = stick.TURN_BOX
    elif pose.get("fx"):                    # effects above the head and beside the body
        x0, y0, x1, y1 = min(x0, -720), min(y0, -1480), max(x1, 760), y1
    if below_px is not None:
        y1 = min(y1, below_px * ss / s + 8)
    W, H = max(4, int((x1 - x0) * s) // 2 * 2), max(4, int((y1 - y0) * s) // 2 * 2)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ox, oy = -x0 * s, -y0 * s
    if sp["kind"] == "brain":
        draw_brain(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t, speaking)
    elif animal:
        draw_animal(im, ox, oy, s, sp, pose, emotion, mouth, blink, t, speaking)
    elif sp["kind"] == "stick":
        stick.draw_stick(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t)
    else:
        draw_human(im, ox, oy, s, sp, view, pose, emotion, mouth, blink, t)
    if pose.get("sq"):                      # squashed (hit on the head, splat on a wall): around the feet
        kx, ky = pose["sq"]
        small = im.resize((max(1, round(W * kx)), max(1, round(H * ky))), Image.BICUBIC)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        im.alpha_composite(small, (max(0, round(ox - ox * kx)), max(0, round(oy - oy * ky))))
    if pose.get("rot") or pose.get("tx") or pose.get("ty"):
        im = im.rotate(pose.get("rot", 0.0), resample=Image.BICUBIC, center=(ox, oy + pose.get("piv", -450) * s),
                       translate=(pose.get("tx", 0.0) * s, pose.get("ty", 0.0) * s))
    im = im.reduce(ss)                      # fast 2x box filter = smooth edges
    W, H = im.size
    ox, oy = ox / ss, oy / ss
    a = im.getchannel("A")
    shade = ImageChops.multiply(_shade_grad(W, H), a)
    dark = Image.new("RGBA", (W, H), (20, 10, 30, 0))
    dark.putalpha(shade)
    im = Image.alpha_composite(im, dark)
    if face_dir < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        ox = W - ox
    return _trim(im, ox, oy)


def _trim(im, ox, oy):
    """Cut away the empty border of a sprite (pasting transparent pixels costs time); keeps the feet anchor."""
    bb = im.getbbox()
    if not bb or bb == (0, 0, im.width, im.height):
        return im, (ox, oy)
    return im.crop(bb), (ox - bb[0], oy - bb[1])


@lru_cache(maxsize=32)
def _shadow(wpx, hpx):
    pad = max(2, hpx)
    im = Image.new("L", (wpx + 2 * pad, hpx + 2 * pad), 0)
    ImageDraw.Draw(im).ellipse([pad, pad, pad + wpx, pad + hpx], fill=85)
    im = im.filter(ImageFilter.GaussianBlur(max(1, hpx * 0.35)))
    sh = Image.new("RGBA", im.size, (20, 18, 30, 0))
    sh.putalpha(im)
    return sh


# ===================================================================== backgrounds
GROUND = {"flat": 1690, "picture": 1500}


def _building_colors(night):
    cols = [(132, 182, 160), (214, 150, 120), (152, 142, 196), (112, 166, 176), (228, 176, 122), (196, 132, 132)]
    return [_mix(c, 0.55) for c in cols] if night else cols


def panorama(bid: str, k: float):
    """The whole wide background picture (sky, buildings, street), drawn once. Returns (image, px per unit, width units, ground y)."""
    return _panorama(bid, k, bg_stamp(bid))


@lru_cache(maxsize=6)
def _panorama(bid: str, k: float, _stamp: float):
    if bid not in FLAT_BACKGROUNDS:
        ps = k * 1.25
        im = get_background(bid, round(FW * ps), round(FH * ps)).copy()
        return im, ps, FW, GROUND["picture"]
    ps = k * 1.3
    PW = 2600
    night = bid == "flat_city_night"
    park = bid == "flat_park"
    W, H = round(PW * ps), round(FH * ps)
    im = Image.new("RGB", (W, H))
    if bid in REALMS:                      # Swarg / Nark: drawn in realms.py
        draw_realm(bid, im, ps, PW)
        return im, ps, PW, GROUND["flat"]
    if bid in PLACES:                      # village, school, kitchen, office, market: places.py
        draw_place(bid, im, ps, PW)
        return im, ps, PW, GROUND["flat"]
    d = ImageDraw.Draw(im)
    top, bot = ((22, 30, 72), (66, 76, 130)) if night else ((96, 160, 214), (206, 228, 242))
    horizon = 1240 if not park else 1290
    for y in range(H):
        u = min(1.0, y / (horizon * ps))
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bot)))
    P = lambda *v: [x * ps for x in v]     # noqa: E731
    L = lambda w: max(1, round(w * ps))     # noqa: E731
    rnd = random.Random(_h(bid))
    if night:
        for _ in range(140):
            x, y = rnd.uniform(0, PW), rnd.uniform(0, 900)
            rr = rnd.uniform(1.5, 3.5)
            d.ellipse(P(x - rr, y - rr, x + rr, y + rr), fill=(240, 240, 220))
        d.ellipse(P(1850, 240, 2030, 420), fill=(245, 242, 222))
        d.ellipse(P(1900, 210, 2080, 390), fill=top)
    else:
        d.ellipse(P(1800, 235, 1990, 425), fill=(250, 214, 108))
    if park:
        for cx, cy, rw, col in ((500, 1330, 900, (150, 196, 130)), (1500, 1350, 1000, (132, 186, 118)),
                                (2400, 1330, 800, (150, 196, 130))):
            d.ellipse(P(cx - rw, cy - 330, cx + rw, cy + 330), fill=col, outline=OUT, width=L(5))
        d.rectangle(P(0, 1290, PW, FH), fill=(118, 178, 96))
        for y in range(round(1290 * ps), H):
            u = (y / ps - 1290) / (FH - 1290)
            d.line([(0, y), (W, y)], fill=(int(118 - 30 * u), int(180 - 40 * u), int(96 - 20 * u)))
        d.line(P(0, 1290, PW, 1290), fill=OUT, width=L(5))
        d.polygon([tuple(P(x, y)) for x, y in ((0, 1560), (PW, 1560), (PW, 1800), (0, 1800))], fill=(214, 190, 140))
        d.line(P(0, 1560, PW, 1560), fill=_mix((214, 190, 140), 0.75), width=L(5))
        d.line(P(0, 1800, PW, 1800), fill=_mix((214, 190, 140), 0.75), width=L(5))
        for _ in range(160):
            x, y = rnd.uniform(0, PW), rnd.choice([rnd.uniform(1320, 1540), rnd.uniform(1830, 1910)])
            c = rnd.choice([(240, 90, 90), (250, 220, 90), (250, 250, 250), (220, 120, 220)])
            d.ellipse(P(x - 7, y - 7, x + 7, y + 7), fill=c)
        for x in range(60, PW, 90):                                       # fence
            d.rectangle(P(x - 8, 1180, x + 8, 1300), fill=(240, 236, 226), outline=OUT, width=L(3))
        d.rectangle(P(0, 1205, PW, 1222), fill=(240, 236, 226), outline=OUT, width=L(3))
        trees = range(200, PW, 520)
        tree_r, foliage_y = 150, 900
        for bx in (900, 2050):                                            # benches
            d.rectangle(P(bx - 140, 1250, bx + 140, 1275), fill=(170, 110, 60), outline=OUT, width=L(4))
            d.rectangle(P(bx - 140, 1205, bx + 140, 1228), fill=(170, 110, 60), outline=OUT, width=L(4))
            for lx in (bx - 120, bx + 110):
                d.rectangle(P(lx, 1275, lx + 12, 1320), fill=(60, 60, 64))
    else:
        cols = _building_colors(night)
        x = -60
        while x < PW + 60:
            w = rnd.randint(190, 300)
            topy = rnd.randint(560, 960)
            c = rnd.choice(cols)
            d.rectangle(P(x, topy, x + w, 1240), fill=c, outline=OUT, width=L(6))
            nc = rnd.choice([2, 3])
            ww, wh = 38, 50
            gap = (w - nc * ww) / (nc + 1)
            for row in range(int((1240 - topy - 70) // 100)):
                wy = topy + 50 + row * 100
                for cix in range(nc):
                    wx = x + gap + cix * (ww + gap)
                    lit = rnd.random() < (0.6 if night else 0.45)
                    wc = ((250, 222, 120) if lit else (50, 60, 90)) if night else ((238, 226, 150) if lit else (112, 162, 212))
                    d.rounded_rectangle(P(wx, wy, wx + ww, wy + wh), radius=L(5), fill=wc, outline=_mix(OUT, 1.6), width=L(3))
            x += w + rnd.randint(-30, 6)
        d.rectangle(P(0, 1240, PW, 1372), fill=_mix((214, 207, 196), 0.6 if night else 1.0))
        d.line(P(0, 1240, PW, 1240), fill=OUT, width=L(6))
        d.line(P(0, 1372, PW, 1372), fill=OUT, width=L(5))
        for y in range(round(1372 * ps), H):
            u = (y / ps - 1372) / (FH - 1372)
            base = (86, 88, 98) if not night else (52, 54, 66)
            d.line([(0, y), (W, y)], fill=_mix(base, 1.0 - 0.18 * u))
        dash = (228, 196, 92)
        for x in range(-40, PW, 230):
            d.rounded_rectangle(P(x, 1708, x + 130, 1726), radius=L(4), fill=dash)
        trees = range(150, PW, 640)
        tree_r, foliage_y = 118, 800
        for lx in range(470, PW, 1280):                                   # street lamps
            if night:
                glow = Image.new("L", (round(500 * ps), round(500 * ps)), 0)
                ImageDraw.Draw(glow).ellipse([glow.width * 0.22, glow.height * 0.22, glow.width * 0.78,
                                              glow.height * 0.78], fill=110)
                glow = glow.filter(ImageFilter.GaussianBlur(60 * ps))
                im.paste((255, 226, 140), (round((lx - 250) * ps), round((720 - 250) * ps)), glow)
                d = ImageDraw.Draw(im)
            d.rectangle(P(lx - 8, 740, lx + 8, 1250), fill=(34, 34, 40))
            d.rounded_rectangle(P(lx - 38, 696, lx + 38, 746), radius=L(10), fill=(252, 226, 140), outline=OUT, width=L(5))
    tc = (78, 150, 84) if not night else (40, 86, 52)
    for tx in trees:
        tx += rnd.randint(-60, 60)
        d.rectangle(P(tx - 12, foliage_y, tx + 12, (1250 if not park else 1300)), fill=(110, 74, 46), outline=OUT, width=L(4))
        d.ellipse(P(tx - tree_r, foliage_y - tree_r, tx + tree_r, foliage_y + tree_r), fill=tc, outline=OUT, width=L(6))
    return im, ps, PW, GROUND["flat"]


def _blurred(bid: str, k: float):
    return _blurred_s(bid, k, bg_stamp(bid))


@lru_cache(maxsize=6)
def _blurred_s(bid: str, k: float, _stamp: float):
    im, ps, *_ = panorama(bid, k)
    return im.filter(ImageFilter.GaussianBlur(7 * ps))


def _soft(bid: str, k: float):
    return _soft_s(bid, k, bg_stamp(bid))


@lru_cache(maxsize=6)
def _soft_s(bid: str, k: float, _stamp: float):
    im, ps, *_ = panorama(bid, k)
    return im.filter(ImageFilter.GaussianBlur(2.6 * ps))


def _car_draw(color, s):
    W, H = round(260 * s), round(130 * s)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pen = Pen(im, 15 * s, 10 * s, s)
    pen.poly([(55, 10), (165, 10), (195, 52), (35, 52)], color)
    pen.poly([(68, 20), (108, 20), (108, 48), (52, 48)], (170, 214, 240), 4)
    pen.poly([(118, 20), (158, 20), (180, 48), (118, 48)], (170, 214, 240), 4)
    pen.d.rounded_rectangle(pen.box(0, 48, 230, 92), radius=16 * s, fill=color, outline=OUT, width=pen.wd(5))
    pen.d.rectangle(pen.box(212, 58, 228, 70), fill=(250, 230, 140))
    for wx in (50, 180):
        pen.circle(wx, 92, 22, (40, 38, 40))
        pen.circle(wx, 92, 9, (190, 190, 196), 0)
    return im


@lru_cache(maxsize=24)
def car_sprite(color, s_q, blur, flip):
    s = s_q / 100
    im = _car_draw(color, s * 2).resize((round(260 * s), round(130 * s)), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(max(1, 3 * s)))
    return im


# people walking past in the background: (look, speed in picture units a second, start offset)
PASSERS = {"flat_village": (("flat_aunty", 60, 0), ("flat_kid", -85, 900)),
           "flat_chai_tapri": (("flat_girl", 55, 300), ("flat_uncle", -45, 1500)),
           "flat_park": (("flat_girl", 65, 200), ("flat_man", -70, 1300)),
           "flat_bus_stop": (("flat_aunty", 50, 600),),
           "flat_city_street": (("flat_man", 75, 100), ("flat_aunty", -55, 1200))}


# ===================================================================== camera
class FlatComposer:
    """Draws the frames of flat-style scenes."""

    def __init__(self, tl: dict, sched: list, w: int, h: int):
        self.tl, self.sched, self.w, self.h = tl, sched, w, h
        self.k = w / FW
        self.chars = {c["id"]: c for c in tl["characters"]}
        self.specs = {cid: char_spec(c) for cid, c in self.chars.items()}
        self.sprites = SpriteCache()
        self.warnings: list = []
        self.segs: dict = {}
        self.bgs: dict = {}
        self.kev = kitchen.events(sched)                  # the kadhai: frying, fire, covered (kitchen.py)
        self.bagplan = bag.plan(sched)                    # the mystery bag (bag.py)
        self.cinema = bool(tl.get("cinematic", True))     # warm grade, depth, passers-by (cinema.py)

    def handles(self, sc) -> bool:
        return sc.bg in FLAT_BACKGROUNDS or any(is_flat_look(self.chars[c]["look"]) for c in sc.cast)

    def _animal(self, cid):
        return self.specs[cid]["kind"] in ("dog", "cat")

    # ------------------------------------------------------------- shot list
    def segments(self, sc):
        key = id(sc)
        if key in self.segs:
            return self.segs[key]
        cast, lines = sc.cast, sc.lines
        segs = []
        last_close: dict = {}
        if not lines:
            segs.append((sc.start, sc.end, dict(type="wide" if len(cast) > 1 else "single", subj=cast[0])))
        for i, ln in enumerate(lines):
            a = sc.start if i == 0 else ln.start
            b = lines[i + 1].start if i + 1 < len(lines) else sc.end
            subj = ln.char
            narr = subj not in cast                               # a narrator line: show who acts meanwhile
            if narr:
                subj = ln.actor if getattr(ln, "actor", "") in cast else cast[0]
            others = [c for c in cast if c != subj]
            partner = others[0] if others else None
            kind = getattr(ln, "shot", "auto") or "auto"
            if kind == "stove" and sc.bg != "flat_kitchen":
                kind = "auto"
            if kind == "bag" and not self._bag_scene(sc):
                kind = "auto"
            if kind == "auto" and getattr(ln, "bag", "") == "open" and self._bag_scene(sc):
                kind = "bag"                                  # the bag popping open: the camera goes to it
            if kind == "auto" and getattr(ln, "bag", "") == "shake" and self._bag_scene(sc) and len(cast) > 1:
                kind = "wide"                                 # the bag shaking by itself: everyone and the bag in view
            auto = kind == "auto"
            acts = {ln.action, getattr(ln, "actor_action", "")}
            far = False
            if auto and self._stick_scene(sc):              # stickman comedy: a tight two-shot of everyone,
                react = acts & stick.REACTIONS or getattr(ln, "effect", "") == "eyes_pop"   # a big reaction: close
                if react and last_close.get(subj, -9) < i - 2:
                    kind = "close"
                else:                                        # pulled back when someone lies, runs or flies
                    far = bool(acts & stick.FAR_MOVES) or self._anyone_down(sc, a, b)
                    kind = "wide" if len(cast) > 1 else "single"
                auto = False
            if auto and acts & stick.NEED_WIDE:              # slapstick needs the whole body (and the floor) in view
                kind = "wide" if len(cast) > 1 else "single"
                auto = False
            if auto:
                if len(cast) > 1 and (narr and not getattr(ln, "actor", "") or acts & TWO_PERSON
                                      or acts & (kitchen.STOVE_ACTIONS | {"look_camera"})):
                    kind = "wide"
                elif narr:
                    kind = "single"
                elif len(cast) > 1 and i == 0:
                    kind = "wide"
                elif ln.emotion in STRONG and last_close.get(subj, -9) < i - 2:
                    kind = "close"
                elif partner and len(cast) == 2 and not self._animal(partner) and                         self.specs[partner]["kind"] not in ("brain", "stick"):     # a stickman's back is just a circle
                    kind = "ots"
                else:
                    kind = "single"
            if kind == "close":
                last_close[subj] = i
            if kind in ("ots",) and not partner:
                kind = "single"
            if kind == "ots" and narr:
                kind = "single"
            medium = (kind == "single" and self.cinema and not self._stick_scene(sc) and not self._animal(subj)
                      and not (acts & FULL_BODY) and self.specs[subj]["kind"] in ("human", "3d"))
            spec = dict(type=kind, subj=subj, partner=partner, far=far, medium=medium)
            dur = ln.end - ln.start
            if auto and partner and dur > 5.5 and kind not in ("wide", "stove") and not narr:   # a reaction shot
                cut = ln.start + dur * 0.58
                segs.append((a, cut, spec))
                if self._animal(subj):
                    react = dict(type="single", subj=partner, partner=subj)
                else:
                    react = dict(type="ots", subj=partner, partner=subj)
                segs.append((cut, b, react))
            else:
                segs.append((a, b, spec))
        self.segs[key] = segs
        return segs

    def layout(self, sc, spec):
        """Background view and where each character stands for one shot (in frame units)."""
        bid = sc.bg
        _, _, PW, G = panorama(bid, self.k)
        si = self.sched.index(sc) if sc in self.sched else 0
        base = PW / 2 + ((_h(bid, si) % 7) - 3) * 120
        stove = self._stove_scene(sc)
        if stove:
            base = kitchen.KX - 300
        cast = sc.cast
        subj, partner = spec["subj"], spec.get("partner")
        side = 1 if partner and cast.index(partner) > cast.index(subj) else -1 if partner else 1
        actors = []
        t = spec["type"]
        if t == "stove":                                       # close on the kadhai, nobody in the shot
            return dict(bg=(kitchen.KX, 2.1, False, kitchen.KY - 70), actors=[], ground=G)
        if t == "bag":                                         # close on the mystery bag
            return dict(bg=(self._bag_x(sc), 2.0, False, G - 230), actors=[], ground=G, type="bag")
        if t == "wide":
            n = len(cast)
            sc_ = 0.82 if n <= 2 else max(0.55, 0.82 - 0.09 * (n - 2))
            xs = [540] if n == 1 else [FW * (0.2 + 0.6 * i / (n - 1)) for i in range(n)]
            if self._stick_scene(sc):                           # stickmen: big in the frame (faces readable on a
                if spec.get("far"):                             # phone); pulled back when someone lies or runs
                    sc_ = 0.68 if n <= 2 else max(0.5, 0.68 - 0.07 * (n - 2))
                    xs = [540] if n == 1 else [FW * 0.2, FW * 0.86] if n == 2 else xs
                else:
                    sc_ = 1.0 if n <= 2 else max(0.72, 0.9 - 0.06 * (n - 3))
                    xs = [540] if n == 1 else [FW * 0.29, FW * 0.71] if n == 2 else \
                        [FW * (0.16 + 0.68 * i / (n - 1)) for i in range(n)]
            if stove:                                          # everyone to the left of the stove
                xs = [400] if n == 1 else [FW * (0.13 + 0.47 * i / (n - 1)) for i in range(n)]
            elif self._bag_scene(sc):                          # everyone to the left of the bag
                xs = [380] if n == 1 else [FW * (0.13 + 0.5 * i / (n - 1)) for i in range(n)]
            for i, cid in enumerate(cast):
                fd = 1 if xs[i] < 540 else -1 if n > 1 else 1
                actors.append(dict(cid=cid, view="front", x=xs[i], g=G, scale=sc_, face=fd))
            bg = (base, 1.0, False)
        elif t == "single":
            fd = side
            if self._animal(subj):
                actors.append(dict(cid=subj, view="side", x=520, g=G + 40, scale=1.45, face=fd))
            elif spec.get("medium"):                            # from the knees up, a little off-centre
                actors.append(dict(cid=subj, view="front", x=540 - 70 * fd, g=G + 360, scale=1.36, face=fd))
            else:
                big = 1.18 if self._stick_scene(sc) and not spec.get("far") else 0.8 if spec.get("far") else 1.05
                actors.append(dict(cid=subj, view="front", x=540, g=G, scale=big, face=fd))
            bg = (base + 260 * fd, 1.12, "soft" if self.cinema and not self._stick_scene(sc) else False)
        elif t == "close":
            fd = side
            if self._animal(subj):
                actors.append(dict(cid=subj, view="side", x=200, g=1660, scale=2.2, face=1))
            else:
                hgt = self.specs[subj].get("height", 1.0)       # a short character: the camera goes lower
                actors.append(dict(cid=subj, view="front", x=540, g=G + 820 - (1 - hgt) * 890 * 1.75, scale=1.75, face=fd))
            bg = (base + 260 * fd, 1.3, True)
        else:  # over the shoulder: the partner's back big in front, the speaker further away
            if self._animal(subj):
                actors.append(dict(cid=subj, view="side", x=300, g=G + 100, scale=1.05, face=1))
            else:
                actors.append(dict(cid=subj, view="front", x=380, g=G + 60, scale=0.64, face=1))
            if partner:
                if self._animal(partner):
                    actors.append(dict(cid=partner, view="side", x=760, g=G + 820, scale=2.4, face=-1, back=True))
                else:
                    actors.append(dict(cid=partner, view="back", x=930, g=G + 1490, scale=2.1, face=1, back=True))
            bg = (base - 380, 1.0, True)
        return dict(bg=bg, actors=actors, ground=G, type=t)

    EASE = 0.18

    def _ease(self, sc, cid, mine, now, recent, t, pose, key):
        """Blend the arms and body from the pose shown just before (a new line starting, or a line just ended).
        Returns a cache tag for the blend, or None."""
        if any(pose.get(q) for q in ("rot", "move", "cloud", "sq", "ride", "sit")):
            return None
        if now is not None:
            i = mine.index(now)
            since = t - now[0]
            if since >= self.EASE:
                return None
            if i > 0 and mine[i - 1][1] >= now[0] - 0.05:          # straight from their previous line
                pa, pe, pt = mine[i - 1][2], mine[i - 1][3], mine[i - 1][1] - mine[i - 1][0]
            elif i > 0 and mine[i - 1][2] in FLAT_PERSIST:
                pa, pe, pt = mine[i - 1][2], mine[i - 1][3], 9.0
            else:
                pa, pe, pt = "idle", "neutral", t - sc.start
            if pa == now[2]:
                return None
        elif recent is not None and recent[2] not in FLAT_PERSIST and 0 <= t - recent[1] < self.EASE:
            since = t - recent[1]                                   # their line just ended: back to standing
            pa, pe, pt = recent[2], recent[3], recent[1] - recent[0]
        else:
            return None
        if pa in stick.SLAPSTICK or pa in ("walk_in", "walk_out", "run_in", "run_out", "ride_in", "ride_out"):
            return None
        prev = pose_for(pa, pe, round(pt * 15) / 15, False, key)
        if any(prev.get(q) for q in ("rot", "move", "cloud", "sq", "ride", "sit")):
            return None
        w = since / self.EASE
        w = w * w * (3 - 2 * w)
        for arm in ("L", "R"):
            ax_, ay_ = stick.hand_target(prev[arm])
            bx_, by_ = stick.hand_target(pose[arm])
            pose[arm] = ("ik", ax_ + (bx_ - ax_) * w, ay_ + (by_ - ay_) * w)
        for q in ("dx", "dy", "head_dx", "head_dy", "crouch"):
            pose[q] = prev.get(q, 0.0) + (pose.get(q, 0.0) - prev.get(q, 0.0)) * w
        return (pa, round(w, 2))

    def _passersby(self, im, bid, t, x0, y0, z, k, G, blur):
        """Villagers walking past far behind the characters (smaller, hazy, out of focus in a shot on one person)."""
        _, _, PW, _G = panorama(bid, k)
        vw = FW / z
        for j, (look, speed, off) in enumerate(PASSERS[bid]):
            span = PW + 900
            X = (off + speed * t) % span - 450 if speed > 0 else span - ((off - speed * t) % span) - 450
            if not (x0 - 300 < X < x0 + vw + 300):
                continue
            face = 1 if speed > 0 else -1
            ph = int((t % 0.785) / 0.785 * 8)                  # 8 drawings of the walk, used over and over
            scale_px = 0.5 * z * k
            ck = ("passer", look, face, round(scale_px, 3), ph, blur == "soft")

            def make(look=look, face=face, ph=ph, scale_px=scale_px):
                sp = char_spec({"look": look})
                pose = pose_for("walk", "neutral", ph * 0.785 / 8, False, look)
                spr, anchor = render_sprite(sp, "front", face, scale_px, pose, "neutral", 0.0, 0.0, 0.0, False)
                hz = Image.new("RGBA", spr.size, cinema.HAZE + (255,))
                hz.putalpha(spr.getchannel("A"))
                spr = Image.blend(spr, hz, 0.3)                    # far away: hazy
                if blur:
                    spr = spr.filter(ImageFilter.GaussianBlur(1.6 if blur == "soft" else 3))
                return spr, anchor
            spr, (ax, ay) = self.sprites.get(ck, make)
            px_, py_ = (X - x0) * z * k, (G - 250 - y0) * z * k
            im.paste(spr, (round(px_ - ax), round(py_ - ay)), spr)

    def _bag_scene(self, sc) -> bool:
        return id(sc) in self.bagplan

    def _bag_x(self, sc) -> float:
        """Where the bag lies in the background picture (right of the middle of the scene's wide shot)."""
        _, _, PW, _G = panorama(sc.bg, self.k)
        si = self.sched.index(sc) if sc in self.sched else 0
        return PW / 2 + ((_h(sc.bg, si) % 7) - 3) * 120 + bag.BAG_DX

    def _last_scene(self):
        return next((x for x in reversed(self.sched) if x.card is None), None)

    def _stick_scene(self, sc) -> bool:
        return bool(sc.cast) and all(self.specs[c]["kind"] == "stick" for c in sc.cast)

    def _latest(self, sc, cid, t):
        last = None
        for m in self._acts(sc, cid):
            if m[0] > t:
                break
            last = m[2]
        return last

    def _anyone_down(self, sc, a, b) -> bool:
        """Someone lies on the floor (or is out running) between a and b: the camera pulls back."""
        for cid in sc.cast:
            for tt in (a + 0.01, (a + b) / 2, b - 0.01):
                if self._latest(sc, cid, tt) in stick.DOWN:
                    return True
        return False

    def _sleeping(self, sc, cid, t) -> bool:
        """Lying asleep on the floor right now (their latest action is lie_sleep)."""
        last = None
        for m in self._acts(sc, cid):
            if m[0] > t:
                break
            last = m[2]
        return last in ("lie_sleep",)

    def _lie_place(self, a, sp):
        """Where someone asleep on the floor lies: feet near the frame edge, head toward the middle."""
        su = a["scale"] * sp.get("height", 1.0)
        if a["x"] < FW / 2:
            return 0.03 * FW + 450 * su, -1, 0.03 * FW + 1040 * su           # (feet anchor x, face, head x)
        return 0.97 * FW - 450 * su, 1, 0.97 * FW - 1040 * su

    def _stove_scene(self, sc) -> bool:
        """A kitchen scene where the kadhai matters: the camera keeps the stove in view."""
        if sc.bg != "flat_kitchen":
            return False
        key = ("stove", id(sc))
        if key not in self.segs:
            self.segs[key] = kitchen.state_at(self.kev, sc.end) is not None or any(
                getattr(l, "shot", "") == "stove" or {l.action, getattr(l, "actor_action", "")} & kitchen.STOVE_ACTIONS
                for l in sc.lines)
        return self.segs[key]

    def _acts(self, sc, cid):
        """What a character does in a scene: their own lines, and lines where they act while someone else speaks."""
        key = ("acts", id(sc), cid)
        if key not in self.segs:
            out = []
            for l in sc.lines:
                if l.char == cid:
                    out.append((l.start, l.end, l.action, l.emotion, l, True))
                elif l.char not in sc.cast and l.action == "look_camera":   # narrator: "everyone looks at us"
                    out.append((l.start, l.end, "look_camera", l.emotion if l.emotion != "neutral" else "relieved",
                                l, False))
                elif getattr(l, "actor", "") == cid:
                    out.append((l.start, l.end, l.actor_action, l.actor_emotion, l, False))
            self.segs[key] = out
        return self.segs[key]

    def _held(self, sc, cid, t):
        """What the character carries at time t: the prop of their latest line that set one (in this scene, or
        carried over from earlier scenes); "none" puts it away. Riding in on a cycle means they have one."""
        prop = None
        for scx in self.sched:
            if scx.start > t:
                break
            for l in scx.lines:
                if l.start > t:
                    break
                if l.char == cid and getattr(l, "prop", ""):
                    prop = None if l.prop == "none" else l.prop
                elif (l.char == cid and l.action in ("ride_in", "ride_out", "ride_cycle")) or \
                        (getattr(l, "actor", "") == cid and l.actor_action in ("ride_in", "ride_out", "ride_cycle")):
                    prop = "cycle"
        return prop

    def _moved_x(self, sc, cid, a, lay, x0, z, t):
        """Where a character stands after walking up to the stove or to someone (None: where the shot puts them)."""
        if lay.get("type") not in ("wide", "single"):
            return None
        x, moved = a["x"], False
        for start, _end, action, _em, _l, _sp in self._acts(sc, cid):
            if start > t:
                break
            tgt = None
            if action in kitchen.STOVE_ACTIONS and self._stove_scene(sc):
                tgt, face = (kitchen.KX - x0) * z - 300 * a["scale"], 1
            elif action == "go_to_bag" and self._bag_scene(sc):
                bfx = (self._bag_x(sc) - x0) * z
                side = 1 if bfx > a["x"] else -1
                tgt, face = bfx - side * (170 * z + 150 * a["scale"]), side
            elif action in TWO_PERSON:
                others = [o for o in lay["actors"] if o["cid"] != cid and not o.get("back")]
                if others:
                    o = min(others, key=lambda o: abs(o["x"] - a["x"]))
                    ox_ = o["x"]
                    if self._sleeping(sc, o["cid"], t):          # asleep on the floor: go to their head
                        ox_ = self._lie_place(o, self.specs[o["cid"]])[2]
                    side = 1 if ox_ > a["x"] else -1
                    dist = (300 if action == "grab_hand" or ox_ != o["x"] else 250) * max(a["scale"], o["scale"])
                    tgt, face = ox_ - side * dist, side
            if tgt is None:
                continue
            e = min(1.0, (t - start) / MOVE_S)
            e = 1 - (1 - e) ** 2
            x = x + (tgt - x) * e
            moved = True
            last_face = face
        return (x, last_face) if moved else None

    def _bg_image(self, bid, bg):
        cx, z, blur = bg[:3]
        key = (bid, round(cx), z, blur, bg[3] if len(bg) > 3 else None)
        if key in self.bgs:
            return self.bgs[key]
        im, ps, PW, G = panorama(bid, self.k)
        src = _soft(bid, self.k) if blur == "soft" else _blurred(bid, self.k) if blur else im
        vw, vh = FW / z, FH / z
        x0 = min(max(0.0, cx - vw / 2), PW - vw)
        y0 = G - G / z if len(bg) < 4 else min(max(0.0, bg[3] - vh / 2), FH - vh)
        box = (x0 * ps, y0 * ps, min(src.width, (x0 + vw) * ps), min(src.height, (y0 + vh) * ps))  # rounding
        out = src.resize((self.w, self.h), Image.LANCZOS, box=box)
        if self.cinema and bid in cinema.OUTDOOR | set(PLACES) and bid not in cinema.NO_GRADE:
            out = cinema.haze(out, 0.1 if blur else 0.06)           # the air between us and the background
        if len(self.bgs) > 24:
            self.bgs.clear()
        self.bgs[key] = (out, x0, y0, z)
        return self.bgs[key]

    WALK_S = 1.6     # seconds a walk in / walk out takes
    RUN_S = 0.75     # ... and a run in

    def lighting_at(self, sc, t):
        """The room's light at time t: the scene's lighting, changed by lines that switch the lights on / off.
        Returns (mode, seconds since the last switch)."""
        mode, since = getattr(sc, "lighting", "day") or "day", 99.0
        for ln in sc.lines:
            sw = getattr(ln, "lights", "")
            if sw and ln.start <= t:
                mode = "day" if sw == "on" else ("phone" if getattr(sc, "lighting", "") == "phone" else "dark")
                since = t - ln.start
        return mode, since

    def _light(self, sc, t, im, glows):
        mode, since = self.lighting_at(sc, t)
        if mode == "day":
            if since < 0.18:                               # the light just came on: a short flash
                return Image.blend(im, Image.new("RGB", im.size, (255, 255, 245)), 0.45 * (1 - since / 0.18))
            return im
        w, h = im.size
        q = 4                                              # light map at quarter size, smoothed when enlarged
        lm = Image.new("RGB", (w // q + 1, h // q + 1), (52, 58, 96))       # dark blue night
        d = ImageDraw.Draw(lm)
        for gx, gy, sc_, kind in glows:
            if kind == "phone" and mode != "phone":
                continue
            flick = 1 + 0.04 * math.sin(t * 13)
            rings = ((520, (96, 112, 170)), (380, (150, 170, 230)), (240, (210, 225, 255)), (130, (255, 255, 255)))                 if kind == "phone" else ((380, (150, 110, 150)), (270, (230, 190, 220)), (190, (255, 255, 255)))
            for r, col in rings:
                rr = r * sc_ * flick / q
                d.ellipse([gx / q - rr, gy / q - rr, gx / q + rr, gy / q + rr], fill=col)
        lm = lm.filter(ImageFilter.GaussianBlur(28 * self.k / q * 4)).resize((w, h), Image.BILINEAR)
        return ImageChops.multiply(im, lm)

    def _walk(self, sc, cid, a, t):
        """None (not walking), "hidden" (not in the frame yet / any more) or (x, direction) while walking."""
        mine = self._acts(sc, cid)
        off = -330 if a["x"] < FW / 2 else FW + 330           # leave / enter on the nearer side of the frame
        for i, (start, _end, action, _em, _l, _sp) in enumerate(mine):
            if i + 1 < len(mine) and mine[i + 1][0] <= t and action in ("run_across", "chase", "fly_away"):
                continue                                      # came back for a later line
            dur = self.RUN_S if action in ("run_in", "run_out") else self.WALK_S * (0.8 if "ride" in action else 1.0)
            u = (t - start) / dur
            kind = "run" if action.startswith("run") else "ride" if action.startswith("ride") else "walk"
            if action == "appear" and u < 0 and i == 0:            # not there yet, then simply there
                return "hidden"
            if action in ("run_across", "chase"):                 # dashes across the whole screen, left to right
                u = (t - start - (0.3 if action == "chase" else 0.0)) / 1.3
                if u < 0:
                    if i == 0:
                        return "hidden"
                    continue
                if u >= 1:
                    return "hidden"
                return (-330 + (FW + 660) * u, 1, "dash")
            if action == "fly_away" and u >= 0 and t - start >= 1.15:   # thrown off the screen: gone
                return "hidden"
            if action == "sneak_in":
                u = (t - start) / 2.6
                if u < 0 and i == 0:
                    return "hidden"
                if 0 <= u < 1:
                    return (off + (a["x"] - off) * u, 1 if a["x"] > off else -1, "sneak")
            if action in ("walk_in", "run_in", "ride_in"):
                if u < 0 and i == 0:
                    return "hidden"
                if 0 <= u < 1:
                    e = 1 - (1 - u) ** 2                          # slow down when arriving
                    return (off + (a["x"] - off) * e, 1 if a["x"] > off else -1, kind)
            elif action in ("walk_out", "run_out", "ride_out"):
                if u >= 1:
                    return "hidden"
                if u >= 0:
                    e = u * u                                     # speed up when leaving
                    return (a["x"] + (off - a["x"]) * e, 1 if off > a["x"] else -1, kind)
        return None

    def _sprite_3d(self, a, sp, action, emotion, speaking, still, mq, blink, tq, k):
        """A 3D character's picture for this frame, or None (then a flat stand-in is drawn)."""
        from . import three_d
        msg = three_d.status()
        if msg:
            if msg not in self.warnings:
                self.warnings.append(msg)
            return None
        back = a["view"] == "back"
        rot = math.pi + 0.25 if back else (1.3 * a["travel"] if a.get("travel") else 0.42 * a["face"])
        if back:
            action, tq, mq, blink = ("idle" if action in ("idle", "talk") else action), 0.0, 0.0, 0.0
        mouth = mq if speaking and not still else 0.0
        ppu = a["scale"] * k * three_d.UNIT * sp.get("height", 1.0)
        below = (FH - a["g"]) * k if a["g"] > FH * 0.9 else None
        ck = ("3d", a["cid"], round(rot, 2), round(ppu, 1), action, emotion, mouth, round(blink, 1), tq,
              round(below) if below is not None else None)
        def make():
            r = three_d.sprite(sp["model"], action, emotion, tq, mouth, blink, rot, ppu, below)
            return _trim(r[0], *r[1]) if r else r
        return self.sprites.get(ck, make)

    # ------------------------------------------------------------- frame
    def frame(self, sc, t: float) -> Image.Image:
        segs = self.segments(sc)
        si = next((i for i, s in enumerate(segs) if s[0] <= t < s[1]), 0 if t < segs[0][0] else len(segs) - 1)
        seg = segs[si]
        lkey = ("lay", id(sc), si)
        if lkey not in self.segs:
            self.segs[lkey] = self.layout(sc, seg[2])
        lay = self.segs[lkey]
        bid = sc.bg
        flat_bg = bid in FLAT_BACKGROUNDS
        base, x0, y0, z = self._bg_image(bid, lay["bg"])
        im = base.copy()
        k = self.k
        blur = lay["bg"][2]
        d = ImageDraw.Draw(im)

        def to_px(X, Y):
            return ((X - x0) * z * k, (Y - y0) * z * k)

        kst = kitchen.state_at(self.kev, t) if bid == "flat_kitchen" else None
        if bid in REALMS:
            animate_realm(im, bid, t, x0, y0, z, k, panorama(bid, k)[2], blur)
        elif bid in PLACES:
            animate_place(im, bid, t, x0, y0, z, k, panorama(bid, k)[2], blur, kadhai=kst is not None)
            if kst is not None:
                kitchen.draw(im, kst, t, x0, y0, z, k)
        elif flat_bg:
            vw = FW / z
            # birds
            for j in range(3):
                bx = x0 - 100 + ((t * 38 + j * 70 + _h(bid) % 300) % (vw + 260))
                by = 330 + j * 22 + 10 * math.sin(t * 1.3 + j)
                flap = math.sin(t * 9 + j * 1.7)
                px, py = to_px(bx, by)
                ws = 22 * z * k
                d.line([(px - ws, py - ws * 0.5 * flap), (px, py), (px + ws, py - ws * 0.5 * flap)],
                       fill=(30, 30, 40) if bid != "flat_city_night" else (200, 200, 220), width=max(1, round(3.5 * z * k)))
            # cars (street only)
            if bid != "flat_park":
                for j, (col, spd, lane) in enumerate((((214, 58, 50), 300, 1478), ((60, 120, 210), -360, 1560))):
                    span = vw + 700
                    off = (t * abs(spd) + j * span * 0.5 + 200) % (span + 900)
                    if off > span:
                        continue
                    cx = x0 - 350 + off if spd > 0 else x0 + vw + 350 - off
                    s_q = round(z * k * 100 * (1.0 if j == 0 else 1.08))
                    spr = car_sprite(col, s_q, blur, spd < 0)
                    px, py = to_px(cx - 130, lane - 120 * (1.08 if j else 1.0))
                    im.paste(spr, (round(px), round(py)), spr)

        bst, bag_px = None, None
        if self._bag_scene(sc):                  # the mystery bag lies on the floor
            bst = bag.state_at(self.bagplan[id(sc)], t)
            if bst:
                bag_px = to_px(self._bag_x(sc), lay["ground"])
                bag.draw_bag(im, bag_px[0], bag_px[1], z * k, bst[0], bst[1])
        if self.cinema and bid in PASSERS and lay.get("type") in ("wide", "single"):
            self._passersby(im, bid, t, x0, y0, z, k, lay["ground"], blur)
        line = next((l for l in sc.lines if l.start <= t < l.end), None)
        glows = []                               # faces lit by a phone screen (for the dark lighting)
        for a in lay["actors"]:
            cid = a["cid"]
            sp = self.specs[cid]
            speaking = bool(line and line.char == cid)
            mine = self._acts(sc, cid)
            now = next((m for m in mine if m[0] <= t < m[1]), None)       # acting right now (own line or meanwhile)
            recent = next((m for m in reversed(mine) if m[0] <= t), mine[0] if mine else None)
            if now is not None:
                action, emotion = now[2], now[3]
                t_act = t - now[0]
                key = now[4].text + cid
            elif recent is None:
                action, emotion, t_act, key = "idle", "neutral", t - sc.start, cid
            else:
                action = recent[2] if recent[2] in FLAT_PERSIST else "idle"
                emotion = recent[3] if recent[3] in KEEP_EMOTION or recent[2] == "look_camera" else "neutral"
                t_act, key = t - sc.start, cid
            if action in ("step_back", "lower_jug") + tuple(stick.STAYS) and now is None:
                t_act = 9.0                            # stays stepped back / jug down
            walk = self._walk(sc, cid, a, t)          # walking in or out of the frame
            if walk == "hidden":
                continue
            if walk:
                a = dict(a, x=walk[0], face=walk[1], travel=walk[1])
                action = {"ride": "ride", "dash": "cartoon_run", "sneak": "tiptoe"}.get(walk[2], "walk")
                t_act = (t - sc.start) * (2.2 if walk[2] == "run" else 1.0)
            elif action in ("walk_in", "walk_out", "appear", "run_in", "run_out", "ride_out", "sneak_in"):
                action = "talk" if speaking else "idle"
            elif action == "ride_in":                  # arrived on the cycle: stands with it
                action = "talk" if speaking else "idle"
            mv = self._moved_x(sc, cid, a, lay, x0, z, t)       # walked up to the stove / to someone
            if mv is not None and not walk:
                a = dict(a, x=mv[0], face=mv[1])
            if action in ("lie_sleep", "wake_jolt") and not walk and lay.get("type") in ("wide", "single"):
                lx, lf, _hx = self._lie_place(a, sp)           # asleep: head toward the middle, room for the alarm
                a = dict(a, x=lx, face=lf)
            reach_down = action in stick.TWO_PERSON and any(  # poking / shaking someone asleep on the floor
                self._sleeping(sc, o["cid"], t) for o in lay["actors"] if o["cid"] != cid)
            still = speaking and line.action == "idle"
            mouth = line.clip.mouth_at(t - line.start) if speaking and not still else 0.0
            if not speaking:
                still = False
            phase = (_h(cid) % 100) / 30
            blink = blink_amount(t, phase)
            # quantize so repeated drawings come from the cache
            mq = round(mouth * 6) / 6
            fq = 15 if speaking or action in SMOOTH_ACTIONS or sp["kind"] == "stick" else 6
            tq = round(t_act * fq) / fq
            if sp["kind"] == "3d":                  # real 3D model, rendered by the hidden browser
                spr3 = self._sprite_3d(a, sp, action, emotion, speaking, still, mq, blink, tq, k)
                if spr3 is not None:
                    spr, (ax, ay) = spr3
                    im.paste(spr, (round(a["x"] * k - ax), round(a["g"] * k - ay)), spr)
                    if action in PHONE_ACTIONS:
                        glows.append((a["x"] * k, (a["g"] - 1.45 * three_d_unit()) * k, a["scale"] * k, "phone"))
                    continue
                sp = sp["fallback"]
            if sp["kind"] in ("human", "brain", "stick"):
                pose = pose_for(action, emotion, tq, speaking, key)
            else:
                pose = dict(dy=0.0, walk=tq if action == "walk" else 0.0)
            eff = ""                                   # the line's cartoon effect (dizzy stars, "!", hearts...)
            if now is not None and getattr(now[4], "effect", "") and (now[5] or now[4].char not in sc.cast):
                eff = now[4].effect
                if sp["kind"] in ("human", "stick"):
                    pose["fx"] = set(pose.get("fx", ())) | {eff}
            held = self._held(sc, cid, t) if sp["kind"] in ("human", "stick") else None
            if reach_down and sp["kind"] in ("human", "stick"):     # bend down to the one on the floor
                pose["crouch"] = 0.55
                pose["rot"], pose["piv"] = -12, -20
                pose["R"] = ("ik", 250 + pose["dx"] * 1.5, -330)
                if action == "shake_awake":
                    pose["L"] = ("ik", -150 - pose["dx"], -300)
                pose["dx"] = 0.0
            if held:                                   # something they carry (a line's "prop")
                hold_prop(pose, held, action)
            blend = None
            if sp["kind"] == "stick" and not walk and not a.get("back"):   # ease from the last pose (0.18 s)
                blend = self._ease(sc, cid, mine, now, recent, t, pose, key)
            if a.get("back"):                    # big foreground back: hardly moves, so it is drawn once
                tq, mq, blink = (round(t_act * 6) / 6 if sp["kind"] not in ("human", "stick") else 0.0), 0.0, 0.0
                if sp["kind"] in ("human", "stick"):
                    pose = pose_for("rest" if action in ("idle", "talk") else action, "neutral", 0.0, False, key)
                    pose["dy"] = 0.0
            scale_px = a["scale"] * k
            ck = (cid, a["view"], a["face"], round(scale_px, 3), action, emotion, mq, round(blink, 1), tq, speaking, key,
                  held, eff, reach_down, blend)
            below = (FH - a["g"]) * k
            spr, (ax, ay) = self.sprites.get(ck, lambda: render_sprite(sp, a["view"], a["face"], scale_px, pose,
                                                                     emotion, mq, blink, tq, speaking, below))
            fx, fy = a["x"] * k, a["g"] * k
            rot = pose.get("rot", 0.0)
            if rot and not pose.get("move"):          # lying down: keep the head and the feet inside the frame
                hk = scale_px * sp.get("height", 1.0)
                sr = math.sin(math.radians(rot)) * a["face"]
                ends = (fx - 590 * sr * hk, fx + 450 * sr * hk)
                lo, hi = 0.05 * self.w, 0.95 * self.w
                if min(ends) < lo:
                    fx += lo - min(ends)
                elif max(ends) > hi:
                    fx -= max(ends) - hi
            if a["g"] < FH and not pose.get("cloud"):   # feet in the frame: soft shadow on the ground
                wpx = round((300 if sp["kind"] in ("human", "stick") else 360) * scale_px)
                sh = _shadow(wpx, max(2, round(wpx * 0.12)))
                im.paste(sh, (round(fx - sh.width / 2), round(fy - sh.height / 2)), sh)
            if action == "slip_fall" and t_act < 3:  # the banana peel that did it
                stick.draw_peel(im, fx, fy, scale_px * sp.get("height", 1.0), a["face"], t_act)
            if eff == "alarm":                        # a ringing alarm clock beside them (by the head when lying)
                hk = scale_px * sp.get("height", 1.0)
                lying = abs(math.sin(math.radians(pose.get("rot", 0.0)))) > 0.7
                sr = math.sin(math.radians(pose.get("rot", 0.0))) * a["face"]
                ax_ = fx - 590 * sr * hk - (130 if sr > 0 else -130) * hk if lying else fx - a["face"] * 300 * hk
                ax_ = min(max(ax_, 90 * hk), self.w - 90 * hk)
                stick.draw_alarm(im, ax_, fy, hk, t)
            if action == "invisible_wall" and 0.42 < t_act < 1.5:     # the invisible wall shows for a moment
                hk = scale_px * sp.get("height", 1.0)
                stick.draw_glass(im, fx + a["face"] * (180 + 70) * hk, fy, hk, (t_act - 0.42) / 1.08)
            if action == "crash_wall":               # the wall they run into
                hk = scale_px * sp.get("height", 1.0)
                stick.draw_wall(im, fx + a["face"] * 330 * hk, fy, hk, a["face"])
            if pose.get("move"):                     # thrown off the screen / running at a wall
                hk = scale_px * sp.get("height", 1.0)
                fx += a["face"] * pose["move"][0] * hk
                fy += pose["move"][1] * hk
            im.paste(spr, (round(fx - ax), round(fy - ay)), spr)
            if action in PHONE_ACTIONS and sp.get("kind") in ("human", "stick"):
                glows.append((fx, fy - (900 - 120) * a["scale"] * k * sp.get("height", 1.0), a["scale"] * k, "phone"))
            if sp.get("kind") == "brain":                   # the inner voice glows on its own in the dark
                glows.append((fx, fy - 830 * a["scale"] * k, a["scale"] * k, "self"))

        if bst and bst[0] == "photo":            # the photo flies out of the bag and is held up big
            inview = bag_px if bag_px and 0 <= bag_px[0] <= self.w else None
            bag.draw_photo(im, (inview[0], inview[1] - 120 * z * k) if inview else None, bst[1], t)
        if self.cinema and bid in cinema.OUTDOOR and lay.get("type") in ("wide", "single", "ots", "close") \
                and not self._stick_scene(sc):           # out-of-focus grass right in front of the camera
            h_ = _h(bid, round(seg[0], 2))
            cinema.foreground(im, h_ % 97, (-1, 1, 0, -1)[h_ % 4])
        im = self._light(sc, t, im, glows)
        if kst is not None:
            im = kitchen.glow(im, kst, t, x0, y0, z, k)
        if self.cinema and bid not in cinema.NO_GRADE and not self._stick_scene(sc):
            im = cinema.grade(im, t)                     # warm colour, sun glow, vignette, grain

        # slow camera drift inside the shot
        a0, b0 = seg[0], seg[1]
        u = min(1.0, max(0.0, (t - a0) / max(0.5, b0 - a0)))
        u = u * u * (3 - 2 * u)
        zoom = 1.0 + 0.045 * u
        if self._stick_scene(sc) and sc is self._last_scene() and si == len(segs) - 1:
            zoom = 1.0 + 0.16 * u                      # the punchline: push in
        dirx = 1 if _h(round(a0, 2)) % 2 else -1
        cw, ch = self.w / zoom, self.h / zoom
        cx = self.w / 2 + dirx * 16 * k * u
        cy = self.h * 0.56
        box = (max(0, cx - cw / 2), max(0, cy - ch * 0.56), 0, 0)
        box = (box[0], box[1], min(self.w, box[0] + cw), min(self.h, box[1] + ch))
        return im.resize((self.w, self.h), Image.BILINEAR, box=box)
