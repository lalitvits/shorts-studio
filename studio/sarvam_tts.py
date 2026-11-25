"""Sarvam voices: Sarvam AI's Bulbul text-to-speech, made for Hindi and other Indian languages.

Needs SARVAM_API_KEY (create one at dashboard.sarvam.ai). Set SARVAM_TTS_MODEL to choose a model (default
bulbul:v3). Bulbul has no acting styles, so a line's emotion is shaped with its speed, its expressiveness
("temperature") and its punctuation, like the Microsoft voices.
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

from .config import find_ffmpeg
from .script import _env

URL = "https://api.sarvam.ai/text-to-speech"
DEFAULT_MODEL = "bulbul:v3"

# Extra speed (percent) per emotion, on top of the app's snappy Shorts pace.
SPEED = {
    "neutral": 0, "happy": 6, "excited": 14, "angry": 10, "sad": -14, "crying": -16, "scared": 12, "surprised": 6,
    "shocked": 4, "worried": -4, "laughing": 8, "sleepy": -20, "bored": -14, "thinking": -10, "proud": -4,
    "embarrassed": -6, "in_love": -8, "disgusted": -4, "confused": -6, "relieved": -6,
}
CALM = {"neutral", "thinking", "bored", "sleepy"}
PACE = 8          # percent faster than Sarvam's normal speed: Shorts need snappy lines


class SarvamTTSError(Exception):
    pass


def ready() -> bool:
    return bool(_env("SARVAM_API_KEY"))


def language_for(text: str) -> str:
    """hi-IN for Devanagari text, en-IN otherwise (Bulbul reads mixed Hindi-English in either)."""
    return "hi-IN" if re.search(r"[ऀ-ॿ]", text) else "en-IN"


def pace_for(emotion: str, voice_rate: int = 0) -> float:
    return round(max(0.5, min(2.0, 1.0 + (PACE + SPEED.get(emotion, 0) + int(voice_rate)) / 100.0)), 2)


def _request(key: str, body: dict) -> bytes:
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"api-subscription-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    audios = data.get("audios") or []
    if not audios:
        raise SarvamTTSError("Sarvam returned no audio for this line.")
    return b"".join(base64.b64decode(a) for a in audios[:1])


def synthesize(text: str, speaker: str, emotion: str, out_wav: Path, rate: int, voice_rate: int = 0,
               tighten: str = ""):
    """Speak `text` with Sarvam voice `speaker` and write a mono WAV at `rate` Hz to out_wav."""
    key = _env("SARVAM_API_KEY")
    if not key:
        raise SarvamTTSError("Sarvam voices need SARVAM_API_KEY.")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise SarvamTTSError("FFmpeg was not found.")
    body = {"text": text, "target_language_code": language_for(text), "speaker": speaker,
            "model": _env("SARVAM_TTS_MODEL") or DEFAULT_MODEL, "pace": pace_for(emotion, voice_rate),
            "temperature": 0.5 if emotion in CALM else 0.8, "speech_sample_rate": rate}
    for attempt in range(4):
        try:
            wav = _request(key, body)
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")
            if (e.code == 429 or e.code >= 500) and attempt < 3:
                time.sleep(2 + attempt * 4)
                continue
            try:
                msg = json.loads(msg)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                msg = msg[:200]
            if e.code in (401, 403):
                msg = "the key was not accepted. " + msg
            raise SarvamTTSError(f"Sarvam voice failed (HTTP {e.code}): {msg}")
        except urllib.error.URLError as e:
            raise SarvamTTSError(f"Could not reach Sarvam ({e.reason}).")
    tmp = out_wav.with_suffix(".sarvam.wav")
    tmp.write_bytes(wav)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp)] + (["-af", tighten] if tighten else []) + [
        "-ar", str(rate), "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)]
    r = subprocess.run(cmd, capture_output=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SarvamTTSError("Could not convert the Sarvam audio.")
