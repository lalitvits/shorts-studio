"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const KEY = "shorts_studio_v1";
const STEPS = ["Story", "Cast", "Scenes and sound", "Voices", "Make video"];
const EXAMPLE = {
  title: "राहुल और बंद दरवाज़ा",
  scenario: "राहुल को घर में एक बंद दरवाज़ा मिलता है। प्रिया उसे चाबी ढूँढने में मदद करती है। आख़िर में चाबी मिल जाती है और दोनों खुश होते हैं।",
};
let A = null;   // menus from the server
let S = null;   // project state

const fresh = () => ({
  title: "", scenario: "", language: "hi", seconds: 30, look3d: true, captions: true, tts: "best", provider: "gemini", step: 1, counter: 2,
  characters: [
    { id: "c1", name: "Lalit", look: "flat_lalit", voice: "hi-IN-MadhurNeural" },
    { id: "c2", name: "Rahul", look: "flat_rahul", voice: "hi-IN-MadhurNeural" },
  ],
  scenes: [], sel: { scene: 0, line: 0 },
  hook: "", effects: true, cinematic: true,
  audio: { mode: "tts", id: "", name: "", seconds: 0, url: "", pause: 0.45, musicId: "", musicName: "", musicUrl: "", musicVolume: 20, musicBuiltin: "" },
});
const HIST = { list: [], at: -1, last: 0, quiet: false };
function record() {                               // undo history: one step per pause in editing
  const snap = JSON.stringify({ ...S, step: undefined });
  if (HIST.list[HIST.at] === snap) return;
  const now = Date.now();
  HIST.list.length = HIST.at + 1;                 // a new change drops the redo steps
  if (now - HIST.last < 700 && HIST.at > 0) HIST.list[HIST.at] = snap;   // typing: merge into one step
  else { HIST.list.push(snap); HIST.at++; if (HIST.list.length > 80) { HIST.list.shift(); HIST.at--; } }
  HIST.last = now;
}
const save = () => { localStorage.setItem(KEY, JSON.stringify(S)); if (!HIST.quiet) record(); };
function undoRedo(dir) {
  const at = HIST.at + dir;
  if (at < 0 || at >= HIST.list.length) return toast(dir < 0 ? "Nothing to undo." : "Nothing to redo.");
  HIST.at = at; HIST.quiet = true;
  const step = S.step;
  S = { ...fresh(), ...JSON.parse(HIST.list[at]), step };
  save(); init(true); HIST.quiet = false;
  toast(dir < 0 ? "Undone." : "Redone.");
}
document.addEventListener("keydown", e => {
  if (!(e.ctrlKey || e.metaKey)) return;
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || "");
  if (typing) return;                             // inside a text box the browser's own undo works
  const k = e.key.toLowerCase();
  if (k === "z" && !e.shiftKey) { e.preventDefault(); undoRedo(-1); }
  else if (k === "y" || (k === "z" && e.shiftKey)) { e.preventDefault(); undoRedo(1); }
});
const timeline = () => ({ title: S.title, tts: S.tts, characters: S.characters, scenes: S.scenes, look3d: S.look3d !== false,
  captions: S.captions !== false, language: S.language,
  hook: S.hook || "", effects: S.effects !== false, cinematic: S.cinematic !== false,
  audio: { mode: S.audio.mode, id: S.audio.id, music_id: S.audio.musicId, music_volume: S.audio.musicVolume,
           music_builtin: S.audio.musicBuiltin || "" } });

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const type = r.headers.get("Content-Type") || "";
  if (!type.includes("json")) { if (!r.ok) throw new Error("Request failed"); return r; }
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "Request failed");
  return j;
}
let toastTimer;
function toast(msg, bad) {
  const t = $("#toast");
  t.textContent = msg; t.className = "show" + (bad ? " bad" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = ""; }, bad ? 9000 : 3500);
}
const opts = (list, sel) => list.map(o => {
  const id = o.id ?? o, label = o.label ?? String(o).replace(/_/g, " ");
  return `<option value="${esc(id)}"${String(id) === String(sel) ? " selected" : ""}>${esc(label)}</option>`;
}).join("");
const defaultBg = () => (A.backgrounds.find(b => b.id === "living_room") || A.backgrounds[0] || {}).id || "";
const charOpts = () => S.characters.map(c => ({ id: c.id, label: c.name || c.id }));

function getPath(p) { return p.split(".").reduce((o, k) => o?.[k], S); }
function setPath(p, v) {
  const ks = p.split("."), last = ks.pop();
  ks.reduce((o, k) => o[k], S)[last] = v;
}

// ------------------------------------------------------------------ screens
function renderNav() {
  $("#nav").innerHTML = STEPS.map((s, i) =>
    `<button data-act="go" data-step="${i + 1}"${S.step === i + 1 ? ' aria-current="step"' : ""}><span class="n">${i + 1}</span>${s}</button>`).join("");
}
function showStep(n) {
  S.step = n; save(); renderNav();
  document.querySelectorAll(".step").forEach(el => { el.hidden = el.id !== "step-" + n; });
  if (n === 3) { renderScenes(); renderAudio(); refreshBackgrounds(); }
  window.scrollTo({ top: 0 });
  refreshPreview();
}
function renderBgFolder() {
  const el = $("#bg-folder"), f = A.bg_folder;
  if (!el || !f) return;
  el.innerHTML = `<b>Your own backgrounds</b>: put pictures in the folder <code>${esc(f.folder)}</code>
    and they appear in the Background menus as "Your picture: ..." (no restart needed).
    Supported files: ${esc(f.supported)}. Vertical pictures (9:16, like 1080 x 1920) fit best; others are cropped from the centre.
    ${f.count ? `You have ${f.count} picture${f.count > 1 ? "s" : ""} there.` : "The folder is empty for now."}
    ${f.skipped && f.skipped.length ? `<br><span class="bad-text">Could not read: ${esc(f.skipped.join(", "))}. Save them again as JPG or PNG.</span>` : ""}
    <div class="actions" style="justify-content:flex-start;margin-top:6px">
      <button class="secondary" data-act="open-bg-folder">Open the folder</button>
      <button class="secondary" data-act="refresh-bgs">Refresh pictures</button></div>`;
}
async function refreshBackgrounds(announce) {            // new pictures in the folder show up without a restart
  try {
    const r = await fetch("/api/backgrounds").then(x => x.json());
    const before = (A.backgrounds || []).map(b => b.id).join("|");
    A.backgrounds = r.backgrounds; A.bg_folder = r.bg_folder;
    renderBgFolder();
    if (r.backgrounds.map(b => b.id).join("|") !== before && S.step === 3) renderScenes();
    if (announce) toast(`${r.bg_folder.count} of your own picture${r.bg_folder.count === 1 ? "" : "s"} found.`);
  } catch (e) { if (announce) toast("Could not look for pictures: " + e.message, true); }
}
window.addEventListener("focus", () => { if (S.step === 3) refreshBackgrounds(); });
function renderSeries() {
  const el = $("#series-info");
  if (el) el.textContent = S.series ? `Series: ${S.series}, episode ${S.episode || 1}` : "";
  const v = $("#voices-left");
  if (v && A.system.gemini) v.textContent = `About ${A.system.gemini_voices_left} Gemini voice lines left today on the free tier (lines you made before cost nothing).`;
}
function renderBanners() {
  const b = [], s = A.system;
  if (!s.ffmpeg) b.push(["bad", "FFmpeg was not found, so videos cannot be made yet. Install FFmpeg, then restart the app (see the README)."]);
  if (!s.edge_tts) b.push(["", "Hindi voices need one more package: run pip install edge-tts, then restart. Until then voices are silent."]);
  if (!s.font) b.push(["", "No Devanagari font was found, so Hindi captions may show empty boxes. Put a font such as Noto Sans Devanagari in assets/fonts."]);
  $("#banners").innerHTML = b.map(([c, m]) => `<div class="banner ${c}">${esc(m)}</div>`).join("");
}
function renderStory() {
  document.querySelectorAll("#step-1 [data-path], #step-3 .soundbox [data-path], #step-4 [data-path], #step-5 [data-path]").forEach(el => {
    const v = getPath(el.dataset.path);
    if (el.type === "radio") el.checked = v === el.value;
    else if (el.type === "checkbox") el.checked = v !== false;
    else el.value = v ?? "";
  });
}
function tune(c) {                                 // the character's voice pitch / speed, or the look's default
  const d = (A.voice_tune || {})[c.look] || [0, 0];
  return [c.voice_pitch ?? d[0], c.voice_rate ?? d[1]];
}
function renderCast() {
  $("#cast").innerHTML = S.characters.map((c, i) => `
    <div class="char">
      <label>Name<input data-path="characters.${i}.name" lang="hi" value="${esc(c.name)}"></label>
      <label>Look<select data-path="characters.${i}.look">${opts(A.looks, c.look)}</select></label>
      ${c.look === "narrator" ? "" : `<div class="full body-row">
        <select aria-label="Height" data-path="characters.${i}.height">${opts(A.heights || [], c.height || "")}</select>
        <select aria-label="Build" data-path="characters.${i}.build">${opts(A.builds || [], c.build || "")}</select>
        <select aria-label="Outfit colour" data-path="characters.${i}.outfit">${opts(A.outfits || [], c.outfit || "")}</select>
      </div>`}
      <div class="full">
        <label>Voice<select data-path="characters.${i}.voice">${opts(A.voices, c.voice)}</select></label>
        <button class="secondary" data-act="sample-char" data-i="${i}">Hear voice</button>
        <label class="tune">Voice effect<select data-path="characters.${i}.voice_fx">${opts(A.voice_fx || [], c.voice_fx ?? (c.look === "flat_brain" ? "devil_whisper" : ""))}</select></label>
        ${String(c.voice).startsWith("gemini:") ? "" : `
        <label class="tune">Pitch <b>${tune(c)[0] > 0 ? "+" : ""}${tune(c)[0]}</b><input type="range" min="-40" max="50" step="2" data-path="characters.${i}.voice_pitch" value="${tune(c)[0]}"></label>
        <label class="tune">Speed <b>${tune(c)[1] > 0 ? "+" : ""}${tune(c)[1]}%</b><input type="range" min="-30" max="40" step="2" data-path="characters.${i}.voice_rate" value="${tune(c)[1]}"></label>`}
        ${S.characters.length > 1 ? `<button class="icon" data-act="del-char" data-i="${i}" aria-label="Remove ${esc(c.name)}">✕</button>` : ""}
      </div>
    </div>`).join("");
}
const soundLabel = id => (A.sounds.find(x => x.id === id) || {}).label || "";
const voiceLabel = ln => !ln ? "" : (ln.text || (ln.sound ? "(" + soundLabel(ln.sound) + ")" : ""));
const nameOf = id => (S.characters.find(c => c.id === id) || {}).name || id;
const isNarr = id => (S.characters.find(c => c.id === id) || {}).look === "narrator";   // a voice, never on screen
function ensureScene(sc) {          // every scene has its own list of characters (they stay in frame even without dialogue)
  if (!Array.isArray(sc.cast)) sc.cast = [];
  if (sc.card !== undefined) return sc;
  (sc.lines || []).forEach(l => {
    if (!sc.cast.includes(l.speaker) && !isNarr(l.speaker)) sc.cast.push(l.speaker);
    if (l.actor && !sc.cast.includes(l.actor) && !isNarr(l.actor)) sc.cast.push(l.actor);
  });
  return sc;
}
const castOpts = sc => sc.cast.filter(id => !isNarr(id)).map(id => ({ id, label: nameOf(id) }))
  .concat(S.characters.filter(c => c.look === "narrator").map(c => ({ id: c.id, label: c.name + " (voice-over)" })));
const KADHAI = [{ id: "", label: "Kadhai: no change" }, { id: "fry", label: "Kadhai: oil frying" },
  { id: "fire", label: "Kadhai: catches FIRE" }, { id: "cover", label: "Kadhai: covered with a thali" },
  { id: "gas_off", label: "Gas turned off" }];
const brollOpts = () => [{ id: "", label: "No cut-away" }]
  .concat((A.explainers || []).map(x => ({ id: x.id, label: x.label })))
  .concat((A.backgrounds || []).filter(b => !String(b.id).startsWith("flat_")).map(b => ({ id: "pic:" + b.id, label: "Cut to picture: " + b.label })));
const r2 = v => Math.round(v * 100) / 100;
function sceneRange(sc) {           // the part of the audio this scene plays: set by hand, else from its lines
  if (sc.audio_from != null && sc.audio_to != null && sc.audio_to > sc.audio_from) return [sc.audio_from, sc.audio_to];
  const t = sc.lines.filter(l => l.start != null && l.end != null && l.end > l.start);
  return t.length ? [Math.min(...t.map(l => l.start)), Math.max(...t.map(l => l.end))] : null;
}
function renderScenes() {
  S.scenes.forEach(ensureScene);
  const prov = A.script_providers;
  $("#provider").innerHTML = prov.map(p => `<option value="${p.id}"${p.id === S.provider ? " selected" : ""}>${esc(p.label)}${p.ready ? "" : " (needs setup)"}</option>`).join("");
  const cur = prov.find(p => p.id === S.provider);
  $("#provider-hint").textContent = cur && !cur.ready ? cur.hint : "";
  if (!S.scenes.length) {
    $("#scenes").innerHTML = `<div class="empty">No scenes yet. Press Write script for a first draft, or add a scene and type the dialogue yourself.</div>`;
    return;
  }
  const file = S.audio.mode === "file";
  $("#scenes").innerHTML = S.scenes.map((sc, si) => {
    if (sc.card !== undefined) return `
    <div class="scene card-scene">
      <div class="scene-head"><h2>${sc.card_style === "black" ? "Black screen" : "Text card"} ${si + 1}</h2>
        <button class="icon" data-act="del-scene" data-si="${si}" aria-label="Delete card ${si + 1}">✕</button></div>
      <div class="line-sub four">
        <input aria-label="Card text" lang="hi" placeholder="${sc.card_style === "black" ? "(no text)" : "20 मिनट बाद..."}" data-path="scenes.${si}.card" value="${esc(sc.card)}">
        <select aria-label="Card style" data-path="scenes.${si}.card_style">${opts([{ id: "dark", label: "Dark with clock" }, { id: "black", label: "Black screen" }, { id: "bright", label: "Bright comic" }], sc.card_style || "dark")}</select>
        <select aria-label="Card sound" data-path="scenes.${si}.card_sound"><option value="">No sound</option>${opts(A.sounds, sc.card_sound || "")}</select>
        <input type="number" min="0" step="0.5" aria-label="Seconds (empty: automatic)" placeholder="Seconds (auto)" data-path="scenes.${si}.card_seconds" value="${sc.card_seconds ?? ""}">
      </div>
    </div>`;
    const rest = S.characters.filter(c => !sc.cast.includes(c.id)), rng = sceneRange(sc);
    return `
    <div class="scene">
      <div class="scene-head"><h2>Scene ${si + 1}</h2>
        <label>Background<select data-path="scenes.${si}.background">${opts(A.backgrounds, sc.background)}</select></label>
        <label>Lighting<select data-path="scenes.${si}.lighting">${opts([{ id: "day", label: "Normal" }, { id: "dark", label: "Night, lights off" }, { id: "phone", label: "Dark, lit by a phone" }], sc.lighting || "day")}</select></label>
        <label>Music<select data-path="scenes.${si}.music">${opts([{ id: "", label: "Keep playing" }, { id: "none", label: "Silence from here" }].concat((A.music || []).map(m => ({ id: m.id, label: "Change to: " + m.label }))), sc.music || "")}</select></label>
        <label>Seconds<input type="number" min="0" step="0.5" style="width:5.5em" title="Make the scene at least this long (empty: as long as its lines)" data-path="scenes.${si}.seconds" value="${sc.seconds || ""}" placeholder="auto"></label>
        <button class="icon" data-act="del-scene" data-si="${si}" aria-label="Delete scene ${si + 1}">✕</button></div>
      <div class="cast-row"><span class="cast-label">Characters in this scene</span>
        ${sc.cast.map(id => `<span class="chip">${esc(nameOf(id))}<button class="chip-x" data-act="remove-cast" data-si="${si}" data-id="${esc(id)}" aria-label="Take ${esc(nameOf(id))} out of scene ${si + 1}">✕</button></span>`).join("") || `<span class="hint">No one is in this scene.</span>`}
        ${rest.length ? `<select class="add-cast" data-si="${si}" aria-label="Add a character to scene ${si + 1}"><option value="">Add character</option>${rest.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("")}</select>` : ""}
      </div>
      ${file ? `<div class="scene-audio">
        <div class="sa-head"><b>Audio for this scene</b><span class="hint" id="len-${si}">${rng ? "Length " + (rng[1] - rng[0]).toFixed(1) + " seconds" : "Not set yet"}</span></div>
        <div class="sa-row">
          <label>From (seconds)<input type="number" min="0" step="0.05" data-path="scenes.${si}.audio_from" value="${sc.audio_from ?? ""}" placeholder="${rng ? rng[0].toFixed(2) : ""}"></label>
          <label>To (seconds)<input type="number" min="0" step="0.05" data-path="scenes.${si}.audio_to" value="${sc.audio_to ?? ""}" placeholder="${rng ? rng[1].toFixed(2) : ""}"></label>
          <button class="hear" data-act="play-scene" data-si="${si}">▶ Play</button>
          <button class="hear" data-act="fit-scene" data-si="${si}">Fit to lines</button>
        </div></div>` : ""}
      ${sc.lines.map((ln, li) => `
        <div class="line${S.sel.scene === si && S.sel.line === li ? " sel" : ""}" data-si="${si}" data-li="${li}">
          <div class="line-main">
            <select aria-label="Speaker" data-path="scenes.${si}.lines.${li}.speaker">${opts(castOpts(sc), ln.speaker)}</select>
            <input aria-label="Dialogue" lang="hi" placeholder="${file ? "Caption text (optional)" : ""}" data-path="scenes.${si}.lines.${li}.text" value="${esc(ln.text)}">
            <button class="icon" data-act="sample-line" data-si="${si}" data-li="${li}" aria-label="Hear this line">▶</button>
            <button class="icon" data-act="del-line" data-si="${si}" data-li="${li}" aria-label="Delete this line">✕</button>
          </div>
          <div class="line-sub four">
            <select aria-label="Emotion" data-path="scenes.${si}.lines.${li}.emotion">${opts(A.emotions, ln.emotion)}</select>
            <select aria-label="Action" data-path="scenes.${si}.lines.${li}.action">${opts(A.actions, ln.action)}</select>
            <div class="sound-pick">
              <select aria-label="Emotional sound (optional)" data-path="scenes.${si}.lines.${li}.sound"><option value="">No sound</option>${opts(A.sounds, ln.sound || "")}</select>
              <button class="icon" data-act="hear-sound" data-si="${si}" data-li="${li}" aria-label="Hear this sound">▶</button>
            </div>
            <select aria-label="Camera shot (flat cartoon style)" title="Camera shot, used by flat cartoon scenes" data-path="scenes.${si}.lines.${li}.shot">${opts(A.shots || [], ln.shot || "auto")}</select>
          </div>
          <div class="line-sub four extras">
            <input aria-label="Phone notification on screen (optional)" lang="hi" placeholder="Notification pop-up (optional)" data-path="scenes.${si}.lines.${li}.popup" value="${esc(ln.popup || "")}">
            <select aria-label="Sticker" data-path="scenes.${si}.lines.${li}.sticker"><option value="">No sticker</option>${opts((A.stickers || []).map(x => ({ id: x, label: "Sticker: " + x })), ln.sticker || "")}</select>
            <select aria-label="Cartoon effect around the speaker" title="Drawn around the speaker during this line: dizzy stars, !, ?, hearts, rain cloud..." data-path="scenes.${si}.lines.${li}.effect">${opts(A.effects || [{ id: "", label: "Effect: none" }], ln.effect || "")}</select>
            <select aria-label="Room light" data-path="scenes.${si}.lines.${li}.lights">${opts([{ id: "", label: "Light: no change" }, { id: "on", label: "Light switches ON" }, { id: "off", label: "Light switches OFF" }], ln.lights || "")}</select>
          </div>
          <div class="line-sub four extras">
            <select aria-label="Meanwhile, someone else acts" title="While this line is spoken, this character does the action next to it (use it with a narrator)" data-path="scenes.${si}.lines.${li}.actor"><option value="">Meanwhile: nobody else</option>${opts(sc.cast.filter(id => id !== ln.speaker && !isNarr(id)).map(id => ({ id, label: "Meanwhile: " + nameOf(id) })), ln.actor || "")}</select>
            <select aria-label="Their action" data-path="scenes.${si}.lines.${li}.actor_action">${opts(A.actions, ln.actor_action || "idle")}</select>
            <select aria-label="Their emotion" data-path="scenes.${si}.lines.${li}.actor_emotion">${opts(A.emotions, ln.actor_emotion || "neutral")}</select>
            <input type="number" min="0" step="0.5" aria-label="Seconds on screen (for a line with no words)" title="The line lasts at least this long; a line with no words is a silent action moment" placeholder="Seconds (auto)" data-path="scenes.${si}.lines.${li}.hold" value="${ln.hold || ""}">
          </div>
          <div class="line-sub four extras">
            <select aria-label="Prop the speaker holds from this line on" title="Something the speaker holds or has with them from this line on" data-path="scenes.${si}.lines.${li}.prop">${opts([{ id: "", label: "Prop: no change" }, { id: "none", label: "Prop: put it away" }].concat((A.props || []).filter(p => p.id).map(p => ({ id: p.id, label: "Prop: " + p.label }))), ln.prop || "")}</select>
            <select aria-label="Kadhai on the stove (kitchen)" data-path="scenes.${si}.lines.${li}.kadhai">${opts(KADHAI, ln.kadhai || "")}</select>
            <select aria-label="Mystery bag on the floor" title="A bag lying in the scene: it can shake, pop open and let a photo fly out" data-path="scenes.${si}.lines.${li}.bag">${opts(A.bag_states || [{ id: "", label: "Bag: no change" }], ln.bag || "")}</select>
            <select aria-label="Cut-away picture (B-roll)" data-path="scenes.${si}.lines.${li}.broll">${opts(brollOpts(), ln.broll || "")}</select>
            <input aria-label="Big text on screen (optional)" lang="hi" placeholder="Big text on screen (line 1 | line 2)" data-path="scenes.${si}.lines.${li}.overlay" value="${esc(ln.overlay || "")}">
          </div>
          ${file ? `<div class="line-time">
            <label>Spoken from (seconds in the audio)<input type="number" min="0" step="0.05" data-path="scenes.${si}.lines.${li}.start" value="${ln.start ?? ""}"></label>
            <label>to<input type="number" min="0" step="0.05" data-path="scenes.${si}.lines.${li}.end" value="${ln.end ?? ""}"></label>
          </div>` : ""}
        </div>`).join("")}
      <div class="scene-actions"><button class="secondary" data-act="add-line" data-si="${si}">Add line</button></div>
    </div>`;
  }).join("");
}

// ------------------------------------------------------------------ audio
let AUDIO = null, playToken = 0, PEAKS = null;
function stopAudio() { playToken++; if (AUDIO) AUDIO.pause(); if (SAMPLE) SAMPLE.pause(); }
async function playRanges(ranges) {
  if (!S.audio.url) return toast("Upload your audio first.", true);
  if (!ranges.length) return toast("Set the From and To times first.", true);
  stopAudio(); const my = playToken;
  if (!AUDIO) AUDIO = new Audio();
  if (!AUDIO.src.endsWith(S.audio.url)) {
    AUDIO.src = S.audio.url;
    await new Promise(r => { AUDIO.onloadedmetadata = r; AUDIO.onerror = r; AUDIO.load(); });
  }
  for (const [from, to] of ranges) {
    if (my !== playToken) return;
    AUDIO.currentTime = from;
    try { await AUDIO.play(); } catch (e) { return toast("The audio could not be played.", true); }
    await new Promise(res => setTimeout(res, Math.max(200, (to - from) * 1000)));
  }
  if (my === playToken) AUDIO.pause();
}
const COLORS = ["#2D3FD3", "#1FA67A", "#E0A100", "#C0392B", "#8E44AD", "#16A085"];
function drawWave() {
  const c = $("#wave");
  if (!c || !c.clientWidth || S.audio.mode !== "file" || !PEAKS) return;
  const dpr = window.devicePixelRatio || 1, W = c.width = Math.round(c.clientWidth * dpr), H = c.height = Math.round(84 * dpr);
  const g = c.getContext("2d"), n = PEAKS.peaks.length, dur = PEAKS.seconds || 1;
  g.clearRect(0, 0, W, H);
  S.scenes.forEach((sc, i) => {
    const r = sceneRange(sc); if (!r) return;
    g.fillStyle = COLORS[i % COLORS.length] + "33"; g.fillRect(r[0] / dur * W, 0, (r[1] - r[0]) / dur * W, H);
    g.fillStyle = COLORS[i % COLORS.length]; g.font = `${12 * dpr}px sans-serif`; g.fillText(String(i + 1), r[0] / dur * W + 4 * dpr, 14 * dpr);
  });
  g.fillStyle = "#5B6285";
  PEAKS.peaks.forEach((v, i) => { const h = Math.max(1, v * (H - 24 * dpr)); g.fillRect(i / n * W, (H - h) / 2 + 6 * dpr, Math.max(1, W / n - 0.5), h); });
}
async function loadPeaks() {
  if (!S.audio.id) { PEAKS = null; return; }
  if (PEAKS && PEAKS.id === S.audio.id) return drawWave();
  try { const r = await api("/api/audio/peaks", { id: S.audio.id }); PEAKS = { id: S.audio.id, ...r }; drawWave(); } catch (e) { PEAKS = null; }
}
function renderAudio() {
  const a = S.audio, file = a.mode === "file";
  $("#audio-file").hidden = !file; $("#voices-tts").hidden = file; $("#voices-file").hidden = !file;
  $("#audio-info").innerHTML = a.id ? `<div class="fileline"><span>${esc(a.name)}, ${a.seconds} seconds</span><button class="hear" data-act="remove-audio">Remove</button></div><audio controls src="${esc(a.url)}"></audio>` : "";
  const apm = $("#ap-music");
  if (apm && apm.options.length <= 2) (A.music || []).forEach(m => apm.add(new Option(m.label, m.id)));
  const mb = $("#music-builtin");
  if (mb) mb.innerHTML = `<option value="">None</option>` + (A.music || []).map(m => `<option value="${m.id}"${m.id === a.musicBuiltin ? " selected" : ""}>${esc(m.label)}</option>`).join("");
  $("#music-info").innerHTML = a.musicId ? `<div class="fileline"><span>${esc(a.musicName)}</span><button class="hear" data-act="remove-music">Remove</button></div><audio controls src="${esc(a.musicUrl)}"></audio>` : "";
  $("#pause-out").textContent = a.pause; $("#vol-out").textContent = a.musicVolume + "%";
  $("#wave").hidden = !(file && a.id);
  if (file && a.id) loadPeaks();
}
function trimScenesFromLines(pad = 0.2) {   // each scene gets the part of the audio its lines use, with a little room
  const raw = S.scenes.map(sc => {
    const t = sc.lines.filter(l => l.start != null && l.end != null);
    return t.length ? [Math.min(...t.map(l => l.start)), Math.max(...t.map(l => l.end))] : null;
  });
  raw.forEach((r, i) => {
    if (!r) return;
    const prev = raw.slice(0, i).reverse().find(x => x), next = raw.slice(i + 1).find(x => x);
    const before = prev ? Math.max(0, Math.min(pad, (r[0] - prev[1]) / 2)) : Math.min(pad, r[0]);
    const after = next ? Math.max(0, Math.min(pad, (next[0] - r[1]) / 2)) : Math.min(pad * 1.5, Math.max(0, S.audio.seconds - r[1]));
    S.scenes[i].audio_from = r2(r[0] - before); S.scenes[i].audio_to = r2(r[1] + after);
  });
}
async function uploadAudio(file) {
  const r = await fetch("/api/audio/upload", { method: "POST", headers: { "X-Filename": encodeURIComponent(file.name), "Content-Type": "application/octet-stream" }, body: file });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "Upload failed");
  return j;
}

// ------------------------------------------------------------------ preview
let pvTimer, pvSeq = 0;
function previewTimeline() {
  if (S.scenes.length) return { tl: timeline(), scene: S.sel.scene, line: S.sel.line };
  const lines = S.characters.map(c => ({ speaker: c.id, text: "नमस्ते!", emotion: "happy", action: c.id === S.characters[0].id ? "wave" : "talk" }));
  return { tl: { ...timeline(), scenes: [{ background: defaultBg(), lines }] }, scene: 0, line: 0 };
}
function refreshPreview() {
  clearTimeout(pvTimer);
  pvTimer = setTimeout(async () => {
    const seq = ++pvSeq, { tl, scene, line } = previewTimeline();
    try {
      const r = await api("/api/frame", { timeline: tl, scene, line, width: 360 });
      if (seq !== pvSeq) return;
      const url = URL.createObjectURL(await r.blob());
      const img = $("#pv"); img.src = url; img.hidden = false; $("#pv-empty").hidden = true;
      $("#pv-label").textContent = S.scenes.length ? `Scene ${scene + 1}, line ${line + 1}` : "Sample pose";
    } catch (e) { $("#pv").hidden = true; $("#pv-empty").hidden = false; $("#pv-empty").textContent = "Preview unavailable: " + e.message; }
  }, 280);
}

// ------------------------------------------------------------------ actions
async function playSound(ln) {
  const ch = S.characters.find(c => c.id === ln.speaker) || S.characters[0];
  const r = await api("/api/sound", { sound: ln.sound, voice: ch.voice });
  const a = new Audio(URL.createObjectURL(await r.blob()));
  await a.play();
  await new Promise(res => { a.onended = res; a.onerror = res; });
}
async function playSample(text, voice, emotion, ch) {
  const t = ch ? tune(ch) : [0, 0];
  const fx = ch ? (ch.voice_fx ?? (ch.look === "flat_brain" ? "devil_whisper" : "")) : "";
  const r = await api("/api/sample", { text, voice, engine: S.tts, emotion: emotion || "neutral", pitch: t[0], rate: t[1], fx });
  const warn = r.headers.get("X-Warning");
  if (warn) toast(warn, true);
  const url = URL.createObjectURL(await r.blob());
  if (SAMPLE) SAMPLE.pause();
  const a = SAMPLE = new Audio(url);
  await a.play();
  await new Promise(res => { a.onended = res; a.onerror = res; a.onpause = res; });   // done (or stopped)
}
let SAMPLE = null;
async function playLines(list, btn) {        // play lines one after another; pressing again stops
  if (btn && btn.dataset.playing) { stopAudio(); return; }
  stopAudio(); const my = playToken, label = btn?.textContent;
  if (btn) { btn.dataset.playing = "1"; btn.textContent = "■ Stop"; }
  try {
    for (const [si, li] of list) {
      if (my !== playToken) break;
      const ln = S.scenes[si].lines[li];
      const ch = S.characters.find(c => c.id === ln.speaker) || S.characters[0];
      if (ln.sound) await playSound(ln);
      if (my !== playToken) break;
      if (ln.text.trim()) await playSample(ln.text, ch.voice, ln.emotion, ch);
    }
  } finally { if (btn) { delete btn.dataset.playing; btn.textContent = label; } }
}
function allLines() {
  const out = [];
  S.scenes.forEach((sc, si) => (sc.lines || []).forEach((ln, li) => { if (ln.text.trim() || ln.sound) out.push([si, li]); }));
  return out;
}
const ACTIONS = {
  go: el => showStep(+el.dataset.step),
  example: () => { Object.assign(S, EXAMPLE); save(); renderStory(); toast("Example added. Press Next to continue."); },
  "add-char": () => {
    S.counter++;
    const cast = (A.looks || []).filter(l => l.id !== "narrator");      // the characters in the Cast menu, in turn
    const pick = cast.length ? cast[S.counter % cast.length] : { id: "flat_lalit", label: "Lalit" };
    const name = (pick.label || "").replace(/^Flat: /, "").split(" (")[0] || "Character " + S.counter;
    S.characters.push({ id: "c" + S.counter, name, look: pick.id,
                        voice: pick.female ? "hi-IN-SwaraNeural" : A.default_voice });
    save(); renderCast();
  },
  "del-char": el => {
    const ch = S.characters[+el.dataset.i], n = S.scenes.reduce((a, sc) => a + sc.lines.filter(l => l.speaker === ch.id).length, 0);
    if (n && !confirm(`Remove ${ch.name}? Their ${n} line(s) in your scenes will be deleted too.`)) return;
    S.characters.splice(+el.dataset.i, 1);
    S.scenes.forEach(sc => { sc.cast = (sc.cast || []).filter(id => id !== ch.id); sc.lines = sc.lines.filter(l => l.speaker !== ch.id); });
    save(); renderCast(); renderScenes(); refreshPreview();
  },
  "sample-char": el => { const c = S.characters[+el.dataset.i]; return playSample("नमस्ते, मेरा नाम " + c.name + " है।", c.voice, "happy", c); },
  "add-card": () => { S.scenes.push({ card: "20 मिनट बाद...", card_style: "dark", card_sound: "tick", cast: [], lines: [] }); save(); renderScenes(); },
  "add-black": () => { S.scenes.push({ card: "", card_style: "black", card_sound: "laugh_track", cast: [], lines: [] }); save(); renderScenes(); },
  "import-script": async el => {
    const text = $("#import-text").value.trim();
    if (!text) return toast("Paste your script first.", true);
    if (S.scenes.length && !confirm("Replace your current characters and scenes with the imported script?")) return;
    el.disabled = true; const label = el.textContent; el.textContent = "Reading your script...";
    try {
      const r = await api("/api/import_script", { text, provider: S.provider });
      S.characters = r.characters;                   // first, so the scenes know who is the narrator
      Object.assign(S, { title: r.title || S.title, hook: r.hook || "", scenario: text.slice(0, 500),
                         characters: r.characters, scenes: r.scenes.map(ensureScene), sel: { scene: 0, line: 0 } });
      S.audio.musicBuiltin = r.music || S.audio.musicBuiltin;
      if (r.language) S.language = r.language;
      S.counter = r.characters.length + 1;
      save(); init(true); showStep(3);
      const how = r.exact ? "read exactly from the Shorts Studio format" : "read by Gemini";
      toast(`Imported (${how}): ${r.characters.length} characters, ${r.scenes.length} scenes.` +
            (r.warnings && r.warnings.length ? ` ${r.warnings.length} note(s): ${r.warnings.slice(0, 3).join(" ")}` : " Check them, then make the video."),
            !!(r.warnings && r.warnings.length));
    } catch (e) { toast(e.message, true); } finally { el.disabled = false; el.textContent = label; }
  },
  "get-format": async () => {
    const q = new URLSearchParams({ idea: $("#fmt-idea").value, language: $("#fmt-lang").value, seconds: $("#fmt-secs").value || 45 });
    const r = await fetch("/api/script_format?" + q).then(x => x.json());
    $("#fmt-text").value = r.text; $("#fmt-out").hidden = false;
    toast("Format ready: copy it into ChatGPT / Gemini / any AI app, then paste its answer in the box below.");
  },
  "get-stick-format": async () => {
    const q = new URLSearchParams({ kind: "stickman", idea: $("#stick-idea").value, seconds: $("#stick-secs").value || 30 });
    const r = await fetch("/api/script_format?" + q).then(x => x.json());
    $("#fmt-text").value = r.text; $("#fmt-out").hidden = false;
    $("#fmt-text").scrollIntoView({ behavior: "smooth", block: "center" });
    toast("Stickman format ready: copy it into ChatGPT / Gemini / any AI app, then paste its answer in the box below and press Import.");
  },
  "export-format": async () => {
    if (!S.scenes.length) return toast("Your project has no scenes yet.", true);
    const r = await api("/api/export_format", { timeline: timeline() });
    $("#fmt-text").value = r.text; $("#fmt-out").hidden = false;
  },
  "copy-format": async () => {
    const t = $("#fmt-text");
    try { await navigator.clipboard.writeText(t.value); } catch (e) { t.select(); document.execCommand("copy"); }
    toast("Copied.");
  },
  "save-format": () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([$("#fmt-text").value], { type: "text/plain;charset=utf-8" }));
    a.download = "shorts-studio-script-format.txt"; a.click();
  },
  "cancel-job": async el => {
    const box = el.dataset.box, id = RUNNING[box];
    if (!id) { stopWatching(box); return; }
    el.disabled = true;
    try {
      const r = await fetch("/api/jobs/" + id + "/cancel", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (r.ok) { toast("Stopping..."); setTimeout(() => { if (RUNNING[box] === id) { stopWatching(box); toast("Stopped."); } }, 15000); return; }
    } catch (e) { /* the app is not answering */ }
    stopWatching(box);                                  // the job is gone already: just close the progress bar
    toast("That video was already stopped (the app was closed or restarted). You can make it again.");
  },
  "refresh-bgs": () => refreshBackgrounds(true),
  "open-bg-folder": async () => {
    const r = await api("/api/open_backgrounds", {});
    if (!r.opened) toast("Put your pictures in: " + r.folder + " (in Codespaces: drag them into that folder in the file list).");
  },
  "add-scene": () => {
    const last = S.scenes[S.scenes.length - 1], cast = last?.cast?.length ? [...last.cast] : S.characters.map(c => c.id);
    S.scenes.push({ background: last?.background || defaultBg(), cast, lines: [{ speaker: cast[0], text: "", emotion: "neutral", action: "talk" }] });
    S.sel = { scene: S.scenes.length - 1, line: 0 }; save(); renderScenes();
  },
  "del-scene": el => { S.scenes.splice(+el.dataset.si, 1); S.sel = { scene: 0, line: 0 }; save(); renderScenes(); refreshPreview(); },
  "add-line": el => {
    const sc = ensureScene(S.scenes[+el.dataset.si]), prev = sc.lines[sc.lines.length - 1];
    if (!sc.cast.length) return toast("Add a character to this scene first.", true);
    const other = sc.cast.find(id => id !== prev?.speaker) || sc.cast[0];
    sc.lines.push({ speaker: other, text: "", emotion: "neutral", action: "talk" });
    S.sel = { scene: +el.dataset.si, line: sc.lines.length - 1 }; save(); renderScenes();
  },
  "del-line": el => {
    const sc = S.scenes[+el.dataset.si]; sc.lines.splice(+el.dataset.li, 1);   // the characters stay in the scene
    S.sel = { scene: 0, line: 0 }; save(); renderScenes(); refreshPreview();
  },
  "remove-cast": el => {
    const sc = ensureScene(S.scenes[+el.dataset.si]), id = el.dataset.id, n = sc.lines.filter(l => l.speaker === id).length;
    if (n && !confirm(`Take ${nameOf(id)} out of this scene? Their ${n} line(s) in this scene will be deleted too.`)) return;
    sc.cast = sc.cast.filter(x => x !== id); sc.lines = sc.lines.filter(l => l.speaker !== id);
    S.sel = { scene: 0, line: 0 }; save(); renderScenes(); renderAudio(); refreshPreview();
  },
  "play-scene": el => { const r = sceneRange(S.scenes[+el.dataset.si]); return playRanges(r ? [r] : []); },
  "play-all": () => playRanges(S.scenes.map(sceneRange).filter(Boolean)),
  "stop-audio": () => stopAudio(),
  "fit-scene": el => {
    const sc = S.scenes[+el.dataset.si], t = sc.lines.filter(l => l.start != null && l.end != null);
    if (!t.length) return toast("This scene's lines have no times yet. Use Match my lines to the audio, or type the times.", true);
    sc.audio_from = r2(Math.max(0, Math.min(...t.map(l => l.start)) - 0.2)); sc.audio_to = r2(Math.max(...t.map(l => l.end)) + 0.2);
    save(); renderScenes(); drawWave();
  },
  "remove-audio": () => { Object.assign(S.audio, { id: "", name: "", seconds: 0, url: "" }); save(); renderAudio(); },
  "remove-music": () => { Object.assign(S.audio, { musicId: "", musicName: "", musicUrl: "" }); save(); renderAudio(); },
  "match-audio": async el => {
    if (!S.audio.id) return toast("Upload your audio file first.", true);
    const spoken = [];                               // reaction lines (a sound, no words) do not use up a spoken part
    S.scenes.forEach(sc => sc.lines.forEach(l => { if (!(l.sound && !l.text.trim())) spoken.push(l); }));
    const n = spoken.length;
    if (!n) return toast("Add your scenes and lines first, then match them to the audio.", true);
    el.disabled = true;
    try {
      const r = await api("/api/audio/match", { id: S.audio.id, lines: n, pause: S.audio.pause });
      spoken.forEach((l, k) => { l.start = r.times[k].start; l.end = r.times[k].end; });
      trimScenesFromLines();
      save(); renderAudio(); renderScenes();
      toast(r.note || `Matched your ${n} lines to the audio and trimmed each scene.`, !!r.note);
    } finally { el.disabled = false; }
  },
  "caption-audio": async el => {
    if (!S.audio.id) return toast("Upload your audio file first.", true);
    el.disabled = true; const label = el.textContent; el.textContent = "Listening...";
    try {
      let spoken = [];
      S.scenes.forEach(sc => sc.lines.forEach(l => { if (!(l.sound && !l.text.trim())) spoken.push(l); }));
      if (!spoken.length) {                          // no lines yet: one line per speech part, speakers take turns
        const seg = (await api("/api/audio/segments", { id: S.audio.id, pause: S.audio.pause })).segments;
        if (!seg.length) return toast("No speech was found in your audio.", true);
        if (!S.scenes.length) S.scenes.push(ensureScene({ background: A.backgrounds[0].id, cast: S.characters.map(c => c.id), lines: [] }));
        const sc = ensureScene(S.scenes[0]);
        if (!sc.cast.length) sc.cast = S.characters.map(c => c.id);
        seg.forEach((g, k) => sc.lines.push({ speaker: sc.cast[k % sc.cast.length], text: "", emotion: "neutral", action: "talk",
                                              sound: "", shot: "auto", start: g[0], end: g[1] }));
        spoken = sc.lines;
        trimScenesFromLines();
      } else if (spoken.some(l => l.start == null || l.end == null)) {   // match the lines to the audio first
        const r = await api("/api/audio/match", { id: S.audio.id, lines: spoken.length, pause: S.audio.pause });
        spoken.forEach((l, k) => { l.start = r.times[k].start; l.end = r.times[k].end; });
        trimScenesFromLines();
      }
      const todo = spoken.filter(l => !l.text.trim());
      if (!todo.length) { save(); renderAudio(); renderScenes(); return toast("Every line already has text. Clear a line's text to write it again from the audio."); }
      const r = await api("/api/audio/transcribe", { id: S.audio.id, ranges: todo.map(l => [l.start, l.end]), language: S.language });
      todo.forEach((l, k) => { if (r.texts[k]) l.text = r.texts[k]; });
      save(); renderAudio(); renderScenes(); refreshPreview();
      toast(r.warning || `Wrote captions for ${todo.filter((l, k) => r.texts[k]).length} lines from your audio. Check them and fix any word.`, !!r.warning);
    } catch (err) { toast(err.message, true); }
    finally { el.disabled = false; el.textContent = label; }
  },
  "hear-sound": el => {
    const ln = S.scenes[+el.dataset.si].lines[+el.dataset.li];
    if (!ln.sound) return toast("Choose a sound for this line first.", true);
    return playSound(ln);
  },
  "sample-line": async el => {
    const ln = S.scenes[+el.dataset.si].lines[+el.dataset.li];
    const ch = S.characters.find(c => c.id === ln.speaker) || S.characters[0];
    if (S.audio.mode === "file") {
      if (ln.start == null || ln.end == null) {
        if (ln.sound) return playSound(ln);
        return toast("Set the From and To times of this line first.", true);
      }
      return playRanges([[ln.start, ln.end]]);
    }
    if (!ln.text.trim()) { if (ln.sound) return playSound(ln); return toast("Type the dialogue or choose a sound first.", true); }
    if (ln.sound) await playSound(ln);                      // the sound comes first, then the words
    return playSample(ln.text, ch.voice, ln.emotion, ch);
  },
  draft: async el => {
    el.disabled = true; el.textContent = "Writing...";
    try {
      const r = await api("/api/script", { scenario: S.scenario, characters: S.characters, language: S.language, seconds: +S.seconds, provider: S.provider });
      S.scenes = r.scenes.map(ensureScene); if (!S.title && r.title) S.title = r.title;
      if (!S.hook && r.hook) S.hook = r.hook;
      S.sel = { scene: 0, line: 0 }; save(); renderScenes(); renderStory(); refreshPreview();
      toast("Draft ready. Edit anything you like.");
    } finally { el.disabled = false; el.textContent = "Write script"; }
  },
  "voice-row": el => playLines([[+el.dataset.si, +el.dataset.li]]),
  "play-voices": el => {
    const list = allLines();
    if (!list.length) return toast("There are no lines to play yet. Add dialogue in the Scenes step.", true);
    return playLines(list, el);
  },
  voices: async el => {
    el.disabled = true; el.textContent = "Generating...";
    try {
      const r = await api("/api/voices", { timeline: timeline() });
      const warn = r.warnings.map(w => `<div class="banner">${esc(w)}</div>`).join("");
      $("#voice-out").innerHTML = warn + `<table><tr><th></th><th>Scene</th><th>Line</th><th>Length</th></tr>` +
        r.rows.map(x => `<tr><td><button class="icon" data-act="voice-row" data-si="${x.scene}" data-li="${x.line}" aria-label="Play this line">▶</button></td><td>${x.scene + 1}</td><td>${esc(voiceLabel(S.scenes[x.scene]?.lines[x.line]))}</td><td>${x.seconds} s${x.silent ? " (silent)" : ""}</td></tr>`).join("") +
        `</table><p class="hint">Total speaking time: ${r.total} seconds.</p>`;
    } finally { el.disabled = false; el.textContent = "Generate voices"; }
  },
  render: async el => {
    el.disabled = true; $("#result").innerHTML = ""; $("#progress").hidden = false;
    $("#bar-fill").style.width = "0%"; $("#stage").textContent = "Starting";
    try {
      const { job } = await api("/api/render", { timeline: timeline(), quality: $("#quality").value });
      await pollJob(job);
    } catch (e) {                                    // it could not start: do not leave the progress bar up
      stopWatching("#progress");
      throw e;
    } finally { el.disabled = false; }
  },
  autopilot: async el => {
    const idea = (S.scenario || "").trim();
    if (!idea) return toast("Write your idea in the Scenario box first.", true);
    el.disabled = true;
    try {
      const { job } = await api("/api/autopilot", { idea, characters: S.characters, options: apOptions() });
      const r = await watchJob(job, "#ap-progress", "#ap-bar", "#ap-stage");
      if (!r) return;
      $("#ap-result").innerHTML = (r.warnings || []).map(w => `<div class="banner">${esc(w)}</div>`).join("") + resultCard(r) +
        `<div class="actions" style="justify-content:flex-start"><button class="secondary" data-act="open-auto">Open it as a project to edit</button></div>`;
      LAST_AUTO = r.timeline; loadVideos();
    } catch (e) { toast(e.message, true); } finally { el.disabled = false; }
  },
  undo: () => undoRedo(-1),
  redo: () => undoRedo(1),
  "new-episode": async () => {                    // series: same cast and style, a fresh story
    let name = S.series;
    if (!name) { name = prompt("Series name (for example: Dada ji aur Golu)", S.title || ""); if (!name) return; }
    const ep = (S.episode || 1);
    if (S.scenes.length) await api("/api/projects", { name: `${name} ep${ep}`, data: S });
    const keep = { characters: S.characters, language: S.language, seconds: S.seconds, tts: S.tts, look3d: S.look3d,
                   captions: S.captions, effects: S.effects, provider: S.provider, counter: S.counter };
    const music = S.audio.musicBuiltin, vol = S.audio.musicVolume;
    S = { ...fresh(), ...keep, series: name, episode: ep + 1 };
    Object.assign(S.audio, { musicBuiltin: music, musicVolume: vol });
    save(); init(true); showStep(1); loadProjects();
    toast(`Episode ${ep} saved as a project. Episode ${ep + 1}: same cast and style, write the new story.`);
  },
  "open-auto": () => {
    if (!LAST_AUTO) return;
    const t = LAST_AUTO, au = t.audio || {};
    Object.assign(S, { title: t.title, hook: t.hook || "", scenes: t.scenes.map(ensureScene), captions: t.captions, effects: t.effects });
    Object.assign(S.audio, { mode: "tts", musicBuiltin: au.music_builtin || "" });
    S.sel = { scene: 0, line: 0 }; save(); init(true); showStep(3); toast("Opened. Change anything, then make the video again.");
  },
  batch: async el => {
    const ideas = $("#batch-ideas").value.split("\n").map(x => x.trim()).filter(Boolean);
    if (!ideas.length) return toast("Write some ideas, one per line.", true);
    el.disabled = true;
    try {
      const { job } = await api("/api/batch", { ideas, characters: S.characters, options: apOptions() });
      const r = await watchJob(job, "#ap-progress", "#ap-bar", "#ap-stage");
      if (!r) return;
      $("#ap-result").innerHTML = `<p><b>${r.videos.length} videos made.</b></p>` +
        r.failed.map(f => `<div class="banner">${esc(f.idea)}: ${esc(f.error)}</div>`).join("") +
        r.videos.map(v => `<details><summary>${esc(v.idea)}</summary>${resultCard(v)}</details>`).join("");
      loadVideos();
    } catch (e) { toast(e.message, true); } finally { el.disabled = false; }
  },
  copy: async el => { await navigator.clipboard.writeText(el.closest(".share").querySelector(".share-text").textContent); toast("Copied."); },
  "save-project": async () => {
    const name = prompt("Project name", S.title || ""); if (!name) return;
    await api("/api/projects", { name, data: S }); toast("Project saved."); loadProjects();
  },
};
const RUNNING = {};                                // progress box -> the job it shows (for Cancel)
const LOST_MSG = "The app stopped while making this video (it was closed or restarted), so the video was not " +
  "finished. Start the app again if needed, then press Make video again.";
async function jobStatus(id, misses) {             // the job, or {status: "lost"} when the app is gone / restarted
  try {
    const r = await fetch("/api/jobs/" + id);
    if (r.status === 404) return { status: "lost" };   // the app restarted: it no longer knows this job
    const j = await r.json();
    misses.n = 0;
    return j;
  } catch (e) {                                     // the app is not answering: wait a little, it may come back
    misses.n += 1;
    return misses.n >= 12 ? { status: "lost" } : { status: "running", stage: "Waiting for the app to answer..." };
  }
}
function stopWatching(box) {                       // hide a progress box and forget its job
  const el = $(box); if (el) el.hidden = true;
  delete RUNNING[box];
}
function pollJob(id) {
  RUNNING["#progress"] = id;
  $("#progress .cancel-btn").disabled = false;
  return new Promise((resolve, reject) => {
    const misses = { n: 0 };
    const tick = async () => {
      try {
        if (RUNNING["#progress"] !== id) return resolve();          // cancelled from the page
        const j = await jobStatus(id, misses);
        if (j.progress !== undefined) $("#bar-fill").style.width = Math.round((j.progress || 0) * 100) + "%";
        $("#stage").textContent = j.stage || "";
        if (j.status === "running") return setTimeout(tick, 700);
        stopWatching("#progress");
        if (j.status === "lost") { toast(LOST_MSG, true); return resolve(); }
        if (j.status === "cancelled") { toast("Stopped. No video was saved."); return resolve(); }
        if (j.status === "error") { toast(j.error, true); return resolve(); }
        const r = j.result;
        $("#result").innerHTML = (r.warnings || []).map(w => `<div class="banner">${esc(w)}</div>`).join("") + resultCard(r) +
          `<p class="hint">${r.seconds} seconds, saved in the output folder as ${esc(r.file)}.</p>`;
        loadVideos();
        resolve();
      } catch (e) { reject(e); }
    };
    tick();
  });
}
let LAST_AUTO = null;
function apOptions() {
  return { language: S.language, seconds: +S.seconds || 30, quality: $("#ap-quality").value, music: $("#ap-music").value,
           tts: S.tts, captions: S.captions !== false, effects: S.effects !== false, look3d: S.look3d !== false,
           provider: S.provider === "basic" ? "basic" : undefined };
}
function watchJob(id, box, bar, stage) {          // progress bar for a background job; resolves with its result
  $(box).hidden = false; $(bar).style.width = "0%";
  RUNNING[box] = id;
  const cb = $(box + " .cancel-btn"); if (cb) cb.disabled = false;
  return new Promise((resolve, reject) => {
    const misses = { n: 0 };
    const tick = async () => {
      try {
        if (RUNNING[box] !== id) return resolve(null);              // cancelled from the page
        const j = await jobStatus(id, misses);
        if (j.progress !== undefined) $(bar).style.width = Math.round((j.progress || 0) * 100) + "%";
        $(stage).textContent = j.stage || "";
        if (j.status === "running") return setTimeout(tick, 800);
        stopWatching(box);
        if (j.status === "lost") { toast(LOST_MSG, true); return resolve(null); }
        if (j.status === "cancelled") { toast("Stopped. Videos finished before you pressed Cancel are kept."); return resolve(null); }
        if (j.status === "error") { toast(j.error, true); return resolve(null); }
        resolve(j.result);
      } catch (e) { reject(e); }
    };
    tick();
  });
}
function ytText(r) {
  if (r.youtube) return `${r.youtube.title}\n\n${r.youtube.description}\n\n${r.youtube.hashtags.join(" ")}`;
  if (r.youtube_text) return r.youtube_text.replace(/^TITLE\n|DESCRIPTION\n/g, "");
  return `${(r.timeline && r.timeline.title) || S.title || "My short"} #shorts #hindi`;
}
function resultCard(r) {                          // a video with its download links, thumbnails and YouTube text
  const f = encodeURIComponent, link = (n, label) => n ? `<a class="secondary" href="/download/${f(n)}">${label}</a>` : "";
  return `<div class="video-card">
    <video controls playsinline preload="metadata" src="/video/${f(r.file)}"></video>
    <div class="kit">
      <div class="actions" style="justify-content:flex-start;flex-wrap:wrap">
        <a class="primary" style="text-decoration:none;display:inline-block" href="/download/${f(r.file)}">Download MP4</a>
        ${link(r.srt, "Subtitles (SRT)")} ${link(r.thumb, "Thumbnail 9:16")} ${link(r.thumb_wide, "Thumbnail 16:9")}
      </div>
      ${r.thumb ? `<div class="thumbs"><img src="/video/${f(r.thumb)}" alt="Thumbnail for Shorts"><img src="/video/${f(r.thumb_wide)}" alt="Wide thumbnail"></div>` : ""}
      <div class="share"><p class="share-text">${esc(ytText(r))}</p><button class="secondary" data-act="copy">Copy title, description and hashtags</button></div>
      ${r.thumb ? "" : `<p class="hint">Thumbnails, subtitles and YouTube text are made with every Full quality video.</p>`}
    </div></div>`;
}
async function loadVideos() {
  const box = $("#videos"); if (!box) return;
  try {
    const { videos } = await api("/api/videos");
    box.innerHTML = videos.length ? videos.map(v => `<details><summary>${esc(v.file)} <span class="hint">${v.size_mb} MB</span></summary>${resultCard(v)}</details>`).join("")
                                  : `<p class="hint">No videos yet.</p>`;
  } catch { /* the list is optional */ }
}
async function loadProjects() {
  const { projects } = await api("/api/projects");
  $("#proj-list").innerHTML = `<option value="">Open a saved project</option>` + projects.map(p => `<option>${esc(p)}</option>`).join("");
}

// ------------------------------------------------------------------ wiring
document.addEventListener("click", async e => {
  const el = e.target.closest("[data-act]"); if (!el) return;
  try { await ACTIONS[el.dataset.act]?.(el); } catch (err) { toast(err.message, true); }
});
document.addEventListener("input", e => {
  const t = e.target, p = t.dataset?.path; if (!p) return;
  let v = t.value;
  if (t.type === "checkbox") v = t.checked;
  else if (t.type === "number") v = v === "" ? null : parseFloat(v);
  else if (t.type === "range") v = parseFloat(v);
  setPath(p, v);
  if (p === "seconds") S.seconds = +t.value;
  save();
  if (p.startsWith("scenes") || p.startsWith("characters")) refreshPreview();
  if (p === "provider") renderScenes();
  const lm = p.match(/^characters\.(\d+)\.look$/);
  if (lm) {                                  // a woman's look: switch the default male voice to the female one (and back)
    const c = S.characters[+lm[1]], fem = !!(A.looks.find(l => l.id === t.value) || {}).female;
    if (fem && c.voice === "hi-IN-MadhurNeural") c.voice = "hi-IN-SwaraNeural";
    else if (!fem && c.voice === "hi-IN-SwaraNeural") c.voice = "hi-IN-MadhurNeural";
    delete c.voice_pitch; delete c.voice_rate;   // the new look's own voice tuning
    save(); renderCast();
  }
  if (p === "audio.mode") { renderAudio(); renderScenes(); }
  const sm = p.match(/^scenes\.(\d+)\.lines\.(\d+)\.sound$/);
  if (sm && t.value) {                       // suggest a matching face; a reaction should not make talking gestures
    const ln = S.scenes[+sm[1]].lines[+sm[2]];
    if (ln.emotion === "neutral") ln.emotion = (A.sound_emotions || {})[t.value] || ln.emotion;
    if (!ln.text.trim() && ln.action === "talk") ln.action = "idle";
    save(); renderScenes(); refreshPreview();
  }
  if (/audio_(from|to)$|\.(start|end)$/.test(p)) {
    drawWave();
    const m = p.match(/^scenes\.(\d+)\./), el = m && $("#len-" + m[1]);
    if (el) { const r = sceneRange(S.scenes[+m[1]]); el.textContent = r ? "Length " + (r[1] - r[0]).toFixed(1) + " seconds" : "Not set yet"; }
  }
  if (p === "audio.pause" || p === "audio.musicVolume") { $("#pause-out").textContent = S.audio.pause; $("#vol-out").textContent = S.audio.musicVolume + "%"; }
});
document.addEventListener("focusin", e => {
  const row = e.target.closest(".line"); if (!row) return;
  const si = +row.dataset.si, li = +row.dataset.li;
  if (S.sel.scene === si && S.sel.line === li) return;
  S.sel = { scene: si, line: li };
  document.querySelectorAll(".line.sel").forEach(x => x.classList.remove("sel"));
  row.classList.add("sel"); refreshPreview();
});
$("#proj-list").addEventListener("change", async e => {
  if (!e.target.value) return;
  try { S = await api("/api/projects/" + encodeURIComponent(e.target.value)); save(); init(true); toast("Project opened."); }
  catch (err) { toast(err.message, true); }
});

document.addEventListener("change", async e => {
  const t = e.target;
  if (t.classList?.contains("add-cast")) {
    if (!t.value) return;
    const sc = ensureScene(S.scenes[+t.dataset.si]);
    sc.cast.push(t.value); save(); renderScenes(); refreshPreview();
    return;
  }
  if (t.id !== "audio-input" && t.id !== "music-input") return;
  const f = t.files[0]; if (!f) return;
  const music = t.id === "music-input";
  toast("Uploading " + f.name + "...");
  try {
    const j = await uploadAudio(f);
    if (music) Object.assign(S.audio, { musicId: j.id, musicName: j.name, musicUrl: j.url });
    else Object.assign(S.audio, { id: j.id, name: j.name, seconds: j.seconds, url: j.url });
    save(); renderAudio(); toast(music ? "Music added." : "Audio added. Now match your lines to it.");
  } catch (err) { toast(err.message, true); }
  t.value = "";
});
window.addEventListener("resize", () => drawWave());
function init(reuse) {
  S.audio = { ...fresh().audio, ...(S.audio || {}) };
  S.scenes.forEach(ensureScene);
  renderBanners(); renderStory(); renderCast(); renderScenes(); renderAudio(); showStep(S.step || 1); loadVideos();
  renderSeries(); if (!reuse) { HIST.list = []; HIST.at = -1; record(); }
}
(async () => {
  try {
    A = await api("/api/assets");
    try { S = { ...fresh(), ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { S = fresh(); }
    if (!S.characters?.length) S.characters = fresh().characters;
    await loadProjects();
    init();
  } catch (e) { toast("Could not start: " + e.message, true); }
})();
