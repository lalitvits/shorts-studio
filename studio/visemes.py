"""Text -> mouth shapes (visemes) for Hindi and English, timed against the voice.

Follows the lip-sync reference for Maa:
  * one mouth shape for each group of sounds (see VISEMES): closed lips for ब प म, F/V for फ व, rounded lips for उ ओ,
    wide open for आ, and so on;
  * the mouth stays open longer for आ and for क ख ग घ ह (those take the shape of the vowel after them);
  * the mouth moves a little BEFORE the sound (LEAD seconds) and rests (closes) in pauses and at commas;
  * short blends between shapes (smoothing).

How the timing works: the line's text becomes a list of mouth shapes with weights (long vowels get more time). The shapes
are laid out over the parts of the audio where the voice is actually sounding (found from the loudness), so they skip
silent gaps. With the app's silent test voices there is no real sound, so the whole line is used and commas become pauses.
Only an approximation: it does not listen to the words, it follows the text and the loudness.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

ENV_HZ = 50
LEAD = 0.10            # the mouth starts moving this many seconds before the sound

VISEMES = ("rest", "aa", "ah", "ee", "eh", "oo", "oh", "ba", "fa", "th", "ta", "la", "ra")

# ---------------------------------------------------------------------------------------------------- Hindi letters
_VOW = {"अ": "ah", "आ": "aa", "इ": "ee", "ई": "ee", "उ": "oo", "ऊ": "oo", "ऋ": "ee",
        "ए": "eh", "ऐ": "eh", "ओ": "oh", "औ": "oh"}
_MATRA = {"ा": "aa", "ि": "ee", "ी": "ee", "ु": "oo", "ू": "oo", "ृ": "ee", "े": "eh", "ै": "eh", "ो": "oh", "ौ": "oh"}
_CONS: dict[str, str | None] = {}


def _reg(chars: str, v: str | None):
    for ch in chars:
        _CONS[ch] = v


_reg("कखगघङहक़ख़ग़", None)                   # throat sounds: they take the shape of the vowel
_reg("चछजझञशषसयज़", "ee")                   # teeth showing
_reg("टठडढणतदन", "ta")
_reg("थध", "th")
_reg("पबभम", "ba")                           # lips pressed together
_reg("फवफ़", "fa")                           # teeth on the lower lip
_reg("ल", "la")
_reg("रड़ढ़", "ra")
_HALANT, _NUKTA, _NASAL = "्", "़", "ंँ"
_SOFT_PAUSE, _HARD_PAUSE = ",;:", ".!?।…"

# how long each shape takes (relative); आ and the throat consonants keep the mouth open longer
_W = {"aa": 1.5, "ah": 0.55, "ee": 1.1, "eh": 1.1, "oo": 1.1, "oh": 1.2, "ba": 0.65, "fa": 0.6, "th": 0.6,
      "ta": 0.55, "la": 0.6, "ra": 0.5}
_THROAT_EXTRA = 0.3

# English letters (a rough guide when the text is in English)
_EN_V = {"a": "aa", "e": "eh", "i": "ee", "o": "oh", "u": "oo", "y": "ee"}
_EN_C = {"b": "ba", "p": "ba", "m": "ba", "f": "fa", "v": "fa", "t": "ta", "d": "ta", "n": "ta", "s": "ee", "z": "ee",
         "l": "la", "r": "ra", "w": "oo", "j": "ee", "c": None, "k": None, "g": None, "h": None, "q": None, "x": None}


@dataclass
class Tok:
    v: str            # mouth shape
    w: float          # relative duration
    pause: bool = False


def tokenize(text: str) -> list[Tok]:
    """The mouth shapes for a line of text, in order. Pauses (commas, full stops) are tokens with pause=True."""
    out: list[Tok] = []
    carry = 0.0
    s = re.sub(r"\s+", " ", text.strip())
    n = len(s)
    i = 0

    def word_end(k: int) -> bool:           # no more letters in this word after position k (only nasal marks)
        while k < n and s[k] in _NASAL + _NUKTA:
            k += 1
        return k >= n or not (s[k].isalpha() or s[k] in _MATRA or s[k] == _HALANT)

    while i < n:
        ch = s[i]
        if ch in _CONS:
            v = _CONS[ch]
            j = i + 1
            if j < n and s[j] == _NUKTA:
                j += 1
            nxt = s[j] if j < n else ""
            if v:
                out.append(Tok(v, _W[v]))
            else:
                carry += _THROAT_EXTRA
            if nxt in _MATRA:
                out.append(Tok(_MATRA[nxt], _W[_MATRA[nxt]] + carry)); carry = 0.0
                i = j + 1
            elif nxt == _HALANT:
                i = j + 1
            else:
                if not word_end(j):                  # inherent short "a" (dropped at the end of a word)
                    out.append(Tok("ah", _W["ah"] + carry)); carry = 0.0
                i = j
            continue
        if ch in _VOW:
            out.append(Tok(_VOW[ch], _W[_VOW[ch]] + carry)); carry = 0.0
        elif ch in _NASAL:
            out.append(Tok("ba", 0.45))
        elif ch in _SOFT_PAUSE or ch in _HARD_PAUSE:
            if not out or not out[-1].pause:
                out.append(Tok("rest", 1.6 if ch in _HARD_PAUSE else 0.9, True))
        elif ch.isascii() and ch.isalpha():
            low = ch.lower()
            two = s[i:i + 2].lower()
            if two in ("th", "sh", "ch"):
                out.append(Tok("th" if two == "th" else "ee", 0.6)); i += 2; continue
            if low in _EN_V:
                out.append(Tok(_EN_V[low], _W[_EN_V[low]] + carry)); carry = 0.0
            elif _EN_C.get(low):
                out.append(Tok(_EN_C[low], _W[_EN_C[low]]))
            else:
                carry += _THROAT_EXTRA
        i += 1
    while out and out[-1].pause:
        out.pop()
    return out


# ---------------------------------------------------------------------------------------------------- timing
REST3 = ("rest", "rest", 0.0, 0.0)


class Track:
    """viseme_at(t): which mouth shape at second t of the line, as (shape, next_shape, blend 0..1, loudness 0..1)."""

    def __init__(self, toks: list[Tok], voiced: list[bool], env: list[float]):
        self.toks, self.voiced, self.env = toks, voiced, env
        n = len(voiced)
        self.cum = [0] * (n + 1)                     # voiced frames before frame i
        for i, v in enumerate(voiced):
            self.cum[i + 1] = self.cum[i] + (1 if v else 0)
        total = self.cum[n]
        wsum = sum(t.w for t in toks) or 1.0
        acc, self.bounds = 0.0, [0.0]
        for t in toks:
            acc += t.w
            self.bounds.append(total * acc / wsum)
        self.run_pos, self.run_left = [0] * n, [0] * n
        for i in range(n):
            self.run_pos[i] = (self.run_pos[i - 1] + 1) if i and voiced[i] and voiced[i - 1] else 0
        for i in range(n - 1, -1, -1):
            self.run_left[i] = (self.run_left[i + 1] + 1) if i < n - 1 and voiced[i] and voiced[i + 1] else 0

    def at(self, t: float):
        i = int((t + LEAD) * ENV_HZ)
        n = len(self.voiced)
        if i < 0 or i >= n or not self.voiced[i]:
            return REST3
        amp = min(1.0, (self.env[i] if i < len(self.env) else 0.6) * 1.3)
        j = self.cum[i] + 0.5
        k = min(len(self.toks) - 1, max(0, bisect.bisect_right(self.bounds, j) - 1))
        cur = self.toks[k].v
        if self.run_pos[i] < 2:                                   # a phrase starts: open from rest
            return ("rest", cur, (self.run_pos[i] + 0.5) / 2, amp)
        if self.run_left[i] < 2:                                  # a phrase ends: close to rest
            return (cur, "rest", 1 - (self.run_left[i] + 0.5) / 2, amp)
        lo, hi = self.bounds[k], self.bounds[k + 1]
        u = (j - lo) / (hi - lo) if hi > lo else 0.0
        if u > 0.65 and k + 1 < len(self.toks):                   # smoothing into the next shape
            return (cur, self.toks[k + 1].v, min(0.9, (u - 0.65) / 0.35), amp)
        return (cur, cur, 0.0, amp)


def _voiced_mask(env: list[float], n: int) -> list[bool]:
    """Frames where the voice sounds; tiny gaps inside a word are filled, tiny blips are dropped."""
    thr = 0.10
    v = [(env[i] > thr) if i < len(env) else False for i in range(n)]
    gap = 5                                                        # 0.1 s
    i = 0
    while i < n:
        if not v[i]:
            j = i
            while j < n and not v[j]:
                j += 1
            if 0 < i and j < n and j - i <= gap:
                for k in range(i, j):
                    v[k] = True
            i = j
        else:
            i += 1
    i = 0
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]:
                j += 1
            if j - i < 3:
                for k in range(i, j):
                    v[k] = False
            i = j
        else:
            i += 1
    return v


def build_track(text: str, env: list[float], duration: float, synthetic: bool = False) -> Track | None:
    """The mouth-shape timeline for one spoken line, or None when the text has no sounds."""
    toks = tokenize(text)
    n = max(1, int(duration * ENV_HZ))
    if not any(not t.pause for t in toks):
        return None
    if synthetic or not env or not any(e > 0.1 for e in env[:n]):
        # no real voice to follow: use the whole line (a little margin at both ends); commas become pauses
        voiced = [0.06 * ENV_HZ <= i < n - 0.06 * ENV_HZ for i in range(n)]
        return Track(toks, voiced, [0.7] * n)
    return Track([t for t in toks if not t.pause], _voiced_mask(env, n), env)
