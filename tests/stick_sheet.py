"""Picture sheets of the stickmen, the slapstick moves and the cartoon effects.
python tests/stick_sheet.py  ->  tests/out/stick_looks.png, stick_moves.png, stick_effects.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from studio.catalog import LOOKS  # noqa: E402
from studio.flat import char_spec, pose_for, render_sprite  # noqa: E402

OUT = Path(__file__).parent / "out"
STICKS = ["stick_classic", "stick_blue", "stick_red", "stick_girl", "stick_kid", "stick_boss"]
CW, CH = 300, 420


def cell(look, action="idle", emotion="happy", t=0.0, effect="", face=1, view="front", mouth=0.0):
    sp = char_spec({"look": look})
    pose = pose_for(action, emotion, t, False, look)
    if effect:
        pose["fx"] = set(pose.get("fx", ())) | {effect}
    spr, (ax, ay) = render_sprite(sp, view, face, 0.24, pose, emotion, mouth, 0.0, t, False)
    im = Image.new("RGB", (CW, CH), (255, 255, 255))
    d = ImageDraw.Draw(im)
    gy = CH - 40
    d.line([(10, gy), (CW - 10, gy)], fill=(225, 225, 225), width=2)
    mv = pose.get("move")
    x = CW / 2 + (mv[0] * 0.24 * sp.get("height", 1) if mv else 0)
    y = gy + (mv[1] * 0.24 * sp.get("height", 1) if mv else 0)
    im.paste(spr, (round(x - ax), round(y - ay)), spr)
    return im


def sheet(cells, cols, name):
    rows = (len(cells) + cols - 1) // cols
    out = Image.new("RGB", (cols * CW, rows * (CH + 22)), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for i, (label, im) in enumerate(cells):
        x, y = (i % cols) * CW, (i // cols) * (CH + 22)
        out.paste(im, (x, y + 22))
        d.text((x + 8, y + 5), label, fill=(0, 0, 0))
    p = OUT / name
    out.save(p)
    print(p)


def main():
    OUT.mkdir(exist_ok=True)
    looks = []
    for k in STICKS:
        looks.append((LOOKS[k]["label"].replace("Stickman: ", ""), cell(k, "wave", "happy", 0.3)))
    for k, (a, e) in zip(STICKS, [("hips", "angry"), ("shrug", "confused"), ("cheer", "excited"), ("think", "thinking"),
                                  ("cry", "crying"), ("arms_crossed", "proud")]):
        looks.append((f"{e}", cell(k, a, e, 0.4)))
    sheet(looks, 6, "stick_looks.png")

    moves = [("slip_fall", 0.12), ("slip_fall", 1.0), ("fall_face", 1.0), ("fly_away", 0.4), ("hit_head", 0.05),
             ("hit_head", 1.0), ("freeze", 0.4), ("double_take", 0.9), ("faint", 1.4), ("fight_cloud", 0.5),
             ("crash_wall", 0.6), ("crash_wall", 1.5), ("dizzy", 0.7), ("shiver", 0.5), ("cartoon_run", 0.3),
             ("tiptoe", 0.8), ("laugh_floor", 0.4), ("kick", 0.36), ("jaw_drop", 0.5), ("get_up", 0.35)]
    looks_cycle = STICKS * 4
    sheet([(f"{a} @{t}s", cell(looks_cycle[i], a, "neutral", t)) for i, (a, t) in enumerate(moves)], 5,
          "stick_moves.png")

    effects = ["dizzy", "impact", "speed", "dust", "sweat", "exclaim", "question", "steam", "hearts", "shiver",
               "rain_cloud", "eyes_pop", "idea", "sparkle"]
    cells = [(e, cell(looks_cycle[i], "idle", "neutral", 0.4, e)) for i, e in enumerate(effects)]
    cells += [("flat man: slip_fall", cell("flat_man", "slip_fall", "neutral", 1.0)),
              ("flat aunty: faint", cell("flat_aunty", "faint", "neutral", 1.4)),
              ("flat boy: kick", cell("flat_boy", "kick", "angry", 0.36)),
              ("flat uncle: jaw_drop", cell("flat_uncle", "jaw_drop", "neutral", 0.5))]
    sheet(cells, 6, "stick_effects.png")


if __name__ == "__main__":
    main()
