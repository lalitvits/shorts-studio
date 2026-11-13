"""Cut Maa's mouth pictures out of her lip-sync reference sheet.

Usage:  python tools/extract_maa_visemes.py path/to/maa_lip_sync_reference.png     (needs only: pip install pillow)
Writes assets/characters/maa/visemes/<shape>.png: the 12 key mouth shapes (rest, aa, ee, oo, eh, oh, ba, fa, th, ta, la,
ra) and 7 emotion mouths (happy, worried, sad, crying, surprised, thinking, affectionate). The app pastes them onto Maa's
faces while she talks.
"""
import sys
from pathlib import Path

from PIL import Image

# (name, x0, y0, x1, y1) of each tile on the reference sheet; a few pixels are trimmed off all sides to drop the gold frame
KEYS = [("rest", 525, 51), ("aa", 635, 51), ("ee", 745, 51), ("oo", 855, 51), ("eh", 962, 51), ("oh", 1070, 51),
        ("ba", 525, 185), ("fa", 635, 185), ("th", 745, 185), ("ta", 855, 185), ("la", 962, 185), ("ra", 1070, 185)]
KEY_W, KEY_H, TRIM_KEY = 102, 82, 6
EMOTIONS = [("happy", 155, 240), ("worried", 380, 460), ("sad", 579, 660), ("crying", 792, 875),
            ("surprised", 1005, 1089), ("thinking", 1216, 1285), ("affectionate", 1432, 1516)]
EMO_Y0, EMO_Y1, TRIM_EMO = 666, 716, 5


def main(path: str):
    im = Image.open(path).convert("RGB")
    out = Path(__file__).resolve().parent.parent / "assets" / "characters" / "maa" / "visemes"
    out.mkdir(parents=True, exist_ok=True)
    for name, x, y in KEYS:
        im.crop((x + TRIM_KEY, y + TRIM_KEY, x + KEY_W - TRIM_KEY, y + KEY_H - TRIM_KEY)).save(out / f"{name}.png")
    for name, x0, x1 in EMOTIONS:
        im.crop((x0 + TRIM_EMO, EMO_Y0 + TRIM_EMO, x1 - TRIM_EMO, EMO_Y1 - TRIM_EMO)).save(out / f"{name}.png")
    print("written to", out)


if __name__ == "__main__":
    main(sys.argv[1])
