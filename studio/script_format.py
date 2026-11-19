"""The Shorts Studio script format: a plain-text screenplay layout that any AI chat app (ChatGPT, Gemini, Claude...)
can fill in, and that the app reads exactly, with no AI.

    build_format(idea)  the instructions + every allowed value + an example, to paste into another AI app
    is_format(text)     does the text use this format?
    parse(text)         the format -> characters, scenes and cards for the app (unknown values are reported)
    export(timeline)    the app's project -> the format (to edit it elsewhere and bring it back)

The layout (one item per line; anything after # on a header line is a comment):

    ### SHORTS STUDIO SCRIPT v1
    title: ...            hook: ...            language: hi            music: happy

    ## CHARACTERS
    - id: vikram | name: विक्रम | look: flat_man | gender: male | height: tall | build: fat | outfit: blue | voice: male

    ## SCENE | background: flat_office | lighting: day | music: keep | seconds: 7
    cast: vikram, dost
    vikram (happy, use_phone, prop: phone, camera: close, sound: pop): सेल्फी तो बनती है!
    dost (shocked, grab_hand, meanwhile: vikram surprised): अरे पागल हो गया है क्या?
    vikram (silent: 2, walk_out)

    ## CARD | text: 20 मिनट बाद... | style: dark | sound: tick | seconds: 2
"""
from __future__ import annotations

import re

from .catalog import (ACTION_LABELS, BUILDS, EMOTIONS, HEIGHTS, LOOKS, OUTFIT_COLORS, PROP_LABELS, SHOT_LABELS,
                      SOUND_LABELS, VOICE_FX_LABELS, VOICES, EDGE_FOR_GENDER, DEFAULT_VOICE, FLAT_BACKGROUNDS)

HEADER = "### SHORTS STUDIO SCRIPT v1"
LIGHTING = {"day": "normal", "dark": "night, lights off", "phone": "dark, faces lit by a phone screen"}
CARD_STYLES = {"dark": "dark with a ticking clock", "black": "black screen", "bright": "bright comic burst"}

# ------------------------------------------------------------------ words other AI apps tend to use
SYN = {
    "camera": {"close_up": "close", "closeup": "close", "extreme_close_up": "close", "face": "close",
               "medium": "single", "mid": "single", "mid_shot": "single", "medium_shot": "single", "single_shot": "single",
               "over_the_shoulder": "ots", "over_shoulder": "ots", "ots_shot": "ots", "wide_shot": "wide",
               "long_shot": "wide", "establishing": "wide", "full": "wide", "full_shot": "wide",
               "stove_close_up": "stove", "kitchen_close_up": "stove", "automatic": "auto"},
    "emotion": {"shock": "shocked", "fear": "scared", "afraid": "scared", "panic": "scared", "nervous": "worried",
                "tense": "worried", "calm": "neutral", "serious": "neutral", "normal": "neutral", "love": "in_love",
                "romantic": "in_love", "tired": "sleepy", "relief": "relieved", "cry": "crying", "sad_crying": "crying",
                "laugh": "laughing", "surprise": "surprised", "excitement": "excited", "anger": "angry",
                "furious": "angry", "confident": "proud", "smile": "happy", "smiling": "happy", "joy": "happy",
                "disgust": "disgusted", "think": "thinking", "boredom": "bored", "shy": "embarrassed"},
    "action": {"enter": "walk_in", "enters": "walk_in", "comes_in": "walk_in", "exit": "walk_out", "exits": "walk_out",
               "leave": "walk_out", "leaves": "walk_out", "runs_in": "run_in", "runs_away": "run_out",
               "selfie": "use_phone", "look_at_phone": "use_phone", "typing": "use_phone", "scroll": "use_phone",
               "call": "phone_call", "on_call": "phone_call", "drink": "drink_tea", "drinking": "drink_tea",
               "stop_hand": "grab_hand", "hold_hand": "grab_hand", "sit_down": "sit", "sitting": "sit",
               "ride": "ride_cycle", "cycling": "ride_cycle", "speak": "talk", "say": "talk", "speaking": "talk",
               "still": "idle", "stand": "idle", "standing": "idle", "pointing": "point", "waving": "wave",
               "crying": "cry", "jumping": "jump", "dancing": "dance", "clapping": "clap", "thinking": "think",
               "shrugging": "shrug", "explaining": "explain", "eat_snack": "eat", "eating": "eat",
               "read": "read_book", "reading": "read_book", "look_at_camera": "look_camera"},
    "prop": {"mobile": "phone", "cellphone": "phone", "smartphone": "phone", "mobile_phone": "phone",
             "bicycle": "cycle", "bike": "cycle", "water_glass": "glass", "glass_of_water": "glass",
             "water_bottle": "bottle", "tea": "cup", "tea_cup": "cup", "plate": "thali", "stick": "lathi",
             "slipper": "chappal", "luggage": "suitcase", "trolley": "suitcase", "trolley_bag": "suitcase",
             "backpack": "bag", "handbag": "bag", "purse": "bag", "flower": "flowers", "bouquet": "flowers",
             "computer": "laptop", "paper": "newspaper", "food_parcel": "parcel", "parcel_box": "parcel",
             "nothing": "none", "no": "none", "put_away": "none",
             # food, fruit and vegetables (English plurals and Hindi names too)
             "samosas": "samosa", "समोसा": "samosa", "jalebis": "jalebi", "जलेबी": "jalebi", "vadapav": "vada_pav",
             "वड़ा_पाव": "vada_pav", "वडा_पाव": "vada_pav", "chai": "cutting_chai", "chai_glass": "cutting_chai",
             "cutting": "cutting_chai", "चाय": "cutting_chai", "कटिंग_चाय": "cutting_chai", "kulhad_chai": "kulhad",
             "कुल्हड़": "kulhad", "clay_cup": "kulhad", "samosa_plate": "plate_samosa", "plate_of_samosas": "plate_samosa",
             "bananas": "banana", "केला": "banana", "apples": "apple", "सेब": "apple", "mangoes": "mango", "आम": "mango",
             "oranges": "orange", "संतरा": "orange", "grape": "grapes", "अंगूर": "grapes", "तरबूज": "watermelon",
             "watermelon_slice": "watermelon", "tomatoes": "tomato", "टमाटर": "tomato", "onions": "onion",
             "प्याज": "onion", "potatoes": "potato", "आलू": "potato", "carrots": "carrot", "गाजर": "carrot",
             "eggplant": "brinjal", "aubergine": "brinjal", "baingan": "brinjal", "बैंगन": "brinjal", "chillies": "chilli",
             "chilies": "chilli", "chili": "chilli", "green_chilli": "chilli", "मिर्च": "chilli", "हरी_मिर्च": "chilli",
             "पत्तागोभी": "cabbage", "kheera": "cucumber", "khira": "cucumber", "kakdi": "cucumber",
             "cucumbers": "cucumber", "खीरा": "cucumber", "ककड़ी": "cucumber", "nimbu": "lemon", "lemons": "lemon",
             "lime": "lemon", "नींबू": "lemon", "gobhi": "cauliflower", "phool_gobhi": "cauliflower",
             "फूलगोभी": "cauliflower", "गोभी": "cauliflower", "okra": "bhindi", "lady_finger": "bhindi",
             "ladyfinger": "bhindi", "भिंडी": "bhindi", "lahsun": "garlic", "लहसुन": "garlic", "matar": "peas",
             "pea": "peas", "pea_pod": "peas", "मटर": "peas", "corn": "bhutta", "corn_cob": "bhutta",
             "roasted_corn": "bhutta", "भुट्टा": "bhutta", "nariyal": "coconut", "नारियल": "coconut", "basket": "veg_basket", "vegetable_basket": "veg_basket", "टोकरी": "veg_basket",
             "sabzi": "sabzi_bag", "vegetables": "sabzi_bag", "thaila": "sabzi_bag", "थैला": "sabzi_bag",
             "सब्ज़ी": "sabzi_bag", "सब्जी": "sabzi_bag", "मोबाइल": "phone", "फोन": "phone", "फ़ोन": "phone",
             "साइकिल": "cycle", "पानी": "glass", "गिलास": "glass", "बोतल": "bottle"},
    "height": {"small": "short", "kid": "child", "very_short": "child", "big": "tall", "giant": "very_tall",
               "average": "normal", "medium": "normal"},
    "build": {"slim": "thin", "skinny": "thin", "lean": "thin", "chubby": "fat", "heavy": "fat", "healthy": "fat",
              "obese": "very_fat", "medium": "normal", "average": "normal", "fit": "normal"},
    "background": {"chai_ki_tapri": "flat_chai_tapri", "chai_tapri": "flat_chai_tapri", "tapri": "flat_chai_tapri",
                   "tea_stall": "flat_chai_tapri", "tea_shop": "flat_chai_tapri", "चाय_की_टपरी": "flat_chai_tapri",
                   "sabzi_mandi": "flat_sabzi_mandi", "mandi": "flat_sabzi_mandi", "vegetable_market": "flat_sabzi_mandi",
                   "सब्ज़ी_मंडी": "flat_sabzi_mandi", "सब्जी_मंडी": "flat_sabzi_mandi", "fruit_market": "flat_market",
                   "market": "flat_market", "bazaar": "flat_market", "बाज़ार": "flat_market", "airport": "flat_airport",
                   "एयरपोर्ट": "flat_airport", "departure_hall": "flat_airport", "bus_stop": "flat_bus_stop",
                   "bus_stand": "flat_bus_stop", "बस_स्टॉप": "flat_bus_stop", "street": "flat_city_street",
                   "road": "flat_city_street", "kitchen": "flat_kitchen", "रसोई": "flat_kitchen", "bedroom": "flat_bedroom",
                   "office": "flat_office", "school": "flat_school", "village": "flat_village", "गाँव": "flat_village",
                   "park": "flat_park", "heaven": "flat_swarg", "hell": "flat_nark"},
    "look": {"man": "flat_man", "young_man": "flat_man", "woman": "flat_aunty", "lady": "flat_aunty",
             "aunty": "flat_aunty", "mother": "flat_aunty", "mom": "flat_aunty", "mummy": "flat_aunty",
             "wife": "flat_girl", "girl": "flat_girl", "young_woman": "flat_girl", "boy": "flat_boy",
             "kid": "flat_kid", "child": "flat_kid", "son": "flat_kid", "college_boy": "flat_youth_a",
             "college_student": "flat_youth_a", "youth": "flat_youth_a", "young_boy": "flat_youth_a",
             "hoodie_boy": "flat_youth_b", "gen_z": "flat_youth_c", "student": "flat_youth_c", "uncle": "flat_uncle",
             "old_man": "flat_uncle", "father": "flat_uncle", "police": "flat_police", "constable": "flat_police",
             "brain": "flat_brain", "dog": "flat_dog", "cat": "flat_cat", "vo": "narrator", "voice_over": "narrator",
             "voiceover": "narrator"},
}
NARRATOR_WORDS = {"narrator", "vo", "voiceover", "voice_over", "वॉयसओवर", "वॉइसओवर", "सूत्रधार"}


def _key(v) -> str:
    return re.sub(r"[\s\-]+", "_", str(v or "").strip().strip('"').strip("'").lower())


def _pick(kind: str, v, allowed) -> str | None:
    k = _key(v)
    if k in allowed:
        return k
    k2 = SYN.get(kind, {}).get(k)
    return k2 if k2 in allowed else None


def _visible_looks() -> dict:
    return {k: v for k, v in LOOKS.items() if not v.get("hidden")}


def _backgrounds() -> list:
    from .backgrounds import list_backgrounds
    return list_backgrounds()


def _music() -> dict:
    from .fx import MUSIC_LABELS
    return MUSIC_LABELS


def _stickers():
    from .overlays import STICKER_KINDS
    return STICKER_KINDS


def _kitchen():
    from .kitchen import EXPLAINERS, KADHAI_STATES
    return KADHAI_STATES, EXPLAINERS


# ------------------------------------------------------------------ the format for other AI apps
def build_format(idea: str = "", language: str = "hi", seconds: int = 45) -> str:
    """Instructions, every allowed value and an example: paste it into any AI chat app with your idea."""
    looks = "\n".join(f"  {k}: {v['label']}" for k, v in _visible_looks().items())
    bgs = "\n".join(f"  {b['id']}: {b['label']}" for b in _backgrounds())
    acts = "\n".join(f"  {k}: {v}" for k, v in ACTION_LABELS.items())
    props = "\n".join(f"  {k}: {v}" for k, v in PROP_LABELS.items() if k)
    cams = "\n".join(f"  {k}: {v}" for k, v in SHOT_LABELS.items())
    sounds = ", ".join(SOUND_LABELS)
    music = ", ".join(_music())
    kadhai, explainers = _kitchen()
    gem = ", ".join(v["id"].split(":", 1)[1] for v in VOICES if v["id"].startswith("gemini:"))
    lang = {"hi": "Hindi in Devanagari script", "hinglish": "Hinglish in Roman letters", "en": "simple English"}.get(
        language, language)
    idea_line = idea.strip() or "<WRITE YOUR STORY IDEA HERE>"
    return f"""You are writing a script for "Shorts Studio", an app that turns it into a cartoon YouTube Short / Reel.
Write the script for this idea: {idea_line}
Length: about {seconds} seconds. Dialogue language: {lang}. Keep each spoken line short (under 14 words).

Reply with ONLY the script in the exact format below (start with the {HEADER} line, no other text).
Use only the allowed values listed further down; English ids for everything except the names and the dialogue.
Write plain text: no Markdown (no **bold**, no code blocks, no numbered or bulleted dialogue lines).

=== FORMAT ===
{HEADER}
title: <short title>
hook: <a punchy opening line, max 6 words, shown big in the first 2 seconds>
language: {language}
music: <music id for the start>

## CHARACTERS
- id: <short English id> | name: <name as shown> | look: <look id> | gender: male/female | height: <height> | build: <build> | outfit: <colour> | voice: male/female/<Gemini voice name> | voice_effect: <effect>
(one "- id:" line per character; add a narrator with "look: narrator" for a voice-over that is never on screen)

## SCENE | background: <background id> | lighting: <lighting> | music: keep/<music id>/none | seconds: <minimum length>
cast: <ids of the characters on screen in this scene, comma separated>
<speaker id> (<emotion>, <action>, prop: <prop>, camera: <camera>, sound: <sound>, ...): <dialogue>
<speaker id> (<emotion>, <action>, silent: <seconds>)          <- a moment with no words (just acting)

## CARD | text: <text on screen, e.g. 20 मिनट बाद...> | style: dark/black/bright | sound: <sound> | seconds: <seconds>

=== WHAT A LINE CAN HAVE (inside the brackets, separated by commas; all optional) ===
  <emotion>                 how they feel (see EMOTIONS)
  <action>                  what they do while speaking: gestures, movement, activity (see ACTIONS)
  prop: <prop>              something they hold or have with them from this line on; "prop: none" puts it away
  camera: <camera>          the camera shot for this line
  sound: <sound>            a sound effect at the start of the line
  meanwhile: <id> <emotion> <action>   someone ELSE acts while this line is spoken (use it with the narrator)
  silent: <seconds>         no words: an acting moment of this many seconds
  popup: "<text>"           a phone notification shown on screen
  sticker: <sticker>        a sticker pops up next to the speaker
  overlay: "<line 1> | <line 2>"   big bold text on screen until the scene ends (line 2 is smaller)
  lights: on/off            the room light switches on or off
  kadhai: <state>           kitchen only: the kadhai on the stove
  cutaway: <cutaway>        the picture cuts to an explainer animation while the line is spoken
Movement is an action: walk_in / walk_out / run_in / run_out / ride_in / ride_out (on a cycle) / appear / step_back.

=== ALLOWED VALUES ===
LOOKS (character drawings):
{looks}
HEIGHT: {", ".join(k for k in HEIGHTS if k)} (or a number like 1.1 = 10% taller than the look)
BUILD: {", ".join(k for k in BUILDS if k)}
OUTFIT colours: {", ".join(k for k in OUTFIT_COLORS if k)}
VOICES: male, female, or a Gemini voice: {gem}
VOICE EFFECTS: {", ".join(k or "none" for k in VOICE_FX_LABELS)}
BACKGROUNDS:
{bgs}
LIGHTING: {", ".join(f"{k} ({v})" for k, v in LIGHTING.items())}
MUSIC: {music}
EMOTIONS: {", ".join(EMOTIONS)}
ACTIONS:
{acts}
PROPS:
{props}
CAMERA:
{cams}
SOUNDS: {sounds}
STICKERS: {", ".join(_stickers())}
KADHAI states (kitchen): {", ".join(kadhai)}
CUTAWAYS: {", ".join(explainers)}

=== EXAMPLE ===
{HEADER}
title: सेल्फी का खतरा
hook: ये पोस्ट मत डालना!
language: hi
music: happy

## CHARACTERS
- id: vikram | name: विक्रम | look: flat_man | gender: male | height: tall | build: normal | outfit: blue | voice: male
- id: dost | name: दोस्त | look: flat_uncle | gender: male | height: normal | build: fat | voice: male
- id: chor | name: चोर | look: flat_man | gender: male | build: thin | outfit: black | voice: male
- id: narrator | name: वॉइसओवर | look: narrator | voice: male

## SCENE | background: flat_city_street | lighting: day | seconds: 7
cast: vikram, dost
vikram (happy, ride_in, camera: wide): गोवा जा रहे हैं, सेल्फी तो बनती है!
vikram (excited, use_phone, camera: close, popup: "5 दिनों के लिए गोवा! घर खाली है"): बस पोस्ट कर देता हूँ।
dost (shocked, grab_hand, sound: whoosh, meanwhile: vikram surprised idle): अरे रुक! ये पोस्ट मत डाल!

## SCENE | background: flat_bedroom | lighting: phone | music: suspense
cast: chor
chor (happy, use_phone, silent: 2, sticker: money)

## SCENE | background: flat_city_street | music: calm
cast: vikram, dost
dost (worried, explain, prop: bottle): चोर सोशल मीडिया पर ही नज़र रखते हैं।
narrator (meanwhile: vikram relieved look_camera, overlay: "ट्रिप की फोटो, घर लौटकर पोस्ट करें | Post trip photos after you return"): समझदार बनें, सुरक्षित रहें।
"""


def is_format(text: str) -> bool:
    return "SHORTS STUDIO SCRIPT" in (text or "")[:400].upper()


# ------------------------------------------------------------------ reading the format
def _split_top(s: str, sep: str) -> list:
    """Split on sep, but not inside quotes or brackets."""
    out, cur, q, depth = [], "", None, 0
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in "\"“”":
            q = '"' if ch == '"' else "”"
            cur += ch
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _kv(part: str):
    m = re.match(r"^\s*([A-Za-z_][\w\- ]*?)\s*[:=]\s*(.*)$", part, re.S)
    if not m:
        return None, part.strip()
    return _key(m.group(1)), m.group(2).strip().strip('"“”').strip()


def _clean(raw: str) -> str:
    """One line without the Markdown that AI chat apps like to add: **bold**, *italics*, `code`, ``` fences,
    > quotes and numbered lists ("1. ..."). Bullets for characters ("- " / "* " / "• ") become "- "."""
    line = (raw or "").strip()
    if line.startswith("```") or line.startswith("~~~") or set(line) <= set("-=_*~ "):   # fences, --- rules
        return ""
    line = re.sub(r"^>+\s*", "", line)
    bullet = bool(re.match(r"^([-*•])\s+", line))
    if bullet:
        line = re.sub(r"^([-*•])\s+", "", line)
    line = re.sub(r"^\d{1,2}[.)]\s+", "", line)
    line = line.replace("**", "").replace("__", "").replace("`", "")
    line = re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "", line)   # *italic* -> italic
    line = line.strip()
    return ("- " + line) if bullet and line else line


def _is_header(line: str) -> bool:
    """## CHARACTERS / ## SCENE | ... / ## CARD | ... (any number of #, or none: "SCENE 2 | background: ...",
    "Characters:")."""
    if line.startswith("#"):
        return True
    head = _key(line.split("|", 1)[0].rstrip(":"))
    if head in ("characters", "character", "cast_list"):
        return True
    return bool(re.match(r"^(scene|card)(_\d+)?(_|$)", head)) and ("|" in line or re.fullmatch(r"(scene|card)(_\d+)?", head))


def _fields(rest: str) -> dict:
    out = {}
    for part in _split_top(rest, "|"):
        k, v = _kv(part)
        if k:
            out[k] = v
    return out


def _num(v, top=60.0):
    m = re.search(r"\d+(\.\d+)?", str(v or ""))
    return min(top, float(m.group(0))) if m else 0.0


def _bg(v, warn) -> str:
    bgs = _backgrounds()
    ids = [b["id"] for b in bgs]
    k = _key(v)
    if not k:
        return "flat_city_street"
    for cand in (k, "flat_" + k):
        if cand in ids:
            return cand
    mine = [b for b in bgs if b.get("mine")]               # your own picture with that name wins
    for b in mine:
        if k == _key(b["id"]):
            return b["id"]
    if SYN["background"].get(k) in ids:                    # "chai ki tapri" -> the flat chai tapri
        return SYN["background"][k]
    for b in bgs:                                          # "airport" -> "Your picture: Airport"
        if k in _key(b["id"]) or k in _key(b["label"]):
            return b["id"]
    warn.append(f'Background "{v}" is not in the app: the city street is used. Add a picture named {k}.jpg to the '
                'my_backgrounds folder to use your own.')
    return "flat_city_street"


def parse(text: str) -> dict:
    """The format -> {title, hook, music, language, characters, scenes, warnings}."""
    from .catalog import NARRATOR_LOOKS
    warn: list = []
    head: dict = {}
    chars: list = []
    scenes: list = []
    cur = None
    section = None
    acts_allowed, emo_allowed = set(ACTION_LABELS), set(EMOTIONS)
    props_allowed = set(PROP_LABELS) - {""} | {"none"}
    cams, sounds = set(SHOT_LABELS), set(SOUND_LABELS)
    stickers = set(_stickers())
    kadhai, explainers = _kitchen()
    music = set(_music())
    looks = _visible_looks()

    def char_by(word: str):
        w = str(word or "").strip().strip(":").strip()
        k = _key(w)
        for c in chars:
            if c["id"] == k or _key(c["name"]) == k or c["name"] == w:
                return c
        if k in NARRATOR_WORDS or w in NARRATOR_WORDS:
            return next((c for c in chars if c["look"] in NARRATOR_LOOKS), None) or add_char({"id": "narrator", "name": w or "Narrator", "look": "narrator"})
        return None

    def add_char(f: dict) -> dict:
        cid = re.sub(r"[^a-z0-9_]", "", _key(f.get("id") or f.get("name") or "")) or f"c{len(chars) + 1}"
        while any(c["id"] == cid for c in chars):
            cid += "x"
        look = f.get("look", "")
        lk = _key(look)
        look = lk if lk in looks else SYN["look"].get(lk)
        gender = "female" if _key(f.get("gender", "")) in ("female", "f", "woman", "girl", "महिला", "स्त्री") else "male"
        if not look:
            if f.get("look"):
                warn.append(f'Look "{f.get("look")}" for {f.get("name") or cid} is not in the app: a flat look is used.')
            look = "flat_aunty" if gender == "female" else "flat_man"
        if LOOKS[look].get("female"):
            gender = "female"
        voice = str(f.get("voice") or "").strip()
        vk = _key(voice)
        gem = {v["id"].split(":", 1)[1].lower(): v["id"] for v in VOICES if v["id"].startswith("gemini:")}
        if vk in gem:
            voice = gem[vk]
        elif voice.lower().startswith("gemini:") and voice.split(":", 1)[1].lower() in gem:
            voice = gem[voice.split(":", 1)[1].lower()]
        elif any(v["id"] == voice for v in VOICES):
            pass
        else:
            voice = EDGE_FOR_GENDER["female" if (vk == "female" or (vk != "male" and gender == "female")) else "male"] \
                or DEFAULT_VOICE
        fx = _key(f.get("voice_effect") or f.get("effect") or "")
        fx = "" if fx in ("", "none", "no") else fx
        if fx and fx not in VOICE_FX_LABELS:
            warn.append(f'Voice effect "{fx}" is not in the app (allowed: {", ".join(k for k in VOICE_FX_LABELS if k)}).')
            fx = ""
        h = f.get("height", "")
        hk = _pick("height", h, set(HEIGHTS) - {""})
        if hk is None and h:
            hk = _num(h, 1.3) or ""
            if not hk:
                warn.append(f'Height "{h}" for {f.get("name") or cid} is not known (use {", ".join(k for k in HEIGHTS if k)}).')
        b = f.get("build", "")
        bk = _pick("build", b, set(BUILDS) - {""})
        if bk is None and b:
            bk = _num(b, 1.7) or ""
            if not bk:
                warn.append(f'Build "{b}" for {f.get("name") or cid} is not known (use {", ".join(k for k in BUILDS if k)}).')
        o = _key(f.get("outfit") or f.get("color") or f.get("colour") or "")
        if o and o not in OUTFIT_COLORS:
            warn.append(f'Outfit colour "{o}" is not in the app (allowed: {", ".join(k for k in OUTFIT_COLORS if k)}).')
            o = ""
        c = dict(id=cid, name=(f.get("name") or cid)[:30], look=look, voice=voice, voice_fx=fx,
                 height=hk or "", build=bk or "", outfit=o)
        chars.append(c)
        return c

    def add_line(raw: str):
        nonlocal cur
        if cur is None or "card" in cur:
            cur = dict(background="flat_city_street", lighting="day", music="", seconds=0.0, cast=[], lines=[])
            scenes.append(cur)
        # speaker, optional (attributes), then ":" and the dialogue
        m = re.match(r"^\s*([^():]+?)\s*(\((.*)\))?\s*(:\s*(.*))?$", raw, re.S)
        if not m:
            warn.append(f"Could not read this line: {raw[:60]}")
            return
        who, attrs, text = m.group(1), m.group(3) or "", (m.group(5) or "").strip()
        c = char_by(who)
        if c is None:
            warn.append(f'"{who.strip()}" speaks but is not in ## CHARACTERS: added with a flat look.')
            c = add_char({"id": who, "name": who.strip()})
        text = text.strip().strip('"“”').strip()
        ln = dict(speaker=c["id"], text=text, emotion="neutral", action="talk", sound="", popup="", sticker="",
                  lights="", shot="auto", hold=0.0, actor="", actor_action="idle", actor_emotion="neutral",
                  kadhai="", broll="", overlay="", prop="")
        for part in _split_top(attrs, ","):
            k, v = _kv(part)
            if k is None:                                  # a bare word: emotion, action, prop, camera or sound
                w = v
                if re.fullmatch(r"\d+(\.\d+)?\s*s?(ec(ond)?s?)?", _key(w)):
                    ln["hold"] = _num(w, 20)
                elif _key(w) in ("silent", "no_words", "pause"):
                    ln["hold"] = ln["hold"] or 1.5
                elif _pick("emotion", w, emo_allowed):
                    ln["emotion"] = _pick("emotion", w, emo_allowed)
                elif _pick("action", w, acts_allowed):
                    ln["action"] = _pick("action", w, acts_allowed)
                elif _pick("prop", w, props_allowed):
                    ln["prop"] = _pick("prop", w, props_allowed)
                elif _pick("camera", w, cams):
                    ln["shot"] = _pick("camera", w, cams)
                elif _key(w) in sounds:
                    ln["sound"] = _key(w)
                else:
                    warn.append(f'Unknown word "{w}" in a line of {c["name"]}: ignored.')
                continue
            if k in ("emotion", "feeling", "mood"):
                ln["emotion"] = _pick("emotion", v, emo_allowed) or _bad(warn, "emotion", v, "neutral")
            elif k in ("action", "movement", "gesture", "activity"):
                ln["action"] = _pick("action", v, acts_allowed) or _bad(warn, "action", v, "talk")
            elif k in ("prop", "holds", "holding", "object"):
                ln["prop"] = _pick("prop", v, props_allowed) or _bad(warn, "prop", v, "")
            elif k in ("camera", "shot", "angle", "camera_angle"):
                ln["shot"] = _pick("camera", v, cams) or _bad(warn, "camera", v, "auto")
            elif k in ("sound", "sfx", "effect"):
                ln["sound"] = _key(v) if _key(v) in sounds else _bad(warn, "sound", v, "")
            elif k in ("silent", "seconds", "hold", "duration"):
                ln["hold"] = _num(v, 20)
            elif k in ("popup", "notification"):
                ln["popup"] = v[:90]
            elif k == "sticker":
                ln["sticker"] = _key(v) if _key(v) in stickers else _bad(warn, "sticker", v, "")
            elif k in ("overlay", "text", "on_screen_text", "screen_text"):
                ln["overlay"] = v[:120]
            elif k in ("lights", "light"):
                ln["lights"] = _key(v) if _key(v) in ("on", "off") else ""
            elif k == "kadhai":
                ln["kadhai"] = _key(v) if _key(v) in kadhai else _bad(warn, "kadhai state", v, "")
            elif k in ("cutaway", "broll", "b_roll"):
                ln["broll"] = _key(v) if _key(v) in explainers else _bad(warn, "cutaway", v, "")
            elif k in ("meanwhile", "actor", "also"):
                words = v.replace(",", " ").split()
                other = None
                for i in range(len(words), 0, -1):          # the name may be several words
                    other = char_by(" ".join(words[:i]))
                    if other:
                        words = words[i:]
                        break
                if not other:
                    warn.append(f'"meanwhile: {v}": no character with that name.')
                    continue
                ln["actor"] = other["id"]
                for w in words:
                    if _pick("emotion", w, emo_allowed):
                        ln["actor_emotion"] = _pick("emotion", w, emo_allowed)
                    elif _pick("action", w, acts_allowed):
                        ln["actor_action"] = _pick("action", w, acts_allowed)
                    else:
                        warn.append(f'"meanwhile: {v}": "{w}" is not an emotion or action.')
            else:
                warn.append(f'Unknown setting "{k}" in a line of {c["name"]}: ignored.')
        if not ln["text"] and not ln["sound"] and not ln["hold"]:
            ln["hold"] = 1.5                                # acting with no words still gets a moment
        cur["lines"].append(ln)

    for raw in (text or "").splitlines():
        line = _clean(raw)
        if not line or "SHORTS STUDIO SCRIPT" in line.upper():
            continue
        low = line.lower()
        if _is_header(line):
            body = line.lstrip("#").strip()
            name, _, rest = body.partition("|")
            name = _key(name)
            if name.startswith("character"):
                section = "chars"
                continue
            if name.startswith("card"):
                f = _fields(rest)
                style = _key(f.get("style", "dark"))
                cur = dict(card=f.get("text", "")[:80], card_style=style if style in CARD_STYLES else "dark",
                           card_sound=_key(f.get("sound")) if _key(f.get("sound")) in sounds else "",
                           card_seconds=_num(f.get("seconds"), 8) or None, cast=[], lines=[])
                if f.get("music"):
                    mk = _key(f["music"])
                    cur["music"] = mk if mk in music or mk == "none" else ""
                scenes.append(cur)
                section = "card"
                continue
            if name.startswith("scene"):
                f = _fields(rest)
                light = _key(f.get("lighting", "day"))
                mk = _key(f.get("music", ""))
                cur = dict(background=_bg(f.get("background", ""), warn),
                           lighting=light if light in LIGHTING else "day",
                           music=mk if mk in music or mk == "none" else "", seconds=_num(f.get("seconds"), 60),
                           cast=[], lines=[])
                if mk and mk not in music and mk not in ("keep", "none", "same"):
                    warn.append(f'Music "{mk}" is not in the app (allowed: {", ".join(sorted(music))}).')
                scenes.append(cur)
                section = "scene"
                continue
            warn.append(f"Unknown section: {line[:50]}")
            continue
        if section == "chars" and (line.startswith(("-", "*", "•")) or re.match(r"^id\s*[:=]", low)):
            add_char(_fields(line.lstrip("-*• ")))
            continue
        if section is None or (section == "chars" and not line.startswith(("-", "*"))):
            k, v = _kv(line)
            if k in ("title", "hook", "language", "music", "voices"):
                head[k] = v
                continue
            if section == "chars":
                section = "scene"
            else:
                continue
        if section != "chars":                     # a dialogue line written as a list item
            line = re.sub(r"^[-*•]\s+", "", line)
            low = line.lower()
        if low.startswith("cast:") and cur is not None and "card" not in cur:
            for w in _split_top(line.split(":", 1)[1], ","):
                c = char_by(w) or add_char({"id": w, "name": w})
                if c["id"] not in cur["cast"]:
                    cur["cast"].append(c["id"])
            continue
        add_line(line)

    narr = {c["id"] for c in chars if c["look"] in NARRATOR_LOOKS}
    if chars and len(narr) == len(chars):
        warn.append("Only a narrator was found: add at least one character who is on screen.")
    for sc in scenes:
        if "card" in sc:
            continue
        cast = [x for x in sc["cast"] if x not in narr]
        for ln in sc["lines"]:
            for who in (ln["speaker"], ln["actor"]):
                if who and who not in narr and who not in cast:
                    cast.append(who)
        if not cast and chars:
            cast = [next((c["id"] for c in chars if c["id"] not in narr), chars[0]["id"])]
        sc["cast"] = cast
    scenes = [sc for sc in scenes if "card" in sc or sc["lines"] or sc["cast"]]
    if not any(sc.get("lines") for sc in scenes):
        warn.append("No lines were found. Each line looks like: vikram (happy, wave): नमस्ते!")
    m = _key(head.get("music", ""))
    lang = _key(head.get("language", "hi"))
    return dict(title=head.get("title", "")[:60], hook=head.get("hook", "")[:60], music=m if m in music else "",
                language=lang if lang in ("hi", "hinglish", "en") else "hi", characters=chars, scenes=scenes,
                warnings=warn[:40], exact=True)


def _bad(warn, what, v, default):
    if str(v or "").strip():
        warn.append(f'{what.capitalize()} "{v}" is not in the app: ignored.')
    return default


# ------------------------------------------------------------------ the app's project -> the format
def export(tl: dict) -> str:
    """Write a project (the app's timeline) in the script format."""
    def q(v):
        return '"' + str(v).replace('"', "'") + '"'
    out = [HEADER, f"title: {tl.get('title', '')}", f"hook: {tl.get('hook', '')}",
           f"language: {tl.get('language', 'hi')}",
           f"music: {(tl.get('audio') or {}).get('musicBuiltin') or (tl.get('audio') or {}).get('music_builtin') or ''}",
           "", "## CHARACTERS"]
    names = {}
    for c in tl.get("characters", []):
        names[c.get("id")] = c.get("id")
        parts = [f"id: {c.get('id')}", f"name: {c.get('name', '')}", f"look: {c.get('look', '')}"]
        for k in ("height", "build", "outfit"):
            if c.get(k):
                parts.append(f"{k}: {c[k]}")
        v = c.get("voice", "")
        parts.append("voice: " + (v.split(":", 1)[1] if v.startswith("gemini:") else v))
        if c.get("voice_fx"):
            parts.append(f"voice_effect: {c['voice_fx']}")
        out.append("- " + " | ".join(parts))
    for sc in tl.get("scenes", []):
        out.append("")
        if sc.get("card") is not None:
            f = [f"text: {sc.get('card', '')}", f"style: {sc.get('card_style') or 'dark'}"]
            if sc.get("card_sound"):
                f.append(f"sound: {sc['card_sound']}")
            if sc.get("card_seconds"):
                f.append(f"seconds: {sc['card_seconds']}")
            out.append("## CARD | " + " | ".join(f))
            continue
        f = [f"background: {sc.get('background', '')}", f"lighting: {sc.get('lighting') or 'day'}"]
        if sc.get("music"):
            f.append(f"music: {sc['music']}")
        if sc.get("seconds"):
            f.append(f"seconds: {sc['seconds']}")
        out.append("## SCENE | " + " | ".join(f))
        out.append("cast: " + ", ".join(sc.get("cast", [])))
        for ln in sc.get("lines", []):
            a = [ln.get("emotion") or "neutral", ln.get("action") or "talk"]
            if ln.get("prop"):
                a.append(f"prop: {ln['prop']}")
            if ln.get("shot") and ln["shot"] != "auto":
                a.append(f"camera: {ln['shot']}")
            if ln.get("sound"):
                a.append(f"sound: {ln['sound']}")
            if ln.get("actor"):
                a.append(f"meanwhile: {ln['actor']} {ln.get('actor_emotion') or 'neutral'} {ln.get('actor_action') or 'idle'}")
            if ln.get("hold"):
                a.append(f"silent: {ln['hold']}" if not ln.get("text") else f"seconds: {ln['hold']}")
            for k, name in (("popup", "popup"), ("overlay", "overlay")):
                if ln.get(k):
                    a.append(f"{name}: {q(ln[k])}")
            for k, name in (("sticker", "sticker"), ("lights", "lights"), ("kadhai", "kadhai"), ("broll", "cutaway")):
                if ln.get(k):
                    a.append(f"{name}: {ln[k]}")
            text = (ln.get("text") or "").strip()
            out.append(f"{ln.get('speaker')} ({', '.join(a)})" + (f": {text}" if text else ""))
    return "\n".join(out) + "\n"
