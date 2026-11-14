"""Set pieces: the parts of a mission that change how it is played, not only how it looks.

Each mission lists its own (stage.Mission.props) as specs; build() turns a spec into the object. A prop steps once a
frame before the players move, draws itself behind the actors, and may offer a deck to stand on or a light in the dark.
"""

import random

import pygame

from . import audio, font
from .actors import STAND
from .settings import GROUND_Y, TILE, C, W

VENT_LAUNCH = -9.6          # a vent throws a player ~128 px up: from the floor over a catwalk at row 4
TROLLEY_V = 1.0             # px a frame along the cable


class Prop:
    def step(self, world):
        pass

    def draw(self, surf, atlas, cam, frame):
        pass

    def deck(self):
        """(left x, right x, top y) of something to stand on, or None."""
        return None

    def lights(self, frame):
        """(x, y, radius) of the light it throws in the dark."""
        return ()

    def sign(self):
        """(world x, y, text) of a bouncing sign over everything (what to do here), or None."""
        return None


def _standing(p, x0, x1, y):
    return p.on_ground and abs(p.y - y) < 1 and x0 <= p.x <= x1


class Drain(Prop):
    """A storm-drain grate in the road: crouch on it and the team drops into the drain under the road. It comes up
    again further on, past what the road holds."""

    def __init__(self, col, room, exit_col):
        self.x0, self.room, self.exit_col = col * TILE, room, exit_col
        self.near = self.used = False

    def step(self, world):
        live = world.live_players()
        self.near = any(abs(p.x - self.x0 - TILE) < 70 for p in live)
        if not self.used and any(p.crouch and _standing(p, self.x0 + 2, self.x0 + 2 * TILE - 2, GROUND_Y)
                                 for p in live):
            self.used = True                              # one way: the drain comes up past its own grate
            world.enter(self.room, self.exit_col)

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -40 or x > W + 8:
            return
        pygame.draw.rect(surf, C["black"], (x + 1, GROUND_Y, 30, 5))
        pygame.draw.rect(surf, C["steel_d"], (x + 1, GROUND_Y, 30, 5), 1)
        for bx in range(x + 4, x + 30, 4):
            pygame.draw.line(surf, C["steel"], (bx, GROUND_Y + 1), (bx, GROUND_Y + 3))
        if self.near and frame % 40 < 26:                 # a chevron: down here
            cx, cy = x + 16, GROUND_Y - 30 + (frame // 6) % 3
            pygame.draw.lines(surf, C["sun"], False, [(cx - 5, cy), (cx, cy + 5), (cx + 5, cy)], 2)


    def sign(self):
        return (self.x0 + 16, GROUND_Y - 62, "DUCK HERE: GO DOWN!") if self.near and not self.used else None


class Door(Prop):
    """A lift cage: walk in and the team rides it up through the tower (a room of its own)."""
    SIGN = "WALK IN: GOING UP!"

    def __init__(self, col, room, exit_col):
        self.x0, self.room, self.exit_col = col * TILE, room, exit_col
        self.used = self.near = False

    def step(self, world):
        self.near = any(-60 < p.x - self.x0 < 8 for p in world.live_players())
        if not self.used and any(self.x0 + 8 < p.x < self.x0 + 40 and p.on_ground for p in world.live_players()):
            self.used = True
            world.enter(self.room, self.exit_col)

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -60 or x > W + 8:
            return
        top = GROUND_Y - 56
        pygame.draw.rect(surf, C["black"], (x - 4, top, 44, 56))
        pygame.draw.rect(surf, C["steel_d"], (x - 4, top, 44, 56), 2)
        for k in range(0, 40, 6):                          # the open gate, folded to the side
            pygame.draw.line(surf, C["steel"], (x - 2 + k // 6, top + 4), (x - 2 + k // 6, GROUND_Y - 2))
        lit = C["green"] if frame % 30 < 20 else C["olive"]
        pygame.draw.rect(surf, lit, (x + 14, top - 7, 12, 5))
        cy = top + 24 + (frame // 6) % 3                  # an arrow: up
        pygame.draw.lines(surf, C["sun"], False, [(x + 14, cy), (x + 20, cy - 6), (x + 26, cy)], 2)


    def sign(self):
        return (self.x0 + 20, GROUND_Y - 78, self.SIGN) if self.near and not self.used else None


class Arc(Prop):
    """A live cross-arm: the line's current jumps along it on a beat. It crackles first; then anything standing on
    it is burnt. Cross it between beats."""
    PERIOD, WARN, LIVE = 210, 120, 165

    def __init__(self, c0, c1, row, phase=0):
        self.x0, self.x1, self.y, self.phase = c0 * TILE, (c1 + 1) * TILE, row * TILE, phase

    def beat(self, frame):
        return (frame + self.phase) % self.PERIOD

    def live(self, frame):
        return self.beat(frame) >= self.LIVE

    def step(self, world):
        t = self.beat(world.frame)
        on_screen = self.x1 > world.cam_x and self.x0 < world.cam_x + W
        if on_screen and t == self.WARN:
            audio.play("fuse")
        if on_screen and t == self.LIVE:
            audio.play("zap")
        if t < self.LIVE:
            return
        for p in world.live_players():
            if _standing(p, self.x0, self.x1, self.y):
                world.kill_player(p)
        for e in world.foes:
            if not getattr(e, "dying", 0) and getattr(e, "on_ground", False) and self.x0 <= e.x <= self.x1 \
                    and abs(e.y - self.y) < 1:
                e.damage(99, world, None)

    def draw(self, surf, atlas, cam, frame):
        x0, x1 = round(self.x0 - cam), round(self.x1 - cam)
        if x1 < 0 or x0 > W:
            return
        y = self.y - 1
        for ix in (x0 + 1, x1 - 2):                        # the insulators at each end
            pygame.draw.rect(surf, C["cyan"] if self.live(frame) else C["steel_l"], (ix - 1, y - 6, 3, 6))
        t = self.beat(frame)
        rnd = random.Random(frame // 2)
        if t >= self.LIVE:                                 # the arc: a jagged white-blue line along the arm
            pts = [(x, y - 3 + rnd.randrange(-3, 4)) for x in range(x0, x1 + 1, 6)]
            if len(pts) > 1:
                pygame.draw.lines(surf, C["cyan"], False, pts, 2)
                pygame.draw.lines(surf, C["white"], False, pts, 1)
        elif t >= self.WARN:                               # the warning: sparks spit along it, faster near the beat
            for _ in range(1 + (t - self.WARN) // 12):
                sx = rnd.randrange(x0, max(x0 + 1, x1))
                pygame.draw.line(surf, C["cyan"], (sx, y - 1), (sx + rnd.randrange(-2, 3), y - 4))

    def lights(self, frame):
        if self.live(frame):
            return [((self.x0 + self.x1) / 2, self.y - 4, (self.x1 - self.x0) // 2 + 10)]
        return ()


class Trolley(Prop):
    """A lineman's cable trolley over the gully: it waits until the whole team is aboard, then runs along the
    cable to the far side. Its cage keeps a rider aboard; a jump can still leave it."""
    W = 48

    def __init__(self, c0, c1, row):
        self.x, self.x_end, self.y = float(c0 * TILE), float(c1 * TILE), row * TILE
        self.cable0, self.cable1 = c0 * TILE - 24, c1 * TILE + self.W + 24
        self.dx, self.v = 0.0, 0.0
        self.going = self.done = False

    def deck(self):
        return self.x, self.x + self.W, self.y

    def step(self, world):
        live = world.live_players()
        aboard = [p for p in live if p.riding is self]
        if not self.going and not self.done and live and len(aboard) == len(live):
            self.going = True
            audio.play("lift")
        self.dx = 0.0
        if self.going:
            self.v = min(TROLLEY_V, self.v + 0.02)
            self.dx = min(self.v, self.x_end - self.x)
            self.x += self.dx
            if self.x >= self.x_end:
                self.going, self.done = False, True
                audio.play("clank")
        self.need = bool(aboard) and not self.going and not self.done     # someone aboard, someone not

    def draw(self, surf, atlas, cam, frame):
        cy = self.y - 58
        a, b = round(self.cable0 - cam), round(self.cable1 - cam)
        if b < 0 or a > W:
            return
        pygame.draw.line(surf, C["ink"], (a, cy), (b, cy), 2)
        for mx in (a, b):                                   # the masts at each end
            pygame.draw.line(surf, C["black"], (mx, cy - 6), (mx, GROUND_Y), 3)
            pygame.draw.line(surf, C["steel_d"], (mx - 6, cy - 4), (mx + 6, cy - 4), 2)
        x = round(self.x - cam)
        for wx in (x + 12, x + 36):                         # the wheels on the cable, the hangers down to the deck
            pygame.draw.circle(surf, C["steel"], (wx, cy), 3)
            pygame.draw.line(surf, C["steel_d"], (wx, cy + 3), (wx, self.y - 22))
        pygame.draw.line(surf, C["steel_d"], (x + 6, self.y - 22), (x + self.W - 6, self.y - 22), 2)
        pygame.draw.rect(surf, C["rust_d"], (x, self.y, self.W, 5))
        pygame.draw.line(surf, C["sun"], (x, self.y), (x + self.W - 1, self.y))
        for k in range(x + 2, x + self.W, 5):               # the cage's rails
            pygame.draw.line(surf, C["steel_d"], (k, self.y - 10), (k, self.y))
        pygame.draw.line(surf, C["steel"], (x, self.y - 10), (x + self.W - 1, self.y - 10))
        if getattr(self, "need", False) and frame % 40 < 26:
            font.draw(surf, "ALL ABOARD", (x + self.W // 2, self.y - 40), C["sun"], center=True)


class Vent(Prop):
    """A steam vent in the floor: stand on it, it hisses, and it throws you high, up to the catwalks no jump
    reaches."""

    def __init__(self, col):
        self.x0 = col * TILE
        self.charge = self.cool = self.puff = 0

    def step(self, world):
        on = [p for p in world.live_players() if _standing(p, self.x0 - 2, self.x0 + TILE + 2, GROUND_Y)]
        if self.cool:
            self.cool -= 1
        elif self.charge:
            self.charge -= 1
            if not self.charge:
                for p in on:
                    p.vy, p.on_ground, p.coyote, p.flung = VENT_LAUNCH, False, 0, 40
                    world.popups.append([p.x, p.y - 30.0, "WHEE!", 40])
                self.cool, self.puff = 36, 30
                audio.play("vent")
        elif on:
            self.charge = 12
            audio.play("fuse")
        if self.puff or self.charge:
            self.puff = max(0, self.puff - 1)
            world.part(self.x0 + random.uniform(3, 13), GROUND_Y - 2, random.uniform(-0.3, 0.3),
                       -random.uniform(1.5, 3.5) if self.puff else -0.6, 26, "smoke", 2)

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -20 or x > W + 4:
            return
        pygame.draw.rect(surf, C["steel_d"], (x, GROUND_Y - 3, TILE, 3))
        pygame.draw.rect(surf, C["black"], (x + 2, GROUND_Y - 2, TILE - 4, 2))
        glow = C["sun"] if self.charge and frame % 4 < 2 else C["ember"]
        for k in range(x + 3, x + TILE - 2, 3):
            surf.set_at((k, GROUND_Y - 2), glow)


class Piston(Prop):
    """A crusher in the works: it shudders, slams to the floor, holds, and rises. Run under it between blows.
    It crushes troopers too."""
    PERIOD, SHAKE, SLAM, HOLD, RISE = 150, 70, 104, 110, 134
    TOP, W, HEAD = 56, 32, 22

    def __init__(self, col, phase=0):
        self.x0, self.phase = col * TILE, phase

    def bottom(self, frame):
        """The head's bottom edge, in px."""
        t = (frame + self.phase) % self.PERIOD
        low, high = GROUND_Y, self.TOP + self.HEAD
        if t < self.SLAM:
            return high
        if t < self.HOLD:
            return high + (low - high) * (t - self.SLAM + 1) / (self.HOLD - self.SLAM)
        if t < self.RISE:
            return low
        return low - (low - high) * (t - self.RISE) / (self.PERIOD - self.RISE)

    def head(self, frame):
        b = self.bottom(frame)
        return pygame.Rect(self.x0, round(b) - self.HEAD, self.W, self.HEAD)

    def step(self, world):
        f = world.frame
        t = (f + self.phase) % self.PERIOD
        r = self.head(f)
        on_screen = -self.W < self.x0 - world.cam_x < W
        if t == self.HOLD and on_screen:
            world.shake = max(world.shake, 4)
            audio.play("stomp")
            for side in (0, self.W):
                world.dust(self.x0 + side, GROUND_Y)
        deadly = self.SLAM <= t < self.HOLD + 4
        for p in world.live_players():
            pr = p.rect()
            if pr.colliderect(r):
                if deadly:
                    world.kill_player(p)
                else:                                         # a head held down is a wall
                    p.x = r.left - p.w / 2 - 0.5 if p.x < r.centerx else r.right + p.w / 2 + 0.5
        if deadly:
            for e in world.foes:
                if not getattr(e, "dying", 0) and e.rect().colliderect(r):
                    e.damage(99, world, None)
                    world.popups.append([e.x, e.y - 30.0, "SQUASHED!", 50])
                    audio.play("squash")

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -self.W or x > W:
            return
        t = (frame + self.phase) % self.PERIOD
        jig = 1 if self.SHAKE <= t < self.SLAM and frame % 4 < 2 else 0
        r = self.head(frame).move(-round(cam) + jig, 0)
        pygame.draw.rect(surf, C["steel_d"], (x + 11 + jig, 0, 10, r.top))     # the ram
        pygame.draw.line(surf, C["steel"], (x + 12 + jig, 0), (x + 12 + jig, r.top))
        pygame.draw.rect(surf, C["black"], r)
        pygame.draw.rect(surf, C["steel"], r.inflate(-2, -2))
        for k in range(-r.h, r.w, 8):                         # hazard stripes along the striking face
            pygame.draw.line(surf, C["gold"], (r.left + k, r.bottom - 3), (r.left + k + 5, r.bottom - 8), 2)
        pygame.draw.line(surf, C["black"], (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
        if self.SHAKE <= t < self.SLAM and t % 10 < 5:          # the warning lamp on the ram
            pygame.draw.circle(surf, C["red"], (x + 16 + jig, max(4, r.top - 6)), 2)


class Dark(Prop):
    """A stretch with the lights out: only muzzle flashes, fire, a few lamps and the Legion's red lenses show."""

    def __init__(self, c0, c1):
        self.x0, self.x1 = c0 * TILE, c1 * TILE
        self.warned = False

    def amount(self, cam):
        """0 to 1: how dark it is with the camera here (it fades in and out over 60 px)."""
        mid = cam + W / 2
        return max(0.0, min(1.0, (mid - self.x0) / 60, (self.x1 - mid) / 60))

    def step(self, world):
        if not self.warned and self.amount(world.cam_x) > 0.2:
            self.warned = True
            audio.play("alarm")
            world.popups.append([world.cam_x + W / 2, 70.0, "LIGHTS OUT", 120])


class Crane(Trolley):
    """The scrapyard's magnet crane: a car wreck hangs from it, and it carries whoever stands on the wreck over the
    flooded pit. The magnet holds your boots (the trolley's cage). Empty at the far end, it swings back."""

    def __init__(self, c0, c1, row):
        super().__init__(c0, c1, row)
        self.x0, self.wait = self.x, 0

    def step(self, world):
        super().step(world)
        if not self.done:
            return
        if any(p.riding is self for p in world.live_players()):
            self.wait = 0
            return
        self.wait += 1
        if self.wait > 60:                                   # nobody aboard: back for the next rider
            self.dx = -min(TROLLEY_V, self.x - self.x0)
            self.x += self.dx
            if self.x <= self.x0:
                self.done, self.v, self.wait = False, 0.0, 0
                audio.play("clank")

    def draw(self, surf, atlas, cam, frame):
        a, b = round(self.cable0 - cam), round(self.cable1 - cam)
        if b < -10 or a > W + 10:
            return
        ry = self.y - 92                                     # the crane's rail, on two lattice towers
        for mx in (a, b):
            pygame.draw.rect(surf, C["black"], (mx - 4, ry, 8, GROUND_Y - ry + 30))
            for k in range(ry, GROUND_Y, 10):
                pygame.draw.line(surf, C["steel_d"], (mx - 4, k), (mx + 3, k + 9))
        pygame.draw.rect(surf, C["black"], (a - 6, ry - 4, b - a + 12, 7))
        for k in range(a, b, 12):
            pygame.draw.line(surf, C["gold"], (k, ry - 3), (k + 6, ry + 2), 2)
        x = round(self.x - cam)
        cx = x + self.W // 2
        pygame.draw.rect(surf, C["steel_d"], (cx - 9, ry + 3, 18, 7))          # the carriage on the rail
        pygame.draw.line(surf, C["ink"], (cx, ry + 10), (cx, self.y - 44), 2)  # the cable down to the magnet
        hum = 1 if self.going and frame % 6 < 3 else 0
        pygame.draw.ellipse(surf, C["black"], (cx - 14, self.y - 46 + hum, 28, 10))
        pygame.draw.ellipse(surf, C["red"], (cx - 12, self.y - 44 + hum, 24, 6))
        for k in (-10, 10):                                  # chains from the magnet to the wreck's corners
            pygame.draw.line(surf, C["steel"], (cx + k // 2, self.y - 36 + hum), (cx + k * 2, self.y))
        pygame.draw.rect(surf, C["black"], (x - 1, self.y - 1, self.W + 2, 13))   # the wreck: a car, on its back
        pygame.draw.rect(surf, C["olive"], (x, self.y, self.W, 7))
        pygame.draw.rect(surf, C["rust_d"], (x + 3, self.y + 7, self.W - 6, 4))
        pygame.draw.line(surf, C["sun"], (x, self.y), (x + self.W - 1, self.y))
        for wx in (x + 9, x + self.W - 9):
            pygame.draw.circle(surf, C["black"], (wx, self.y + 12), 4)
            pygame.draw.circle(surf, C["steel_d"], (wx, self.y + 12), 2)
        if getattr(self, "need", False) and frame % 40 < 26:
            font.draw(surf, "ALL ABOARD", (cx, self.y - 60), C["sun"], center=True)

    def sign(self):
        if not self.going and not self.done and not getattr(self, "need", False) and self.x == self.x0:
            return (self.x + self.W // 2, self.y - 70, "HOP ON THE WRECK!")
        return None


class Crusher(Piston):
    """The scrapyard's car press: a crusher's beat, flattening wrecks (and troopers) under a yellow slab."""

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -self.W - 8 or x > W + 8:
            return
        for px in (x - 6, x + self.W + 1):                    # the press's posts, hazard-striped
            pygame.draw.rect(surf, C["black"], (px, self.TOP - 8, 5, GROUND_Y - self.TOP + 8))
            for k in range(self.TOP - 8, GROUND_Y, 8):
                pygame.draw.line(surf, C["gold"], (px, k + 4), (px + 4, k), 2)
        pygame.draw.rect(surf, C["black"], (x - 6, self.TOP - 12, self.W + 12, 6))
        pygame.draw.rect(surf, C["rust_d"], (x + 2, GROUND_Y - 4, self.W - 4, 4))   # what is left of the last car
        t = (frame + self.phase) % self.PERIOD
        jig = 1 if self.SHAKE <= t < self.SLAM and frame % 4 < 2 else 0
        r = self.head(frame).move(-round(cam) + jig, 0)
        pygame.draw.rect(surf, C["steel_d"], (x + 12 + jig, self.TOP - 6, 8, max(0, r.top - self.TOP + 6)))
        pygame.draw.rect(surf, C["black"], r)
        pygame.draw.rect(surf, C["gold"], r.inflate(-2, -2))
        pygame.draw.line(surf, C["sun"], (r.left + 1, r.top + 1), (r.right - 2, r.top + 1))
        pygame.draw.line(surf, C["black"], (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
        if self.SHAKE <= t < self.SLAM and t % 10 < 5:
            pygame.draw.circle(surf, C["red"], (x + 16 + jig, self.TOP - 16), 2)


class Ladder(Door):
    """A boxcar rolling slowly on the next track, its ladder down: walk to it and the team climbs onto the roofs
    of the moving train (a room of its own)."""
    SIGN = "HOP ON THE TRAIN!"

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -70 or x > W + 8:
            return
        top = GROUND_Y - 60
        pygame.draw.rect(surf, C["black"], (x - 12, top, 64, 54))
        pygame.draw.rect(surf, C["rust_d"], (x - 10, top + 2, 60, 50))
        for k in range(x - 6, x + 48, 8):                     # the boxcar's planks
            pygame.draw.line(surf, C["rust"], (k, top + 4), (k, top + 49))
        for wx in (x - 2, x + 42):
            pygame.draw.circle(surf, C["black"], (wx, GROUND_Y - 4), 5)
            pygame.draw.circle(surf, C["steel"], (wx, GROUND_Y - 4), 2 + (frame // 8) % 2)
        pygame.draw.line(surf, C["steel_l"], (x + 14, top - 8), (x + 14, GROUND_Y - 2))
        pygame.draw.line(surf, C["steel_l"], (x + 26, top - 8), (x + 26, GROUND_Y - 2))
        for k in range(top - 6, GROUND_Y - 2, 6):             # the ladder, bright: climb here
            pygame.draw.line(surf, C["sun"], (x + 14, k), (x + 26, k))


class Gantries(Prop):
    """On the train's roofs: signal gantries come at you at head height. A bell, a DUCK! sign, then the beam sweeps
    the roof. Crouch under it; troopers who stand get knocked off."""
    SPEED, BOTTOM, BEAM = 4.0, GROUND_Y - 15, 10

    def __init__(self, first, every, last):
        self.times = set(range(first, last, every))
        self.beams = []                                     # each beam's left edge; the room's camera stays at 0

    def step(self, world):
        if world.room_t in self.times:
            self.beams.append(float(W + 240))                # 60 frames off screen: the warning's time
            audio.play("bell")
        self.beams = [x - self.SPEED for x in self.beams if x > -20]
        for x in self.beams:
            r = pygame.Rect(round(x), 0, self.BEAM, self.BOTTOM)
            for p in world.live_players():
                if p.rect().colliderect(r):
                    world.kill_player(p)
            for e in world.foes:
                if not getattr(e, "dying", 0) and e.rect().colliderect(r):
                    e.damage(99, world, None, push=-1)
                    world.popups.append([e.x, e.y - 30.0, "BONK!", 50])

    def draw(self, surf, atlas, cam, frame):
        for x in self.beams:
            x = round(x - cam)
            if x > W:
                continue
            pygame.draw.rect(surf, C["black"], (x, 0, self.BEAM, self.BOTTOM))
            for k in range(0, self.BOTTOM, 8):
                pygame.draw.line(surf, C["steel_d"], (x + 1, k), (x + self.BEAM - 2, k + 7))
            pygame.draw.rect(surf, C["gold"], (x - 2, self.BOTTOM - 4, self.BEAM + 4, 4))
            for k in range(x - 2, x + self.BEAM + 2, 4):
                pygame.draw.line(surf, C["black"], (k, self.BOTTOM - 4), (k + 2, self.BOTTOM - 1))
            lamp = C["red"] if frame % 20 < 10 else C["green"]
            pygame.draw.circle(surf, lamp, (x + self.BEAM // 2, self.BOTTOM - 26), 2)

    def sign(self):
        return (W - 60, 56, "DUCK!") if any(x > W - 60 for x in self.beams) else None


class Shutter(Prop):
    """A blast shutter come down over the way, jammed a hand's width off the floor: slide under it (down + jump).
    It is a wall to anyone standing, and it stops shots both ways."""
    SLOT, W = 15, 12                    # the gap: over a slide (12 px tall), under anyone standing (21)
    SIGN = "SLIDE UNDER!"

    def __init__(self, col):
        self.x0 = col * TILE + 2
        self.near = False

    def rect(self):
        return pygame.Rect(self.x0, 0, self.W, GROUND_Y - self.SLOT)

    def step(self, world):
        r, live = self.rect(), world.live_players()
        self.near = any(0 < self.x0 - p.x < 110 for p in live)
        for p in live:
            if p.slide and r.colliderect(round(p.x - p.w / 2), round(p.y) - STAND, p.w, STAND):
                p.slide = max(p.slide, 2)               # a slide never ends under it, as under a low ceiling
            if p.rect().colliderect(r):
                self.touch(p, world, r)
        for e in world.foes:
            if not getattr(e, "dying", 0) and e.rect().colliderect(r):
                self.touch_foe(e, world, r)
        for b in self.stops(world):
            if r.collidepoint(b.x, b.y):
                b.dead = True

    def stops(self, world):
        return world.shots + world.bolts

    def touch(self, p, world, r):
        p.x = r.left - p.w / 2 - 0.5 if p.x < r.centerx else r.right + p.w / 2 + 0.5

    touch_foe = touch

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -20 or x > W + 8:
            return
        bottom = GROUND_Y - self.SLOT
        for rx in (x - 3, x + self.W):                         # the guide rails, down to the floor
            pygame.draw.rect(surf, C["black"], (rx, 0, 3, GROUND_Y))
        pygame.draw.rect(surf, C["steel_d"], (x, 0, self.W, bottom))
        for k in range(2, bottom, 5):                          # the slats
            pygame.draw.line(surf, C["steel"], (x, k), (x + self.W - 1, k))
        for k in range(-6, self.W, 6):                         # hazard stripes on the jammed edge
            pygame.draw.line(surf, C["gold"], (x + max(0, k), bottom - 2), (x + min(self.W - 1, k + 4), bottom - 6), 2)
        pygame.draw.line(surf, C["black"], (x, bottom - 1), (x + self.W - 1, bottom - 1))
        for rx in (x - 3, x + self.W):                         # the rails' hazard paint: never a plain girder
            for k in range(bottom - 40, GROUND_Y, 6):
                pygame.draw.line(surf, C["gold"], (rx, k + 3), (rx + 2, k), 1)
        lamp = C["red"] if frame % 30 < 15 else C["rust_d"]
        pygame.draw.circle(surf, lamp, (x + self.W // 2, bottom - 12), 2)
        if self.near and frame % 40 < 26:                      # a chevron along the floor: under here
            cy = GROUND_Y - 7
            cx = x - 14 + (frame // 6) % 3
            pygame.draw.lines(surf, C["sun"], False, [(cx, cy - 4), (cx + 4, cy), (cx, cy + 4)], 2)

    def sign(self):
        return (self.x0 + self.W // 2, GROUND_Y - 70, self.SIGN) if self.near else None


class Laser(Shutter):
    """A Legion laser fence across the road, its lowest beam a hand's width off the floor: slide under it.
    Standing in it burns; troopers who walk into it are fried. Shots pass through light."""
    SIGN = "LASERS: SLIDE!"

    def stops(self, world):
        return ()

    def touch(self, p, world, r):
        world.kill_player(p)

    def touch_foe(self, e, world, r):
        e.damage(99, world, None)
        world.popups.append([e.x, e.y - 30.0, "FRIED!", 50])
        audio.play("zap")

    def draw(self, surf, atlas, cam, frame):
        x = round(self.x0 - cam)
        if x < -20 or x > W + 8:
            return
        bottom = GROUND_Y - self.SLOT
        for px in (x - 4, x + self.W + 1):                    # the emitter posts, a lamp at each beam
            pygame.draw.rect(surf, C["black"], (px, 40, 4, GROUND_Y - 40))
            for by in range(bottom - 2, 44, -10):
                surf.set_at((px + 1, by), C["red"])
        rnd = random.Random(frame // 3)
        for by in range(bottom - 2, 44, -10):                 # the beams: red, flickering, a white core
            j = rnd.randrange(-1, 2)
            pygame.draw.line(surf, C["red"], (x - 1, by + j), (x + self.W, by + j), 2)
            pygame.draw.line(surf, C["white"], (x, by + j), (x + self.W - 1, by + j))
        for k in range(42, 0, -6):                            # above the posts: a haze of heat
            if (k + frame // 4) % 12 < 6:
                surf.set_at((x + self.W // 2 + rnd.randrange(-3, 4), k), C["red"])
        if self.near and frame % 40 < 26:
            cy = GROUND_Y - 7
            cx = x - 16 + (frame // 6) % 3
            pygame.draw.lines(surf, C["sun"], False, [(cx, cy - 4), (cx + 4, cy), (cx, cy + 4)], 2)

    def lights(self, frame):
        return [(self.x0 + self.W / 2, GROUND_Y - 60, 40)]


class Crumble(Prop):
    """A rotten catwalk over a pit: it holds a moment, shudders under your boots, and drops. Keep running. The
    Legion bolts a new one in place after a while."""
    HOLD, BACK = 32, 300

    def __init__(self, c0, c1, row):
        self.x0, self.x1, self.y = c0 * TILE, (c1 + 1) * TILE, row * TILE
        self.t, self.fall, self.near = 0, 0.0, False

    def deck(self):
        return (self.x0, self.x1, self.y) if self.t <= self.HOLD else None

    def step(self, world):
        live = world.live_players()
        self.near = self.t == 0 and any(0 < self.x0 - p.x < 90 for p in live)
        if self.t == 0:
            if any(p.riding is self for p in live):
                self.t = 1
                audio.play("clank")
            return
        self.t += 1
        if self.t == self.HOLD + 1:
            audio.play("stomp")
            world.dust((self.x0 + self.x1) / 2, self.y)
        if self.t > self.HOLD:
            self.fall += 0.25 * (self.t - self.HOLD)
        if self.t > self.BACK and not any(self.x0 - 8 <= p.x <= self.x1 + 8 for p in live):
            self.t, self.fall = 0, 0.0                       # a new one, bolted in where nobody stands

    def draw(self, surf, atlas, cam, frame):
        x, x1 = round(self.x0 - cam), round(self.x1 - cam)
        y = round(self.y + self.fall)
        if x1 < 0 or x > W or y > GROUND_Y + 60:
            return
        if 0 < self.t <= self.HOLD:                          # the shudder: harder as it gives
            x += (frame % 4 < 2) * (1 + self.t // 12)
            x1 = x + self.x1 - self.x0
        w = x1 - x
        tilt = min(8, round(self.fall / 4))                  # it drops nose first
        pygame.draw.polygon(surf, C["black"], [(x, y - 1), (x + w, y - 1 + tilt), (x + w, y + 5 + tilt), (x, y + 5)])
        pygame.draw.polygon(surf, C["rust_d"], [(x + 1, y), (x + w - 1, y + tilt), (x + w - 1, y + 4 + tilt), (x + 1, y + 4)])
        pygame.draw.line(surf, C["rust"], (x + 1, y), (x + w - 1, y + tilt))
        for k in range(x + 4, x + w - 2, 7):                 # the rotten slats
            pygame.draw.line(surf, C["black"], (k, y + 1 + tilt * (k - x) // w), (k + 1, y + 4 + tilt * (k - x) // w))
        if self.t == 0:                                      # the brackets it hangs on, while it hangs
            for bx in (x + 2, x + w - 4):
                pygame.draw.line(surf, C["steel_d"], (bx, y + 5), (bx + 2, y + 12), 2)

    def sign(self):
        return ((self.x0 + self.x1) // 2, self.y - 50, "IT WON'T HOLD: RUN!") if self.near else None


KINDS = {"drain": Drain, "door": Door, "arc": Arc, "trolley": Trolley, "vent": Vent, "piston": Piston, "dark": Dark,
         "crane": Crane, "crusher": Crusher, "ladder": Ladder, "gantries": Gantries, "shutter": Shutter,
         "laser": Laser, "crumble": Crumble}
ROOM_KINDS = ("drain", "door", "ladder")         # the props that lead into a room


def build(spec):
    return KINDS[spec[0]](*spec[1:])


def light_mask(size, alpha, lights):
    """A veil of the darkness, with the lights cut out of it: an outer soft ring and a clear centre."""
    veil = pygame.Surface(size, pygame.SRCALPHA)
    veil.fill((4, 3, 10, alpha))
    for k, a in ((1.0, alpha * 2 // 3), (0.72, alpha // 3), (0.45, 0)):     # three steps, each over all lights:
        for x, y, r in lights:                                              # one light's ring never covers another's centre
            pygame.draw.circle(veil, (4, 3, 10, a), (round(x), round(y)), max(2, round(r * k)))
    return veil

