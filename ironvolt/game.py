"""The cabinet: attract mode, credits, play, continues, the stage-clear tally and name entry.

Game.step(controls) runs one 60 Hz frame; Game.draw(surface) paints it at 320x224.
"""

import math

import pygame

from . import __version__, audio, font, storage
from .autopilot import BotPad
from .settings import C, H, W
from .stage import NAME
from .world import World

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


class Game:
    def __init__(self, atlas, free_play=True):
        self.atlas = atlas
        self.free_play = free_play
        self.credits = 0
        self.scores = storage.load()
        self.mode = "title"
        self.t = 0
        self.world = None
        self.demo = None
        self.bots = [BotPad(), BotPad()]
        self.paused = False
        self.entry = []                    # players waiting to enter initials: [index, letters, cursor]
        self.drift = 0.0
        self.logo = font.logo("IRONVOLT", 4, C["cream"], C["ember"], C["ink"])

    # ---------------------------------------------------------- credits

    def coin(self):
        self.credits = min(9, self.credits + 1)
        audio.play("coin")

    def pay(self):
        if self.free_play:
            return True
        if self.credits:
            self.credits -= 1
            return True
        return False

    # ---------------------------------------------------------- flow

    def go(self, mode):
        self.mode, self.t = mode, 0

    def start(self, players):
        self.world = World(players)
        self.demo = None
        self.paused = False
        audio.play("start")
        audio.music(True)
        self.go("play")

    def step(self, ctl):
        self.t += 1
        if ctl.coin:
            self.coin()
        starts = ctl.any_start()
        if self.mode in ("title", "scores", "demo"):
            self.drift += 0.5
            if starts and self.pay():
                self.start(sorted(set(starts)))
                return
            if self.mode == "title" and self.t > 600:
                self.go("scores")
            elif self.mode == "scores" and self.t > 360:
                self.demo = World((0,), seed=7, god=True)
                self.go("demo")
            elif self.mode == "demo":
                self.bots[0].think(self.demo, self.demo.players[0])
                self.demo.step(self.bots)
                if self.t > 1500 or self.demo.locked:
                    self.demo = None
                    self.go("title")
        elif self.mode == "play":
            self.play_step(ctl, starts)
        elif self.mode in ("over", "clear"):
            if self.t > (240 if self.mode == "over" else 420) or (self.t > 90 and starts):
                self.begin_entry()
        elif self.mode == "entry":
            self.entry_step(ctl)

    def play_step(self, ctl, starts):
        w = self.world
        if self.paused:
            return
        for i in starts:
            p = w.players[i]
            if p is None and self.pay():
                w.join(i)
                audio.play("start")
            elif p and p.out and getattr(p, "continue_t", 0) > 0 and self.pay():
                w.carry_on(i)
                audio.play("start")
        w.step(ctl.pads)
        if w.cleared > 180:
            audio.music(False)
            self.bonus = w.hostages_freed * 1000
            for p in w.players:
                if p:
                    p.score += self.bonus
            self.go("clear")
        elif all(p is None or (p.out and getattr(p, "continue_t", 0) <= 0) for p in w.players):
            audio.music(False)
            self.go("over")

    def begin_entry(self):
        self.entry = [[p.index, "AAA", 0] for p in self.world.players
                      if p and storage.qualifies(self.scores, p.score)]
        if self.entry:
            self.go("entry")
        else:
            self.world = None
            self.go("scores")

    def entry_step(self, ctl):
        if not self.entry:
            self.world = None
            self.go("scores")
            return
        e = self.entry[0]
        pad = ctl.pads[e[0]]
        name = list(e[1])
        i = LETTERS.index(name[e[2]])
        if pad.pressed("up") or pad.pressed("right"):
            name[e[2]] = LETTERS[(i + 1) % len(LETTERS)]
        if pad.pressed("down") or pad.pressed("left"):
            name[e[2]] = LETTERS[(i - 1) % len(LETTERS)]
        e[1] = "".join(name)
        if pad.pressed("fire") or pad.pressed("jump") or pad.pressed("start") or self.t > 1800:
            e[2] += 1
            audio.play("pickup")
            if e[2] == 3 or self.t > 1800:
                self.scores = storage.insert(self.scores, e[1], self.world.players[e[0]].score)
                self.entry.pop(0)
                self.t = 0

    def toggle_pause(self):
        if self.mode == "play":
            self.paused = not self.paused
            audio.music(not self.paused)

    def to_title(self):
        audio.music(False)
        self.world = None
        self.paused = False
        self.go("title")

    # ---------------------------------------------------------- drawing

    def draw(self, surf):
        if self.mode == "play" or (self.mode in ("over", "clear") and self.world):
            self.world.draw(surf, self.atlas)
            self.hud(surf, self.world)
            if self.mode == "play":
                self.banners(surf)
            if self.paused:
                self.shade(surf)
                font.draw(surf, "PAUSE", (W // 2, 96), C["cream"], 2, center=True)
                font.draw(surf, "ENTER RESUME   ESC TITLE", (W // 2, 120), C["steel_l"], center=True)
            if self.mode == "over":
                self.shade(surf)
                font.draw(surf, "GAME OVER", (W // 2, 100), C["red"], 3, center=True)
            if self.mode == "clear":
                self.tally(surf)
        elif self.mode == "demo" and self.demo:
            self.demo.draw(surf, self.atlas)
            self.hud(surf, self.demo)
            font.draw(surf, "DEMO PLAY", (W // 2, 40), C["cream"], center=True)
            self.prompt(surf, 196)
        elif self.mode == "entry":
            self.backdrop(surf)
            e = self.entry[0] if self.entry else None
            font.draw(surf, "NEW HIGH SCORE", (W // 2, 56), C["sun"], 2, center=True)
            if e:
                font.draw(surf, "PLAYER %d  %07d" % (e[0] + 1, self.world.players[e[0]].score),
                          (W // 2, 86), C["cream"], center=True)
                for k, ch in enumerate(e[1]):
                    x = W // 2 - 30 + k * 24
                    col = C["sun"] if k == e[2] and self.t % 30 < 20 else C["cream"]
                    font.draw(surf, ch, (x, 110), col, 3)
                    if k == e[2]:
                        pygame.draw.line(surf, C["ember"], (x, 134), (x + 14, 134), 2)
                font.draw(surf, "UP DOWN CHOOSE   FIRE NEXT", (W // 2, 160), C["steel_l"], center=True)
        elif self.mode == "scores":
            self.backdrop(surf)
            font.draw(surf, "BEST SOLDIERS", (W // 2, 30), C["sun"], 2, center=True)
            for k, (name, score) in enumerate(self.scores):
                col = (C["cream"], C["steel_l"])[k % 2]
                y = 60 + k * 13
                font.draw(surf, "%2d" % (k + 1), (88, y), C["ember"])
                font.draw(surf, name, (116, y), col)
                font.draw(surf, "%07d" % score, (170, y), col)
            self.prompt(surf, 200)
        else:
            self.backdrop(surf)
            bob = round(math.sin(self.t * 0.05) * 2)
            surf.blit(self.logo, (W // 2 - self.logo.get_width() // 2, 44 + bob))
            font.draw(surf, "ARCADE RUN AND GUN", (W // 2, 90), C["sun"], center=True)
            font.draw(surf, "HI %07d" % self.scores[0][1], (W // 2, 8), C["cream"], center=True)
            font.draw(surf, "MOVE ARROWS  FIRE Z  JUMP X  GRENADE C", (W // 2, 150), C["steel_l"], center=True)
            font.draw(surf, "P2  WASD  G  H  J      FULLSCREEN F11", (W // 2, 160), C["steel_l"], center=True)
            self.prompt(surf, 120)
            font.draw(surf, "V" + __version__, (W - 4 - font.width("V" + __version__), H - 10), C["steel"])

    def prompt(self, surf, y):
        if self.free_play or self.credits:
            if self.t % 60 < 40:
                font.draw(surf, "PRESS START", (W // 2, y), C["cream"], 2, center=True)
        elif self.t % 60 < 40:
            font.draw(surf, "INSERT COIN", (W // 2, y), C["cream"], 2, center=True)
        label = "FREE PLAY" if self.free_play else "CREDIT %d" % self.credits
        font.draw(surf, label, (W // 2, H - 10), C["steel_l"], center=True)

    def backdrop(self, surf):
        surf.blit(self.atlas.sky, (0, 0))
        for layer, factor, yoff in self.atlas.layers:
            lw = layer.get_width()
            ox = -int(self.drift * factor) % lw
            surf.blit(layer, (ox - lw, yoff))
            surf.blit(layer, (ox, yoff))
        self.shade(surf, 90)

    def shade(self, surf, alpha=130):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 6, 14, alpha))
        surf.blit(veil, (0, 0))

    def hud(self, surf, w):
        font.draw(surf, "HI %07d" % max(self.scores[0][1], *(p.score for p in w.players if p)),
                  (W // 2, 4), C["cream"], center=True)
        for i in (0, 1):
            p = w.players[i]
            x = 6 if i == 0 else W - 96
            tag = C["ember"] if i == 0 else C["cyan"]
            if p is None:
                if self.mode == "play" and self.t % 60 < 40:
                    font.draw(surf, "PRESS %dP START" % (i + 1) if (self.free_play or self.credits)
                              else "INSERT COIN", (x, 4), C["steel_l"])
                continue
            font.draw(surf, "%dUP" % (i + 1), (x, 4), tag)
            font.draw(surf, "%07d" % p.score, (x + 24, 4), C["cream"])
            if p.out:
                ct = getattr(p, "continue_t", 0)
                if ct > 0:
                    font.draw(surf, "CONTINUE? %d" % (ct // 60), (x, 14), C["sun"])
                continue
            for k in range(min(p.lives, 5)):                  # lives as little helmets
                pygame.draw.rect(surf, C["ink"], (x + k * 7, 14, 6, 6))
                pygame.draw.rect(surf, tag, (x + k * 7 + 1, 15, 4, 4))
            ammo = "--" if p.weapon == "P" else str(p.ammo)
            font.draw(surf, "%s %s" % (p.weapon, ammo), (x + 40, 14), C["sun"])
            font.draw(surf, "B%d" % p.grenades, (x + 76, 14), C["steel_l"])
        if w.boss and w.boss.state == "fight":
            frac = max(0, w.boss.hp) / w.boss.HP
            pygame.draw.rect(surf, C["ink"], (W // 2 - 61, 26, 122, 6))
            pygame.draw.rect(surf, C["red"] if w.boss.angry else C["ember"], (W // 2 - 60, 27, round(120 * frac), 4))
            font.draw(surf, "BASTION", (W // 2, 34), C["cream"], center=True)

    def banners(self, surf):
        w = self.world
        if w.frame < 180:
            if w.frame < 120:
                font.draw(surf, NAME, (W // 2, 80), C["cream"], center=True)
            if 60 < w.frame and w.frame % 20 < 14:
                font.draw(surf, "GO!", (W // 2, 96), C["sun"], 3, center=True)
        elif w.locked and w.boss and w.boss.state == "enter" and w.frame % 30 < 20:
            font.draw(surf, "WARNING", (W // 2, 90), C["red"], 3, center=True)
        elif not w.locked and not any(0 < f.x - w.cam_x < W for f in w.foes) and (w.frame // 30) % 2:
            font.draw(surf, "GO >", (W - 50, 100), C["sun"], 2)

    def tally(self, surf):
        self.shade(surf)
        font.draw(surf, "MISSION COMPLETE", (W // 2, 60), C["sun"], 2, center=True)
        font.draw(surf, "PRISONERS FREED  %d" % self.world.hostages_freed, (W // 2, 96), C["cream"], center=True)
        font.draw(surf, "BONUS  %d" % self.bonus, (W // 2, 110), C["cream"], center=True)
        if self.t > 120:
            font.draw(surf, "MORE MISSIONS SOON", (W // 2, 150), C["steel_l"], center=True)
