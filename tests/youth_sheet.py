"""Picture sheet of the three 20-year-old young man designs.   python tests/youth_sheet.py -> tests/out/youth.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from studio.flat import FW, render_sprite, char_spec, pose_for  # noqa: E402
from studio.render import Composer, build_schedule, normalize  # noqa: E402
from studio.tts import ENV_HZ, Clip  # noqa: E402

DESIGNS = [("flat_youth_a", "A: open check shirt, quiff"), ("flat_youth_b", "B: hoodie, spiky hair"),
           ("flat_youth_c", "C: graphic tee, side fringe")]


def fake(ln, ch):
    secs = ln.get("hold") or 2
    return Clip(Path(""), secs, [0.5] * int(secs * ENV_HZ), synthetic=True)


def frames(look, w=300, h=533):
    chars = [{"id": "y", "name": "Y", "look": look}, {"id": "o", "name": "O", "look": "flat_uncle"}]
    tl = normalize({"characters": chars, "scenes": [{"background": "flat_chai_tapri", "cast": ["y", "o"], "lines": [
        {"speaker": "y", "text": "", "action": "talk", "emotion": "happy", "hold": 1.5, "shot": "close"},
        {"speaker": "y", "text": "", "action": "wave", "emotion": "excited", "hold": 1.5, "shot": "single"},
        {"speaker": "y", "text": "", "action": "use_phone", "emotion": "laughing", "hold": 1.5, "shot": "single"},
        {"speaker": "o", "text": "", "action": "talk", "emotion": "neutral", "hold": 1.5, "shot": "ots"}]}]})
    sched, _ = build_schedule(tl, fake)
    comp = Composer(tl, sched, w, h, 2)
    return [comp.frame(l.start + 0.6) for l in sched[0].lines]


def lineup(w=900, h=533):
    """All three next to the existing young man and the kid, to compare heights."""
    chars = [{"id": k, "name": k, "look": k} for k, _ in DESIGNS] + [{"id": "m", "name": "m", "look": "flat_man"},
                                                                     {"id": "k", "name": "k", "look": "flat_kid"}]
    tl = normalize({"characters": chars, "scenes": [{"background": "flat_chai_tapri", "cast": [c["id"] for c in chars],
                                                     "lines": [{"speaker": "m", "text": "", "hold": 1, "shot": "wide"}]}]})
    sched, _ = build_schedule(tl, fake)
    comp = Composer(tl, sched, 540, 960, 2)
    return comp.frame(0.8).resize((300, 533))


def main():
    rows = [(label, frames(k)) for k, label in DESIGNS]
    W, H = 300, 533
    out = Image.new("RGB", (W * 5, (H + 30) * 3), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for r, (label, ims) in enumerate(rows):
        y = r * (H + 30)
        d.text((8, y + 8), label, fill=(0, 0, 0))
        for i, im in enumerate(ims):
            out.paste(im, (i * W, y + 30))
    out.paste(lineup(), (4 * W, 30))
    d.text((4 * W + 8, 8), "With the old young man and the kid", fill=(0, 0, 0))
    p = Path(__file__).parent / "out" / "youth.png"
    out.save(p)
    print(p)


if __name__ == "__main__":
    main()
