"""One click from an idea to a finished video, and batch mode (many ideas, one video each).

make_video(): script (Gemini when a key is set, else the basic split) -> music picked to fit the story -> voices ->
render. It returns the render result plus the timeline, so the app can open it as a project and you can edit it.
"""
from __future__ import annotations

from . import script as script_mod
from .render import render_video

MOODS_SAD = {"sad", "crying", "worried", "bored"}
MOODS_TENSE = {"angry", "scared", "shocked", "disgusted"}


def pick_music(scenes: list) -> str:
    bgs = [sc.get("background") for sc in scenes]
    if "flat_nark" in bgs:
        return "hell"
    if "flat_swarg" in bgs:
        return "heaven"
    emos = [ln.get("emotion") for sc in scenes for ln in sc.get("lines", [])]
    if not emos:
        return "happy"
    sad = sum(e in MOODS_SAD for e in emos) / len(emos)
    tense = sum(e in MOODS_TENSE for e in emos) / len(emos)
    if sad > 0.4:
        return "emotional"
    if tense > 0.4:
        return "suspense"
    return "comedy" if len(emos) % 2 else "happy"


def make_video(idea: str, characters: list, opts: dict, progress=None) -> dict:
    progress = progress or (lambda stage, frac: None)
    language = opts.get("language", "hi")
    provider = opts.get("provider") or ("gemini" if script_mod._env("GEMINI_API_KEY") else "basic")
    progress("Writing the script", 0.02)
    draft = script_mod.generate(idea, characters, language, int(opts.get("seconds", 30)), provider)
    music = opts.get("music", "auto")
    if music == "auto":
        music = pick_music(draft["scenes"])
    tl = dict(title=draft["title"] or idea[:40], hook=draft.get("hook", ""), scenario=idea, language=language,
              characters=characters, scenes=draft["scenes"], tts=opts.get("tts", "auto"),
              captions=opts.get("captions", True), effects=opts.get("effects", True), look3d=opts.get("look3d", True),
              audio=dict(mode="tts", music_builtin=music or "", music_volume=opts.get("music_volume", 18)))
    res = render_video(tl, opts.get("quality", "preview"),
                       lambda stage, frac: progress(stage, 0.05 + 0.95 * frac))
    res["timeline"] = tl
    return res


def make_batch(ideas: list, characters: list, opts: dict, progress=None) -> dict:
    progress = progress or (lambda stage, frac: None)
    ideas = [i.strip() for i in ideas if i and i.strip()][:20]
    done, failed = [], []
    for k, idea in enumerate(ideas):
        def sub(stage, frac, k=k):
            progress(f"Video {k + 1} of {len(ideas)}: {stage}", (k + frac) / len(ideas))
        try:
            r = make_video(idea, characters, opts, sub)
            done.append(dict(idea=idea, **{x: r.get(x) for x in ("file", "seconds", "srt", "thumb", "thumb_wide",
                                                                   "youtube", "warnings")}))
        except Exception as e:  # noqa: BLE001  one bad idea should not stop the rest
            failed.append(dict(idea=idea, error=str(e)))
    return dict(videos=done, failed=failed)
