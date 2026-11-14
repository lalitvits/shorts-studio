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
    "sit": "Sit on sofa", "sit_phone": "Sit and use phone", "sit_tea": "Sit and drink tea",
    "sit_read": "Sit and read", "sit_eat": "Sit and eat a snack", "sit_sleep": "Sit and sleep",
}
ACTIONS = list(ACTION_LABELS)

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
_FLAT = {
    "flat_uncle": ("Flat: Uncle (red cap, vest)", False, dict(
        kind="human", skin=(186, 122, 78), top="vest", top_color=(240, 238, 230), bottom="pants",
        bottom_color=(190, 168, 112), hat="cap", hat_color=(214, 60, 45), hair="none", hair_color=(58, 36, 28),
        mustache=True, female=False, height=1.0)),
    "flat_aunty": ("Flat: Aunty (kurta, hair bun)", True, dict(
        kind="human", skin=(204, 142, 98), top="kurta", top_color=(226, 92, 120), accent=(250, 200, 70),
        bottom="dress", bottom_color=(120, 40, 70), hat=None, hair="bun", hair_color=(40, 30, 30),
        mustache=False, female=True, height=0.95, bindi=True)),
    "flat_boy": ("Flat: Boy (blue t-shirt, shorts)", False, dict(
        kind="human", skin=(196, 136, 92), top="tshirt", top_color=(60, 130, 214), bottom="shorts",
        bottom_color=(60, 66, 84), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=0.78)),
    "flat_man": ("Flat: Young man (yellow t-shirt)", False, dict(
        kind="human", skin=(176, 116, 74), top="tshirt", top_color=(240, 196, 60), bottom="pants",
        bottom_color=(52, 70, 110), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=1.0)),
    "flat_girl": ("Flat: Girl (green kurta, long hair)", True, dict(
        kind="human", skin=(206, 150, 106), top="kurta", top_color=(70, 170, 120), accent=(240, 240, 230),
        bottom="dress", bottom_color=(240, 236, 226), hat=None, hair="long", hair_color=(36, 28, 28),
        mustache=False, female=True, height=0.9, bindi=False)),
    "flat_police": ("Flat: Police havaldar (khaki uniform, lathi)", False, dict(
        kind="human", skin=(176, 116, 74), top="uniform", top_color=(196, 168, 110), bottom="pants",
        bottom_color=(196, 168, 110), hat="police_cap", hat_color=(196, 168, 110), band_color=(196, 40, 40),
        hair="none", hair_color=(40, 30, 28), mustache=True, female=False, height=1.0, belly=1.0, holds="lathi",
        shoe=(30, 28, 30))),
    "flat_dog": ("Flat: Dog (brown)", False, dict(kind="dog", color=(146, 94, 58), light=(196, 150, 104), height=1.0)),
    "flat_cat": ("Flat: Cat (grey)", False, dict(kind="cat", color=(150, 150, 160), light=(220, 220, 226), height=0.9)),
}
for _k, (_label, _fem, _spec) in _FLAT.items():
    LOOKS[_k] = dict(label=_label, style="flat", flat=_spec, female=_fem, sprite=False, scale=1.0,
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
for _k, _v in LOOKS.items():
    _v["id"] = _k

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
}

# Camera shot for a line (flat cartoon style). "auto" picks one like a cartoon editor would.
SHOT_LABELS = {"auto": "Camera: automatic", "wide": "Camera: wide (everyone)", "single": "Camera: on the speaker",
               "ots": "Camera: over the shoulder", "close": "Camera: close-up"}

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
# Edge voice used when a Gemini voice fails or its daily limit is used up, and the Gemini voice used for an
# Edge voice when the engine is "Gemini for everyone".
EDGE_FOR_GENDER = {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"}
GEMINI_FOR_GENDER = {"male": "Charon", "female": "Kore"}
DEFAULT_VOICE = VOICES[0]["id"]


# Optional emotional sounds a line can have. id -> label shown in the dropdown (order = dropdown order).
SOUND_LABELS = {
    "laugh": "Laugh", "giggle": "Giggle", "cry": "Cry", "angry": "Angry growl", "frustrated": "Frustrated groan",
    "sigh": "Sigh", "gasp": "Gasp", "scream": "Scream", "yawn": "Yawn", "hmm": "Hmm (thinking)",
    # sound effects (fx.py): not a voice, so the mouth does not move with them
    "punch": "Punch hit (effect)", "slap": "Slap (effect)", "whoosh": "Whoosh (effect)", "pop": "Pop (effect)",
    "ding": "Ding, idea! (effect)", "boing": "Boing, comedy (effect)", "thud": "Thud, fall (effect)",
}
FX_SOUNDS = {"punch", "slap", "whoosh", "pop", "ding", "boing", "thud"}
# The emotion that usually goes with each sound (the app suggests it when the line is still "neutral").
SOUND_EMOTIONS = {"laugh": "laughing", "giggle": "happy", "cry": "crying", "angry": "angry", "frustrated": "angry",
                  "sigh": "sad", "gasp": "surprised", "scream": "scared", "yawn": "sleepy", "hmm": "thinking"}
