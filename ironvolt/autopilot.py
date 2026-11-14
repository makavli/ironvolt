"""A bot that plays: the attract-mode demo, and the test that proves the stage can be finished."""

import math

from .settings import RESPAWN_SAFE, TILE
from .controls import BUTTONS


class BotPad:
    def __init__(self):
        self.now = dict.fromkeys(BUTTONS, False)
        self.before = dict(self.now)
        self.jump_hold = 0

    def held(self, b):
        return self.now[b]

    def pressed(self, b):
        return self.now[b] and not self.before[b]

    def axis(self):
        return (self.now["right"] - self.now["left"], self.now["down"] - self.now["up"])

    def think(self, world, p):
        self.before = dict(self.now)
        s = dict.fromkeys(BUTTONS, False)
        if p is None or not p.active:
            self.now = s
            return
        st = world.stage
        boss = world.boss
        dx = 1
        flying = hasattr(boss, "FLY")
        if boss and not boss.dying:
            near = (20, 36) if flying else (100, 150)          # a gunship is fought from just under its nose
            dx = -1 if p.x > boss.x - near[0] else (1 if p.x < boss.x - near[1] else 0)
            if dx < 0 and p.x < world.cam_x + 24:           # cornered: stand and fight
                dx = 0
            if dx == 0 and (boss.x - p.x) * p.facing < 0:     # backed off from a boss that walks in: turn round
                dx = 1 if boss.x > p.x else -1
        if world.stage.timed and world.foes:                  # on the lift: face whoever is nearest
            f = min(world.foes, key=lambda f: abs(f.x - p.x))
            dx = (1 if f.x > p.x else -1) if abs(f.x - p.x) > 40 or (f.x - p.x) * p.facing < 0 else 0
        if p.safe > RESPAWN_SAFE - 40 and not p.on_ground:     # dropping back in: straight down, onto the ground
            dx = 0
        ahead = p.x + 12 * (dx or 1)
        wall = any(st.solid(int(ahead // TILE), int((p.y - k) // TILE)) for k in (4, 18))
        pit = dx and st.floor_y(p.x + 10 * dx, p.y - 2) is None and not world.deck_at(p.x + 10 * dx)
        if p.riding is not None and getattr(p.riding, "going", False):
            pit = False                                        # the trolley's cage: ride it out
        danger = any(abs(b.x - p.x) < 34 and abs(b.y - (p.y - 10)) < 30 and (b.x - p.x) * b.vx < 0 or
                     (b.kind == "shell" and abs(b.x - p.x) < 20) for b in world.bolts)
        if p.on_ground and (wall or pit or danger) and not self.jump_hold:
            self.jump_hold = 22
        drop = bool(boss and not boss.dying and p.on_ground and p.on_catwalk(st) and not self.jump_hold
                    and getattr(boss, "mode", "") not in ("whistle", "charge"))   # fight from the floor
        if drop and not self.before.get("jump"):
            self.jump_hold = 1
        if self.jump_hold:
            s["jump"] = True
            if not world.freeze:                       # a hit-stop must not cut the jump short
                self.jump_hold -= 1
        air = [f for f in world.foes if f.__class__.__name__ == "Drone" and abs(f.x - p.x) < 50 and f.y < p.y - 30]
        if air:
            s["up"] = True
            dx = 0 if p.on_ground and abs(air[0].x - p.x) < 20 else dx     # never in mid-air: a pit may be below
        elif boss and not boss.dying and boss.state == "fight":
            s["up"] = flying or (world.frame // 60) % 3 == 0     # mix diagonal shots in
        s["right"], s["left"] = dx > 0, dx < 0
        if drop:
            s["down"], s["up"] = True, False
        if boss and not flying:                        # a gunship can end a bomb run behind you: walk back
            s["left"] = s["left"] and not s["up"]
        s["fire"] = (world.frame // 4) % 2 == 0
        s["bomb"] = bool(boss and boss.state == "fight" and world.frame % 240 == 0 and abs(boss.x - p.x) < 140)
        self.now = s
