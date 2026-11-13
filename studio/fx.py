"""Sound effects and built-in background music, all synthesized here (no files, no internet, no copyright issues).

Effects   punch, slap, whoosh, pop, ding, boing, thud: short sounds for impacts, scene changes and comedy beats.
          A line can play one (the "sound" menu), punch and slap actions play their hit automatically, and every
          scene change plays a whoosh.
Music     a few short loops (happy, comedy, suspense, emotional, heaven, hell) that FFmpeg repeats under the video.

Your own recordings win: put e.g. assets/sounds/punch.mp3 or assets/music/happy.mp3 in place to use them instead.
Everything made here is cached in data/cache/fx.
"""
from __future__ import annotations

import array
import math
import random
import subprocess
import wave
from pathlib import Path

from .config import ASSETS_DIR, CACHE_DIR, find_ffmpeg

RATE = 22050
CACHE = CACHE_DIR / "fx"
VERSION = "v1"
TWO_PI = 2 * math.pi

FX_LABELS = {"punch": "Punch hit (effect)", "slap": "Slap (effect)", "whoosh": "Whoosh (effect)",
             "pop": "Pop (effect)", "ding": "Ding, idea! (effect)", "boing": "Boing, comedy (effect)",
             "thud": "Thud, fall (effect)"}
MUSIC_LABELS = {"happy": "Happy (ukulele-style)", "comedy": "Comedy (bouncy)", "suspense": "Suspense",
                "emotional": "Emotional (slow)", "heaven": "Heavenly (Swarg)", "hell": "Dark drums (Nark)"}

# when a punch or slap action lands (seconds after the line starts, repeating): matches the 3D and flat poses
HIT_PERIOD = {"punch": 1 / 2.4, "slap": 1 / 1.3}
HIT_OFFSET = {"punch": 0.0, "slap": 0.45 / 1.3}


# ----------------------------------------------------------------- helpers
def _write(path: Path, samples, peak=0.85):
    top = max((abs(v) for v in samples), default=0.0) or 1.0
    k = peak / top
    data = array.array("h", (int(max(-1.0, min(1.0, v * k)) * 32767) for v in samples))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def _lowpass(x, a):
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def _user(folder: str, stem: str) -> Path | None:
    for ext in (".wav", ".mp3", ".ogg", ".m4a", ".flac"):
        p = ASSETS_DIR / folder / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def _convert(src: Path, out: Path, seconds: float | None = None) -> Path:
    ffmpeg = find_ffmpeg()
    if ffmpeg and (not out.exists() or out.stat().st_mtime < src.stat().st_mtime):
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-vn"]
        if seconds:
            cmd += ["-t", str(seconds)]
        subprocess.run(cmd + ["-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", str(out)], capture_output=True)
    return out


# ----------------------------------------------------------------- effects
def _punch():
    n, rnd, out, ph = int(0.32 * RATE), random.Random(1), [], 0.0
    for i in range(n):
        t = i / RATE
        ph += (55 + 90 * math.exp(-t * 30)) / RATE
        body = math.sin(TWO_PI * ph) * math.exp(-t * 14)
        click = rnd.uniform(-1, 1) * math.exp(-t * 90) * 0.8
        out.append(body + click)
    return [math.tanh(2.2 * v) for v in _lowpass(out, 0.5)]


def _slap():
    n, rnd, out = int(0.22 * RATE), random.Random(2), []
    prev = 0.0
    for i in range(n):
        t = i / RATE
        v = rnd.uniform(-1, 1)
        hp = v - prev                                     # bright crack
        prev = v
        out.append(hp * math.exp(-t * 45) + 0.4 * math.sin(TWO_PI * 1700 * t) * math.exp(-t * 70))
    return out


def _whoosh():
    n, rnd = int(0.45 * RATE), random.Random(3)
    y1 = y2 = 0.0
    out = []
    for i in range(n):
        t = i / RATE
        u = t / 0.45
        f = 300 + 2600 * math.sin(math.pi * u) ** 2
        r = 0.97
        a1, a2 = 2 * r * math.cos(TWO_PI * f / RATE), -r * r
        y = (1 - r) * rnd.uniform(-1, 1) + a1 * y1 + a2 * y2
        y2, y1 = y1, y
        out.append(y * math.sin(math.pi * u) ** 1.5)
    return out


def _pop():
    n = int(0.09 * RATE)
    ph, out = 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (500 + 9000 * t) / RATE
        out.append(math.sin(TWO_PI * ph) * math.exp(-t * 45))
    return out


def _ding():
    n = int(1.4 * RATE)
    return [sum(g * math.sin(TWO_PI * f * i / RATE) * math.exp(-(i / RATE) * d)
                for f, g, d in ((1318, 1.0, 3.0), (2636, 0.45, 5.0), (3954, 0.2, 8.0), (1975, 0.25, 4.0)))
            for i in range(n)]


def _boing():
    n, ph, out = int(0.7 * RATE), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (180 + 140 * math.sin(TWO_PI * 11 * t) * math.exp(-t * 3) + 60 * t) / RATE
        out.append(math.sin(TWO_PI * ph) * math.exp(-t * 3.5))
    return out


def _thud():
    n, rnd, ph, out = int(0.5 * RATE), random.Random(4), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (45 + 40 * math.exp(-t * 20)) / RATE
        out.append(math.sin(TWO_PI * ph) * math.exp(-t * 8) + rnd.uniform(-1, 1) * math.exp(-t * 40) * 0.5)
    return _lowpass(out, 0.3)


MAKERS = {"punch": _punch, "slap": _slap, "whoosh": _whoosh, "pop": _pop, "ding": _ding, "boing": _boing,
          "thud": _thud}


def fx_wav(fx_id: str) -> Path:
    """The WAV file of an effect (your own assets/sounds/<id>.* if present)."""
    user = _user("sounds", fx_id)
    if user:
        return _convert(user, CACHE / f"user_{fx_id}.wav", 5)
    path = CACHE / f"{VERSION}_{fx_id}.wav"
    if not path.exists():
        _write(path, MAKERS[fx_id]())
    return path


# ----------------------------------------------------------------- music
def _note(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _pluck(buf, start, freq, dur, amp, decay=0.996, seed=0):
    """Karplus-Strong string: a soft guitar / ukulele-like note."""
    period = max(2, int(RATE / freq))
    rnd = random.Random(seed)
    ring = [rnd.uniform(-1, 1) for _ in range(period)]
    n = min(int(dur * RATE), len(buf) - start)
    for i in range(n):
        j = i % period
        v = ring[j]
        ring[j] = decay * 0.5 * (v + ring[(j + 1) % period])
        buf[start + i] += v * amp


def _tone(buf, start, freq, dur, amp, attack=0.01, release=0.2, wave_="sine", trem=0.0):
    n = min(int(dur * RATE), len(buf) - start)
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / attack) * min(1.0, (dur - t) / release)
        ph = (freq * t) % 1.0
        v = math.sin(TWO_PI * ph) if wave_ == "sine" else (4 * abs(ph - 0.5) - 1)
        if trem:
            v *= 1 - trem * (0.5 + 0.5 * math.sin(TWO_PI * 5 * t))
        buf[start + i] += v * env * amp


def _kick(buf, start, amp=0.9):
    ph = 0.0
    for i in range(min(int(0.25 * RATE), len(buf) - start)):
        t = i / RATE
        ph += (50 + 110 * math.exp(-t * 35)) / RATE
        buf[start + i] += math.sin(TWO_PI * ph) * math.exp(-t * 16) * amp


def _hat(buf, start, amp=0.15, seed=0):
    rnd, prev = random.Random(seed), 0.0
    for i in range(min(int(0.05 * RATE), len(buf) - start)):
        v = rnd.uniform(-1, 1)
        buf[start + i] += (v - prev) * math.exp(-i / RATE * 90) * amp
        prev = v


def _music(mid: str):
    spec = {   # bpm, chords (root midi, minor?), style
        "happy": (112, [(60, 0), (67, 0), (69, 1), (65, 0)], "pluck"),
        "comedy": (128, [(65, 0), (60, 0), (65, 0), (60, 0)], "oompah"),
        "suspense": (88, [(57, 1), (57, 1), (58, 0), (56, 0)], "suspense"),
        "emotional": (70, [(57, 1), (65, 0), (60, 0), (67, 0)], "pluck_slow"),
        "heaven": (64, [(60, 0), (65, 0), (57, 1), (67, 0)], "pad"),
        "hell": (80, [(40, 1), (40, 1), (41, 0), (39, 0)], "drums"),
    }[mid]
    bpm, chords, style = spec
    beat = 60.0 / bpm
    bars = 8
    total = bars * 4 * beat
    buf = [0.0] * int(total * RATE + RATE)
    rnd = random.Random(hash(mid) & 0xFFFF)
    for bar in range(bars):
        root, minor = chords[bar % len(chords)]
        triad = [root, root + (3 if minor else 4), root + 7]
        t0 = bar * 4 * beat
        if style in ("pluck", "pluck_slow"):
            pattern = [0, 1, 2, 1, 0, 2, 1, 2] if style == "pluck" else [0, 1, 2, 1]
            step = 4 * beat / len(pattern)
            for k, p in enumerate(pattern):
                _pluck(buf, int((t0 + k * step) * RATE), _note(triad[p] + 12), step * 2.5, 0.35,
                       0.997 if style == "pluck" else 0.999, seed=bar * 10 + k)
            _tone(buf, int(t0 * RATE), _note(root - 12), 4 * beat * 0.95, 0.25, 0.02, 0.3, "tri")
            if style == "pluck":
                for b in range(4):
                    _kick(buf, int((t0 + b * beat) * RATE), 0.45 if b % 2 == 0 else 0.0)
                    _hat(buf, int((t0 + (b + 0.5) * beat) * RATE), 0.12, seed=bar * 4 + b)
        elif style == "oompah":
            for b in range(4):
                bass = root - 12 if b % 2 == 0 else root - 5
                _tone(buf, int((t0 + b * beat) * RATE), _note(bass), beat * 0.45, 0.45, 0.005, 0.08, "tri")
                for nn in triad:
                    _pluck(buf, int((t0 + (b + 0.5) * beat) * RATE), _note(nn + 12), beat * 0.4, 0.13, 0.99, seed=b)
            if bar % 2 == 1:
                _pluck(buf, int((t0 + 3.5 * beat) * RATE), _note(root + 24), beat, 0.25, 0.995, seed=bar)
        elif style == "suspense":
            _tone(buf, int(t0 * RATE), _note(root - 12), 4 * beat, 0.35, 0.4, 0.4, "sine", trem=0.4)
            for b in range(8):
                _tone(buf, int((t0 + b * beat / 2) * RATE), _note(root + 12 + (1 if b % 4 == 3 else 0)),
                      beat * 0.2, 0.12, 0.005, 0.1, "tri")
            if bar % 2 == 1:
                _tone(buf, int((t0 + 2 * beat) * RATE), _note(root + 25), 2 * beat, 0.07, 0.5, 0.8)
        elif style == "pad":
            for nn in triad + [root + 12]:
                _tone(buf, int(t0 * RATE), _note(nn), 4 * beat + 0.3, 0.12, 0.8, 0.8, "sine", trem=0.2)
            for k in range(3):
                tt = t0 + rnd.uniform(0, 4 * beat)
                _tone(buf, int(tt * RATE), _note(rnd.choice(triad) + 24), 1.2, 0.06, 0.005, 1.1)
        elif style == "drums":
            _tone(buf, int(t0 * RATE), _note(root), 4 * beat, 0.3, 0.3, 0.3, "tri", trem=0.3)
            for b, a in ((0, 1.0), (1.5, 0.6), (2, 0.9), (3, 0.5), (3.5, 0.7)):
                _kick(buf, int((t0 + b * beat) * RATE), a)
    n = int(total * RATE)
    tail = buf[n:]                                       # wrap the ringing tail to the start: a seamless loop
    out = buf[:n]
    for i, v in enumerate(tail):
        out[i] += v
    return [math.tanh(1.3 * v) for v in out]


def music_wav(mid: str) -> Path:
    """The WAV loop of a built-in music track (your own assets/music/<id>.* if present)."""
    user = _user("music", mid)
    if user:
        return _convert(user, CACHE / f"user_music_{mid}.wav")
    path = CACHE / f"{VERSION}_music_{mid}.wav"
    if not path.exists():
        _write(path, _music(mid), 0.8)
    return path


# ----------------------------------------------------------------- the effects track of a video
def hit_times(action: str, start: float, end: float) -> list[float]:
    """When a punch or slap lands during a line (start..end, seconds in the video)."""
    if action not in HIT_PERIOD:
        return []
    out, k = [], 0
    while True:
        t = start + HIT_OFFSET[action] + k * HIT_PERIOD[action]
        if t >= end - 0.05:
            return out
        out.append(t)
        k += 1


def build_track(events: list, total: float, path: Path):
    """events: [(time in seconds, fx id, volume)]; writes one mono WAV with all of them mixed."""
    n = int((total + 1.0) * RATE)
    buf = array.array("h", [0]) * n
    cache: dict = {}
    for t, fid, vol in events:
        if fid not in cache:
            with wave.open(str(fx_wav(fid)), "rb") as w:
                s = array.array("h")
                s.frombytes(w.readframes(w.getnframes()))
                cache[fid] = s
        s, off = cache[fid], int(t * RATE)
        for i in range(min(len(s), n - off)):
            if off + i < 0:
                continue
            v = buf[off + i] + int(s[i] * vol)
            buf[off + i] = 32767 if v > 32767 else -32768 if v < -32768 else v
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())
