"""Menus: a cursor list (main menu, pause), the options page and the controls layout page.

Every pad steers them: up/down moves, left/right changes a value, fire, jump or start confirms, grenade goes back.
"""

import sys

import pygame

from . import audio, font
from .settings import C, W
from .storage import OPTIONS

WEB = sys.platform == "emscripten"


def nav(ctl):
    """This step's (up/down, left/right, confirm, back) from every pad at once."""
    dy = dx = 0
    ok = back = False
    for p in ctl.pads:
        dy += p.pressed("down") - p.pressed("up")
        dx += p.pressed("right") - p.pressed("left")
        ok = ok or p.pressed("fire") or p.pressed("jump") or p.pressed("start")
        back = back or p.pressed("bomb")
    return max(-1, min(1, dy)), max(-1, min(1, dx)), ok, back


class Menu:
    """A vertical list. step() returns the item confirmed, "back", or None."""

    def __init__(self, items):
        self.items, self.i = list(items), 0

    def step(self, ctl):
        dy, _, ok, back = nav(ctl)
        if dy:
            self.i = (self.i + dy) % len(self.items)
            audio.play("clank")
        if ok:
            audio.play("pickup")
            return self.items[self.i]
        return "back" if back else None

    def draw(self, surf, y, t, gap=13):
        for k, item in enumerate(self.items):
            on = k == self.i
            font.draw(surf, item, (W // 2, y + k * gap), C["cream"] if on else C["steel"], center=True)
            if on:
                x = W // 2 - font.width(item) // 2 - 12
                font.draw(surf, ">", (x + (t // 8) % 3, y + k * gap), C["ember"])


ROWS = [
    ("GAME", None), ("DIFFICULTY", "level"), ("LIVES", "lives"), ("ENEMIES", "enemies"),
    ("ENEMY FIRE", "enemy_fire"), ("TOO FEEBLE OFFER", "feeble"),
    ("FREE PLAY", "free_play"),
    ("VIDEO", None), ("FULLSCREEN", "fullscreen"), ("SCALING", "scale"), ("CRT LINES", "crt"),
    ("AUDIO", None), ("MUSIC", "music"), ("EFFECTS", "sfx"),
    ("PADS", None), ("RUMBLE", "rumble"), ("SWAP FIRE AND JUMP", "swap"),
    ("ACCESSIBILITY", None), ("SCREEN SHAKE", "shake"), ("FLASHES", "flashes"), ("GAME SPEED", "speed"),
    ("BACK", "back"),
]
SHOWN = 20                                     # option rows on screen at once
WEB_HIDDEN = ("fullscreen", "scale")              # the page's own fullscreen button does these


class Options:
    """The options page. Changes apply at once (on_change(key)) and are saved when the page is left."""

    def __init__(self, opts, on_change=lambda key: None):
        self.opts, self.on_change = opts, on_change
        self.rows = [r for r in ROWS if not (WEB and r[1] in WEB_HIDDEN)]
        self.picks = [k for k, r in enumerate(self.rows) if r[1]]
        self.i = 0

    @property
    def key(self):
        return self.rows[self.picks[self.i]][1]

    def step(self, ctl):
        dy, dx, ok, back = nav(ctl)
        if dy:
            self.i = (self.i + dy) % len(self.picks)
            audio.play("clank")
        if self.key == "back":
            return "back" if ok or back else None
        if dx or ok:
            choices = OPTIONS[self.key]
            k = choices.index(self.opts[self.key])
            k = (k + (dx or 1)) % len(choices) if ok else max(0, min(len(choices) - 1, k + dx))
            if choices[k] != self.opts[self.key]:
                self.opts[self.key] = choices[k]
                self.on_change(self.key)
                audio.play("clank")
        return "back" if back else None

    def draw(self, surf, t):
        font.draw(surf, "OPTIONS", (W // 2, 6), C["sun"], 2, center=True)
        y = 26
        sel = self.picks[self.i]
        top = max(0, min(sel - 9, len(self.rows) - SHOWN))   # more rows than fit: the list scrolls with the cursor
        for k, (label, key) in enumerate(self.rows):
            if not top <= k < top + SHOWN:
                continue
            on = k == sel
            if key is None:
                font.draw(surf, label, (40, y), C["ember"])
            elif key == "back":
                font.draw(surf, label, (W // 2, y + 2), C["cream"] if on else C["steel"], center=True)
            else:
                font.draw(surf, label, (52, y), C["cream"] if on else C["steel_l"])
                value = self.opts[key]
                font.draw(surf, "< %s >" % value if on else value, (236, y), C["sun"] if on else C["steel"],
                          center=True)
            if on:
                font.draw(surf, ">", (40 + (t // 8) % 3 if key != "back" else W // 2 - 26, y + (key == "back") * 2),
                          C["ember"])
            y += 9
        font.draw(surf, "UP DOWN CHOOSE  LEFT RIGHT CHANGE  GRENADE BACK", (W // 2, 214), C["steel"], center=True)


# The controls page. Pad buttons: (name on an Xbox pad, on a PlayStation pad, action, where it is on the drawing,
# where its label goes, which side of the pad the label is on). Placed by hand so no two lines cross.
PAD = [
    ("VIEW", "CREATE", "COIN", (151, 104), (8, 58), "L"),
    ("STICK", "STICK", "MOVE / AIM", (134, 112), (8, 96), "L"),
    ("D-PAD", "D-PAD", "MOVE / AIM", (148, 132), (8, 130), "L"),
    ("MENU", "OPTIONS", "START / PAUSE", (169, 104), (110, 50), "T"),
    ("RB", "R1", "GRENADE", (190, 87), (228, 50), "R"), ("RT", "R2", "FIRE", (200, 84), (228, 76), "R"),
    ("B", "CIRCLE", "GRENADE", (196, 112), (228, 102), "R"), ("X", "SQUARE", "FIRE", (180, 112), (228, 128), "R"),
    ("A", "CROSS", "JUMP", (188, 120), (228, 154), "R"),
]
KEYBOARD = [
    ("MOVE / AIM", "ARROWS", "WASD"), ("FIRE", "Z", "G"), ("JUMP", "X", "H"), ("GRENADE", "C", "J"),
    ("START", "ENTER", "2"), ("COIN", "5", "5"), ("CROUCH", "DOWN", "S"), ("SLIDE / DROP", "DOWN+JUMP", "S+H"),
    ("KNIFE", "Z UP CLOSE", "G UP CLOSE"),
]
SYSTEM = [("PAUSE", "ESC"), ("FULLSCREEN", "F11"), ("CRT LINES", "F2"), ("FREE PLAY", "F3")]


class Layout:
    """Left/right flips between the keyboard and the pad; it opens on what player 1 used last."""

    def __init__(self, device, swap=False):
        self.page = 0 if device == "keyboard" else 1
        self.ps = device == "playstation"
        self.swap = swap

    def step(self, ctl):
        _, dx, ok, back = nav(ctl)
        if dx:
            self.page = 1 - self.page
            audio.play("clank")
        return "back" if ok or back else None

    def draw(self, surf, t):
        font.draw(surf, "CONTROLS", (W // 2, 6), C["sun"], 2, center=True)
        tabs = ("KEYBOARD", "PLAYSTATION PAD" if self.ps else "PAD")
        for k, tab in enumerate(tabs):
            x = W // 2 + (-60 if k == 0 else 60)
            font.draw(surf, tab, (x, 28), C["cream"] if k == self.page else C["steel"], center=True)
            if k == self.page:
                half = font.width(tab) // 2 + 3
                pygame.draw.line(surf, C["ember"], (x - half, 37), (x + half, 37))
        (self.draw_keys if self.page == 0 else self.draw_pad)(surf)
        font.draw(surf, "LEFT RIGHT FLIP   FIRE OR GRENADE BACK", (W // 2, 214), C["steel"], center=True)

    def draw_keys(self, surf):
        font.draw(surf, "P1", (190, 48), C["ember"], center=True)
        font.draw(surf, "P2", (262, 48), C["cyan"], center=True)
        for k, (action, p1, p2) in enumerate(KEYBOARD):
            y = 60 + k * 12
            font.draw(surf, action, (30, y), C["steel_l"])
            font.draw(surf, p1, (190, y), C["cream"], center=True)
            font.draw(surf, p2, (262, y), C["cream"], center=True)
        for k, (action, key) in enumerate(SYSTEM):
            x, y = 30 + (k % 2) * 140, 168 + (k // 2) * 12
            font.draw(surf, action, (x, y), C["steel_l"])
            font.draw(surf, key, (x + 100, y), C["sun"])

    def draw_pad(self, surf):
        ink, body, light = C["ink"], C["steel_d"], C["steel"]
        for x in (122, 198):                                         # the grips, then the shell
            pygame.draw.circle(surf, ink, (x, 140), 16)
            pygame.draw.circle(surf, body, (x, 140), 14)
        pygame.draw.rect(surf, ink, (106, 90, 108, 56), border_radius=16)
        pygame.draw.rect(surf, body, (108, 92, 104, 52), border_radius=14)
        for x in (114, 182):
            pygame.draw.rect(surf, light, (x, 84, 24, 5), border_radius=2)
        pygame.draw.circle(surf, ink, (134, 112), 8)
        pygame.draw.circle(surf, light, (134, 112), 6)
        pygame.draw.rect(surf, ink, (145, 125, 7, 15))
        pygame.draw.rect(surf, ink, (141, 129, 15, 7))
        pygame.draw.circle(surf, light, (151, 104), 2)
        pygame.draw.circle(surf, light, (169, 104), 2)
        face = {"X": C["blue"], "A": C["green"], "B": C["red"]}
        for name, colour in face.items():
            spot = next(p[3] for p in PAD if p[0] == name)
            pygame.draw.circle(surf, ink, spot, 4)
            pygame.draw.circle(surf, colour, spot, 3)
        pygame.draw.circle(surf, C["gold"], (188, 104), 3)              # Y: not used
        for xb, ps, action, spot, (x, y), side in PAD:
            if self.swap and xb in ("X", "A"):
                action = "JUMP" if action == "FIRE" else "FIRE"
            font.draw(surf, ps if self.ps else xb, (x, y), C["sun"])
            font.draw(surf, action, (x, y + 9), C["cream"])
            end = {"L": (x + 82, y + 8), "T": (spot[0], y + 18), "R": (x - 4, y + 8)}[side]
            pygame.draw.line(surf, C["steel_l"], end, spot)
        font.draw(surf, "SWAP FIRE AND JUMP IN OPTIONS", (W // 2, 190), C["steel"], center=True)
