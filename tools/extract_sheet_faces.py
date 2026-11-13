"""Cut the 20 emotion faces of Rahul, Aman and Priya out of their character-sheet pictures and clean them up.

Usage:  python tools/extract_sheet_faces.py rahul.png aman.png priya.png      (any order, file name = character)
Needs (only for this tool, not for the app):  pip install numpy scipy scikit-learn opencv-python-headless pillow
Writes assets/characters/<name>/heads/<emotion>.png: transparent background, head only (hoodie and effect marks
removed, the app draws its own sharp effect marks), enlarged 3x with flat colour regions and smooth edges.

The faces on the sheets are about 110 px wide. For the very best quality replace the files with bigger pictures
(see README, "Faces").
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from sklearn.cluster import KMeans

SCALE, COLOURS = 3, 28
AMAN_PRIYA_ORDER = ["neutral", "happy", "sad", "worried", "angry", "surprised", "laughing", "crying", "scared", "excited",
                    "sleepy", "embarrassed", "confused", "bored", "in_love", "proud", "disgusted", "thinking", "shocked", "relieved"]
RAHUL_ORDER = ["neutral", "happy", "sad", "angry", "worried", "surprised", "laughing", "crying", "scared", "excited",
               "sleepy", "embarrassed", "confused", "bored", "in_love", "proud", "disgusted", "thinking", "shocked", "relieved"]

CHARS = {
    "rahul": dict(xs=[770, 940, 1107, 1273, 1440], ys=[120, 300, 480, 660], per_row=5, order=RAHUL_ORDER,
                  box=(74, 74, 74, 64), inner=(58, 64), outer=(70, 78), long_hair=False,
                  hoodie=lambda r, g, b: (b > 130) & (r < 110) & (b - r > 70)),
    "aman": dict(xs=[383 + 120.2 * i for i in range(10)], ys=[449, 626], per_row=10, order=AMAN_PRIYA_ORDER,
                 box=(64, 70, 64, 60), inner=(52, 58), outer=(62, 70), long_hair=False,
                 hoodie=lambda r, g, b: (r > 195) & (g < 150) & (b < 75)),
    "priya": dict(xs=[383 + 120.2 * i for i in range(10)], ys=[449, 626], per_row=10, order=AMAN_PRIYA_ORDER,
                  box=(64, 70, 64, 60), inner=(52, 58), outer=(62, 70), long_hair=True,
                  hoodie=lambda r, g, b: (g > 110) & (r < 110) & (g - r > 50) & (b < 150)),
}


def biggest_blob(mask: np.ndarray) -> np.ndarray:
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


SKIN = lambda r, g, b: (r > 205) & (g > 150) & (b > 90) & (r - b > 45) & (r - b < 150)


def collar_line(crop: Image.Image, cfg: dict) -> int:
    """Row where the hoodie starts, measured on the neutral face (every face of the character is cut there)."""
    rgb = np.array(crop).astype(int)
    h, w = rgb.shape[:2]
    hood = cfg["hoodie"](rgb[..., 0], rgb[..., 1], rgb[..., 2])
    hood[: int(0.55 * h)] = False
    big = np.where(hood.sum(1) >= 0.10 * w)[0]
    return int(big.min()) if len(big) else h - 14


def head_mask(crop: Image.Image, cfg: dict, y_cut: int) -> np.ndarray:
    rgb = np.array(crop).astype(int)
    h, w = rgb.shape[:2]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sat, lum = rgb.max(2) - rgb.min(2), rgb.mean(2)
    fg = ndi.binary_fill_holes((sat >= 38) | (lum < 205))      # pale low-colour pixels are the sheet background
    blob = biggest_blob(ndi.binary_opening(fg, iterations=2))   # drops thin tile borders and specks
    fg = ndi.binary_dilation(blob, iterations=2) & fg
    cx, cy = w / 2, cfg["box"][1] - 2
    yy, xx = np.mgrid[0:h, 0:w]
    ell = lambda rx, ry: ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    dark = (r < 150) & (g < 120) & (b < 110)
    inner = ell(*cfg["inner"])
    hood = ndi.binary_dilation(cfg["hoodie"](r, g, b), iterations=1) & ~inner   # stray sleeves around the head
    fg &= ell(*cfg["outer"]) & (inner | SKIN(r, g, b) | dark) & ~hood          # effect marks are redrawn by the app
    below = yy > y_cut
    if cfg["long_hair"]:                                          # long hair keeps falling past the shoulders
        fg &= ~(below & ~(dark & (abs(xx - cx) > 0.30 * w)))
    else:
        fg &= ~below
    fg = biggest_blob(ndi.binary_opening(fg, iterations=1))
    return ndi.binary_erosion(fg, iterations=1)


def clean_upscale(rgb: np.ndarray, mask: np.ndarray) -> Image.Image:
    h, w = mask.shape
    idx = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    big = cv2.resize(rgb[idx[0], idx[1]], (w * SCALE, h * SCALE), interpolation=cv2.INTER_CUBIC)
    for _ in range(2):
        big = cv2.bilateralFilter(big, 9, 26, 9)
    m = cv2.GaussianBlur(cv2.resize(mask.astype(np.float32), (w * SCALE, h * SCALE), interpolation=cv2.INTER_CUBIC),
                         (0, 0), SCALE * 0.5)
    alpha = m > 0.5
    km = KMeans(n_clusters=COLOURS, n_init=1, random_state=0).fit(big[alpha][::6])
    labels = km.predict(big.reshape(-1, 3)).reshape(big.shape[:2])
    probs = np.stack([cv2.GaussianBlur((labels == i).astype(np.float32), (0, 0), SCALE * 0.55) for i in range(COLOURS)])
    q = km.cluster_centers_.astype(np.uint8)[probs.argmax(0)]
    a = cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), 1.0)
    return Image.fromarray(np.dstack([q, (a * 255).astype(np.uint8)]), "RGBA")


def skin_width(crop: Image.Image, cfg: dict, mask: np.ndarray) -> int:
    """Ear-to-ear width: the widest row of skin around the middle of the head (hair is ignored)."""
    rgb = np.array(crop).astype(int)
    best = 0
    cy = cfg["box"][1]
    for y in range(cy - 14, cy + 30):
        ok = SKIN(rgb[y, :, 0], rgb[y, :, 1], rgb[y, :, 2]) & mask[y]
        xs = np.where(ok)[0]
        if len(xs) > 10:
            best = max(best, int(xs.max() - xs.min()))
    return best


def main(paths):
    root = Path(__file__).resolve().parent.parent / "assets" / "characters"
    for p in paths:
        name = Path(p).stem.lower()
        for key in CHARS:
            if key in name:
                name = key
        cfg = CHARS[name]
        sheet = Image.open(p).convert("RGB")
        out = root / name / "heads"
        out.mkdir(parents=True, exist_ok=True)
        L, T, R, B = cfg["box"]
        crops = []
        for i, emo in enumerate(cfg["order"]):
            cx, cy = cfg["xs"][i % cfg["per_row"]], cfg["ys"][i // cfg["per_row"]]
            crops.append((emo, sheet.crop((int(cx - L), int(cy - T), int(cx + R), int(cy + B)))))
        # canvas convention (see README): skull ~55% of the picture width, face centre 57% down
        y_cut = collar_line(crops[0][1], cfg) - 2
        sw = skin_width(crops[0][1], cfg, head_mask(crops[0][1], cfg, y_cut))
        cw = int(round(sw / 0.55))
        ch = int(round(cw * 0.935))
        for emo, crop in crops:
            mask = head_mask(crop, cfg, y_cut)
            rgb = np.zeros((ch, cw, 3), np.uint8)
            msk = np.zeros((ch, cw), bool)
            ox, oy = int(cw / 2 - crop.width / 2), int(0.57 * ch - cfg["box"][1])
            y0, x0 = max(oy, 0), max(ox, 0)
            sub_rgb = np.array(crop)[y0 - oy: y0 - oy + (ch - y0), x0 - ox: x0 - ox + (cw - x0)]
            sub_m = mask[y0 - oy: y0 - oy + (ch - y0), x0 - ox: x0 - ox + (cw - x0)]
            rgb[y0: y0 + sub_rgb.shape[0], x0: x0 + sub_rgb.shape[1]] = sub_rgb
            msk[y0: y0 + sub_m.shape[0], x0: x0 + sub_m.shape[1]] = sub_m
            clean_upscale(rgb, msk).save(out / f"{emo}.png", optimize=True)
        print("done", name, "neck cut at row", y_cut, "skin width", sw, "canvas", cw, "x", ch)


if __name__ == "__main__":
    main(sys.argv[1:])
