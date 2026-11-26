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
from .catalog import (CAMERA_MOVES, ACTIONS, BUILDS, DEFAULT_VOICE, EMOTIONS, GEMINI_FOR_LOOK, HEIGHTS, LOOK_ALIASES, LOOKS,
                      NARRATOR_LOOKS, OUTFIT_COLORS, PROPS, SARVAM_FOR_LOOK, SHOT_LABELS, SOUND_LABELS, VOICE_FX_FOR_LOOK,
                      VOICE_FX_LABELS, VOICE_TUNE)
from .flat import FlatComposer
from . import fx as fx_mod
from . import kitchen
from . import bag
from . import overlays
from . import stick
from .config import GROUND_Y, OUTPUT_DIR, QUALITY, WORLD_W, find_devanagari_font, find_ffmpeg
from .rig import (BOX_H, BOX_W, KEEP_EMOTION, ORG_X, ORG_Y, PERSISTENT, SIT_ACTIONS, blink_amount,
                  draw_character, draw_sofa, pose_for)
from .sfx import SoundError, get_sound
from .tts import ENV_HZ, RATE, Clip, estimate_seconds, get_clip, join_clips, read_samples


class RenderError(Exception):
    pass


class RenderCancelled(BaseException):
    """You pressed Cancel. (Not an Exception, so nothing on the way swallows it as an ordinary error.)"""


# ----------------------------------------------------------------- model
def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


CARD_STYLES = ("dark", "black", "bright")
LIGHTING = ("day", "dark", "phone", "bw", "dim")
STICKERS = ("pizza", "burger", "money", "heart", "idea", "angry", "laugh", "question", "exclaim", "sleep", "fire")


RENAMED_BG = {"village_tea_stall": "flat_chai_tapri", "village": "flat_village",
              "village_night": "flat_village"}   # removed pictures -> what older projects show instead


def _broll(v) -> str:
    """A line's cut-away picture: one of the explainer animations, or "pic:<background id>" (your own picture)."""
    v = str(v or "")
    return v if v in kitchen.EXPLAINERS or (v.startswith("pic:") and len(v) < 120) else ""


def _body(v, names, lo, hi):
    """A height / build: one of the names ("tall", "fat"...) or a number (1.1 = 10% taller / wider); "" = the look's own."""
    if v in names:
        return v
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return ""


def _scene_music(v) -> str:
    """A scene's music: a built-in track id, "none" (silence from here), or "" (keep the music playing)."""
    return v if v in fx_mod.MUSIC_LABELS or v == "none" else ""


def _clampi(v, default, lo, hi):
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def normalize(tl: dict) -> dict:
    au = tl.get("audio") or {}
    try:
        mv = max(0.0, min(1.0, float(au.get("music_volume", 20)) / 100))
    except (TypeError, ValueError):
        mv = 0.2
    audio = dict(mode="file" if au.get("mode") == "file" else "tts", id=au.get("id") or None,
                 music_id=au.get("music_id") or None, music_volume=mv,
                 music_builtin=au.get("music_builtin") if au.get("music_builtin") in fx_mod.MUSIC_LABELS else None)
    chars = []
    for c in tl.get("characters", []):
        cid = str(c.get("id") or f"c{len(chars) + 1}")
        look = LOOK_ALIASES.get(c.get("look"), c.get("look"))
        chars.append(dict(id=cid, name=str(c.get("name") or cid),
                          look=look if look in LOOKS else "rahul",
                          voice=c.get("voice") or DEFAULT_VOICE,
                          voice_pitch=_clampi(c.get("voice_pitch"), VOICE_TUNE.get(look, (0, 0))[0], -60, 80),
                          voice_rate=_clampi(c.get("voice_rate"), VOICE_TUNE.get(look, (0, 0))[1], -40, 60),
                          voice_fx=c["voice_fx"] if c.get("voice_fx") in VOICE_FX_LABELS
                          else VOICE_FX_FOR_LOOK.get(look, ""),
                          height=_body(c.get("height"), HEIGHTS, 0.5, 1.3),
                          build=_body(c.get("build"), BUILDS, 0.7, 1.7),
                          outfit=c.get("outfit") if c.get("outfit") in OUTFIT_COLORS else ""))
    if not chars:
        raise RenderError("Add at least one character.")
    ids = [c["id"] for c in chars]
    narrators = {c["id"] for c in chars if c["look"] in NARRATOR_LOOKS}       # voice-over: never on screen
    if len(narrators) == len(chars):
        raise RenderError("Add at least one character who is on screen (the narrator is only a voice).")
    scenes = []
    for sc in tl.get("scenes", []):
        lines = []
        for ln in sc.get("lines", []):
            text = str(ln.get("text", "")).strip()
            sound = ln.get("sound") if ln.get("sound") in SOUND_LABELS else ""
            hold = min(20.0, _num(ln.get("hold")) or 0.0)
            if not text and not sound and not hold and audio["mode"] != "file":
                if (ln.get("action") in ("talk", "idle", None, "") and not ln.get("kadhai") and not ln.get("actor")
                        and not ln.get("bag")
                        and not ln.get("broll") and not ln.get("overlay")):
                    continue                                     # nothing to say, play or show
                hold = stick.move_hold(ln.get("action"))          # an action with no words: a silent moment
            actor = ln.get("actor") if ln.get("actor") in ids and ln.get("actor") not in narrators else ""
            lines.append(dict(speaker=ln.get("speaker") if ln.get("speaker") in ids else ids[0], text=text, sound=sound,
                              hold=hold, actor=actor,
                              actor_action=ln.get("actor_action") if ln.get("actor_action") in ACTIONS else "idle",
                              actor_emotion=ln.get("actor_emotion") if ln.get("actor_emotion") in EMOTIONS else "neutral",
                              kadhai=ln.get("kadhai") if ln.get("kadhai") in kitchen.KADHAI_STATES else "",
                              broll=_broll(ln.get("broll")),
                              prop=ln.get("prop") if ln.get("prop") in PROPS or ln.get("prop") == "none" else "",
                              overlay=" ".join(str(ln.get("overlay") or "").split())[:120],
                              emotion=ln.get("emotion") if ln.get("emotion") in EMOTIONS else "neutral",
                              action=ln.get("action") if ln.get("action") in ACTIONS else "talk",
                              shot=ln.get("shot") if ln.get("shot") in SHOT_LABELS else "auto",
                              move=ln.get("move") if ln.get("move") in CAMERA_MOVES else "auto",
                              lights=ln.get("lights") if ln.get("lights") in ("on", "off") else "",
                              popup=" ".join(str(ln.get("popup") or "").split())[:90],
                              sticker=str(ln.get("sticker") or "") if str(ln.get("sticker") or "") in STICKERS else "",
                              effect=ln.get("effect") if ln.get("effect") in stick.EFFECTS else "",
                              bag=ln.get("bag") if ln.get("bag") in bag.BAG_STATES else "",
                              start=_num(ln.get("start")), end=_num(ln.get("end"))))
        # who is in the scene: the characters the user added (they stay in frame even with no dialogue)
        speakers = []
        for ln in lines:
            if ln["speaker"] not in speakers:
                speakers.append(ln["speaker"])
        given = sc.get("cast")
        cast = [c for c in given if c in ids] if isinstance(given, list) else []
        cast = [c for c in cast + [x for x in speakers if x not in cast] if c not in narrators]
        for ln in lines:                          # a narrator line shows someone acting: they are in the scene
            if ln["actor"] and ln["actor"] not in cast:
                cast.append(ln["actor"])
        if lines and not cast and sc.get("card") is None:     # only narration: show the first on-screen character
            cast = [next(i for i in ids if i not in narrators)]
        if sc.get("card") is not None:          # a text card (or a black screen) between scenes
            snd = sc.get("card_sound") if sc.get("card_sound") in SOUND_LABELS else ""
            scenes.append(dict(background="", cast=[], lines=[], audio_from=None, audio_to=None, lighting="day",
                               card=" ".join(str(sc.get("card") or "").split())[:80],
                               card_style=sc.get("card_style") if sc.get("card_style") in CARD_STYLES else "dark",
                               card_sound=snd, card_seconds=_num(sc.get("card_seconds")) or 0.0,
                               music=_scene_music(sc.get("music"))))
        elif cast:
            scenes.append(dict(background=RENAMED_BG.get(sc.get("background"), sc.get("background")) or "living_room",
                               cast=cast, lines=lines,
                               audio_from=_num(sc.get("audio_from")), audio_to=_num(sc.get("audio_to")),
                               lighting=sc.get("lighting") if sc.get("lighting") in LIGHTING else "day",
                               music=_scene_music(sc.get("music")), seconds=min(60.0, _num(sc.get("seconds")) or 0.0),
                               card=None))
    if not any(sc["cast"] for sc in scenes):
        raise RenderError("Add at least one scene with a character in it.")
    return dict(title=str(tl.get("title") or "").strip(), characters=chars, scenes=scenes,
                kit=bool(tl["kit"]) if "kit" in tl else None,
                tts=tl.get("tts") or "auto", audio=audio, look3d=bool(tl.get("look3d", True)),
                captions=bool(tl.get("captions", True)), language=str(tl.get("language") or "hi"),
                cinematic=bool(tl.get("cinematic", True)),
                hook=" ".join(str(tl.get("hook") or "").split())[:80], effects=bool(tl.get("effects", True)))


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
    move: str = "auto"      # camera movement during the line (catalog.CAMERA_MOVES)
    lights: str = ""        # "on" / "off": the room light switches when this line starts
    popup: str = ""         # a phone-notification banner shown during this line
    sticker: str = ""       # a sticker that pops up next to the speaker
    src: tuple = None       # own-audio mode: (start, end) of this line in your audio file
    actor: str = ""         # a narrator line: the character the camera shows acting meanwhile
    actor_action: str = "idle"
    actor_emotion: str = "neutral"
    kadhai: str = ""        # the kadhai on the stove changes: fry, fire, cover, gas_off
    broll: str = ""         # cut away to an explainer animation / your picture while this line plays
    overlay: str = ""       # big bold text over the picture, from this line to the end of the scene
    prop: str = ""          # something the speaker holds from this line on ("none" puts it away)
    effect: str = ""        # a cartoon effect around the speaker: dizzy stars, "!", hearts, rain cloud...
    bag: str = ""           # the mystery bag: here, shake, open, photo, gone (bag.py)


@dataclass
class SceneT:
    bg: str
    cast: list
    start: float
    end: float
    lines: list = field(default_factory=list)
    card: str | None = None        # a text card / black screen instead of a scene
    card_style: str = "dark"
    card_sound: str = ""
    lighting: str = "day"          # day, dark (night, lights off) or phone (dark, lit by a phone screen)
    music: str = ""                # the music from this scene on ("" keeps the music, "none" stops it)


def _card_seconds(sc: dict) -> float:
    if sc["card_seconds"]:
        return max(0.6, min(8.0, sc["card_seconds"]))
    if sc["card_sound"]:
        import wave as _w
        from .fx import fx_wav
        try:
            with _w.open(str(fx_wav(sc["card_sound"]))) as w:
                return max(1.6, min(6.0, w.getnframes() / w.getframerate() + 0.3))
        except Exception:  # noqa: BLE001
            pass
    return 2.0 if sc["card"] else 1.2


def _line_extras(lt, ln: dict):
    lt.lights, lt.popup, lt.sticker = ln.get("lights", ""), ln.get("popup", ""), ln.get("sticker", "")
    lt.actor, lt.actor_action = ln.get("actor", ""), ln.get("actor_action", "idle")
    lt.actor_emotion = ln.get("actor_emotion", "neutral")
    lt.kadhai, lt.broll, lt.overlay = ln.get("kadhai", ""), ln.get("broll", ""), ln.get("overlay", "")
    lt.prop = ln.get("prop", "")
    lt.effect = ln.get("effect", "")
    lt.bag = ln.get("bag", "")
    lt.move = ln.get("move", "auto")
    return lt


def trim_empty(tl: dict, sched: list, total: float) -> tuple[list, float]:
    """Cut the end of a scene where everyone has already left the frame (run across, walked out, flew away) and
    nothing more is said or heard; later scenes move up."""
    fc = FlatComposer(tl, sched, 108, 192)
    shift = 0.0
    for sc in sched:
        if shift:
            sc.start, sc.end = sc.start - shift, sc.end - shift
            for ln in sc.lines:
                ln.start, ln.end = ln.start - shift, ln.end - shift
        if sc.card is not None or not sc.cast or not fc.handles(sc):
            continue
        t, empty_from = sc.end - 0.05, None
        while t > sc.start:
            if all(fc._walk(sc, cid, {"x": 0.0}, t) == "hidden" for cid in sc.cast):
                empty_from = t
                t -= 0.1
            else:
                break
        if empty_from is None:
            continue
        new_end = empty_from + 0.5
        if new_end > sc.end - 0.6 or any(ln.end > empty_from and (ln.text or ln.reaction) for ln in sc.lines):
            continue
        cut = sc.end - new_end
        sc.lines = [ln for ln in sc.lines if ln.start < new_end]
        for ln in sc.lines:
            ln.end = min(ln.end, new_end)
        sc.end = new_end
        shift += cut
    return sched, total - shift


def silent_clip(seconds: float) -> Clip:
    """A moment with no voice (a silent action beat)."""
    return Clip(None, seconds, [0.0] * (int(seconds * ENV_HZ) + 1), synthetic=False)


def make_clip(ln: dict, ch: dict, engine: str, warnings: list | None = None) -> Clip:
    """The audio of one line made by the app: its voice, an emotional sound, or the sound followed by the words."""
    sound = get_sound(ln["sound"], ch["voice"]) if ln["sound"] else None
    if not ln["text"]:                              # a reaction: only the emotional sound (or a silent beat)
        return sound or silent_clip(ln.get("hold") or 1.0)
    voice = ch["voice"]
    if engine == "gemini" and not voice.startswith("gemini:"):        # the Gemini voice that suits this look
        g = GEMINI_FOR_LOOK.get(ch["look"])
        voice = f"gemini:{g}" if g else voice
    elif engine == "sarvam" and not voice.startswith("sarvam:"):      # the Sarvam voice that suits this look
        s = SARVAM_FOR_LOOK.get(ch["look"])
        voice = f"sarvam:{s}" if s else voice
    c = get_clip(ln["text"], voice, engine, emotion=ln["emotion"], voice_pitch=ch.get("voice_pitch", 0),
                 voice_rate=ch.get("voice_rate", 0), voice_fx=ch.get("voice_fx", ""))
    if warnings is not None and c.warning and c.warning not in warnings:
        warnings.append(c.warning)
    return join_clips(sound, c) if sound else c     # the sound first, then the words


def choose_engine(tl: dict, warnings: list | None = None) -> str:
    """'best': Gemini's acting voices for the whole video when today's free Gemini lines cover every line that is
    not made yet; otherwise the Microsoft voices with emotion (never a mix, so nobody's voice changes mid-video)."""
    eng = tl.get("tts") or "auto"
    if eng != "best":
        return eng
    from . import gemini_tts, sarvam_tts
    from .tts import CACHE_DIR as _C, _key
    fallback = "sarvam" if sarvam_tts.ready() else "auto"     # natural Hindi when there is a Sarvam key
    if not gemini_tts.ready():
        return fallback
    by_id = {c["id"]: c for c in tl["characters"]}
    need = 0
    for sc in tl["scenes"]:
        for ln in sc["lines"]:
            if not ln["text"]:
                continue
            ch = by_id[ln["speaker"]]
            name = ch["voice"].split(":", 1)[1] if ch["voice"].startswith("gemini:") else GEMINI_FOR_LOOK.get(ch["look"], "Charon")
            if not (_C / "tts" / f"{_key('gemini-tag', ' '.join(ln['text'].split()), name, ln['emotion'])}.wav").exists():
                need += 1
    left = gemini_tts.lines_left()
    if need <= left:
        return "gemini"
    if warnings is not None:
        warnings.append(f"Voices: this video needs {need} new Gemini voice lines but only about {left} are left today "
                        "(free tier), so the " + ("Sarvam" if fallback == "sarvam" else "Microsoft voices with emotion")
                        + " voices were used. Lines already made with Gemini are kept for next time.")
    return fallback


def build_schedule(tl: dict, clip_for) -> tuple[list, float]:
    by_id = {c["id"]: c for c in tl["characters"]}
    t, out = 0.5, []
    for sc in tl["scenes"]:
        if sc.get("card") is not None:
            secs = _card_seconds(sc)
            out.append(SceneT("", [], t, t + secs, [], sc["card"], sc["card_style"], sc["card_sound"],
                              music=sc.get("music", "")))
            t += secs
            continue
        st = SceneT(sc["background"], list(sc["cast"]), t, t, lighting=sc.get("lighting", "day"),
                    music=sc.get("music", ""))
        t0 = t
        t += 0.25
        for ln in sc["lines"]:
            clip = clip_for(ln, by_id[ln["speaker"]])
            dur = max(clip.duration, ln.get("hold") or 0.0)          # "hold": the line lasts at least this long
            st.lines.append(_line_extras(LineT(ln["speaker"], ln["text"], ln["emotion"], ln["action"],
                                  t, t + dur, clip, None, not ln["text"] and bool(ln["sound"]), ln["shot"]),
                                  ln))
            t += dur + 0.18
        if not sc["lines"]:                      # a scene with only silent characters holds for a moment
            t += 2.0
        t += 0.4
        if sc.get("seconds") and t - t0 < sc["seconds"]:            # the scene's length from the script
            t = t0 + sc["seconds"]
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
        if sc.get("card") is not None:         # a card plays no part of your audio: a short silence instead
            secs = _card_seconds(sc)
            out.append(SceneT("", [], t, t + secs, [], sc["card"], sc["card_style"], sc["card_sound"]))
            parts.append((cursor, cursor + 0.02, secs - 0.02))
            t += secs
            continue
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
        st = SceneT(sc["background"], list(sc["cast"]), t, t, lighting=sc.get("lighting", "day"))
        for idx, ln in enumerate(speech):
            sfx = get_sound(ln["sound"], by_id[ln["speaker"]]["voice"]) if ln["sound"] else None
            ls, le = times.get(idx, (ln["start"], ln["end"]))
            ls, le = min(max(ls, a), b), min(max(le, a), b)
            if le <= ls:
                le = min(b, ls + 0.1)
            e = env[int(ls * ENV_HZ): int(le * ENV_HZ)]
            clip = Clip(Path(""), max(0.1, le - ls), _union(e, sfx.env) if sfx else e, synthetic=False)
            ln = dict(ln, _src=(ls, le))
            st.lines.append(_line_extras(LineT(ln["speaker"], ln["text"], ln["emotion"], ln["action"],
                                  t + (ls - a), t + (ls - a) + clip.duration, clip, sfx,
                                  not ln["text"] and bool(ln["sound"]), ln["shot"], ln["_src"]), ln))
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
        fxon = tl.get("effects", True)
        self.cuts = [sc.start for i, sc in enumerate(sched[1:], 1)            # scene changes: zoom punch
                     if sc.card_style != "black" and sched[i - 1].card_style != "black"
                     and not (sc.card is not None and sched[i - 1].card is not None)] if fxon else []
        self.hits = sorted([h for sc in sched for ln in sc.lines              # punch / slap / thrown chappal: shake
                            for h in fx_mod.hit_times(ln.action, ln.start, ln.end)] + overlays.throw_hits(sched)) \
            if fxon else []
        self.shakes = kitchen.shake_times(sched) if fxon else []           # the oil catching fire: a big shake
        self.bumps = stick.impact_times(sched) if fxon else []             # a slapstick fall / hit lands
        self._pics: dict = {}

    def line_at(self, t: float):
        sc = self.scene_at(t)
        return next((l for l in sc.lines if l.start <= t < l.end), None)

    def _broll(self, ln, t: float) -> Image.Image:
        """A cut-away while the line plays: an explainer animation, or your picture slowly zooming in."""
        a, b = kitchen.broll_span(ln)
        u = min(1.0, max(0.0, (t - a) / max(0.1, b - a)))
        if ln.broll in kitchen.EXPLAINERS:
            return kitchen.draw_explainer(self.w, self.h, u, t, ln.broll)
        bid = ln.broll[4:]
        if bid not in self._pics:
            try:
                self._pics[bid] = get_background(bid, self.w, self.h).convert("RGB")
            except Exception:  # noqa: BLE001  the picture is gone: show the scene instead
                self._pics[bid] = None
        pic = self._pics[bid]
        if pic is None:
            return self._frame(t)
        z = 1.0 + 0.1 * u
        cw, ch = self.w / z, self.h / z
        return pic.resize((self.w, self.h), Image.BILINEAR, box=((self.w - cw) / 2, (self.h - ch) / 2,
                                                                  (self.w + cw) / 2, (self.h + ch) / 2))

    def scene_at(self, t: float) -> SceneT:
        for sc in self.sched:
            if t < sc.end:
                return sc
        return self.sched[-1]

    def frame(self, t: float) -> Image.Image:
        cur = self.line_at(t)
        im = self._broll(cur, t) if cur is not None and cur.broll and t >= kitchen.broll_span(cur)[0] \
            else self._frame(t)
        sc = self.scene_at(t)
        for ln in sc.lines:                                   # notification banners and stickers
            if ln.popup:
                overlays.draw_popup(im, t, ln, self.w, self.h)
            if ln.sticker:
                overlays.draw_sticker(im, t, ln, self.w, self.h)
            if ln.action == "throw":
                overlays.draw_throw(im, t, ln, self.w, self.h)
        zoom, dx, dy = 1.0, 0.0, 0.0
        for c in self.cuts:                                   # zoom punch into each new scene
            u = (t - c) / 0.25
            if 0 <= u < 1:
                zoom = max(zoom, 1.0 + 0.14 * (1 - u) ** 2)
        for hgt in self.hits:                                 # shake when a punch or slap lands
            u = (t - hgt) / 0.22
            if 0 <= u < 1:
                amp = 16 * self.k * (1 - u)
                dx += amp * math.sin(t * 97)
                dy += amp * math.cos(t * 71)
                zoom = max(zoom, 1.035)
        for b in self.bumps:                                  # someone hits the floor / a wall
            u = (t - b) / 0.3
            if 0 <= u < 1:
                amp = 20 * self.k * (1 - u)
                dy += amp * math.cos(t * 90)
                dx += 0.4 * amp * math.sin(t * 77)
        for sh in self.shakes:                                # the fire flaring up
            u = (t - sh) / 0.6
            if 0 <= u < 1:
                amp = 24 * self.k * (1 - u)
                dx += amp * math.sin(t * 83)
                dy += amp * math.cos(t * 61)
                zoom = max(zoom, 1.05)
        if zoom == 1.0 and not dx and not dy:
            return im
        cw, ch = self.w / zoom, self.h / zoom
        x0 = min(max(0.0, (self.w - cw) / 2 + dx), self.w - cw)
        y0 = min(max(0.0, (self.h - ch) / 2 + dy), self.h - ch)
        return im.resize((self.w, self.h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

    def _card(self, sc, t: float) -> Image.Image:
        """A text card's picture (the words themselves are drawn by the subtitle renderer, for Hindi shaping)."""
        w, h = self.w, self.h
        if sc.card_style == "black":
            return Image.new("RGB", (w, h), (0, 0, 0))
        key = ("card", sc.card_style, w)
        if key not in self._sofa:
            im = Image.new("RGB", (w, h))
            d = ImageDraw.Draw(im)
            top, bot = ((24, 28, 52), (8, 10, 22)) if sc.card_style == "dark" else ((255, 214, 64), (255, 150, 40))
            for y in range(h):
                u = y / h
                d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bot)))
            if sc.card_style == "bright":                 # comic burst
                cx, cy = w / 2, h * 0.45
                for i in range(24):
                    a0, a1 = i * math.pi / 12, (i + 0.5) * math.pi / 12
                    d.polygon([(cx, cy), (cx + math.cos(a0) * h, cy + math.sin(a0) * h),
                               (cx + math.cos(a1) * h, cy + math.sin(a1) * h)], fill=(255, 236, 120))
            self._sofa[key] = im
        im = self._sofa[key].copy()
        if sc.card_style == "dark":                       # a small clock whose hand turns
            d = ImageDraw.Draw(im)
            cx, cy, r = w / 2, h * 0.36, w * 0.09
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(230, 230, 240), width=max(2, int(w * 0.008)))
            ang = -math.pi / 2 + (t - sc.start) * 4
            d.line([(cx, cy), (cx + math.cos(ang) * r * 0.75, cy + math.sin(ang) * r * 0.75)], fill=(255, 200, 80),
                   width=max(2, int(w * 0.01)))
            d.line([(cx, cy), (cx, cy - r * 0.5)], fill=(230, 230, 240), width=max(2, int(w * 0.012)))
        return im

    def _frame(self, t: float) -> Image.Image:
        sc = self.scene_at(t)
        if sc.card is not None:
            return self._card(sc, t)
        if self.flat.handles(sc):                                 # flat cartoon style with its own camera
            return self.flat.frame(sc, t)
        im = (get_background_3d if self.look3d else get_background)(sc.bg, self.w, self.h).copy()
        line = next((l for l in sc.lines if l.start <= t < l.end), None)
        xs, scale = layout(len(sc.cast))
        sx = xs[sc.cast.index(line.char)] if line and line.char in sc.cast else None

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


def make_ass(sched: list, w: int, h: int, font_family: str, captions: bool = True, hook: str = "",
             hook_end: float = 2.4, language: str = "hi") -> str:
    """Captions, the hook title and text-card titles, in one ASS subtitle file."""
    size, outline, margin_v = int(h * 0.05), max(2, int(h * 0.006)), int(h * 0.29)
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font_family},{size},&H0000D7FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,"
        f"{outline},1,2,{int(w * 0.06)},{int(w * 0.06)},{margin_v},1\n"
        f"Style: Hook,{font_family},{int(h * 0.068)},&H00FFFFFF,&H00FFFFFF,&H00141414,&H96000000,-1,0,0,0,100,100,0,0,1,"
        f"{int(outline * 1.8)},3,8,{int(w * 0.07)},{int(w * 0.07)},{int(h * 0.27)},1\n"
        f"Style: Card,{font_family},{int(h * 0.072)},&H00FFFFFF,&H00FFFFFF,&H00202020,&H96000000,-1,0,0,0,100,100,0,0,1,"
        f"{int(outline * 1.5)},2,5,{int(w * 0.08)},{int(w * 0.08)},0,1\n"
        f"Style: Over,{font_family},{int(h * 0.058)},&H00FFFFFF,&H00FFFFFF,&H002A1FD0,&H002A1FD0,-1,0,0,0,100,100,0,0,3,"
        f"{int(h * 0.012)},0,2,{int(w * 0.06)},{int(w * 0.06)},{int(h * 0.2)},1\n"
        f"Style: Explain,{font_family},{int(h * 0.046)},&H00FFFFFF,&H00FFFFFF,&H00301810,&H96000000,-1,0,0,0,100,100,0,0,1,"
        f"{int(outline * 1.4)},2,2,{int(w * 0.06)},{int(w * 0.06)},{int(h * 0.09)},1\n"
        + overlays.popup_ass_styles(w, h, font_family) + "\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    if hook:                                    # big opening title that pops in, then fades
        txt = hook.replace("{", "").replace("}", "")
        events.append(f"Dialogue: 1,{_ass_time(0.12)},{_ass_time(hook_end)},Hook,,0,0,0,,"
                      "{\\fad(80,300)\\fscx40\\fscy40\\t(0,180,\\fscx112\\fscy112)\\t(180,320,\\fscx100\\fscy100)}"
                      + txt)
    events += overlays.popup_ass_events(sched, w, h, _ass_time)
    for sc in sched:                            # text cards
        if sc.card:
            txt = sc.card.replace("{", "").replace("}", "")
            col = "{\\c&H202020&\\3c&HFFFFFF&}" if sc.card_style == "bright" else ""
            events.append(f"Dialogue: 2,{_ass_time(sc.start + 0.05)},{_ass_time(sc.end - 0.05)},Card,,0,0,0,,"
                          "{\\fad(120,150)\\fscx60\\fscy60\\t(0,200,\\fscx106\\fscy106)\\t(200,320,\\fscx100\\fscy100)}"
                          + col + txt)
    for sc in sched:                            # big bold text over the picture, until the scene ends
        for ln in sc.lines:
            if getattr(ln, "overlay", ""):
                parts = [x.strip().replace("{", "").replace("}", "") for x in ln.overlay.split("|") if x.strip()]
                if parts:
                    txt = parts[0] + "".join("\\N{\\fs%d}%s" % (int(h * 0.036), x) for x in parts[1:])
                    events.append(f"Dialogue: 3,{_ass_time(ln.start + 0.05)},{_ass_time(sc.end)},Over,,0,0,0,,"
                                  "{\\fad(150,200)\\fscx70\\fscy70\\t(0,220,\\fscx105\\fscy105)\\t(220,340,\\fscx100\\fscy100)}"
                                  + txt)
            if getattr(ln, "broll", "") in kitchen.EXPLAINERS:         # the explainer's words, step by step
                b0, b1 = kitchen.broll_span(ln)
                span = b1 - b0
                for a, b, txt in kitchen.explain_labels(ln.broll, language):
                    events.append(f"Dialogue: 2,{_ass_time(b0 + a * span)},{_ass_time(b0 + b * span)},"
                                  "Explain,,0,0,0,,{\\fad(120,120)}" + txt)
    for sc in (sched if captions else []):
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
    y = int(h * 0.71) - int(size * 1.35) * len(lines)          # lower middle, like the video's captions
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
            if not ln.clip.wav:                   # a silent beat
                continue
            s = read_samples(ln.clip.wav)
            off = int(ln.start * RATE)
            end = min(n, off + len(s))
            buf[off:end] = s[: end - off]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf.tobytes())


def _no_cancel(progress):
    def p(stage, frac):
        try:
            progress(stage, frac)
        except RenderCancelled:
            pass
    return p


# ------------------------------------------------------------------ parallel drawing
_WCOMP = None


def _init_worker(tl, sched, w, h, ss):
    global _WCOMP
    _WCOMP = Composer(tl, sched, w, h, ss)


def _draw_frame(t: float) -> bytes:
    return _WCOMP.frame(t).tobytes()


def worker_count(frames: int) -> int:
    """How many processes draw frames: one per spare CPU (FFmpeg needs one), only for longer videos.
    Set SHORTS_WORKERS=1 to turn it off."""
    import os
    env = os.environ.get("SHORTS_WORKERS")
    if env and env.isdigit():
        return max(1, int(env))
    cpus = os.cpu_count() or 1
    # Measured on a 2-core / 4-thread laptop: no gain, because FFmpeg's encoder already uses every core.
    # Machines with 6 or more threads have spare cores, so they draw in parallel.
    return min(4, cpus // 2) if cpus >= 6 and frames >= 90 else 1


def _draw_all(comp, tl, sched, w, h, ss, fps, frames, write, progress):
    """Draw every frame (in parallel when it helps) and hand them to write() in order."""
    n = worker_count(frames)
    if n > 1:
        import multiprocessing as mp
        try:
            with mp.get_context("spawn").Pool(n, initializer=_init_worker, initargs=(tl, sched, w, h, ss)) as pool:
                batch = n * 6                      # a few frames per worker at a time keeps memory small
                for b0 in range(0, frames, batch):
                    ts = [i / fps for i in range(b0, min(frames, b0 + batch))]
                    for buf in pool.map(_draw_frame, ts, chunksize=2):
                        write(buf)
                    progress("Drawing frames", min(frames, b0 + batch) / frames)
            return
        except BrokenPipeError:
            raise
        except Exception as e:                     # noqa: BLE001  fall back to one process (Cancel is not caught)
            print("Parallel drawing failed, drawing in one process:", e)
            return _draw_range(comp, fps, frames, write, progress, start=getattr(write, "count", 0))
    _draw_range(comp, fps, frames, write, progress)


def _draw_range(comp, fps, frames, write, progress, start=0):
    for i in range(start, frames):
        write(comp.frame(i / fps).tobytes())
        if i % 5 == 0:
            progress("Drawing frames", i / frames)


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
        engine = choose_engine(tl, warnings)
        n_lines = max(1, sum(len(sc["lines"]) for sc in tl["scenes"]))
        done = [0]

        def clip_for(ln, ch):
            progress("Making voices", done[0] / n_lines)      # (also where Cancel is noticed)
            done[0] += 1
            return make_clip(ln, ch, engine, warnings)

        try:
            sched, total = build_schedule(tl, clip_for)
        except SoundError as e:
            raise RenderError(str(e))
        sched, total = trim_empty(tl, sched, total)    # no empty screen after everyone has left
        voice_input = "voice.wav"
    music_path = None
    if au["music_id"]:
        try:
            music_path = str(get_audio(au["music_id"])["path"])
        except AudioError as e:
            raise RenderError("Background music: " + str(e))
    elif au["music_builtin"] or any(sc.music for sc in sched):
        progress("Making music", 0.0)
        music_path = str(fx_mod.music_wav(au["music_builtin"])) if au["music_builtin"] else None
    music_parts = None
    if not au["music_id"] and any(sc.music for sc in sched):     # a scene changes the music: one track for all
        cur, music_parts = au["music_builtin"], []
        for sc in sched:
            if sc.music:
                cur = None if sc.music == "none" else sc.music
            if music_parts and music_parts[-1][2] == cur:
                music_parts[-1] = (music_parts[-1][0], sc.end, cur)
            else:
                music_parts.append((sc.start if music_parts else 0.0, sc.end, cur))
    if total > 180:
        warnings.append("This video is longer than 3 minutes, so YouTube will not treat it as a Short.")

    w, h, fps = q["w"], q["h"], q["fps"]
    comp = Composer(tl, sched, w, h, q["ss"])
    stick_ids = {c["id"] for c in tl["characters"] if LOOKS.get(c["look"], {}).get("flat", {}).get("kind") == "stick"}
    on_screen = {c["id"] for c in tl["characters"] if c["look"] not in NARRATOR_LOOKS}
    stick_video = bool(stick_ids) and stick_ids >= on_screen      # a stickman comedy: music carries it
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
        hook_end = min(2.4, total)
        (work / "captions.ass").write_text(make_ass(sched, w, h, family, tl["captions"], tl["hook"], hook_end,
                                                    tl["language"]), encoding="utf-8")
        events = []                               # sound effects: hits, scene whooshes, the hook's pop
        if tl["effects"]:
            thrown = set(round(x, 3) for x in overlays.throw_hits(sched))
            events += [(hgt, "chappal" if round(hgt, 3) in thrown else
                        "punch" if any(ln.action == "punch" and ln.start <= hgt < ln.end
                                       for sc in sched for ln in sc.lines) else "slap", 1.0)
                       for hgt in comp.hits]
            events += [(h - 0.42, "whoosh", 0.6) for h in thrown]
            events += [(c - 0.15, "whoosh", 0.55) for c in comp.cuts]
            if tl["hook"]:
                events.append((0.1, "pop", 0.6))
            events += kitchen.sound_events(sched)          # sizzle, fire, thali clang, gas knob, footsteps, splash
            events += stick.sound_events(sched, stick_ids)  # slip, thud, bonk, tweeting birds, zip, crash...
            events += bag.sound_events(sched)              # the mystery bag rustling, popping open
        events += [(sc.start + 0.05, sc.card_sound, 1.0) for sc in sched if sc.card is not None and sc.card_sound]
        events += [(ln.start, "click", 0.9) for sc in sched for ln in sc.lines if getattr(ln, "lights", "")]
        events += [(ln.start + 0.05, "ping", 0.9) for sc in sched for ln in sc.lines if ln.popup]
        events += [(ln.start + 0.02, "pop", 0.6) for sc in sched for ln in sc.lines if ln.sticker]
        events += [(ln.start, ln.sound_fx, 0.9) for sc in sched for ln in sc.lines if getattr(ln, "sound_fx", "")]
        fx_idx = None

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
        nxt = 2 + (1 if sfx_idx else 0)
        if events:
            fx_mod.build_track(events, total, work / "fx.wav")
            cmd += ["-i", "fx.wav"]
            fx_idx, nxt = nxt, nxt + 1
        if music_parts:
            fx_mod.build_music_track(music_parts, total, work / "music.wav")
            music_idx = nxt
            cmd += ["-i", "music.wav"]
        elif music_path:
            music_idx = nxt
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
        if fx_idx:
            graph += f";[{fx_idx}:a]{norm}[fxs]"
            streams.append(("fxs", 0.9))
        if music_idx:
            graph += f";[{music_idx}:a]{norm}[mus]"
            mvol, mname = au["music_volume"], "mus"
            if stick_video:                    # no words: the music is louder, and dips under each sound effect
                mvol = max(mvol, 0.55)
                if fx_idx:
                    graph = graph.replace(f"[{fx_idx}:a]{norm}[fxs]", f"[{fx_idx}:a]{norm},asplit=2[fxs][fxk]")
                    graph += ";[mus][fxk]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=350[musd]"
                    mname = "musd"
            streams.append((mname, mvol))
        if len(streams) == 1:
            audio_graph = graph.rsplit("[voice]", 1)[0] + "[aout]"
        else:
            weights = " ".join(f"{w:.2f}" for _, w in streams)
            audio_graph = (graph + ";" + "".join(f"[{nm}]" for nm, _ in streams) +
                           f"amix=inputs={len(streams)}:duration=first:weights='{weights}',"
                           f"volume={sum(w for _, w in streams):.2f}[aout]")
        vf = "ass=captions.ass:fontsdir=fonts" if (tl["captions"] or tl["hook"] or any(sc.card for sc in sched) or
                                                   any(ln.popup or ln.overlay or ln.broll for sc in sched
                                                       for ln in sc.lines)) else "null"
        cmd += ["-filter_complex", f"[0:v]{vf}[vout];{audio_graph}",
                "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
        log = open(work / "ffmpeg.log", "wb")
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log, cwd=work)
        frames = int(math.ceil(total * fps))

        def write(buf):
            proc.stdin.write(buf)
            write.count += 1
        write.count = 0
        try:
            _draw_all(comp, tl, sched, w, h, q["ss"], fps, frames, write, progress)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        except BaseException:                       # cancelled (or failed): stop FFmpeg, remove the half-made file
            proc.kill()
            proc.wait()
            log.close()
            out.unlink(missing_ok=True)
            raise
        progress = _no_cancel(progress)             # the frames are done: finish the video even if Cancel comes now
        if any(LOOKS.get(c["look"], {}).get("style") == "3d" for c in tl["characters"]):
            from . import three_d
            if three_d.status() and three_d.status() not in comp.flat.warnings:
                comp.flat.warnings.append(three_d.status())
        progress("Encoding", 0.99)
        for msg in comp.flat.warnings:
            if msg not in warnings:
                warnings.append(msg)
        code = proc.wait()
        log.close()
        if code != 0 or not out.exists():
            tail = (work / "ffmpeg.log").read_text(errors="ignore")[-600:]
            raise RenderError("FFmpeg failed: " + tail)
        res = dict(file=out.name, seconds=round(total, 1), warnings=warnings, size=[w, h])
        if tl.get("kit") if tl.get("kit") is not None else quality == "final":      # subtitles, thumbnails and YouTube text next to the video
            progress("Making thumbnails and YouTube text", 0.995)
            try:
                from .publish import make_kit
                big = comp if w == 1080 else Composer(tl, sched, 1080, 1920, 2)
                res.update(make_kit(tl, sched, out, big.frame))
            except Exception as e:  # noqa: BLE001  the video itself is fine
                warnings.append(f"Could not make the thumbnails / YouTube text: {e}")
        progress("Done", 1.0)
        return res
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
