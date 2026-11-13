"""Cut Maa's faces and her saree fabrics out of her character sheet.

Usage:  python tools/extract_maa.py path/to/maa_sheet.png
Needs (only this tool): pip install numpy scipy opencv-python-headless pillow
Writes assets/characters/maa/: heads/<face>.png and heads/<face>_nomouth.png (the face without its mouth, used for
lip-sync) for each of her faces, map.json (which face each of the 20 emotions uses), mouths.json (where the mouth is on
each face) and the fabric pictures for her clothes.

The sheet has six expression faces (warm, thinking, surprised, worried, sad, crying) plus one large warm face. The other
emotions borrow the closest of these (see MAP). The faces on the sheet are small, so they look soft in a 1080p video.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

BOXES = {
    "warm_big": (0, 4, 392, 405),
    "warm": (1183, 52, 1297, 202), "thinking": (1301, 52, 1415, 202), "surprised": (1419, 52, 1533, 202),
    "worried": (1183, 258, 1297, 408), "sad": (1301, 258, 1415, 408), "crying": (1419, 258, 1533, 408),
}
# the 20 emotions of the app -> which face of the sheet to use
MAP = {"neutral": "warm_big", "happy": "warm_big", "proud": "warm_big", "relieved": "warm_big", "in_love": "warm_big",
       "laughing": "warm_big", "excited": "warm_big", "embarrassed": "warm_big",
       "thinking": "thinking", "confused": "thinking", "surprised": "surprised", "shocked": "surprised",
       "worried": "worried", "scared": "worried", "angry": "worried", "disgusted": "worried",
       "sad": "sad", "sleepy": "sad", "bored": "sad", "crying": "crying"}
FABRICS = {"saree_floral": (868, 828, 1086, 918), "saree_border": (870, 940, 998, 986), "blouse": (1004, 928, 1085, 1006)}
UP = 2
SKULL_K = 1.28       # her real face is drawn a little smaller than the cartoon heads, so she is in proportion
ANCHOR_Y = 0.50      # Maa's eye line sits higher in her picture (more room below for her chin and neck); catalog: anchor_y


def head_mask(crop: np.ndarray, bottom: float = 0.97) -> np.ndarray:
    h, w = crop.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.grabCut(crop, m, (int(0.03 * w), int(0.02 * h), int(0.94 * w), int(bottom * h)),
                np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_RECT)
    fg = (m == 1) | (m == 3)
    fg = ndi.binary_closing(fg, iterations=2)
    fg = ndi.binary_fill_holes(fg)                                  # the bindi, earrings
    lab, n = ndi.label(fg)
    if n > 1:
        fg = lab == (1 + int(np.argmax(ndi.sum(fg, lab, range(1, n + 1)))))
    return cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.0) > 0.5


# Measured by eye on the sheet (pixels inside each head crop): the point between the eyes (ax, ay), the face width at
# eye level (skull), and the centre of the mouth (mx, my).
CAL = {
    "warm_big": dict(ax=270, ay=200, skull=240, mx=255, my=292, cut=388),
    "warm": dict(ax=65, ay=60, skull=82, mx=65, my=91, cut=140),
    "thinking": dict(ax=66, ay=58, skull=72, mx=75, my=91, cut=143),
    "surprised": dict(ax=68, ay=56, skull=74, mx=71, my=92, cut=138),
    "worried": dict(ax=71, ay=62, skull=80, mx=63, my=96, cut=138),
    "sad": dict(ax=72, ay=83, skull=88, mx=78, my=115, cut=146),
    "crying": dict(ax=72, ay=67, skull=82, mx=60, my=96, cut=136),
}


def skin_colour(crop: np.ndarray, fg: np.ndarray):
    r, g, b = [crop[..., i].astype(int) for i in range(3)]
    skin = (r > 130) & (g > 70) & (b > 45) & (r > g + 12) & (g > b) & fg
    return skin


def build(sheet: np.ndarray, name: str, box):
    x0, y0, x1, y1 = box
    crop = np.ascontiguousarray(sheet[y0:y1, x0:x1])
    c = CAL[name]
    fg = head_mask(crop, 0.97)
    fg[int(c["cut"]):] = False                         # below the neck line is the shoulder: the body is drawn instead
    xs = np.where(fg.any(0))[0]
    hx = (xs.min() + xs.max()) / 2.0                  # the head (hair and face) is centred over the neck
    skull = float(c["skull"]) * SKULL_K
    cw = int(round(skull / 0.55)); ch = int(round(cw * 0.935))
    ox, oy = int(round(0.5 * cw - hx)), int(round(ANCHOR_Y * ch - c["ay"]))
    rgba = np.dstack([crop, (fg * 255).astype(np.uint8)])
    canvas = np.zeros((ch, cw, 4), np.uint8)
    sx0, sy0 = max(0, -ox), max(0, -oy)
    dx0, dy0 = max(0, ox), max(0, oy)
    wd, hd = min(rgba.shape[1] - sx0, cw - dx0), min(rgba.shape[0] - sy0, ch - dy0)
    canvas[dy0:dy0 + hd, dx0:dx0 + wd] = rgba[sy0:sy0 + hd, sx0:sx0 + wd]
    fade = int(0.12 * skull)                           # fade the bottom (neck) so it melts into the body drawn underneath
    canvas[:, :, 3] = (canvas[:, :, 3] * np.clip((ch - 1 - np.arange(ch)) / fade, 0, 1)[:, None]).astype(np.uint8)
    img = Image.fromarray(canvas, "RGBA").resize((cw * UP, ch * UP), Image.LANCZOS)
    rgb = img.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2.2, percent=90, threshold=2))
    img = Image.merge("RGBA", (*rgb.split(), img.getchannel("A")))
    meta = dict(cx=(0.5 * cw + c["mx"] - hx) * UP, cy=(ANCHOR_Y * ch + c["my"] - c["ay"]) * UP, sk=skull * UP, skull=c["skull"] * UP)
    skin_rgb = [int(v) for v in np.median(crop[skin_colour(crop, fg)], 0)]
    return img, meta, skin_rgb


def remove_mouth(img: Image.Image, meta: dict) -> Image.Image:
    """The face without its mouth: the skin above and below the mouth is blended across it (no dark smears)."""
    a = np.array(img).astype(np.float32)
    H, W = a.shape[:2]
    cx, cy, sk = meta["cx"], meta["cy"], meta["sk"]
    yy, xx = np.mgrid[0:H, 0:W]
    m = (((xx - cx) / (0.27 * sk)) ** 2 + ((yy - cy) / (0.085 * sk)) ** 2) <= 1
    fill = a.copy()
    for x in np.where(m.any(0))[0]:
        ys = np.where(m[:, x])[0]
        y0, y1 = ys.min(), ys.max()
        x0, x1 = max(0, x - 3), min(W, x + 4)
        top = a[max(0, y0 - 7): y0 - 1, x0:x1, :3].reshape(-1, 3).mean(0)
        bot = a[y1 + 2: y1 + 8, x0:x1, :3].reshape(-1, 3).mean(0)
        t = (np.arange(y0, y1 + 1) - y0) / max(1, y1 - y0)
        fill[y0:y1 + 1, x, :3] = top[None, :] * (1 - t)[:, None] + bot[None, :] * t[:, None]
    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), sk * 0.02)[..., None]
    out = a * (1 - alpha) + fill * alpha
    out[..., 3] = a[..., 3]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def main(path: str):
    sheet = np.array(Image.open(path).convert("RGB"))
    root = Path(__file__).resolve().parent.parent / "assets" / "characters" / "maa"
    (root / "heads").mkdir(parents=True, exist_ok=True)
    base, metas, skins = {}, {}, []
    for name, box in BOXES.items():
        if name not in MAP.values():
            continue
        base[name] = build(sheet, name, box)
        skins.append(base[name][2])
    meta_all = {}
    for src in sorted(set(MAP.values())):                    # each face is stored once; map.json says who uses it
        img, meta, _ = base[src]
        img.save(root / "heads" / f"{src}.png", optimize=True)
        remove_mouth(img, meta).save(root / "heads" / f"{src}_nomouth.png", optimize=True)
        meta_all[src] = {k: round(v, 1) for k, v in meta.items()}
    (root / "map.json").write_text(json.dumps(MAP, indent=1), encoding="utf-8")
    (root / "mouths.json").write_text(json.dumps(meta_all, indent=1), encoding="utf-8")
    for name, (x0, y0, x1, y1) in FABRICS.items():
        Image.fromarray(sheet[y0:y1, x0:x1]).save(root / f"{name}.png")
    print("skin colour (median of the faces):", [int(v) for v in np.median(skins, 0)])
    print("written to", root)


if __name__ == "__main__":
    main(sys.argv[1])
