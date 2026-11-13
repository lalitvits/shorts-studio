"""The 3D characters (old man, young man, spiky-hair boy, young woman).

They are real Three.js models (studio/web3d/chars.js, built like their preview pages). A hidden browser (Microsoft
Edge or Google Chrome, driven by the `playwright` package) poses each one for a video frame and renders it to a
transparent picture, which the flat-style composer pastes into the scene.

One background thread owns the browser, so video renders and preview stills from any thread can share it.
If no browser can be started, sprite() returns None and the caller draws a flat stand-in instead.
"""
from __future__ import annotations

import atexit
import base64
import io
import queue
import threading
from concurrent.futures import Future
from pathlib import Path

from PIL import Image, ImageEnhance

STAGE = Path(__file__).resolve().parent / "web3d" / "stage.html"
UNIT = 560          # flat-world units per 3D unit (a 3D character is about 1.75 units tall)
VIBRANCE = 1.2      # colour saturation of the 3D characters (1.0 = exactly the model's colours)

# app emotion -> 3D mood
MOODS = {"happy": "happy", "relieved": "happy", "laughing": "laughing", "sad": "sad", "sleepy": "sleepy",
         "angry": "angry", "surprised": "surprised", "shocked": "surprised", "excited": "excited", "proud": "proud",
         "in_love": "in_love", "crying": "crying", "worried": "worried", "bored": "bored", "embarrassed": "embarrassed",
         "disgusted": "disgusted", "scared": "scared", "confused": "confused", "thinking": "thinking",
         "neutral": "neutral"}


class _Worker:
    def __init__(self):
        self.q: queue.Queue = queue.Queue()
        self.error: str | None = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, name="3d-renderer", daemon=True)
        self.thread.start()

    def _run(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.error = "3D characters need the playwright package: pip install playwright"
            self.ready.set()
            return
        try:
            pw = sync_playwright().start()
            browser = None
            for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
                try:
                    browser = pw.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"], **kw)
                    break
                except Exception:
                    continue
            if browser is None:
                raise RuntimeError("no Edge or Chrome browser was found")
            page = browser.new_page()
            page.goto(STAGE.as_uri())
            page.wait_for_function("window.R3 !== undefined", timeout=20000)
        except Exception as e:  # noqa: BLE001
            self.error = f"3D characters could not start a browser ({e}). They are drawn flat instead."
            self.ready.set()
            return
        self.ready.set()
        while True:
            job = self.q.get()
            if job is None:
                break
            args, fut = job
            try:
                fut.set_result(page.evaluate("o => R3.render(o)", args))
            except Exception as e:  # noqa: BLE001
                fut.set_exception(e)
        try:
            browser.close()
            pw.stop()
        except Exception:  # noqa: BLE001
            pass

    def call(self, args: dict):
        fut: Future = Future()
        self.q.put((args, fut))
        return fut.result(timeout=60)


_W: _Worker | None = None
_LOCK = threading.Lock()


def _worker() -> _Worker:
    global _W
    with _LOCK:
        if _W is None:
            _W = _Worker()
    _W.ready.wait(60)
    return _W


@atexit.register
def _shutdown():
    if _W is not None:
        _W.q.put(None)


def status() -> str | None:
    """None when 3D rendering works, else a message for the user."""
    return _worker().error


def sprite(model: str, action: str, emotion: str, t: float, mouth: float | None, blink: float, rot_y: float,
           ppu: float, below_px: float | None):
    """(RGBA picture, (feet x, feet y) in it) or None when 3D rendering is not available."""
    w = _worker()
    if w.error:
        return None
    r = w.call(dict(kind=model, action=action, mood=MOODS.get(emotion, "neutral"), t=t, mouth=mouth, blink=blink,
                    rotY=rot_y, ppu=ppu, below=below_px))
    im = Image.open(io.BytesIO(base64.b64decode(r["png"].split(",", 1)[1]))).convert("RGBA")
    if VIBRANCE != 1.0:                     # a little extra colour so they pop against the cartoon backgrounds
        a = im.getchannel("A")
        im = ImageEnhance.Color(im.convert("RGB")).enhance(VIBRANCE).convert("RGBA")
        im.putalpha(a)
    return im, (r["ax"], r["ay"])
