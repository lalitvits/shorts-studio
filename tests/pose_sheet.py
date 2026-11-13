"""Draw contact sheets of every emotion and activity to check them by eye.
Run from the project folder:  python tests/pose_sheet.py   (writes tests/out/*.png)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from studio.catalog import EMOTIONS, LOOKS  # noqa: E402
from studio.config import GROUND_Y  # noqa: E402
from studio.rig import BOX_H, BOX_W, ORG_X, ORG_Y, draw_character, draw_sofa, pose_for, solve  # noqa: E402

K = 0.5
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def cell(action, emotion, t, seated, look="rahul", scale=1.3, speaking=False, mouth=0.0, crop_head=False):
    w, h = int(BOX_W * K), int(BOX_H * K)
    im = Image.new("RGB", (w, h), (230, 241, 251))
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(ORG_Y * K), w, h], fill=(211, 209, 199))
    pose = pose_for(action, emotion, t, speaking, 0.0, seated=seated)
    if seated:
        cx = ORG_X
        layer, pos = draw_sofa(im, K, ORG_Y, cx - 250 * scale, cx + 250 * scale, scale)
        # draw_sofa uses world x, so shift into this cell's box
        im.paste(layer, (int((cx - 250 * scale - 40) * K), int((ORG_Y - 420 * scale) * K)), layer)
    ch = draw_character(LOOKS[look], pose, emotion, mouth, 0.0, K, scale, 2, t)
    im.paste(ch, (0, 0), ch)
    if crop_head:
        J = solve(pose)
        hx = (ORG_X + J["head"][0] * scale) * K
        hy = (ORG_Y + J["head"][1] * scale) * K
        r = 165 * K * scale / 1.3
        im = im.crop((int(hx - r * 1.6), int(hy - r * 1.55), int(hx + r * 1.6), int(hy + r * 1.75))).resize((300, 340))
    ImageDraw.Draw(im).text((6, 4), f"{emotion if crop_head else action}", fill=(18, 23, 53))
    return im


def sheet(cells, cols, name):
    cw, ch = cells[0].size
    rows = (len(cells) + cols - 1) // cols
    s = Image.new("RGB", (cw * cols, ch * rows), (255, 255, 255))
    for i, c in enumerate(cells):
        s.paste(c, ((i % cols) * cw, (i // cols) * ch))
    s.save(OUT / name)
    print("wrote", OUT / name, s.size)


if __name__ == "__main__":
    looks = ["rahul", "aman", "priya"]
    sheet([cell("talk", e, 1.1 + i * 0.13, False, looks[i % 3], crop_head=True) for i, e in enumerate(EMOTIONS)],
          5, "emotions.png")
    acts = [("use_phone", 1.0, False), ("drink_tea", 2.5, False), ("read_book", 1.0, False), ("eat", 1.4, False),
            ("clap", 1.0, False), ("dance", 0.5, False), ("facepalm", 1.0, False), ("sit", 1.0, True),
            ("sit_phone", 1.0, True), ("sit_tea", 2.5, True), ("sit_read", 1.0, True), ("sit_sleep", 1.0, True)]
    sheet([cell(a, "neutral", t, s, looks[i % 3], scale=1.15 if s else 1.3) for i, (a, t, s) in enumerate(acts)],
          4, "activities.png")
    lineup = [("thumbs_up", "happy", "rahul"), ("cheer", "laughing", "aman"), ("explain", "happy", "priya")]
    sheet([cell(a, e, 1.0, False, lk, scale=1.2) for a, e, lk in lineup], 3, "lineup.png")
    gest = ["thumbs_up", "point", "explain", "think", "wave", "cheer", "shrug", "ok_sign", "arms_crossed", "stop"]
    sheet([cell(a, "happy" if a in ("cheer", "thumbs_up", "wave", "ok_sign") else "neutral", 1.0, False, looks[i % 3], scale=1.2)
           for i, a in enumerate(gest)], 5, "gestures.png")
