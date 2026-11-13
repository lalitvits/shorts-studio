"""Emotional sounds (laugh, angry growl, frustrated groan, sigh, ...).

Where a sound comes from, in this order:
  1. Your own recording in assets/sounds/. Name it after the sound, for example `laugh.mp3`, or `laugh_female.mp3` /
     `laugh_male.mp3` to use a different recording for female and male characters. This sounds the most natural.
  2. A simple synthesized sound made by this file (no internet needed). It is built from a basic voice model: a
     buzzing source shaped by vowel-like resonances plus breath noise. It is recognisable but clearly artificial.

The pitch of the synthesized sounds follows the character's voice (male or female). Results are cached in
data/cache/sfx so each sound is made only once.
"""
from __future__ import annotations

import array
import hashlib
import math
import random
import subprocess
import wave
from pathlib import Path

from .catalog import SOUND_LABELS, VOICES
from .config import ASSETS_DIR, CACHE_DIR, find_ffmpeg
from .tts import RATE, Clip, compute_env, read_samples

SOUNDS_DIR = ASSETS_DIR / "sounds"
CACHE = CACHE_DIR / "sfx"
CACHE.mkdir(parents=True, exist_ok=True)
VERSION = "v1"
TWO_PI = 2 * math.pi
EXTS = (".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".opus")


class SoundError(Exception):
    pass


def gender_of(voice_id: str) -> str:
    return next((v.get("gender", "male") for v in VOICES if v["id"] == voice_id), "male")


# ----------------------------------------------------------------- synthesis building blocks
class _Res:
    """A two-pole resonator: one formant (a resonance of the vocal tract)."""

    def __init__(self):
        self.y1 = self.y2 = 0.0
        self.a1 = self.a2 = self.g = 0.0

    def tune(self, f: float, bw: float):
        r = math.exp(-math.pi * bw / RATE)
        self.a1, self.a2, self.g = 2 * r * math.cos(TWO_PI * f / RATE), -r * r, 1 - r

    def run(self, x: float) -> float:
        y = self.g * x + self.a1 * self.y1 + self.a2 * self.y2
        self.y2, self.y1 = self.y1, y
        return y


def _fn(x):
    return x if callable(x) else (lambda t, v=x: v)


def synth(dur, f0, amp, form, breath=0.1, voiced=1.0, rough=0.0, rough_hz=60.0, drive=0.0, seed=1):
    """Make `dur` seconds of sound. f0, amp, breath, voiced, rough take a number or a function of time.
    form(t) -> list of (frequency, bandwidth, gain) formants."""
    f0, amp, breath, voiced, rough = map(_fn, (f0, amp, breath, voiced, rough))
    rnd = random.Random(seed)
    n = int(dur * RATE)
    out = [0.0] * n
    res = [_Res() for _ in range(4)]
    gains = [0.0] * 4
    phase = lp = 0.0
    for i in range(n):
        t = i / RATE
        if i % 32 == 0:
            for k, (r, (f, bw, g)) in enumerate(zip(res, form(t))):
                r.tune(f, bw)
                gains[k] = g
        a = amp(t)
        if a <= 1e-4:
            continue
        phase += f0(t) / RATE
        phase -= int(phase)
        lp += 0.35 * ((2 * phase - 1) - lp)                      # buzzing source, softened
        b = breath(t)
        e = voiced(t) * (1 - b) * lp + b * rnd.uniform(-1, 1) * 0.7
        rg = rough(t)
        if rg:
            e *= 1 - rg * (0.5 + 0.5 * math.sin(TWO_PI * rough_hz * t))
        y = 0.0
        for r, g in zip(res, gains):
            if g:
                y += g * r.run(e)
        out[i] = y * a
    if drive:
        out = [math.tanh(drive * v) / math.tanh(drive) for v in out]
    return out


def _vowel(f, scale, shape):
    return [(fr * scale * (f(t) if callable(f) else 1.0), bw, g) for fr, bw, g in shape]


A = [(800, 90, 1.0), (1250, 110, 0.6), (2650, 160, 0.35), (3300, 200, 0.2)]
I = [(320, 70, 1.0), (2250, 120, 0.7), (3010, 150, 0.5), (3800, 200, 0.2)]
O = [(450, 80, 1.0), (850, 90, 0.7), (2400, 150, 0.25), (3200, 200, 0.1)]
UH = [(620, 90, 1.0), (1050, 100, 0.6), (2500, 150, 0.3), (3300, 200, 0.15)]
NASAL = [(250, 60, 1.0), (1000, 120, 0.4), (2300, 200, 0.2), (3100, 250, 0.1)]
HISS = [(900, 500, 0.6), (1900, 700, 0.8), (3200, 900, 0.6), (4500, 1200, 0.3)]


def _glide(t, t0, t1, a, b):
    if t <= t0:
        return a
    if t >= t1:
        return b
    return a + (b - a) * (t - t0) / (t1 - t0)


def _adsr(t, att, hold_to, dec, total):
    if t < att:
        return t / att
    if t < hold_to:
        return 1.0
    return max(0.0, 1.0 - (t - hold_to) / max(dec, 1e-3)) if t < total else 0.0


# ----------------------------------------------------------------- the sounds
def _laugh(sc):
    bursts, period = 5, 0.19
    def amp(t):
        k = int(t / period)
        if k >= bursts:
            return 0.0
        tt = t - k * period
        return min(1.0, tt / 0.012) * math.exp(-max(0.0, tt - 0.03) / 0.07) * (1 - 0.1 * k)
    def f0(t):
        k, tt = int(t / period), t % period
        return sc["f0"] * (1.35 - 0.04 * k) * (1 - 0.14 * min(tt, 0.14) / 0.14)
    def breath(t):
        return 0.6 if (t % period) < 0.03 else 0.3
    return synth(bursts * period + 0.1, f0, amp, lambda t: _vowel(None, sc["fs"], A), breath=breath)


def _giggle(sc):
    bursts, period = 7, 0.115
    def amp(t):
        k = int(t / period)
        if k >= bursts:
            return 0.0
        tt = t - k * period
        return min(1.0, tt / 0.008) * math.exp(-max(0.0, tt - 0.02) / 0.04) * (1 - 0.07 * k)
    def f0(t):
        k = int(t / period)
        return sc["f0"] * 1.5 * (1 + 0.03 * math.sin(k * 1.7))
    return synth(bursts * period + 0.05, f0, amp, lambda t: _vowel(None, sc["fs"], I), breath=0.3)


def _cry(sc):
    cyc = 0.78
    def ph(t):
        return t % cyc
    def amp(t):
        if int(t / cyc) >= 3:
            return 0.0
        p = ph(t)
        if p < 0.2:
            return 0.25 * (p / 0.2)                              # the breath in
        q = p - 0.2
        return min(1.0, q / 0.03) * math.exp(-max(0.0, q - 0.1) / 0.28) * (1.0 - 0.15 * int(t / cyc))
    def voiced(t):
        return 0.0 if ph(t) < 0.2 else 1.0
    def f0(t):
        q = max(0.0, ph(t) - 0.2)
        return sc["f0"] * (1.3 - 0.35 * min(q, 0.4) / 0.4) * (1 + 0.07 * math.sin(TWO_PI * 9 * t))
    return synth(3 * cyc, f0, amp, lambda t: _vowel(None, sc["fs"], A), breath=lambda t: 0.9 if ph(t) < 0.2 else 0.2,
                 voiced=voiced)


def _angry(sc):
    total = 1.05
    return synth(total, lambda t: sc["f0"] * 0.8 * (1 + 0.05 * math.sin(TWO_PI * 3 * t)),
                 lambda t: _adsr(t, 0.05, 0.72, 0.3, total), lambda t: _vowel(None, sc["fs"], O),
                 breath=0.3, rough=0.85, rough_hz=48, drive=2.5)


def _frustrated(sc):
    total = 1.3
    def amp(t):
        return _adsr(t, 0.08, 0.8, 0.5, total)
    return synth(total, lambda t: sc["f0"] * _glide(t, 0.0, 1.1, 1.05, 0.78), amp,
                 lambda t: _vowel(None, sc["fs"], UH), breath=lambda t: 0.2 + 0.5 * max(0.0, (t - 0.9) / 0.4),
                 rough=lambda t: 0.4 * max(0.0, (t - 0.6) / 0.6), rough_hz=35, drive=1.4)


def _sigh(sc):
    total = 1.6
    def amp(t):
        return min(1.0, t / 0.3) * math.exp(-max(0.0, t - 0.3) / 0.55)
    return synth(total, lambda t: sc["f0"] * _glide(t, 0.0, 1.0, 0.9, 0.72), amp,
                 lambda t: _vowel(None, sc["fs"], HISS), breath=0.85,
                 voiced=lambda t: 0.25 if t < 0.7 else 0.0)


def _gasp(sc):
    total = 0.6
    def amp(t):
        if t < 0.3:
            return min(1.0, t / 0.03) * math.exp(-max(0.0, t - 0.1) / 0.14)
        return 0.45 * math.exp(-(t - 0.3) / 0.12)
    def form(t):
        k = _glide(t, 0.0, 0.3, 0.8, 1.35)
        return [(f * k, bw, g) for f, bw, g in HISS]
    return synth(total, lambda t: sc["f0"] * 1.4, amp, form, breath=lambda t: 0.95 if t < 0.3 else 0.5,
                 voiced=lambda t: 0.0 if t < 0.3 else 1.0)


def _scream(sc):
    total = 1.3
    def f0(t):
        base = sc["f0"] * 2.4 * _glide(t, 0.0, 0.25, 0.85, 1.1) * _glide(t, 0.8, 1.3, 1.0, 0.8)
        return min(1100.0, base * (1 + 0.04 * math.sin(TWO_PI * 6.5 * t)))
    return synth(total, f0, lambda t: _adsr(t, 0.04, 1.05, 0.25, total),
                 lambda t: [(f * sc["fs"] * 1.05, bw * 1.6, g) for f, bw, g in A], breath=0.15, rough=0.5,
                 rough_hz=70, drive=2.0)


def _yawn(sc):
    total = 2.4
    def f0(t):
        return sc["f0"] * (_glide(t, 0.0, 0.9, 0.9, 1.15) if t < 0.9 else _glide(t, 0.9, 2.2, 1.15, 0.7))
    def amp(t):
        return math.sin(math.pi * min(1.0, t / total)) ** 1.5
    def form(t):
        k = _glide(t, 0.0, 1.0, 0.85, 1.0) * _glide(t, 1.2, 2.3, 1.0, 0.85)
        return [(fr * sc["fs"] * k, bw, g) for fr, bw, g in A]
    return synth(total, f0, amp, form, breath=lambda t: 0.45 + 0.4 * max(0.0, (t - 1.8) / 0.6))


def _hmm(sc):
    total = 0.9
    def amp(t):
        return min(1.0, t / 0.08) * (1.0 - 0.7 * max(0.0, (t - 0.7) / 0.2))
    return synth(total, lambda t: sc["f0"] * _glide(t, 0.0, 0.8, 0.95, 1.2) * (1 + 0.02 * math.sin(TWO_PI * 5 * t)),
                 amp, lambda t: [(fr * sc["fs"], bw, g) for fr, bw, g in NASAL], breath=0.12)


MAKERS = {"laugh": _laugh, "giggle": _giggle, "cry": _cry, "angry": _angry, "frustrated": _frustrated,
          "sigh": _sigh, "gasp": _gasp, "scream": _scream, "yawn": _yawn, "hmm": _hmm}
VOICE_SHAPE = {"male": dict(f0=112.0, fs=1.0), "female": dict(f0=205.0, fs=1.17)}


def _write_wav(path: Path, samples: list, peak: float = 0.8):
    top = max((abs(v) for v in samples), default=0.0) or 1.0
    k = peak / top
    fade = int(0.008 * RATE)
    n = len(samples)
    data = array.array("h")
    for i, v in enumerate(samples):
        f = min(1.0, i / fade, (n - 1 - i) / fade) if fade else 1.0
        data.append(int(max(-1.0, min(1.0, v * k * f)) * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def _synth_cached(sound_id: str, gender: str) -> Path:
    path = CACHE / f"{VERSION}_{sound_id}_{gender}.wav"
    if not path.exists():
        _write_wav(path, MAKERS[sound_id](VOICE_SHAPE.get(gender, VOICE_SHAPE["male"])))
    return path


def _user_file(sound_id: str, gender: str) -> Path | None:
    for stem in (f"{sound_id}_{gender}", sound_id):
        for ext in EXTS:
            p = SOUNDS_DIR / f"{stem}{ext}"
            if p.exists():
                return p
    return None


def _convert(user: Path) -> Path:
    key = hashlib.sha1(f"{user}|{user.stat().st_size}|{user.stat().st_mtime_ns}".encode()).hexdigest()[:16]
    out = CACHE / f"user_{key}.wav"
    if not out.exists():
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            raise SoundError("FFmpeg was not found, so your own sound files cannot be read. Install it (see README).")
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(user), "-vn", "-t", "10", "-ar", str(RATE),
                            "-ac", "1", "-c:a", "pcm_s16le", str(out)], capture_output=True)
        if r.returncode != 0 or not out.exists():
            raise SoundError(f"Could not read your sound file {user.name}.")
    return out


def get_sound(sound_id: str, voice: str) -> Clip:
    if sound_id not in SOUND_LABELS:
        raise SoundError("Unknown sound.")
    from .catalog import FX_SOUNDS
    if sound_id in FX_SOUNDS:                     # a sound effect, not a voice: the mouth stays still
        from .fx import fx_wav
        wav = fx_wav(sound_id)
        s = read_samples(wav)
        return Clip(wav, len(s) / RATE, [0.0] * (len(s) * 50 // RATE + 1))
    gender = gender_of(voice)
    user = _user_file(sound_id, gender)
    wav = _convert(user) if user else _synth_cached(sound_id, gender)
    s = read_samples(wav)
    return Clip(wav, len(s) / RATE, compute_env(s))
