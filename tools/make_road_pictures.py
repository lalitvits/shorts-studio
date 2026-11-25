"""Draw the road pictures used as cut-aways in the speed breaker video, into my_backgrounds/:

  speed_breaker_sign.png   the highway with a big "speed breaker ahead" warning sign in front
  speed_breaker_road.png   a close look down the road at the speed breaker (the opening shot)

Run from the project folder:  python tools/make_road_pictures.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from studio.flat import panorama  # noqa: E402
from studio.places_more import _font  # noqa: E402

OUT = (36, 31, 32)


def sign_picture() -> Image.Image:
    pano = panorama("flat_highway", 1.0)[0].convert("RGB")
    im = pano.crop((760, 0, 1840, 1920))
    d = ImageDraw.Draw(im)
    cx = 600
    d.rounded_rectangle((cx - 22, 760, cx + 22, 1720), radius=10, fill=(236, 236, 230), outline=OUT, width=7)  # pole
    for y in range(820, 1700, 120):
        d.rectangle((cx - 19, y, cx + 19, y + 60), fill=(36, 36, 40))
    d.ellipse((cx - 90, 1690, cx + 90, 1740), fill=(0, 0, 0, 60))
    tri = [(cx, 180), (cx + 330, 740), (cx - 330, 740)]                                   # red warning triangle
    d.polygon(tri, fill=(214, 40, 36))
    d.line(tri + [tri[0]], fill=OUT, width=12, joint="curve")
    inner = [(cx, 300), (cx + 228, 690), (cx - 228, 690)]
    d.polygon(inner, fill=(255, 255, 255))
    d.pieslice((cx - 120, 560, cx + 120, 760), 180, 360, fill=(30, 30, 34))               # the bump symbol
    d.rectangle((cx - 190, 655, cx + 190, 668), fill=(30, 30, 34))
    d.rounded_rectangle((cx - 230, 770, cx + 230, 920), radius=18, fill=(250, 200, 40), outline=OUT, width=10)
    f = _font(110)
    w = d.textlength("SLOW", font=f)
    d.text((cx - w / 2, 782), "SLOW", font=f, fill=(30, 30, 34))
    d.rounded_rectangle((cx - 250, 940, cx + 250, 1030), radius=14, fill=(255, 255, 255), outline=OUT, width=8)
    f2 = _font(40)
    t = "SPEED BREAKER AHEAD"
    w = d.textlength(t, font=f2)
    d.text((cx - w / 2, 963), t, font=f2, fill=(200, 30, 30))
    return im


def road_picture() -> Image.Image:
    pano, ps = panorama("flat_highway", 2.0)[:2]                    # drawn large, then cropped round the bump
    cx, top, w = 1300 * ps, 880 * ps, 560 * ps                       # (picture units -> pixels)
    im = pano.convert("RGB").crop((round(cx - w / 2), round(top), round(cx + w / 2),
                                   round(top + w * 16 / 9))).resize((1080, 1920), Image.LANCZOS)
    d = ImageDraw.Draw(im)                                           # the question, on a card at the top
    d.rounded_rectangle((110, 170, 970, 420), radius=34, fill=(255, 255, 255), outline=OUT, width=10)
    for text, y, size, col in (("Ye chhote speed breaker", 200, 74, (30, 30, 34)),
                               ("kyun hote hain?", 300, 84, (206, 36, 36))):
        f = _font(size)
        d.text((540 - d.textlength(text, font=f) / 2, y), text, font=f, fill=col)
    return im


if __name__ == "__main__":
    folder = ROOT / "my_backgrounds"
    folder.mkdir(exist_ok=True)
    p = folder / "speed_breaker_sign.png"
    sign_picture().save(p)
    print("wrote", p)
    p = folder / "speed_breaker_road.png"
    road_picture().save(p)
    print("wrote", p)
