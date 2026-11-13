"""On-screen controls for phones and tablets: a floating stick on the left half, buttons on the right.

They drive player 1 like a pad and stay hidden until the screen is first touched, so a keyboard or a pad never sees
them. Positions are in game pixels (320x224); App.touch_map turns the screen's 0..1 finger positions into those.
"""

import math

import pygame

from .controls import BUTTONS, eight_way
from .settings import C, H, W

STICK_R = 22                     # how far the thumb travels for a full push
# button: (centre, radius). Hit areas are a little larger than drawn: thumbs are wide.
KEYS = {
    "jump": ((292, 194), 17),
    "fire": ((252, 204), 15),
    "bomb": ((290, 152), 12),
    "start": ((160, 213), 8),
}
LABELS = {"jump": "JUMP", "fire": "FIRE", "bomb": "GR", "start": "II"}
SLACK = 7


def hit(x, y):
    """The button under a finger at (x, y), or None."""
    best = None
    for name, ((bx, by), r) in KEYS.items():
        d = math.hypot(x - bx, y - by)
        if d <= r + SLACK and (best is None or d < best[0]):
            best = (d, name)
    return best and best[1]


class Touch:
    def __init__(self):
        self.fingers = {}                # finger id -> ["stick", origin, now] or ["key", button name]
        self.used = False                # shown once the screen has been touched
        self.to_game = lambda nx, ny: (nx * W, ny * H)

    def handle(self, e):
        if e.type not in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return False
        key = (getattr(e, "touch_id", 0), e.finger_id)
        if e.type == pygame.FINGERUP:
            self.fingers.pop(key, None)
            return True
        x, y = self.to_game(e.x, e.y)
        if not (math.isfinite(x) and math.isfinite(y)):   # only a forged event; SDL sends real numbers
            return True
        f = self.fingers.get(key)
        if e.type == pygame.FINGERDOWN:
            self.used = True
            name = hit(x, y)
            if name:
                self.fingers[key] = ["key", name]
            elif x < W * 0.55:
                self.fingers[key] = ["stick", (x, y), (x, y)]
        elif f and f[0] == "stick":
            ox, oy = f[1]
            d = math.hypot(x - ox, y - oy)
            if d > STICK_R:                  # the base follows a thumb that runs past its edge
                ox, oy = x - (x - ox) * STICK_R / d, y - (y - oy) * STICK_R / d
            f[1], f[2] = (ox, oy), (x, y)
        elif f:
            f[1] = hit(x, y) or f[1]         # a thumb sliding from button to button
        return True

    def state(self):
        s = dict.fromkeys(BUTTONS, False)
        for f in self.fingers.values():
            if f[0] == "key":
                s[f[1]] = True
            else:
                dx, dy = eight_way((f[2][0] - f[1][0]) / STICK_R, (f[2][1] - f[1][1]) / STICK_R, 0.35)
                s["left"] |= dx < 0
                s["right"] |= dx > 0
                s["up"] |= dy < 0
                s["down"] |= dy > 0
        return s

    def draw(self, surf):
        if not self.used:
            return
        held = {f[1] for f in self.fingers.values() if f[0] == "key"}
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        for name, (centre, r) in KEYS.items():
            on = name in held
            pygame.draw.circle(layer, (*C["cream"], 120 if on else 50), centre, r)
            pygame.draw.circle(layer, (*C["cream"], 170), centre, r, 1)
        for f in self.fingers.values():
            if f[0] == "stick":
                pygame.draw.circle(layer, (*C["cream"], 40), [round(v) for v in f[1]], STICK_R)
                pygame.draw.circle(layer, (*C["cream"], 140), [round(v) for v in f[2]], 9)
        surf.blit(layer, (0, 0))
        from . import font
        for name, ((x, y), r) in KEYS.items():
            font.draw(surf, LABELS[name], (x, y - 3), C["cream"], center=True)
