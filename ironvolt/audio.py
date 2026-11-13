"""Synthesized sound: every effect and the songs (music.py) are computed at start-up (no audio files).

The songs are built in a background thread (a slice a frame in the browser) so the title appears at
once. Without an audio device (tests, a PC with no sound), every call is a silent no-op.
"""

import math
import random
import sys
import threading
import time
from array import array

import pygame

from . import music as songs
from .music import RATE

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

ORDER = ("title", "stage", "boss")            # built in this order: the first one heard comes first
VOLUME = {"title": 0.11, "stage": 0.16, "boss": 0.13}   # evens out the songs' loudness
_tracks = {}
_building = None
_playing, _ch = None, 0
_volume = {"music": 0.8, "sfx": 0.8}              # the options' sliders, 0..1
_base = {"heavy": 0.7}                            # effects mixed quieter than the rest


def _stereo(mono):
    out = array("h", bytes(4 * len(mono)))
    out[0::2] = mono
    out[1::2] = mono
    return out


def init():
    """Starts the mixer and the sound build. Returns False with no audio device."""
    global _on, _building
    try:
        size = 1024 if sys.platform == "emscripten" else 512    # the browser mixes on the game's own thread
        pygame.mixer.pre_init(RATE, -16, 2, size)
        pygame.mixer.init(RATE, -16, 2, size)
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(2)               # channels 0 and 1 are the music's: one fades out as the other comes in
    except pygame.error:
        return False
    _on = True
    for name, data in _effects().items():
        _sounds[name] = pygame.mixer.Sound(buffer=_stereo(data).tobytes())
    set_volume()
    _building = _build_all()
    if sys.platform != "emscripten":               # a browser has no threads: tick() builds there, a slice a frame
        threading.Thread(target=lambda: all(True for _ in _building), daemon=True).start()
    return True


def _build_all():
    for name in ORDER:
        data = yield from songs.build(name)
        _tracks[name] = pygame.mixer.Sound(buffer=data.tobytes())


def tick(budget=0.002):
    """Browser only: builds the music for a few milliseconds of this frame. The browser's sound runs on this same
    thread: a longer slice made frames late enough to starve it, and it ticked until the build was done."""
    global _building
    if sys.platform != "emscripten" or _building is None:
        return
    end = time.perf_counter() + budget
    try:
        while time.perf_counter() < end:
            next(_building)
    except StopIteration:
        _building = None


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
    if _on and name in _sounds:
        _sounds[name].play()


def music(on=True, track="stage"):
    """Plays a song on a loop, crossfading from the one before; music(False) fades out. Calling it again
    with the song already playing does nothing, and a song still being built starts once it is ready."""
    global _playing, _ch
    if not _on:
        return
    if not on:
        if _playing:
            pygame.mixer.Channel(_ch).fadeout(600)
            _playing = None
        return
    if track == _playing or track not in _tracks:
        return
    fade = 4000                                    # from silence: eases in under the start jingle
    if _playing:
        pygame.mixer.Channel(_ch).fadeout(1200)
        _ch, fade = 1 - _ch, 1200
    ch = pygame.mixer.Channel(_ch)
    ch.set_volume(VOLUME[track] * _volume["music"])
    ch.play(_tracks[track], loops=-1, fade_ms=fade)
    _playing = track


def music_ready(track="stage"):
    return track in _tracks
