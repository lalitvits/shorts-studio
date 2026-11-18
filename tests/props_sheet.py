"""Picture sheet of props, heights / builds and the cycle.   python tests/props_sheet.py -> tests/out/props.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from studio.catalog import PROPS  # noqa: E402
from studio.render import Composer, build_schedule, normalize  # noqa: E402
from studio.tts import ENV_HZ, Clip  # noqa: E402


def fake(ln, ch):
    secs = ln.get("hold") or 1.6
    return Clip(Path(""), secs, [0.0] * int(secs * ENV_HZ), synthetic=True)


def sheet(tl, picks_per_line=1, at=0.7):
    tl = normalize(tl)
    sched, _ = build_schedule(tl, fake)
    comp = Composer(tl, sched, 216, 384, 2)
    ims = []
    for sc in sched:
        for ln in sc.lines:
            ims.append((ln.prop or ln.action, comp.frame(ln.start + (ln.end - ln.start) * at)))
    return ims


def main():
    chars = [{"id": "m", "name": "M", "look": "flat_man"}]
    lines = [{"speaker": "m", "text": "", "action": "talk", "hold": 1.6, "prop": p, "shot": "single"} for p in PROPS]
    lines += [{"speaker": "m", "text": "", "action": "drink_tea", "hold": 1.6, "prop": "glass", "shot": "single"},
              {"speaker": "m", "text": "", "action": "walk", "hold": 1.6, "prop": "suitcase", "shot": "single"},
              {"speaker": "m", "text": "", "action": "ride_cycle", "hold": 1.6, "prop": "none", "shot": "single"}]
    ims = sheet({"characters": chars, "scenes": [{"background": "flat_city_street", "lines": lines}]})
    bodies = [{"id": f"b{i}", "name": "B", "look": lk, "height": h, "build": b, "outfit": o}
              for i, (lk, h, b, o) in enumerate((("flat_man", "short", "fat", "red"), ("flat_man", "tall", "thin", ""),
                                                 ("flat_aunty", "", "very_fat", "green"), ("flat_police", "", "thin", ""),
                                                 ("flat_kid", "", "fat", "purple"), ("flat_uncle", "very_tall", "fat", "")))]
    ims += sheet({"characters": bodies, "scenes": [{"background": "flat_park", "cast": [b["id"] for b in bodies],
                                                    "lines": [{"speaker": "b0", "text": "", "hold": 1.0, "action": "talk",
                                                               "shot": "wide"}]}]})
    ims += sheet({"characters": chars, "scenes": [{"background": "flat_city_street", "lines": [
        {"speaker": "m", "text": "", "action": "ride_in", "hold": 2.0, "shot": "wide"}]}]}, at=0.4)
    w, h, cols = 216, 384, 8
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (cols * w, rows * (h + 16)), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + 16)
        out.paste(im, (x, y + 16))
        d.text((x + 4, y + 2), name, fill=(0, 0, 0))
    p = Path(__file__).parent / "out" / "props.png"
    p.parent.mkdir(exist_ok=True)
    out.save(p)
    print(p, len(ims))


if __name__ == "__main__":
    main()
