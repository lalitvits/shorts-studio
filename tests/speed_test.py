"""Render the same video with 1 process and with the parallel workers and compare. Run: python tests/speed_test.py"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.render import render_video, worker_count  # noqa: E402

TL = {"title": "speed", "tts": "silent", "captions": True, "effects": True,
      "characters": [{"id": "a", "name": "A", "look": "flat_uncle"}, {"id": "b", "name": "B", "look": "3d_woman"}],
      "scenes": [{"background": "flat_market", "cast": ["a", "b"], "lines": [
          {"speaker": "a", "text": "अरे भाई, ये आम कितने के हैं? बहुत महंगे लग रहे हैं।", "emotion": "surprised", "action": "talk"},
          {"speaker": "b", "text": "सौ रुपये किलो, सबसे मीठे आम हैं!", "emotion": "happy", "action": "explain"},
          {"speaker": "a", "text": "चलो दो किलो दे दो।", "emotion": "happy", "action": "talk"}]}]}

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "preview"
    res = {}
    for n in ("1", ""):
        os.environ["SHORTS_WORKERS"] = n
        t0 = time.time()
        r = render_video(TL, q)
        res[n or f"auto ({worker_count(10**6)})"] = (round(time.time() - t0, 1), r["file"], r["warnings"])
    for k, v in res.items():
        print(f"workers {k}: {v[0]} s  {v[1]}  warnings={v[2]}")
