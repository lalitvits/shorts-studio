"""Captions from your own audio: Gemini listens to each line's part of the uploaded audio and writes down the words.

Uses GEMINI_API_KEY (the same key as the script writer). Every result is saved in data/cache/transcripts, so a
line is only sent once. Hindi is written in Devanagari (English words in Latin letters); nothing is translated.
"""
from __future__ import annotations

import base64
import json
import subprocess
import time
import urllib.error
import urllib.request

from .config import CACHE_DIR, UPLOADS_DIR, find_ffmpeg
from .script import _env

DIR = CACHE_DIR / "transcripts"
MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
HINT = {
    "hi": "The speech is most likely Hindi or Hinglish: write Hindi words in Devanagari script and English words "
          "in Latin script.",
    "en": "The speech is most likely English.",
}


class TranscribeError(Exception):
    pass


def _cache(uid: str) -> dict:
    p = DIR / f"{uid}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        return {}


def _save(uid: str, data: dict):
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{uid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")


def _cut(uid: str, start: float, end: float) -> bytes:
    ffmpeg = find_ffmpeg()
    src = UPLOADS_DIR / f"{uid}.wav"
    if not ffmpeg or not src.exists():
        raise TranscribeError("The audio file is not available. Upload it again.")
    a, b = max(0.0, start - 0.1), end + 0.15
    r = subprocess.run([ffmpeg, "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
                        "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 100:
        raise TranscribeError("Could not cut this part of the audio.")
    return r.stdout


def _ask(model: str, key: str, wav: bytes, language: str) -> str:
    prompt = ("Transcribe the speech in this audio clip exactly, word for word. " + HINT.get(language, "") +
              " Do not translate and do not add anything. Answer with only the spoken words. "
              "If nothing is spoken, answer with an empty line.")
    body = {"contents": [{"parts": [{"text": prompt},
                                    {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(wav).decode()}}]}],
            "generationConfig": {"temperature": 0.0}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"), headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    try:
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        return ""
    return " ".join(text.replace("\n", " ").split()).strip().strip('"“”')


def transcribe(uid: str, start: float, end: float, language: str = "hi") -> str:
    """The words spoken between start and end (seconds into the uploaded audio)."""
    k = f"{start:.2f}-{end:.2f}-{language}"
    cache = _cache(uid)
    if k in cache:
        return cache[k]
    key = _env("GEMINI_API_KEY")
    if not key:
        raise TranscribeError("Captions from your audio need a Gemini key (GEMINI_API_KEY), like the script writer.")
    wav = _cut(uid, start, end)
    chosen = _env("GEMINI_MODEL")
    models = [chosen] + [m for m in MODELS if m != chosen] if chosen else MODELS
    last = ""
    for model in models:
        for attempt in range(4):
            try:
                text = _ask(model, key, wav, language)
                cache = _cache(uid)
                cache[k] = text
                _save(uid, cache)
                return text
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "ignore")
                if e.code == 429 and "PerDay" not in body and attempt < 3:
                    time.sleep(20)                       # per-minute limit: wait and try again
                    continue
                last = f"{model}: HTTP {e.code}"
                break                                    # daily limit, unknown model, ...: next model
            except urllib.error.URLError as e:
                raise TranscribeError(f"Could not reach Gemini ({e.reason}).")
    raise TranscribeError(f"Gemini could not write the captions ({last}).")


def transcribe_many(uid: str, ranges: list, language: str = "hi") -> tuple[list, str]:
    """Texts for many (start, end) ranges, and a warning ('' when all went well)."""
    out, warning = [], ""
    for s, e in ranges:
        try:
            out.append(transcribe(uid, float(s), float(e), language))
        except TranscribeError as err:
            warning = str(err)
            out.append("")
    return out, warning
