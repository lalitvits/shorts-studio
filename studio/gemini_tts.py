"""Gemini voices: Google's Gemini text-to-speech, with the line's emotion setting how it is spoken.

Uses the same key as the script writer (GEMINI_API_KEY). Set GEMINI_TTS_MODEL to choose a model; otherwise the
first one that works from MODELS is used. The free tier has small per-minute and per-day limits: when the
per-minute limit is hit the app waits and tries again; when the daily limit is hit, the caller falls back to the
Microsoft online voices for the rest of the lines.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import CACHE_DIR, find_ffmpeg
from .script import _env

MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-3.1-flash-tts-preview",
          "gemini-2.5-flash-preview-tts"]

# How each emotion is spoken: an audio tag in front of the line. (The newer TTS models read a written instruction
# like "Say angrily: ..." out loud, but they act on a tag like "[angry]" without saying it.)
TAGS = {
    "neutral": "", "happy": "[happy]", "sad": "[sad]", "worried": "[worried]", "angry": "[angry]",
    "surprised": "[surprised]", "laughing": "[laughing]", "crying": "[crying]", "scared": "[scared]",
    "excited": "[excited]", "sleepy": "[sleepy]", "embarrassed": "[embarrassed]", "confused": "[confused]",
    "bored": "[bored]", "in_love": "[affectionate]", "proud": "[proud]", "disgusted": "[disgusted]",
    "thinking": "[thoughtful]", "shocked": "[shocked]", "relieved": "[relieved]",
}


class GeminiTTSError(Exception):
    def __init__(self, msg: str, daily: bool = False):
        super().__init__(msg)
        self.daily = daily      # the daily limit is used up: stop asking for the rest of this run


_working_model: str | None = None
FREE_PER_MODEL = 10          # free tier, measured: about 10 lines per model per day (Google can change this)
USAGE = CACHE_DIR / "gemini_voice_usage.json"


def _today() -> str:
    """The free-tier day (it resets at midnight Pacific time, about UTC-8)."""
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - 8 * 3600))


def _usage() -> dict:
    try:
        u = json.loads(USAGE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        u = {}
    if u.get("day") != _today():
        u = {"day": _today(), "count": {}, "exhausted": {}}
    return u


def _save_usage(u: dict):
    try:
        USAGE.write_text(json.dumps(u), encoding="utf-8")
    except OSError:
        pass


def lines_left() -> int:
    """About how many Gemini voice lines are left today on the free tier."""
    u = _usage()
    now = time.time()
    return sum(0 if u["exhausted"].get(m, 0) > now else max(0, FREE_PER_MODEL - u["count"].get(m, 0))
               for m in MODELS[:3])


class _Exhausted(dict):        # model -> time its daily limit resets; kept on disk so it survives a restart
    def get(self, m, default=0):
        return _usage()["exhausted"].get(m, default)

    def __setitem__(self, m, until):
        u = _usage()
        u["exhausted"][m] = until
        _save_usage(u)

    def values(self):
        return _usage()["exhausted"].values() or [time.time()]


_exhausted = _Exhausted()


def _count(model: str):
    u = _usage()
    u["count"][model] = u["count"].get(model, 0) + 1
    _save_usage(u)


def ready() -> bool:
    return bool(_env("GEMINI_API_KEY"))


def prompt_for(text: str, emotion: str) -> str:
    tag = TAGS.get(emotion, "")
    return f"{tag} {text}" if tag else text


def _request(model: str, key: str, prompt: str, voice: str) -> bytes:
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    try:
        part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    except (KeyError, IndexError):
        raise GeminiTTSError("Gemini returned no audio for this line.")
    raw = base64.b64decode(part["data"])
    if raw[:4] == b"RIFF":
        return raw
    rate = int((re.search(r"rate=(\d+)", part.get("mimeType", "")) or [0, 24000])[1])
    return _pcm_to_wav(raw, rate)


def _pcm_to_wav(raw: bytes, rate: int) -> bytes:
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(raw)
    return buf.getvalue()


def _retry_seconds(err_body: str) -> float | None:
    m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', err_body)
    return float(m.group(1)) if m else None


def synthesize(text: str, voice: str, emotion: str, out_wav: Path, rate: int):
    """Speak `text` with Gemini voice `voice` and write a mono WAV at `rate` Hz to out_wav.
    The free tier's daily limit is per model, so when one model's limit is used up the next model is tried."""
    global _working_model
    key = _env("GEMINI_API_KEY")
    if not key:
        raise GeminiTTSError("Gemini voices need GEMINI_API_KEY (the same key as the script writer).")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise GeminiTTSError("FFmpeg was not found.")
    chosen = _env("GEMINI_TTS_MODEL")
    order = [chosen] if chosen else ([_working_model] if _working_model else []) + [m for m in MODELS if m != _working_model]
    now = time.time()
    models = [m for m in order if _exhausted.get(m, 0) <= now]
    if not models:
        raise GeminiTTSError("The free Gemini voice limit for today is used up; these lines use the Microsoft voices. "
                             "It resets in about %d hours." % max(1, round((min(_exhausted.values()) - now) / 3600)),
                             daily=True)
    prompt = prompt_for(text, emotion)
    last, daily_hit = "no model answered", False
    for model in models:
        for attempt in range(4):
            try:
                wav = _request(model, key, prompt, voice)
                _working_model = model
                _count(model)
                tmp = out_wav.with_suffix(".gem.wav")
                tmp.write_bytes(wav)
                r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-ar", str(rate), "-ac", "1",
                                    "-c:a", "pcm_s16le", str(out_wav)], capture_output=True)
                tmp.unlink(missing_ok=True)
                if r.returncode != 0:
                    raise GeminiTTSError("Could not convert the Gemini audio.")
                return
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "ignore")
                if e.code == 429:
                    wait = _retry_seconds(body)
                    if "PerDay" in body or (wait is not None and wait > 90):   # daily limit of this model: next model
                        _exhausted[model] = time.time() + (wait or 3600)
                        if _working_model == model:
                            _working_model = None
                        last, daily_hit = f"{model}: daily limit", True
                        break
                    if attempt < 3:
                        time.sleep(min(65.0, (wait or 20.0) + 1.0))    # per-minute limit: wait, then try again
                        continue
                    last = f"{model}: busy"
                    break
                if e.code in (400, 404) and not chosen:              # this model does not exist (any more): next
                    last = f"{model}: HTTP {e.code}"
                    break
                if e.code >= 500 and attempt < 3:
                    time.sleep(3)
                    continue
                raise GeminiTTSError(f"Gemini voice failed (HTTP {e.code}): {body[:200]}")
            except urllib.error.URLError as e:
                raise GeminiTTSError(f"Could not reach Gemini ({e.reason}).")
    if daily_hit:
        raise GeminiTTSError("The free Gemini voice limit for today is used up; these lines use the Microsoft voices.",
                             daily=True)
    raise GeminiTTSError(f"No Gemini voice model worked ({last}). Set GEMINI_TTS_MODEL to one your key can use.")
