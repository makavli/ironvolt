"""Every picture in the game, made in code at start-up: pixel sprites from text maps, tiles, parallax layers.

Sprites are drawn without outlines; `outlined()` adds the hard dark rim arcade sprites have.
Nothing here needs a display, so tests can build all of it headless.
"""

import math
import random

import pygame

from .settings import C, H, PLAYER_PAL, TILE, W

INK = C["ink"]

# Shared characters in the text maps.
BASE_PAL = {
    "H": C["steel_l"], "h": C["steel"], "s": C["skin"], "S": C["skin_d"], "b": C["rust_d"], "y": C["gold"],
    "P": C["night"], "p": C["dusk"], "K": C["black"], "w": C["white"], "c": C["cream"],
}

TOP = [
    "......HHH.......",
    ".....HHHhh......",
    ".....HhhVVVV....",
    ".....hhhVVVV....",
    ".....sssssss....",
    "......Ssss......",
    ".....aAAAAa.....",
    "....aAAAyAAa....",
    "....aAAAAAAa....",
    "....aaAAAAaa....",
    ".....bbbbbb.....",
]
FOE_TOP = [
    "......ooo.......",
    ".....oOOOOo.....",
    "....oOOOOOOo....",
    "....oOORRRRR....",
    ".....omMMMMm....",
    "......MmMM......",
    ".....gGGGGg.....",
    "....gGGGGGGg....",
    "....gGGwGGGg....",
    "....ggGGGGgg....",
    ".....bbbbbb.....",
]
LEGS = {
    "stand": [
        ".....PPPPPPP....", ".....PPP.PPP....", ".....PpP.PpP....", ".....PPP.PPP....",
        ".....PPP.PPP....", ".....PPP.PPP....", ".....PpP.PpP....", ".....PPP.PPP....",
        "....KKKK.KKKK...", "....KKKK.KKKKK..",
    ],
    "run0": [
        ".....PPPPPPP....", ".....PPP.PPPP...", "....PPP...PPP...", "....PP.....PPP..",
        "...PPP......PP..", "..KPP.......PP..", ".KKK........PP..", ".KK.........PP..",
        "...........KKKK.", "...........KKKKK",
    ],
    "run1": [
        ".....PPPPPPP....", ".....PPPPPPP....", "......PPPPP.....", "......PPPPPP....",
        "......PP.PPP....", "......PP..KKK...", "......PP........", "......PP........",
        ".....KKKK.......", ".....KKKKK......",
    ],
    "run2": [
        ".....PPPPPPP....", ".....PPPP.PPP...", "....PPP....PPP..", "....PP......PPP.",
        "...PP........PPK", "...PP.......KKK.", "...PP...........", "...PP...........",
        "..KKKK..........", "..KKKKK.........",
    ],
    "run3": [
        ".....PPPPPPP....", ".....PPPPPPP....", ".....PPPPP......", "....PPPPPP......",
        "....PPP.PP......", "...KKK..PP......", "........PP......", "........PP......",
        ".......KKKK.....", ".......KKKKK....",
    ],
    "jump": [
        ".....PPPPPPP....", "....PPPP.PPPP...", "...PPP....PPP...", "...PP....PPP....",
        "..KKK...KKK.....", "..KK....KK......", "................", "................",
        "................", "................",
    ],
    "crouch": [
        "....PPPPPPPPP...", "...PPPPP.PPPPP..", "...PP.....PPPP..", "..KKKK....KKKK..",
        "..KKKKK...KKKKK.",
    ],
}
HOSTAGE = [
    "....cccc......", "...cccccc.....", "...sSssss.....", "...sKsKss.....", "...bbbbbb.....",
    "....bbbb......", "..cccccccc....", "..cyyyyyyc....", "..cccccccc....", "...sscccss....",
    "..PPPPPPPP....", ".PPPPPPPPPP...", ".KK......KK...",
]
HOSTAGE_FREE = [
    "s...cccc...s..", "s..cccccc..s..", "ss.sSssss.ss..", ".sssKsKsss....", "...bbbbbb.....",
    "....bbbb......", "..cccccccc....", "..cccccccc....", "..cccccccc....", "...cccccc.....",
    "...PPPPPP.....", "...PP..PP.....", "..KKK..KKK....",
]
DRONE = [
    [
        "..LLLLLL..LLLLLL..", "........mm........", ".....mmMMMMmm.....", "...mMMMMMMMMMMm...",
        "..mMMRRMMMMMMMMm..", "..mmMMMMMMMMMMmm..", "....mmmmmmmmmm....", ".....m......m.....",
        "....mm......mm....",
    ],
    [
        "....LLLLLLLLLL....", "........mm........", ".....mmMMMMmm.....", "...mMMMMMMMMMMm...",
        "..mMMMMRRMMMMMMm..", "..mmMMMMMMMMMMmm..", "....mmmmmmmmmm....", ".....m......m.....",
        "....mm......mm....",
    ],
]


def sprite(rows, pal):
    width = max(len(r) for r in rows)
    surf = pygame.Surface((width, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), pal[ch])
    return surf


def outlined(surf, colour=INK):
    """Adds a 1-pixel dark rim around the opaque pixels (the canvas grows by 1 on each side)."""
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    rim = pygame.mask.from_surface(surf).to_surface(setcolor=colour, unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(rim, (dx, dy))
    out.blit(surf, (1, 1))
    return out


def white(surf):
    """The hit flash: the same shape in solid white."""
    return pygame.mask.from_surface(surf).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))


def flipped(frames):
    return [pygame.transform.flip(f, True, False) for f in frames]


def _soldier(top, pal):
    frames = {}
    for name, legs in LEGS.items():
        rows = (top[3:] if name == "crouch" else top) + legs
        frames[name] = outlined(sprite(rows, pal))
    return frames


def player_frames(index):
    pal = dict(BASE_PAL, **PLAYER_PAL[index])
    return _soldier(TOP, pal)


def foe_frames(armour=C["olive"], armour_d=C["olive_d"]):
    pal = dict(BASE_PAL, O=C["steel_d"], o=C["ink"], R=C["red"], M=C["steel"], m=C["steel_d"],
               G=armour, g=armour_d, P=C["rust_d"], p=C["rust"])
    return _soldier(FOE_TOP, pal)


def hostage_frames():
    pal = dict(BASE_PAL)
    return [outlined(sprite(HOSTAGE, pal)), outlined(sprite(HOSTAGE_FREE, pal))]


def drone_frames():
    pal = {"L": C["steel_l"], "m": C["steel_d"], "M": C["steel"], "R": C["red"]}
    return [outlined(sprite(rows, pal)) for rows in DRONE]


def capsule(letter, colour):
    """A weapon pickup: a rounded crate with a big letter."""
    from . import font
    s = pygame.Surface((14, 12), pygame.SRCALPHA)
    pygame.draw.rect(s, C["ink"], (0, 0, 14, 12), border_radius=3)
    pygame.draw.rect(s, colour, (1, 1, 12, 10), border_radius=2)
    pygame.draw.line(s, C["white"], (3, 2), (10, 2))
    font.draw(s, letter, (4, 3), C["white"], shadow=C["ink"])
    return s


def glow(radius, colour):
    """A soft additive light: blit with BLEND_ADD for muzzle flashes and explosions."""
    size = radius * 2 + 1
    s = pygame.Surface((size, size))
    for r in range(radius, 0, -1):
        t = (1 - r / radius) ** 2
        pygame.draw.circle(s, [int(c * t) for c in colour], (radius, radius), r)
    return s


# ---------------------------------------------------------------- tiles

def _hash(x, y, seed=0):
    return (x * 73856093 ^ y * 19349663 ^ seed * 83492791) & 0xFFFF


def ground_tile(tx, ty, top):
    """Industrial ground: a riveted steel lip on top, packed rust and slag below."""
    s = pygame.Surface((TILE, TILE))
    rnd = random.Random(_hash(tx, ty))
    s.fill(C["rust_d"])
    for _ in range(18):
        x, y = rnd.randrange(TILE), rnd.randrange(TILE)
        s.set_at((x, y), C["rust"] if rnd.random() < 0.6 else C["ink"])
    if rnd.random() < 0.25:                          # a buried pipe or rock
        y = rnd.randrange(6, 13)
        pygame.draw.line(s, C["steel_d"], (0, y), (TILE, y), 2)
        pygame.draw.line(s, C["steel"], (0, y), (TILE, y))
    if top:
        pygame.draw.rect(s, C["steel_d"], (0, 0, TILE, 5))
        pygame.draw.line(s, C["steel_l"], (0, 0), (TILE, 0))
        pygame.draw.line(s, C["steel"], (0, 1), (TILE, 1))
        pygame.draw.line(s, C["ink"], (0, 5), (TILE, 5))
        for rx in (3, 12):
            s.set_at((rx, 3), C["steel_l"])
            s.set_at((rx + 1, 4), C["ink"])
        if rnd.random() < 0.3:                       # rust streak
            x = rnd.randrange(2, 14)
            pygame.draw.line(s, C["rust"], (x, 2), (x, 8))
    return s


def crate_tile():
    s = pygame.Surface((TILE, TILE))
    s.fill(C["rust"])
    pygame.draw.rect(s, C["ink"], (0, 0, TILE, TILE), 1)
    pygame.draw.rect(s, C["rust_d"], (2, 2, 12, 12), 1)
    pygame.draw.line(s, C["rust_d"], (2, 2), (13, 13), 2)
    pygame.draw.line(s, C["rust_d"], (13, 2), (2, 13), 2)
    pygame.draw.line(s, C["ember"], (1, 1), (14, 1))
    for p in ((2, 2), (13, 2), (2, 13), (13, 13)):
        s.set_at(p, C["steel_l"])
    return s


def girder_tile():
    """A one-way catwalk: you can jump up through it and stand on it."""
    s = pygame.Surface((TILE, 6), pygame.SRCALPHA)
    pygame.draw.rect(s, C["steel_d"], (0, 0, TILE, 6))
    pygame.draw.line(s, C["steel_l"], (0, 0), (TILE, 0))
    for x in range(0, TILE, 4):
        pygame.draw.line(s, C["ink"], (x, 2), (x + 3, 5))
    pygame.draw.line(s, C["ink"], (0, 5), (TILE, 5))
    return s


# ---------------------------------------------------------------- backgrounds

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def sky():
    """Dusk sky in dithered bands, with a striped low sun. One screen, it does not scroll."""
    bands = [C["black"], C["ink"], C["night"], C["dusk"], C["rose"], C["ember"], C["sun"]]
    s = pygame.Surface((W, H))
    horizon = 150
    for y in range(H):
        t = min(1.0, y / horizon) * (len(bands) - 1)
        i = int(t)
        f = t - i
        for x in range(W):
            j = i + 1 if f * 16 > BAYER[y % 4][x % 4] and i + 1 < len(bands) else i
            s.set_at((x, y), bands[j])
    rnd = random.Random(7)
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(60)
        s.set_at((x, y), C["cream"] if rnd.random() < 0.3 else C["steel"])
    cx, cy, r = 228, 120, 34                         # the sun, cut by horizontal bars like a heat haze
    for y in range(cy - r, cy + r):
        half = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
        if y > cy - 6 and (y - cy) % 6 < (y - cy) // 6 + 1:
            continue
        colour = C["cream"] if y < cy - 16 else C["sun"] if y < cy + 6 else C["ember"]
        pygame.draw.line(s, colour, (cx - half, y), (cx + half, y))
    return s


def _ridge(width, base, amp, rnd, rough):
    pts, y = [], base
    for x in range(0, width + 1, 4):
        y += rnd.uniform(-rough, rough)
        y = max(base - amp, min(base + amp // 3, y))
        pts.append((x, int(y)))
    pts[-1] = (width, pts[0][1])                     # seamless wrap
    return pts


def mountains(width=640):
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(3)
    for base, amp, colour in ((118, 40, C["dusk"]), (140, 30, C["night"])):
        pts = _ridge(width, base, amp, rnd, 5)
        pygame.draw.polygon(s, colour, pts + [(width, H), (0, H)])
        for x, y in pts[::3]:                        # lit rims on the sunward side
            s.set_at((x, y), C["rose"])
    return s


def factory(width=640):
    """Mid layer: cooling towers, stacks, cranes, lit windows."""
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(11)
    body, rim, lit = C["ink"], C["night"], (C["sun"], C["ember"])
    x = 0
    while x < width - 40:
        kind = rnd.choice(("block", "tower", "stack", "crane", "block"))
        if kind == "block":
            w, h = rnd.randrange(30, 60), rnd.randrange(30, 70)
            r = pygame.Rect(x, 170 - h, w, h + 60)
            pygame.draw.rect(s, body, r)
            pygame.draw.line(s, rim, r.topleft, r.topright)
            for wy in range(r.top + 4, 165, 6):
                for wx in range(r.left + 3, r.right - 3, 5):
                    if rnd.random() < 0.22:
                        s.set_at((wx, wy), rnd.choice(lit))
                        s.set_at((wx + 1, wy), rnd.choice(lit))
        elif kind == "tower":
            w, h = rnd.randrange(34, 46), rnd.randrange(60, 80)
            top = 170 - h
            pts = [(x, 170), (x + 6, top + h // 2), (x + 3, top), (x + w - 3, top),
                   (x + w - 6, top + h // 2), (x + w, 170)]
            pygame.draw.polygon(s, body, pts + [(x + w, H), (x, H)])
            pygame.draw.line(s, rim, (x + 3, top), (x + w - 3, top))
        elif kind == "stack":
            w, h = 6, rnd.randrange(70, 100)
            pygame.draw.rect(s, body, (x, 170 - h, w, h + 60))
            for by in range(170 - h + 6, 170, 14):
                pygame.draw.line(s, rim, (x, by), (x + w, by))
            s.set_at((x + 2, 170 - h - 1), C["red"])         # aircraft light
        else:
            h = rnd.randrange(80, 100)
            pygame.draw.line(s, body, (x + 4, 170), (x + 4, 170 - h), 3)
            pygame.draw.line(s, body, (x - 20, 170 - h), (x + 40, 170 - h), 2)
            pygame.draw.line(s, body, (x + 30, 170 - h), (x + 30, 140 - h // 3), 1)
            for i in range(-20, 40, 6):
                pygame.draw.line(s, body, (x + i, 170 - h), (x + i + 3, 170 - h + 3))
        x += rnd.randrange(24, 60)
    pygame.draw.rect(s, body, (0, 168, width, H - 168))
    return s


def near(width=640):
    """Near layer: pylons, wrecks and a broken fence, darkest of all."""
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(19)
    col = C["black"]
    for x in range(0, width, 160):                   # pylons with sagging cables
        px = x + rnd.randrange(20, 60)
        pygame.draw.line(s, col, (px, 180), (px, 70), 2)
        pygame.draw.line(s, col, (px - 12, 80), (px + 12, 80), 2)
        pygame.draw.line(s, col, (px - 8, 92), (px + 8, 92), 1)
        for dx in (-12, 12):
            for i in range(0, 160, 4):
                sag = 18 * math.sin(math.pi * i / 160)
                s.set_at(((px + dx + i) % width, int(80 + sag)), col)
    for x in range(0, width, 2):                     # fence posts and mesh
        if x % 24 == 0:
            pygame.draw.line(s, col, (x, 150), (x, 180), 2)
        if (x // 2) % 2 == 0 and rnd.random() < 0.85:
            s.set_at((x, 152 + (x // 2) % 4), col)
    for _ in range(3):                               # wrecked hulls
        x = rnd.randrange(0, width - 60)
        pygame.draw.polygon(s, col, [(x, 180), (x + 8, 160), (x + 40, 156), (x + 56, 168), (x + 60, 180)])
        pygame.draw.circle(s, col, (x + 14, 180), 7)
        pygame.draw.circle(s, col, (x + 46, 180), 7)
    pygame.draw.rect(s, col, (0, 178, width, H - 178))
    return s


def pillar():
    """A foreground girder that sweeps past in front of everything (parallax faster than the floor)."""
    s = pygame.Surface((22, H), pygame.SRCALPHA)
    pygame.draw.rect(s, C["black"], (4, 0, 14, H))
    for y in range(0, H, 16):
        pygame.draw.line(s, C["ink"], (4, y), (17, y + 15))
        pygame.draw.line(s, C["ink"], (17, y), (4, y + 15))
    pygame.draw.line(s, C["night"], (17, 0), (17, H))
    return s


class Atlas:
    """Builds everything once. `convert()` is skipped: it needs a display, and the game also runs headless."""

    def __init__(self):
        self.players = [player_frames(0), player_frames(1)]
        self.players_l = [{k: pygame.transform.flip(v, True, False) for k, v in p.items()} for p in self.players]
        self.foe = foe_frames()
        self.foe_l = {k: pygame.transform.flip(v, True, False) for k, v in self.foe.items()}
        self.lobber = foe_frames(C["rust"], C["rust_d"])
        self.lobber_l = {k: pygame.transform.flip(v, True, False) for k, v in self.lobber.items()}
        self.white = {}
        self.hostage = hostage_frames()
        self.drone = drone_frames()
        self.caps = {"H": capsule("H", C["red"]), "S": capsule("S", C["blue"]), "R": capsule("R", C["olive"]),
                     "B": capsule("B", C["rust"]), "1": capsule("1", C["green"])}
        self.ground = {}
        self.crate = crate_tile()
        self.girder = girder_tile()
        self.sky = sky()
        self.layers = [(mountains(), 0.08, 0), (factory(), 0.25, 0), (near(), 0.55, 8)]
        self.pillar = pillar()
        self.glow_s = glow(7, (120, 80, 36))
        self.glow_l = glow(18, (150, 70, 30))

    def flash(self, surf):
        key = id(surf)
        if key not in self.white:
            self.white[key] = white(surf)
        return self.white[key]

    def ground_at(self, tx, ty, top):
        key = (tx % 23, ty, top)
        if key not in self.ground:
            self.ground[key] = ground_tile(*key)
        return self.ground[key]
