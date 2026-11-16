"""Picture sheet of the kitchen-fire tools: frying, the fire, the jug, the grab, the thali, the explainer, the ending.

    python tests/kitchen_sheet.py   ->  tests/out/kitchen.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from studio.render import Composer, build_schedule, normalize  # noqa: E402
from studio.tts import ENV_HZ, Clip, estimate_seconds  # noqa: E402

TL = {
    "title": "Kitchen fire", "language": "hi",
    "characters": [
        {"id": "neha", "name": "Neha", "look": "flat_aunty"},
        {"id": "beta", "name": "Beta", "look": "flat_kid"},
        {"id": "lalit", "name": "Lalit", "look": "flat_man"},
        {"id": "vo", "name": "Narrator", "look": "narrator"},
    ],
    "scenes": [
        {"background": "flat_kitchen", "cast": ["neha"], "music": "panic", "lines": [
            {"speaker": "neha", "text": "", "action": "cook", "emotion": "happy", "kadhai": "fry", "hold": 2},
            {"speaker": "vo", "text": "रविवार की सुबह थी, अचानक कड़ाही के तेल ने आग पकड़ ली!", "kadhai": "fire",
             "shot": "stove"},
            {"speaker": "vo", "text": "नेहा घबराकर पीछे हट गईं।", "actor": "neha", "actor_action": "step_back",
             "actor_emotion": "scared"}]},
        {"background": "flat_kitchen", "cast": ["neha", "beta", "lalit"], "lines": [
            {"speaker": "beta", "text": "", "action": "run_in", "emotion": "scared", "hold": 1.2},
            {"speaker": "beta", "text": "", "action": "hold_jug", "emotion": "scared", "hold": 1.5},
            {"speaker": "lalit", "text": "रुको! पानी बिल्कुल मत डालना!", "action": "grab_hand", "emotion": "shocked",
             "actor": "beta", "actor_action": "lower_jug", "actor_emotion": "surprised"}]},
        {"background": "flat_kitchen", "cast": ["neha", "beta", "lalit"], "lines": [
            {"speaker": "vo", "text": "ललित ने तुरंत गैस बंद की", "actor": "lalit", "actor_action": "turn_off_gas",
             "actor_emotion": "worried"},
            {"speaker": "vo", "text": "और थाली से कड़ाही ढक दी।", "actor": "lalit", "actor_action": "cover_kadhai",
             "actor_emotion": "worried"}]},
        {"background": "flat_kitchen", "cast": ["neha", "beta", "lalit"], "music": "calm", "lines": [
            {"speaker": "lalit", "text": "बेटा, तेल की आग पर पानी डालते ही वो भाप बनकर फटता है।",
             "action": "hand_on_shoulder", "emotion": "neutral", "broll": "oil_fire"},
            {"speaker": "vo", "text": "इस वीडियो को शेयर करें!", "actor": "lalit", "actor_action": "look_camera",
             "actor_emotion": "relieved", "overlay": "आग पर पानी न डालें, उसे ढकें! | NEVER USE WATER ON OIL FIRE"}]},
    ],
}


def fake(ln, ch):
    secs = max(estimate_seconds(ln["text"]), ln.get("hold") or 0) or 1.0
    return Clip(Path(""), secs, [0.6] * int(secs * ENV_HZ), synthetic=True)


def main():
    tl = normalize(TL)
    sched, total = build_schedule(tl, fake)
    comp = Composer(tl, sched, 270, 480, 2)
    picks = []
    for sc in sched:
        for ln in sc.lines:
            for f in (0.15, 0.55, 0.95):
                picks.append(ln.start + (ln.end - ln.start) * f)
    w, h, cols = 270, 480, 8
    rows = (len(picks) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 18)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(picks):
        im = comp.frame(t)
        x, y = (i % cols) * w, (i // cols) * (h + 18)
        sheet.paste(im, (x, y + 18))
        d.text((x + 4, y + 3), f"{t:.1f}s", fill=(0, 0, 0))
    out = Path(__file__).parent / "out" / "kitchen.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(out, f"{total:.1f}s", len(picks), "frames")


if __name__ == "__main__":
    main()
