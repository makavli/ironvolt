"""Sound: every effect is synthesized at start-up; the songs are Ogg loops in songs/ (see CREDITS.md), each loaded when
its mission needs it.

Without an audio device (tests, a PC with no sound), every call is a silent no-op.
"""

import math
import os
import random
import struct
import sys
import tempfile
import time
from array import array

import pygame

from .music import RATE

WEB = sys.platform == "emscripten"
_sounds = {}
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
        env = math.exp(-decay * t) * min(1.0, i / 40, (n - i) / 120)      # no click where it starts or stops
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
        "whistle": _cat(_tone(0.3, 880, 900, duty=0.5, vol=0.18, decay=1), _tone(0.55, 1175, 1150, duty=0.5, vol=0.2, decay=2)),
        "fuse": _tone(0.05, 1600, 1600, duty=0.25, vol=0.16, decay=6),
        "rotor": _tone(0.35, 140, 90, noise=0.7, vol=0.3, decay=3, seed=11),
        "stomp": _tone(0.45, 90, 30, noise=0.85, vol=0.6, decay=4, seed=12),
        "slash": _tone(0.08, 2600, 500, noise=0.55, vol=0.3, decay=10, seed=10),
        "zap": _cat(_tone(0.05, 3000, 900, noise=0.7, vol=0.3, decay=4, seed=13),
                    _tone(0.22, 1800, 400, noise=0.8, vol=0.28, decay=5, seed=14)),
        "vent": _tone(0.5, 2400, 600, noise=0.95, vol=0.3, decay=4, seed=15),
        "drop": _cat(_tone(0.12, 400, 150, duty=0.5, vol=0.25, decay=4), _tone(0.3, 140, 60, noise=0.6, vol=0.3, seed=16)),
        "bell": _cat(*(_tone(0.16, 1568, 1568, wave="tri", vol=0.35, decay=3) for _ in range(3))),
        "squash": _cat(_tone(0.06, 300, 120, noise=0.5, vol=0.3, decay=6, seed=18),
                       _tone(0.25, 520, 90, wave="tri", vol=0.35, decay=3)),
        "lift": _cat(_tone(0.1, 180, 180, duty=0.3, vol=0.22, decay=1),
                     _tone(0.45, 90, 120, noise=0.4, vol=0.25, decay=2, seed=17)),
    }


# --------------------------------------------------------------- music

MIX = 44100                                       # the mixer's rate everywhere; SDL converts for the device
SONGS = os.path.join(os.path.dirname(__file__), "songs")
# per song, so every song plays as loud: rms x volume ~1120 for a mission, ~1210 for a boss
VOLUME = {"title": 0.159, "stage": 0.192, "boss": 0.17, "line": 0.167, "warden": 0.191, "pylon": 0.165, "harrow": 0.172,
          "cradle": 0.172, "graive": 0.174, "sakura": 0.187, "blademaster": 0.172, "harbour": 0.157, "leviathan": 0.182}
_tracks = {}                                      # song -> Sound, only the ones in use: one is ~10 MB decoded
_playing, _ch = None, 0
_volume = {"music": 0.8, "sfx": 0.8}              # the options' sliders, 0..1
_base = {"heavy": 0.7}                            # effects mixed quieter than the rest
_last = {}                                        # effect -> when it last started (ms)


def _sound(mono, path):
    """A Sound from mono samples at RATE, sent through a WAV file so SDL converts it to the mixer's rate: handed over
    raw, 22 kHz samples played at the mixer's rate came out 2-4x too fast and too high. A file, as the browser's
    pygame loads sounds from paths only."""
    out = array("h", bytes(4 * len(mono)))
    out[0::2] = mono
    out[1::2] = mono
    n = 2 * len(out)
    head = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + n, b"WAVE", b"fmt ", 16, 1, 2, RATE, RATE * 4, 4, 16,
                       b"data", n)
    with open(path, "wb") as f:
        f.write(head + out.tobytes())
    return pygame.mixer.Sound(path)


def init():
    """Starts the mixer, makes the effects and loads the songs. Returns False with no audio device."""
    global _on
    try:
        # pygame.init() has already opened the mixer with pygame's defaults: reopen it with ours. The browser fills the
        # sound on the game's own thread between frames, so its buffer must outlast a slow frame or the sound ticks.
        pygame.mixer.quit()
        pygame.mixer.init(MIX, -16, 2, 4096 if WEB else 512, allowedchanges=0)
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(2)               # channels 0 and 1 are the music's: one fades out as the other comes in
    except pygame.error:
        return False
    _on = True
    with tempfile.TemporaryDirectory() as tmp:
        for name, data in _effects().items():
            _sounds[name] = _sound(data, os.path.join(tmp, name + ".wav"))
    set_volume()
    _log("audio: mixer %s, start jingle %.2fs" % (pygame.mixer.get_init(), _sounds["start"].get_length()))
    return True


def _log(text):
    if WEB:                                        # the page's console: tools/web_check.py reads these lines
        import platform
        platform.window.console.log(text)


def _load(names):
    """Keeps exactly these songs decoded, loading the missing ones."""
    for name in [n for n in _tracks if n not in names]:
        del _tracks[name]                          # a channel still fading it out keeps its own reference
    for name in names:
        if name not in _tracks:
            t = time.perf_counter()
            _tracks[name] = pygame.mixer.Sound(os.path.join(SONGS, name + ".ogg"))
            _log("song %s loaded in %.2fs" % (name, time.perf_counter() - t))


def set_volume(music=None, sfx=None):
    """Music and effects levels, 0..1; the song playing follows at once."""
    if music is not None:
        _volume["music"] = music
    if sfx is not None:
        _volume["sfx"] = sfx
    if not _on:
        return
    for name, sound in _sounds.items():
        sound.set_volume(_base.get(name, 1.0) * _volume["sfx"])
    if _playing:
        pygame.mixer.Channel(_ch).set_volume(VOLUME[_playing] * _volume["music"])


def play(name):
    """Starts an effect, unless the same one started under 40 ms ago: five bullets on one wall make one clank, not
    five stacked into a loud click."""
    if _on and name in _sounds:
        now = pygame.time.get_ticks()
        if now - _last.get(name, -1000) >= 40:
            _last[name] = now
            _sounds[name].play()


def music(on=True, track="stage", ready=()):
    """Plays a song on a loop, crossfading from the one before; music(False) fades out. Calling it again
    with the song already playing does nothing. `ready`: songs to load now as well (the mission's boss theme), so
    none loads in the middle of the action; every other song is let go."""
    global _playing, _ch
    if not _on:
        return
    if not on:
        if _playing:
            pygame.mixer.Channel(_ch).fadeout(600)
            _playing = None
        return
    if track == _playing:
        return
    _load({track, *ready})
    fade = 4000                                    # from silence: eases in under the start jingle
    if _playing:
        pygame.mixer.Channel(_ch).fadeout(1200)
        _ch, fade = 1 - _ch, 1200
    ch = pygame.mixer.Channel(_ch)
    ch.set_volume(VOLUME[track] * _volume["music"])
    ch.play(_tracks[track], loops=-1, fade_ms=fade)
    _playing = track
