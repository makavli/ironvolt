"""One play of a stage: the actors, the camera, collisions, effects, and drawing it all."""

import math
import random

import pygame

from . import audio
from .actors import Bastion, Drone, Foe, Hostage, Pickup, Player, Turret, Warden
from .settings import CHAIN_FRAMES, CHAIN_MAX, DIFFICULTY, GRENADES, TILE, C, H, W
from .stage import AIR, CRATE, GROUND, WALK, Stage

CONTINUE_FRAMES = 600


class World:
    def __init__(self, players=(0,), seed=None, god=False, level="NORMAL", lives=None, stage=0):
        if seed is not None:
            random.seed(seed)
        self.lives_set = lives            # the options' lives, or None: the difficulty's
        self.shake_on = self.flashes_on = True      # accessibility options
        self.set_level(level)
        self.deaths = 0                   # the team's, for the "too feeble?" offer
        self.offered = 0                  # deaths when it was last offered
        self.stage = Stage(stage)
        self.cam_x = self.cam_ox = 0.0    # the camera now, and a step ago
        self.blend = 1.0                  # how far from the step before to this one the picture is drawn (app.py)
        self.still = False                # a hit-stop holds the picture
        self.jolt = (0, 0)                # this step's screen shake
        self.felt = []                    # this step's (player index, moment): the app turns them into rumble
        self.players = [None, None]
        self.god = god
        self.frame = 0
        for i in players:
            self.join(i)
        self.foes, self.shots, self.bolts, self.thrown = [], [], [], []
        self.pickups, self.hostages = [], []
        self.parts, self.popups, self.flashes = [], [], []
        self.boss = None
        self.spawn_i = 0
        self.shake = 0
        self.freeze = 0
        self.hostages_freed = 0
        self.cleared = 0                  # frames since the boss fell
        self.locked = False

    def set_level(self, level):
        self.level = level
        self.lives, self.windup, self.fire, self.boss_hp, self.safe, self.feeble_at = DIFFICULTY[level]
        self.lives = self.lives_set or self.lives
        if getattr(self, "boss", None) and self.boss.hp > 0:            # a change mid-fight keeps the damage done
            self.boss.hp = max(1, round(self.boss.hp * self.boss_hp / self.boss.HP))
            self.boss.HP = self.boss_hp
        for p in getattr(self, "players", ()):
            if p and not p.out:
                p.lives = max(p.lives, self.lives - 1)

    # ---------------------------------------------------------- players

    def join(self, i):
        p = Player(i, self.drop_x(16 * i), -10 if self.frame else 176)
        p.god = self.god
        p.lives = self.lives
        self.players[i] = p
        return p

    def advance(self):
        """The next mission, with the same team: scores, lives, guns and grenades carry over."""
        nxt = World((), god=self.god, level=self.level, lives=self.lives_set, stage=self.stage.index + 1)
        nxt.shake_on, nxt.flashes_on = self.shake_on, self.flashes_on
        nxt.deaths, nxt.offered = self.deaths, self.offered
        for i, p in enumerate(self.players):
            if p:
                p.x, p.y, p.vx, p.vy = 40.0 + 16 * i, 176.0, 0.0, 0.0
                p.ox, p.oy = p.x, p.y
                p.dying = p.slide = p.slash = 0
                p.chain = p.chain_t = 0
                p.safe = self.safe
                if p.out:
                    p.continue_t = CONTINUE_FRAMES          # a fresh chance to continue on the new stage
                nxt.players[i] = p
        return nxt

    def live_players(self):
        return [p for p in self.players if p and p.active]

    def nearest(self, x):
        live = self.live_players()
        return min(live, key=lambda p: abs(p.x - x)) if live else None

    def kill_player(self, p):
        if p.god or p.dying or p.out:
            if p.god and p.y > H + 40:                 # the demo falls in a pit: put it back
                p.x, p.y, p.vy = self.drop_x(), -10.0, 0.0
            return
        if p.safe and p.y <= H:
            return
        p.dying = 70
        p.chain = p.chain_t = 0
        self.deaths += 1
        p.vy, p.vx = -3.6, -p.facing * 1.2
        p.on_ground = False
        self.sparks(p.x, p.y - 12, 10)
        self.hitstop(8)
        self.feel(p, "hurt")
        self.shake = 6
        audio.play("hurt")

    def respawn(self, p):
        if p.lives > 0:
            p.lives -= 1
            p.x, p.y, p.vx, p.vy = self.drop_x(), -10.0, 0.0, 0.0
            p.buffer = p.trigger = 0
            p.safe, p.weapon, p.ammo = self.safe, "P", 0
            p.grenades = max(p.grenades, GRENADES)
        else:
            p.out = True
            p.continue_t = CONTINUE_FRAMES

    def drop_x(self, off=0):
        """Where a player drops back in: near the left of the screen, and never over a pit."""
        for x in range(int(self.cam_x) + 40 + off, int(self.cam_x) + W - 40, 8):
            if self.stage.floor_y(x - 5) is not None and self.stage.floor_y(x + 5) is not None:
                return float(x)
        return self.cam_x + 40 + off

    def carry_on(self, i):
        """A continue: the score keeps counting, and the player drops back in."""
        p = self.players[i]
        p.out, p.lives, p.dying = False, self.lives, 0
        p.score = p.score // 10 * 10 + 1               # arcade habit: the last digit counts continues
        self.respawn(p)

    # ---------------------------------------------------------- effects

    def feel(self, p, moment):
        """A moment for a player's hands (see controls.FEEL)."""
        if isinstance(p, Player):
            self.felt.append((p.index, moment))

    def hitstop(self, frames):
        """Holds the action for a few frames: the weight of a hit, scaled to what was hit."""
        self.freeze = max(self.freeze, frames)

    def award(self, owner, points, x, y, text=None):
        """Points for a player. A kill (no text) inside the chain window multiplies them: x2, x3... up to x8."""
        if isinstance(owner, Player):
            if text is None:
                owner.chain = owner.chain + 1 if owner.chain_t else 1
                owner.chain_t = CHAIN_FRAMES
                mult = min(CHAIN_MAX, owner.chain)
                points *= mult
                if mult > 1:
                    text = "%d X%d" % (points, mult)
            owner.score += points
        self.popups.append([x, y, text or str(points), 50])

    def flash(self, x, y, small=False):
        self.flashes.append((x, y, small))

    def part(self, x, y, vx, vy, life, kind, size=1, colour=None):
        self.parts.append([x, y, vx, vy, life, life, kind, size, colour])

    def sparks(self, x, y, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, 3)
            self.part(x, y, math.cos(a) * sp, math.sin(a) * sp - 1, random.randint(8, 16), "spark")

    def smoke(self, x, y, size):
        self.part(x, y, random.uniform(-0.2, 0.2), -random.uniform(0.3, 0.7), random.randint(30, 50), "smoke", size)

    def dust(self, x, y):
        for d in (-1, 1):
            self.part(x + d * 4, y - 1, d * 0.6, -0.2, 14, "dust", 1)

    def casing(self, x, y, d):
        self.part(x, y, d * random.uniform(0.8, 1.4), -random.uniform(1.5, 2.5), 40, "casing")

    def explode(self, x, y, radius, dmg, owner, hurts_players=False, big=False):
        audio.play("big_boom" if big else "boom")
        self.shake = max(self.shake, 14 if big else 5)
        self.hitstop(10 if big else 3 if dmg else 0)
        for p in self.players if big else [owner] if dmg else []:     # your own blast kicks; a big one shakes everyone
            self.feel(p, "big_boom" if big else "boom")
        n = 40 if big else 10 + radius // 2
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1.0) * radius / 10
            self.part(x, y, math.cos(a) * sp, math.sin(a) * sp - 0.5, random.randint(14, 30), "fire",
                      random.randint(2, 5 if not big else 9))
        for _ in range(n // 2):
            self.smoke(x + random.uniform(-radius / 2, radius / 2), y + random.uniform(-radius / 2, 0),
                       random.uniform(1.0, 2.0 if not big else 3.5))
        for _ in range(n // 3):
            self.part(x, y, random.uniform(-3, 3), random.uniform(-4, -1), 60, "debris")
        self.part(x, y, 0, 0, 8, "ring", radius)
        self.flash(x, y)
        if dmg:
            for e in self.foes:
                if not getattr(e, "dying", 0) and math.hypot(e.x - x, (e.y - e.h / 2) - y) < radius + e.w / 2:
                    e.damage(dmg, self, owner, push=1 if e.x > x else -1)
            if self.boss and self.boss.hitbox().inflate(radius, radius).collidepoint(x, y):
                self.boss.damage(dmg, self, owner)
            for h in self.hostages:
                if not h.freed and math.hypot(h.x - x, h.y - 7 - y) < radius:
                    h.free(self, owner)
        if hurts_players:
            for p in self.live_players():
                if math.hypot(p.x - x, (p.y - p.h / 2) - y) < radius * 0.7 + 4:
                    self.kill_player(p)

    def boss_down(self):
        self.hitstop(20)
        self.bolts.clear()
        self.boss.marks.clear()

    # ---------------------------------------------------------- the step

    def spawn(self, kind, x, extra):
        if x == "edge":
            x = self.cam_x + W + 14
        if kind == "drone":
            self.foes.append(Drone(x + 10, random.uniform(40, 86)))
            return
        y = self.stage.floor_y(x)
        if y is None:
            return
        if kind == "hostage":
            self.hostages.append(Hostage(x, y, extra))
        elif kind == "turret":
            self.foes.append(Turret(x, y))
        else:
            self.foes.append(Foe(x, y, kind))       # soldier, lobber or shield

    def actors(self):
        """Everything with a position of its own."""
        return [p for p in self.players if p] + self.foes + self.shots + self.bolts + self.thrown + self.pickups + \
            self.hostages + ([self.boss] if self.boss else [])

    def step(self, pads):
        self.frame += 1
        self.felt.clear()
        self.cam_ox = self.cam_x
        for a in self.actors():
            a.ox, a.oy = a.x, a.y
        self.jolt = (0, 0)
        if self.shake:                                            # rolled here, not in draw(): once a step,
            self.shake -= 1                                       # whatever the screen's refresh rate
        if self.shake and self.shake_on:
            self.jolt = (round(random.uniform(-1, 1) * min(self.shake, 4)),
                         round(random.uniform(-1, 1) * min(self.shake, 3)))
        for p in self.players:
            if p and p.out and getattr(p, "continue_t", 0):
                p.continue_t -= 1
            if p and p.chain_t and not self.freeze:              # a hit-stop does not eat the chain's time
                p.chain_t -= 1
                if not p.chain_t:
                    p.chain = 0
        self.still = self.freeze > 0
        if self.freeze:
            self.freeze -= 1
            for i, p in enumerate(self.players):
                if p and p.active:
                    p.listen(pads[i])                             # a press during a hit-stop still counts
            return
        self.flashes.clear()                                      # a flash lasts one step, not one screen refresh
        for i, p in enumerate(self.players):
            if p:
                p.step(pads[i], self)
        self.camera()
        for group in (self.foes, self.shots, self.bolts, self.thrown, self.pickups, self.hostages):
            for a in group:
                a.step(self)
        if self.boss:
            self.boss.step(self)
        self.collide()
        self.effects()
        for group in (self.foes, self.shots, self.bolts, self.thrown, self.pickups, self.hostages):
            group[:] = [a for a in group if not a.dead]
        if self.boss and self.boss.dead:
            self.boss = None
            self.cleared = 1
        if self.cleared:
            self.cleared += 1
        if self.frame % 7 == 0:                                   # embers drifting on the wind
            self.part(self.cam_x + W + 4, random.uniform(20, 170), -random.uniform(0.4, 0.9),
                      -random.uniform(0.05, 0.25), 600, "ember")

    def camera(self):
        live = self.live_players()
        if self.locked:
            return
        if live:                                     # follow the leader, but never past the slowest player:
            xs = [p.x for p in live]                 # the screen edge must not shove anyone into a wall
            self.cam_x = max(self.cam_x, min(max(xs) - 130, min(xs) - 6, self.stage.width - W))
        if self.cam_x >= self.stage.boss_x:
            self.cam_x = float(self.stage.boss_x)
            self.locked = True
            self.foes = [f for f in self.foes if f.x > self.cam_x]
            kind = Warden if self.stage.mission.boss == "warden" else Bastion
            self.boss = kind(self.cam_x + W + 60, 176, self.cam_x, self.cam_x + W)
            self.boss.HP = self.boss.hp = self.boss_hp
            audio.play("alarm")
        while self.spawn_i < len(self.stage.spawns) and self.stage.spawns[self.spawn_i][0] <= self.cam_x:
            _, kind, x, extra = self.stage.spawns[self.spawn_i]
            self.spawn(kind, x, extra)
            self.spawn_i += 1

    def collide(self):
        for s in self.shots:
            r = s.rect()
            for e in self.foes:
                if not getattr(e, "dying", 0) and r.colliderect(e.rect()):
                    if getattr(e, "kind", "") == "shield" and e.blocks(s):
                        s.dead = True                     # the riot shield takes it: go round, over, or under
                        self.sparks(s.x, s.y, 2)
                        audio.play("clank")
                        break
                    e.damage(s.dmg, self, s.owner, push=1 if s.vx > 0 else -1)
                    s.dead = True
                    s.burst(self) if s.kind == "rocket" else self.sparks(s.x, s.y, 3)
                    audio.play("hit")
                    break
            if not s.dead and self.boss and r.colliderect(self.boss.hitbox()):
                self.boss.damage(s.dmg, self, s.owner)
                s.dead = True
                s.burst(self) if s.kind == "rocket" else self.sparks(s.x, s.y, 2)
                audio.play("hit")
            if not s.dead:
                for h in self.hostages:
                    if not h.freed and r.colliderect(h.rect()):
                        h.free(self, s.owner)
        for g in self.thrown:                                     # a grenade bursts on the first enemy it touches
            r = g.rect()
            if not g.dead and (any(not getattr(e, "dying", 0) and r.colliderect(e.rect()) for e in self.foes)
                               or self.boss and r.colliderect(self.boss.hitbox())):
                g.blow(self)
        for p in self.live_players():
            pr = p.rect()
            for b in self.bolts:
                if pr.inflate(-2, -2).colliderect(b.rect()):
                    b.dead = True
                    self.kill_player(p)
            for k in self.pickups:
                if pr.colliderect(k.rect()):
                    k.apply(p)
                    self.feel(p, "pickup")
            for h in self.hostages:
                if not h.freed and pr.colliderect(h.rect()):
                    h.free(self, p)
            if p.vy > 0:                                          # falling onto a head: feet were above it a step ago
                for e in self.foes:
                    if not getattr(e, "dying", 0) and pr.colliderect(e.rect()) and p.oy <= e.rect().top + 3:
                        p.stomp(e, self)
                        break
            if self.boss and not self.boss.dying and pr.colliderect(self.boss.hitbox()):
                p.x = self.boss.hitbox().left - p.w / 2 - 1
                self.kill_player(p)

    def effects(self):
        for q in self.parts:
            q[0] += q[2]
            q[1] += q[3]
            q[4] -= 1
            kind = q[6]
            if kind in ("debris", "casing"):
                q[3] += 0.2
                ty = int(q[1] // TILE)
                if self.stage.tile(int(q[0] // TILE), ty) in (GROUND, CRATE) and q[3] > 0:
                    q[1] = ty * TILE - 1
                    q[3] *= -0.4
                    q[2] *= 0.6
            elif kind == "fire":
                q[2] *= 0.9
                q[3] = q[3] * 0.9 - 0.04
            elif kind == "spark":
                q[3] += 0.15
            elif kind == "ember":
                q[2] += math.sin((self.frame + q[1]) * 0.05) * 0.01
        self.parts = [q for q in self.parts if q[4] > 0 and q[0] > self.cam_x - 30][-700:]
        for q in self.popups:
            q[1] -= 0.4
            q[3] -= 1
        self.popups = [q for q in self.popups if q[3] > 0]

    # ---------------------------------------------------------- drawing

    def draw(self, surf, atlas):
        """Paints the moment `blend` of the way from the step before to this one: even motion at any refresh rate."""
        b = self.blend
        slid = [(a, a.x, a.y) for a in self.actors()] if b < 1 else ()
        for a, x, y in slid:                                      # actors are slid back for the painting only
            if abs(x - a.ox) < 24 and abs(y - a.oy) < 24:         # (a longer hop is a respawn: a cut, not a slide)
                a.x, a.y = a.ox + (x - a.ox) * b, a.oy + (y - a.oy) * b
        self.paint(surf, atlas, self.cam_ox + (self.cam_x - self.cam_ox) * b, 0 if self.still else 1 - b)
        for a, x, y in slid:
            a.x, a.y = x, y

    def paint(self, surf, atlas, view, back):
        sx, sy = self.jolt
        cam = round(view) - sx              # whole pixels: the tiles and all that stands on them move as one
        sky, layers, pillar = atlas.themes[self.stage.mission.theme]
        surf.blit(sky, (0, 0))
        for layer, factor, yoff in layers:
            lw = layer.get_width()
            ox = -int((view - sx) * factor) % lw
            surf.blit(layer, (ox - lw, yoff + sy))
            surf.blit(layer, (ox, yoff + sy))
        game = surf.subsurface(pygame.Rect(0, 0, W, H))
        self.draw_tiles(game, atlas, cam, sy)
        for a in self.hostages:
            a.draw(game, atlas, cam, self.frame)
        for a in self.pickups:
            a.draw(game, atlas, cam)
        if self.boss:
            self.boss.draw(game, atlas, cam)
        for e in self.foes:
            e.draw(game, atlas, cam)
        for p in self.players:
            if p:
                p.draw(game, atlas, cam)
        for g in self.thrown:
            g.draw(game, cam)
        for s in self.shots:
            s.draw(game, cam)
        for b in self.bolts:
            b.draw(game, cam, self.frame)
        self.draw_parts(game, atlas, cam, back)
        for x, y, small in self.flashes if self.flashes_on else ():
            img = atlas.glow_s if small else atlas.glow_l
            game.blit(img, (round(x - cam) - img.get_width() // 2, round(y) - img.get_height() // 2),
                      special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(game, C["white"], (round(x - cam), round(y)), 2 if small else 3)
        if cam < self.stage.boss_x - W:                           # foreground girders sweep past
            near = (view - sx) * 1.4
            for i in range(int(near // 420), int((near + W) // 420) + 2):
                px = round(i * 420 + 200 - near)
                if -30 < px < W + 30:
                    game.blit(pillar, (px, 0))
        from . import font
        for x, y, text, life in self.popups:
            if life > 10 or life % 4 < 2:
                font.draw(game, text, (round(x - cam), round(y)), C["cream"], center=True)

    def draw_tiles(self, surf, atlas, cam, sy):
        tile, theme = self.stage.tile, self.stage.mission.theme
        c0 = int(cam // TILE)
        for tx in range(c0, c0 + W // TILE + 2):
            px = round(tx * TILE - cam)
            for ty in range(len(self.stage.grid)):
                t = tile(tx, ty)
                if t == AIR:
                    continue
                y = ty * TILE + sy
                if t == GROUND:                                   # a deck where it is open above, an edge at a drop
                    surf.blit(atlas.ground_at(tx, ty, tile(tx, ty - 1) != GROUND, tile(tx - 1, ty) in (AIR, WALK),
                                              tile(tx + 1, ty) in (AIR, WALK), theme), (px, y))
                elif t == CRATE:
                    surf.blit(atlas.crate_at(tx, ty, theme, tile(tx - 1, ty) != CRATE, tile(tx + 1, ty) != CRATE),
                              (px, y))
                elif t == WALK:
                    surf.blit(atlas.girders[tile(tx - 1, ty) != WALK, tile(tx + 1, ty) != WALK], (px, y))
                    if ty + 1 < len(self.stage.grid) and tile(tx, ty + 1) == AIR and tx % 3 == 0:
                        pygame.draw.line(surf, C["ink"], (px + 8, y + 8), (px + 8, y + 22))   # hangers

    def draw_parts(self, surf, atlas, cam, back=0.0):
        for x, y, vx, vy, life, full, kind, size, colour in self.parts:
            px, py = round(x - vx * back - cam), round(y - vy * back)
            t = life / full
            if kind == "fire":
                col = C["white"] if t > 0.8 else C["sun"] if t > 0.55 else C["ember"] if t > 0.3 else C["rose"]
                r = max(1, round(size * (0.5 + t)))
                pygame.draw.circle(surf, col, (px, py), r)
            elif kind == "smoke":
                r = max(1, round(size * (2.5 - 1.5 * t)))
                col = C["steel_d"] if t > 0.5 else C["night"]
                if t > 0.15 or life % 2:
                    pygame.draw.circle(surf, col, (px, py), r)
            elif kind == "spark":
                pygame.draw.line(surf, C["sun"], (px, py), (round(px - vx), round(py - vy)))
            elif kind == "debris":
                surf.set_at((px, py), C["ink"] if life % 8 < 4 else C["rust"])
            elif kind == "casing":
                surf.set_at((px, py), C["gold"])
            elif kind == "dust":
                pygame.draw.circle(surf, C["steel"], (px, py), 1 + (life < 8))
            elif kind == "ember":
                if life % 30 < 24:
                    surf.set_at((px, py), C["ember"] if life % 60 < 30 else C["sun"])
            elif kind == "ring":
                r = round(size * (1.2 - t))
                if r > 0:
                    pygame.draw.circle(surf, C["cream"], (px, py), r, 1)
