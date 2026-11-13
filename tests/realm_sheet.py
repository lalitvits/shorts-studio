"""Contact sheet of the Swarg and Nark backgrounds. Run:  python tests/realm_sheet.py [width]
Row 1: Swarg shots; row 2: Nark shots; row 3: the same Nark shot 0.25 s apart (to see the movement)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from studio.render import Composer, build_schedule, normalize  # noqa: E402
from tests.flat_sheet import fake  # noqa: E402

SAMPLE = {
    "title": "Swarg aur Nark", "captions": False,
    "characters": [
        {"id": "uncle", "name": "Uncle", "look": "flat_uncle", "voice": "hi-IN-MadhurNeural"},
        {"id": "aunty", "name": "Aunty", "look": "flat_aunty", "voice": "hi-IN-SwaraNeural"},
        {"id": "dog", "name": "Moti", "look": "flat_dog", "voice": "hi-IN-MadhurNeural"},
    ],
    "scenes": [
        {"background": "flat_swarg", "cast": ["aunty", "uncle"], "lines": [
            {"speaker": "aunty", "text": "वाह! स्वर्ग कितना सुंदर है।", "emotion": "happy", "action": "explain"},
            {"speaker": "uncle", "text": "यहाँ तो चाय भी मुफ़्त है!", "emotion": "excited", "action": "cheer"},
            {"speaker": "aunty", "text": "चलो अब घूमते हैं।", "emotion": "in_love", "action": "talk"}]},
        {"background": "flat_nark", "cast": ["uncle", "dog"], "lines": [
            {"speaker": "uncle", "text": "अरे बाप रे! ये नरक है!", "emotion": "scared", "action": "talk"},
            {"speaker": "dog", "text": "भौं! मैंने कहा था चप्पल मत चुराओ!", "emotion": "angry", "action": "talk"},
            {"speaker": "uncle", "text": "मुझे माफ़ कर दो!", "emotion": "crying", "action": "talk"}]},
    ],
}


def main(width=270):
    tl = normalize(SAMPLE)
    sched, total = build_schedule(tl, fake)
    comp = Composer(tl, sched, width, int(width * 16 / 9), 2)
    rows = []
    for sc in sched:
        rows.append([comp.frame(s[0] + 0.4) for s in comp.flat.segments(sc)][:4])
    nark = sched[1]
    t0 = time.time()
    rows.append([comp.frame(nark.start + 0.4 + i * 0.25) for i in range(4)])
    per = (time.time() - t0) / 4
    h = rows[0][0].height
    sheet = Image.new("RGB", (4 * width, len(rows) * h), (255, 255, 255))
    for r, row in enumerate(rows):
        for c, f in enumerate(row):
            sheet.paste(f, (c * width, r * h))
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    sheet.save(out / "realm_sheet.png")
    print(f"{per * 1000:.0f} ms per frame at {width}px -> {out / 'realm_sheet.png'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 270)
