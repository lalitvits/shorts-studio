"""Picture sheet of the food / fruit / vegetable props and the new places.  -> tests/out/food_places.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from props_sheet import sheet  # noqa: E402

FOOD = ["samosa", "jalebi", "vada_pav", "cutting_chai", "kulhad", "plate_samosa", "banana", "apple", "mango", "orange",
        "grapes", "watermelon", "tomato", "onion", "potato", "carrot", "brinjal", "chilli", "cabbage", "veg_basket",
        "sabzi_bag"]
PLACES = ["flat_chai_tapri", "flat_sabzi_mandi", "flat_airport", "flat_bus_stop"]


def main():
    me = [{"id": "m", "name": "M", "look": "flat_man"}]
    lines = [{"speaker": "m", "text": "", "action": "talk", "hold": 1.6, "prop": p, "shot": "close"} for p in FOOD[:6]]
    lines += [{"speaker": "m", "text": "", "action": "talk", "hold": 1.6, "prop": p, "shot": "single"} for p in FOOD[6:]]
    lines += [{"speaker": "m", "text": "", "action": "eat", "hold": 1.6, "prop": "samosa", "shot": "close"},
              {"speaker": "m", "text": "", "action": "drink_tea", "hold": 1.6, "prop": "cutting_chai", "shot": "close"}]
    ims = sheet({"characters": me, "scenes": [{"background": "flat_chai_tapri", "lines": lines}]})
    two = [{"id": "a", "name": "A", "look": "flat_man"}, {"id": "b", "name": "B", "look": "flat_aunty"}]
    for bg in PLACES:                                   # each place: wide shot, single shot, a later moment
        ims += sheet({"characters": two, "scenes": [{"background": bg, "cast": ["a", "b"], "lines": [
            {"speaker": "a", "text": "", "hold": 4.0, "action": "talk", "shot": "wide"},
            {"speaker": "b", "text": "", "hold": 4.0, "action": "talk", "shot": "single"}]}]}, at=0.6)
    w, h, cols = 216, 384, 8
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (cols * w, rows * (h + 16)), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + 16)
        out.paste(im, (x, y + 16))
        d.text((x + 4, y + 2), name, fill=(0, 0, 0))
    p = Path(__file__).parent / "out" / "food_places.png"
    out.save(p)
    print(p, len(ims))


if __name__ == "__main__":
    main()
