"""The cabinet: the main menu and attract mode, credits, options, play and pause, continues, the stage-clear tally
and name entry.

Game.step(controls) runs one 60 Hz frame; Game.draw(surface) paints it at 320x224.
"""

import math
import os
import sys

import pygame

from . import __version__, audio, font, storage
from .autopilot import BotPad
from .menu import Layout, Menu, Options
from .settings import CHAIN_FRAMES, CHAIN_MAX, LEVELS, C, H, W
from .stage import MISSIONS
from .world import World

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
WEB = sys.platform == "emscripten"
MAIN = ["START GAME", "OPTIONS", "CONTROLS", "HIGH SCORES"] + ([] if WEB else ["QUIT"])   # a tab cannot close
PAUSE = ["RESUME", "OPTIONS", "CONTROLS", "QUIT TO TITLE"]

# The attract-mode intro: the Long Dusk in five screens (the full story is docs/STORY.md).
STORY = [
    ["2079. THE VOLTLINE BURNED", "IN A SINGLE NIGHT.", "", "THE ASH NEVER SETTLED.", "THE SUN NEVER ROSE AGAIN."],
    ["SEVENTEEN YEARS OF DUSK.", "", "POWER IS THE ONLY MONEY LEFT,", "AND ONE TOWER STILL TURNS:", "THE CRADLE."],
    ["WARLORD OTTAR GRAIVE", "AND HIS RUST LEGION HOLD IT.", "", "TOWNS THAT KNEEL GET LIGHT.", "THE REST STAY DARK."],
    ["THE LEGION TAKES THE PEOPLE", "WHO CAN KEEP THE CRADLE ALIVE:", "", "TECHNICIANS. LINEMEN.", "IN CHAINS."],
    ["THE OLD REPAIR CREWS FIGHT BACK.", "", "KES ADEYEMI.  JUNO VARGA.", "", "THE IRONVOLT BRIGADE."],
]
LEVEL_LINES = {"EASY": "FIVE LIVES. SLOWER SHOTS.", "NORMAL": "THE CABINET AS IT WAS.",
               "HARD": "TWO LIVES. NO MERCY."}
try:                                         # playtests: IRONVOLT_STAGE=2 starts on a later mission
    FIRST_STAGE = min(max(0, int(os.environ.get("IRONVOLT_STAGE", "1")) - 1), len(MISSIONS) - 1)
except ValueError:
    FIRST_STAGE = 0


class Game:
    def __init__(self, atlas):
        self.atlas = atlas
        self.opts = storage.load_options()
        self.free_play = self.opts["free_play"] == "ON"
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
        self.controls = None              # set by the app: the prompts follow the device in use
        self.level = self.opts["level"]   # the last difficulty chosen is offered first next time
        self.on_option = lambda key: None  # set by the app: the options it applies (video, sound, pads)
        self.menu, self.pause_menu = Menu(MAIN), Menu(PAUSE)
        self.sub = None                    # the options or controls page, over the title or the pause
        self.quit = False                  # QUIT chosen on the main menu
        self.pending = []                 # players who pressed start, while they choose the difficulty
        self.feeble = None                # the "too feeble?" offer on screen: 0 drop a level, 1 stay

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

    def set_option(self, key, value):
        self.opts[key] = value
        self.apply(key)
        storage.save_options(self.opts)

    def apply(self, key):
        """An option just changed: the game's own take effect here, the app's in on_option."""
        self.free_play = self.opts["free_play"] == "ON"
        self.level = self.opts["level"]
        for w in (self.world, self.demo):
            if w:
                w.shake_on, w.flashes_on = self.opts["shake"] == "ON", self.opts["flashes"] == "FULL"
        self.on_option(key)

    def start(self, players, level=None):
        lives = None if self.opts["lives"] == "AUTO" else int(self.opts["lives"])
        self.world = World(players, level=level or self.level, lives=lives, stage=FIRST_STAGE)
        if self.opts["level"] != self.world.level:
            self.set_option("level", self.world.level)       # offered first next time
        self.demo = None
        self.paused = False
        self.feeble = None
        self.apply("start")
        audio.play("start")
        self.go("play")

    def step(self, ctl):
        self.t += 1
        if ctl.coin:
            self.coin()
        starts = ctl.any_start()
        if self.mode in ("title", "story", "scores", "demo", "select"):
            audio.music(True, "title")
        if self.mode in ("title", "story", "scores", "demo"):
            self.drift += 0.5
            if self.mode == "title":
                self.title_step(ctl)
                return
            if starts and self.pay():
                self.begin(starts)
                return
            if self.t > 30 and (self.skip(ctl) or any(p.pressed("bomb") for p in ctl.pads)):
                self.demo = None
                self.go("title")                             # any button brings the menu back
            elif self.mode == "story" and self.t > 240 * len(STORY):
                self.go("scores")
            elif self.mode == "scores" and self.t > 360:
                self.demo = World((0,), seed=7, god=True)
                self.apply("demo")
                self.go("demo")
            elif self.mode == "demo":
                self.bots[0].think(self.demo, self.demo.players[0])
                self.demo.step(self.bots)
                if self.t > 1500 or self.demo.locked:
                    self.demo = None
                    self.go("title")
        elif self.mode == "select":
            self.drift += 0.5
            self.select_step(ctl, starts)
        elif self.mode == "play":
            self.play_step(ctl, starts)
        elif self.mode in ("over", "clear"):
            if self.t > (240 if self.mode == "over" else 420) or (self.t > 90 and starts):
                if self.mode == "clear" and not self.world.stage.last:
                    self.world = self.world.advance()       # on to the next mission, the same team
                    audio.play("start")
                    self.go("play")
                else:
                    self.begin_entry()
        elif self.mode == "entry":
            self.entry_step(ctl)

    def begin(self, who):
        self.pending = sorted(set(who))
        self.demo = None
        self.go("select")

    def title_step(self, ctl):
        if any(p.pressed(b) for p in ctl.pads for b in ("up", "down", "left", "right", "fire", "jump", "bomb",
                                                         "start")):
            self.t = 1                                       # the attract loop waits for an idle menu
        if self.sub:
            self.sub_step(ctl)
            return
        choice = self.menu.step(ctl)
        if choice == "START GAME":
            if self.pay():
                self.begin([i for i, p in enumerate(ctl.pads)
                            if p.pressed("fire") or p.pressed("jump") or p.pressed("start")] or [0])
            else:
                audio.play("clank")
        elif choice in ("OPTIONS", "CONTROLS"):
            self.open(choice)
        elif choice == "HIGH SCORES":
            self.go("scores")
        elif choice == "QUIT":
            self.quit = True
        elif self.t > 600:
            self.go("story")

    def open(self, page):
        if page == "OPTIONS":
            self.sub = Options(self.opts, self.apply)
        else:
            dev = self.controls.device[0] if self.controls else "keyboard"
            self.sub = Layout(dev, self.opts["swap"] == "ON")

    def sub_step(self, ctl):
        if self.sub.step(ctl) == "back":
            self.close_sub()

    def close_sub(self):
        if isinstance(self.sub, Options):
            storage.save_options(self.opts)
        self.sub = None

    def back(self):
        """Esc: closes a page, resumes from pause, pauses play. Returns False when the game should quit."""
        if self.sub:
            self.close_sub()
        elif self.mode == "play" and self.feeble is None:
            self.toggle_pause()
        elif self.mode in ("story", "scores", "demo", "select"):
            if self.mode == "select" and not self.free_play:
                self.credits = min(9, self.credits + 1)     # the credit paid for this start comes back
            self.demo = None
            self.go("title")
        elif self.mode == "title":
            return WEB                                      # a browser tab cannot close itself
        return True

    def skip(self, ctl):
        return any(p.pressed("fire") or p.pressed("jump") for p in ctl.pads)

    def select_step(self, ctl, starts):
        i = LEVELS.index(self.level)
        for pad in ctl.pads:
            i += pad.pressed("down") - pad.pressed("up")
        if LEVELS[max(0, min(2, i))] != self.level:
            self.level = LEVELS[max(0, min(2, i))]
            audio.play("clank")
        if (self.t > 15 and (starts or self.skip(ctl))) or self.t > 900:
            self.start(self.pending)

    def feeble_step(self, ctl, starts):
        w = self.world
        for pad in ctl.pads:
            if pad.pressed("left") or pad.pressed("right") or pad.pressed("up") or pad.pressed("down"):
                self.feeble = 1 - self.feeble
                audio.play("clank")
        if self.t > 40 and (starts or self.skip(ctl)):
            if self.feeble == 0:
                w.set_level(LEVELS[LEVELS.index(w.level) - 1])
                w.popups.append([w.cam_x + W // 2, 90, w.level + " NOW", 90])
                audio.play("pickup")
            self.feeble = None

    def play_step(self, ctl, starts):
        w = self.world
        if self.paused:
            self.pause_step(ctl)
            return
        if self.feeble is not None:
            self.feeble_step(ctl, starts)
            return
        if (w.feeble_at and w.deaths - w.offered >= w.feeble_at and not w.cleared
                and not any(p and p.dying for p in w.players)):
            w.offered, self.feeble, self.t = w.deaths, 0, 0       # the offer comes back after as many deaths again
            audio.play("alarm")
            return
        for i in starts:
            p = w.players[i]
            if p and not p.out:
                self.toggle_pause()                         # start on a pad pauses, like a console
                return
            if p is None and self.pay():
                w.join(i)
                audio.play("start")
            elif p and p.out and getattr(p, "continue_t", 0) > 0 and self.pay():
                w.carry_on(i)
                audio.play("start")
        w.step(ctl.pads)
        if w.cleared:
            audio.music(False)                      # the boss is down: silence, then the tally
        else:
            stage_song, boss_song = w.stage.mission.song
            audio.music(True, boss_song if w.locked else stage_song)
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

    def pause_step(self, ctl):
        if self.sub:
            self.sub_step(ctl)
            return
        choice = self.pause_menu.step(ctl)
        if choice in ("RESUME", "back"):
            self.toggle_pause()
        elif choice in ("OPTIONS", "CONTROLS"):
            self.open(choice)
        elif choice == "QUIT TO TITLE":
            self.to_title()

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
            self.pause_menu.i = 0
            if self.paused:
                audio.music(False)                  # play_step brings the right song back
                audio.play("clank")

    def to_title(self):
        audio.music(False)
        self.world = None
        self.paused = False
        self.sub = None
        self.go("title")

    # ---------------------------------------------------------- drawing

    def draw(self, surf):
        if self.mode == "play" or (self.mode in ("over", "clear") and self.world):
            self.world.draw(surf, self.atlas)
            self.hud(surf, self.world)
            if self.mode == "play" and self.feeble is None:
                self.banners(surf)
            if self.paused and self.sub:
                self.shade(surf, 220)
                self.sub.draw(surf, self.t)
            elif self.paused:
                self.shade(surf, 190)
                font.draw(surf, "PAUSE", (W // 2, 70), C["cream"], 2, center=True)
                self.pause_menu.draw(surf, 100, self.t)
            if self.mode == "over":
                self.shade(surf)
                font.draw(surf, "GAME OVER", (W // 2, 100), C["red"], 3, center=True)
            if self.mode == "clear":
                self.tally(surf)
            if self.feeble is not None and self.mode == "play":
                self.feeble_offer(surf)
        elif self.mode == "demo" and self.demo:
            self.demo.draw(surf, self.atlas)
            self.hud(surf, self.demo)
            font.draw(surf, "DEMO PLAY", (W // 2, 40), C["cream"], center=True)
            self.prompt(surf, 190)
        elif self.mode == "select":
            self.backdrop(surf)
            font.draw(surf, "CHOOSE YOUR FIGHT", (W // 2, 44), C["sun"], 2, center=True)
            for k, name in enumerate(LEVELS):
                on = name == self.level
                y = 74 + k * 26
                font.draw(surf, name, (W // 2, y), C["cream"] if on else C["steel"], 2, center=True)
                if on:
                    x = W // 2 - font.width(name, 2) // 2 - 18
                    font.draw(surf, ">", (x + (self.t // 8) % 3, y), C["ember"], 2)
            font.draw(surf, LEVEL_LINES[self.level], (W // 2, 158), C["sun"], center=True)
            font.draw(surf, "UP DOWN CHOOSE   FIRE OR START GO", (W // 2, 184), C["steel_l"], center=True)
        elif self.mode == "story":
            self.backdrop(surf)
            self.shade(surf, 60)
            page, t = divmod(self.t, 240)
            lines = STORY[min(page, len(STORY) - 1)]
            shown = t // 2                                   # typed out, two frames a letter
            y = 72
            for line in lines:
                if shown <= 0:
                    break
                font.draw(surf, line[:shown], (W // 2 - font.width(line) // 2, y), C["cream"])
                shown -= len(line) + 4
                y += 14
            self.prompt(surf, 190)
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
            self.prompt(surf, 190)
        elif self.sub:
            self.backdrop(surf)
            self.shade(surf, 210)
            self.sub.draw(surf, self.t)
        else:
            self.backdrop(surf)
            bob = round(math.sin(self.t * 0.05) * 2)
            surf.blit(self.logo, (W // 2 - self.logo.get_width() // 2, 36 + bob))
            font.draw(surf, "ARCADE RUN AND GUN", (W // 2, 82), C["sun"], center=True)
            font.draw(surf, "HI %07d" % self.scores[0][1], (W // 2, 8), C["cream"], center=True)
            self.menu.draw(surf, 106, self.t)
            if not (self.free_play or self.credits) and self.t % 60 < 40:
                font.draw(surf, "INSERT COIN", (W // 2, 180), C["cream"], center=True)
            label = "FREE PLAY" if self.free_play else "CREDIT %d" % self.credits
            font.draw(surf, label, (W // 2, H - 10), C["steel_l"], center=True)
            font.draw(surf, "V" + __version__, (W - 4 - font.width("V" + __version__), H - 10), C["steel"])

    def feeble_offer(self, surf):
        w = self.world
        self.shade(surf, 170)
        shake = 1 if self.t < 20 and self.t % 4 < 2 else 0
        font.draw(surf, "TOO FEEBLE, SOLDIER?", (W // 2 + shake, 64), C["red"], 2, center=True)
        font.draw(surf, "%d DEATHS. THE LEGION IS LAUGHING." % w.deaths, (W // 2, 92), C["cream"], center=True)
        lower = LEVELS[LEVELS.index(w.level) - 1]
        for k, label in enumerate(("DROP TO " + lower, "I CAN TAKE IT")):
            on = k == self.feeble
            x = W // 2 + (-64 if k == 0 else 64)
            font.draw(surf, label, (x, 124), C["sun"] if on else C["steel"], center=True)
            if on:
                half = font.width(label) // 2 + 4
                pygame.draw.line(surf, C["ember"], (x - half, 134), (x + half, 134), 1)
        font.draw(surf, "LEFT RIGHT CHOOSE   FIRE CONFIRM", (W // 2, 160), C["steel_l"], center=True)

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
        if w is self.world:
            font.draw(surf, w.level, (W // 2, 14), C["steel"], center=True)
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
            if p.chain > 1:                                   # the kill chain: multiplier, and the time left
                mult = min(CHAIN_MAX, p.chain)
                col = C["red"] if mult == CHAIN_MAX and self.t % 8 < 4 else C["gold"]
                font.draw(surf, "CHAIN X%d" % mult, (x, 24), col)
                pygame.draw.rect(surf, C["ink"], (x + 52, 26, 32, 3))
                pygame.draw.rect(surf, col, (x + 52, 26, round(32 * p.chain_t / CHAIN_FRAMES), 3))
        if w.boss and w.boss.state == "fight":
            frac = max(0, w.boss.hp) / w.boss.HP
            pygame.draw.rect(surf, C["ink"], (W // 2 - 61, 26, 122, 6))
            pygame.draw.rect(surf, C["red"] if w.boss.angry else C["ember"], (W // 2 - 60, 27, round(120 * frac), 4))
            font.draw(surf, w.stage.mission.boss_title.split()[0], (W // 2, 34), C["cream"], center=True)

    def banners(self, surf):
        w = self.world
        if w.frame < 240:
            if w.frame < 170:
                m = w.stage.mission
                for k, line in enumerate(["MISSION %d" % m.number, m.name, ""] + m.briefing):
                    if w.frame > k * 12:
                        font.draw(surf, line, (W // 2, 60 + k * 12), C["sun"] if k < 2 else C["cream"],
                                  center=True)
            elif w.frame % 20 < 14:
                font.draw(surf, "GO!", (W // 2, 90), C["sun"], 3, center=True)
        elif w.locked and w.boss and w.boss.state == "enter" and w.frame % 30 < 20:
            font.draw(surf, "WARNING", (W // 2, 80), C["red"], 3, center=True)
            font.draw(surf, w.stage.mission.boss_title, (W // 2, 110), C["cream"], center=True)
        elif not w.locked and not any(0 < f.x - w.cam_x < W for f in w.foes) and (w.frame // 30) % 2:
            font.draw(surf, "GO >", (W - 50, 100), C["sun"], 2)

    def tally(self, surf):
        self.shade(surf)
        font.draw(surf, "MISSION COMPLETE", (W // 2, 60), C["sun"], 2, center=True)
        font.draw(surf, "PRISONERS FREED  %d" % self.world.hostages_freed, (W // 2, 96), C["cream"], center=True)
        font.draw(surf, "BONUS  %d" % self.bonus, (W // 2, 110), C["cream"], center=True)
        st = self.world.stage
        for k, line in enumerate(st.mission.outro):
            if self.t > 60 + k * 30:
                font.draw(surf, line, (W // 2, 134 + k * 12), C["steel_l"], center=True)
        if self.t > 150:
            font.draw(surf, "MORE MISSIONS SOON" if st.last else "NEXT  MISSION %d" % (st.mission.number + 1),
                      (W // 2, 172), C["sun"], center=True)
