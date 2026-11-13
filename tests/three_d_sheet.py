"""Contact sheet of the 3D characters in scenes. Run:  python tests/three_d_sheet.py [width]
Needs Microsoft Edge or Google Chrome and `pip install playwright`. Writes tests/out/three_d_scenes.png."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from studio.render import Composer, build_schedule, normalize  # noqa: E402
from tests.flat_sheet import fake  # noqa: E402

SAMPLE = {
    "title": "Dada ji aur pota", "captions": False,
    "characters": [
        {"id": "dada", "name": "Dada ji", "look": "3d_oldman", "voice": "hi-IN-MadhurNeural"},
        {"id": "ravi", "name": "Ravi", "look": "3d_youngman", "voice": "hi-IN-MadhurNeural"},
        {"id": "golu", "name": "Golu", "look": "3d_boy", "voice": "hi-IN-MadhurNeural"},
        {"id": "meera", "name": "Meera", "look": "3d_woman", "voice": "hi-IN-SwaraNeural"},
        {"id": "dog", "name": "Moti", "look": "flat_dog", "voice": "hi-IN-MadhurNeural"},
    ],
    "scenes": [
        {"background": "flat_city_street", "cast": ["dada", "golu"], "lines": [
            {"speaker": "dada", "text": "गोलू! फिर से क्रिकेट खेलकर खिड़की तोड़ दी?", "emotion": "angry", "action": "point"},
            {"speaker": "golu", "text": "नहीं दादा जी, वो तो रवि भैया ने तोड़ी!", "emotion": "scared", "action": "shrug"},
            {"speaker": "dada", "text": "झूठ मत बोल!", "emotion": "angry", "action": "slap"}]},
        {"background": "flat_swarg", "cast": ["meera", "ravi"], "lines": [
            {"speaker": "meera", "text": "वाह, स्वर्ग में स्वागत है!", "emotion": "happy", "action": "wave"},
            {"speaker": "ravi", "text": "मज़ा आ गया!", "emotion": "laughing", "action": "cheer"}]},
        {"background": "flat_nark", "cast": ["ravi", "dog"], "lines": [
            {"speaker": "ravi", "text": "ये कहाँ आ गया मैं?", "emotion": "surprised", "action": "talk"},
            {"speaker": "dog", "text": "भौं! नरक में!", "emotion": "angry", "action": "talk"},
            {"speaker": "ravi", "text": "ले मुक्का!", "emotion": "angry", "action": "punch"}]},
        {"background": "living_room", "cast": ["dada", "meera"], "lines": [
            {"speaker": "meera", "text": "दादा जी, चाय लीजिए।", "emotion": "happy", "action": "explain"},
            {"speaker": "dada", "text": "जीती रहो बेटी।", "emotion": "happy", "action": "sit_tea"}]},
    ],
}


def main(width=270):
    tl = normalize(SAMPLE)
    sched, total = build_schedule(tl, fake)
    comp = Composer(tl, sched, width, int(width * 16 / 9), 2)
    frames = []
    t0 = time.time()
    for sc in sched:
        for s in comp.flat.segments(sc):
            frames.append(comp.frame(s[0] + min(0.6, (s[1] - s[0]) / 2)))
    per = (time.time() - t0) / len(frames)
    cols = 5
    h = frames[0].height
    sheet = Image.new("RGB", (cols * width, ((len(frames) + cols - 1) // cols) * h), (255, 255, 255))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * width, (i // cols) * h))
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    sheet.save(out / "three_d_scenes.png")
    print(f"{len(frames)} shots, {per * 1000:.0f} ms per first frame, warnings: {comp.flat.warnings} -> {out / 'three_d_scenes.png'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 270)
