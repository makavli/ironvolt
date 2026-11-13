"""Two players on one keyboard and/or gamepads, read as one small state per player each frame.

P1: arrows, Z fire, X jump, C grenade, Enter or 1 start.   P2: WASD, G fire, H jump, J grenade, 2 start.
Coin: 5 (or a pad's Back). Pads: A jump, B/X fire, Y/RB grenade, Start start. Pad 1 is P1, pad 2 is P2.
"""

import pygame

KEYS = [
    {"left": [pygame.K_LEFT], "right": [pygame.K_RIGHT], "up": [pygame.K_UP], "down": [pygame.K_DOWN],
     "fire": [pygame.K_z], "jump": [pygame.K_x], "bomb": [pygame.K_c], "start": [pygame.K_RETURN, pygame.K_1]},
    {"left": [pygame.K_a], "right": [pygame.K_d], "up": [pygame.K_w], "down": [pygame.K_s],
     "fire": [pygame.K_g], "jump": [pygame.K_h], "bomb": [pygame.K_j], "start": [pygame.K_2]},
]
BUTTONS = ("left", "right", "up", "down", "fire", "jump", "bomb", "start")
DEAD = 0.45


class Pad:
    """One player's buttons this frame, with presses (down this frame, up the frame before)."""

    def __init__(self):
        self.now = dict.fromkeys(BUTTONS, False)
        self.before = dict(self.now)

    def set(self, state):
        self.before, self.now = self.now, state

    def held(self, b):
        return self.now[b]

    def pressed(self, b):
        return self.now[b] and not self.before[b]

    def axis(self):
        return (self.now["right"] - self.now["left"], self.now["down"] - self.now["up"])


class Controls:
    def __init__(self):
        self.pads = [Pad(), Pad()]
        self.coin = False
        self.joys = []
        self.refresh()

    def refresh(self):
        """Call on JOYDEVICEADDED / REMOVED."""
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        self.joys = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

    def read(self, events=()):
        keys = pygame.key.get_pressed()
        self.coin = any(e.type == pygame.KEYDOWN and e.key == pygame.K_5 for e in events)
        for i, pad in enumerate(self.pads):
            state = {b: any(keys[k] for k in KEYS[i][b]) for b in BUTTONS}
            if i < len(self.joys):
                self._merge(self.joys[i], state, events)
            pad.set(state)

    def _merge(self, j, state, events):
        try:
            ax = j.get_axis(0) if j.get_numaxes() > 0 else 0.0
            ay = j.get_axis(1) if j.get_numaxes() > 1 else 0.0
            hx, hy = j.get_hat(0) if j.get_numhats() else (0, 0)
            b = lambda n: j.get_numbuttons() > n and j.get_button(n)
        except pygame.error:
            return
        state["left"] |= ax < -DEAD or hx < 0
        state["right"] |= ax > DEAD or hx > 0
        state["up"] |= ay < -DEAD or hy > 0
        state["down"] |= ay > DEAD or hy < 0
        state["jump"] |= bool(b(0))
        state["fire"] |= bool(b(1) or b(2))
        state["bomb"] |= bool(b(3) or b(5))
        state["start"] |= bool(b(7))
        if any(e.type == pygame.JOYBUTTONDOWN and e.button == 6 and e.instance_id == j.get_instance_id()
               for e in events):
            self.coin = True

    def any_start(self):
        return [i for i, p in enumerate(self.pads) if p.pressed("start")]
