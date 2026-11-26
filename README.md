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

## ElevenLabs voices (they act out every emotion)

Set `ELEVENLABS_API_KEY` (elevenlabs.io: Profile, API Keys; in a codespace add it as a Codespaces secret with that name). Pick an "ElevenLabs" voice for a character in the Cast step, or choose "ElevenLabs voices for everyone". Each line is spoken with its emotion (scared, crying, angry, sweet...) by the `eleven_v3` model, which speaks Hindi; set `ELEVENLABS_MODEL` to use another model. In the script format write `voice: eleven:liam` (a ready-made voice) or `voice: eleven:<voice id>` (any voice from your ElevenLabs library). Without a key, or when the month's free characters are used up, the line uses the Microsoft voice and the app warns you. Every line is made once and saved.

## Sketch-comedy tools (scripts like "2 AM pizza")

- **Paste a full script** (Story step): a screenplay with stage directions in brackets. Gemini turns it into characters, scenes, emotions, actions, sound effects, lighting, phone pop-ups, stickers, text cards and the ending; the dialogue is kept word for word. Gemini's safety filter sometimes refuses comedy with slaps or throws: the app tries three times, then tells you to press Import again or soften that line.
- **Bedroom at night** background, and **lighting** per scene: normal, night with the lights off, or dark lit by a phone (a blue glow on the face of whoever holds one). A line can **switch the light on or off** (with a click and a flash). **Appear**: a character is hidden until their line, then simply there.
- **"My brain" (inner voice)**: a floating pink brain with little devil horns that glows in the dark. **Voice effects** for any character: echo, devil, devil whisper, chipmunk, phone call.
- **Sounds**: stomach growl, notification ping, doorbell, chappal smack, audience laughter, meme boom, dun-dun-duuun, light switch, clock ticking, record scratch. Put a real recording in `assets/sounds/<name>.mp3` (for example `growl.mp3`) to replace a synthesized one; the growl in particular is only an approximation.
- **On screen**: a phone-notification banner per line (slides down with a ping; start the text with the app to choose its icon and name, and add a sender: `whatsapp: Mummy: खाना खा लिया?`, `bank: Rs 50,000 credited`, `phone: Missed call from Boss`. Apps: WhatsApp, Messages, Phone, Bank/UPI, Food, Shopping, Instagram, YouTube, Gmail, Calendar, Alarm, Battery, Settings, Telegram, Facebook, News. Without an app the words pick one, and a plain message is the default) and stickers (pizza, burger, money, heart, idea, angry, laugh, question, exclamation, sleep, fire).
- **Text cards** ("20 मिनट बाद" with a ticking clock), **black screen** endings (with laughter), and the **throw** action: a chappal flies at the camera, smack, shake.
- **New actions and props**: wipe tears, hold a food parcel, hide it behind the back, a realistic full-size phone.
- **Pacing**: the Microsoft voices are 10% faster and their long pauses between sentences are shortened, for snappy Shorts.

## Write scripts with any AI app (the Shorts Studio format)

In the Story step, open **Paste a full script**:

1. Type your idea (optional), pick the language and length, and press **Get the script format**. You get instructions, every value the app understands, and an example. Press **Copy** (or **Download as .txt**).
2. Paste it into any AI chat app (ChatGPT, Gemini, Claude, ...). It answers with a script in the format.
3. Paste that answer into the box and press **Import script**. A script in this format is read **exactly, with no AI and no daily limit**; anything it does not know is listed (for example a background you do not have yet).

What the format can say:
- **Characters**: look, gender, **height** (child, short, normal, tall, very tall, or a number), **build** (thin, normal, fat, very fat), **outfit colour**, voice and voice effect, or a narrator.
- **Scenes**: background (also your own pictures), lighting, music changes, length in seconds; **cards** (text screens and black endings).
- **Lines**: emotion, action and **movement** (walk / run / ride a cycle in or out, appear, step back...), **props** (mobile, glass of water, bottle, cup, cycle, suitcase, bag, umbrella, laptop, newspaper, flowers, parcel, jug, thali, chappal, lathi; food: samosa, plate of samosas, jalebi, vada pav, cutting chai, kulhad chai; fruit: banana, apple, mango, orange, grapes, watermelon; vegetables: tomato, onion, potato, carrot, brinjal, green chilli, cabbage, basket of vegetables, cloth bag of sabzi; a prop stays with the character until "prop: none"; eating or drinking with a food or chai prop uses it), **camera angle** (wide, single, over the shoulder, close-up, stove), sound effect, notification pop-up, sticker, big on-screen text, light switch, kadhai, cut-away, silent acting moments, and **meanwhile** (someone else acts while a line is spoken).
- Common words other AI apps use are understood too ("close-up", "mobile", "bicycle", "chubby", "enter"...), and speakers can be written by name ("दोस्त").

**My project in this format** writes your current project in the format, so you can edit it in another AI app and bring it back. The Cast step also has **height, build and outfit colour** for each character, and each line has a **Prop** menu.

## Story and safety-video tools (scripts like "kitchen fire")

- **Narrator (voice-over)**: add a character with the look "Narrator". It is never on screen; while it speaks, the camera keeps showing the scene. Any line can also make someone else act meanwhile ("Meanwhile: Neha, Step back in fear"), so the narration and the acting happen together.
- **Silent moments**: a line with no words and a number of seconds is an action beat ("Lalit covers the kadhai, 2 seconds"). A scene can have a length in seconds (from the script's 0:10 - 0:25), and it lasts at least that long.
- **Kadhai on the stove** (flat kitchen): a line can make it fry (puris, bubbles, sizzle), **catch fire** (flames shoot up, the camera shakes, warm flickering light on everyone), be **covered with a steel thali** (the fire dies, then smoke) or have the **gas turned off**. The camera keeps the stove in view, and there is a close-up shot of the stove.
- **New actions**: cook at the stove, step back in fear, run in, lift a water jug, jug pushed down (water splashes), grab someone's hand, turn off the gas, cover the kadhai, hand on someone's shoulder, look at the camera. A character who grabs a hand or touches a shoulder walks up to the nearest person; one who works at the stove walks to it.
- **Kid look** (about 10 years old, striped t-shirt) and a high, young voice.
- **Three 20-year-old young men**: A (open check shirt over a tee, quiff, light stubble, watch), B (hoodie, spiky hair) and C (graphic tee, side fringe, stubble, watch), each with a young voice. In the script format: look flat_youth_a / flat_youth_b / flat_youth_c (or "college boy", "hoodie boy", "student").
- **Sounds**: oil sizzling, fire flaring up, water splash, running footsteps, metal clang. The kitchen and action sounds are added by themselves.
- **Music that changes per scene** (with a cross-fade): for example panic while the fire burns, then calm while explaining. New tracks: Panic and Calm.
- **Cut-away (B-roll)**: while a line plays, the picture can cut to an **explainer animation** (why water on an oil fire explodes into a fireball, and why covering it with a plate puts it out, with step-by-step captions), or to one of your own pictures (Backgrounds), slowly zooming in.
- **Big text on screen**: a bold message over the picture from a line to the end of its scene; write a second, smaller line after ` | ` (for example `आग पर पानी न डालें, उसे ढकें! | NEVER USE WATER ON OIL FIRE`).
- **Mystery bag**: a travel bag lying on the floor of a scene, set per line with the **Bag** menu (`bag:` in the script format): lies there, **shakes by itself** (rustling sound), **pops open** (the camera cuts to a close-up of it), **a photo flies out** (an old sepia photo held up big in front of the camera, then it lies next to the bag), or is taken away. It stays in the next scenes with the same background, as it was left. "Walk up to the mystery bag" brings a character next to it, and "Camera: close-up on the mystery bag" shows it big.
- **One phone size**: the mobile is the same big phone whether someone uses it, just holds it, or makes a call.
- **Paste a full script** understands all of these: VO lines, visuals, kadhai, B-roll, on-screen text, music changes and scene timings.

## Stickman comedy (no dialogue, works in every country)

Tell the joke with actions, faces and sound effects only.

- **Stickmen**: Classic (black), Blue (spiky hair), Red (headband), Girl (bow, skirt), Kid (cap) and Boss (tie, glasses, mustache). They have big expressive eyes and can do every action, emotion and prop the flat cartoon people can.
- **Slapstick moves** (in the Action menu as "Comedy: ...", and they work for the flat cartoon people too): slip and fall, trip on the face, get up, get hit and fly off the screen, bonk on the head, freeze in shock, double-take, faint, fight in a dust cloud, run and crash into a wall, dizzy, shiver, cartoon run, run across the screen, chase, sneak in on tiptoe, roll on the floor laughing, kick, jaw drop, sleep on the floor (snoring, snot bubble), fall asleep standing, wake up with a jolt, poke someone, shake someone by the shoulders, exaggerated disappointment (slumps under a rain cloud). Poking and shaking walk up to the other person first; a slip shows the banana peel that caused it. Each move adds its own sound and effects, and a little camera shake when someone hits the ground. A fall stays down until that character's next action (for example "Get up").
- **Cartoon effects** (a line's **Effect** menu): dizzy stars, impact burst, speed lines, dust puffs, flying sweat, a red "!" or a "?" above the head, angry steam, floating hearts, shivering lines, a rain cloud over the head, eyes popping out, an idea bulb, sparkles, an alarm clock ringing beside them (with its sound), a fly buzzing around the head (with its sound), a snot bubble.
- **Cartoon sounds**: slip, slide whistle up and down, zip (fast run), bonk, dizzy birds tweeting, crash, glass breaking, crickets (awkward silence), sad trombone "wah wah waaah", sneaky tiptoe music, awooga horn, spring "doing", fight cloud, alarm clock, fly buzzing, snoring, poke "boop".
- **Made for phones**: in a stickman scene the camera keeps everyone big in a tight two-shot (faces readable on a phone), pulls back when someone lies down, runs or flies, cuts to a quick close-up on a jaw drop or a freeze, and pushes in on the last shot (the punchline). Stickmen move smoothly (15 poses a second, breathing when they stand, easing from one pose to the next), have bigger and clearer faces (happy eyes, an angry red face...), hold plates and books out in front, and show food bigger.
- **No dead time**: a silent simple gesture (wave, point, shrug, cheer...) lasts 1 second unless you set the seconds, and when everyone has left the frame the scene ends half a second later instead of showing an empty screen.
- **Invisible wall**: "Walk into an invisible wall" bonks into nothing; the glass shows for a moment. ("Crash into a brick wall" shows real bricks.)
- **Sound**: in a stickman video the music is louder and dips under every sound effect, and walking, fast gestures and big face changes get small sounds of their own (steps, whooshes, pops).
- **Backgrounds**: Plain white (the classic stickman look) and Doodle paper (notebook lines, hand-drawn hills, sun, drifting clouds).
- **How to make one**: add stickmen in Cast, pick the Plain white background, then add lines with **no words**: set the seconds, an action, an emotion, a sound and an effect. In the script format, write `tom (scared, slip_fall, silent: 2, fx: dizzy)`.
- **Stickman comedy script**: under "Paste a full script", the **Get the stickman script format** button gives a separate format just for stickman gags. Type a gag idea and a length, copy the format into ChatGPT, Gemini or any AI app, and paste its answer back to Import. It teaches the AI how to build a gag with only stickmen, slapstick moves, faces, cartoon effects and sounds, and no dialogue. It gives these rules: one simple situation everyone knows, 2 or 3 characters with a visible goal, 15 to 18 short beats, show instead of explaining, a visible cause for every action, three escalating attempts, big reactions, no dead beats, sounds on the physical beats, and a visual punchline in the last 3 seconds. It also lists ready ideas (banana trouble, the impossible fly, gym disaster, the last samosa, the sleeping champion) and includes a full example.

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

- **Cinematic look** (on by default; switch it off in "Make the video"): a warm late-afternoon colour grade with a soft sun glow, a gentle vignette and fine film grain; a slightly hazy background, softly out of focus in shots on one speaker; out-of-focus grass right in front of the camera in outdoor places; villagers walking past far behind the characters (village, chai tapri, park, street, bus stop); and medium shots that frame a talking speaker from the knees up, a little off-centre. Captions now sit in the lower middle of the picture, above the YouTube buttons. Stickman scenes on white or doodle paper keep their clean look.
- **The cast (the only characters in the Cast menu):** Lalit (rolled-up blue checked shirt over a white tee, side-parted hair), Rahul (yellow t-shirt, orange gamchha, a quiff with faded sides), Deepak (fat, round face, glasses, green hoodie, a short textured crop), plus the five village characters below and the narrator. They have realistic hair with a natural hairline, volume and strands. Older characters are hidden, not deleted: old projects still play, and scripts that name them get the nearest cast member (old "rahul" becomes the new Rahul, "aman" Lalit, "flat_uncle" Dadaji...).
- **Village characters:** Dadaji (bald with grey side tufts, round glasses, a big grey mustache, white kurta with buttons, a red checked gamchha and a walking stick), a village aunty (saree with a contrasting pallu, long braid, bindi, earrings), a village girl (kurta, dupatta, salwar, braid with a ribbon), a farmer (saffron pagdi, kurta-dhoti, big mustache, blue checked gamchha) and a cool dog (sunglasses, a cap worn backwards, a gold chain). In the script format: flat_dadaji, flat_village_aunty, flat_village_girl, flat_farmer, flat_cool_dog (or "dadaji", "bahu", "kisan", "cool dog"...).
- **Facing left and right:** people turn toward whoever they talk to (a 3/4 view: eyes, nose and mouth to that side, one ear), and anyone walking in, out or past is drawn fully side-on (the body in profile, legs striding, the near arm swinging, the head in profile). Dogs sit facing the camera in shots on them and walk side-on. With the cinematic look, characters also get a warm rim of sunlight on their edges, outdoor places get soft sun rays and floating dust, and the camera sways gently like a handheld one.
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

**Flat cartoon places** (they move): city street (day and night), park, village, school, kitchen, office, market (fruit stalls and string lights), bedroom at night, Swarg, Nark, and new: **chai ki tapri, "चाचा की चाय"** (a bright turquoise stall with a Hindi signboard, "चाचा की चाय" with chasing light bulbs round it, a pink and yellow striped awning with marigold garlands, truck-art flowers painted on the counter, a Hindi price board "मसाला चाय ₹10", colourful bunting across the street and a rangoli in front, under a big neem tree, in front of a street of painted houses: the chaiwala pours chai from high up, steam and bubbles, swinging chips packets, a flickering diya, a sleeping dog wagging its tail, leaves drifting down, a bench and red stools; it replaces the old "Village tea stall" picture), **sabzi mandi** (vegetable and fruit thelas, tarpaulin shades, sacks, a swinging scale, shoppers), **airport** (departure board with BOARDING blinking, planes taking off outside the windows, seats) and **bus stop** (shelter, bench, a bus driving past). In the script format you can also write them as "chai ki tapri" (or "chacha ki chai"), "sabzi mandi", "airport" or "bus stand".

The app has nine backgrounds, all in `assets/backgrounds/`: classroom, garden park, kitchen, living room, office, railway platform, school playground, street market and village tea stall. Each picture file is one background, and its file name is its name in the dropdown.

- **Add your own:** put pictures in the **`my_backgrounds/`** folder (next to `run.py`). They appear in the Background menus as "Your picture: ..." within a few seconds, with no restart; the Scenes step shows the folder, an **Open the folder** button and **Refresh pictures**. Pictures in that folder stay on your computer (they are not pushed to GitHub).
- **Supported files:** JPG / JPEG, PNG, WebP, BMP, GIF (first frame) and TIFF. HEIC (iPhone) photos: save them as JPG first. Vertical pictures (9:16, like 1080 x 1920) fit best. Other shapes are cropped from the centre. A file that cannot be read is skipped, and the Scenes step names it.
- A picture in `my_backgrounds/` with the same name as a built-in one (for example `kitchen.jpg`) replaces it. Saving over a picture is picked up from the next preview.
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

**Cancel**: while a video is being made, press **Cancel** next to the progress bar. It stops within a second or two (while voices or frames are being made), stops FFmpeg and deletes the half-made file. "Make it for me" and batch videos have a Cancel button too; there, videos already finished are kept. Once all frames are drawn, the last few seconds of encoding finish anyway.

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
