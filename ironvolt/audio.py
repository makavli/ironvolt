"""Synthesized sound: every effect and the music loop are computed at start-up (no audio files).

The music is built in a background thread so the title appears at once. Without an audio device
(tests, a PC with no sound), every call is a silent no-op.
"""

import math
import random
import sys
import threading
from array import array

import pygame

RATE = 22050
_sounds = {}
_music = None
_on = False


def _tone(seconds, f0, f1=None, wave="square", vol=0.5, noise=0.0, decay=6.0, duty=0.5, seed=1):
    rnd = random.Random(seed)
    n = int(RATE * seconds)
    out = array("h")
    phase, f1 = 0.0, f0 if f1 is None else f1
    held = 0.0
    for i in range(n):
        t = i / n
        f = f0 * (f1 / f0) ** t if f0 > 0 else 0
        phase = (phase + f / RATE) % 1.0
        if wave == "square":
            v = 1.0 if phase < duty else -1.0
        elif wave == "tri":
            v = 4 * abs(phase - 0.5) - 1
        else:
            v = math.sin(phase * 2 * math.pi)
        if noise:
            if i % max(1, int(RATE / (f * 2 + 1))) == 0 if f else True:
                held = rnd.uniform(-1, 1)
            v = v * (1 - noise) + held * noise
        env = math.exp(-decay * t) * min(1.0, i / 40)
        out.append(int(max(-1, min(1, v * env * vol)) * 32767))
    return out


def _cat(*parts):
    out = array("h")
    for p in parts:
        out.extend(p)
    return out


def _effects():
    return {
        "shot": _tone(0.09, 1400, 300, duty=0.25, vol=0.30, decay=9),
        "heavy": _tone(0.06, 700, 200, noise=0.6, vol=0.35, decay=10, seed=2),
        "spread": _tone(0.12, 900, 150, noise=0.4, vol=0.35, decay=8, seed=3),
        "rocket": _tone(0.25, 200, 600, noise=0.5, vol=0.35, decay=4, seed=4),
        "boom": _tone(0.55, 120, 30, noise=0.9, vol=0.7, decay=5, seed=5),
        "big_boom": _tone(1.2, 90, 20, noise=0.95, vol=0.8, decay=3, seed=6),
        "hit": _tone(0.05, 300, 120, noise=0.7, vol=0.35, decay=12, seed=7),
        "jump": _tone(0.10, 220, 520, duty=0.5, vol=0.18, decay=6),
        "land": _tone(0.05, 160, 60, noise=0.8, vol=0.18, decay=14, seed=8),
        "pickup": _cat(*(_tone(0.06, f, f, duty=0.25, vol=0.3, decay=2) for f in (660, 880, 1320))),
        "coin": _cat(_tone(0.07, 988, 988, vol=0.3, decay=1), _tone(0.30, 1319, 1319, vol=0.3, decay=4)),
        "start": _cat(*(_tone(0.08, f, f, vol=0.3, decay=1.5) for f in (523, 659, 784, 1047))),
        "hurt": _tone(0.5, 600, 80, duty=0.5, vol=0.4, decay=3),
        "free": _cat(_tone(0.1, 784, 784, wave="tri", vol=0.5, decay=1), _tone(0.2, 1047, 1047, wave="tri", vol=0.5)),
        "alarm": _cat(*(_tone(0.18, f, f, duty=0.5, vol=0.25, decay=0.5) for f in (440, 330, 440, 330))),
        "enemy_shot": _tone(0.08, 500, 250, duty=0.5, vol=0.18, decay=8),
        "clank": _tone(0.04, 2000, 1500, noise=0.5, vol=0.2, decay=15, seed=9),
    }


# --------------------------------------------------------------- music

NOTE = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}


def _freq(name):
    """'A3' -> Hz. '-' is a rest."""
    if name == "-":
        return 0.0
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[pitch] + 12 * (octave - 4) - 9) / 12)


def _track():
    """A driving loop in A minor: bass, a pulse lead and noise drums, 16 bars at 120 bpm."""
    step = 60 / 120 / 4                            # one 16th note
    roots = ["A2", "A2", "F2", "G2", "A2", "A2", "C3", "E2"] * 2
    lead = ("E5 - E5 G5 A5 - G5 E5 D5 - E5 - C5 - D5 - "
            "E5 - E5 G5 A5 - C6 B5 A5 - G5 - E5 - - - "
            "F5 - F5 E5 D5 - C5 D5 E5 - D5 - C5 - A4 - "
            "B4 - C5 - D5 - E5 - G5 - F5 - E5 - D5 - ").split()
    lead = lead * 4
    n_steps = 16 * 16
    length = int(n_steps * step * RATE)
    mix = [0.0] * length
    per = int(step * RATE)

    def add(start, dur, f, vol, wave, duty=0.5):
        if f <= 0:
            return
        n = int(dur * per)
        ph = 0.0
        for i in range(n):
            j = start + i
            if j >= length:
                return
            ph = (ph + f / RATE) % 1.0
            if wave == "tri":
                v = 4 * abs(ph - 0.5) - 1
            else:
                v = 1.0 if ph < duty else -1.0
            env = min(1.0, (n - i) / 300) * (0.75 + 0.25 * math.exp(-i / 900))
            mix[j] += v * vol * env

    rnd = random.Random(42)
    for s in range(n_steps):
        bar, beat = divmod(s, 16)
        root = _freq(roots[bar])
        if s % 2 == 0:                             # octave-hopping bass on the 8ths, room between notes
            add(s * per, 1.6, root * (2 if s % 4 else 1), 0.20, "tri")
        note = lead[s % len(lead)]
        if note != "-":
            add(s * per, 1.8, _freq(note), 0.09, "square", 0.25)
        if beat in (0, 8) or (beat == 10 and bar % 2):  # kick
            for i in range(int(0.12 * RATE)):
                j = s * per + i
                if j < length:
                    mix[j] += math.sin(2 * math.pi * (110 * math.exp(-i / 400)) * i / RATE) * 0.5 * math.exp(-i / 1200)
        if beat in (4, 12):                        # snare
            for i in range(int(0.10 * RATE)):
                j = s * per + i
                if j < length:
                    mix[j] += rnd.uniform(-1, 1) * 0.22 * math.exp(-i / 700)
        if beat % 2 == 0:                          # hats
            for i in range(int(0.02 * RATE)):
                j = s * per + i
                if j < length:
                    mix[j] += rnd.uniform(-1, 1) * 0.035 * math.exp(-i / 120)
    gain = 0.9 / max(1.0, max(map(abs, mix)))      # scaled under full scale, never clipped
    return array("h", (int(v * gain * 30000) for v in mix))


def init():
    """Starts the mixer and the sound build. Returns False with no audio device."""
    global _on
    try:
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.mixer.init(RATE, -16, 1, 512)
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(1)               # channel 0 is the music's alone
    except pygame.error:
        return False
    _on = True
    for name, data in _effects().items():
        _sounds[name] = pygame.mixer.Sound(buffer=data.tobytes())
    _sounds["heavy"].set_volume(0.7)
    if sys.platform == "emscripten":
        _build_music()                             # a browser has no threads; this takes a moment under the loader
    else:
        threading.Thread(target=_build_music, daemon=True).start()
    return True


def _build_music():
    global _music
    _music = pygame.mixer.Sound(buffer=_track().tobytes())


def play(name):
    if _on and name in _sounds:
        _sounds[name].play()


def music(on=True, volume=0.3):
    if not _on or _music is None:
        return
    ch = pygame.mixer.Channel(0)
    if on and not ch.get_busy():
        ch.set_volume(volume)
        ch.play(_music, loops=-1, fade_ms=4000)      # eases in under the start jingle
    elif not on:
        ch.fadeout(600)


def music_ready():
    return _music is not None
