"""Everything that moves. Positions are floats (sub-pixel); x is the centre, y is the feet (bottom edge).

Body.move() is the one collision routine: axis by axis against the tile grid, with one-way catwalks.
"""

import math
import random

import pygame

from . import audio
from .settings import (BULLET_V, ENEMY_BULLET_V, GRAVITY, GRENADES, JUMP_V, LIVES, MAX_FALL, RESPAWN_SAFE, RUN,
                       GROUND_Y, SCORE, TILE, WEAPONS, C, H, W)
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
SLIDE, SLIDE_V, SLIDE_DRAG = 22, 3.2, 0.95  # down + jump on solid ground: a low dash under rifle fire
KNIFE_REACH, KNIFE_DMG, KNIFE_RATE = 18, 3, 14   # fire with a foe this close: a stab that downs any trooper
SAPPER_FUSE = 40                           # frames from a sapper lighting up beside you to the blast: time to knife it
STOMP_DMG, STOMP_BOUNCE = 2, -4.6          # landing on a foe's head; hold jump to bounce high


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
        self.slide = self.slash = 0    # frames left in a slide, and of the knife's swipe on screen
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
        if self.slide:
            self.slide -= 1
            self.vx *= SLIDE_DRAG
            if not self.on_ground or not self.vx:      # off a ledge or into a wall: over
                self.slide = 0
            elif not self.slide and not self.room_to_stand(world.stage):
                self.slide = 1                          # never stand up under a ceiling too low for it
            self.crouch = self.crouch or bool(self.slide)
        if dx and not self.slide:
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
        if not self.slide:
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
        if self.buffer and self.crouch and not self.slide and self.on_catwalk(world.stage):
            self.drop, self.buffer, self.coyote, self.on_ground = 10, 0, 0, False   # down + jump: through a catwalk
        elif self.buffer and self.crouch and not self.slide and self.on_ground:
            self.slide, self.vx, self.buffer = SLIDE, self.facing * SLIDE_V, 0      # down + jump on solid ground
            world.dust(self.x, self.y)
            audio.play("land")
        elif self.buffer and self.coyote:
            self.slide = 0                              # a jump out of a slide keeps its speed
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
        self.slash = max(0, self.slash - 1)
        rate = WEAPONS[self.weapon][0]
        # a tap fires once half the wait is over (mashing beats holding); a held button keeps the weapon's beat
        if (self.trigger and self.cooldown <= rate // 2) or (pad.held("fire") and not self.cooldown):
            self.trigger = 0
            foe = self.in_reach(world)
            if foe:
                self.stab(foe, world)
                rate = KNIFE_RATE
            else:
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

    def room_to_stand(self, stage):
        h, self.h = self.h, STAND
        free = not self.blocked(stage, self.y)
        self.h = h
        return free

    def in_reach(self, world):
        """The foe a knife would reach: in front, at body height. Not the boss: a blade is no answer to a tank."""
        x0 = self.x if self.facing > 0 else self.x - KNIFE_REACH
        box = pygame.Rect(round(x0), round(self.y - STAND), KNIFE_REACH, STAND)
        return next((e for e in world.foes if not getattr(e, "dying", 0) and box.colliderect(e.rect())), None)

    def stab(self, foe, world):
        foe.damage(KNIFE_DMG, world, self, push=self.facing)
        self.slash = 8
        world.sparks(foe.x - self.facing * 3, self.y - 13, 5)
        world.hitstop(3)                                # a blow that lands: the world holds its breath
        world.feel(self, "heavy")
        audio.play("slash")

    def stomp(self, foe, world):
        foe.damage(STOMP_DMG, world, self)
        self.vy, self.coyote, self.slide = STOMP_BOUNCE, 0, 0
        world.dust(self.x, self.y)
        world.hitstop(2)
        world.feel(self, "land")
        audio.play("hit")

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
        if self.dying:
            return frames["down" if self.on_ground else "hurt"]
        if self.slide:
            return frames["slide"]
        if self.crouch:
            return frames["crouch"]
        up = "" if self.aim[1] >= 0 else "u" if self.aim[0] else "U"      # the head tilts back to aim up
        if not self.on_ground:
            return frames[("jump" if self.vy < 0 else "fall") + up]
        if self.run_t:
            return frames["run%d" % (int(self.run_t * 2.4) % 8) + up]     # a frame every 3.5 px: boots do not skate
        return frames["stand" + up]

    def draw(self, surf, atlas, cam):
        if self.out or (self.safe and (self.safe // 3) % 2) and not self.dying:
            return
        img = self.frame(atlas)
        x, y = round(self.x - cam), round(self.y)
        surf.blit(img, (x - img.get_width() // 2, y - img.get_height() + 1))
        if self.dying:
            return
        # the hands: 15 px up (9 in a crouch), riding the stride's rise and dip. What they hold points along the aim.
        ax, ay = self.aim
        n = math.hypot(ax, ay) or 1
        hx = x + (2 if self.facing > 0 else -3)         # the same pixel of the body, facing either way
        hy = y - (9 if self.crouch else 15 + img.get_height() - atlas.tall)
        if self.slash:                                  # the knife: a thrust, and a bright arc that fades
            held = atlas.knife[self.index][self.facing, 0, self.facing]
            hx += self.facing * (0, 1, 2, 3, 4, 5, 5, 4)[self.slash - 1]
            r = pygame.Rect(x + self.facing * 6 - 10, hy - 10, 20, 20)
            a = 0 if self.facing > 0 else math.pi
            sweep = 1.4 * (8 - self.slash) / 8 + 0.4
            pygame.draw.arc(surf, C["white"] if self.slash > 4 else C["steel_l"], r, a - sweep / 2, a + sweep / 2, 2)
        else:
            held = atlas.guns[self.weapon][ax, ay, ax or self.facing]
            kick = 2 if self.recoil else 0
            hx, hy = hx - round(ax / n * kick), hy - round(ay / n * kick)
        surf.blit(held, (hx - held.get_width() // 2, hy - held.get_height() // 2))


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
        if self.kind == "wave":                                 # low and wide: a jump clears it, a crouch does not
            return pygame.Rect(round(self.x) - 4, round(self.y) - 5, 8, 8)
        r = 3 if self.kind in ("shell", "missile") else 2      # a pixel inside the picture: a graze is a miss
        return pygame.Rect(round(self.x) - r, round(self.y) - r, r * 2, r * 2)

    def draw(self, surf, cam, frame):
        x, y = round(self.x - cam), round(self.y)
        if self.kind == "shell":
            pygame.draw.circle(surf, C["ink"], (x, y), 4)
            pygame.draw.circle(surf, C["steel"], (x, y), 3)
            surf.set_at((x - 1, y - 1), C["white"])
        elif self.kind == "wave":
            for k in range(3):                                  # three crackling forks, redrawn every frame
                h = 3 + (frame * 7 + k * 5) % 6
                pygame.draw.line(surf, C["cyan"], (x - 4 + k * 4, y + 2), (x - 3 + k * 3, y + 2 - h))
            pygame.draw.line(surf, C["white"], (x - 5, y + 2), (x + 5, y + 2))
            surf.set_at((x, y - 3 - frame % 3), C["white"])
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
    """A Rust Legion trooper. Rifles walk in and fire level; lobbers hold ground and arc shells; shields walk in
    behind a riot shield that stops level shots, and lower it for a moment to fire. Sappers carry no gun: they run
    at you with a satchel charge and light it up close, so shoot them early or knife them before the fuse burns.
    Guards, Graive's own, wear his red plate, take three hits and fire their rifles two shots at a time."""
    w, h = 10, 21

    def __init__(self, x, y, kind="soldier"):
        super().__init__(x, y)
        self.kind = kind
        self.hp = {"soldier": 2, "lobber": 3, "shield": 4, "sapper": 1, "guard": 3}[kind]
        self.facing = -1
        self.timer = random.randint(40, 80)
        self.hurt = 0
        self.dying = 0
        self.run_t = 0.0
        self.aiming = 0
        self.stun = 0
        self.fuse = 0

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
        elif self.kind == "sapper":
            self.charge(world, target)
        else:
            dx = target.x - self.x
            self.facing = 1 if dx > 0 else -1
            far = abs(dx) > (150 if self.kind == "soldier" else 220)
            on_screen = 0 < self.x - world.cam_x < W
            if self.kind != "lobber" and (far or not on_screen) and not self.aiming:
                ahead = self.x + self.facing * 8
                if world.stage.floor_y(ahead, self.y - 4) is not None and abs(world.stage.floor_y(ahead, self.y - 4) - self.y) < 20:
                    self.vx = self.facing * (0.6 if self.kind == "shield" else 0.9)
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

    def charge(self, world, target):
        """A sapper runs straight in; up close it stops and lights the fuse, and the charge goes off where it stands."""
        if self.fuse:
            self.fuse -= 1
            self.vx = 0
            if self.fuse % 6 == 0:
                audio.play("fuse")
            if self.fuse == 0:
                self.dead, self.dying = True, 1            # gone in its own blast, which then skips it
                world.explode(self.x, self.y - 10, 24, 0, None, hurts_players=True)
            return
        dx = target.x - self.x
        self.facing = 1 if dx > 0 else -1
        if abs(dx) < 16 and abs(target.y - self.y) < 24:
            self.fuse = SAPPER_FUSE
            return
        ahead = self.x + self.facing * 8
        floor = world.stage.floor_y(ahead, self.y - 4)
        self.vx = self.facing * 1.45 if floor is not None and abs(floor - self.y) < 20 else 0

    def fire(self, world, target):
        mx, my = self.x + self.facing * 10, self.y - 15
        if self.kind == "lobber":
            t = 52.0
            vx = max(-3.2, min(3.2, (target.x - mx) / t))
            world.bolts.append(Bolt(mx, my - 4, vx, -0.5 * 0.16 * t, 0.16, "shell"))
        elif self.kind == "guard":                        # two shots, fanned: one flies level, one dips
            for vy in (0.0, 0.35):
                world.bolts.append(Bolt(mx, my, self.facing * ENEMY_BULLET_V * world.fire, vy))
        else:
            world.bolts.append(Bolt(mx, my, self.facing * ENEMY_BULLET_V * world.fire, 0))
        world.flash(mx, my, small=True)
        audio.play("enemy_shot")

    def blocks(self, shot):
        """The shield stops a level shot at its face, but not one from behind or above, nor while it fires."""
        if 0 < self.aiming < 12:
            return False
        return shot.vx * self.facing < 0 and abs(shot.vy) < abs(shot.vx)

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
        frames = {"lobber": (atlas.lobber, atlas.lobber_l), "shield": (atlas.riot, atlas.riot_l),
                  "sapper": (atlas.sapper, atlas.sapper_l), "guard": (atlas.guard, atlas.guard_l)}.get(
            self.kind, (atlas.foe, atlas.foe_l))[not right]
        if self.dying and (self.dying // 4) % 2:
            return
        if self.dying or self.stun:
            img = frames["hurt"]                          # knocked off its feet, or back on its heels
        elif self.run_t:
            img = frames["run%d" % (int(self.run_t * 2.4) % 8)]
        else:
            img = frames["stand"]
        x, y = round(self.x - cam), round(self.y)
        surf.blit(atlas.flash(img) if self.hurt else img, (x - img.get_width() // 2, y - img.get_height() + 1))
        if self.kind == "sapper":
            if self.fuse and not self.dying and self.fuse % 6 < 3:            # the lit fuse on the satchel, faster as it burns down
                surf.set_at((x - self.facing * 5, y - 17), C["sun"])
                surf.set_at((x - self.facing * 5, y - 18), C["white"])
        elif not self.dying and not self.stun:
            lift = self.kind == "lobber" and self.aiming      # a grenadier raises the tube to lob
            gun = (atlas.tube if self.kind == "lobber" else atlas.rifle)[self.facing, -1 if lift else 0, self.facing]
            sx, sy = x + (2 if right else -3), y - 15 - (img.get_height() - atlas.tall)
            surf.blit(gun, (sx - gun.get_width() // 2, sy - gun.get_height() // 2))
            if self.aiming and self.aiming % 6 < 3:
                surf.set_at((sx + self.facing * 9, sy - (4 if lift else 0)), C["red"])
        if self.kind == "shield" and not self.dying:
            img = atlas.shield[0 < self.aiming < 12, self.facing]      # lowered to the ground while it fires
            surf.blit(img, (x + 3 if right else x - 3 - img.get_width(), y - 24))


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
        img = atlas.drone[int(self.t * 10) % len(atlas.drone)]
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
        base, dome = atlas.turret
        c, s = math.cos(self.angle), math.sin(self.angle)
        surf.blit(base, (x - base.get_width() // 2, y - base.get_height() + 1))
        pygame.draw.line(surf, C["ink"], (x, y - 10), (x + c * 13, y - 10 + s * 13), 5)
        pygame.draw.line(surf, C["steel"], (x, y - 10), (x + c * 12, y - 10 + s * 12), 3)
        pygame.draw.line(surf, C["steel_l"], (x, y - 11), (x + c * 12, y - 11 + s * 12))
        dome = atlas.flash(dome) if self.hurt else dome
        surf.blit(dome, (x - dome.get_width() // 2, y - 10 - dome.get_height() // 2))
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

    def draw(self, surf, atlas, cam, frame=0):
        if self.freed > 50:
            name = "run%d" % (self.freed // 2 % 8)            # off to the left, arms in the air
        elif self.freed:
            name = "cheer%d" % (self.freed // 8 % 2)
        else:
            name = "bound0" if frame // 8 % 8 else "bound1"   # now and then he pulls at the ropes
        img = atlas.hostage[name]
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
        ink = C["ink"]
        img = atlas.bastion[self.angry]                  # once it breaks, the cracked hull
        surf.blit(atlas.flash(img) if self.hurt and self.hurt % 2 else img, (x - 53, y - 71))
        for i in range(-40, 44, 8):                      # the tread's links crawl with it
            tx = x + i + int(self.tread) % 8
            if x - 42 < tx < x + 42:
                pygame.draw.line(surf, ink, (tx, y - 15), (tx, y - 13))
                pygame.draw.line(surf, ink, (tx, y - 3), (tx, y - 1))
        # chin gun
        c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
        gx, gy = x - 40, y - 18
        pygame.draw.line(surf, ink, (gx, gy), (gx + c * 13, gy + s * 13), 5)
        pygame.draw.line(surf, C["steel"], (gx, gy), (gx + c * 12, gy + s * 12), 3)
        pygame.draw.line(surf, C["steel_l"], (gx, gy - 1), (gx + c * 12, gy + s * 12 - 1))
        pygame.draw.circle(surf, ink, (gx, gy), 3)
        pygame.draw.circle(surf, C["steel"], (gx, gy), 2)
        # the core: pulses faster as it breaks
        rate = 12 if not self.angry else 5
        core = C["cyan"] if (self.t // rate) % 2 else C["white"]
        pygame.draw.circle(surf, core, (x + 34, y - 30), 4 if self.angry else 3)
        if not self.angry:                               # still behind its grille
            pygame.draw.line(surf, ink, (x + 31, y - 30), (x + 37, y - 30))
        for mx, frames in self.marks:                    # missile warnings: a slow blink, a fast one as it falls
            if frames % 8 < 5 if frames > 0 else frames % 4 < 2:
                px = round(mx - cam)
                pygame.draw.line(surf, C["red"], (px - 4, y - 2), (px + 4, y - 2))
                pygame.draw.polygon(surf, C["red"], [(px, y - 4), (px - 3, y - 9), (px + 3, y - 9)])


class Warden(Body):
    """WARDEN, the prisoner line's armoured engine: a roof gun, and a charge down the track when its whistle
    blows. Climb a gantry, or jump it. Once broken it charges faster and drops troopers from its back door."""
    w, h = 100, 40
    HP = 150

    def __init__(self, x, y, left, right):
        super().__init__(x, y)
        self.hp = self.HP
        self.left, self.right = left, right
        self.home = right - 66
        self.state = "enter"
        self.mode, self.mt = "idle", 0          # idle, whistle, charge, brake, back
        self.t = self.hurt = self.dying = self.burst = 0
        self.speed = self.wheel = 0.0
        self.gun_angle = math.pi
        self.marks = []                         # none: World.boss_down clears every boss's

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
                world.explode(self.x + random.uniform(-45, 45), self.y - random.uniform(5, 40), 18, 0, None)
            if self.dying == 1:
                world.explode(self.x, self.y - 20, 60, 0, None, big=True)
                self.dead = True
            return
        x0 = self.x
        if self.angry and self.t % 6 == 0:
            world.smoke(self.x + random.uniform(-40, 40), self.y - 40, 1.0)
        if self.state == "enter":
            self.x = max(self.home, self.x - 1.2)
            if self.x == self.home:
                self.state, self.t = "fight", 0
            self.wheel += self.x - x0
            return
        self.mt += 1
        if self.mode == "idle" and self.mt > (190 if self.angry else 260):
            self.mode, self.mt = "whistle", 0
            audio.play("whistle")
        elif self.mode == "whistle":
            if self.mt % 4 == 0:
                world.smoke(self.x - 30, self.y - 48, 1.2)    # steam from the stack: it is coming
            if self.mt >= 55:
                self.mode, self.mt, self.speed = "charge", 0, 0.0
        elif self.mode == "charge":
            self.speed = min(5.0 if self.angry else 4.0, self.speed + 0.2)
            self.x -= self.speed
            if world.frame % 2 == 0:
                world.sparks(self.x - 30 + random.uniform(-20, 50), self.y - 2, 1)
            if self.x - self.w / 2 <= self.left + 4:
                self.x = self.left + 4 + self.w / 2
                self.mode, self.mt = "brake", 0
                world.shake = max(world.shake, 8)
                world.explode(self.x - 50, self.y - 20, 14, 0, None)
                audio.play("rocket")
        elif self.mode == "brake" and self.mt > 45:
            self.mode, self.mt = "back", 0
        elif self.mode == "back":
            self.x = min(self.home, self.x + 1.1)
            if self.x == self.home:
                self.mode, self.mt = "idle", 0
        self.wheel += self.x - x0
        target = world.nearest(self.x)
        if target is None:
            return
        gx, gy = self.x - 8, self.y - 44
        want = math.atan2((target.y - 12) - gy, target.x - gx)
        self.gun_angle += max(-0.05, min(0.05, (want - self.gun_angle + math.pi) % (2 * math.pi) - math.pi))
        period = 95 if self.angry else 125
        beat = self.t % period
        if self.mode != "charge":
            if period - 40 <= beat < period - 16 and beat % 6 == 0:     # the roof gun glints before a burst
                world.flash(gx + math.cos(self.gun_angle) * 12, gy + math.sin(self.gun_angle) * 12, small=True)
            if beat == period - 16:
                self.burst = 5 if self.angry else 3
        if self.burst and self.t % 7 == 0:
            self.burst -= 1
            c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
            world.bolts.append(Bolt(gx + c * 12, gy + s * 12, c * 2.2 * world.fire, s * 2.2 * world.fire))
            world.flash(gx + c * 12, gy + s * 12, small=True)
            audio.play("enemy_shot")
        if (self.angry and self.mode == "idle" and self.t % 240 == 120
                and sum(isinstance(f, Foe) for f in world.foes) < 2):
            trooper = Foe(self.x + self.w / 2 - 6, self.y, "soldier")   # out of the back door
            trooper.vy = -2.5
            world.foes.append(trooper)

    def damage(self, dmg, world, owner, push=0.0):
        if self.dying or self.state == "enter":
            return True
        calm = not self.angry
        self.hp -= dmg
        self.hurt = 3
        if self.hp <= 0:
            self.dying = 150
            world.award(owner, SCORE["boss"], self.x, self.y - 50)
            world.boss_down()
        elif calm and self.angry:                        # its armour splits: a beat to see that the fight has changed
            world.explode(self.x, self.y - 25, 20, 0, None)
            world.hitstop(8)
            world.shake = max(world.shake, 10)
            audio.play("alarm")
        return True

    def hitbox(self):
        return pygame.Rect(round(self.x - self.w / 2), round(self.y - self.h), self.w, self.h)

    def draw(self, surf, atlas, cam):
        x, y = round(self.x - cam), round(self.y)
        img = atlas.warden[self.angry]                   # once it breaks, the split armour
        surf.blit(atlas.flash(img) if self.hurt and self.hurt % 2 else img,
                  (x - img.get_width() // 2, y - img.get_height()))
        ink = C["ink"]
        a = self.wheel / 6                               # the wheels turn with the distance rolled, all in step
        c, s = math.cos(a), math.sin(a)
        for wx in (-36, -16, 16, 36):
            cx, cy = x + wx, y - 6
            pygame.draw.circle(surf, ink, (cx, cy), 6)
            pygame.draw.circle(surf, C["steel"], (cx, cy), 5)        # the tyre
            pygame.draw.circle(surf, C["steel_d"], (cx, cy), 4)
            for dx, dy in ((c, s), (-s, c)):             # two spokes, square to each other
                pygame.draw.line(surf, C["steel"], (cx - round(dx * 4), cy - round(dy * 4)),
                                 (cx + round(dx * 4), cy + round(dy * 4)))
            surf.set_at((cx, cy), ink)
        px, py = round(c * 3), round(s * 3)              # the crank pins: a coupling rod for each pair of wheels
        for x0, x1 in ((-36, -16), (16, 36)):
            pygame.draw.line(surf, ink, (x + x0 + px, y - 6 + py), (x + x1 + px, y - 6 + py), 3)
            pygame.draw.line(surf, C["steel_l"], (x + x0 + px, y - 6 + py), (x + x1 + px, y - 6 + py))
        lamp = C["red"] if self.mode == "whistle" and self.mt % 8 < 4 else C["sun"]
        surf.blit(atlas.glow_s, (x - 54, y - 29), special_flags=pygame.BLEND_ADD)      # its light on the dusk
        pygame.draw.circle(surf, lamp, (x - 47, y - 22), 2)
        surf.set_at((x - 48, y - 23), C["white"] if lamp == C["sun"] else C["cream"])
        c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
        gx, gy = x - 8, y - 44
        pygame.draw.line(surf, ink, (gx, gy), (gx + c * 13, gy + s * 13), 5)
        pygame.draw.line(surf, C["steel"], (gx, gy), (gx + c * 12, gy + s * 12), 3)
        pygame.draw.line(surf, C["steel_l"], (gx, gy - 1), (gx + c * 11, gy + s * 11 - 1))
        pygame.draw.circle(surf, ink, (round(gx + c * 12), round(gy + s * 12)), 2)    # the muzzle
        pygame.draw.circle(surf, ink, (gx, gy), 4)
        pygame.draw.circle(surf, C["steel"], (gx, gy), 3)
        surf.set_at((gx + 1, gy - 2), C["steel_l"])
        if self.angry:                                   # the split armour shows the firebox behind its grate
            glow = C["sun"] if (self.t // 5) % 2 else C["ember"]
            pygame.draw.rect(surf, C["ember"], (x + 3, y - 28, 12, 7))
            pygame.draw.rect(surf, glow, (x + 4, y - 26, 10, 4))
            for bx in (x + 6, x + 9, x + 12):
                pygame.draw.line(surf, ink, (bx, y - 28), (bx, y - 22))


class Harrow(Body):
    """HARROW, the grid company's old line-survey gunship under Legion plate. It hangs over the arena out of jumping
    reach and fires aimed bursts from its chin gun; when its siren sounds it climbs and makes a bomb run along the
    road. Shoot up at it, and run out from under the bombs. Once broken it runs faster and drops drones."""
    w, h = 72, 34                               # up to the rotor pylons: a shot through them counts
    HP = 150
    FLY = 88                                    # the hull's underside: a jump from the road tops out below it

    def __init__(self, x, y, left, right):
        super().__init__(x, self.FLY)
        self.hp = self.HP
        self.left, self.right = left, right
        self.home = right - 90
        self.state = "enter"
        self.mode, self.mt = "hover", 0         # hover, siren, run, settle
        self.t = self.hurt = self.dying = self.burst = 0
        self.dir, self.vy = -1, 0.0
        self.gun_angle = math.pi * 0.75
        self.marks = []                         # none: World.boss_down clears every boss's

    @property
    def angry(self):
        return self.hp <= self.HP // 2

    def step(self, world):
        self.t += 1
        if self.hurt:
            self.hurt -= 1
        if self.dying:                          # it loses the air and comes down on the road
            self.dying -= 1
            self.vy = min(3.0, self.vy + 0.04)
            self.y = min(GROUND_Y - 4, self.y + self.vy)
            self.x += self.dir * 0.4
            if self.dying % 6 == 0:
                world.explode(self.x + random.uniform(-34, 34), self.y - random.uniform(4, 24), 16, 0, None)
            if self.dying == 1:
                world.explode(self.x, self.y - 10, 60, 0, None, big=True)
                self.dead = True
            return
        if self.t % 40 == 0:
            audio.play("rotor")
        if self.angry and self.t % 5 == 0:
            world.smoke(self.x + 20 + random.uniform(-6, 6), self.y - 22, 1.0)
        bob = math.sin(self.t / 18) * 3
        if self.state == "enter":
            self.x = max(self.home, self.x - 1.3)
            self.y = self.FLY + bob
            if self.x == self.home:
                self.state, self.t = "fight", 0
            return
        target = world.nearest(self.x)
        self.mt += 1
        mid = (self.left + self.right) / 2
        if self.mode == "hover":
            if target is not None:              # it drifts to sit just ahead of whoever it hunts
                want = max(self.left + 50, min(self.right - 50, target.x + 30))
                self.x += max(-0.8, min(0.8, (want - self.x) * 0.02))
            self.y = self.FLY + bob
            if self.mt > (210 if self.angry else 300):
                self.mode, self.mt = "siren", 0
                self.dir = -1 if self.x > mid else 1
                audio.play("alarm")
        elif self.mode == "siren":              # a climb, its siren lamp flashing: the bomb run is coming
            self.y = max(self.FLY - 26, self.y - 0.7)
            if self.mt >= 50:
                self.mode, self.mt = "run", 0
        elif self.mode == "run":
            self.x += self.dir * (2.6 if self.angry else 2.0)
            if self.mt % (12 if self.angry else 16) == 0:
                world.bolts.append(Bolt(self.x, self.y + 2, self.dir * 0.6, 0.4, 0.14, "shell"))
            end = self.left + 40 if self.dir < 0 else self.right - 40
            if (self.x - end) * self.dir >= 0:
                self.x = end
                self.mode, self.mt = "settle", 0
        elif self.mode == "settle":
            self.y = min(self.FLY + bob, self.y + 0.8)
            if self.mt > 40:
                self.mode, self.mt = "hover", 0
        if target is None:
            return
        gx, gy = self.x + self.nose(), self.y + 2
        want = math.atan2((target.y - 12) - gy, target.x - gx)
        self.gun_angle += max(-0.06, min(0.06, (want - self.gun_angle + math.pi) % (2 * math.pi) - math.pi))
        period = 90 if self.angry else 120
        beat = self.t % period
        if self.mode in ("hover", "settle"):
            if period - 36 <= beat < period - 14 and beat % 6 == 0:     # the chin gun glints before a burst
                world.flash(gx + math.cos(self.gun_angle) * 10, gy + math.sin(self.gun_angle) * 10, small=True)
            if beat == period - 14:
                self.burst = 4 if self.angry else 3
        if self.burst and self.t % 7 == 0:
            self.burst -= 1
            c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
            world.bolts.append(Bolt(gx + c * 10, gy + s * 10, c * 2.2 * world.fire, s * 2.2 * world.fire))
            world.flash(gx + c * 10, gy + s * 10, small=True)
            audio.play("enemy_shot")
        if (self.angry and self.mode == "hover" and self.t % 300 == 150
                and sum(isinstance(f, Drone) for f in world.foes) < 2):
            world.foes.append(Drone(self.x, self.y + 12))           # out of the bay doors

    def damage(self, dmg, world, owner, push=0.0):
        if self.dying or self.state == "enter":
            return True
        calm = not self.angry
        self.hp -= dmg
        self.hurt = 3
        if self.hp <= 0:
            self.dying, self.vy = 150, 0.0
            world.award(owner, SCORE["boss"], self.x, self.y - 40)
            world.boss_down()
        elif calm and self.angry:                        # a rotor takes a hit: a beat to see the fight change
            world.explode(self.x + 20, self.y - 20, 20, 0, None)
            world.hitstop(8)
            world.shake = max(world.shake, 10)
            audio.play("alarm")
        return True

    def hitbox(self):
        return pygame.Rect(round(self.x - self.w / 2), round(self.y - self.h), self.w, self.h)

    def nose(self):
        """The chin gun's offset: under the nose, which turns into a rightward bomb run."""
        return 24 if self.dir > 0 and self.mode == "run" else -24

    def draw(self, surf, atlas, cam):
        x, y = round(self.x - cam), round(self.y)
        img = atlas.harrow[self.angry]
        if self.nose() > 0:
            img = atlas.harrow_r[self.angry]             # it turns its nose into the bomb run
        surf.blit(atlas.flash(img) if self.hurt and self.hurt % 2 else img,
                  (x - img.get_width() // 2, y - img.get_height()))
        ink = C["ink"]
        for rx in (-18, 18):                             # two rotors: a blur that beats, the blades catching the light
            half = 4 + round(24 * abs(math.cos(self.t * 0.7 + rx)))
            ry = y - 34
            pygame.draw.line(surf, ink, (x + rx - half, ry), (x + rx + half, ry), 2)
            pygame.draw.line(surf, C["steel_l"], (x + rx - half + 2, ry), (x + rx + half - 2, ry))
            pygame.draw.rect(surf, ink, (x + rx - 1, ry - 1, 3, 4))
        lamp = C["red"] if self.mode == "siren" and self.mt % 8 < 4 else C["sun"]
        surf.blit(atlas.glow_s, (x - 7, y - 3), special_flags=pygame.BLEND_ADD)    # its searchlight on the ash
        pygame.draw.circle(surf, lamp, (x, y + 1), 2)
        c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
        gx, gy = x + self.nose(), y + 2
        pygame.draw.line(surf, ink, (gx, gy), (gx + c * 11, gy + s * 11), 4)
        pygame.draw.line(surf, C["steel"], (gx, gy), (gx + c * 10, gy + s * 10), 2)
        pygame.draw.circle(surf, ink, (gx, gy), 3)
        pygame.draw.circle(surf, C["steel"], (gx, gy), 2)
        if self.angry:                                   # the torn engine cowl shows the turbine glowing
            glow = C["sun"] if (self.t // 5) % 2 else C["ember"]
            pygame.draw.rect(surf, C["ember"], (x + 14, y - 26, 10, 5))
            pygame.draw.rect(surf, glow, (x + 15, y - 25, 8, 3))


class Graive(Body):
    """OTTAR GRAIVE in the Cradle's lineman rig: a walking frame built to carry a technician up a reactor tower, now
    plated and armed. It strides in firing its arm cannon, crouches, and leaps at you; the landing sends a shockwave
    crawling along the floor both ways. Jump the waves, and never be where it lands. Broken, it leaps sooner and its
    landing sends a second wave after the first."""
    w, h = 36, 44                               # under the arena's catwalks, so standing on one is safe
    HP = 170

    def __init__(self, x, y, left, right):
        super().__init__(x, y)
        self.floor = y
        self.hp = self.HP
        self.left, self.right = left, right
        self.home = right - 70
        self.state = "enter"
        self.mode, self.mt = "stride", 0        # stride, crouch, leap, land
        self.t = self.hurt = self.dying = self.burst = 0
        self.stride = 0.0
        self.facing = -1
        self.target_x = x
        self.gun_angle = math.pi
        self.marks = []                         # none: World.boss_down clears every boss's

    @property
    def angry(self):
        return self.hp <= self.HP // 2

    def step(self, world):
        self.t += 1
        if self.hurt:
            self.hurt -= 1
        if self.dying:                          # the rig staggers, sparks, goes down on its knees
            self.dying -= 1
            self.y = min(self.floor, self.y + 2)
            if self.dying % 7 == 0:
                world.explode(self.x + random.uniform(-18, 18), self.y - random.uniform(6, 40), 16, 0, None)
            if self.dying == 1:
                world.explode(self.x, self.y - 20, 60, 0, None, big=True)
                self.dead = True
            return
        if self.angry and self.t % 6 == 0:
            world.smoke(self.x + random.uniform(-10, 10), self.y - 44, 1.0)
        x0 = self.x
        if self.state == "enter":
            self.x = max(self.home, self.x - 0.8)
            self.stride += self.x - x0
            if self.x == self.home:
                self.state, self.t = "fight", 0
            return
        target = world.nearest(self.x)
        self.mt += 1
        if self.mode == "stride":
            if target is not None:
                self.facing = 1 if target.x > self.x else -1
                want = max(self.left + 30, min(self.right - 30, target.x - self.facing * 110))
                self.x += max(-0.5, min(0.5, want - self.x))
            if self.mt > (150 if self.angry else 230):
                if target is not None and target.y < self.floor - 4:     # up on a catwalk: its arc would pass
                    self.mt = 0                                          # through it, so it keeps shooting
                else:
                    self.mode, self.mt = "crouch", 0
                    audio.play("alarm")
        elif self.mode == "crouch":             # it sinks on its legs and vents: the leap is coming
            if self.mt % 4 == 0:
                world.smoke(self.x - self.facing * 10, self.y - 30, 1.2)
            if self.mt >= 28:
                land = self.x if target is None else target.x
                self.target_x = max(self.left + 24, min(self.right - 24, land))
                self.vx = (self.target_x - self.x) / 52.0
                self.vy, self.mode, self.mt = -6.5, "leap", 0
        elif self.mode == "leap":
            self.vy += 0.25
            self.x += self.vx
            self.y += self.vy
            if self.y >= self.floor:
                self.y, self.vy = self.floor, 0.0
                self.mode, self.mt = "land", 0
                self.shockwave(world)
        elif self.mode == "land":
            if self.angry and self.mt == 24:
                self.shockwave(world)
            if self.mt > 50:
                self.mode, self.mt = "stride", 0
        self.stride += self.x - x0 if self.mode == "stride" else 0
        if target is None or self.mode in ("leap", "crouch"):
            return
        gx, gy = self.x + self.facing * 16, self.y - 34 + (6 if self.mode == "land" and self.mt < 10 else 0)
        want = math.atan2((target.y - 12) - gy, target.x - gx)
        self.gun_angle += max(-0.06, min(0.06, (want - self.gun_angle + math.pi) % (2 * math.pi) - math.pi))
        period = 80 if self.angry else 110
        beat = self.t % period
        if period - 36 <= beat < period - 14 and beat % 6 == 0:          # the arm cannon glints before a burst
            world.flash(gx + math.cos(self.gun_angle) * 12, gy + math.sin(self.gun_angle) * 12, small=True)
        if beat == period - 14:
            self.burst = 4 if self.angry else 3
        if self.burst and self.t % 7 == 0:
            self.burst -= 1
            c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
            world.bolts.append(Bolt(gx + c * 12, gy + s * 12, c * 2.2 * world.fire, s * 2.2 * world.fire))
            world.flash(gx + c * 12, gy + s * 12, small=True)
            audio.play("enemy_shot")

    def shockwave(self, world):
        speed = 2.6 if self.angry else 2.2
        for d in (-1, 1):
            world.bolts.append(Bolt(self.x + d * 20, self.floor - 4, d * speed, 0, 0, "wave"))
        world.shake = max(world.shake, 8)
        world.dust(self.x - 12, self.floor)
        world.dust(self.x + 12, self.floor)
        audio.play("stomp")

    def damage(self, dmg, world, owner, push=0.0):
        if self.dying or self.state == "enter":
            return True
        calm = not self.angry
        self.hp -= dmg
        self.hurt = 3
        if self.hp <= 0:
            self.dying, self.mode = 160, "stride"
            world.award(owner, SCORE["boss"], self.x, self.y - 50)
            world.boss_down()
        elif calm and self.angry:                        # its chest plate blows off on the Cradle's core
            world.explode(self.x, self.y - 34, 20, 0, None)
            world.hitstop(8)
            world.shake = max(world.shake, 10)
            audio.play("alarm")
        return True

    def hitbox(self):
        return pygame.Rect(round(self.x - self.w / 2), round(self.y - self.h), self.w, self.h)

    def draw(self, surf, atlas, cam):
        x, y = round(self.x - cam), round(self.y)
        ink, plate, dark = C["ink"], C["steel_d"], C["black"]
        if self.mode == "leap" and not self.dying:      # its shadow where it will land
            sx = round(self.target_x - cam)
            pygame.draw.ellipse(surf, ink, (sx - 16, self.floor - 3, 32, 6))
            pygame.draw.ellipse(surf, C["red"] if self.t % 8 < 4 else dark, (sx - 12, self.floor - 2, 24, 4), 1)
        sink = 6 if self.mode == "crouch" or (self.mode == "land" and self.mt < 10) or self.dying else 0
        tuck = 6 if self.mode == "leap" else 0
        for side in (-1, 1):                             # two legs: hip, knee forward, a broad foot
            phase = self.stride / 5 + (0 if side < 0 else math.pi)
            step = round(math.sin(phase) * 6) if self.mode == "stride" else 0
            lift = max(0, round(math.cos(phase) * 3)) if self.mode == "stride" else tuck
            hip = (x + side * 7, y - 22 + sink)
            foot = (x + side * 7 + step, y - 1 - lift)
            knee = (x + side * 7 + step // 2 + self.facing * 6, (hip[1] + foot[1]) // 2)
            for a, b in ((hip, knee), (knee, foot)):
                pygame.draw.line(surf, ink, a, b, 6)
                pygame.draw.line(surf, plate, a, b, 4)
                pygame.draw.line(surf, C["steel"], (a[0], a[1] - 1), (b[0], b[1] - 1))
            pygame.draw.circle(surf, ink, knee, 4)
            pygame.draw.circle(surf, C["rust"], knee, 3)
            pygame.draw.rect(surf, ink, (foot[0] - 7, foot[1] - 3, 14, 5))
            pygame.draw.rect(surf, plate, (foot[0] - 6, foot[1] - 2, 12, 3))
        img = atlas.graive[self.angry][self.facing > 0]
        surf.blit(atlas.flash(img) if self.hurt and self.hurt % 2 else img,
                  (x - img.get_width() // 2, y - 20 + sink - img.get_height()))
        c, s = math.cos(self.gun_angle), math.sin(self.gun_angle)
        gx, gy = x + self.facing * 16, y - 34 + sink
        pygame.draw.line(surf, ink, (gx, gy), (gx + c * 13, gy + s * 13), 6)
        pygame.draw.line(surf, C["rust"], (gx, gy), (gx + c * 12, gy + s * 12), 4)
        pygame.draw.line(surf, C["sun"], (gx, gy - 1), (gx + c * 11, gy + s * 11 - 1))
        pygame.draw.circle(surf, ink, (round(gx + c * 12), round(gy + s * 12)), 2)
        if self.angry:                                   # the core behind the blown chest plate
            glow = C["white"] if (self.t // 4) % 2 else C["cyan"]
            pygame.draw.circle(surf, C["blue"], (x, y - 46 + sink), 5)
            pygame.draw.circle(surf, glow, (x, y - 46 + sink), 3)
