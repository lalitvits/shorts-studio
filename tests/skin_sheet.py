"""All flat cartoon people side by side (close-ups of the faces too), to compare skin tones.
python tests/skin_sheet.py [name]  ->  tests/out/skin_<name>.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from studio.render import Composer, build_schedule, normalize  # noqa: E402
from studio.tts import ENV_HZ, Clip  # noqa: E402

PEOPLE = ["flat_uncle", "flat_aunty", "flat_boy", "flat_man", "flat_girl", "flat_police", "flat_kid", "flat_youth_a",
          "flat_youth_b", "flat_youth_c", "maa"]


def fake(ln, ch):
    secs = ln.get("hold") or 1.5
    return Clip(Path(""), secs, [0.0] * int(secs * ENV_HZ), synthetic=True)


def main(name="now"):
    chars = [{"id": f"p{i}", "name": k, "look": k} for i, k in enumerate(PEOPLE)]
    lines = [{"speaker": c["id"], "text": "", "action": "talk", "emotion": "happy", "hold": 1.5, "shot": "close"}
             for c in chars]
    tl = normalize({"characters": chars, "scenes": [{"background": "flat_park", "cast": [c["id"] for c in chars],
                                                     "lines": lines}]})
    sched, _ = build_schedule(tl, fake)
    comp = Composer(tl, sched, 216, 384, 2)
    ims = [comp.frame(l.start + 0.5).crop((0, 40, 216, 300)) for l in sched[0].lines]
    out = Image.new("RGB", (216 * 6, 276 * 2), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for i, (im, k) in enumerate(zip(ims, PEOPLE)):
        x, y = (i % 6) * 216, (i // 6) * 276
        out.paste(im, (x, y + 16))
        d.text((x + 4, y + 2), k, fill=(0, 0, 0))
    p = Path(__file__).parent / "out" / f"skin_{name}.png"
    out.save(p)
    print(p)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["now"]))
