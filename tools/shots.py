"""Renders moments of the game to PNGs at 3x, plus one contact sheet (shots/sheet.png). Headless."""
import os, sys, tempfile
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["IRONVOLT_HOME"] = tempfile.mkdtemp()       # the default options and scores, not the player's
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init()
from ironvolt.art import Atlas
from ironvolt.autopilot import BotPad
from ironvolt.game import Game
from ironvolt.world import World

out = os.path.join(os.path.dirname(__file__), "..", "shots")
os.makedirs(out, exist_ok=True)
a, s = Atlas(), pygame.Surface((320, 224))
pics = []

def keep(name):
    big = pygame.transform.scale(s, (960, 672))
    pygame.image.save(big, os.path.join(out, name + ".png"))
    pics.append(s.copy())

g = Game(a)
g.t = 30; g.draw(s); keep("title")
g.mode = "scores"; g.draw(s); keep("scores")
g.mode = "title"
for page, name in (("OPTIONS", "options"), ("CONTROLS", "controls_keys")):
    g.open(page); g.draw(s); keep(name)
g.sub.page = 1; g.draw(s); keep("controls_pad")
g.sub = None
from ironvolt.stage import MISSIONS
for st in range(len(MISSIONS)):
    w, bots = World((0, 1), seed=3, god=True, stage=st), [BotPad(), BotPad()]
    g.world, g.mode = w, "play"
    marks = {150, 700, 1500, 2600, 3800, 5200}
    for f in range(12000):
        for i in (0, 1):
            bots[i].think(w, w.players[i])
        w.step(bots)
        b = w.boss
        moment = (b and b.state == "fight" and b.t in (200, 900)) or (b and b.dying == 60) or (
            b and getattr(b, "mode", "") == "charge" and b.mt == 20)
        if f in marks or moment:
            g.t = f; g.draw(s); keep("play%d_%05d" % (st + 1, f))
        if f == 700 and st == 0:
            g.paused = True; g.draw(s); keep("pause"); g.paused = False
        if w.cleared > 5:
            break
cols = 3
rows = (len(pics) + cols - 1) // cols
sheet = pygame.Surface((cols * 640, rows * 448))
for i, p in enumerate(pics):
    sheet.blit(pygame.transform.scale(p, (640, 448)), ((i % cols) * 640, (i // cols) * 448))
pygame.image.save(sheet, os.path.join(out, "sheet.png"))
print(len(pics), "shots")
