"""Tuning and palette. Units are pixels and frames: the game steps at a fixed 60 Hz, like the cabinets."""

W, H = 320, 224            # the arcade screen; everything is drawn at this size, then scaled by whole steps
TILE = 16
FPS = 60
STEP = 1 / FPS
MAX_DT = 1 / 30            # a long hitch never runs more than two steps at once

GROUND_Y = 176             # top of the main floor
GRAVITY = 0.28             # for everything but the player, whose jump arc is tuned in actors.py
MAX_FALL = 6.0             # well under a tile a frame: nothing falls through a floor
RUN = 1.5
JUMP_V = -6.6              # a held jump tops out 58 px up: the stage's 3-tile (48 px) slabs, with room to spare
LIVES = 3
GRENADES = 10
RESPAWN_SAFE = 120         # frames of blinking safety after a respawn
CHAIN_FRAMES = 150         # a kill within this many frames of the last one grows the chain
CHAIN_MAX = 8              # the score multiplier tops out here

# Chosen before a game starts. lives, enemy wind-up before a shot (frames), enemy bullet speed (x),
# boss armour, respawn safety (frames), deaths before the game asks if you are too feeble
LEVELS = ("EASY", "NORMAL", "HARD")
DIFFICULTY = {
    "EASY": (5, 36, 0.8, 100, 180, None),
    "NORMAL": (3, 24, 1.0, 150, 120, 4),
    "HARD": (2, 16, 1.25, 200, 90, 3),
}

BULLET_V = 6.5             # a pistol shot crosses the screen in under a second
ENEMY_BULLET_V = 1.9

# weapon: (frames between shots when held, ammo given by the pickup, damage)
WEAPONS = {
    "P": (10, 0, 1),       # pistol, endless
    "H": (4, 160, 1),      # heavy gun
    "S": (12, 40, 1),      # spread: five pellets
    "R": (22, 20, 6),      # rockets: blast on impact
}

SCORE = {"soldier": 100, "lobber": 150, "drone": 200, "turret": 500, "hostage": 1000, "boss": 20000}

# A limited palette, in the spirit of 90s arcade boards.
C = {
    "black": (8, 6, 14),
    "ink": (22, 18, 36),
    "night": (40, 30, 66),
    "dusk": (86, 44, 98),
    "rose": (178, 66, 92),
    "ember": (236, 104, 52),
    "sun": (255, 196, 84),
    "cream": (255, 240, 200),
    "white": (255, 255, 255),
    "steel": (112, 120, 140),
    "steel_d": (64, 70, 88),
    "steel_l": (176, 186, 204),
    "rust": (150, 72, 40),
    "rust_d": (92, 42, 28),
    "olive": (96, 110, 58),
    "olive_d": (58, 68, 36),
    "skin": (232, 168, 120),
    "skin_d": (176, 110, 76),
    "cyan": (80, 226, 255),
    "blue": (48, 112, 220),
    "red": (226, 40, 52),
    "green": (96, 220, 96),
    "gold": (250, 210, 60),
}

# Player colours: P1 ember armour, P2 blue armour.
PLAYER_PAL = [
    {"A": C["ember"], "a": C["rust"], "V": C["cyan"]},
    {"A": C["blue"], "a": (30, 60, 140), "V": C["gold"]},
]
