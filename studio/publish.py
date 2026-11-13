"""Everything to upload next to the video: subtitles (SRT), two thumbnails and YouTube title / description / hashtags.

Made after a full-quality render (and on request for any video):
  <video>.srt            the dialogue with times, for YouTube's own subtitle track
  <video>-thumb.png      1080 x 1920 (Shorts), the most dramatic moment with the title on it
  <video>-thumb-wide.png 1280 x 720 (normal videos / community posts)
  <video>-youtube.txt    title, description and hashtags (written by Gemini when a key is set)
Titles are drawn by FFmpeg's subtitle renderer, so Hindi letters are shaped correctly.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageFont

from .config import OUTPUT_DIR, find_devanagari_font, find_ffmpeg

STRONG = ("angry", "shocked", "surprised", "crying", "laughing", "scared", "excited")


# ----------------------------------------------------------------- subtitles
def _srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(sched: list, path: Path) -> Path:
    rows, n = [], 0
    for sc in sched:
        for ln in sc.lines:
            if not ln.text.strip():
                continue
            n += 1
            rows.append(f"{n}\n{_srt_time(ln.start)} --> {_srt_time(ln.end)}\n{ln.text.strip()}\n")
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


# ----------------------------------------------------------------- thumbnails
def best_moment(sched: list) -> float:
    """A dramatic moment: a strong-emotion line if there is one, else the middle of the longest line."""
    lines = [ln for sc in sched for ln in sc.lines]
    if not lines:
        return 0.5
    later = [ln for sc in sched for ln in sc.lines[1:]]        # a scene's first line is a wide shot: prefer closer
    strong = [ln for ln in later if ln.emotion in STRONG] or [ln for ln in lines if ln.emotion in STRONG]
    ln = strong[0] if strong else max(lines, key=lambda x: x.end - x.start)
    return ln.start + min(0.7, (ln.end - ln.start) / 2)


def _ass_title(w: int, h: int, text: str, family: str, size: int, align: int, margin_l: int, margin_r: int,
               margin_v: int) -> str:
    text = text.replace("{", "").replace("}", "")
    return ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: T,{family},{size},&H0000E6FF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,"
            f"{max(3, size // 9)},4,{align},{margin_l},{margin_r},{margin_v},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,{text}\n")


def _burn_title(src: Path, dst: Path, ass: str, work: Path):
    ffmpeg = find_ffmpeg()
    font = find_devanagari_font()
    fonts = work / "fonts"
    fonts.mkdir(exist_ok=True)
    if font:
        shutil.copy(font, fonts / ("t" + font.suffix))
    (work / "t.ass").write_text(ass, encoding="utf-8")
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-vf", "ass=t.ass:fontsdir=fonts",
                        "-frames:v", "1", str(dst)], capture_output=True, cwd=work)
    if r.returncode != 0 or not dst.exists():
        shutil.copy(src, dst)                      # without the title rather than nothing


def make_thumbnails(frame: Image.Image, title: str, base: Path) -> tuple[Path, Path]:
    font = find_devanagari_font()
    family = "Arial"
    if font:
        try:
            family = ImageFont.truetype(str(font), 20).getname()[0]
        except Exception:
            pass
    work = Path(tempfile.mkdtemp(prefix="thumb_"))
    try:
        v = frame.convert("RGB").resize((1080, 1920), Image.LANCZOS)
        v = ImageEnhance.Color(ImageEnhance.Contrast(v).enhance(1.08)).enhance(1.15)
        v.save(work / "v.png")
        tall = base.with_name(base.stem + "-thumb.png")
        _burn_title(work / "v.png", tall, _ass_title(1080, 1920, title, family, 120, 2, 60, 60, 170), work)
        wide = Image.new("RGB", (1280, 720))
        bg = v.resize((1280, int(1280 * 1920 / 1080))).crop((0, 400, 1280, 1120)).filter(ImageFilter.GaussianBlur(24))
        wide.paste(ImageEnhance.Brightness(bg).enhance(0.55), (0, 0))
        fg = v.resize((405, 720), Image.LANCZOS)
        wide.paste(fg, (40, 0))
        wide.save(work / "w.png")
        wide_p = base.with_name(base.stem + "-thumb-wide.png")
        _burn_title(work / "w.png", wide_p, _ass_title(1280, 720, title, family, 84, 6, 480, 40, 0), work)
        return tall, wide_p
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ----------------------------------------------------------------- YouTube text
def youtube_text(tl: dict, sched: list) -> dict:
    title = tl.get("title") or "Funny short"
    lines = [f"{ln.char}: {ln.text}" for sc in sched for ln in sc.lines if ln.text.strip()]
    fallback = dict(title=f"{title} #shorts"[:100],
                    description=(tl.get("hook") or title) + "\n\n#shorts #comedy #cartoon #hindi",
                    hashtags=["#shorts", "#comedy", "#cartoon", "#hindi", "#funny"], by="app")
    from .script import _env, _gemini, _parse_json, ScriptError
    if not _env("GEMINI_API_KEY") or not lines:
        return fallback
    lang = {"hi": "Hindi in Devanagari script", "hinglish": "Hinglish in Roman letters", "en": "English"}.get(
        tl.get("language", "hi"), "Hindi in Devanagari script")
    prompt = f"""You write YouTube Shorts metadata for a short cartoon video.
Video title idea: {title}
Hook: {tl.get("hook", "")}
Dialogue:
{chr(10).join(lines[:40])}

Write in {lang}. Reply with JSON only:
{{"title": "catchy title, at most 70 characters, may use 1 emoji, end with #shorts",
  "description": "2 to 3 short lines that make people watch, then a call to like and subscribe",
  "hashtags": ["#shorts", "... 6 to 10 relevant hashtags, mixing Hindi and English words"]}}"""
    try:
        data = _parse_json(_gemini(prompt))
        tags = [t if str(t).startswith("#") else "#" + str(t) for t in data.get("hashtags", [])][:12]
        if "#shorts" not in [t.lower() for t in tags]:
            tags.insert(0, "#shorts")
        return dict(title=str(data.get("title") or fallback["title"])[:100],
                    description=str(data.get("description") or fallback["description"]), hashtags=tags, by="gemini")
    except (ScriptError, ValueError, KeyError, OSError):
        return fallback


def make_kit(tl: dict, sched: list, video: Path, frame_at) -> dict:
    """frame_at(t) -> full-size PIL image of the video at t seconds."""
    base = video.with_suffix("")
    srt = write_srt(sched, base.with_suffix(".srt"))
    yt = youtube_text(tl, sched)
    shown = tl.get("hook") or tl.get("title") or ""
    shown = re.sub(r"#\S+", "", shown).strip()
    tall, wide = make_thumbnails(frame_at(best_moment(sched)), shown, base.with_suffix(".png"))
    txt = base.with_name(base.stem + "-youtube.txt")
    txt.write_text(f"TITLE\n{yt['title']}\n\nDESCRIPTION\n{yt['description']}\n\n{' '.join(yt['hashtags'])}\n",
                   encoding="utf-8")
    return dict(srt=srt.name, thumb=tall.name, thumb_wide=wide.name, youtube=yt, youtube_file=txt.name)


def list_videos(n: int = 12) -> list[dict]:
    """The newest videos in the output folder, with their kit files when they exist."""
    out = []
    for p in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:n]:
        b = p.with_suffix("")
        item = dict(file=p.name, size_mb=round(p.stat().st_size / 1e6, 1))
        for key, path in (("srt", b.with_suffix(".srt")), ("thumb", b.with_name(b.stem + "-thumb.png")),
                          ("thumb_wide", b.with_name(b.stem + "-thumb-wide.png")),
                          ("youtube_file", b.with_name(b.stem + "-youtube.txt"))):
            if path.exists():
                item[key] = path.name
        yt = b.with_name(b.stem + "-youtube.txt")
        if yt.exists():
            item["youtube_text"] = yt.read_text(encoding="utf-8")
        out.append(item)
    return out


def kit_json(kit: dict) -> str:
    return json.dumps(kit, ensure_ascii=False)
