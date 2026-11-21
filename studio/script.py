"""Turn a short scenario into scenes with dialogue.

Providers
  gemini  Google's Gemini API. Set GEMINI_API_KEY (free keys exist, with daily limits).
          Model names change often: set GEMINI_MODEL if the default stops working.
  ollama  A model running on your own computer (https://ollama.com). Set OLLAMA_MODEL.
          Hindi quality depends heavily on the model you pick.
  basic   No AI. Splits your text into sentences and alternates the speakers.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .backgrounds import list_backgrounds, resolve
from .catalog import ACTIONS, EMOTIONS

GEMINI_MODEL_DEFAULT = "gemini-3.1-flash-lite"
OLLAMA_URL_DEFAULT = "http://localhost:11434"


class ScriptError(Exception):
    pass


def _env(name: str) -> str | None:
    """An environment variable; on Windows also the one saved for your user account (setx, or System settings),
    so a key saved after this program's terminal was opened is still found."""
    v = os.environ.get(name)
    if v or os.name != "nt":
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return str(winreg.QueryValueEx(k, name)[0]) or None
    except OSError:
        return None


def provider_status() -> list[dict]:
    return [
        {"id": "gemini", "label": "Gemini (free key)", "ready": bool(_env("GEMINI_API_KEY")),
         "hint": "Set the GEMINI_API_KEY environment variable, then restart."},
        {"id": "ollama", "label": "Ollama (on this computer)", "ready": True,
         "hint": "Start Ollama and set OLLAMA_MODEL if needed."},
        {"id": "basic", "label": "Basic split (no AI)", "ready": True, "hint": ""},
    ]


def _prompt(scenario: str, chars: list[dict], language: str, seconds: int) -> str:
    bgs = ", ".join(b["id"] for b in list_backgrounds())
    cast = "\n".join(f'- id "{c["id"]}": {c["name"]}' for c in chars)
    lang = LANG_RULES.get(language, LANG_RULES["en"])
    lines = max(4, round(seconds / 4))
    return f"""You write scripts for a vertical short video with cartoon characters.
Write about {lines} dialogue lines in total, grouped into 2 to 4 scenes. Keep every line under 12 words.
Dialogue language: {lang}.

Also write "hook": a punchy opening line of at most 6 words, in the same language and script, that makes viewers
want to keep watching (shown as a big title in the first two seconds).

Characters (use only these ids as "speaker"):
{cast}

Allowed backgrounds: {bgs}
Allowed emotions: {", ".join(EMOTIONS)}
Allowed actions: {", ".join(ACTIONS)}

Use activity actions (use_phone, drink_tea, read_book, eat, sit_tea, sit_phone, ...) only when the story
calls for them, and sit_* actions for scenes on a sofa. Use "talk" otherwise. Match emotions to the story.

Scenario: {scenario}

Reply with JSON only, in this shape:
{{"title": "short title", "hook": "...", "scenes": [{{"background": "living_room", "lines": [{{"speaker": "<id>", "text": "...", "emotion": "happy", "action": "talk"}}]}}]}}"""


LANG_RULES = {
    "hi": ("Hindi in DEVANAGARI script only (natural spoken Hindi). Every Hindi word must be written in Devanagari "
           "letters, for example: \"दादा जी, ये क्या किया?\". Never write Hindi in Roman/Latin letters, even if the "
           "scenario is written in English or Hinglish. Common English words (like \"sorry\", \"phone\") may be "
           "written in Devanagari too (\"सॉरी\", \"फ़ोन\")"),
    "hinglish": ("Hinglish: natural spoken Hindi mixed with English, written in Roman/Latin letters, for example: "
                 "\"Dada ji, ye kya kiya?\""),
    "en": "simple spoken English",
}


def _devanagari_share(data: dict) -> float:
    """How much of the dialogue's letters are Devanagari (0..1)."""
    text = " ".join(str(ln.get("text", "")) for sc in data.get("scenes", []) for ln in sc.get("lines", []))
    dev = sum(1 for ch in text if "\u0900" <= ch <= "\u097f")
    lat = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    return dev / max(1, dev + lat)


def _http_json(url: str, body: dict, headers: dict | None = None, timeout: int = 90) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise ScriptError(f"The AI service answered {e.code}. {detail}")
    except Exception as e:
        raise ScriptError(f"Could not reach the AI service: {e}")


def _gemini(prompt: str) -> str:
    key = _env("GEMINI_API_KEY")
    if not key:
        raise ScriptError("GEMINI_API_KEY is not set. Create a free key in Google AI Studio and set it, "
                          "or choose another script option.")
    model = _env("GEMINI_MODEL") or GEMINI_MODEL_DEFAULT
    data = _http_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}},
        {"x-goog-api-key": key})
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise BlockedError(f"Gemini's safety filter refused this text ({block}).")
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ScriptError("The AI answered with no text. Try again, or set GEMINI_MODEL to another model.")


class BlockedError(Exception):
    pass


def _ollama(prompt: str) -> str:
    base = os.environ.get("OLLAMA_URL", OLLAMA_URL_DEFAULT)
    model = os.environ.get("OLLAMA_MODEL", "llama3.1")
    data = _http_json(f"{base}/api/generate",
                      {"model": model, "prompt": prompt, "stream": False, "format": "json"}, timeout=300)
    return data.get("response", "")


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise ScriptError("The AI did not return valid JSON. Try again.")


def _default_bg(chars: list[dict]) -> str | None:
    """Flat cartoon characters get the flat street; the others the usual first picture."""
    if any(str(c.get("look", "")).startswith("stick_") for c in chars):
        return "flat_white"
    if any(str(c.get("look", "")).startswith("flat_") for c in chars):
        return "flat_city_street"
    return resolve(None)


def normalize_scenes(data: dict, chars: list[dict]) -> list[dict]:
    ids = [c["id"] for c in chars]
    bg_ids = {b["id"] for b in list_backgrounds()}
    scenes = []
    for sc in data.get("scenes", []):
        lines = []
        for ln in sc.get("lines", []):
            text = str(ln.get("text", "")).strip()
            if not text:
                continue
            sp = ln.get("speaker")
            if sp not in ids:  # also accept a character's name
                sp = next((c["id"] for c in chars if c["name"].lower() == str(sp).lower()), ids[0])
            em = ln.get("emotion") if ln.get("emotion") in EMOTIONS else "neutral"
            ac = ln.get("action") if ln.get("action") in ACTIONS else "talk"
            lines.append({"speaker": sp, "text": text, "emotion": em, "action": ac})
        if lines:
            bg = sc.get("background") if sc.get("background") in bg_ids else _default_bg(chars)
            cast = []
            for ln in lines:
                if ln["speaker"] not in cast:
                    cast.append(ln["speaker"])
            scenes.append({"background": bg, "cast": cast, "lines": lines})
    if not scenes:
        raise ScriptError("The AI returned no usable scenes. Try again or use the basic split.")
    return scenes


def _basic(scenario: str, chars: list[dict]) -> dict:
    parts = [s.strip() for s in re.split(r"(?<=[।.?!])\s+|\n+", scenario) if s.strip()]
    if not parts:
        raise ScriptError("Write a few sentences in the scenario first.")
    scenes, i = [], 0
    for n in range(0, len(parts), 2):
        lines = []
        for text in parts[n:n + 2]:
            lines.append({"speaker": chars[i % len(chars)]["id"], "text": text, "emotion": "neutral",
                          "action": "talk"})
            i += 1
        cast = []
        for ln in lines:
            if ln["speaker"] not in cast:
                cast.append(ln["speaker"])
        scenes.append({"background": _default_bg(chars), "cast": cast, "lines": lines})
    return {"title": parts[0][:40], "scenes": scenes}


IMPORT_PROMPT = """You turn a short-video screenplay into a JSON timeline for a cartoon video app. Keep the dialogue
exactly as written (same language and script); do not translate or shorten it. Stage directions in brackets become
emotions, actions, sounds, lighting, pop-ups, stickers and text cards - they are never spoken.

Allowed character looks (use the "flat_" cartoon looks, pick the best fit for each character; "flat_brain" is a floating cartoon brain for an
inner voice / "my mind" character; "narrator" is a voice-over (VO / वॉयसओवर) that is never on screen; "flat_kid" is
a child of about 10; "stick_" looks are stickmen, for stick-figure / stickman comedy - use them only when the script
asks for stickmen, usually with the "flat_white" or "flat_doodle" background):
{looks}
Allowed backgrounds (use the "flat_" cartoon ones): {bgs}
Allowed emotions: {emotions}
Allowed actions: {actions}
  - use_phone: looking at a phone (a dark room is then lit by its screen); hold_parcel / hide_behind: a food parcel;
    wipe_tears; throw: throws a chappal at the camera; appear: hidden until this line (someone who suddenly appears);
    walk_in / walk_out / run_in; point; talk (default).
  - kitchen: cook (frying at the stove), step_back (jumps back in fear), hold_jug (lifts a water jug, about to throw
    it), lower_jug (the jug is pushed down), grab_hand (grabs someone's hand to stop them), turn_off_gas,
    cover_kadhai (puts a steel plate on the kadhai), hand_on_shoulder, look_camera (looks at the camera, relieved).
  - slapstick comedy: slip_fall, fall_face, get_up, fly_away (hit and thrown off the screen), hit_head (bonk, stars),
    freeze (frozen in shock), double_take, faint, fight_cloud (a cartoon fight in a dust cloud), crash_wall,
    dizzy, shiver, cartoon_run, run_across (runs through the frame), chase (runs across just behind the other one:
    put it on the other one's run_across line as the actor), sneak_in / tiptoe, laugh_floor, kick, jaw_drop,
    lie_sleep (asleep on the floor, snoring), sleep_stand (falls asleep standing), wake_jolt, poke / shake_awake
    (walks up to the nearest person first), disappointed (slumps, rain cloud), invisible_wall (walks into an
    invisible wall: bonk, the glass shows for a moment).
    Their sounds (slip, thud, bonk, tweet, zip, crash...) are added automatically: do not put them in "sound".
    A fall stays down until the character's next action (get_up).
Allowed camera shots: {shots}
Allowed props (something a character holds or has with them, from that line on; "none" puts it away): {props}
  Movement on a cycle: ride_in / ride_out / ride_cycle. Leaving running: run_out.
Character body: "height" one of {heights}; "build" one of {builds}; "outfit" colour one of {outfits} ("" = default).
Allowed sounds (a line's "sound" plays at the start of the line): {sounds}
Allowed stickers: {stickers}
Allowed cartoon effects (a line's "effect", drawn around the speaker): {effects}

Rules:
- A sound with no speech (stomach growl, doorbell, notification...) is its own line with "text": "" and the sound,
  spoken by the character the camera should show at that moment.
- A phone notification on screen: put its text in "popup" on the line where it appears (and "sound": "ping").
- Night with lights off: the scene's "lighting" is "dark", or "phone" when a phone lights a face. When a light is
  switched on, set "lights": "on" on the first line after it (that line's speaker usually has action "appear").
- A time jump ("20 minutes later") is a card: {{"card": "20 मिनट बाद...", "card_style": "dark", "card_sound": "tick"}}.
- A throw / hit followed by the screen going black: a line with action "throw" (text may be empty), then
  {{"card": "", "card_style": "black", "card_sound": "laugh_track"}} if laughter / a meme sound ends the video.
- Background music mentioned (suspense, comedy...): set "music" to one of: {music}.
- Voice effects: "devil_whisper" for an inner / devil voice, otherwise "".
- Voice-over (VO): a character with look "narrator" speaks it. While the narrator (or anyone) speaks, the person the
  visuals show doing something goes in "actor", with "actor_action" and "actor_emotion" (for example the narrator
  says "she stepped back" -> actor: her id, actor_action: "step_back", actor_emotion: "scared"). This also works on a
  normal line: "Stop!" said by the father while the son's jug is pushed down -> actor: son, actor_action: "lower_jug".
- A visual with no words: a line with "text": "", the action, and "hold": its seconds (for example 2).
- Kadhai / stove: "kadhai" on the line where it changes: "fry" (oil frying), "fire" (the oil catches fire),
  "cover" (covered with a plate), "gas_off". The actions cook / turn_off_gas / cover_kadhai already do their part.
  A close-up of the stove: "shot": "stove". Their sounds (sizzle, fire, clang, knob click, running footsteps, water
  splash) are added automatically: do not put them in "sound".
- A graphic / animation / B-roll explaining why water on an oil fire explodes and why covering works: "broll":
  "oil_fire" on the line spoken during it.
- Big bold text on screen at the end (a message): "overlay" on the line where it appears; put a second line after
  " | " (for example "आग पर पानी न डालें, उसे ढकें! | NEVER USE WATER ON OIL FIRE").
- Music that changes in a scene (for example panic, then calm while explaining): the scene's "music" (one of the music
  ids); "" keeps the music playing. Scene timings in the script (0:10 - 0:25): the scene's "seconds" (here 15).

Reply with JSON only:
{{"title": "...", "hook": "a punchy opening line (max 6 words, same language)", "music": "...",
  "characters": [{{"id": "short_id", "name": "name as in the script", "look": "...", "gender": "male|female",
                   "voice_fx": "", "height": "", "build": "", "outfit": ""}}],
  "scenes": [{{"background": "...", "lighting": "day|dark|phone", "music": "", "seconds": 0, "cast": ["id", ...],
              "lines": [{{"speaker": "id", "text": "...", "emotion": "...", "action": "...", "sound": "",
                         "popup": "", "sticker": "", "lights": "", "shot": "auto", "hold": 0, "actor": "",
                         "actor_action": "", "actor_emotion": "", "kadhai": "", "broll": "", "overlay": "",
                         "prop": "", "effect": ""}}]}},
             {{"card": "...", "card_style": "dark|black|bright", "card_sound": ""}}]}}

Screenplay:
{script}"""


def _secs(v, top: float) -> float:
    try:
        return max(0.0, min(top, float(v or 0)))
    except (TypeError, ValueError):
        return 0.0


def import_screenplay(text: str, provider: str = "gemini") -> dict:
    """A full screenplay (with stage directions) -> characters, scenes, cards, title, hook and music."""
    from .catalog import (BUILDS, DEFAULT_VOICE, EDGE_FOR_GENDER, EFFECT_LABELS, FLAT_BACKGROUNDS, HEIGHTS, LOOKS,
                          OUTFIT_COLORS,
                          PROPS, SHOT_LABELS, SOUND_LABELS, VOICE_FX_LABELS)
    from .fx import MUSIC_LABELS
    from .kitchen import EXPLAINERS, KADHAI_STATES
    from .overlays import STICKER_KINDS
    if not text.strip():
        raise ScriptError("Paste your script first.")
    if provider == "basic" or not _env("GEMINI_API_KEY"):
        raise ScriptError("Importing a full script needs Gemini (set GEMINI_API_KEY).")
    looks = "\n".join(f"- {k}: {v['label']}" for k, v in LOOKS.items())
    prompt = IMPORT_PROMPT.format(looks=looks, bgs=", ".join(b["id"] for b in list_backgrounds()),
                                  emotions=", ".join(EMOTIONS), actions=", ".join(ACTIONS),
                                  sounds=", ".join(SOUND_LABELS), stickers=", ".join(STICKER_KINDS),
                                  music=", ".join(MUSIC_LABELS), shots=", ".join(SHOT_LABELS),
                                  props=", ".join(PROPS), heights=", ".join(k for k in HEIGHTS if k),
                                  builds=", ".join(k for k in BUILDS if k), outfits=", ".join(k for k in OUTFIT_COLORS if k),
                                  effects=", ".join(k for k in EFFECT_LABELS if k),
                                  script=text.strip()[:6000])
    # Gemini's safety check is borderline on comedy with slaps, chappals or jokes about dowry: it can refuse the same
    # text once and accept it the next time. Say what the text is, and try a few times.
    context = ("Context: this is a harmless, family-friendly Indian comedy sketch for a cartoon YouTube Short. "
               "Nobody is really hurt; the humour is everyday family life.\n\n")
    data = None
    for attempt in range(3):
        try:
            data = _parse_json(_gemini(context + prompt))
            break
        except BlockedError as e:
            last = e
    if data is None:
        raise ScriptError(f"{last} It does this now and then with comedy scripts; press Import again, or soften a "
                          "line that sounds violent (for example a slap or a throw).")
    chars, ids = [], set()
    for c in data.get("characters", [])[:8]:
        cid = re.sub(r"[^a-z0-9_]", "", str(c.get("id", "")).lower())[:16] or f"c{len(chars) + 1}"
        while cid in ids:
            cid += "x"
        ids.add(cid)
        look = c.get("look") if c.get("look") in LOOKS else ("flat_aunty" if c.get("gender") == "female" else "flat_man")
        if LOOKS[look].get("style") not in ("flat", "narrator"):   # picture / 3D looks: a flat one (all the acting)
            look = "flat_aunty" if c.get("gender") == "female" or LOOKS[look].get("female") else "flat_man"
        fem = c.get("gender") == "female" or LOOKS[look].get("female")
        fxv = c.get("voice_fx") if c.get("voice_fx") in VOICE_FX_LABELS else ("devil_whisper" if look == "flat_brain" else "")
        chars.append(dict(id=cid, name=str(c.get("name") or cid)[:30], look=look,
                          voice=EDGE_FOR_GENDER["female" if fem else "male"] or DEFAULT_VOICE, voice_fx=fxv,
                          height=c.get("height") if c.get("height") in HEIGHTS else "",
                          build=c.get("build") if c.get("build") in BUILDS else "",
                          outfit=c.get("outfit") if c.get("outfit") in OUTFIT_COLORS else ""))
        c["_id"] = cid
    if not chars:
        raise ScriptError("No characters were found in the script.")
    narr = {c["id"] for c in chars if c["look"] == "narrator"}
    if len(narr) == len(chars):
        raise ScriptError("The script has only a narrator; add at least one character who is on screen.")
    remap = {str(c.get("id")): c["_id"] for c in data.get("characters", [])[:8] if "_id" in c}
    remap.update({str(c.get("name")): c["_id"] for c in data.get("characters", [])[:8] if "_id" in c})
    bg_ids = {b["id"] for b in list_backgrounds()}
    scenes = []
    for sc in data.get("scenes", [])[:30]:
        if "card" in sc:
            scenes.append(dict(card=str(sc.get("card") or "")[:80],
                               card_style=sc.get("card_style") if sc.get("card_style") in ("dark", "black", "bright") else "dark",
                               card_sound=sc.get("card_sound") if sc.get("card_sound") in SOUND_LABELS else "",
                               cast=[], lines=[]))
            continue
        lines = []
        for ln in sc.get("lines", [])[:40]:
            sp = remap.get(str(ln.get("speaker")), ln.get("speaker"))
            if sp not in ids:
                sp = chars[0]["id"]
            lines.append(dict(
                speaker=sp, text=str(ln.get("text") or "").strip(),
                emotion=ln.get("emotion") if ln.get("emotion") in EMOTIONS else "neutral",
                action=ln.get("action") if ln.get("action") in ACTIONS else "talk",
                sound=ln.get("sound") if ln.get("sound") in SOUND_LABELS else "",
                popup=str(ln.get("popup") or "")[:90],
                sticker=ln.get("sticker") if ln.get("sticker") in STICKER_KINDS else "",
                lights=ln.get("lights") if ln.get("lights") in ("on", "off") else "",
                shot=ln.get("shot") if ln.get("shot") in SHOT_LABELS else "auto",
                hold=_secs(ln.get("hold"), 20),
                actor=remap.get(str(ln.get("actor") or ""), ln.get("actor")) if ln.get("actor") else "",
                actor_action=ln.get("actor_action") if ln.get("actor_action") in ACTIONS else "idle",
                actor_emotion=ln.get("actor_emotion") if ln.get("actor_emotion") in EMOTIONS else "neutral",
                kadhai=ln.get("kadhai") if ln.get("kadhai") in KADHAI_STATES else "",
                broll=ln.get("broll") if ln.get("broll") in EXPLAINERS else "",
                overlay=str(ln.get("overlay") or "")[:120],
                prop=ln.get("prop") if ln.get("prop") in PROPS or ln.get("prop") == "none" else "",
                effect=ln.get("effect") if ln.get("effect") in EFFECT_LABELS else ""))
            if lines[-1]["actor"] not in ids or lines[-1]["actor"] in narr:
                lines[-1]["actor"] = ""
            last = lines[-1]
            if last["speaker"] in narr and last["action"] not in ("talk", "idle", "look_camera"):
                if not last["actor"]:          # the narrator does not act: the action is the on-screen person's
                    cands = [x for x in sc.get("cast", []) if remap.get(str(x), x) in ids and remap.get(str(x), x) not in narr]
                    last["actor"] = remap.get(str(cands[0]), cands[0]) if cands else ""
                    last["actor_action"], last["actor_emotion"] = last["action"], last["emotion"]
                last["action"] = "talk"
        if not lines:
            continue
        auto = {"throw": ("chappal", "slap", "whoosh", "punch"), "cook": ("sizzle",), "turn_off_gas": ("click",),
                "cover_kadhai": ("clang",), "run_in": ("footsteps",), "lower_jug": ("splash",)}
        from .stick import MOVE_SOUNDS, move_hold
        for a_, snds in MOVE_SOUNDS.items():
            auto[a_] = tuple(x[1] for x in snds)
        for ln in lines:                       # sounds the app adds by itself are not added twice
            made = set(auto.get(ln["action"], ())) | set(auto.get(ln["actor_action"], ()))
            made |= {"fry": {"sizzle"}, "fire": {"fire", "whoosh"}, "cover": {"clang"}, "gas_off": {"click"}}.get(ln["kadhai"], set())
            if ln["sound"] in made:
                ln["sound"] = ""
            if not ln["text"] and not ln["sound"] and not ln["hold"]:
                ln["hold"] = move_hold(ln["action"])   # a visual with no words still gets a moment on screen
        lighting = sc.get("lighting") if sc.get("lighting") in ("day", "dark", "phone") else "day"
        on = [i for i, ln in enumerate(lines) if ln["lights"] == "on"]
        if on:                                 # a light switched on means the room was dark before
            if lighting == "day":
                lighting = "dark"
            appear = next((i for i, ln in enumerate(lines) if ln["action"] == "appear"), None)
            if appear is not None and on[0] < appear:       # it comes on when that person appears
                lines[on[0]]["lights"], lines[appear]["lights"] = "", "on"
        cast = [remap.get(str(x), x) for x in sc.get("cast", [])]
        cast = [x for x in cast if x in ids]
        for ln in lines:
            if ln["speaker"] not in cast:
                cast.append(ln["speaker"])
        cast = [x for x in cast if x not in narr]
        for ln in lines:
            if ln["actor"] and ln["actor"] not in cast:
                cast.append(ln["actor"])
        if not cast:
            cast = [next(c["id"] for c in chars if c["id"] not in narr)]
        bg = sc.get("background") if sc.get("background") in bg_ids else next(iter(FLAT_BACKGROUNDS))
        if bg not in FLAT_BACKGROUNDS:         # flat cartoon characters: the cartoon version of that place
            bg = next((f for f in FLAT_BACKGROUNDS if f == "flat_" + bg or bg in f), bg)
        if any(ln["kadhai"] or {ln["action"], ln["actor_action"]} & {"cook", "turn_off_gas", "cover_kadhai"}
               for ln in lines):
            bg = "flat_kitchen"                # the kadhai and stove are in the cartoon kitchen
        scenes.append(dict(background=bg, lighting=lighting, cast=cast, lines=lines,
                           music=sc.get("music") if sc.get("music") in MUSIC_LABELS or sc.get("music") == "none" else "",
                           seconds=_secs(sc.get("seconds"), 60)))
    if not any(s.get("lines") for s in scenes):
        raise ScriptError("No dialogue was found in the script.")
    music = data.get("music") if data.get("music") in MUSIC_LABELS else ""
    return dict(title=str(data.get("title") or "")[:60], hook=str(data.get("hook") or "")[:60], music=music,
                characters=chars, scenes=scenes)


def generate(scenario: str, chars: list[dict], language: str = "hi", seconds: int = 45,
             provider: str = "gemini") -> dict:
    if not chars:
        raise ScriptError("Add at least one character first.")
    if not scenario.strip():
        raise ScriptError("Write your scenario first.")
    if provider == "basic":
        data = _basic(scenario, chars)
    else:
        prompt = _prompt(scenario, chars, language, seconds)
        ask = _gemini if provider == "gemini" else _ollama
        data = _parse_json(ask(prompt))
        if language == "hi" and _devanagari_share(data) < 0.6:      # came back in Roman letters: ask once more
            again = _parse_json(ask(prompt + "\n\nIMPORTANT: your last answer used Roman letters for Hindi. "
                                             "Write ALL dialogue, the title and the hook in Devanagari script."))
            if _devanagari_share(again) > _devanagari_share(data):
                data = again
    return {"title": str(data.get("title", "")).strip(), "hook": str(data.get("hook", "") or "").strip(),
            "scenes": normalize_scenes(data, chars)}
