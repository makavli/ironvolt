"""Everything that moves. Positions are floats (sub-pixel); x is the centre, y is the feet (bottom edge).

Body.move() is the one collision routine: axis by axis against the tile grid, with one-way catwalks.
"""

import math
import random

import pygame

from . import audio
from .settings import (BULLET_V, ENEMY_BULLET_V, GRAVITY, GRENADES, JUMP_V, LIVES, MAX_FALL, RESPAWN_SAFE, RUN,
                       SCORE, TILE, WEAPONS, C, H, W)
from .stage import WALK


class Body:
    w, h = 10, 20
    lip = 0                                 # px the feet may be under a ledge's top and still make it (players)

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.ox, self.oy = self.x, self.y   # where it was a step ago: the picture blends between the two
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.drop = 0                       # frames left falling through catwalks
        self.dead = False

    def rect(self):
        return pygame.Rect(round(self.x - self.w / 2), round(self.y - self.h), self.w, self.h)

    def blocked(self, stage, y):
        """Would the body overlap a solid tile with its feet at y?"""
        return any(stage.solid(tx, ty)
                   for tx in range(int((self.x - self.w / 2) // TILE), int((self.x + self.w / 2 - 0.01) // TILE) + 1)
                   for ty in range(int((y - self.h) // TILE), int((y - 0.01) // TILE) + 1))

    def move(self, stage):
        """Moves by (vx, vy) and resolves tile collisions. Returns True if it landed this step."""
        self.x += self.vx
        if self.vx:
            tx = int((self.x + (self.w / 2 - 0.01 if self.vx > 0 else -self.w / 2)) // TILE)     # the leading edge
            feet = int((self.y - 0.01) // TILE)
            if any(stage.solid(tx, ty) for ty in range(int((self.y - self.h) // TILE), feet + 1)):
                if self.y - feet * TILE <= self.lip and not self.blocked(stage, feet * TILE):
                    self.y = float(feet * TILE)         # a toe on the ledge counts: up and over, speed kept
                else:
                    self.x = tx * TILE - self.w / 2 if self.vx > 0 else (tx + 1) * TILE + self.w / 2
                    self.vx = 0
        prev = self.y
        self.y += self.vy
        landed, was = False, self.on_ground
        self.on_ground = False
        left, right = self.x - self.w / 2, self.x + self.w / 2 - 0.01
        if self.vy >= 0:
            ty = int(self.y // TILE)
            for tx in range(int(left // TILE), int(right // TILE) + 1):
                t = stage.tile(tx, ty)
                top_px = ty * TILE
                if stage.solid(tx, ty) or (t == WALK and prev <= top_px + 0.01 and not self.drop):
                    self.y = top_px
                    self.vy = 0
                    self.on_ground = True
                    landed = not was
                    break
        else:
            ty = int((self.y - self.h) // TILE)
            for tx in range(int(left // TILE), int(right // TILE) + 1):
                if stage.solid(tx, ty):
                    self.y = (ty + 1) * TILE + self.h
                    self.vy = 0
                    break
        if self.drop:
            self.drop -= 1
        return landed


# ------------------------------------------------------------------ player

ACCEL, FRICTION, TURN = 0.5, 0.5, 1.0      # on the ground: full speed in 3 frames, a stop in 3, a turn-about in 4
AIR_ACCEL, AIR_DRAG = 0.3, 0.15            # in the air: steering, yes, but a jump keeps some of its momentum
JUMP_GRAVITY, FALL_GRAVITY = 0.36, 0.5     # falling is heavier than rising: snappy arcs
HANG_V, HANG = 1.0, 0.5                    # a held jump floats at its top (half gravity): room to aim and to land
JUMP_CUT = 0.4                             # let go early, jump lower
COYOTE, BUFFER = 6, 6                      # frames of forgiveness at ledges and before landing
FIRE_BUFFER = 8                            # a tap between two shots still fires, as soon as the gun allows
STAND, DUCK = 21, 12                       # body heights: rifle fire flies 15 px up, over a crouch


class Player(Body):
    w, h = 10, STAND
    lip = 4

    def __init__(self, index, x, y):
        super().__init__(x, y)
        self.index = index
        self.facing = 1
        self.aim = (1, 0)
        self.crouch = False
        self.weapon, self.ammo = "P", 0
        self.cooldown = 0
        self.grenades = GRENADES
        self.lives = LIVES
        self.score = 0
        self.chain, self.chain_t = 0, 0    # kills in a row, and frames left to add the next
        self.safe = RESPAWN_SAFE
        self.dying = 0
        self.out = False               # no lives left (may continue)
        self.coyote = self.buffer = 0
        self.trigger, self.lob = 0, False      # a fire press and a grenade press, waiting their turn
        self.run_t = 0.0
        self.recoil = 0
        self.god = False               # tests and the attract demo

    @property
    def active(self):
        return not self.out and not self.dying

    def listen(self, pad):
        """Presses are kept for a few frames, and through a hit-stop: none is ever swallowed."""
        if pad.pressed("jump"):
            self.buffer = BUFFER
        if pad.pressed("fire"):
            self.trigger = FIRE_BUFFER
        self.lob = self.lob or pad.pressed("bomb")

    def on_catwalk(self, stage):
        """Catwalk under the feet, anywhere across them, and nothing solid to catch a drop."""
        ty = int(self.y // TILE)
        cols = range(int((self.x - self.w / 2) // TILE), int((self.x + self.w / 2 - 0.01) // TILE) + 1)
        return any(stage.tile(tx, ty) == WALK for tx in cols) and not any(stage.solid(tx, ty) for tx in cols)

    def step(self, pad, world):
        if self.out:
            return
        if self.dying:
            self.dying -= 1
            self.vy = min(MAX_FALL, self.vy + GRAVITY)
            if self.on_ground:
                self.vx *= 0.8                          # the body skids to a stop: it does not glide
            self.move(world.stage)
            if self.dying == 0:
                world.respawn(self)
            return
        self.listen(pad)
        if self.safe:
            self.safe -= 1
        dx, dy = pad.axis()
        self.crouch = dy > 0 and self.on_ground
        if dx:
            self.facing = dx
        target = 0 if self.crouch else dx * RUN
        if not self.on_ground:
            accel = AIR_ACCEL if dx else AIR_DRAG
        elif not target:
            accel = FRICTION
        else:
            accel = TURN if self.vx * dx < 0 else ACCEL
            if self.vx * dx <= -RUN:
                world.dust(self.x, self.y)              # boots dig in on a full turn-about
        self.vx += max(-accel, min(accel, target - self.vx))
        # aim: up, diagonals, down only in the air
        if dy < 0:
            self.aim = (dx, -1) if dx else (0, -1)
        elif dy > 0 and not self.on_ground:
            self.aim = (dx, 1) if dx else (0, 1)
        else:
            self.aim = (self.facing, 0)

        # jumping: buffered presses, coyote time, a cut when the button is let go, a float at the top while held
        self.coyote = COYOTE if self.on_ground else max(0, self.coyote - 1)
        if self.buffer and self.crouch and self.on_catwalk(world.stage):
            self.drop, self.buffer, self.coyote, self.on_ground = 10, 0, 0, False   # down + jump: through a catwalk
        elif self.buffer and self.coyote:
            self.vy = JUMP_V
            self.buffer = self.coyote = 0
            if self.on_ground:
                world.dust(self.x, self.y)              # kicked up at take-off (a coyote jump has left the ground)
            self.on_ground = False
            audio.play("jump")
        self.buffer = max(0, self.buffer - 1)
        held = pad.held("jump")
        if not held and self.vy < JUMP_V * JUMP_CUT:
            self.vy = JUMP_V * JUMP_CUT
        gravity = JUMP_GRAVITY if self.vy < 0 else FALL_GRAVITY
        # the float is for a jump only: a step off a ledge, or a drop through a catwalk, just falls
        if held and not self.coyote and not self.drop and abs(self.vy) < HANG_V:
            gravity *= HANG
        self.vy = min(MAX_FALL, self.vy + gravity)

        self.h = DUCK if self.crouch else STAND
        if self.move(world.stage):
            world.dust(self.x, self.y)
            world.feel(self, "land")
            audio.play("land")
        self.x = max(world.cam_x + 6, min(world.cam_x + W - 6, self.x))
        self.run_t = self.run_t + abs(self.vx) * 0.12 if self.on_ground and abs(self.vx) > 0.2 else 0

        self.cooldown, self.recoil = max(0, self.cooldown - 1), max(0, self.recoil - 1)
        rate = WEAPONS[self.weapon][0]
        # a tap fires once half the wait is over (mashing beats holding); a held button keeps the weapon's beat
        if (self.trigger and self.cooldown <= rate // 2) or (pad.held("fire") and not self.cooldown):
            self.trigger = 0
            self.shoot(world)
            self.cooldown = rate
        self.trigger = max(0, self.trigger - 1)
        if self.lob and self.grenades:
            self.grenades -= 1
            world.thrown.append(Grenade(self.x + self.facing * 4, self.y - 16,
                                        self.facing * 2.4 + self.vx * 0.5, -3.4, self))
        self.lob = False

        if self.y > H + 40:
            world.kill_player(self)

    def muzzle(self):
        ax, ay = self.aim
        n = math.hypot(ax, ay) or 1
        sx, sy = self.x + self.facing * 2, self.y - (9 if self.crouch else 15)
        return sx + ax / n * 11, sy + ay / n * 11, ax / n, ay / n

    def shoot(self, world):
        mx, my, ux, uy = self.muzzle()
        dmg = WEAPONS[self.weapon][2]
        if self.weapon == "S":
            for a in (-0.28, -0.14, 0, 0.14, 0.28):
                c, s = math.cos(a), math.sin(a)
                world.shots.append(Shot(mx, my, (ux * c - uy * s) * 4.5, (ux * s + uy * c) * 4.5, dmg, self, "pellet"))
            audio.play("spread")
            world.shake = max(world.shake, 3)           # the big guns kick the screen
        elif self.weapon == "R":
            world.shots.append(Shot(mx, my, ux * 2.5, uy * 2.5, dmg, self, "rocket"))
            audio.play("rocket")
            world.shake = max(world.shake, 3)
        else:
            jitter = random.uniform(-0.25, 0.25) if self.weapon == "H" else 0
            world.shots.append(Shot(mx, my, (ux - uy * jitter) * BULLET_V, (uy + ux * jitter) * BULLET_V, dmg, self,
                                    "heavy" if self.weapon == "H" else "bullet"))
            audio.play("heavy" if self.weapon == "H" else "shot")
        world.flash(mx, my, small=True)
        world.casing(self.x, self.y - 14, -self.facing)
        self.recoil = 3
        world.feel(self, "shot" if self.weapon == "P" else "heavy")
        if self.weapon != "P":
            self.ammo -= 1
            if self.ammo <= 0:
                self.weapon, self.ammo = "P", 0

    def frame(self, atlas):
        frames = (atlas.players if self.facing > 0 else atlas.players_l)[self.index]
        if self.dying or not self.on_ground:
            return frames["jump"]
        if self.crouch:
            return frames["crouch"]
        if self.run_t:
            return frames["run%d" % (int(self.run_t) % 4)]
        return frames["stand"]

    def draw(self, surf, atlas, cam):
        if self.out or (self.safe and (self.safe // 3) % 2) and not self.dying:
            return
        img = self.frame(atlas)
        x = round(self.x - cam) - img.get_width() // 2
        y = round(self.y) - img.get_height() + 1
        bob = 1 if self.run_t and int(self.run_t) % 2 else 0
        surf.blit(img, (x, y - bob))
        if self.dying:
            return
        # arm and gun, drawn toward the aim so all 8 directions read clearly
        ax, ay = self.aim
        n = math.hypot(ax, ay) or 1
        ux, uy = ax / n, ay / n
        kick = 2 if self.recoil else 0
        sx = round(self.x - cam + self.facing * 2 - ux * kick)
        sy = round(self.y - (9 if self.crouch else 15) - bob - uy * kick)
        length = {"P": 8, "H": 11, "S": 10, "R": 12}[self.weapon]
        ex, ey = sx + ux * length, sy + uy * length
        pygame.draw.line(surf, C["ink"], (sx, sy), (ex, ey), 4)
        pygame.draw.line(surf, C["steel_d"], (sx, sy), (ex, ey), 2)
        pygame.draw.line(surf, C["steel_l"], (sx + ux * 3, sy + uy * 3 - 1), (ex, ey - 1), 1)
        hand = {"P": C["steel"], "H": C["red"], "S": C["blue"], "R": C["olive"]}[self.weapon]
        surf.set_at((round(sx + ux * 3), round(sy + uy * 3)), hand)


# ------------------------------------------------------------------ projectiles

class Shot:
    """A player projectile. Rockets accelerate and burst."""

    def __init__(self, x, y, vx, vy, dmg, owner, kind):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.ox, self.oy = x, y
        self.dmg, self.owner, self.kind = dmg, owner, kind
        self.dead = False
        self.life = 90 if kind == "pellet" else 160

    def step(self, world):
        if self.kind == "rocket":
            self.vx *= 1.06
            self.vy *= 1.06
            sp = math.hypot(self.vx, self.vy)
            if sp > 6.5:
                self.vx, self.vy = self.vx / sp * 6.5, self.vy / sp * 6.5
            if world.frame % 2 == 0:
                world.smoke(self.x - self.vx, self.y - self.vy, 0.5)
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if (self.life <= 0 or not -10 < self.x - world.cam_x < W + 10 or not -10 < self.y < H + 10):
            self.dead = True
        elif world.stage.solid(int(self.x // TILE), int(self.y // TILE)):
            self.dead = True
            self.burst(world)

    def burst(self, world):
        if self.kind == "rocket":
            world.explode(self.x, self.y, 22, 6, self.owner)
        else:
            world.sparks(self.x, self.y, 3)
            audio.play("clank")

    def rect(self):
        return pygame.Rect(round(self.x) - 2, round(self.y) - 2, 4, 4)

    def draw(self, surf, cam):
        x, y = round(self.x - cam), round(self.y)
        if self.kind == "rocket":
            pygame.draw.line(surf, C["steel_l"], (x, y), (round(x - self.vx), round(y - self.vy)), 3)
            surf.set_at((x, y), C["white"])
        elif self.kind == "heavy":
            pygame.draw.line(surf, C["sun"], (x, y), (round(x - self.vx * 1.2), round(y - self.vy * 1.2)), 2)
            surf.set_at((x, y), C["white"])
        elif self.kind == "pellet":
            pygame.draw.circle(surf, C["cyan"], (x, y), 2)
            surf.set_at((x, y), C["white"])
        else:
            pygame.draw.line(surf, C["sun"], (x, y), (round(x - self.vx * 0.8), round(y - self.vy * 0.8)), 2)
            surf.set_at((x, y), C["white"])


class Bolt:
    """An enemy bullet: slow, round and bright, so it can be read and dodged."""

    def __init__(self, x, y, vx, vy, gravity=0.0, kind="bolt"):
        self.x, self.y, self.vx, self.vy, self.g, self.kind = x, y, vx, vy, gravity, kind
        self.ox, self.oy = x, y
        self.dead = False
        self.t = 0

    def step(self, world):
        self.t += 1
        self.vy += self.g
        self.x += self.vx
        self.y += self.vy
        if not -20 < self.x - world.cam_x < W + 20 or self.y > H + 10 or self.t > 600:
            self.dead = True
        elif world.stage.solid(int(self.x // TILE), int(self.y // TILE)):
            self.dead = True
            if self.kind in ("shell", "missile"):
                world.explode(self.x, self.y - 2, 20, 0, None, hurts_players=True)
            else:
                world.sparks(self.x, self.y, 2)

    def rect(self):
        r = 3 if self.kind in ("shell", "missile") else 2      # a pixel inside the picture: a graze is a miss
        return pygame.Rect(round(self.x) - r, round(self.y) - r, r * 2, r * 2)

    def draw(self, surf, cam, frame):
        x, y = round(self.x - cam), round(self.y)
        if self.kind == "shell":
            pygame.draw.circle(surf, C["ink"], (x, y), 4)
            pygame.draw.circle(surf, C["steel"], (x, y), 3)
            surf.set_at((x - 1, y - 1), C["white"])
        elif self.kind == "missile":
            pygame.draw.line(surf, C["ink"], (x, y - 9), (x, y), 4)
            pygame.draw.line(surf, C["steel_l"], (x, y - 9), (x, y - 1), 2)
            surf.set_at((x, y), C["red"])
        else:
            pygame.draw.circle(surf, C["red"] if frame % 6 < 3 else C["ember"], (x, y), 3)
            pygame.draw.circle(surf, C["sun"], (x, y), 1)


class Grenade(Body):
    w, h = 4, 4

    def __init__(self, x, y, vx, vy, owner):
        super().__init__(x, y)
        self.vx, self.vy, self.owner = vx, vy, owner
        self.fuse = 75
        self.bounces = 0

    def step(self, world):
        self.vy = min(MAX_FALL, self.vy + 0.2)
        hit_wall = self.vx
        if self.move(world.stage):
            self.bounces += 1
            self.vy = -2.0 / self.bounces
            self.vx *= 0.6
            audio.play("clank")
        if hit_wall and self.vx == 0:
            self.vx = -hit_wall * 0.5
        self.fuse -= 1
        if self.fuse <= 0 or self.bounces >= 3 or self.y > H:
            self.blow(world)

    def blow(self, world):
        self.dead = True
        world.explode(self.x, self.y - 4, 30, 8, self.owner)

    def draw(self, surf, cam):
        x, y = round(self.x - cam), round(self.y - 2)
        pygame.draw.circle(surf, C["ink"], (x, y), 3)
        pygame.draw.circle(surf, C["olive"], (x, y), 2)
        if self.fuse % 8 < 4:
            surf.set_at((x, y - 3), C["red"])


# ------------------------------------------------------------------ enemies

class Foe(Body):
    """A Rust Legion trooper. Rifles walk in and fire level; lobbers hold ground and arc shells."""
    w, h = 10, 21

    def __init__(self, x, y, kind="soldier"):
        super().__init__(x, y)
        self.kind = kind
        self.hp = 2 if kind == "soldier" else 3
        self.facing = -1
        self.timer = random.randint(40, 80)
        self.hurt = 0
        self.dying = 0
        self.run_t = 0.0
        self.aiming = 0
        self.stun = 0

    def step(self, world):
        if self.dying:
            self.dying -= 1
            self.vy = min(MAX_FALL, self.vy + GRAVITY)
            self.x += self.vx
            self.y += self.vy
            if self.dying == 0 or self.y > H + 30:
                self.dead = True
            return
        if self.hurt:
            self.hurt -= 1
        target = world.nearest(self.x)
        if self.stun:                                     # staggered by a hit: it slides back, and does nothing else
            self.stun -= 1
            self.vx *= 0.7
        elif target is None:
            self.vx = 0
        else:
            dx = target.x - self.x
            self.facing = 1 if dx > 0 else -1
            far = abs(dx) > (150 if self.kind == "soldier" else 220)
            on_screen = 0 < self.x - world.cam_x < W
            if self.kind == "soldier" and (far or not on_screen) and not self.aiming:
                ahead = self.x + self.facing * 8
                if world.stage.floor_y(ahead, self.y - 4) is not None and abs(world.stage.floor_y(ahead, self.y - 4) - self.y) < 20:
                    self.vx = self.facing * 0.9
                else:
                    self.vx = 0
            else:
                self.vx = 0
            self.timer -= 1
            if on_screen and self.timer <= 0 and not far:
                if not self.aiming:
                    self.aiming = world.windup        # a visible wind-up before every shot
                self.timer = random.randint(70, 120)
            if self.aiming:
                self.aiming -= 1
                if self.aiming % 8 == 4:                  # the muzzle glints: a shot is coming
                    world.flash(self.x + self.facing * 10, self.y - (19 if self.kind == "lobber" else 15), small=True)
                if self.aiming == 0:
                    self.fire(world, target)
        self.vy = min(MAX_FALL, self.vy + GRAVITY)
        self.move(world.stage)
        self.run_t = self.run_t + 0.11 if self.vx and not self.stun else 0
        if self.y > H + 20 or self.x < world.cam_x - 40:
            self.dead = True

    def fire(self, world, target):
        mx, my = self.x + self.facing * 10, self.y - 15
        if self.kind == "lobber":
            t = 52.0
            vx = max(-3.2, min(3.2, (target.x - mx) / t))
            world.bolts.append(Bolt(mx, my - 4, vx, -0.5 * 0.16 * t, 0.16, "shell"))
        else:
            world.bolts.append(Bolt(mx, my, self.facing * ENEMY_BULLET_V * world.fire, 0))
        world.flash(mx, my, small=True)
        audio.play("enemy_shot")

    def damage(self, dmg, world, owner, push=0.0):
        if self.dying:
            return False
        self.hp -= dmg
        self.hurt = 4
        if self.hp <= 0:
            self.dying = 50
            self.vx = push * 1.4 or -self.facing * 1.2
            self.vy = -3.0
            world.award(owner, SCORE[self.kind], self.x, self.y - 24)
            world.sparks(self.x, self.y - 12, 6)
            world.hitstop(1)                              # a common kill: one frame, or a firefight stutters
            audio.play("hurt")
        else:
            self.stun, self.aiming, self.vx = 8, 0, push * 1.5     # a hit staggers: knocked back, the wind-up lost
        return True

    def draw(self, surf, atlas, cam):
        right = self.facing > 0
        frames = (atlas.foe if right else atlas.foe_l) if self.kind == "soldier" else \
                 (atlas.lobber if right else atlas.lobber_l)
        if self.dying:
            img = frames["jump"]
            if (self.dying // 4) % 2:
                return
        elif self.run_t:
            img = frames["run%d" % (int(self.run_t) % 4)]
        else:
            img = frames["stand"]
        if self.hurt:
            img = atlas.flash(img)
        x = round(self.x - cam) - img.get_width() // 2
        y = round(self.y) - img.get_height() + 1
        surf.blit(img, (x, y))
        if not self.dying:
            sx, sy = round(self.x - cam + self.facing * 2), round(self.y - 15)
            lift = -4 if self.kind == "lobber" and self.aiming else 0
            pygame.draw.line(surf, C["ink"], (sx, sy), (sx + self.facing * 9, sy + lift), 4)
            pygame.draw.line(surf, C["steel_d"], (sx, sy), (sx + self.facing * 9, sy + lift), 2)
            if self.aiming and self.aiming % 6 < 3:
                surf.set_at((sx + self.facing * 10, sy + lift), C["red"])


class Drone(Body):
    w, h = 16, 9

    def __init__(self, x, y):
        super().__init__(x, y)
        self.hp = 3
        self.t = random.random() * 6
        self.home = y
        self.timer = 90
        self.hurt = 0

    def step(self, world):
        self.t += 0.06
        if self.hurt:
            self.hurt -= 1
        target = world.nearest(self.x)
        aim_x = target.x + 30 * math.sin(self.t * 0.7) if target else self.x - 1
        self.vx += max(-0.05, min(0.05, (aim_x - self.x) * 0.004))
        self.vx = max(-1.4, min(1.4, self.vx * 0.98))
        self.x += self.vx
        self.y = self.home + 6 * math.sin(self.t * 2)
        self.timer -= 1
        if target and self.timer <= 0 and abs(target.x - self.x) < 24 and 0 < self.x - world.cam_x < W:
            world.bolts.append(Bolt(self.x, self.y + 2, self.vx * 0.5, 0.5, 0.12, "bolt"))
            self.timer = 80
            audio.play("enemy_shot")
        if self.x < world.cam_x - 60:
            self.dead = True

    def damage(self, dmg, world, owner, push=0.0):
        self.hp -= dmg
        self.hurt = 4
        if self.hp <= 0:
            self.dead = True
            world.award(owner, SCORE["drone"], self.x, self.y - 10)
            world.explode(self.x, self.y - 4, 14, 0, owner)
            world.hitstop(1)
        return True

    def draw(self, surf, atlas, cam):
        img = atlas.drone[(int(self.t * 10)) % 2]
        if self.hurt:
            img = atlas.flash(img)
        surf.blit(img, (round(self.x - cam) - img.get_width() // 2, round(self.y) - img.get_height()))


class Turret(Body):
    w, h = 16, 14

    def __init__(self, x, y):
        super().__init__(x, y)
        self.hp = 10
        self.angle = math.pi
        self.timer = 60
        self.hurt = 0

    def step(self, world):
        if self.hurt:
            self.hurt -= 1
        target = world.nearest(self.x)
        if target is None or not -8 < self.x - world.cam_x < W + 8:
            return
        want = math.atan2((target.y - 12) - (self.y - 10), target.x - self.x)
        diff = (want - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-0.03, min(0.03, diff))
        self.timer -= 1
        c, s = math.cos(self.angle), math.sin(self.angle)
        if self.timer in (18, 12, 6):                     # the barrel glints before it fires
            world.flash(self.x + c * 12, self.y - 10 + s * 12, small=True)
        if self.timer <= 0:
            self.timer = 80
            world.bolts.append(Bolt(self.x + c * 12, self.y - 10 + s * 12, c * 1.7 * world.fire, s * 1.7 * world.fire))
            world.flash(self.x + c * 12, self.y - 10 + s * 12, small=True)
            audio.play("enemy_shot")
        if self.x < world.cam_x - 40:
            self.dead = True

    def damage(self, dmg, world, owner, push=0.0):
        self.hp -= dmg
        self.hurt = 4
        if self.hp <= 0:
            self.dead = True
            world.award(owner, SCORE["turret"], self.x, self.y - 20)
            world.explode(self.x, self.y - 8, 24, 0, owner)
            world.hitstop(5)
        return True

    def draw(self, surf, atlas, cam):
        x, y = round(self.x - cam), round(self.y)
        body = C["white"] if self.hurt else C["steel_d"]
        c, s = math.cos(self.angle), math.sin(self.angle)
        pygame.draw.line(surf, C["ink"], (x, y - 10), (x + c * 13, y - 10 + s * 13), 5)
        pygame.draw.line(surf, C["steel"], (x, y - 10), (x + c * 12, y - 10 + s * 12), 3)
        pygame.draw.rect(surf, C["ink"], (x - 9, y - 7, 18, 7))
        pygame.draw.rect(surf, C["rust"], (x - 8, y - 6, 16, 6))
        pygame.draw.circle(surf, C["ink"], (x, y - 10), 7)
        pygame.draw.circle(surf, body, (x, y - 10), 6)
        pygame.draw.circle(surf, C["steel_l"] if not self.hurt else C["white"], (x - 2, y - 12), 2)
        surf.set_at((x + round(c * 3), y - 10 + round(s * 3)), C["red"])


# ------------------------------------------------------------------ hostages, pickups

class Hostage(Body):
    w, h = 12, 14

    def __init__(self, x, y, gift):
        super().__init__(x, y)
        self.gift = gift
        self.freed = 0

    def step(self, world):
        if self.freed:
            self.freed += 1
            if self.freed > 50:
                self.vx = -1.6
            self.vy = min(MAX_FALL, self.vy + GRAVITY)
            if self.freed < 50 and self.on_ground and self.freed % 16 == 0:
                self.vy = -2.5                                        # jumping for joy
            self.move(world.stage)
            if self.x < world.cam_x - 20:
                self.dead = True

    def free(self, world, by):
        if self.freed:
            return
        self.freed = 1
        world.hostages_freed += 1
        world.award(by, SCORE["hostage"], self.x, self.y - 22, "THANK YOU!")
        world.pickups.append(Pickup(self.x + 6, self.y - 10, self.gift))
        audio.play("free")

    def draw(self, surf, atlas, cam):
        img = atlas.hostage[1 if self.freed else 0]
        if self.freed > 50 and (self.freed // 6) % 2:
            img = pygame.transform.flip(img, True, False)
        surf.blit(img, (round(self.x - cam) - img.get_width() // 2, round(self.y) - img.get_height() + 1))


class Pickup(Body):
    w, h = 12, 10

    def __init__(self, x, y, kind):
        super().__init__(x, y)
        self.kind = kind
        self.vy = -2.5
        self.t = 0

    def step(self, world):
        self.t += 1
        self.vy = min(MAX_FALL, self.vy + 0.18)
        self.move(world.stage)
        if self.x < world.cam_x - 20 or self.y > H + 20:
            self.dead = True

    def apply(self, p):
        if self.kind in WEAPONS:
            if p.weapon == self.kind:
                p.ammo += WEAPONS[self.kind][1]
            else:
                p.weapon, p.ammo = self.kind, WEAPONS[self.kind][1]
        elif self.kind == "B":
            p.grenades += 10
        elif self.kind == "1":
            p.lives += 1
        self.dead = True
        audio.play("pickup")

    def draw(self, surf, atlas, cam):
        img = atlas.caps[self.kind]
        bob = round(math.sin(self.t * 0.15)) if self.on_ground else 0
        surf.blit(img, (round(self.x - cam) - 7, round(self.y) - 12 + bob))


# ------------------------------------------------------------------ the boss

class Bastion(Body):
    """BASTION, a tracked siege engine: a mortar on top, a chin gun, and missiles once it is angry."""
    w, h = 84, 50
    HP = 150

    def __init__(self, x, y, left, right):
        super().__init__(x, y)
        self.hp = self.HP
        self.left, self.right = left, right
        self.state = "enter"
        self.t = 0
        self.tread = 0.0
        self.goal = right - 70
        self.hurt = 0
        self.dying = 0
        self.gun_angle = math.pi
        self.burst = 0
        self.marks = []                       # (x, frames until the missile falls)

    @property
    def angry(self):
        return self.hp <= self.HP // 2

    def step(self, world):
        self.t += 1
        if self.hurt:
            self.hurt -= 1
        if self.dying:
            self.dying -= 1
            if self.dying % 7 == 0:
                world.explode(self.x + random.uniform(-40, 40), self.y - random.uniform(5, 50), 18, 0, None)
            if self.dying == 1:
                world.explode(self.x, self.y - 25, 60, 0, None, big=True)
                self.dead = True
            return
        if self.angry and self.t % 5 == 0:
            world.smoke(self.x + random.uniform(-30, 30), self.y - random.uniform(30, 45), 1.0)
        speed = 0.6 if not self.angry else 1.0
        if self.state == "enter":
            self.x -= 0.8
            self.tread -= 0.8
            if self.x <= self.goal:
                self.state = "fight"
                self.t = 0
            return
        if abs(self.goal - self.x) < 2:                  # it roams its own side: the player always keeps room to dodge
            self.goal = random.uniform(self.left + (130 if self.angry else 160), self.right - 50)
        step = max(-speed, min(speed, self.goal - self.x))
        self.x += step
        self.tread += step
        target = world.nearest(self.x)
        if target is None:
            return
        want = math.atan2((target.y - 10) - (self.y - 18), target.x - (self.x - 40))
        self.gun_angle += max(-0.04, min(0.04, (want - self.gun_angle + math.pi) % (2 * math.pi) - math.pi))
        # mortar; once angry it alternates with the missiles, so that one blast lands at a time
        if self.t % 150 == 110 if self.angry else self.t % 110 == 0:
            for spread in ((0,) if not self.angry else (-30, 0, 30)):
                t = 60.0
                vx = (target.x + spread - (self.x + 10)) / t
                world.bolts.append(Bolt(self.x + 10, self.y - 58, vx, -0.5 * 0.14 * t, 0.14, "shell"))
            world.flash(self.x + 10, self.y - 58)
            audio.play("rocket")
            world.shake = max(world.shake, 4)
        beat = self.t % 190
        if 65 <= beat < 95 and beat % 6 == 5:            # the chin gun glints for half a second before a burst
            world.flash(self.x - 40 + math.cos(self.gun_angle) * 12, self.y - 18 + math.sin(self.gun_angle) * 12,
                        small=True)
        if beat == 95:
            self.burst = 8
        if self.burst and self.t % 6 == 0:                # chin gun burst
            self.burst -= 1
            c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
            gx, gy = self.x - 40 + c * 12, self.y - 18 + s * 12
            world.bolts.append(Bolt(gx, gy, c * 2.2 * world.fire, s * 2.2 * world.fire))
            world.flash(gx, gy, small=True)
            audio.play("enemy_shot")
        if self.angry and self.t % 150 == 40:
            for off in (-48, 0, 48):                     # far enough apart to stand between two
                self.marks.append([target.x + off, 50])
            audio.play("alarm")
        for m in self.marks:
            m[1] -= 1
            if m[1] == 0:
                world.bolts.append(Bolt(m[0], -10, 0, 4.0, 0.0, "missile"))
        self.marks = [m for m in self.marks if m[1] > -47]     # a mark stays lit until its missile lands

    def damage(self, dmg, world, owner, push=0.0):
        if self.dying or self.state == "enter":
            return True
        calm = not self.angry
        self.hp -= dmg
        self.hurt = 3
        if self.hp <= 0:
            self.dying = 150
            world.award(owner, SCORE["boss"], self.x, self.y - 60)
            world.boss_down()
        elif calm and self.angry:                        # it breaks: a beat to see that the fight has changed
            self.t = self.burst = 0
            world.explode(self.x, self.y - 30, 20, 0, None)
            world.hitstop(8)
            world.shake = max(world.shake, 10)
            audio.play("alarm")
        return True

    def hitbox(self):
        return pygame.Rect(round(self.x - 42), round(self.y - 50), 84, 50)

    def draw(self, surf, atlas, cam):
        x, y = round(self.x - cam), round(self.y)
        hot = self.hurt and self.hurt % 2
        hull = C["white"] if hot else C["steel_d"]
        armour = C["white"] if hot else C["rust"]
        ink = C["ink"]
        # treads
        pygame.draw.rect(surf, ink, (x - 46, y - 16, 92, 16), border_radius=7)
        pygame.draw.rect(surf, C["steel_d"], (x - 44, y - 14, 88, 12), border_radius=6)
        for i in range(-40, 44, 8):
            tx = x + i + int(self.tread) % 8
            if x - 44 < tx < x + 44:
                pygame.draw.line(surf, ink, (tx, y - 14), (tx, y - 3))
        for wx in range(-34, 40, 17):
            pygame.draw.circle(surf, ink, (x + wx, y - 8), 5)
            pygame.draw.circle(surf, C["steel"], (x + wx, y - 8), 4)
            pygame.draw.circle(surf, ink, (x + wx, y - 8), 1)
        # hull
        hull_pts = [(x - 48, y - 16), (x - 40, y - 38), (x + 30, y - 40), (x + 46, y - 26), (x + 44, y - 16)]
        pygame.draw.polygon(surf, ink, [(px + (1 if px > x else -1), py + 1) for px, py in hull_pts])
        pygame.draw.polygon(surf, armour, hull_pts)
        pygame.draw.line(surf, C["ember"] if not hot else C["white"], (x - 40, y - 37), (x + 30, y - 39))
        for rx in range(-36, 40, 10):
            surf.set_at((x + rx, y - 20), C["sun"])
        pygame.draw.rect(surf, hull, (x - 30, y - 34, 40, 12))
        pygame.draw.rect(surf, ink, (x - 30, y - 34, 40, 12), 1)
        for i in range(4):                               # vents
            pygame.draw.line(surf, ink, (x - 26 + i * 9, y - 31), (x - 26 + i * 9, y - 25))
        # chin gun
        c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
        gx, gy = x - 40, y - 18
        pygame.draw.line(surf, ink, (gx, gy), (gx + c * 13, gy + s * 13), 5)
        pygame.draw.line(surf, C["steel_l"], (gx, gy), (gx + c * 12, gy + s * 12), 2)
        pygame.draw.circle(surf, ink, (gx, gy), 5)
        pygame.draw.circle(surf, hull, (gx, gy), 4)
        # mortar turret
        pygame.draw.rect(surf, ink, (x - 6, y - 54, 32, 16), border_radius=4)
        pygame.draw.rect(surf, hull, (x - 5, y - 53, 30, 14), border_radius=3)
        pygame.draw.line(surf, ink, (x + 6, y - 54), (x + 14, y - 66), 7)
        pygame.draw.line(surf, C["steel"], (x + 6, y - 54), (x + 14, y - 66), 4)
        # the core: pulses faster as it breaks
        rate = 12 if not self.angry else 5
        core = C["cyan"] if (self.t // rate) % 2 else C["white"]
        pygame.draw.circle(surf, ink, (x + 34, y - 30), 5)
        pygame.draw.circle(surf, core, (x + 34, y - 30), 4)
        for mx, frames in self.marks:                    # missile warnings: a slow blink, a fast one as it falls
            if frames % 8 < 5 if frames > 0 else frames % 4 < 2:
                px = round(mx - cam)
                pygame.draw.line(surf, C["red"], (px - 4, y - 2), (px + 4, y - 2))
                pygame.draw.polygon(surf, C["red"], [(px, y - 4), (px - 3, y - 9), (px + 3, y - 9)])
