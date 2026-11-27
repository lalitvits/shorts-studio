"""ElevenLabs voices: very expressive text-to-speech that acts out each line's emotion, and speaks Hindi.

Needs ELEVENLABS_API_KEY (elevenlabs.io: Profile, API Keys; the free plan has about 10,000 characters a month).
The model is eleven_v3 (set ELEVENLABS_MODEL to choose another, for example eleven_multilingual_v2). With eleven_v3
the line's emotion is an audio tag in front of the words ("[crying] ..."), which the voice acts out without saying
it. Other models get no tag; their delivery comes from the punctuation.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import find_ffmpeg


def _env(name: str):
    from .script import _env as env          # imported here: the catalog loads this module (no circular import)
    return env(name)

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
DEFAULT_MODEL = "eleven_v3"

# How each emotion is acted (eleven_v3 audio tags; the voice performs them and does not read them out).
TAGS = {
    "neutral": "[casually]", "happy": "[cheerfully] [warmly]", "sad": "[sad] [sighs] [quietly]",
    "worried": "[nervous] [stammering] [anxiously]", "angry": "[angry] [shouting] [scolding]",
    "surprised": "[surprised] [gasps]", "laughing": "[laughing] [laughs]", "crying": "[crying] [sobbing]",
    "scared": "[scared] [whispers] [trembling]", "excited": "[excited] [energetic] [loudly]",
    "sleepy": "[sleepy] [yawning] [mumbling]", "embarrassed": "[embarrassed] [awkward laugh]",
    "confused": "[confused] [hesitant]", "bored": "[bored] [flatly]", "in_love": "[sweetly] [softly]",
    "proud": "[proudly] [confident]", "disgusted": "[disgusted]", "thinking": "[thoughtful] [slowly]",
    "shocked": "[shocked] [gasps] [loudly]", "relieved": "[relieved] [long sigh] [exhausted]",
}

# Ready-made ElevenLabs voices (name -> voice id) that every account has. They speak Hindi with eleven_v3 and
# eleven_multilingual_v2. Any other voice from your ElevenLabs voice library can be used as "eleven:<voice id>".
VOICES = {
    "adam": ("pNInz6obpgDQGcFmaJgB", "male", "deep, firm"),
    "brian": ("nPczCjzI2devNBz1zQrb", "male", "deep, warm"),
    "chris": ("iP95p4xoKVk53GoZ742B", "male", "casual, young"),
    "eric": ("cjVigY5qzO86Huf0OWal", "male", "smooth"),
    "liam": ("TX3LPaxmHKxFdv7VOQHJ", "male", "young, energetic"),
    "will": ("bIHbv24MWmeRgasZH58o", "male", "friendly, young"),
    "bill": ("pqHfZKP75CvOlQylNhV4", "male", "older"),
    "george": ("JBFqnCBsd6RMkjVDRZzb", "male", "warm, mature"),
    "sarah": ("EXAVITQu4vr4xnSDxMaL", "female", "soft, young"),
    "jessica": ("cgSgspJ2msm6clMCkdW9", "female", "expressive, young"),
    "laura": ("FGY2WhTYpPnrIDTdsKH5", "female", "upbeat"),
    "lily": ("pFZP5JQG7iQjIQuC4Bku", "female", "warm"),
    "matilda": ("XrExE9yKIg1WjnnlVkGX", "female", "friendly"),
    "alice": ("Xb7hH8MSUJpSbSDYk0k2", "female", "clear, confident"),
}


class ElevenLabsError(Exception):
    pass


def ready() -> bool:
    return bool(_env("ELEVENLABS_API_KEY"))


def voice_id(name: str) -> str:
    """A voice name from VOICES, or a raw ElevenLabs voice id."""
    return VOICES.get(name.lower(), (name,))[0]


def prompt_for(text: str, emotion: str, model: str) -> str:
    """The emotion's tags in front of the words. Tags written in the line itself ([laughs], [sarcastic]...) are kept
    for eleven_v3, which acts them, and removed for other models."""
    if model != "eleven_v3":
        import re
        return " ".join(re.sub(r"\[[^\[\]]{1,30}\]", " ", text).split())
    tag = TAGS.get(emotion, "")
    return f"{tag} {text}" if tag else text


def synthesize(text: str, voice: str, emotion: str, out_wav: Path, rate: int, speed: float = 1.0,
               tighten: str = ""):
    """Speak `text` with ElevenLabs voice `voice` (a name or an id) acting `emotion`; write a mono WAV at `rate`."""
    key = _env("ELEVENLABS_API_KEY")
    if not key:
        raise ElevenLabsError("ElevenLabs voices need ELEVENLABS_API_KEY.")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise ElevenLabsError("FFmpeg was not found.")
    model = _env("ELEVENLABS_MODEL") or DEFAULT_MODEL
    body = {"text": prompt_for(text, emotion, model), "model_id": model,
            # eleven_v3 takes stability 0.0 (creative, most acting), 0.5 or 1.0; the older models any value
            "voice_settings": {"stability": 0.0 if model == "eleven_v3" else 0.35, "similarity_boost": 0.75,
                               "style": 0.6, "use_speaker_boost": True}}
    if model != "eleven_v3":
        body["voice_settings"]["speed"] = max(0.7, min(1.2, speed))
    req = urllib.request.Request(API.format(voice=voice_id(voice)), data=json.dumps(body).encode("utf-8"),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                mp3 = r.read()
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")
            if (e.code == 429 or e.code >= 500) and attempt < 3:
                time.sleep(3 + attempt * 5)
                continue
            try:
                detail = json.loads(msg).get("detail")
                msg = detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
            except (ValueError, AttributeError):
                msg = msg[:200]
            if e.code == 401:
                msg = "the key was not accepted, or the free characters for this month are used up. " + msg
            raise ElevenLabsError(f"ElevenLabs voice failed (HTTP {e.code}): {msg}")
        except urllib.error.URLError as e:
            raise ElevenLabsError(f"Could not reach ElevenLabs ({e.reason}).")
    if not mp3:
        raise ElevenLabsError("ElevenLabs returned no audio for this line.")
    tmp = out_wav.with_suffix(".eleven.mp3")
    tmp.write_bytes(mp3)
    filters = [f for f in (tighten, f"atempo={speed:.2f}" if model == "eleven_v3" and abs(speed - 1) > 0.02 else "") if f]
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp)] + (["-af", ",".join(filters)] if filters else []) + [
        "-ar", str(rate), "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)]
    r = subprocess.run(cmd, capture_output=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise ElevenLabsError("Could not convert the ElevenLabs audio.")
