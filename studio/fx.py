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
             "thud": "Thud, fall (effect)", "growl": "Stomach growl (effect)",
             "ping": "Phone notification (effect)", "doorbell": "Doorbell ting-tong (effect)",
             "chappal": "Chappal smack (effect)", "laugh_track": "Audience laughing (effect)",
             "boom": "Meme boom (effect)", "dun_dun": "Dun dun duuun (effect)", "click": "Light switch click (effect)",
             "tick": "Clock ticking (effect)", "scratch": "Record scratch (effect)",
             "sizzle": "Oil sizzling, chhann (effect)", "fire": "Fire flaring up (effect)",
             "splash": "Water splash (effect)", "footsteps": "Running footsteps (effect)",
             "clang": "Metal clang, thali (effect)",
             "slip": "Cartoon slip, wheee (effect)", "slide_up": "Slide whistle up (effect)",
             "slide_down": "Slide whistle down, falling (effect)", "zip": "Cartoon zip, fast run (effect)",
             "bonk": "Bonk on the head (effect)", "tweet": "Dizzy birds tweeting (effect)",
             "crash": "Crash, smash (effect)", "glass_break": "Glass breaking (effect)",
             "crickets": "Crickets, awkward silence (effect)", "wah_wah": "Sad trombone, wah wah waaah (effect)",
             "tiptoe": "Sneaky tiptoe music (effect)", "awooga": "Awooga horn, eyes pop (effect)",
             "spring": "Spring boing, doing (effect)", "fight": "Cartoon fight cloud (effect)",
             "alarm": "Alarm clock ringing (effect)", "buzz": "Fly buzzing (effect)", "snore": "Snoring (effect)",
             "boop": "Poke, boop (effect)", "rustle": "Rustling, something moving inside (effect)"}
MUSIC_LABELS = {"happy": "Happy (ukulele-style)", "comedy": "Comedy (bouncy)", "suspense": "Suspense",
                "emotional": "Emotional (slow)", "heaven": "Heavenly (Swarg)", "hell": "Dark drums (Nark)",
                "panic": "Panic (fast, tense)", "calm": "Calm, explaining (soft)"}

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


def _growl():
    """Stomach growl: an irregular low buzz whose resonance slides up and down (gurgle), in two bursts."""
    n, rnd = int(1.6 * RATE), random.Random(5)
    out, ph = [], 0.0
    y1 = y2 = 0.0
    for i in range(n):
        t = i / RATE
        burst = max(0.0, math.sin(math.pi * min(1.0, t / 0.7))) if t < 0.7 else \
            0.8 * max(0.0, math.sin(math.pi * min(1.0, (t - 0.8) / 0.8))) if t > 0.8 else 0.0
        f0 = 55 + 25 * math.sin(TWO_PI * 1.3 * t) + 10 * math.sin(TWO_PI * 7 * t)
        ph += f0 / RATE * (1 + 0.3 * rnd.uniform(-1, 1))
        src = (2 * (ph % 1.0) - 1) + 0.3 * rnd.uniform(-1, 1)
        fr = 180 + 220 * (0.5 + 0.5 * math.sin(TWO_PI * 2.2 * t + math.sin(TWO_PI * 0.7 * t) * 2))
        r = 0.985
        a1, a2 = 2 * r * math.cos(TWO_PI * fr / RATE), -r * r
        y = (1 - r) * src + a1 * y1 + a2 * y2
        y2, y1 = y1, y
        out.append(y * burst)
    return [math.tanh(3 * v) for v in out]



def _ping():
    """Phone notification: two quick chimes."""
    n = int(0.6 * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        a = math.sin(TWO_PI * 1568 * t) * math.exp(-t * 14) if t < 0.3 else 0.0
        b = math.sin(TWO_PI * 2093 * (t - 0.11)) * math.exp(-(t - 0.11) * 9) if t >= 0.11 else 0.0
        out.append(a + 0.9 * b + 0.2 * math.sin(TWO_PI * 4186 * t) * math.exp(-t * 30))
    return out


def _bell(t, f):
    return sum(g * math.sin(TWO_PI * f * m * t) * math.exp(-t * d) for m, g, d in ((1, 1.0, 2.2), (2.0, 0.4, 3.5),
                                                                                   (3.01, 0.22, 5.0), (4.2, 0.1, 7.0)))


def _doorbell():
    """Ting-tong."""
    n = int(2.0 * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        v = _bell(t, 659) if t < 0.75 else _bell(t, 659) * 0.3
        if t >= 0.6:
            v += _bell(t - 0.6, 523)
        out.append(v)
    return out


def _chappal():
    """Slipper smack: a flat slap with some body."""
    n, rnd, out, ph = int(0.35 * RATE), random.Random(6), [], 0.0
    lp = 0.0
    for i in range(n):
        t = i / RATE
        v = rnd.uniform(-1, 1)
        lp += 0.45 * (v - lp)
        ph += (110 + 80 * math.exp(-t * 40)) / RATE
        out.append(lp * math.exp(-t * 35) * 1.4 + 0.7 * math.sin(TWO_PI * ph) * math.exp(-t * 20))
    return out


def _gemini_laughs() -> list:
    """Real-sounding laughs: four Gemini voices laughing (made once and saved; uses 4 free Gemini voice lines)."""
    from .gemini_tts import synthesize, ready
    if not ready():
        return []
    out = []
    for name, text in (("Puck", "[laughing] हा हा हा हा हा!"), ("Kore", "[laughing] ही ही ही ही!"),
                       ("Fenrir", "[laughing] हा हा हा, हो हो!"), ("Leda", "[laughing] हा हा हा हा!")):
        path = CACHE / f"laugh_{name}.wav"
        try:
            if not path.exists():
                synthesize(text, name, "laughing", path, RATE)
            with wave.open(str(path), "rb") as w:
                a = array.array("h")
                a.frombytes(w.readframes(w.getnframes()))
                out.append([v / 32768 for v in a])
        except Exception:  # noqa: BLE001  no key / limit used up: the synthesized laughs below are used
            continue
    return out


def _laugh_track():
    """A small studio audience laughing: many laughs, each a little higher or lower, mixed over a murmur."""
    src = _gemini_laughs()
    if len(src) < 2:
        from .sfx import _synth_cached
        src = []
        for g in ("male", "female"):
            with wave.open(str(_synth_cached("laugh", g)), "rb") as w:
                a = array.array("h")
                a.frombytes(w.readframes(w.getnframes()))
                src.append([v / 32768 for v in a])
    n, rnd = int(3.2 * RATE), random.Random(7)
    out = [0.0] * n
    for k in range(10 if len(src) > 2 else 14):
        s = src[k % len(src)]
        rate = rnd.uniform(0.9, 1.12) if len(src) > 2 else rnd.uniform(0.82, 1.25)
        off = int(rnd.uniform(0.0, 0.9) * RATE)
        amp = rnd.uniform(0.35, 0.8)
        j = 0.0
        while int(j) < len(s) - 1 and off < n:
            out[off] += s[int(j)] * amp
            j += rate
            off += 1
    lp = 0.0
    for i in range(n):                                    # crowd murmur
        t = i / RATE
        lp += 0.08 * (rnd.uniform(-1, 1) - lp)
        out[i] += lp * 0.9 * min(1.0, t / 0.3) * min(1.0, (3.2 - t) / 1.2)
    fade = int(1.0 * RATE)
    for i in range(n - fade, n):
        out[i] *= (n - i) / fade
    return out


def _boom():
    """'Vine boom' meme hit: a deep boom with a long tail."""
    n, ph, out = int(1.6 * RATE), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (48 + 30 * math.exp(-t * 12)) / RATE
        out.append(math.sin(TWO_PI * ph) * math.exp(-t * 2.6) * min(1.0, t / 0.005))
    echo = int(0.11 * RATE)
    for i in range(echo, n):
        out[i] += 0.35 * out[i - echo]
    return [math.tanh(2.5 * v) for v in out]


def _dun_dun():
    """Dramatic 'dun dun duuun' sting."""
    n = int(2.4 * RATE)
    out = [0.0] * n
    for start, f, dur in ((0.0, 147, 0.32), (0.4, 147, 0.32), (0.85, 139, 1.5)):
        ph = 0.0
        lp = 0.0
        for i in range(int(start * RATE), min(n, int((start + dur) * RATE))):
            t = i / RATE - start
            ph += f / RATE
            saw = 2 * (ph % 1.0) - 1
            lp += 0.15 * (saw - lp)
            out[i] += lp * min(1.0, t / 0.02) * min(1.0, (dur - t) / 0.15)
    return out


def _click():
    n, rnd = int(0.08 * RATE), random.Random(8)
    return [(rnd.uniform(-1, 1) * math.exp(-(i / RATE) * 250) + 0.6 * math.sin(TWO_PI * 2400 * i / RATE)
             * math.exp(-(i / RATE) * 120)) for i in range(n)]


def _tick():
    """Clock ticking (for a 'later...' card)."""
    n = int(2.0 * RATE)
    out = [0.0] * n
    for k in range(4):
        s = int((0.05 + k * 0.5) * RATE)
        f = 3000 if k % 2 == 0 else 2500
        for i in range(int(0.04 * RATE)):
            if s + i < n:
                out[s + i] += math.sin(TWO_PI * f * i / RATE) * math.exp(-(i / RATE) * 120)
    return out


def _scratch():
    """Record scratch."""
    n, rnd, out = int(0.6 * RATE), random.Random(9), []
    y1 = y2 = 0.0
    for i in range(n):
        t = i / RATE
        f = 600 + 2200 * abs(math.sin(TWO_PI * 2.5 * t))
        r = 0.96
        a1, a2 = 2 * r * math.cos(TWO_PI * f / RATE), -r * r
        y = (1 - r) * rnd.uniform(-1, 1) + a1 * y1 + a2 * y2
        y2, y1 = y1, y
        out.append(y * math.exp(-t * 3))
    return out


def _sizzle():
    """Hot oil frying (chhann): bright hissing noise full of tiny crackles."""
    n, rnd, out = int(3.0 * RATE), random.Random(10), []
    prev = lp = 0.0
    for i in range(n):
        t = i / RATE
        v = rnd.uniform(-1, 1)
        hp = v - prev                                      # hiss
        prev = v
        lp += 0.5 * (hp - lp)
        crack = rnd.uniform(-1, 1) * 3.0 if rnd.random() < 0.004 else 0.0
        env = min(1.0, t / 0.08) * (0.75 + 0.25 * math.sin(TWO_PI * 0.9 * t)) * min(1.0, (3.0 - t) / 0.5)
        out.append((lp * 0.6 + crack) * env)
    return out


def _fire():
    """Oil catching fire: a deep 'whoomp', then a roaring, crackling fire."""
    n, rnd, out = int(2.8 * RATE), random.Random(11), []
    lp = lp2 = ph = 0.0
    for i in range(n):
        t = i / RATE
        v = rnd.uniform(-1, 1)
        lp += 0.06 * (v - lp)                              # low roar
        lp2 += 0.3 * (v - lp2)
        ph += (40 + 70 * math.exp(-t * 9)) / RATE
        whoomp = math.sin(TWO_PI * ph) * math.exp(-t * 5) * 1.4
        roar = (lp * 3.0 + lp2 * 0.35) * min(1.0, t / 0.12) * (0.8 + 0.2 * math.sin(TWO_PI * 3.1 * t))
        crack = rnd.uniform(-1, 1) * 2.2 if rnd.random() < 0.0025 else 0.0
        out.append((whoomp + roar + crack) * min(1.0, (2.8 - t) / 0.8))
    return [math.tanh(1.6 * v) for v in out]


def _splash():
    """Water slopping out of a jug: a noisy splash with a falling 'blub', then drops."""
    n, rnd, out = int(1.0 * RATE), random.Random(12), []
    y1 = y2 = 0.0
    for i in range(n):
        t = i / RATE
        f = 1800 - 1300 * min(1.0, t / 0.35)
        r = 0.93
        a1, a2 = 2 * r * math.cos(TWO_PI * f / RATE), -r * r
        y = (1 - r) * rnd.uniform(-1, 1) * 6 + a1 * y1 + a2 * y2
        y2, y1 = y1, y
        drops = sum(math.sin(TWO_PI * (900 + 300 * k) * (t - d0)) * math.exp(-(t - d0) * 40)
                    for k, d0 in enumerate((0.42, 0.55, 0.71)) if t >= d0)
        out.append(y * math.exp(-t * 4) + 0.3 * drops)
    return out


def _footsteps():
    """Quick running footsteps on a hard floor."""
    n, rnd = int(1.5 * RATE), random.Random(13)
    out = [0.0] * n
    for k in range(7):
        s0 = int((0.05 + k * 0.19 + rnd.uniform(-0.015, 0.015)) * RATE)
        ph, amp = 0.0, 0.7 + 0.3 * (k % 2)
        for i in range(int(0.12 * RATE)):
            if s0 + i >= n:
                break
            t = i / RATE
            ph += (70 + 60 * math.exp(-t * 60)) / RATE
            out[s0 + i] += amp * (math.sin(TWO_PI * ph) * math.exp(-t * 35) + rnd.uniform(-1, 1) * math.exp(-t * 120) * 0.6)
    return out


def _clang():
    """A steel plate banged onto a kadhai: bright metal ringing."""
    n = int(1.6 * RATE)
    parts = ((523, 1.0, 3.2), (1290, 0.7, 4.0), (2210, 0.5, 5.5), (3170, 0.35, 7.0), (531, 0.6, 3.0), (4410, 0.2, 9))
    rnd = random.Random(14)
    return [sum(g * math.sin(TWO_PI * f * i / RATE) * math.exp(-(i / RATE) * dcy) for f, g, dcy in parts)
            + rnd.uniform(-1, 1) * math.exp(-(i / RATE) * 80) * 0.8 for i in range(n)]


# ----------------------------------------------------------------- cartoon comedy sounds (stickman slapstick)
def _glide(f0, f1, dur, vib=0.0, shape="sine", amp_env=None):
    """A tone sliding from f0 to f1 Hz (a slide whistle when sine with a little vibrato)."""
    n, ph, out = int(dur * RATE), 0.0, []
    for i in range(n):
        u = i / n
        f = f0 * (f1 / f0) ** u
        f *= 1 + vib * math.sin(TWO_PI * 6 * i / RATE)
        ph += f / RATE
        v = math.sin(TWO_PI * ph)
        if shape == "brass":                                  # rich, buzzy (trombone / horn)
            v = sum(math.sin(TWO_PI * ph * h) / h ** 0.8 for h in range(1, 8))
        a = amp_env(u) if amp_env else min(1.0, u * 30) * min(1.0, (1 - u) * 12)
        out.append(v * a)
    return out


def _slide_up():
    return _glide(380, 1500, 0.55, vib=0.012)


def _slide_down():
    return _glide(1500, 300, 0.8, vib=0.012)


def _slip():
    """A banana-peel slip: a quick rising whistle with a squeak."""
    a = _glide(500, 2200, 0.32, vib=0.03)
    rnd = random.Random(21)
    sq = [math.sin(TWO_PI * (2600 + 300 * math.sin(i / 90)) * i / RATE) * math.exp(-i / RATE * 18) * 0.5
          + rnd.uniform(-1, 1) * 0.05 for i in range(int(0.15 * RATE))]
    return sq + a


def _zip():
    """A cartoon zoom-off: a fast rising whoosh with a whistle on top."""
    n, rnd, out, ph = int(0.45 * RATE), random.Random(5), [], 0.0
    y = 0.0
    for i in range(n):
        u = i / n
        y += 0.25 * (rnd.uniform(-1, 1) - y)
        ph += (600 + 2600 * u * u) / RATE
        env = math.sin(math.pi * min(1.0, u * 1.15)) ** 1.5
        out.append(env * (y * 0.9 + 0.45 * math.sin(TWO_PI * ph)))
    return out


def _bonk():
    """A hollow wooden bonk on the head."""
    n, out = int(0.35 * RATE), []
    for i in range(n):
        t = i / RATE
        f = 520 * (1 + 0.6 * math.exp(-t * 40))
        out.append(math.sin(TWO_PI * f * t) * math.exp(-t * 16) + 0.5 * math.sin(TWO_PI * 2.7 * f * t) * math.exp(-t * 40))
    return out


def _tweet():
    """Little birds tweeting around a dizzy head."""
    out = [0.0] * int(1.4 * RATE)
    for k in range(6):
        s0 = int((0.05 + k * 0.21) * RATE)
        n = int(0.12 * RATE)
        ph = 0.0
        for i in range(n):
            u = i / n
            ph += (3200 + 900 * math.sin(math.pi * u) + (k % 2) * 400) / RATE
            out[s0 + i] += math.sin(TWO_PI * ph) * math.sin(math.pi * u) * 0.6
    return out


def _crash():
    """A big smash: a thump plus bright crashing noise and rattling bits."""
    n, rnd, out = int(1.1 * RATE), random.Random(9), []
    y = 0.0
    for i in range(n):
        t = i / RATE
        y += 0.6 * (rnd.uniform(-1, 1) - y)
        boom = math.sin(TWO_PI * (60 + 50 * math.exp(-t * 25)) * t) * math.exp(-t * 9)
        rattle = rnd.uniform(-1, 1) * (math.exp(-t * 4) * 0.4 if rnd.random() < 0.25 else 0)
        out.append(boom + y * math.exp(-t * 6) * 0.8 + rattle)
    return out


def _glass_break():
    rnd, out = random.Random(17), [0.0] * int(1.2 * RATE)
    for k in range(26):                                      # many little glass pieces ringing
        s0 = int(rnd.uniform(0, 0.6) ** 2 * RATE)
        f = rnd.uniform(2500, 7000)
        a = rnd.uniform(0.2, 0.6)
        for i in range(min(int(0.25 * RATE), len(out) - s0)):
            t = i / RATE
            out[s0 + i] += a * math.sin(TWO_PI * f * t) * math.exp(-t * 30)
    for i in range(int(0.2 * RATE)):                         # the first crack
        out[i] += rnd.uniform(-1, 1) * math.exp(-i / RATE * 25)
    return out


def _crickets():
    out = [0.0] * int(2.4 * RATE)
    for k in range(8):
        s0 = int((0.1 + k * 0.3) * RATE)
        for c in range(3):                                   # one chirp = 3 fast pulses
            for i in range(int(0.03 * RATE)):
                j = s0 + int(c * 0.045 * RATE) + i
                if j < len(out):
                    out[j] += math.sin(TWO_PI * 4300 * i / RATE) * math.sin(math.pi * i / (0.03 * RATE)) * 0.5
    return out


def _wah_wah():
    """The sad trombone: wah wah wah waaaah."""
    out = []
    for f, dur, vib in ((311, 0.45, 0.0), (294, 0.45, 0.0), (277, 0.45, 0.0), (262, 1.3, 0.03)):
        out += _glide(f * 1.02, f * 0.97, dur, vib=vib, shape="brass",
                      amp_env=lambda u: min(1.0, u * 8) * (1 - u) ** 0.6)
    return out


def _tiptoe():
    """Sneaky pizzicato steps (plink ... plonk ... plink ...)."""
    out = [0.0] * int(2.6 * RATE)
    notes = (55, 59, 62, 59, 55, 58, 62, 58)
    for k, m in enumerate(notes):
        s0 = int(k * 0.3 * RATE)
        f = _note(m)
        for i in range(int(0.25 * RATE)):
            t = i / RATE
            out[s0 + i] += (math.sin(TWO_PI * f * t) + 0.3 * math.sin(TWO_PI * 2 * f * t)) * math.exp(-t * 18)
    return out


def _awooga():
    """The old car horn: a-WOO-ga."""
    out = _glide(220, 330, 0.4, shape="brass", amp_env=lambda u: min(1.0, u * 10) * (1 - 0.3 * u))
    out += _glide(330, 300, 0.35, shape="brass", amp_env=lambda u: (1 - u) ** 0.5)
    return out


def _spring():
    """A spring: doi-oi-oing."""
    n, ph, out = int(0.8 * RATE), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (260 + 180 * math.sin(TWO_PI * 18 * t) * math.exp(-t * 4)) / RATE
        out.append((math.sin(TWO_PI * ph) + 0.3 * math.sin(TWO_PI * ph * 3.01)) * math.exp(-t * 4))
    return out


def _fight():
    """A cartoon brawl in a dust cloud: punches, slaps and whooshes all mixed up."""
    rnd = random.Random(33)
    out = [0.0] * int(2.4 * RATE)
    parts = [_punch(), _slap(), _boing(), _whoosh(), _bonk()]
    t = 0.0
    while t < 2.1:
        snd = parts[rnd.randrange(len(parts))]
        s0 = int(t * RATE)
        a = rnd.uniform(0.35, 0.7)
        for i in range(min(len(snd), len(out) - s0)):
            out[s0 + i] += snd[i] * a
        t += rnd.uniform(0.09, 0.22)
    return out


def _alarm():
    """An old alarm clock: a hammer rattling between two bells, in bursts."""
    n, out = int(2.4 * RATE), []
    for i in range(n):
        t = i / RATE
        on = (t % 0.6) < 0.45
        hit = (t * 28) % 1.0
        env = math.exp(-hit * 6) if on else 0.0
        v = (math.sin(TWO_PI * 2350 * t) + 0.7 * math.sin(TWO_PI * 3120 * t) + 0.4 * math.sin(TWO_PI * 5400 * t))
        out.append(v * env)
    return out


def _buzz():
    """A fly buzzing around: a raspy hum that swells and fades as it circles."""
    n, ph, out = int(2.2 * RATE), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (210 + 25 * math.sin(TWO_PI * 1.7 * t) + 8 * math.sin(TWO_PI * 23 * t)) / RATE
        saw = 2 * (ph % 1.0) - 1
        out.append(saw * (0.45 + 0.55 * math.sin(math.pi * t / 2.2) * (0.6 + 0.4 * math.sin(TWO_PI * 1.1 * t))))
    return _lowpass(out, 0.35)


def _snore():
    """One big cartoon snore: a rattly breath in, then a whistling breath out."""
    rnd, out = random.Random(41), []
    n1 = int(0.9 * RATE)
    y = 0.0
    for i in range(n1):                                   # zzzrrrk (in)
        t = i / RATE
        y += 0.2 * (rnd.uniform(-1, 1) - y)
        rattle = 0.5 + 0.5 * math.sin(TWO_PI * 32 * t)
        out.append((y * 2 + 0.5 * math.sin(TWO_PI * 85 * t)) * rattle * math.sin(math.pi * i / n1))
    out += [0.0] * int(0.15 * RATE)
    out += [v * 0.5 for v in _glide(900, 600, 0.7, vib=0.01)]   # pheeew (out)
    return out


def _rustle():
    """Something moving inside a bag: scratchy rustling bursts."""
    rnd, out = random.Random(52), []
    n = int(0.65 * RATE)
    y = 0.0
    for i in range(n):
        t = i / RATE
        y += 0.5 * (rnd.uniform(-1, 1) - y)
        burst = max(0.0, math.sin(TWO_PI * 7 * t)) ** 2 * (0.6 + 0.4 * math.sin(TWO_PI * 2.3 * t))
        out.append(y * burst * math.sin(math.pi * t / 0.65))
    return out


def _step():
    """One soft cartoon footstep (a muffled tap)."""
    n, rnd, out = int(0.12 * RATE), random.Random(3), []
    for i in range(n):
        t = i / RATE
        out.append(math.sin(TWO_PI * (140 + 60 * math.exp(-t * 60)) * t) * math.exp(-t * 45)
                   + rnd.uniform(-1, 1) * math.exp(-t * 90) * 0.35)
    return _lowpass(out, 0.4)


def _boop():
    """A cartoon poke: a short, round boop."""
    n, ph, out = int(0.18 * RATE), 0.0, []
    for i in range(n):
        t = i / RATE
        ph += (700 + 500 * math.exp(-t * 40)) / RATE
        out.append(math.sin(TWO_PI * ph) * math.exp(-t * 22))
    return out


MAKERS = {"punch": _punch, "slap": _slap, "whoosh": _whoosh, "pop": _pop, "ding": _ding, "boing": _boing,
          "thud": _thud, "growl": _growl, "ping": _ping, "doorbell": _doorbell, "chappal": _chappal,
          "laugh_track": _laugh_track, "boom": _boom, "dun_dun": _dun_dun, "click": _click, "tick": _tick,
          "scratch": _scratch, "sizzle": _sizzle, "fire": _fire, "splash": _splash, "footsteps": _footsteps,
          "clang": _clang, "slip": _slip, "slide_up": _slide_up, "slide_down": _slide_down, "zip": _zip,
          "bonk": _bonk, "tweet": _tweet, "crash": _crash, "glass_break": _glass_break, "crickets": _crickets,
          "wah_wah": _wah_wah, "tiptoe": _tiptoe, "awooga": _awooga, "spring": _spring, "fight": _fight,
          "alarm": _alarm, "buzz": _buzz, "snore": _snore, "boop": _boop, "step": _step, "rustle": _rustle}


def fx_wav(fx_id: str) -> Path:
    """The WAV file of an effect (your own assets/sounds/<id>.* if present)."""
    user = _user("sounds", fx_id)
    if user:
        return _convert(user, CACHE / f"user_{fx_id}.wav", 5)
    if fx_id not in MAKERS:                       # a voice sound (laugh, gasp, scream...) used as an effect, e.g. on a card
        from .sfx import MAKERS as VOICE_SOUNDS, _synth_cached, _user_file
        if fx_id not in VOICE_SOUNDS:
            raise KeyError(fx_id)
        src = _user_file(fx_id, "male") or _synth_cached(fx_id, "male")
        return _convert(src, CACHE / f"voice_{fx_id}.wav")
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
        "panic": (148, [(52, 1), (52, 1), (53, 0), (51, 0)], "panic"),
        "calm": (84, [(60, 0), (57, 1), (65, 0), (67, 0)], "calm"),
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
        elif style == "panic":                           # driving low pulse, high tense notes, hats on every 8th
            for b in range(8):
                _tone(buf, int((t0 + b * beat / 2) * RATE), _note(root - 12), beat * 0.4, 0.4, 0.005, 0.1, "tri")
                _hat(buf, int((t0 + b * beat / 2) * RATE), 0.1, seed=bar * 8 + b)
            for b in range(4):
                _kick(buf, int((t0 + b * beat) * RATE), 0.6)
            _tone(buf, int(t0 * RATE), _note(root + 13), 4 * beat, 0.08, 0.3, 0.3, "sine", trem=0.6)
            if bar % 2:
                _tone(buf, int((t0 + 2 * beat) * RATE), _note(root + 24), 2 * beat, 0.06, 0.1, 0.4, "tri")
        elif style == "calm":                            # soft plucks over a warm pad
            for nn in triad:
                _tone(buf, int(t0 * RATE), _note(nn), 4 * beat + 0.3, 0.09, 0.6, 0.8, "sine")
            for kk, p_ in enumerate([0, 2, 1, 2]):
                _pluck(buf, int((t0 + kk * beat) * RATE), _note(triad[p_] + 12), beat * 2.2, 0.22, 0.998, seed=bar * 4 + kk)
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


def build_music_track(parts: list, total: float, path: Path, fade: float = 0.8):
    """parts: [(start, end, music id or None)] in time order; writes one WAV with each part's music looped,
    cross-fading where the music changes (a scene can switch the music, e.g. panic -> calm)."""
    n = int((total + 1.0) * RATE)
    buf = array.array("h", [0]) * n
    cache: dict = {}
    for a, b, mid in parts:
        if not mid:
            continue
        if mid not in cache:
            with wave.open(str(music_wav(mid)), "rb") as w:
                if w.getframerate() != RATE or w.getnchannels() != 1:
                    raise ValueError("music must be mono at the fx rate")
                s = array.array("h")
                s.frombytes(w.readframes(w.getnframes()))
                cache[mid] = s
        s = cache[mid]
        i0, i1 = max(0, int((a - fade / 2) * RATE)), min(n, int((b + fade / 2) * RATE))
        fd = max(1, int(fade * RATE))
        for i in range(i0, i1):
            g = min(1.0, (i - i0) / fd, (i1 - i) / fd)
            v = buf[i] + int(s[(i - i0) % len(s)] * g)
            buf[i] = 32767 if v > 32767 else -32768 if v < -32768 else v
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())


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
            try:
                p = fx_wav(fid)
                with wave.open(str(p), "rb") as w:
                    ok = w.getframerate() == RATE and w.getnchannels() == 1 and w.getsampwidth() == 2
                if not ok:                            # another sample rate: convert it once
                    p = _convert(p, CACHE / f"conv_{fid}.wav")
                with wave.open(str(p), "rb") as w:
                    s = array.array("h")
                    s.frombytes(w.readframes(w.getnframes()))
                    cache[fid] = s
            except Exception as e:  # noqa: BLE001  a missing sound must never stop the video
                print(f"Sound effect '{fid}' could not be made ({e}); it is left out.")
                cache[fid] = array.array("h")
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
