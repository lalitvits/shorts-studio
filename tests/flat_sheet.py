"""Contact sheet of the flat cartoon style (no voices needed). Run:  python tests/flat_sheet.py
Writes tests/out/flat_sheet.png with frames from every camera shot, plus a timing figure."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from studio.render import Composer, build_schedule, normalize  # noqa: E402
from studio.tts import ENV_HZ, Clip, estimate_seconds  # noqa: E402

SAMPLE = {
    "title": "Uncle and the street dog",
    "captions": False,
    "characters": [
        {"id": "uncle", "name": "Uncle", "look": "flat_uncle", "voice": "hi-IN-MadhurNeural"},
        {"id": "dog", "name": "Moti", "look": "flat_dog", "voice": "hi-IN-MadhurNeural"},
        {"id": "aunty", "name": "Aunty", "look": "flat_aunty", "voice": "hi-IN-SwaraNeural"},
        {"id": "boy", "name": "Chintu", "look": "flat_boy", "voice": "hi-IN-MadhurNeural"},
    ],
    "scenes": [
        {"background": "flat_city_street", "cast": ["uncle", "dog"], "lines": [
            {"speaker": "uncle", "text": "अरे ओ मोती! फिर से मेरी चप्पल ले गया तू?", "emotion": "angry", "action": "talk"},
            {"speaker": "dog", "text": "भौं भौं! मैंने कुछ नहीं किया अंकल!", "emotion": "crying", "action": "talk"},
            {"speaker": "uncle", "text": "झूठ मत बोल, पूरी गली ने देखा है तुझे मेरी नई चप्पल लेकर भागते हुए, समझा?", "emotion": "angry", "action": "point"},
            {"speaker": "uncle", "text": "हा हा हा, चल माफ़ किया।", "emotion": "laughing", "action": "talk"},
            {"speaker": "dog", "text": "थैंक यू अंकल!", "emotion": "happy", "action": "talk"}]},
        {"background": "flat_park", "cast": ["aunty", "boy"], "lines": [
            {"speaker": "aunty", "text": "चिंटू, होमवर्क किया?", "emotion": "worried", "action": "talk"},
            {"speaker": "boy", "text": "हाँ मम्मी, सब कर लिया!", "emotion": "happy", "action": "thumbs_up"},
            {"speaker": "aunty", "text": "सच में? दिखाओ ज़रा।", "emotion": "surprised", "action": "explain"}]},
        {"background": "flat_city_night", "cast": ["boy"], "lines": [
            {"speaker": "boy", "text": "आज तो बच गया!", "emotion": "relieved", "action": "cheer"}]},
        {"background": "living_room", "cast": ["uncle", "aunty"], "lines": [
            {"speaker": "aunty", "text": "चाय पियोगे?", "emotion": "happy", "action": "drink_tea"},
            {"speaker": "uncle", "text": "हाँ, ज़रूर।", "emotion": "happy", "action": "phone_call"}]},
    ],
}


def fake(ln, ch):
    secs = estimate_seconds(ln["text"])
    env = [0.2 + 0.7 * ((i // 2) % 2) for i in range(int(secs * ENV_HZ))]
    return Clip(Path(""), secs, env, synthetic=True)


def main(width=360):
    tl = normalize(SAMPLE)
    sched, total = build_schedule(tl, fake)
    comp = Composer(tl, sched, width, int(width * 16 / 9), 2)
    times = []
    for sc in sched:
        for seg in comp.flat.segments(sc) if comp.flat.handles(sc) else [(sc.start, sc.end, None)]:
            times.append(seg[0] + min(0.6, (seg[1] - seg[0]) / 2))
    t0 = time.time()
    frames = [comp.frame(t) for t in times]
    per = (time.time() - t0) / len(frames)
    t0 = time.time()
    for i in range(30):
        comp.frame(sched[0].start + 0.5 + i / 30)
    per2 = (time.time() - t0) / 30
    cols = 6
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * frames[0].height), (255, 255, 255))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * width, (i // cols) * f.height))
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    sheet.save(out / "flat_sheet.png")
    print(f"{len(frames)} shots, total {total:.1f}s, first frame of a shot {per * 1000:.0f} ms, "
          f"following frames {per2 * 1000:.0f} ms at {width}px wide -> {out / 'flat_sheet.png'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 360)
