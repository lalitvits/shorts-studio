"""Timeline -> video.

Pipeline: normalize the timeline JSON -> synthesize voices -> schedule scenes
-> draw every frame (background + rigged characters) -> pipe raw frames to
FFmpeg together with the mixed voice track -> FFmpeg burns word-highlighted
captions (ASS subtitles, so Hindi letters are shaped correctly) and encodes MP4.
"""
from __future__ import annotations

import array
import io
import math
import re
import shutil
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audio import AudioError, env_segments, fit_segments, get_audio, load_env
from .backgrounds import get_background, get_background_3d
from .shading import shade_3d, soft_shadow
from .visemes import build_track
from .catalog import ACTIONS, DEFAULT_VOICE, EMOTIONS, LOOK_ALIASES, LOOKS, SHOT_LABELS, SOUND_LABELS
from .flat import FlatComposer
from .config import GROUND_Y, OUTPUT_DIR, QUALITY, WORLD_W, find_devanagari_font, find_ffmpeg
from .rig import (BOX_H, BOX_W, KEEP_EMOTION, ORG_X, ORG_Y, PERSISTENT, SIT_ACTIONS, blink_amount,
                  draw_character, draw_sofa, pose_for)
from .sfx import SoundError, get_sound
from .tts import ENV_HZ, RATE, Clip, estimate_seconds, get_clip, join_clips, read_samples


class RenderError(Exception):
    pass


# ----------------------------------------------------------------- model
def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def normalize(tl: dict) -> dict:
    au = tl.get("audio") or {}
    try:
        mv = max(0.0, min(1.0, float(au.get("music_volume", 20)) / 100))
    except (TypeError, ValueError):
        mv = 0.2
    audio = dict(mode="file" if au.get("mode") == "file" else "tts", id=au.get("id") or None,
                 music_id=au.get("music_id") or None, music_volume=mv)
    chars = []
    for c in tl.get("characters", []):
        cid = str(c.get("id") or f"c{len(chars) + 1}")
        look = LOOK_ALIASES.get(c.get("look"), c.get("look"))
        chars.append(dict(id=cid, name=str(c.get("name") or cid),
                          look=look if look in LOOKS else "rahul",
                          voice=c.get("voice") or DEFAULT_VOICE))
    if not chars:
        raise RenderError("Add at least one character.")
    ids = [c["id"] for c in chars]
    scenes = []
    for sc in tl.get("scenes", []):
        lines = []
        for ln in sc.get("lines", []):
            text = str(ln.get("text", "")).strip()
            sound = ln.get("sound") if ln.get("sound") in SOUND_LABELS else ""
            if not text and not sound and audio["mode"] != "file":   # nothing to say or play (own audio: acting only)
                continue
            lines.append(dict(speaker=ln.get("speaker") if ln.get("speaker") in ids else ids[0], text=text, sound=sound,
                              emotion=ln.get("emotion") if ln.get("emotion") in EMOTIONS else "neutral",
                              action=ln.get("action") if ln.get("action") in ACTIONS else "talk",
                              shot=ln.get("shot") if ln.get("shot") in SHOT_LABELS else "auto",
                              start=_num(ln.get("start")), end=_num(ln.get("end"))))
        # who is in the scene: the characters the user added (they stay in frame even with no dialogue)
        speakers = []
        for ln in lines:
            if ln["speaker"] not in speakers:
                speakers.append(ln["speaker"])
        given = sc.get("cast")
        cast = [c for c in given if c in ids] if isinstance(given, list) else []
        cast = cast + [x for x in speakers if x not in cast]
        if lines or cast:
            scenes.append(dict(background=sc.get("background") or "living_room", cast=cast, lines=lines,
                               audio_from=_num(sc.get("audio_from")), audio_to=_num(sc.get("audio_to"))))
    if not any(sc["cast"] for sc in scenes):
        raise RenderError("Add at least one scene with a character in it.")
    return dict(title=str(tl.get("title") or "").strip(), characters=chars, scenes=scenes,
                tts=tl.get("tts") or "auto", audio=audio, look3d=bool(tl.get("look3d", True)),
                captions=bool(tl.get("captions", True)), language=str(tl.get("language") or "hi"))


@dataclass
class LineT:
    char: str
    text: str
    emotion: str
    action: str
    start: float
    end: float
    clip: Clip
    sfx: object = None      # an emotional sound to mix in on top (own-audio mode)
    reaction: bool = False  # a sound with no words: the sprite's own mouth is kept (no lip-sync)
    shot: str = "auto"      # camera shot (flat cartoon style)
    src: tuple = None       # own-audio mode: (start, end) of this line in your audio file


@dataclass
class SceneT:
    bg: str
    cast: list
    start: float
    end: float
    lines: list = field(default_factory=list)


def make_clip(ln: dict, ch: dict, engine: str, warnings: list | None = None) -> Clip:
    """The audio of one line made by the app: its voice, an emotional sound, or the sound followed by the words."""
    sound = get_sound(ln["sound"], ch["voice"]) if ln["sound"] else None
    if not ln["text"]:                              # a reaction: only the emotional sound
        return sound
    c = get_clip(ln["text"], ch["voice"], engine, emotion=ln["emotion"])
    if warnings is not None and c.warning and c.warning not in warnings:
        warnings.append(c.warning)
    return join_clips(sound, c) if sound else c     # the sound first, then the words


def build_schedule(tl: dict, clip_for) -> tuple[list, float]:
    by_id = {c["id"]: c for c in tl["characters"]}
    t, out = 0.5, []
    for sc in tl["scenes"]:
        st = SceneT(sc["background"], list(sc["cast"]), t, t)
        t += 0.25
        for ln in sc["lines"]:
            clip = clip_for(ln, by_id[ln["speaker"]])
            st.lines.append(LineT(ln["speaker"], ln["text"], ln["emotion"], ln["action"],
                                  t, t + clip.duration, clip, None, not ln["text"] and bool(ln["sound"]), ln["shot"]))
            t += clip.duration + 0.18
        if not sc["lines"]:                      # a scene with only silent characters holds for a moment
            t += 2.0
        t += 0.4
        st.end = t
        out.append(st)
    return out, t


def _union(a: list, b: list) -> list:
    n = max(len(a), len(b))
    return [max(a[i] if i < len(a) else 0.0, b[i] if i < len(b) else 0.0) for i in range(n)]


def build_schedule_file(tl: dict, env: list, audio_seconds: float) -> tuple[list, float, list]:
    """Timeline made from your audio. Each scene plays its own trimmed part of the audio (audio_from .. audio_to,
    seconds into your file); the scenes follow each other. Line times (start/end) are seconds in the original audio.
    A reaction line (an emotional sound, no words, no times) is added after the scene's speech and makes the scene
    a little longer. Returns (scenes, total seconds, [(from, to, extra seconds) audio parts in scene order])."""
    by_id = {c["id"]: c for c in tl["characters"]}
    t, cursor, out, parts = 0.0, 0.0, [], []

    def is_tail(ln):
        return bool(ln["sound"]) and not ln["text"] and ln["start"] is None and ln["end"] is None

    def timed(ln):
        return ln["start"] is not None and ln["end"] is not None and ln["end"] > ln["start"]

    def untrimmed(sc):     # no trim and no timed lines: the scene gets a share of the rest of the audio
        a_, b_ = sc["audio_from"], sc["audio_to"]
        return (a_ is None or b_ is None or b_ <= a_) and not any(timed(ln) for ln in sc["lines"] if not is_tail(ln))

    def weight(sc):
        return max(1, len([ln for ln in sc["lines"] if not is_tail(ln)]))

    for si, sc in enumerate(tl["scenes"]):
        speech = [ln for ln in sc["lines"] if not is_tail(ln)]
        tails = [ln for ln in sc["lines"] if is_tail(ln)]
        spans = [(ln["start"], ln["end"]) for ln in speech if timed(ln)]
        a, b = sc["audio_from"], sc["audio_to"]
        if a is None or b is None or b <= a:                 # not trimmed: its lines' times, else a fair share
            run = []                                         # the following untrimmed scenes
            for s in tl["scenes"][si + 1:]:
                if not untrimmed(s):
                    break
                run.append(s)
            nxt = next((s for s in tl["scenes"][si + 1 + len(run):]), None)
            end = audio_seconds                              # where the audio still free for these scenes ends
            if nxt is not None:
                nspans = [ln["start"] for ln in nxt["lines"] if timed(ln)]
                nstart = nxt["audio_from"] if nxt["audio_from"] is not None else (min(nspans) if nspans else None)
                if nstart is not None and nstart > cursor:
                    end = nstart
            later = sum(weight(s) for s in run)
            if spans:
                first = next(i for i, ln in enumerate(speech) if timed(ln))
                last = max(i for i, ln in enumerate(speech) if timed(ln))
                a = cursor if first > 0 else min(x for x, _ in spans)
                b = max(y for _, y in spans)
                after = len(speech) - 1 - last               # untimed lines after the last timed one get room too
                if after:
                    b = b + max(0.0, end - b) * after / (after + later)
            else:
                a = cursor
                b = cursor + (end - cursor) * weight(sc) / (weight(sc) + later)
        a = min(max(0.0, a), max(0.0, audio_seconds - 0.3))
        b = min(max(b, a + 0.3), max(audio_seconds, a + 0.3))
        cursor = b
        # Lines without times follow the speech in the audio. If no line has times, they are fitted to the speech
        # parts found in the scene's audio (like "Match my lines to the audio"); otherwise the missing ones share
        # the gap up to the next timed line.
        times = {}
        untimed = [i for i, ln in enumerate(speech) if not timed(ln)]
        if untimed and len(untimed) == len(speech):
            segs = env_segments(env[int(a * ENV_HZ): int(b * ENV_HZ)], offset=a)
            for i, (x, y) in zip(untimed, fit_segments(segs, len(speech), a, b)):
                times[i] = (x, y)
        elif untimed:
            k = 0
            while k < len(speech):
                if timed(speech[k]):
                    k += 1
                    continue
                j = k
                while j < len(speech) and not timed(speech[j]):
                    j += 1
                lo = speech[k - 1]["end"] if k > 0 else a
                hi = speech[j]["start"] if j < len(speech) else b
                lo, hi = min(max(lo, a), b), min(max(hi, a), b)
                if hi - lo < 0.3:
                    hi = min(b, lo + 0.3)
                segs = env_segments(env[int(lo * ENV_HZ): int(hi * ENV_HZ)], offset=lo)
                for q, (x, y) in zip(range(k, j), fit_segments(segs, j - k, lo, hi)):
                    times[q] = (x, y)
                k = j
        st = SceneT(sc["background"], list(sc["cast"]), t, t)
        for idx, ln in enumerate(speech):
            sfx = get_sound(ln["sound"], by_id[ln["speaker"]]["voice"]) if ln["sound"] else None
            ls, le = times.get(idx, (ln["start"], ln["end"]))
            ls, le = min(max(ls, a), b), min(max(le, a), b)
            if le <= ls:
                le = min(b, ls + 0.1)
            e = env[int(ls * ENV_HZ): int(le * ENV_HZ)]
            clip = Clip(Path(""), max(0.1, le - ls), _union(e, sfx.env) if sfx else e, synthetic=False)
            ln = dict(ln, _src=(ls, le))
            st.lines.append(LineT(ln["speaker"], ln["text"], ln["emotion"], ln["action"],
                                  t + (ls - a), t + (ls - a) + clip.duration, clip, sfx,
                                  not ln["text"] and bool(ln["sound"]), ln["shot"], ln["_src"]))
        extra = 0.0
        for ln in tails:
            sfx = get_sound(ln["sound"], by_id[ln["speaker"]]["voice"])
            d = sfx.duration + 0.25
            st.lines.append(LineT(ln["speaker"], "", ln["emotion"], ln["action"], t + (b - a) + extra,
                                  t + (b - a) + extra + d, Clip(Path(""), d, sfx.env, synthetic=False), sfx, True,
                                  ln["shot"]))
            extra += d
        st.end = t + (b - a) + extra
        out.append(st)
        parts.append((a, b, extra))
        t = st.end
    return out, t, parts


def build_sfx_track(sched: list, total: float, path: Path):
    """A silent track with each emotional sound placed where its line starts (own-audio mode)."""
    n = int((total + 0.5) * RATE)
    buf = array.array("h", [0]) * n
    for sc in sched:
        for ln in sc.lines:
            if ln.sfx is None:
                continue
            s = read_samples(ln.sfx.wav)
            off = int(ln.start * RATE)
            for i in range(min(len(s), n - off)):
                v = buf[off + i] + s[i]
                buf[off + i] = 32767 if v > 32767 else -32768 if v < -32768 else v
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())


def layout(n: int) -> tuple[list, float]:
    if n == 1:
        return [540], 1.30
    if n == 2:
        return [300, 780], 1.12
    return [(i + 1) * WORLD_W / (n + 1) for i in range(n)], max(0.7, 1.0 - 0.1 * (n - 3))


class Composer:
    def __init__(self, tl: dict, sched: list, w: int, h: int, ss: int = 2):
        self.tl, self.sched, self.w, self.h, self.ss = tl, sched, w, h, ss
        self.look3d = bool(tl.get("look3d"))
        self._sofa: dict = {}
        self._tracks: dict = {}
        self.k = w / WORLD_W
        self.chars = {c["id"]: c for c in tl["characters"]}
        self.flat = FlatComposer(tl, sched, w, h)

    def scene_at(self, t: float) -> SceneT:
        for sc in self.sched:
            if t < sc.end:
                return sc
        return self.sched[-1]

    def frame(self, t: float) -> Image.Image:
        sc = self.scene_at(t)
        if self.flat.handles(sc):                                 # flat cartoon style with its own camera
            return self.flat.frame(sc, t)
        im = (get_background_3d if self.look3d else get_background)(sc.bg, self.w, self.h).copy()
        line = next((l for l in sc.lines if l.start <= t < l.end), None)
        xs, scale = layout(len(sc.cast))
        sx = xs[sc.cast.index(line.char)] if line else None

        # Sitting is a scene-level choice: if a character has any sit_* line, they sit the whole scene.
        seated = {cid for cid in sc.cast if any(l.char == cid and l.action in SIT_ACTIONS for l in sc.lines)}
        if seated:
            sx0 = min(xs[sc.cast.index(c)] for c in seated) - 250 * scale
            sx1 = max(xs[sc.cast.index(c)] for c in seated) + 250 * scale
            key = (sc.bg, round(sx0), round(sx1), scale)
            if key not in self._sofa:
                lay, pos = draw_sofa(im, self.k, GROUND_Y, sx0, sx1, scale)
                self._sofa[key] = (shade_3d(lay) if self.look3d else lay, pos)
            layer, pos = self._sofa[key]
            im.paste(layer, pos, layer)

        for i, cid in enumerate(sc.cast):
            speaking = bool(line and line.char == cid)
            mine = [l for l in sc.lines if l.char == cid]
            recent = next((l for l in reversed(mine) if l.start <= t), mine[0] if mine else None)  # latest or first line
            if speaking:
                action, emotion = line.action, line.emotion
            elif recent is None:   # in the scene but never speaks: stands there and listens
                action, emotion = "idle", "neutral"
            else:  # keep doing a long activity while listening; otherwise stand still
                action = recent.action if recent.action in PERSISTENT else "idle"
                emotion = recent.emotion if recent.emotion in KEEP_EMOTION else "neutral"
            if cid in seated and action == "idle":
                action = "sit"
            phase = i * 1.7
            t_act = (t - sc.start) if (action in PERSISTENT or not speaking) else (t - line.start)
            pose = pose_for(action, emotion, t_act, speaking, phase, seated=cid in seated)
            if not speaking and sx is not None and not pose.get("prop"):
                pose["look_x"] = 0.8 if sx > xs[i] else -0.8
            still = speaking and line.action == "idle"           # "Stand still": no lip movement at all
            lipsync = speaking and not line.reaction and not still
            mouth = line.clip.mouth_at(t - line.start) if speaking and not still else 0.0
            look = LOOKS[self.chars[cid]["look"]]
            vis = None
            if lipsync and line.text:                             # mouth shapes that follow the words, timed on the voice
                if id(line) not in self._tracks:
                    self._tracks[id(line)] = build_track(line.text, line.clip.env, line.clip.duration, line.clip.synthetic)
                trk = self._tracks[id(line)]
                vis = trk.at(t - line.start) if trk else None
            if self.look3d:                                       # soft blurred shadow on the floor
                cs = scale * look.get("scale", 1.0) * self.k
                soft_shadow(im, xs[i] * self.k, GROUND_Y * self.k, 130 * cs, 17 * cs, 11 * cs)
            layer = draw_character(look, pose, emotion, mouth, blink_amount(t, phase), self.k, scale, self.ss, t_act,
                                   lipsync=lipsync, ground_shadow=not self.look3d, viseme=vis)
            if self.look3d and look.get("style") != "clay":      # the clay character is already lit and shaded
                layer = shade_3d(layer)
            im.paste(layer, (int((xs[i] - ORG_X) * self.k), int((GROUND_Y - ORG_Y) * self.k)), layer)
        return im


# --------------------------------------------------------------- captions
def _ass_time(s: float) -> str:
    cs = int(round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _chunks(words: list) -> list:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4 or sum(len(x) for x in cur) + len(cur) > 17:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def make_ass(sched: list, w: int, h: int, font_family: str) -> str:
    size, outline, margin_v = int(h * 0.05), max(2, int(h * 0.006)), int(h * 0.15)
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font_family},{size},&H0000D7FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,"
        f"{outline},1,8,{int(w * 0.06)},{int(w * 0.06)},{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for sc in sched:
        for ln in sc.lines:
            words = [x.replace("{", "").replace("}", "") for x in ln.text.split()]
            if not words:
                continue
            weights = [len(x) + 1.5 for x in words]
            span, tw, t = ln.end - ln.start, sum(weights), ln.start
            timed = []
            for x, wt in zip(words, weights):
                d = span * wt / tw
                timed.append((x, t, t + d))
                t += d
            for ch in _chunks(timed):
                text = " ".join("{\\k%d}%s" % (max(1, round((b - a) * 100)), x) for x, a, b in ch)
                events.append(f"Dialogue: 0,{_ass_time(ch[0][1])},{_ass_time(ch[-1][2])},Cap,,0,0,0,,{text}")
    return head + "\n".join(events) + "\n"


def _font(size: int):
    fp = find_devanagari_font()
    if not fp:
        return ImageFont.load_default(size)
    try:
        return ImageFont.truetype(str(fp), size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(str(fp), size)


def draw_caption(im: Image.Image, text: str):
    """Caption for still previews (the real video uses ASS subtitles)."""
    h, w = im.height, im.width
    size = int(h * 0.05)
    font = _font(size)
    d = ImageDraw.Draw(im)
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) > w * 0.86 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    y = int(h * 0.15)
    for ln in lines:
        tw = d.textlength(ln, font=font)
        d.text(((w - tw) / 2, y), ln, font=font, fill=(255, 255, 255), stroke_width=max(2, int(h * 0.006)),
               stroke_fill=(0, 0, 0))
        y += int(size * 1.35)


# ------------------------------------------------------------------ audio
def build_audio(sched: list, total: float, path: Path):
    n = int((total + 0.5) * RATE)
    buf = array.array("h", [0]) * n
    for sc in sched:
        for ln in sc.lines:
            s = read_samples(ln.clip.wav)
            off = int(ln.start * RATE)
            end = min(n, off + len(s))
            buf[off:end] = s[: end - off]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())


# ------------------------------------------------------------------ render
def render_video(tl: dict, quality: str = "preview", progress=None) -> dict:
    progress = progress or (lambda stage, frac: None)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RenderError("FFmpeg was not found. Install it, then restart the app (see README).")
    q = QUALITY.get(quality, QUALITY["preview"])
    tl = normalize(tl)
    au = tl["audio"]
    warnings: list = []

    if au["mode"] == "file":
        if not au["id"]:
            raise RenderError("Upload your audio file first (Voices step), or switch back to voices made by the app.")
        progress("Reading your audio", 0.0)
        try:
            meta = get_audio(au["id"])
            sched, total, parts = build_schedule_file(tl, load_env(au["id"]), meta["seconds"])
        except (AudioError, SoundError) as e:
            raise RenderError(str(e))
        voice_input = str(meta["path"])
        if tl["captions"]:                     # lines without text get their words from your audio (Gemini)
            todo = [ln for sc in sched for ln in sc.lines if not ln.text and ln.src and not ln.reaction]
            if todo:
                progress("Writing captions from your audio", 0.0)
                from .transcribe import transcribe_many
                texts, warn = transcribe_many(au["id"], [ln.src for ln in todo], tl["language"])
                for ln, tx in zip(todo, texts):
                    ln.text = tx
                if warn:
                    warnings.append("Captions: " + warn + " Type the caption text of those lines yourself.")
    else:
        progress("Making voices", 0.0)

        def clip_for(ln, ch):
            return make_clip(ln, ch, tl["tts"], warnings)

        try:
            sched, total = build_schedule(tl, clip_for)
        except SoundError as e:
            raise RenderError(str(e))
        voice_input = "voice.wav"
    music_path = None
    if au["music_id"]:
        try:
            music_path = str(get_audio(au["music_id"])["path"])
        except AudioError as e:
            raise RenderError("Background music: " + str(e))
    if total > 180:
        warnings.append("This video is longer than 3 minutes, so YouTube will not treat it as a Short.")

    w, h, fps = q["w"], q["h"], q["fps"]
    comp = Composer(tl, sched, w, h, q["ss"])
    work = Path(tempfile.mkdtemp(prefix="shorts_"))
    try:
        if au["mode"] != "file":
            progress("Mixing audio", 0.0)
            build_audio(sched, total, work / "voice.wav")

        font_path = find_devanagari_font()
        family = "Arial"
        (work / "fonts").mkdir()
        if font_path:
            shutil.copy(font_path, work / "fonts" / ("caption" + font_path.suffix))
            try:
                family = ImageFont.truetype(str(font_path), 20).getname()[0]
            except Exception:
                pass
        else:
            warnings.append("No Devanagari font found. Hindi captions may show empty boxes. "
                            "Put a font such as Noto Sans Devanagari in assets/fonts (see README).")
        (work / "captions.ass").write_text(make_ass(sched, w, h, family), encoding="utf-8")

        stamp = time.strftime("%Y%m%d-%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "-", tl["title"].lower()).strip("-")[:30] or "short"
        out = OUTPUT_DIR / f"{slug}-{stamp}-{quality}.mp4"
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
               "-framerate", str(fps), "-i", "pipe:0", "-i", voice_input]
        norm = "aresample=44100,aformat=channel_layouts=stereo"
        sfx_idx = music_idx = None
        if au["mode"] == "file" and any(ln.sfx is not None for sc in sched for ln in sc.lines):
            build_sfx_track(sched, total, work / "sfx.wav")
            cmd += ["-i", "sfx.wav"]
            sfx_idx = 2
        if music_path:
            music_idx = 2 + (1 if sfx_idx else 0)
            cmd += ["-stream_loop", "-1", "-i", music_path]
        if au["mode"] == "file":      # cut each scene's part out of your audio and join the parts in scene order
            n = len(parts)
            head = f"[1:a]asplit={n}" + "".join(f"[i{k}]" for k in range(n)) + ";" if n > 1 else ""
            cuts = "".join(f"{'[i%d]' % k if n > 1 else '[1:a]'}atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,{norm}"
                           f"{',apad=pad_dur=%.3f' % x if x > 0 else ''}[p{k}];"
                           for k, (a, b, x) in enumerate(parts))
            graph = head + cuts + "".join(f"[p{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[voice0];[voice0]apad[voice]"
        else:
            graph = f"[1:a]{norm},apad[voice]"
        streams = [("voice", 1.0)]
        if sfx_idx:
            graph += f";[{sfx_idx}:a]{norm}[sfx]"
            streams.append(("sfx", 1.0))
        if music_idx:
            graph += f";[{music_idx}:a]{norm}[mus]"
            streams.append(("mus", au["music_volume"]))
        if len(streams) == 1:
            audio_graph = graph.rsplit("[voice]", 1)[0] + "[aout]"
        else:
            weights = " ".join(f"{w:.2f}" for _, w in streams)
            audio_graph = (graph + ";" + "".join(f"[{nm}]" for nm, _ in streams) +
                           f"amix=inputs={len(streams)}:duration=first:weights='{weights}',"
                           f"volume={sum(w for _, w in streams):.2f}[aout]")
        vf = "ass=captions.ass:fontsdir=fonts" if tl["captions"] else "null"
        cmd += ["-filter_complex", f"[0:v]{vf}[vout];{audio_graph}",
                "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
        log = open(work / "ffmpeg.log", "wb")
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log, cwd=work)
        frames = int(math.ceil(total * fps))
        try:
            for i in range(frames):
                proc.stdin.write(comp.frame(i / fps).tobytes())
                if i % 5 == 0:
                    progress("Drawing frames", i / frames)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        progress("Encoding", 0.99)
        for msg in comp.flat.warnings:
            if msg not in warnings:
                warnings.append(msg)
        code = proc.wait()
        log.close()
        if code != 0 or not out.exists():
            tail = (work / "ffmpeg.log").read_text(errors="ignore")[-600:]
            raise RenderError("FFmpeg failed: " + tail)
        progress("Done", 1.0)
        return dict(file=out.name, seconds=round(total, 1), warnings=warnings, size=[w, h])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render_still(tl: dict, scene_i: int = 0, line_i: int = 0, width: int = 270) -> bytes:
    """One preview picture of a scene (no audio needed)."""
    tl = normalize(tl)

    def fake(ln, ch):
        secs = estimate_seconds(ln["text"])
        return Clip(Path(""), secs, [0.6] * int(secs * ENV_HZ), synthetic=True)

    sched, _ = build_schedule(tl, fake)
    sc = sched[max(0, min(scene_i, len(sched) - 1))]
    comp = Composer(tl, sched, width, int(width * 16 / 9), 2)
    if sc.lines:
        ln = sc.lines[max(0, min(line_i, len(sc.lines) - 1))]
        im = comp.frame(ln.start + 0.45)
        if tl["captions"]:
            draw_caption(im, ln.text)
    else:
        im = comp.frame(sc.start + 0.45)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()
