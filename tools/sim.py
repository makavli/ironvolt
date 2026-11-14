"""Plays the stage with the autopilot, headless, and prints what happened. Usage: python tools/sim.py [god] [MISSION] [seed=N]"""
import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init()
from ironvolt.art import Atlas
from ironvolt.autopilot import BotPad
from ironvolt.world import World

god = "god" in sys.argv
mission = next((int(a) for a in sys.argv[1:] if a.isdigit()), 1)
from ironvolt.stage import MISSIONS  # noqa: E402
mission = min(max(1, mission), len(MISSIONS))
a, s = Atlas(), pygame.Surface((320, 224))
seed = next((int(a[5:]) for a in sys.argv[1:] if a.startswith("seed=")), 1)
w, bots = World((0,), seed=seed, god=god, stage=mission - 1), [BotPad(), BotPad()]
t = time.time()
deaths = 0
rooms = set()
for f in range(30000):
    p = w.players[0]
    was = p.dying
    bots[0].think(w, p)
    w.step(bots)
    deaths += bool(p.dying and not was)
    rooms.add(w.stage.room)
    if f % 300 == 0:
        w.draw(s, a)
    if w.cleared > 10 or (p.out and not god):
        break
print("frames", f, "cam", int(w.cam_x), "boss_hp", w.boss and w.boss.hp, "cleared", bool(w.cleared),
      "score", p.score, "freed", w.hostages_freed, "deaths", deaths, "out", p.out, "rooms", sorted(r for r in rooms if r), "pages", sorted(w.pages), "%.1fs" % (time.time() - t))
