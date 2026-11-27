"""The fixed menus the app (and the AI script writer) can pick from.

To add a new outfit or voice, add one entry here. The UI dropdowns and the AI
prompt are built from these lists, so nothing else needs to change.
"""
from __future__ import annotations

EMOTIONS = ["neutral", "happy", "sad", "worried", "angry", "surprised", "laughing", "crying",
            "scared", "excited", "sleepy", "embarrassed", "confused", "bored", "in_love",
            "proud", "disgusted", "thinking", "shocked", "relieved"]

# id -> label shown in the dropdown. Order = order in the dropdown.
ACTION_LABELS = {
    "talk": "Talk", "idle": "Stand still (mouth does not move)", "wave": "Wave / greet", "point": "Point", "think": "Think",
    "explain": "Explain (open hands)", "thumbs_up": "Thumbs up", "ok_sign": "OK sign", "stop": "Stop (raise hand)",
    "arms_crossed": "Arms crossed", "shrug": "Shrug", "look_around": "Look around", "walk": "Walk in place",
    "jump": "Jump", "cheer": "Cheer / celebrate", "clap": "Clap", "dance": "Dance", "facepalm": "Facepalm",
    "use_phone": "Use phone", "phone_call": "Talk on phone (phone at ear)", "drink_tea": "Drink tea", "read_book": "Read a book", "eat": "Eat a snack",
    "punch": "Punch", "slap": "Slap", "walk_in": "Walk in (enters the scene)", "walk_out": "Walk out (leaves the scene)",
    "appear": "Appear (hidden until this line)",
    "wipe_tears": "Wipe tears", "hold_parcel": "Hold a food parcel", "hide_behind": "Hide something behind the back",
    "throw": "Throw a chappal (at the camera)",
    "cook": "Cook at the stove (frying)", "step_back": "Step back in fear", "run_in": "Run in (enters running)",
    "hold_jug": "Lift a water jug (about to throw it)", "lower_jug": "Jug pushed down (water splashes)",
    "grab_hand": "Grab someone's hand (stop them)", "turn_off_gas": "Turn off the gas knob",
    "cover_kadhai": "Cover the kadhai with a thali", "hand_on_shoulder": "Hand on someone's shoulder",
    "look_camera": "Look at the camera (relieved)",
    "ride_in": "Ride in on a cycle", "ride_out": "Ride away on a cycle", "ride_cycle": "Ride a cycle (in place)",
    "run_out": "Run away (leaves running)",
    "sit": "Sit on sofa", "sit_phone": "Sit and use phone", "sit_tea": "Sit and drink tea",
    "sit_read": "Sit and read", "sit_eat": "Sit and eat a snack", "sit_sleep": "Sit and sleep", "sit_call": "Sit and talk on the phone", "folded_hands": "Folded hands (pleading, namaste)",
    "wipe_sweat": "Wipe sweat off the forehead (nervous)",
    "go_to_bag": "Walk up to the mystery bag (bends toward it)",
}
# slapstick comedy moves (stick.py): they work for the stickmen and the flat cartoon people
SLAPSTICK_LABELS = {
    "slip_fall": "Slip and fall on the back (banana-peel style)", "fall_face": "Trip and fall on the face",
    "get_up": "Get up after a fall", "fly_away": "Get hit and fly off the screen",
    "hit_head": "Bonk on the head (stars, dizzy)", "freeze": "Freeze in shock (stiff, trembling)",
    "double_take": "Double-take (look away, look back shocked)", "faint": "Faint (fall back stiff, X eyes)",
    "fight_cloud": "Fight in a dust cloud", "crash_wall": "Run and crash into a brick wall (splat)",
    "dizzy": "Dizzy (wobbly, spiral eyes)", "shiver": "Shiver with fear",
    "cartoon_run": "Cartoon run on the spot (legs spinning)",
    "run_across": "Run across the screen (enters, exits other side)",
    "chase": "Chase (runs across just behind the other one)", "sneak_in": "Sneak in on tiptoe (enters)",
    "tiptoe": "Sneak on tiptoe (in place)", "laugh_floor": "Roll on the floor laughing", "kick": "Kick",
    "jaw_drop": "Jaw drop (eyes pop out)",
    "lie_sleep": "Sleep lying on the floor (snoring, keeps sleeping)",
    "sleep_stand": "Fall asleep standing up (swaying, snoring)",
    "wake_jolt": "Wake up with a jolt (jumps up, eyes pop)",
    "poke": "Poke someone (walks up, poke poke poke)", "shake_awake": "Shake someone by the shoulders",
    "disappointed": "Exaggerated disappointment (slumps, rain cloud)",
    "invisible_wall": "Walk into an invisible wall (bonk, glass shows for a moment)",
}
ACTION_LABELS.update(SLAPSTICK_LABELS)
ACTIONS = list(ACTION_LABELS)
# cartoon effects drawn around the character during a line (stick.py)
EFFECT_LABELS = {
    "": "Effect: none", "dizzy": "Dizzy stars around the head", "impact": "Impact burst (POW star)",
    "speed": "Speed lines", "dust": "Dust puffs at the feet", "sweat": "Sweat drops flying",
    "exclaim": "Red ! above the head", "question": "? above the head", "steam": "Angry steam from the ears",
    "hearts": "Floating hearts", "shiver": "Shivering lines", "rain_cloud": "Rain cloud over the head (sad)",
    "eyes_pop": "Eyes pop out", "idea": "Idea bulb above the head", "sparkle": "Sparkles (proud, shiny)",
    "alarm": "Alarm clock ringing next to them", "fly": "A fly buzzing around the head", "snore": "Snot bubble (asleep)",
}
EFFECTS = [k for k in EFFECT_LABELS if k]

# The three characters, copied from their character sheets (hoodie, dark jeans, white sneakers).
# Each one's face is a set of 20 pictures in assets/characters/<id>/heads/<emotion>.png.
_JEANS = (32, 42, 56)
LOOKS = {
    "rahul": dict(label="Rahul (blue hoodie)", skin=(251, 204, 133), shirt=(20, 101, 199), pants=_JEANS,
                  hair=(76, 41, 20), hair_style="spiky", dress=None, female=False, scale=1.0, sprite=True),
    "aman": dict(label="Aman (orange hoodie)", skin=(251, 209, 155), shirt=(236, 102, 14), pants=_JEANS,
                 hair=(64, 43, 32), hair_style="swoop", dress=None, female=False, scale=0.99, sprite=True),
    "priya": dict(label="Priya (green hoodie)", skin=(252, 206, 153), shirt=(15, 160, 84), pants=_JEANS,
                  hair=(74, 50, 38), hair_style="long", dress=None, female=True, scale=0.97, sprite=True),
}
# Maa: realistic faces and her saree are cut from her character sheet; she is a little shorter than the others.
LOOKS["maa"] = dict(label="Maa (saree)", skin=(222, 140, 98), shirt=(112, 28, 42), pants=(240, 226, 196),
                    hair=(112, 118, 135), hair_style="none", dress=None, outfit="saree", female=True, scale=0.94,
                    sprite=True, anchor_y=0.50)
# Golu: a simple 3D clay-toy character built from shaded spheres (see clay.py); no outlines, no picture files.
LOOKS["clay"] = dict(label="Golu (clay 3D toy)", skin=(240, 190, 150), shirt=(150, 118, 222), pants=(52, 92, 112),
                     hair=(78, 50, 36), hair_style="none", dress=None, style="clay", female=False, scale=1.0,
                     sprite=False, shoe=(226, 72, 62))
# Flat cartoon characters (drawn from shapes, see flat.py). They act in the flat style with an automatic camera.
HIDDEN_LOOKS: set[str] = set()   # looks kept out of the Cast menu (still usable by script import and tests)
_FLAT = {
    "flat_uncle": ("Flat: Uncle (red cap, vest)", False, dict(
        kind="human", skin=(232, 180, 138), top="vest", top_color=(240, 238, 230), bottom="pants",
        bottom_color=(190, 168, 112), hat="cap", hat_color=(214, 60, 45), hair="none", hair_color=(58, 36, 28),
        mustache=True, female=False, height=1.0)),
    "flat_aunty": ("Flat: Aunty (kurta, hair bun)", True, dict(
        kind="human", skin=(242, 196, 158), top="kurta", top_color=(226, 92, 120), accent=(250, 200, 70),
        bottom="dress", bottom_color=(120, 40, 70), hat=None, hair="bun", hair_color=(40, 30, 30),
        mustache=False, female=True, height=0.95, bindi=True)),
    "flat_boy": ("Flat: Boy (blue t-shirt, shorts)", False, dict(
        kind="human", skin=(240, 192, 150), top="tshirt", top_color=(60, 130, 214), bottom="shorts",
        bottom_color=(60, 66, 84), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=0.78)),
    "flat_man": ("Flat: Young man (yellow t-shirt)", False, dict(
        kind="human", skin=(234, 184, 140), top="tshirt", top_color=(240, 196, 60), bottom="pants",
        bottom_color=(52, 70, 110), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=1.0)),
    "flat_girl": ("Flat: Girl (green kurta, long hair)", True, dict(
        kind="human", skin=(246, 204, 168), top="kurta", top_color=(70, 170, 120), accent=(240, 240, 230),
        bottom="dress", bottom_color=(240, 236, 226), hat=None, hair="long", hair_color=(36, 28, 28),
        mustache=False, female=True, height=0.9, bindi=False)),
    "flat_police": ("Flat: Police havaldar (khaki uniform, lathi)", False, dict(
        kind="human", skin=(228, 176, 132), top="uniform", top_color=(196, 168, 110), bottom="pants",
        bottom_color=(196, 168, 110), hat="police_cap", hat_color=(196, 168, 110), band_color=(196, 40, 40),
        hair="none", hair_color=(40, 30, 28), mustache=True, female=False, height=1.0, belly=1.0, holds="lathi",
        shoe=(30, 28, 30))),
    "flat_kid": ("Flat: Kid, about 10 (striped t-shirt, shorts)", False, dict(
        kind="human", skin=(242, 196, 156), top="tshirt", top_color=(230, 80, 70), bottom="shorts",
        bottom_color=(50, 80, 140), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=0.66, stripes=(250, 236, 220))),
    "flat_youth_a": ("Flat: Young man, 20 (open check shirt, quiff)", False, dict(
        kind="human", skin=(244, 200, 160), top="open_shirt", top_color=(250, 250, 246), shirt_color=(200, 46, 52),
        bottom="pants", bottom_color=(46, 86, 160), hat=None, hair="quiff", hair_color=(34, 26, 24), mustache=False,
        stubble=True, watch=True, female=False, height=1.0, build=0.92, shoe=(245, 245, 245))),
    "flat_youth_b": ("Flat: Young man, 20 (hoodie, spiky hair)", False, dict(
        kind="human", skin=(238, 190, 148), top="hoodie", top_color=(60, 66, 84), bottom="pants",
        bottom_color=(36, 38, 46), hat=None, hair="spiky", hair_color=(28, 24, 24), mustache=False, stubble=False,
        female=False, height=1.0, build=0.92, shoe=(245, 245, 245))),
    "flat_youth_c": ("Flat: Young man, 20 (graphic tee, side fringe)", False, dict(
        kind="human", skin=(232, 182, 140), top="tee_print", top_color=(250, 190, 40), accent=(36, 40, 60),
        accent2=(250, 250, 250), bottom="pants", bottom_color=(60, 96, 150), hat=None, hair="side",
        hair_color=(40, 28, 24), mustache=False, stubble=True, watch=True, female=False, height=1.0, build=0.95,
        shoe=(40, 40, 46))),
    # stickmen (stick.py): thick lines, a big round head and big expressive eyes
    "stick_classic": ("Stickman: Classic (black)", False, dict(kind="stick", color=(30, 30, 34), height=1.0)),
    "stick_blue": ("Stickman: Blue (spiky hair)", False, dict(kind="stick", color=(40, 96, 200), hair="spiky",
                                                              height=1.0)),
    "stick_red": ("Stickman: Red (headband)", False, dict(kind="stick", color=(206, 44, 44), band=True,
                                                          accent=(206, 44, 44), height=1.0)),
    "stick_girl": ("Stickman: Girl (bow, skirt)", True, dict(kind="stick", color=(200, 50, 130), bow=True, skirt=True,
                                                             lashes=True, accent=(246, 110, 170), height=0.95)),
    "stick_kid": ("Stickman: Kid (cap)", False, dict(kind="stick", color=(234, 120, 30), cap=True,
                                                     accent=(60, 140, 220), hair="tuft", height=0.72)),
    "stick_boss": ("Stickman: Boss (tie, glasses, mustache)", False, dict(kind="stick", color=(60, 62, 72), tie=True,
                                                                          glasses=True, mustache=True, hair="messy",
                                                                          accent=(200, 40, 50), height=1.04)),
    # village characters (bald grandpa, saree aunty, girl with a braid, farmer, a cool dog)
    "flat_dadaji": ("Flat: Dadaji (bald, round glasses, white kurta, gamchha, walking stick)", False, dict(
        kind="human", skin=(240, 194, 154), top="kurta", top_color=(250, 248, 238), accent=(236, 230, 212),
        bottom="pants", bottom_color=(244, 240, 228), hat=None, hair="bald", hair_color=(200, 200, 206),
        mustache="big", glasses=True, buttons=True, plain=True, gamchha=((196, 40, 52), (252, 236, 232)), holds="cane",
        female=False, height=0.96, build=0.94, shoe=(120, 80, 50))),
    "flat_village_aunty": ("Flat: Village aunty (saree, long braid, bindi)", True, dict(
        kind="human", skin=(242, 198, 160), top="kurta", top_color=(236, 112, 44), accent=(196, 30, 96),
        bottom="dress", bottom_color=(236, 112, 44), hat=None, hair="braid", hair_color=(32, 24, 24),
        ribbon=(196, 30, 96), mustache=False, female=True, bindi=True, earrings=True, height=0.93)),
    "flat_village_girl": ("Flat: Village girl (kurta, dupatta, braid with ribbon)", True, dict(
        kind="human", skin=(246, 204, 168), top="kurta", top_color=(70, 168, 116), accent=(250, 200, 50),
        bottom="pants", bottom_color=(246, 240, 226), hat=None, hair="braid", hair_color=(30, 24, 24),
        ribbon=(230, 40, 60), mustache=False, female=True, bindi=False, earrings=True, height=0.87)),
    "flat_farmer": ("Flat: Farmer (saffron pagdi, kurta-dhoti, big mustache, gamchha)", False, dict(
        kind="human", skin=(228, 178, 134), top="kurta", top_color=(242, 238, 224), accent=(232, 226, 208),
        bottom="pants", bottom_color=(248, 246, 236), hat="pagdi", hat_color=(244, 140, 28), hair="short",
        hair_color=(36, 28, 26), mustache="big", plain=True, gamchha=((40, 110, 200), (240, 246, 255)), female=False,
        height=1.0, build=1.04, shoe=(110, 70, 40))),
    "flat_lalit": ("Flat: Lalit (young man, rolled-up blue shirt, side parting, watch)", False, dict(
        kind="human", skin=(242, 198, 158), top="open_shirt", top_color=(250, 250, 246), shirt_color=(70, 130, 200),
        bottom="pants", bottom_color=(44, 64, 110), hat=None, hair="real_side", hair_color=(66, 44, 30), mustache=False,
        stubble=True, watch=True, female=False, height=1.02, build=0.94, shoe=(245, 245, 245))),
    "flat_rahul": ("Flat: Rahul (young man, yellow t-shirt, quiff, orange gamchha)", False, dict(
        kind="human", skin=(232, 184, 142), top="tshirt", top_color=(250, 196, 40), bottom="pants",
        bottom_color=(60, 60, 72), hat=None, hair="real_quiff", hair_color=(58, 38, 26), mustache=False,
        gamchha=((240, 120, 30), (255, 236, 200)), female=False, height=1.0, build=0.92, shoe=(200, 60, 50))),
    "flat_deepak": ("Flat: Deepak (young man, fat, glasses, green hoodie)", False, dict(
        kind="human", skin=(238, 192, 152), top="hoodie", top_color=(60, 150, 100), bottom="pants",
        bottom_color=(96, 76, 56), hat=None, hair="real_crop", hair_color=(52, 36, 28), mustache=False, glasses=True,
        female=False, height=0.97, build=1.62, chubby=1.0, shoe=(60, 60, 70))),
    # road characters (speed breaker comedy): two labourers, an uncle on his scooter, a biker
    "flat_majdoor_a": ("Flat: Labourer A (red hard hat, green shirt)", False, dict(
        kind="human", skin=(184, 122, 80), top="tshirt", top_color=(108, 140, 92), bottom="pants",
        bottom_color=(92, 92, 84), hat="hardhat", hat_color=(226, 84, 40), hair="short", hair_color=(30, 24, 22),
        mustache=False, stubble=True, female=False, height=0.98, build=0.95, shoe=(90, 70, 50))),
    "flat_majdoor_b": ("Flat: Labourer B (blue hard hat, brown shirt)", False, dict(
        kind="human", skin=(170, 110, 72), top="tshirt", top_color=(150, 102, 62), bottom="pants",
        bottom_color=(110, 84, 60), hat="hardhat", hat_color=(52, 110, 206), hair="short", hair_color=(30, 24, 22),
        mustache=True, female=False, height=1.02, build=0.92, shoe=(80, 60, 44))),
    "flat_scooter_uncle": ("Flat: Scooter uncle (white helmet, glasses, mustache, yellow shirt, tie, red scooter)",
                           False, dict(
        kind="human", skin=(232, 182, 140), top="tshirt", top_color=(240, 190, 50), bottom="pants",
        bottom_color=(120, 86, 52), hat="helmet", hat_color=(246, 246, 240), hair="short", hair_color=(60, 44, 36),
        mustache="big", glasses=True, tie=(170, 40, 40), female=False, height=0.98, build=1.15, shoe=(90, 60, 40),
        vehicle="scooter", vehicle_color=(212, 42, 38))),
    "flat_biker": ("Flat: Biker (black jacket, sunglasses, black motorbike)", False, dict(
        kind="human", skin=(222, 170, 128), top="hoodie", top_color=(38, 38, 44), bottom="pants",
        bottom_color=(40, 46, 70), hat=None, hair="spiky", hair_color=(24, 20, 20), mustache=False, shades=True,
        female=False, height=1.0, build=0.95, shoe=(30, 30, 34), vehicle="bike", vehicle_color=(34, 34, 40))),
    # office comedy: a corporate boss, and an employee (with a halo for heaven scenes)
    "flat_boss": ("Flat: Corporate boss (black suit, white shirt, tie, big mustache)", False, dict(
        kind="human", skin=(236, 188, 146), top="open_shirt", top_color=(250, 250, 248), shirt_color=(34, 34, 40),
        bottom="pants", bottom_color=(34, 34, 40), hat=None, hair="short", hair_color=(24, 20, 20), mustache="big",
        tie=(30, 30, 36), female=False, height=1.0, build=1.18, shoe=(24, 24, 28))),
    "flat_employee": ("Flat: Employee (orange spiky hair, red-white striped t-shirt)", False, dict(
        kind="human", skin=(250, 232, 216), top="tshirt", top_color=(206, 40, 44), stripes=(250, 246, 240),
        bottom="pants", bottom_color=(36, 36, 42), hat=None, hair="spiky", hair_color=(236, 112, 30), mustache=False,
        female=False, height=0.98, build=0.9, shoe=(30, 30, 34))),
    "flat_employee_angel": ("Flat: Employee in heaven (orange spiky hair, striped t-shirt, halo)", False, dict(
        kind="human", skin=(250, 232, 216), top="tshirt", top_color=(206, 40, 44), stripes=(250, 246, 240),
        bottom="pants", bottom_color=(36, 36, 42), hat=None, hair="spiky", hair_color=(236, 112, 30), mustache=False,
        halo=True, female=False, height=0.98, build=0.9, shoe=(30, 30, 34))),
    "flat_cool_dog": ("Flat: Cool dog (sunglasses, cap, gold chain)", False, dict(
        kind="dog", color=(150, 96, 56), light=(206, 160, 112), shades=True, cap=(40, 96, 210), chain=True,
        height=1.05)),
    "flat_brain": ("Flat: My brain (inner voice, little devil)", False, dict(
        kind="brain", color=(244, 150, 172), glow=(255, 110, 140), horns=True, height=1.0)),
    "flat_heart": ("Flat: Talking heart (red, beats, big eyes, little arms and legs)", False, dict(
        kind="brain", shape="heart", color=(222, 36, 52), glow=(255, 90, 110), horns=False, height=1.0)),
    "flat_heart_broken": ("Flat: Broken heart (cracked, with a plaster; talks, cries, beats)", False, dict(
        kind="brain", shape="heart", broken=True, color=(206, 40, 56), glow=(170, 120, 200), horns=False, height=0.9)),
    "flat_dog": ("Flat: Dog (brown)", False, dict(kind="dog", color=(146, 94, 58), light=(196, 150, 104), height=1.0)),
    "flat_cat": ("Flat: Cat (grey)", False, dict(kind="cat", color=(150, 150, 160), light=(220, 220, 226), height=0.9)),
}
for _k, (_label, _fem, _spec) in _FLAT.items():
    LOOKS[_k] = dict(label=_label, style="flat", flat=_spec, female=_fem, sprite=False, scale=1.0,
                     hidden=_k in HIDDEN_LOOKS,
                     skin=_spec.get("skin", (200, 140, 95)), shirt=_spec.get("top_color", _spec.get("color")),
                     pants=_spec.get("bottom_color", (60, 60, 60)), hair=_spec.get("hair_color", (40, 30, 30)))
# 3D characters: real Three.js models (studio/web3d/chars.js) rendered by a hidden browser, see three_d.py.
# "flat" holds the colours of a flat stand-in, used only when no browser is available.
_3D = {
    "3d_oldman": ("3D: Old man (grey hair, mustache)", False, "oldman", dict(
        skin=(217, 168, 130), top="tshirt", top_color=(122, 143, 106), bottom="pants", bottom_color=(107, 88, 71),
        hair="short", hair_color=(220, 220, 226), mustache=True)),
    "3d_youngman": ("3D: Young man (yellow hoodie)", False, "hoodie", dict(
        skin=(227, 176, 138), top="tshirt", top_color=(247, 194, 74), bottom="pants", bottom_color=(59, 95, 168),
        hair="short", hair_color=(90, 64, 48), mustache=False)),
    "3d_boy": ("3D: Boy (spiky hair, black hoodie)", False, "spiky", dict(
        skin=(227, 176, 138), top="tshirt", top_color=(38, 40, 46), bottom="pants", bottom_color=(58, 63, 75),
        hair="short", hair_color=(64, 48, 42), mustache=False)),
    "3d_woman": ("3D: Young woman (sari)", True, "woman", dict(
        skin=(232, 184, 144), top="kurta", top_color=(31, 122, 92), accent=(198, 40, 69), bottom="dress",
        bottom_color=(198, 40, 69), hair="long", hair_color=(74, 48, 32), mustache=False, bindi=False)),
}
for _k, (_label, _fem, _model, _fb) in _3D.items():
    _fb.update(kind="human", hat=None, female=_fem, height=1.0)
    LOOKS[_k] = dict(label=_label, style="3d", flat=dict(kind="3d", model=_model, height=1.0, fallback=_fb),
                     female=_fem, sprite=False, scale=1.0, skin=_fb["skin"], shirt=_fb["top_color"],
                     pants=_fb["bottom_color"], hair=_fb["hair_color"])
# The narrator: a voice-over that is never on screen (the camera keeps showing the scene while it speaks).
LOOKS["narrator"] = dict(label="Narrator (voice-over, not on screen)", style="narrator", female=False, sprite=False,
                         scale=1.0, skin=(200, 150, 110), shirt=(90, 90, 100), pants=(60, 60, 70), hair=(40, 30, 30))
NARRATOR_LOOKS = {"narrator"}
for _k, _v in LOOKS.items():
    _v["id"] = _k
# the characters shown in the Cast menu; every other look is hidden (old projects and scripts using them still work)
CAST = ["flat_lalit", "flat_rahul", "flat_deepak", "flat_dadaji", "flat_village_aunty", "flat_village_girl",
        "flat_farmer", "flat_cool_dog", "narrator"]
CAST_PENDING: set[str] = set()       # new characters waiting for their pictures to be approved
for _k, _v in LOOKS.items():
    _v["hidden"] = _k not in CAST or _k in CAST_PENDING

# A character's body (flat cartoon style). "" keeps the look's own.
HEIGHTS = {"": "Height: as the look", "child": "Height: child", "short": "Height: short", "normal": "Height: normal",
           "tall": "Height: tall", "very_tall": "Height: very tall"}
HEIGHT_VALUES = {"child": 0.66, "short": 0.86, "normal": 0.97, "tall": 1.07, "very_tall": 1.15}
BUILDS = {"": "Build: as the look", "thin": "Build: thin", "normal": "Build: normal", "fat": "Build: fat",
          "very_fat": "Build: very fat"}
BUILD_VALUES = {"thin": 0.86, "normal": 1.0, "fat": 1.28, "very_fat": 1.5}
OUTFIT_COLORS = {"": "Outfit: as the look", "red": (214, 60, 52), "blue": (60, 120, 210), "green": (70, 160, 100),
                 "yellow": (240, 196, 60), "orange": (240, 140, 50), "pink": (226, 110, 150),
                 "purple": (140, 90, 190), "white": (240, 238, 232), "black": (50, 50, 56), "grey": (140, 140, 150),
                 "brown": (150, 100, 66), "khaki": (196, 168, 110), "sky_blue": (130, 190, 236),
                 "maroon": (130, 40, 56)}

# Things a character can hold or have with them (flat cartoon style). A line's "prop" stays with the character for
# the rest of the scene ("none" puts it away).
PROP_LABELS = {"": "Prop: none", "phone": "Mobile phone (in the hand)", "glass": "Glass of water", "bottle": "Water bottle",
               "cup": "Tea cup", "book": "Book", "newspaper": "Newspaper", "suitcase": "Suitcase (rolling)",
               "bag": "Bag", "umbrella": "Umbrella (open)", "laptop": "Laptop", "flowers": "Flowers",
               "cycle": "Cycle (bicycle, standing with it)", "parcel": "Food parcel", "jug": "Water jug",
               "thali": "Steel thali (plate)", "chappal": "Chappal", "lathi": "Lathi (stick)",
               # food
               "samosa": "Samosa", "jalebi": "Jalebi", "vada_pav": "Vada pav", "cutting_chai": "Cutting chai (small glass)",
               "kulhad": "Kulhad chai (clay cup)", "plate_samosa": "Plate of samosas (both hands)",
               "tasla": "Tasla (iron pan of cement, both hands)",
               "chips": "Packet of chips", "blanket": "Blanket (covers the body: lie_sleep under it)",
               # fruit
               "banana": "Banana", "apple": "Apple", "mango": "Mango", "orange": "Orange", "grapes": "Grapes",
               "watermelon": "Watermelon slice",
               # vegetables
               "tomato": "Tomato", "onion": "Onion", "potato": "Potato", "carrot": "Carrot", "brinjal": "Brinjal (baingan)",
               "chilli": "Green chilli", "cabbage": "Cabbage", "cucumber": "Cucumber (kheera)", "lemon": "Lemon (nimbu)",
               "cauliflower": "Cauliflower (gobhi)", "bhindi": "Bhindi (lady finger)", "garlic": "Garlic", "peas": "Peas (matar pod)",
               "bhutta": "Bhutta (roasted corn)", "coconut": "Coconut", "veg_basket": "Basket of vegetables",
               "sabzi_bag": "Cloth bag of vegetables"}
FOOD_PROPS = {"samosa", "jalebi", "vada_pav", "banana", "apple", "mango", "orange", "grapes", "watermelon", "tomato",
              "onion", "potato", "carrot", "brinjal", "chilli", "cabbage", "cucumber", "lemon", "cauliflower", "bhindi",
              "garlic", "peas", "bhutta", "coconut"}
DRINK_PROPS = {"cutting_chai", "kulhad", "glass", "bottle"}
PROPS = [k for k in PROP_LABELS if k]

# Procedural flat-cartoon backgrounds (animated: cars, birds). id -> dropdown label.
FLAT_BACKGROUNDS = {
    "flat_city_street": "Flat cartoon: city street (cars, birds)",
    "flat_city_night": "Flat cartoon: city street at night",
    "flat_park": "Flat cartoon: park",
    "flat_swarg": "Flat cartoon: Swarg / heaven (clouds, sun rays, petals)",
    "flat_nark": "Flat cartoon: Nark / hell (fire, lava, embers)",
    "flat_village": "Flat cartoon: village (huts, well, smoke)",
    "flat_school": "Flat cartoon: school (flag, clock)",
    "flat_kitchen": "Flat cartoon: kitchen (stove, steam, cooker)",
    "flat_office": "Flat cartoon: office (computers, city window)",
    "flat_market": "Flat cartoon: market (stalls, lights, shoppers)",
    "flat_bedroom": "Flat cartoon: bedroom at night (bed, window, fan)",
    "flat_chai_tapri": "Flat cartoon: chai ki tapri, Chacha ki Chai (colourful stall, chaiwala pouring chai)",
    "flat_sabzi_mandi": "Flat cartoon: sabzi mandi (vegetable and fruit carts)",
    "flat_airport": "Flat cartoon: airport (departure board, planes)",
    "flat_bus_stop": "Flat cartoon: bus stop (shelter, passing bus)",
    "flat_highway": "Flat cartoon: highway with a speed breaker (trees, marker posts, golden hour)",
    "flat_bathroom": "Flat cartoon: bathroom (tiles, shower curtain, bucket and mug, wooden door)",
    "flat_white": "Plain white (stickman comedy)",
    "flat_doodle": "Doodle paper (hand-drawn hills, sun, clouds)",
}

# Camera movement during a line (flat cartoon style). "auto" picks one from the line's emotion and never repeats
# the same move twice in a row, so the camera is never still for long.
CAMERA_MOVES = {"auto": "Move: automatic (follows the emotion)", "static": "Move: none (steady)",
                "push_in": "Move: slow zoom in", "pull_out": "Move: slow zoom out",
                "punch_in": "Move: snap zoom in (shock)", "punch_out": "Move: snap zoom out",
                "dutch": "Move: tilted angle (tension)", "low": "Move: low angle (looking up)",
                "pan": "Move: slow pan across", "shake": "Move: shaky camera (panic)",
                "crash": "Move: crash zoom with a shake (big moment)"}

# Camera shot for a line (flat cartoon style). "auto" picks one like a cartoon editor would.
SHOT_LABELS = {"auto": "Camera: automatic", "wide": "Camera: wide (everyone)", "single": "Camera: on the speaker",
               "ots": "Camera: over the shoulder", "close": "Camera: close-up",
               "stove": "Camera: close-up on the stove (kitchen)", "bag": "Camera: close-up on the mystery bag"}

# Older saved projects used other ids; they now open as the closest of the three.
LOOK_ALIASES = {"blue_shirt": "rahul", "rahul_sheet": "rahul", "vikram": "rahul", "vikram_sheet": "rahul",
                "red_kurta": "aman", "aman_sheet": "aman",
                "yellow_top": "priya", "priya_sheet": "priya", "neha": "priya", "neha_sheet": "priya",
                "green_saree": "priya"}

VOICES = [
    dict(id="hi-IN-MadhurNeural", label="Hindi, male (Madhur)", lang="hi", gender="male"),
    dict(id="hi-IN-SwaraNeural", label="Hindi, female (Swara)", lang="hi", gender="female"),
    dict(id="en-IN-PrabhatNeural", label="English (India), male (Prabhat)", lang="en", gender="male"),
    dict(id="en-IN-NeerjaNeural", label="English (India), female (Neerja)", lang="en", gender="female"),
]
# Gemini voices (Google Gemini text-to-speech, uses GEMINI_API_KEY). The line's emotion sets how it is spoken.
# Gemini voices are not officially male or female; "gender" here is how they sound, used for fallbacks and sounds.
_GEMINI = [
    ("Algenib", "male", "gravelly, older"), ("Charon", "male", "calm, clear"), ("Puck", "male", "upbeat"),
    ("Fenrir", "male", "excitable"), ("Orus", "male", "firm"), ("Iapetus", "male", "clear"),
    ("Achird", "male", "friendly"), ("Sadachbia", "male", "lively, young"),
    ("Kore", "female", "firm"), ("Leda", "female", "youthful"), ("Aoede", "female", "breezy"),
    ("Gacrux", "female", "mature, older"), ("Sulafat", "female", "warm"), ("Despina", "female", "smooth"),
]
for _n, _g, _d in _GEMINI:
    VOICES.append(dict(id=f"gemini:{_n}", label=f"Gemini, {_g}: {_n} ({_d}, follows emotion)", lang="any",
                       gender=_g, engine="gemini"))
# Sarvam voices (Sarvam AI Bulbul v3, uses SARVAM_API_KEY): natural Hindi and Indian English. The description is how
# each one sounds, from its measured pitch.
_SARVAM = [
    ("kabir", "male", "deep"), ("shubh", "male", "deep"), ("soham", "male", "deep"), ("varun", "male", "deep"),
    ("mani", "male", "deep"), ("gokul", "male", "low"), ("vijay", "male", "low"), ("ratan", "male", "low"),
    ("aditya", "male", "medium"), ("rehan", "male", "medium"), ("aayan", "male", "medium"),
    ("anand", "male", "medium"), ("rahul", "male", "medium"), ("amit", "male", "medium"), ("tarun", "male", "medium"),
    ("sunny", "male", "medium"), ("advait", "male", "medium"), ("sumit", "male", "light"),
    ("manan", "male", "light, young"), ("mohit", "male", "light, young"), ("ashutosh", "male", "light, young"),
    ("rohan", "male", "light, young"), ("dev", "male", "high, boyish"),
    ("neha", "female", "low, mature"), ("simran", "female", "medium"), ("priya", "female", "medium"),
    ("pooja", "female", "medium"), ("shruti", "female", "medium"), ("roopa", "female", "medium"),
    ("ishita", "female", "medium"), ("rupali", "female", "medium"), ("shreya", "female", "medium"),
    ("tanya", "female", "high"), ("suhani", "female", "high"), ("kavya", "female", "high"),
    ("ritu", "female", "high"), ("kavitha", "female", "very high"),
]
for _n, _g, _d in _SARVAM:
    VOICES.append(dict(id=f"sarvam:{_n}", label=f"Sarvam, {_g}: {_n.title()} ({_d}, natural Hindi)", lang="any",
                       gender=_g, engine="sarvam"))
# Sarvam voice for each look when the engine is "Sarvam voices for everyone"
SARVAM_FOR_LOOK = {
    "rahul": "aditya", "aman": "rohan", "priya": "priya", "maa": "neha", "clay": "dev", "flat_uncle": "kabir",
    "flat_aunty": "pooja", "flat_boy": "dev", "flat_man": "amit", "flat_girl": "kavya", "flat_police": "shubh",
    "flat_kid": "dev", "flat_youth_a": "rohan", "flat_youth_b": "manan", "flat_youth_c": "mohit",
    "stick_classic": "sumit", "stick_blue": "varun", "stick_red": "vijay", "stick_girl": "tanya", "stick_kid": "dev",
    "stick_boss": "anand", "flat_dadaji": "ratan", "flat_village_aunty": "roopa", "flat_village_girl": "suhani",
    "flat_farmer": "gokul", "flat_lalit": "aditya", "flat_rahul": "rahul", "flat_deepak": "tarun",
    "flat_cool_dog": "sunny", "flat_brain": "rehan", "flat_dog": "mani", "flat_cat": "kavitha",
    "3d_oldman": "ratan", "3d_youngman": "amit", "3d_boy": "dev", "3d_woman": "shreya", "narrator": "kabir",
    "flat_majdoor_a": "gokul", "flat_majdoor_b": "vijay", "flat_scooter_uncle": "ratan", "flat_biker": "varun",
    "flat_boss": "kabir", "flat_employee": "rohan", "flat_employee_angel": "rohan",
}
SARVAM_FOR_GENDER = {"male": "aditya", "female": "priya"}
# ElevenLabs voices (uses ELEVENLABS_API_KEY): the most expressive, they act out the line's emotion
from .elevenlabs_tts import VOICES as _ELEVEN  # noqa: E402
for _n, (_id, _g, _d) in _ELEVEN.items():
    VOICES.append(dict(id=f"eleven:{_n}", label=f"ElevenLabs, {_g}: {_n.title()} ({_d}, acts the emotion)", lang="any",
                       gender=_g, engine="eleven"))
ELEVEN_FOR_LOOK = {"flat_lalit": "liam", "flat_rahul": "will", "flat_deepak": "chris", "flat_dadaji": "bill",
                   "flat_boss": "adam", "flat_employee": "liam", "flat_employee_angel": "liam", "narrator": "brian",
                   "flat_village_aunty": "lily", "flat_village_girl": "jessica", "flat_aunty": "matilda",
                   "maa": "lily", "priya": "jessica", "3d_woman": "sarah", "flat_girl": "sarah"}
ELEVEN_FOR_GENDER = {"male": "liam", "female": "jessica"}
# Edge voice used when a Gemini voice fails or its daily limit is used up, and the Gemini voice used for an
# Edge voice when the engine is "Gemini for everyone".
EDGE_FOR_GENDER = {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"}
# (pitch Hz, speed %) that suits each look's age and build; the Cast step fills these in when you pick a look
VOICE_TUNE = {"3d_oldman": (-10, -10), "flat_uncle": (-6, -4), "flat_police": (-8, -6), "maa": (-4, -10),
              "flat_aunty": (-2, -4), "flat_boy": (28, 8), "3d_boy": (20, 6), "flat_girl": (12, 4),
              "3d_woman": (6, 2), "flat_man": (0, 2), "3d_youngman": (0, 2), "flat_dog": (8, 10), "flat_cat": (24, 6),
              "flat_kid": (34, 10), "narrator": (-4, -4), "flat_youth_a": (6, 4), "flat_youth_b": (4, 6),
              "flat_youth_c": (8, 4), "flat_lalit": (4, 4), "flat_rahul": (8, 6), "flat_deepak": (0, 0), "flat_dadaji": (-12, -12), "flat_village_aunty": (-2, -4),
              "flat_village_girl": (14, 4), "flat_farmer": (-6, -2), "flat_cool_dog": (6, 8), "stick_kid": (30, 10), "stick_girl": (12, 4), "stick_boss": (-6, -4),
              "clay": (14, 4)}
# Voice effects (tts.VOICE_FX) and the look that gets one by default
VOICE_FX_LABELS = {"": "No effect", "echo": "Echo", "devil": "Devil (deep, with echo)",
                   "devil_whisper": "Devil whisper (inner voice)", "chipmunk": "Chipmunk (high)",
                   "phone": "Phone call", "muffled": "Muffled (from behind a door)"}
VOICE_FX_FOR_LOOK = {"flat_brain": "devil_whisper"}
# Gemini voice for each look when the engine picks Gemini for a character that has a Microsoft voice
GEMINI_FOR_LOOK = {"flat_lalit": "Achird", "flat_rahul": "Puck", "flat_deepak": "Sadachbia", "flat_dadaji": "Algenib", "flat_farmer": "Orus", "flat_village_aunty": "Kore",
                   "flat_village_girl": "Leda", "flat_cool_dog": "Puck", "flat_youth_a": "Puck", "flat_youth_b": "Sadachbia", "flat_youth_c": "Achird", "narrator": "Charon", "flat_kid": "Sadachbia", "flat_brain": "Fenrir", "3d_oldman": "Algenib", "flat_uncle": "Algenib", "flat_police": "Orus", "flat_boy": "Sadachbia",
                   "3d_boy": "Sadachbia", "3d_youngman": "Puck", "flat_man": "Achird", "3d_woman": "Leda",
                   "flat_girl": "Leda", "flat_aunty": "Sulafat", "maa": "Gacrux", "priya": "Kore", "rahul": "Charon",
                   "aman": "Puck"}
GEMINI_FOR_GENDER = {"male": "Charon", "female": "Kore"}
DEFAULT_VOICE = VOICES[0]["id"]


# Optional emotional sounds a line can have. id -> label shown in the dropdown (order = dropdown order).
SOUND_LABELS = {
    "laugh": "Laugh", "giggle": "Giggle", "cry": "Cry", "angry": "Angry growl", "frustrated": "Frustrated groan",
    "sigh": "Sigh", "gasp": "Gasp", "scream": "Scream", "yawn": "Yawn", "hmm": "Hmm (thinking)",
    # sound effects (fx.py): not a voice, so the mouth does not move with them
    "punch": "Punch hit (effect)", "slap": "Slap (effect)", "whoosh": "Whoosh (effect)", "pop": "Pop (effect)",
    "ding": "Ding, idea! (effect)", "boing": "Boing, comedy (effect)", "thud": "Thud, fall (effect)",
    "growl": "Stomach growl (effect)", "ping": "Phone notification (effect)", "doorbell": "Doorbell ting-tong (effect)",
    "chappal": "Chappal smack (effect)", "laugh_track": "Audience laughing (effect)", "boom": "Meme boom (effect)",
    "dun_dun": "Dun dun duuun (effect)", "click": "Light switch click (effect)", "tick": "Clock ticking (effect)",
    "scratch": "Record scratch (effect)",
    "sizzle": "Oil sizzling, chhann (effect)", "fire": "Fire flaring up (effect)", "splash": "Water splash (effect)",
    "footsteps": "Running footsteps (effect)", "clang": "Metal clang, thali (effect)",
    "slip": "Cartoon slip, wheee (effect)", "slide_up": "Slide whistle up (effect)",
    "slide_down": "Slide whistle down, falling (effect)", "zip": "Cartoon zip, fast run (effect)",
    "bonk": "Bonk on the head (effect)", "tweet": "Dizzy birds tweeting (effect)", "crash": "Crash, smash (effect)",
    "glass_break": "Glass breaking (effect)", "crickets": "Crickets, awkward silence (effect)",
    "wah_wah": "Sad trombone, wah wah waaah (effect)", "tiptoe": "Sneaky tiptoe music (effect)",
    "awooga": "Awooga horn, eyes pop (effect)", "spring": "Spring boing, doing (effect)",
    "fight": "Cartoon fight cloud (effect)",
    "alarm": "Alarm clock ringing (effect)", "buzz": "Fly buzzing (effect)", "snore": "Snoring (effect)",
    "boop": "Poke, boop (effect)", "rustle": "Rustling, something moving inside (effect)",
    "knock": "Banging on the door, dham dham (effect)", "door_open": "Door creaking open (effect)",
}
FX_SOUNDS = {"slip", "slide_up", "slide_down", "zip", "bonk", "tweet", "crash", "glass_break", "crickets", "wah_wah",
             "tiptoe", "awooga", "spring", "fight", "alarm", "buzz", "snore", "boop", "rustle",
             "punch", "slap", "whoosh", "pop", "ding", "boing", "thud", "growl", "ping", "doorbell", "chappal",
             "laugh_track", "boom", "dun_dun", "click", "tick", "scratch", "sizzle", "fire", "splash", "footsteps",
             "clang", "knock", "door_open"}
# The emotion that usually goes with each sound (the app suggests it when the line is still "neutral").
SOUND_EMOTIONS = {"laugh": "laughing", "giggle": "happy", "cry": "crying", "angry": "angry", "frustrated": "angry",
                  "sigh": "sad", "gasp": "surprised", "scream": "scared", "yawn": "sleepy", "hmm": "thinking"}
