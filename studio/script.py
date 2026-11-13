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
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ScriptError("The AI answered with no text. Try again, or set GEMINI_MODEL to another model.")


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
