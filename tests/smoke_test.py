"""Quick end-to-end check. Run from the project folder:  python tests/smoke_test.py"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.backgrounds import list_backgrounds  # noqa: E402
from studio.render import render_still, render_video  # noqa: E402

SAMPLE = {
    "title": "Rahul and the locked door",
    "tts": "silent",
    "characters": [
        {"id": "rahul", "name": "Rahul", "look": "rahul", "voice": "hi-IN-MadhurNeural"},
        {"id": "priya", "name": "Priya", "look": "priya", "voice": "hi-IN-SwaraNeural"},
        {"id": "aman", "name": "Aman", "look": "aman", "voice": "hi-IN-MadhurNeural"},
        {"id": "maa", "name": "Maa", "look": "maa", "voice": "hi-IN-SwaraNeural"},
        {"id": "golu", "name": "Golu", "look": "clay", "voice": "hi-IN-MadhurNeural"},
    ],
    "scenes": [
        {"background": "living_room", "cast": ["rahul", "priya", "aman"], "lines": [   # Aman never speaks but stays in the scene
            {"speaker": "rahul", "text": "अरे, चाबी कहाँ है?", "emotion": "worried", "action": "look_around"},
            {"speaker": "priya", "text": "रुको, मैं ढूँढती हूँ।", "emotion": "happy", "action": "point"},
            {"speaker": "aman", "text": "", "sound": "laugh", "emotion": "laughing", "action": "idle"},      # a reaction
            {"speaker": "rahul", "text": "हद है!", "sound": "frustrated", "emotion": "angry", "action": "talk"}]},
        {"background": "living_room", "lines": [
            {"speaker": "rahul", "text": "चाय पीते हुए सोचते हैं।", "emotion": "neutral", "action": "sit_tea"},
            {"speaker": "priya", "text": "देखो, फ़ोन पर चाबी की फ़ोटो है!", "emotion": "excited", "action": "sit_phone"},
            {"speaker": "rahul", "text": "हा हा, मैं भूल गया था!", "emotion": "laughing", "action": "sit_tea"}]},
        {"background": "flat_chai_tapri", "lines": [
            {"speaker": "rahul", "text": "मिल गई! चलो, दरवाज़ा खोलें।", "emotion": "happy", "action": "thumbs_up"},
            {"speaker": "priya", "text": "शाबाश! हम जीत गए!", "emotion": "proud", "action": "cheer"},
            {"speaker": "maa", "text": "शाबाश बच्चो!", "emotion": "happy", "action": "talk"},
            {"speaker": "golu", "text": "वाह, बहुत बढ़िया, बेटा!", "emotion": "excited", "action": "cheer"}]},
    ],
}

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "out"
    out.mkdir(exist_ok=True)
    for bg in list_backgrounds():
        tl = json.loads(json.dumps(SAMPLE))
        tl["scenes"][0]["background"] = bg["id"]
        (out / f"still_{bg['id']}.png").write_bytes(render_still(tl, 0, 0, 360))
    print("stills ok:", len(list_backgrounds()))
    t = time.time()
    res = render_video(SAMPLE, "preview", lambda s, f: None)
    print("video:", res, f"{time.time() - t:.1f}s")
