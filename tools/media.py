"""Renders the README media into docs/media: gameplay GIFs and stills, played by the bot. Headless; needs ffmpeg.

Usage: python tools/media.py
"""
import os, shutil, subprocess, sys, tempfile
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init()
from ironvolt.art import Atlas
from ironvolt.autopilot import BotPad
from ironvolt.game import Game
from ironvolt.world import World

out = os.path.join(os.path.dirname(__file__), "..", "docs", "media")
os.makedirs(out, exist_ok=True)
a, s = Atlas(), pygame.Surface((320, 224))
g = Game(a)


def still(name, scale=3):
    pygame.image.save(pygame.transform.scale(s, (320 * scale, 224 * scale)), os.path.join(out, name + ".png"))


def gif(name, frames, last=None):
    """frames: a folder of PNGs at 1x; the GIF is 2x, 30 fps, one shared palette, nearest-neighbour scaling."""
    src = os.path.join(frames, "%05d.png")
    start = max(0, len(os.listdir(frames)) - last) if last else 0
    vf = "fps=30,scale=640:448:flags=neighbor,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=none"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "60", "-start_number", str(start), "-i", src, "-vf", vf, "-loop", "0",
                    os.path.join(out, name + ".gif")], check=True)


g.t = 30; g.draw(s); still("title")
w, bots = World((0, 1), seed=3, god=True), [BotPad(), BotPad()]
g.world, g.mode = w, "play"
clips = {"run": (560, 980), "boss": None}   # boss clip starts when the fight does
tmp = {k: tempfile.mkdtemp() for k in clips}
n = {k: 0 for k in clips}
boss_from = None
for f in range(12000):
    for i in (0, 1):
        bots[i].think(w, w.players[i])
    w.step(bots)
    if boss_from is None and w.boss and w.boss.state == "fight":
        boss_from = f
        clips["boss"] = (f, 10 ** 9)          # records to the end; only the last 9 s are kept, so it ends on the kill
    for k, span in clips.items():
        if span and span[0] <= f < span[1]:
            g.t = f; g.draw(s)
            pygame.image.save(s, os.path.join(tmp[k], "%05d.png" % n[k])); n[k] += 1
    if f in (700, 2600):
        g.t = f; g.draw(s); still("play_%d" % f)
    if w.cleared > 5:
        break
for k in clips:
    assert n[k] > 60, "clip %s caught only %d frames" % (k, n[k])
    gif(k, tmp[k], last=540 if k == "boss" else None); shutil.rmtree(tmp[k])
for name in sorted(os.listdir(out)):
    print("%-16s %6d KB" % (name, os.path.getsize(os.path.join(out, name)) // 1024))
