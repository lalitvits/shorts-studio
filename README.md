# Shorts Studio

Make vertical (1080x1920) Hindi or English short videos with cartoon characters on your own computer. Free to run.

You write a scenario, pick characters and backgrounds from dropdowns, edit the script, generate voices, and get an MP4 with moving characters, lip movement and word-highlighted captions. Upload it to YouTube yourself.

## Quick tour of the newest features

- **Make it for me** (Story step): type an idea and press one button. Gemini writes the script and a hook, the app picks backgrounds, emotions, actions and fitting music, makes the voices and the video. "Open it as a project" lets you change anything. **Batch mode** (same box) makes one video per idea, up to 20, one after another.
- **Hindi in Devanagari:** the script writer now always writes Hindi in Devanagari (it asks Gemini again if it answers in Roman letters). Choose "Hinglish (Roman letters)" if you want that instead.
- **Hook:** a big title that pops in during the first two seconds (Story step; Gemini writes one for you).
- **Effects** (Make video step, on by default): a zoom punch and whoosh between scenes, screen shake with a hit sound when a character punches or slaps, a pop for the hook. Effect sounds (punch, slap, whoosh, pop, ding, boing, thud) are also in each line's sound menu.
- **Built-in music:** six loops made by the app (happy, comedy, suspense, emotional, heavenly, dark drums), free to use. Put your own `assets/music/<name>.mp3` (for example `happy.mp3`) or `assets/sounds/punch.mp3` to replace one.
- **Walk in / walk out** actions: a character enters from the side of the frame, or leaves and stays gone for the rest of the scene.
- **3D characters:** 13 more faces (worried, scared, crying with tears, embarrassed with blush, angry with an anger mark, in love, thinking, ...) and props in the hand (phone, tea cup, book, snack).
- **Five more flat backgrounds:** village, school, kitchen, office and market, each with moving details.
- **After a full-quality video:** subtitles (`.srt`), a 9:16 and a 16:9 thumbnail with the title, and YouTube title, description and hashtags (written by Gemini), all next to the MP4 in `output/` and shown under the video with copy and download buttons. "Your recent videos" lists earlier videos with a player.
- **Undo / Redo** (left side, or Ctrl+Z / Ctrl+Y outside text boxes).
- **Series:** "New episode (same cast)" saves the current episode as a project and starts the next one with the same characters, voices, music and settings.
- **Gemini voice lines left today** is shown in the Voices step (free tier: about 10 lines per voice model per day).
- **Speed:** drawing a full-quality frame is about 30% faster. On computers with 6 or more CPU threads, frames are drawn in parallel; set `SHORTS_WORKERS=1` to turn that off (on a 2-core laptop it did not help, so it stays off there).

## Sketch-comedy tools (scripts like "2 AM pizza")

- **Paste a full script** (Story step): a screenplay with stage directions in brackets. Gemini turns it into characters, scenes, emotions, actions, sound effects, lighting, phone pop-ups, stickers, text cards and the ending; the dialogue is kept word for word. Gemini's safety filter sometimes refuses comedy with slaps or throws: the app tries three times, then tells you to press Import again or soften that line.
- **Bedroom at night** background, and **lighting** per scene: normal, night with the lights off, or dark lit by a phone (a blue glow on the face of whoever holds one). A line can **switch the light on or off** (with a click and a flash). **Appear**: a character is hidden until their line, then simply there.
- **"My brain" (inner voice)**: a floating pink brain with little devil horns that glows in the dark. **Voice effects** for any character: echo, devil, devil whisper, chipmunk, phone call.
- **Sounds**: stomach growl, notification ping, doorbell, chappal smack, audience laughter, meme boom, dun-dun-duuun, light switch, clock ticking, record scratch. Put a real recording in `assets/sounds/<name>.mp3` (for example `growl.mp3`) to replace a synthesized one; the growl in particular is only an approximation.
- **On screen**: a phone-notification banner per line (slides down with a ping) and stickers (pizza, burger, money, heart, idea, angry, laugh, question, exclamation, sleep, fire).
- **Text cards** ("20 मिनट बाद" with a ticking clock), **black screen** endings (with laughter), and the **throw** action: a chappal flies at the camera, smack, shake.
- **New actions and props**: wipe tears, hold a food parcel, hide it behind the back, a realistic full-size phone.
- **Pacing**: the Microsoft voices are 10% faster and their long pauses between sentences are shortened, for snappy Shorts.

## What you need

- Python 3.10 or newer
- FFmpeg
- A browser

## Set up (about five minutes)

1. Install FFmpeg
   - Windows: `winget install Gyan.FFmpeg` (then open a new terminal)
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
2. Install the Python packages: `pip install -r requirements.txt`
3. Start the app: `python run.py` (your browser opens at http://localhost:8000)

If something is missing, a yellow banner at the top of the app tells you what to install.

## Hindi voices, captions and script writing

**Voices.** The app uses the free `edge-tts` package (listed in requirements.txt). It talks to Microsoft's online read-aloud service, so it needs internet. It is an unofficial client: it can change or stop working, and the terms for monetised videos are unclear, so read them before you rely on it. Voices are hidden behind `studio/tts.py`, so you can add another engine without touching the rest. Without internet or without the package, the app uses silent clips so you can still test timing and animation.

**Your own audio: lip-sync and captions.** Lines without From/To times are fitted to the speech the app finds in your audio, so every character's mouth follows their own part even if you never press "Match my lines to the audio". **Write captions from my audio** (Scenes and sound step) has Gemini listen to each line's part and type its words: Hindi in Devanagari, English words in Latin letters, nothing translated. With no lines yet, it makes one line per spoken part, with the speakers taking turns. Lines you leave empty are also captioned automatically when you make the video, if captions are on. Each part is sent to Gemini once and saved.

**Gemini voices (emotional).** With your Gemini key set, pick a "Gemini" voice for a character in the Cast step (14 voices, for example Algenib for an old man, Sadachbia for a boy, Kore or Gacrux for women), or choose "Gemini voices for everyone" as the voice engine. Each line is spoken with its emotion (angry, crying, laughing, scared...) through an audio tag such as `[angry]`. The free tier allows only about **10 lines per day per voice model**. The app uses the next Gemini voice model when one runs out (about 30 lines a day in total), then the Microsoft voices, with a warning. Every line is made once and saved, so re-rendering costs nothing. Set `GEMINI_TTS_MODEL` to force one model.

**Captions.** Captions are burned in with FFmpeg's subtitle renderer, which shapes Hindi letters correctly. You need a Devanagari font. Windows (Nirmala), macOS and most Linux systems already have one. If you see empty boxes, put a font such as Noto Sans Devanagari into `assets/fonts/`. Word timing is estimated from word length, so highlights can drift a little on long sentences.

**Script writer.** Pick one in step 3:
- *Gemini*: create a free key in Google AI Studio and set `GEMINI_API_KEY`, then restart. Model names change often; if the default stops working, set `GEMINI_MODEL`. Free tiers have daily limits that can change.
- *Ollama*: run a model on your own computer. Set `OLLAMA_MODEL` (default `llama3.1`). Hindi quality depends on the model.
- *Basic split*: no AI. Splits your text into sentences and alternates the speakers.
- Or skip all of them and type the scenes yourself.

## Using GitHub Codespaces (no laptop)

1. Open the repository on GitHub (https://github.com/lalitvits/shorts-studio).
2. Click Code, then Codespaces, then Create codespace on main. The first start takes a few minutes: it installs FFmpeg, Hindi fonts, the Python packages and a Chromium browser for the 3D characters.
3. For Gemini (script writing, Gemini voices, captions from your audio): on GitHub open Settings, Codespaces, New secret, name it `GEMINI_API_KEY`, paste your key and allow this repository. Restart the codespace after adding it. Never put the key in the code: the repository is public.
4. The app starts by itself each time the codespace starts. Open the Ports tab and click the globe next to port 8000 (or "Open in Browser"). On a phone, keep that `...-8000.app.github.dev` link: it opens the app straight away while the codespace is running and you are signed in to GitHub in that browser. A small helper (`.devcontainer/start-app`) starts the app with the codespace and restarts it if it stops; on a new codespace it waits until the setup has installed everything. If the app is not running, look at `/tmp/shorts-studio.log` and `/tmp/shorts-studio-keeper.log`. A codespace stops itself after 30 idle minutes: start it again at github.com/codespaces and the app comes back within a minute.
5. Download the MP4 from the app, and stop the codespace when you finish. Free monthly hours are limited, and a 2-core machine renders slowly, so use quick previews.

## Maa

**Maa** (60 to 65, the mother, in a cream saree with red flowers and a maroon blouse) comes from her own sheet, which is a shaded 3D-style painting, so she looks different from the flat cartoon characters.

- **Face:** the real faces from her sheet, with her grey hair in a bun, bindi and gold earring. The sheet has only six expressions (warm, thinking, surprised, worried, sad, crying), so the other emotions borrow the closest one (see `assets/characters/maa/map.json`): for example angry and disgusted use the worried face, and laughing and excited use the large warm smile. The faces are small on the sheet, so they look soft at 1080p.
- **Body:** drawn in the app with the saree cloth, border and blouse pictures cut from her sheet, with gold bangles. It is a simplified saree (a cloth across the chest, the loose end over one shoulder, and a border along the hem), not the sheet's full drape. Her side and back views from the sheet are not used.
- **Lip-sync:** the mouth in her picture is removed and a soft mouth opens and closes with the voice. It does not move for thinking, confused and sad (the hand or the cut chin gets in the way).
- Choosing Maa or Priya in the Look dropdown switches a default male voice to the female one (and back for the others); you can still pick any voice.
- To redo her faces from the sheet: `python tools/extract_maa.py maa_sheet.png` (needs `numpy scipy opencv-python-headless`).

## Flat cartoon style (street cartoons)

A second drawing style, like simple 2D street cartoons: outlined flat characters, a city street with cars driving past and birds flying, and a camera that cuts between shots on its own.

- **Turn it on:** pick a "Flat cartoon" background (city street, city street at night, park) or any "Flat:" character (Uncle in a red cap and vest, Aunty, Boy, Young man, Girl, Dog, Cat). Older characters in such a scene are redrawn as flat people in their own colours, and flat characters in a picture background keep that picture.
- **Automatic camera:** the first line of a scene is a wide shot with everyone. After that the speaker is shown over the other character's shoulder (the background goes soft), or on their own when the other one is an animal, with a close-up for strong emotions (angry, crying, laughing, shocked...). In long lines the camera cuts to the listener's reaction. Every shot drifts and zooms in slowly. Choose a shot for a line in the Scenes step ("Camera: ...") to override it.
- **Swarg and Nark:** two more flat backgrounds that move all the time. *Swarg* (heaven): a golden palace on a cloud floor, a rainbow, turning sun rays, drifting clouds, twinkling sparkles, falling flower petals and flying doves. *Nark* (hell): Yama's gate with a skull, a lava river with flickering flames and popping bubbles, boiling cauldrons with fire and steam, glowing cracks in the rock, rising embers and bats. They are drawn in `studio/realms.py`; `python tests/realm_sheet.py` draws a contact sheet.
- **Animals talk too:** the dog and cat move their mouths with their voice, wag their tails when happy and cry with tears.
- **Captions** can be switched off in the Make video step (flat cartoons usually have none).
- Open the saved project **flat-cartoon-uncle-and-dog** for a ready example, and `python tests/flat_sheet.py` draws a contact sheet of every shot into `tests/out/`.
- To add your own flat character, add an entry to `_FLAT` in `studio/catalog.py` (colours, cap or hair, top and bottom).

## 3D characters

Four real 3D characters: **Old man** (grey hair, mustache, green cardigan), **Young man** (yellow hoodie), **Boy** (spiky hair, black zip hoodie) and **Young woman** (sari). Pick them in the Cast step ("3D: ..."). They act in every flat-cartoon background (street, park, Swarg, Nark) and in picture backgrounds, with the same automatic camera, lip-sync and blinking.

- **Actions:** all the usual ones, plus **Punch** and **Slap**. "Sit ..." actions sit on a stool, and "Sit and sleep" lies down.
- **Moods:** the 20 emotions map onto happy, neutral, sad, angry, surprised, laughing and sleepy faces.
- **How it works:** the models are built with Three.js (`studio/web3d/chars.js`, made from the four preview pages), and a hidden Microsoft Edge or Google Chrome window draws them for each frame. You need `pip install playwright` (in requirements.txt) and Edge or Chrome installed. No extra browser download is needed. Without them, these characters are drawn as flat cartoons and the app shows a warning.
- They take a little longer to render than flat characters (about 80 ms per character per frame at full quality).
- `python tests/three_d_sheet.py` draws a sheet of them in scenes.

## Characters, emotions and activities

- **Five characters.** Rahul, Aman and Priya are copied from their character sheets, Maa from her own sheet, and Golu is a clay-toy 3D character built from shapes: **Rahul** (blue hoodie, 28, lead), **Aman** (orange hoodie, 26, supportive friend) and **Priya** (green hoodie, 27, co-lead). Each has hoodie, dark jeans and white sneakers in the sheet's colours, and the real face pictures from the sheet.
- **Emotions (20):** neutral, happy, sad, worried, angry, surprised, laughing, crying, scared, excited, sleepy, embarrassed, confused, bored, in love, proud, disgusted, thinking, shocked, relieved. Each face is the picture from the sheet. The effect marks (sparkles, anger mark, sweat drops, hearts, "zzz", question marks) are drawn by the app so they stay sharp, and the body changes with the emotion when the character has no other action.
- **Gestures:** talk, stand still, wave / greet, point, think, explain (open hands), thumbs up, OK sign, stop, arms crossed, shrug, look around, walk in place, jump, cheer / celebrate, clap, dance, facepalm.
- **Activities with props:** use phone, **talk on phone** (the phone is held at the ear and the mouth moves), drink tea, read a book, eat a snack.
- **Sitting on a sofa:** sit, sit and use phone, sit and drink tea, sit and read, sit and eat, sit and sleep. A character with any "sit" line sits for the whole scene. If two characters sit, they share one sofa.
- A character keeps doing a long activity (tea, phone, book, snack, arms crossed, sitting) while the other one talks.
- `python tests/pose_sheet.py` draws contact sheets of everything into `tests/out/` so you can check how it looks.

## Faces

Each face is `assets/characters/<name>/heads/<emotion>.png` (20 per character, about 390 pixels wide, transparent background). They were cut out of your three sheets, enlarged 3 times and cleaned (flat colour regions, smooth edges), so they are sharp in a 1080 x 1920 video. The faces on the sheets are about 110 pixels wide, so very fine details (tiny eye highlights, thin lashes) are simplified a little.

To use sharper pictures of your own, replace the files:

1. Make a bigger picture (600 pixels or more) of the face in the same style, on a transparent background (PNG).
2. Save it under the same name, for example `assets/characters/rahul/heads/happy.png`. Emotion names: neutral, happy, sad, angry, worried, surprised, laughing, crying, scared, excited, sleepy, embarrassed, confused, bored, in_love, proud, disgusted, thinking, shocked, relieved.
3. Framing: head centred left to right, face centre about 57% down the picture, and ear to ear about 55% of the picture width. Leave out the hoodie and the effect marks.
4. A missing emotion uses the neutral picture. Restart the app after changing files.

`python tools/extract_sheet_faces.py rahul.png aman.png priya.png` redoes the cut-out and clean-up from the three original sheets (file names must contain the character's name). Only this tool needs extra packages: `pip install numpy scipy scikit-learn opencv-python-headless`.

## Backgrounds

The app has nine backgrounds, all in `assets/backgrounds/`: classroom, garden park, kitchen, living room, office, railway platform, school playground, street market and village tea stall. Each picture file is one background, and its file name is its name in the dropdown.

- **Add one:** drop a picture (PNG, JPG or WebP) into `assets/backgrounds/` and restart the app. Vertical pictures (9:16, like 1080 x 1920) fit best. Other shapes are cropped from the centre.
- **Remove one:** delete its file.
- Characters stand with their feet about 78% of the way down the picture, so pictures with the floor or ground in the lower part work best.
- Older projects that used the previous backgrounds (room, street, park, village) open with the closest new one.

## 3D-like look

In **Make video**, the **3D-like look** box (on by default) gives the flat characters soft lighting, shading and depth: light from the top left, rounded shading on the face, hair and clothes, softer edges, a soft shadow on the floor, and a slight blur and vignette on the background so the characters stand out. It is a look, not true 3D (the characters are still flat drawings that are lit and shaded). Untick the box for the original flat cartoon look, which renders faster.

## Lip-sync (mouth shapes that follow the words)

The mouth does not just open and close with the loudness. The text of each line becomes a sequence of mouth shapes, and the shapes are laid out over the parts of the voice that are actually sounding (following Maa's lip-sync reference):

- **12 shapes:** rest/closed, **Aa** (आ, wide open), **Ee** (इ ई, teeth), **Oo** (उ ऊ, rounded), **Eh** (ए ऐ), **Oh** (ओ औ), **Ba** (ब प म, lips pressed), **Fa/Va** (फ व), **Th/Dh** (थ ध), **Ta/Da** (ट ड त द न), **La** (ल), **Ra** (र). क ख ग घ ह take the shape of the vowel after them, and the mouth stays open longer for them and for आ.
- **Timing:** the mouth starts moving about 0.1 s before the sound, closes at commas and full stops, and rests in silent gaps in the audio. With your own audio the shapes skip the silent parts; with the silent test voices the whole line is used. Shapes blend into each other a little (smoothing).
- **Mood:** happy opens the mouth a little more, sad a little less; Maa's resting mouth matches her mood (worried, sad, crying, surprised, affectionate).
- **Maa** uses the real mouth photos from her reference sheet pasted onto her face. The other characters get the same twelve shapes drawn in their own style.
- It follows the **text and the loudness**; it does not listen to the words. With your own audio, the line's text should match what is said, otherwise the shapes drift. A line with no text (only audio) falls back to opening with the loudness.
- A line that only has an emotional sound (a reaction) keeps the picture's own mouth, for example the big laughing mouth.
- **Stand still (mouth does not move):** if a line's action is Stand still, the mouth does not move at all, even though the voice or audio plays. Choose Talk (or another action) when you want lip-sync.
- For **sleepy, bored and thinking** (and **confused** for Rahul and Maa, **sad** for Maa) the picture has a hand over the mouth or no usable lower face, so the mouth cannot move there: use another emotion while someone is talking.
- The mouth is drawn in the same place on every face picture. If you replace face pictures, keep the framing described under Faces.
- To redo Maa's mouth photos: `python tools/extract_maa_visemes.py maa_lip_sync_reference.png`.

## Golu (clay 3D toy)

**Golu** is a simple 3D-looking character built from shapes, like a clay toy: a round head with a tuft of hair, a bean-shaped body, thick arms and legs, mitten hands and round red shoes, all lit from the top left with soft shading and no outlines. There are no picture files: the app draws him from spheres and cylinders (`studio/clay.py`). He uses the same skeleton as everyone else, so every action, emotion, prop and the lip-sync work for him too.

- He is a toy made of shapes, not a sculpted 3D model, so he looks simpler than the character sheets.
- He is always shaded, so the **3D-like look** box does not change him (it still changes the floor shadow and the background).
- His face is painted flat on the head, and props and effect marks (phone, tea mug, sparkles) are flat drawings.
- To change his colours, edit the `clay` entry in `studio/catalog.py` (skin, shirt, pants, hair, shoe).

## Emotional sounds (optional)

Every line has a **Sound** dropdown, set to **No sound** unless you choose one. The choices are laugh, giggle, cry, angry growl, frustrated groan, sigh, gasp, scream, yawn and hmm (thinking). The ▶ button next to it plays the sound.

- **A reaction:** a line with a sound and no words. The character stays in the scene and reacts (face and body) while the sound plays. This is how a character who is not talking can laugh or growl. Pick the speaker, the sound, and an emotion; the app suggests a matching emotion and a standing pose when the line is still neutral.
- **A sound before words:** a line with both words and a sound plays the sound first, then the words.
- **With your own audio:** a reaction line without times is added after the scene's speech, one after another, and makes the scene a little longer. Give it From/To times to place it somewhere inside the scene instead. Reaction lines do not use up a spoken part when you press Match my lines to the audio.
- Sounds are played one line at a time, so a reaction cannot overlap another character's speech (with your own audio you can overlap by giving the reaction line times).

**Where the sounds come from:** the app makes simple synthesized sounds with no internet needed. Their pitch follows the character's voice (male or female). They are recognisable but clearly artificial. For natural sounds, put your own recordings in `assets/sounds/`: name a file after the sound, for example `laugh.mp3`, or `laugh_female.mp3` and `laugh_male.mp3` to use different recordings for female and male characters. Your file is used instead of the synthesized one (the first 10 seconds are used). The sound names are: laugh, giggle, cry, angry, frustrated, sigh, gasp, scream, yawn, hmm. Restart the app after adding files.

## Characters in a scene

Each scene has its own list of **characters in this scene** (under the scene's background). A character stays in the picture for the whole scene, even if they have no dialogue: they stand there and listen. They leave only when you take them out with the ✕ on their name. Use **Add character** to bring one in. Taking a character out of a scene also deletes their lines in that scene (the app asks first). A scene can have characters and no lines at all, and then it holds for a moment.

## Your own audio

In the **Scenes and sound** step choose **My own audio file (voice-over or dubbing)** instead of the voices made by the app. The characters then only act: they move, change expression, and their mouths move with your audio. You still write the scenes and dialogue by hand as before.

1. Choose your audio file (MP3, WAV, M4A, AAC, OGG or FLAC) from your computer. A waveform appears, with each scene's part shaded in its own colour.
2. Write your scenes and lines (the text becomes the captions; it can be empty if you do not want captions on a line).
3. Press **Match my lines to the audio**. The app finds the spoken parts, gives each line a start and end time, and trims each scene to its part of the audio. If the number of parts differs from your number of lines, it merges or splits some and tells you to check. The pause setting changes where parts split.
4. **Trim each scene yourself:** every scene has an **Audio for this scene** box with From and To seconds, taken from the same audio file. Change them to use a different part, press **▶ Play** to hear exactly what that scene will play, or **Fit to lines** to reset them from the scene's lines. **Play all scenes in order** plays the trimmed parts one after another, the way the video will sound.
5. Each line also has "Spoken from / to" seconds (time in the original audio): these set when the speaker's mouth moves.
6. The video plays the scenes in order, each for the length of its trimmed audio, and the trimmed parts are joined into the soundtrack.

**Background music** (optional, either mode): choose a music file and a volume. It is repeated if it is shorter than the video.

Notes: your audio files are kept in `data/uploads` on your computer. A video longer than 3 minutes is not a YouTube Short, and the app warns you.

## Quality choices

In **Make video**: **Low quality** is 270 x 480 and renders fastest (good for checking timing, but small), **Quick preview** is 540 x 960, and **Full quality** is 1080 x 1920.

## Make it yours

- **New character:** add an entry in `studio/catalog.py` (colours, size) and a folder of 20 face pictures in `assets/characters/<id>/heads/`.
- **New voice:** add an entry in `studio/catalog.py`. It shows up in the dropdowns and in the AI prompt.
- **New action or emotion:** add a branch in `pose_for` in `studio/rig.py`, and add its name to the lists in `catalog.py`.
- **Your own character art:** the character is drawn from a skeleton in `studio/rig.py`. Replace the shape drawing in `draw_character` with sprite images rotated around the same joint positions.

## How it works

`web/` (screens) calls `studio/server.py`, which uses `script.py` (scenario to scenes), `tts.py` (voices), `audio.py` (your own audio files), `sfx.py` (emotional sounds) and `render.py` (draws each frame with `rig.py` and `backgrounds.py`, then pipes frames and audio to FFmpeg). A project is one JSON timeline: characters plus scenes with lines (speaker, text, emotion, action).

## Check it works

`python tests/smoke_test.py` renders a still of every background and a short sample video into `output/`.

## Known limits

- Quick preview is about 2x faster than full quality. Rendering is single-threaded drawing plus FFmpeg encoding, so long videos take minutes.
- Characters face the camera. The sheets' side, 3/4 and back views, the outfit variations and the laptop poses are not in the app yet, and characters stay in place instead of walking across the screen.
- Preview thumbnails draw captions with Pillow; on some Windows setups Hindi in the thumbnail can look slightly off even though the video captions are correct.
- Props are limited to a phone, a mug, a snack and a book, and there is one sofa style. More are easy to add in `studio/rig.py`.
- No background music yet.
