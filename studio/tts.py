"""Voices.

`get_clip(text, voice)` returns a Clip: a 22 kHz mono WAV, its duration, and a
mouth-movement envelope (how loud the voice is every 20 ms).

Engines
  edge    free online voices through the `edge-tts` package (needs internet).
          This is an unofficial client of Microsoft's Edge read-aloud service, so
          it can change or stop working, and its terms for monetised videos are
          unclear. Keep it behind this interface so you can swap in another engine.
  silent  no sound; duration is estimated from the text. Used for tests and as a
          fallback so you can still preview timing and animation.
  auto    edge when available, otherwise silent (with a warning).
  gemini  Google Gemini text-to-speech for every character (see gemini_tts.py); the line's emotion sets how it is
          spoken. A character with a "Gemini" voice uses Gemini with any engine except silent. When Gemini fails
          or its free limit is used up, the line uses the Microsoft voice instead (with a warning).
"""
from __future__ import annotations

import array
import asyncio
import hashlib
import math
import random
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from .config import CACHE_DIR, find_ffmpeg

RATE = 22050
ENV_HZ = 50


class TTSError(Exception):
    pass


@dataclass
class Clip:
    wav: Path
    duration: float
    env: list
    synthetic: bool = False
    warning: str = ""

    def mouth_at(self, t: float) -> float:
        if t < 0 or not self.env:
            return 0.0
        i = int(t * ENV_HZ)
        if i >= len(self.env):
            return 0.0
        seg = self.env[max(0, i - 1): i + 2]
        return min(1.0, max(seg) * 1.35)


def _key(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:24]


def read_samples(path: Path) -> array.array:
    with wave.open(str(path), "rb") as w:
        raw = w.readframes(w.getnframes())
    a = array.array("h")
    a.frombytes(raw)
    return a


def compute_env(samples: array.array) -> list:
    step = RATE // ENV_HZ
    vals = []
    for i in range(0, len(samples) - step + 1, step):
        chunk = samples[i:i + step]
        vals.append(math.sqrt(sum(s * s for s in chunk) / step))
    loud = sorted(v for v in vals if v > 40)
    if not loud:
        return [0.0] * len(vals)
    ref = loud[int(len(loud) * 0.9)] or 1.0
    return [min(1.0, v / ref) for v in vals]


def _write_silence(path: Path, seconds: float):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * int(seconds * RATE))


def _synthetic_env(text: str, seconds: float) -> list:
    rng = random.Random(_key(text))
    n = int(seconds * ENV_HZ)
    env, level = [], 0.0
    for i in range(n):
        if i % rng.randint(6, 11) == 0:
            level = rng.choice([0.1, 0.35, 0.6, 0.85, 1.0])
        env.append(level * (0.75 + 0.25 * math.sin(i * 0.9)))
    return env


def _edge_to_wav(text: str, voice: str, rate: str, out_wav: Path, pitch: str = "+0Hz", volume: str = "+0%"):
    import edge_tts  # imported here so the app still starts without it

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise TTSError("FFmpeg was not found. Install it and restart the app.")
    mp3 = out_wav.with_suffix(".mp3")

    async def run():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume).save(str(mp3))

    asyncio.run(run())
    if not mp3.exists() or mp3.stat().st_size == 0:
        raise TTSError("The voice service returned no audio.")
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(RATE), "-ac", "1",
                        "-c:a", "pcm_s16le", str(out_wav)], capture_output=True)
    mp3.unlink(missing_ok=True)
    if r.returncode != 0:
        raise TTSError("Could not convert the voice audio: " + r.stderr.decode("utf-8", "ignore")[-300:])


def estimate_seconds(text: str) -> float:
    n = len(text.replace(" ", ""))
    return max(1.2, n / 11.0 + 0.4)


def _gender(voice: str) -> str:
    from .catalog import VOICES
    return next((v.get("gender", "male") for v in VOICES if v["id"] == voice), "male")


def _gemini_clip(text: str, voice: str, emotion: str) -> Clip:
    from . import gemini_tts
    name = voice.split(":", 1)[1]
    wav = CACHE_DIR / "tts" / f"{_key('gemini-tag', text, name, emotion)}.wav"
    if not wav.exists():
        gemini_tts.synthesize(text, name, emotion, wav, RATE)
    s = read_samples(wav)
    return Clip(wav, len(s) / RATE, compute_env(s))


# How each emotion changes the Microsoft voices (they have no acting styles, so the delivery is shaped with
# speed %, pitch Hz and volume %, plus pauses and exclamation marks in the text). Checked by ear-tests with Gemini:
# the sad and excited versions were clearly picked over the flat one; anger is only a subtle change with these
# voices (raised pitch, faster, louder). For real acting use the Gemini voices.
PROSODY = {
    "neutral": (0, 0, 0), "happy": (8, 12, 5), "excited": (18, 22, 15), "angry": (14, 8, 25), "sad": (-20, -14, -20),
    "crying": (-22, -10, -22), "scared": (16, 18, -5), "surprised": (6, 25, 10), "shocked": (4, 28, 15),
    "worried": (-6, 6, -8), "laughing": (12, 18, 10), "sleepy": (-25, -12, -18), "bored": (-18, -10, -12),
    "thinking": (-12, -4, -6), "proud": (-4, -6, 10), "embarrassed": (-8, 8, -15), "in_love": (-10, 6, -10),
    "disgusted": (-6, -8, 5), "confused": (-8, 10, 0), "relieved": (-8, 4, 0),
}
LOUD = {"angry", "excited", "surprised", "shocked", "laughing", "scared"}
SOFT = {"sad", "crying", "worried", "thinking", "sleepy", "bored", "embarrassed", "in_love"}


def shape_text(text: str, emotion: str) -> str:
    """Punctuation that makes the voice act: pauses for soft emotions, exclamations for loud ones."""
    t = text.rstrip()
    if not t:
        return t
    if emotion in SOFT:
        t = t.replace(",", "...").replace("،", "...")
        if t[-1] in ".!?।":
            t = t.rstrip(".!?।") + ("...?" if t[-1] == "?" else "...")
        else:
            t += "..."
    elif emotion in LOUD:
        if t[-1] in ".।":
            t = t[:-1] + "!"
        elif t[-1] not in "!?":
            t += "!"
    return t


def prosody(emotion: str, pitch_hz: int = 0, rate_pct: int = 0) -> tuple[str, str, str]:
    r, p, v = PROSODY.get(emotion, (0, 0, 0))
    r = max(-50, min(80, r + int(rate_pct)))
    p = max(-60, min(80, p + int(pitch_hz)))
    return f"{r:+d}%", f"{p:+d}Hz", f"{v:+d}%"


def get_clip(text: str, voice: str, engine: str = "auto", rate: str = "+0%", emotion: str = "neutral",
             voice_pitch: int = 0, voice_rate: int = 0) -> Clip:
    text = " ".join(text.split())
    warning = ""
    from .catalog import EDGE_FOR_GENDER, GEMINI_FOR_GENDER
    gem = voice.startswith("gemini:")
    if engine != "silent" and (gem or engine == "gemini"):
        gvoice = voice if gem else "gemini:" + GEMINI_FOR_GENDER[_gender(voice)]
        try:
            return _gemini_clip(text, gvoice, emotion)
        except Exception as e:  # noqa: BLE001  (no key, limit used up, network, ...)
            warning = f"Gemini voice: {e}"
            if gem:
                voice = EDGE_FOR_GENDER[_gender(voice)]
            engine = "auto"
    if gem:                                   # silent engine with a Gemini voice
        voice = EDGE_FOR_GENDER[_gender(voice)]
    if engine in ("auto", "edge"):
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            if engine == "edge":
                raise TTSError("edge-tts is not installed. Run: pip install edge-tts")
            warning = "edge-tts is not installed, so voices are silent. Run: pip install edge-tts"
            engine = "silent"
    if engine in ("auto", "edge"):
        r, p, v = prosody(emotion, voice_pitch, voice_rate)
        said = shape_text(text, emotion)
        wav = CACHE_DIR / "tts" / f"{_key('edge2', said, voice, r, p, v)}.wav"
        if not wav.exists():
            try:
                _edge_to_wav(said, voice, r, wav, pitch=p, volume=v)
            except Exception as e:  # network down, service change, ...
                if engine == "edge":
                    raise TTSError(f"Voice generation failed: {e}")
                warning = f"Online voice failed ({e}). Using silence for this line."
                engine = "silent"
        if engine != "silent":
            s = read_samples(wav)
            return Clip(wav, len(s) / RATE, compute_env(s), warning=warning)
    secs = estimate_seconds(text)
    wav = CACHE_DIR / "tts" / f"{_key('silent', secs)}.wav"
    if not wav.exists():
        _write_silence(wav, secs)
    return Clip(wav, secs, _synthetic_env(text, secs), synthetic=True, warning=warning)


def join_clips(first: Clip, second: Clip, gap: float = 0.12) -> Clip:
    """One clip: `first`, a short pause, then `second` (used for an emotional sound followed by words)."""
    key = _key("join", first.wav, first.wav.stat().st_size, second.wav, second.wav.stat().st_size, gap)
    out = CACHE_DIR / "tts" / f"{key}.wav"
    a, b = read_samples(first.wav), read_samples(second.wav)
    pause = int(gap * RATE)
    if not out.exists():
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(a.tobytes() + b"\x00\x00" * pause + b.tobytes())
    env = first.env + [0.0] * int(gap * ENV_HZ) + second.env
    return Clip(out, (len(a) + pause + len(b)) / RATE, env, synthetic=second.synthetic, warning=second.warning)
