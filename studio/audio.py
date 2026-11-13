"""Audio files from your computer.

Two uses:
  voice-over / dubbing   your own recording replaces the voices made by the app. The characters act while it plays,
                         and their mouths move with its loudness.
  background music       mixed quietly under either kind of voice.

`speech_segments` finds where speech starts and stops, and `match_lines` fits your dialogue lines to those parts so
you do not have to type every time by hand.
"""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from pathlib import Path
from urllib.parse import unquote

from .config import UPLOADS_DIR, find_ffmpeg
from .tts import ENV_HZ, RATE, compute_env, read_samples

ALLOWED = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".wma", ".aiff", ".aif",
           ".mp4", ".mov", ".mkv", ".webm"}
MAX_BYTES = 500 * 1024 * 1024
_ENV: dict[str, list] = {}


class AudioError(Exception):
    pass


def _check_id(uid: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{10}", str(uid or "")):
        raise AudioError("That audio file is not available. Upload it again.")
    return uid


def save_upload(stream, length: int, filename: str) -> dict:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise AudioError("FFmpeg was not found. Install it, then restart the app (see the README).")
    filename = unquote(filename or "audio")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise AudioError("Use an audio file such as MP3, WAV, M4A, AAC, OGG or FLAC.")
    if length <= 0 or length > MAX_BYTES:
        raise AudioError("The file is empty or larger than 500 MB.")
    uid = uuid.uuid4().hex[:10]
    if ext == ".wav":          # <uid>.wav is the converted copy below; keep the original under another name
        ext = "_src.wav"
    path = UPLOADS_DIR / f"{uid}{ext}"
    left = length
    with open(path, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    wav = UPLOADS_DIR / f"{uid}.wav"
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-vn", "-ar", str(RATE), "-ac", "1",
                        "-c:a", "pcm_s16le", str(wav)], capture_output=True)
    if r.returncode != 0 or not wav.exists():
        path.unlink(missing_ok=True)
        raise AudioError("Could not read that file as audio. Try an MP3 or WAV.")
    samples = read_samples(wav)
    _ENV[uid] = compute_env(samples)
    meta = dict(id=uid, name=Path(filename).name, ext=ext, seconds=round(len(samples) / RATE, 2))
    (UPLOADS_DIR / f"{uid}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def get_audio(uid: str) -> dict:
    """Meta data plus the original file path."""
    uid = _check_id(uid)
    mp = UPLOADS_DIR / f"{uid}.json"
    if not mp.exists():
        raise AudioError("That audio file is not available. Upload it again.")
    meta = json.loads(mp.read_text(encoding="utf-8"))
    meta["path"] = UPLOADS_DIR / f"{uid}{meta['ext']}"
    if not meta["path"].exists():
        raise AudioError("That audio file is not available. Upload it again.")
    return meta


def load_env(uid: str) -> list:
    uid = _check_id(uid)
    if uid not in _ENV:
        wav = UPLOADS_DIR / f"{uid}.wav"
        if not wav.exists():
            raise AudioError("That audio file is not available. Upload it again.")
        _ENV[uid] = compute_env(read_samples(wav))
    return _ENV[uid]


def speech_segments(uid: str, pause: float = 0.45, min_len: float = 0.25) -> list[list[float]]:
    """[[start, end], ...] in seconds: the parts of the audio where something is being said."""
    return env_segments(load_env(uid), pause, min_len)


def env_segments(env: list, pause: float = 0.45, min_len: float = 0.25, offset: float = 0.0) -> list[list[float]]:
    """speech_segments for a loudness envelope (or a slice of one that starts `offset` seconds into the audio)."""
    loud = [i for i, v in enumerate(env) if v > 0.12]
    segs: list[list[float]] = []
    for i in loud:
        t = i / ENV_HZ
        if segs and t - segs[-1][1] <= pause:
            segs[-1][1] = t + 1 / ENV_HZ
        else:
            segs.append([t, t + 1 / ENV_HZ])
    total = len(env) / ENV_HZ
    out = [[max(0.0, round(a - 0.05, 2)) + offset, min(total, round(b + 0.08, 2)) + offset]
           for a, b in segs if b - a >= min_len]
    return out


def fit_segments(segs: list, n: int, a: float, b: float) -> list[list[float]]:
    """Exactly n [start, end] parts from the speech parts `segs` (merging the closest or splitting the longest);
    with no speech found, [a, b] is divided evenly."""
    if n <= 0:
        return []
    if not segs:
        step = (b - a) / n
        return [[a + i * step, a + (i + 1) * step] for i in range(n)]
    segs = [list(s) for s in segs]
    while len(segs) > n:
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        k = gaps.index(min(gaps))
        segs[k] = [segs[k][0], segs[k + 1][1]]
        del segs[k + 1]
    while len(segs) < n:
        k = max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])
        x, y = segs[k]
        mid = (x + y) / 2
        segs[k:k + 1] = [[x, mid], [mid, y]]
    return segs


def match_lines(uid: str, n_lines: int, pause: float = 0.45) -> dict:
    """Exactly n_lines (start, end) pairs that cover the speech, merging or splitting parts where needed."""
    segs = speech_segments(uid, pause)
    total = len(load_env(uid)) / ENV_HZ
    found = len(segs)
    if n_lines <= 0:
        return dict(times=[], found=found, note="")
    if not segs:
        step = total / n_lines
        return dict(times=[dict(start=round(i * step, 2), end=round((i + 1) * step, 2)) for i in range(n_lines)],
                    found=0, note="No clear speech was found, so the audio was divided evenly.")
    segs = fit_segments(segs, n_lines, 0.0, total)
    note = "" if found == n_lines else (f"Found {found} speech parts for your {n_lines} lines, so some were "
                                        f"{'merged' if found > n_lines else 'split'}. Check the times and adjust if needed.")
    return dict(times=[dict(start=round(a, 2), end=round(b, 2)) for a, b in segs], found=found, note=note)


def peaks(uid: str, n: int = 700) -> dict:
    """A thin picture of the loudness over time, for drawing a waveform."""
    env = load_env(uid)
    total = len(env) / ENV_HZ
    n = max(1, min(n, len(env)))
    step = len(env) / n
    out = [round(max(env[int(i * step): max(int(i * step) + 1, int((i + 1) * step))]), 2) for i in range(n)]
    return dict(peaks=out, seconds=round(total, 2))
