"""Two players, keyboard and pads, seamless: whatever a player touched last is what the prompts show.

- Pads go through SDL's game-controller layer, so Xbox, DualShock 4, DualSense, Switch Pro and most other pads
  report the same buttons. Hot-plug works. Pad 1 is P1, pad 2 is P2; the keyboard drives both players at once
  (P1 on the arrows, P2 on WASD), so you can switch device mid-game without a menu.
- Stick: radial dead zone, then 8 clean directions for aiming.
- Rumble on pads that have it; the PlayStation light bar shows the player's colour.
- Without the controller layer (rare builds), plain joysticks are read with the usual XInput layout.
- In the browser SDL knows no pad mappings, so pads are plain joysticks in the W3C "standard" button order.
"""

import math
import sys

import pygame

WEB = sys.platform == "emscripten"

KEYBOARD, XBOX, PLAYSTATION, TOUCH = "keyboard", "xbox", "playstation", "touch"
BUTTONS = ("left", "right", "up", "down", "fire", "jump", "bomb", "start")
DEADZONE = 0.25
TRIGGER = 0.4

KEYS = [
    {"left": [pygame.K_LEFT], "right": [pygame.K_RIGHT], "up": [pygame.K_UP], "down": [pygame.K_DOWN],
     "fire": [pygame.K_z], "jump": [pygame.K_x], "bomb": [pygame.K_c], "start": [pygame.K_RETURN, pygame.K_1]},
    {"left": [pygame.K_a], "right": [pygame.K_d], "up": [pygame.K_w], "down": [pygame.K_s],
     "fire": [pygame.K_g], "jump": [pygame.K_h], "bomb": [pygame.K_j], "start": [pygame.K_2]},
]
COIN_KEYS = (pygame.K_5,)

# What each action is called on each device (P1 keys; P2 keys are in KEYS_P2).
PROMPTS = {
    "move": ("ARROWS", "STICK / D-PAD", "STICK / D-PAD"),
    "fire": ("Z", "X / RT", "SQUARE / R2"),
    "jump": ("X", "A", "CROSS"),
    "bomb": ("C", "B / RB", "CIRCLE / R1"),
    "start": ("ENTER", "MENU", "OPTIONS"),
    "coin": ("5", "VIEW", "CREATE"),
}
SWAPPED = {"fire": ("A / RT", "CROSS / R2"), "jump": ("X", "SQUARE")}
TOUCH_NAMES = {"move": "LEFT THUMB", "fire": "FIRE", "jump": "JUMP", "bomb": "GR", "start": "II", "coin": "5"}
KEYS_P2 = {"move": "WASD", "fire": "G", "jump": "H", "bomb": "J", "start": "2", "coin": "5"}

# Rumble (low, high, ms) for game moments.
FEEL = {
    "shot": (0.0, 0.10, 40), "heavy": (0.05, 0.18, 40), "boom": (0.45, 0.35, 160), "big_boom": (1.0, 0.9, 700),
    "hurt": (0.9, 0.7, 400), "land": (0.15, 0.0, 50), "pickup": (0.0, 0.3, 80), "knife": (0.3, 0.5, 80),
}
PLAYSTATION_WORDS = ("dualsense", "dualshock", "playstation", "ps4", "ps5", "wireless controller", "054c")
LIGHTS = [(255, 110, 40), (40, 110, 255)]


def eight_way(x, y, deadzone=DEADZONE):
    """A stick position -> (-1|0|1, -1|0|1) in 8 equal sectors, after a radial dead zone."""
    if math.hypot(x, y) <= deadzone:
        return 0, 0
    sector = round(math.atan2(y, x) / (math.pi / 4)) % 8
    return [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)][sector]


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


class _Device:
    swap = False                               # the options' "swap fire and jump": the two face buttons trade

    def __init__(self, index, use_controller):
        if use_controller:
            from pygame._sdl2 import controller
            self.ctl = controller.Controller(index)
            self.joy = None
            self.name = self.ctl.name or ""
            self.id = self.ctl.as_joystick().get_instance_id()
        else:
            self.ctl = None
            self.joy = pygame.joystick.Joystick(index)
            self.name = self.joy.get_name() or ""
            self.id = self.joy.get_instance_id()
        self.kind = PLAYSTATION if any(w in self.name.lower() for w in PLAYSTATION_WORDS) else XBOX
        self.web = WEB
        self.coin_was = False

    def state(self):
        """Buttons from this pad, plus whether it was touched at all (for the prompts)."""
        s = dict.fromkeys(BUTTONS, False)
        if self.ctl:
            c, b = self.ctl, self.ctl.get_button
            lx, ly = c.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32767, c.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32767
            rt = c.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767
            dx, dy = eight_way(lx, ly)
            dx += b(pygame.CONTROLLER_BUTTON_DPAD_RIGHT) - b(pygame.CONTROLLER_BUTTON_DPAD_LEFT)
            dy += b(pygame.CONTROLLER_BUTTON_DPAD_DOWN) - b(pygame.CONTROLLER_BUTTON_DPAD_UP)
            a, x = b(pygame.CONTROLLER_BUTTON_A), b(pygame.CONTROLLER_BUTTON_X)
            if self.swap:
                a, x = x, a
            s["jump"] = bool(a)
            s["fire"] = bool(x) or rt > TRIGGER
            s["bomb"] = bool(b(pygame.CONTROLLER_BUTTON_B) or b(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER))
            s["start"] = bool(b(pygame.CONTROLLER_BUTTON_START))
            coin = bool(b(pygame.CONTROLLER_BUTTON_BACK))
        else:
            j = self.joy
            ax = j.get_axis(0) if j.get_numaxes() > 0 else 0.0
            ay = j.get_axis(1) if j.get_numaxes() > 1 else 0.0
            hx, hy = j.get_hat(0) if j.get_numhats() else (0, 0)
            b = lambda n: j.get_numbuttons() > n and j.get_button(n)
            dx, dy = eight_way(ax, ay)
            if self.web:                       # W3C standard: A B X Y LB RB LT RT BACK START LS RS UP DOWN LEFT RIGHT
                dx += b(15) - b(14)
                dy += b(13) - b(12)
                s["jump"] = bool(b(2 if self.swap else 0))
                s["fire"] = bool(b(0 if self.swap else 2) or b(7))
                s["bomb"] = bool(b(1) or b(5))
                s["start"] = bool(b(9))
                coin = bool(b(8))
            else:
                dx += hx
                dy -= hy
                s["jump"] = bool(b(2 if self.swap else 0))
                s["fire"] = bool(b(0 if self.swap else 2) or b(1))
                s["bomb"] = bool(b(3) or b(5))
                s["start"] = bool(b(7))
                coin = bool(b(6))
        s["left"], s["right"], s["up"], s["down"] = dx < 0, dx > 0, dy < 0, dy > 0
        coin_pressed = coin and not self.coin_was
        self.coin_was = coin
        return s, any(s.values()), coin_pressed

    def rumble(self, low, high, ms):
        dev = self.ctl or self.joy
        try:
            dev.rumble(low, high, ms)
        except (pygame.error, AttributeError):
            pass

    def light(self, colour):
        if self.ctl and self.kind == PLAYSTATION:
            try:
                self.ctl.set_led(colour)
            except (pygame.error, AttributeError):
                pass


class Controls:
    def __init__(self):
        self.pads = [Pad(), Pad()]
        self.devices = []                     # in the order they were plugged in: [0] is P1's, [1] P2's
        self.device = [KEYBOARD, KEYBOARD]    # what each player touched last
        self.coin = False
        self.rumble_on = True
        self.swap = False                     # pads: fire and jump trade face buttons
        self.use_controller = False
        from .touch import Touch                 # here, not at the top: touch.py reads this module
        self.touch = Touch()                  # on-screen controls for player 1 on a phone or tablet
        try:
            if not WEB:
                from pygame._sdl2 import controller
                controller.init()
                self.use_controller = True
        except (ImportError, pygame.error):
            pass
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self._open(i)

    def _open(self, index):
        try:
            if self.use_controller:
                from pygame._sdl2 import controller
                if not controller.is_controller(index):
                    return
            dev = _Device(index, self.use_controller)
        except (pygame.error, IndexError):
            return
        if all(d.id != dev.id for d in self.devices):
            self.devices.append(dev)
            self._lights()

    def _lights(self):
        for i, d in enumerate(self.devices[:2]):
            d.light(LIGHTS[i])

    def handle(self, e):
        """Hot-plug and touches. Call with every event."""
        if self.touch.handle(e):
            return
        if e.type in (pygame.JOYDEVICEADDED, getattr(pygame, "CONTROLLERDEVICEADDED", -1)):
            self._open(e.device_index)
        elif e.type in (pygame.JOYDEVICEREMOVED, getattr(pygame, "CONTROLLERDEVICEREMOVED", -1)):
            self.devices = [d for d in self.devices if d.id != e.instance_id]
            self._lights()

    def read(self, events=()):
        keys = pygame.key.get_pressed()
        self.coin = any(e.type == pygame.KEYDOWN and e.key in COIN_KEYS for e in events)
        for i, pad in enumerate(self.pads):
            state = {b: any(keys[k] for k in KEYS[i][b]) for b in BUTTONS}
            if any(state.values()):
                self.device[i] = KEYBOARD
            if i == 0 and self.touch.fingers:
                state = {b: v or self.touch.state()[b] for b, v in state.items()}
                self.device[0] = TOUCH
            if i < len(self.devices):
                self.devices[i].swap = self.swap
                try:
                    pstate, touched, coin = self.devices[i].state()
                except pygame.error:
                    pstate, touched, coin = {}, False, False
                for b, v in pstate.items():
                    state[b] = state[b] or v
                if touched:
                    self.device[i] = self.devices[i].kind
                self.coin |= coin
            pad.set(state)

    def any_start(self):
        return [i for i, p in enumerate(self.pads) if p.pressed("start")]

    def prompt(self, action, player=0):
        if self.device[player] == TOUCH:
            return TOUCH_NAMES[action]
        if self.device[player] == KEYBOARD:
            return PROMPTS[action][0] if player == 0 else KEYS_P2[action]
        kind = 1 if self.device[player] == XBOX else 2
        if self.swap and action in SWAPPED:
            return SWAPPED[action][kind - 1]
        return PROMPTS[action][kind]

    def feel(self, player, moment):
        spec = FEEL.get(moment)
        if spec and self.rumble_on and player < len(self.devices):
            dev, now = self.devices[player], pygame.time.get_ticks()
            low, high, ms = spec
            # a weaker buzz never cuts a stronger one that is still running
            if now < getattr(dev, "busy_until", 0) and low + high < getattr(dev, "busy_power", 0):
                return
            dev.busy_until, dev.busy_power = now + ms, low + high
            dev.rumble(low, high, ms)

    def close(self):
        for d in self.devices:
            d.rumble(0, 0, 1)
