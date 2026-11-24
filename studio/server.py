"""Tiny local web server (standard library only). Serves the UI and a JSON API."""
from __future__ import annotations

import json
import mimetypes
import re
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from . import audio as audio_mod
from . import script as script_mod
from .backgrounds import folder_info, list_backgrounds
from .catalog import ACTION_LABELS, DEFAULT_VOICE, EMOTIONS, LOOKS, SHOT_LABELS, SOUND_EMOTIONS, SOUND_LABELS, VOICES
from .config import OUTPUT_DIR, PROJECTS_DIR, UPLOADS_DIR, WEB_DIR, find_devanagari_font, find_ffmpeg
from .render import RenderCancelled, RenderError, make_clip, normalize, render_still, render_video
from .sfx import SoundError, get_sound
from .tts import TTSError, get_clip

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()



def _cast_order(look_id: str) -> int:
    """The Cast menu in the order of catalog.CAST (Lalit, Rahul, Deepak, Dadaji...)."""
    from .catalog import CAST
    return CAST.index(look_id) if look_id in CAST else len(CAST)

def _has_edge() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


def assets_payload() -> dict:
    font = find_devanagari_font()
    return {
        "backgrounds": list_backgrounds(),
        "bg_folder": folder_info(),
        "heights": [{"id": k, "label": v} for k, v in __import__("studio.catalog", fromlist=["x"]).HEIGHTS.items()],
        "builds": [{"id": k, "label": v} for k, v in __import__("studio.catalog", fromlist=["x"]).BUILDS.items()],
        "outfits": [{"id": k, "label": ("Outfit: " + k.replace("_", " ")) if k else v} for k, v in
                    __import__("studio.catalog", fromlist=["x"]).OUTFIT_COLORS.items()],
        "props": [{"id": k, "label": v} for k, v in __import__("studio.catalog", fromlist=["x"]).PROP_LABELS.items()],
        "looks": [{"id": k, "label": v["label"], "female": bool(v.get("female")), "flat": v.get("style") == "flat"}
                  for k, v in sorted(LOOKS.items(), key=lambda kv: _cast_order(kv[0])) if not v.get("hidden")],
        "voice_fx": [{"id": k, "label": v} for k, v in __import__("studio.catalog", fromlist=["x"]).VOICE_FX_LABELS.items()],
        "shots": [{"id": k, "label": v} for k, v in SHOT_LABELS.items()],
        "stickers": list(__import__("studio.overlays", fromlist=["x"]).STICKER_KINDS),
        "music": [{"id": k, "label": v} for k, v in __import__("studio.fx", fromlist=["x"]).MUSIC_LABELS.items()],
        "explainers": [{"id": k, "label": v} for k, v in __import__("studio.kitchen", fromlist=["x"]).EXPLAINERS.items()],
        "voices": VOICES, "default_voice": DEFAULT_VOICE,
        "voice_tune": {k: list(v) for k, v in __import__("studio.catalog", fromlist=["x"]).VOICE_TUNE.items()},
        "emotions": EMOTIONS,
        "actions": [{"id": k, "label": ("Comedy: " + v) if k in __import__("studio.catalog", fromlist=["x"]).SLAPSTICK_LABELS
                     else v} for k, v in ACTION_LABELS.items()],
        "effects": [{"id": k, "label": v} for k, v in __import__("studio.catalog", fromlist=["x"]).EFFECT_LABELS.items()],
        "bag_states": [{"id": k, "label": v} for k, v in __import__("studio.bag", fromlist=["x"]).BAG_LABELS.items()],
        "sounds": [{"id": k, "label": v} for k, v in SOUND_LABELS.items()], "sound_emotions": SOUND_EMOTIONS,
        "script_providers": script_mod.provider_status(),
        "system": {"gemini_voices_left": __import__("studio.gemini_tts", fromlist=["x"]).lines_left(),
                   "gemini": script_mod.provider_status()[0]["ready"], "ffmpeg": bool(find_ffmpeg()), "edge_tts": _has_edge(), "font": font.name if font else None},
    }


def _start_job(fn, *args) -> str:
    """Run fn(*args, progress) in the background; the app polls /api/jobs/<id>."""
    job_id = uuid.uuid4().hex[:10]
    with LOCK:
        JOBS[job_id] = {"status": "running", "stage": "Starting", "progress": 0.0}

    def progress(stage, frac):
        _progress(job_id, stage, frac)

    def run():
        try:
            res = fn(*args, progress)
            with LOCK:
                JOBS[job_id].update(status="done", result=res, progress=1.0, stage="Done")
        except RenderCancelled:
            with LOCK:
                JOBS[job_id].update(status="cancelled", stage="Cancelled")
        except Exception as e:  # shown in the UI
            traceback.print_exc()
            with LOCK:
                JOBS[job_id].update(status="error", error=str(e))
    threading.Thread(target=run, daemon=True).start()
    return job_id


def _progress(job_id: str, stage: str, frac: float):
    """Report progress; stops the job (RenderCancelled) when you pressed Cancel."""
    with LOCK:
        job = JOBS[job_id]
        if job.get("cancel"):
            raise RenderCancelled()
        job.update(stage=stage, progress=round(frac, 3))


def _run_job(job_id: str, tl: dict, quality: str):
    def progress(stage, frac):
        _progress(job_id, stage, frac)
    try:
        res = render_video(tl, quality, progress)
        with LOCK:
            JOBS[job_id].update(status="done", result=res, progress=1.0, stage="Done")
    except RenderCancelled:
        with LOCK:
            JOBS[job_id].update(status="cancelled", stage="Cancelled")
    except Exception as e:  # shown in the UI
        traceback.print_exc()
        with LOCK:
            JOBS[job_id].update(status="error", error=str(e))


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w\- ]+", "", name, flags=re.U).strip()[:60]


class Handler(BaseHTTPRequestHandler):
    server_version = "ShortsStudio/1.0"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    # ------------------------------------------------------------ helpers
    def _send(self, code: int, body: bytes, ctype: str = "application/json", extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _file(self, path: Path, download: bool = False):
        if not path.is_file():
            return self._json({"error": "Not found"}, 404)
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        size, start, end, code = len(data), 0, len(data) - 1, 200
        extra = {"Accept-Ranges": "bytes"}
        rng = self.headers.get("Range")
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
            if m.group(1) == "" and m.group(2):
                start, end = max(0, size - int(m.group(2))), size - 1
            code = 206
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        if download:
            extra["Content-Disposition"] = f'attachment; filename="{path.name}"'
        self._send(code, data[start:end + 1], ctype, extra)

    # --------------------------------------------------------------- routes
    def do_GET(self):
        path = unquote(self.path.split("?")[0])
        try:
            if path == "/api/assets":
                return self._json(assets_payload())
            if path.startswith("/api/jobs/"):
                with LOCK:
                    job = JOBS.get(path.rsplit("/", 1)[1])
                return self._json(job or {"error": "Unknown job"}, 200 if job else 404)
            if path == "/api/script_format":                    # the format to paste into another AI app
                from urllib.parse import parse_qs, urlparse
                from . import script_format
                q = parse_qs(urlparse(self.path).query)
                if q.get("kind", [""])[0] == "stickman":      # no-dialogue stickman comedy
                    text = script_format.build_stick_format(q.get("idea", [""])[0],
                                                            int(float(q.get("seconds", ["30"])[0] or 30)))
                else:
                    text = script_format.build_format(q.get("idea", [""])[0], q.get("language", ["hi"])[0],
                                                      int(float(q.get("seconds", ["45"])[0] or 45)))
                return self._json({"text": text})
            if path == "/api/backgrounds":                      # look in the backgrounds folders again
                return self._json({"backgrounds": list_backgrounds(True), "bg_folder": folder_info()})
            if path == "/api/videos":                           # newest videos with their kit files
                from .publish import list_videos
                return self._json({"videos": list_videos()})
            if path == "/api/projects":
                names = sorted(p.stem for p in PROJECTS_DIR.glob("*.json"))
                return self._json({"projects": names})
            if path.startswith("/api/projects/"):
                p = PROJECTS_DIR / (_safe_name(path.rsplit("/", 1)[1]) + ".json")
                return self._file(p)
            if path.startswith("/audio/"):
                return self._file(UPLOADS_DIR / Path(path).name)
            if path.startswith("/video/") or path.startswith("/download/"):
                name = Path(path).name
                return self._file(OUTPUT_DIR / name, download=path.startswith("/download/"))
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            target = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
                return self._json({"error": "Not found"}, 404)
            return self._file(target)
        except Exception as e:
            traceback.print_exc()
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/audio/upload":                      # raw file bytes, not JSON
                meta = audio_mod.save_upload(self.rfile, int(self.headers.get("Content-Length") or 0),
                                             self.headers.get("X-Filename", "audio"))
                return self._json({"id": meta["id"], "name": meta["name"], "seconds": meta["seconds"],
                                   "url": f"/audio/{meta['id']}{meta['ext']}"})
            data = self._body()
            if path == "/api/audio/match":
                return self._json(audio_mod.match_lines(data.get("id", ""), int(data.get("lines", 0)),
                                                        float(data.get("pause", 0.45))))
            if path == "/api/audio/peaks":
                return self._json(audio_mod.peaks(data.get("id", "")))
            if path == "/api/audio/transcribe":                 # captions from your audio, one per range
                from .transcribe import transcribe_many
                texts, warn = transcribe_many(data.get("id", ""), data.get("ranges", []), data.get("language", "hi"))
                return self._json({"texts": texts, "warning": warn})
            if path == "/api/audio/segments":
                return self._json({"segments": audio_mod.speech_segments(data.get("id", ""), float(data.get("pause", 0.45)))})
            if path == "/api/open_backgrounds":                 # show your backgrounds folder (this computer)
                info = folder_info()
                import os
                if os.name == "nt" and self.client_address[0] in ("127.0.0.1", "::1"):
                    os.startfile(info["folder"])               # noqa: S606  opens File Explorer
                    return self._json({"opened": True, **info})
                return self._json({"opened": False, **info})
            if path == "/api/import_script":                    # a full screenplay -> scenes
                from . import script_format
                if script_format.is_format(data.get("text", "")):  # our own format: read exactly, no AI
                    return self._json(script_format.parse(data.get("text", "")))
                return self._json(script_mod.import_screenplay(data.get("text", ""), data.get("provider", "gemini")))
            if path == "/api/export_format":                    # your project -> the script format
                from . import script_format
                return self._json({"text": script_format.export(data.get("timeline") or {})})
            if path == "/api/script":
                res = script_mod.generate(data.get("scenario", ""), data.get("characters", []),
                                          data.get("language", "hi"), int(data.get("seconds", 45)),
                                          data.get("provider", "gemini"))
                return self._json(res)
            if path == "/api/frame":
                png = render_still(data["timeline"], int(data.get("scene", 0)), int(data.get("line", 0)),
                                   int(data.get("width", 270)))
                return self._send(200, png, "image/png")
            if path == "/api/sample":
                clip = get_clip(data.get("text", "") or "नमस्ते", data.get("voice", DEFAULT_VOICE),
                                "auto" if data.get("engine") == "best" else data.get("engine", "auto"),
                                emotion=data.get("emotion") or "neutral",
                                voice_pitch=int(data.get("pitch") or 0), voice_rate=int(data.get("rate") or 0),
                                voice_fx=data.get("fx") or "")
                headers = {"X-Warning": clip.warning.encode("ascii", "ignore").decode()} if clip.warning else {}
                return self._send(200, clip.wav.read_bytes(), "audio/wav", headers)
            if path == "/api/sound":                              # hear one emotional sound
                clip = get_sound(data.get("sound", ""), data.get("voice", DEFAULT_VOICE))
                return self._send(200, clip.wav.read_bytes(), "audio/wav")
            if path == "/api/voices":
                tl = normalize(data["timeline"])
                by_id = {c["id"]: c for c in tl["characters"]}
                rows, warnings, total = [], [], 0.0
                for si, sc in enumerate(tl["scenes"]):
                    for li, ln in enumerate(sc["lines"]):
                        clip = make_clip(ln, by_id[ln["speaker"]], tl["tts"])
                        total += clip.duration
                        if clip.warning and clip.warning not in warnings:
                            warnings.append(clip.warning)
                        rows.append({"scene": si, "line": li, "seconds": round(clip.duration, 1),
                                     "silent": clip.synthetic})
                return self._json({"rows": rows, "total": round(total, 1), "warnings": warnings})
            if path in ("/api/autopilot", "/api/batch"):          # idea(s) -> finished video(s)
                from . import autopilot
                chars = data.get("characters") or []
                if not chars:
                    return self._json({"error": "Add at least one character in the Cast step."}, 400)
                opts = data.get("options") or {}
                if path == "/api/autopilot":
                    if not str(data.get("idea", "")).strip():
                        return self._json({"error": "Write your idea first."}, 400)
                    return self._json({"job": _start_job(autopilot.make_video, data["idea"], chars, opts)})
                ideas = [i for i in data.get("ideas", []) if str(i).strip()]
                if not ideas:
                    return self._json({"error": "Write at least one idea, one per line."}, 400)
                return self._json({"job": _start_job(autopilot.make_batch, ideas, chars, opts)})
            if path.startswith("/api/jobs/") and path.endswith("/cancel"):     # the Cancel button
                with LOCK:
                    job = JOBS.get(path.split("/")[3])
                    if job and job.get("status") == "running":
                        job.update(cancel=True, stage="Stopping...")
                return self._json({"ok": bool(job)}, 200 if job else 404)
            if path == "/api/render":
                normalize(data["timeline"])  # fail fast with a readable message
                job_id = uuid.uuid4().hex[:10]
                with LOCK:
                    JOBS[job_id] = {"status": "running", "stage": "Starting", "progress": 0.0}
                threading.Thread(target=_run_job, args=(job_id, data["timeline"], data.get("quality", "preview")),
                                 daemon=True).start()
                return self._json({"job": job_id})
            if path == "/api/projects":
                name = _safe_name(data.get("name", ""))
                if not name:
                    return self._json({"error": "Give the project a name."}, 400)
                (PROJECTS_DIR / f"{name}.json").write_text(json.dumps(data.get("data", {}), ensure_ascii=False,
                                                                      indent=1), encoding="utf-8")
                return self._json({"saved": name})
            return self._json({"error": "Unknown action"}, 404)
        except (RenderError, TTSError, script_mod.ScriptError, audio_mod.AudioError, SoundError) as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:
            traceback.print_exc()
            self._json({"error": f"Something went wrong: {e}"}, 500)


def serve(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)
