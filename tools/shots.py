"""Renders moments of the game to PNGs at 3x, plus one contact sheet (shots/sheet.png). Headless."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
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
w, bots = World((0, 1), seed=3, god=True), [BotPad(), BotPad()]
g.world, g.mode = w, "play"
marks = {150, 700, 1500, 2600, 3800, 5200}
for f in range(12000):
    for i in (0, 1):
        bots[i].think(w, w.players[i])
    w.step(bots)
    if f in marks or (w.boss and w.boss.state == "fight" and w.boss.t in (200, 900)) or (w.boss and w.boss.dying == 60):
        g.t = f; g.draw(s); keep("play_%05d" % f)
    if w.cleared > 5:
        break
cols = 3
rows = (len(pics) + cols - 1) // cols
sheet = pygame.Surface((cols * 640, rows * 448))
for i, p in enumerate(pics):
    sheet.blit(pygame.transform.scale(p, (640, 448)), ((i % cols) * 640, (i // cols) * 448))
pygame.image.save(sheet, os.path.join(out, "sheet.png"))
print(len(pics), "shots")
