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
HIDDEN_LOOKS: set[str] = set()   # looks kept out of the Cast menu (still usable by script import and tests)
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
    "flat_kid": ("Flat: Kid, about 10 (striped t-shirt, shorts)", False, dict(
        kind="human", skin=(198, 140, 96), top="tshirt", top_color=(230, 80, 70), bottom="shorts",
        bottom_color=(50, 80, 140), hat=None, hair="short", hair_color=(30, 26, 26), mustache=False,
        female=False, height=0.66, stripes=(250, 236, 220))),
    "flat_brain": ("Flat: My brain (inner voice, little devil)", False, dict(
        kind="brain", color=(244, 150, 172), glow=(255, 110, 140), horns=True, height=1.0)),
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
}

# Camera shot for a line (flat cartoon style). "auto" picks one like a cartoon editor would.
SHOT_LABELS = {"auto": "Camera: automatic", "wide": "Camera: wide (everyone)", "single": "Camera: on the speaker",
               "ots": "Camera: over the shoulder", "close": "Camera: close-up",
               "stove": "Camera: close-up on the stove (kitchen)"}

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
# (pitch Hz, speed %) that suits each look's age and build; the Cast step fills these in when you pick a look
VOICE_TUNE = {"3d_oldman": (-10, -10), "flat_uncle": (-6, -4), "flat_police": (-8, -6), "maa": (-4, -10),
              "flat_aunty": (-2, -4), "flat_boy": (28, 8), "3d_boy": (20, 6), "flat_girl": (12, 4),
              "3d_woman": (6, 2), "flat_man": (0, 2), "3d_youngman": (0, 2), "flat_dog": (8, 10), "flat_cat": (24, 6),
              "flat_kid": (34, 10), "narrator": (-4, -4),
              "clay": (14, 4)}
# Voice effects (tts.VOICE_FX) and the look that gets one by default
VOICE_FX_LABELS = {"": "No effect", "echo": "Echo", "devil": "Devil (deep, with echo)",
                   "devil_whisper": "Devil whisper (inner voice)", "chipmunk": "Chipmunk (high)",
                   "phone": "Phone call"}
VOICE_FX_FOR_LOOK = {"flat_brain": "devil_whisper"}
# Gemini voice for each look when the engine picks Gemini for a character that has a Microsoft voice
GEMINI_FOR_LOOK = {"narrator": "Charon", "flat_kid": "Sadachbia", "flat_brain": "Fenrir", "3d_oldman": "Algenib", "flat_uncle": "Algenib", "flat_police": "Orus", "flat_boy": "Sadachbia",
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
}
FX_SOUNDS = {"punch", "slap", "whoosh", "pop", "ding", "boing", "thud", "growl", "ping", "doorbell", "chappal",
             "laugh_track", "boom", "dun_dun", "click", "tick", "scratch", "sizzle", "fire", "splash", "footsteps",
             "clang"}
# The emotion that usually goes with each sound (the app suggests it when the line is still "neutral").
SOUND_EMOTIONS = {"laugh": "laughing", "giggle": "happy", "cry": "crying", "angry": "angry", "frustrated": "angry",
                  "sigh": "sad", "gasp": "surprised", "scream": "scared", "yawn": "sleepy", "hmm": "thinking"}
