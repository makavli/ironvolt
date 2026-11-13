"""Every picture in the game, made in code at start-up: pixel sprites from text maps, tiles, parallax layers.

Sprites are drawn without outlines; `outlined()` adds the hard dark rim arcade sprites have.
Nothing here needs a display, so tests can build all of it headless.
"""

import math
import random

import pygame

from .settings import C, H, PLAYER_PAL, TILE, W

INK = C["ink"]


def mix(a, b, t):
    """The colour a part t of the way to b: the lit and shaded tones the palette itself does not hold."""
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# Letters in the text maps. People share them: L A a x are armour from lit to deep shade, H h d a helmet, V v a visor
# or a lens, s S skin, U u the suit under the armour, P p trousers and Q the leg on the far side, K k boots and J the
# far one, g gloves.
BASE_PAL = {
    "w": C["white"], "s": C["skin"], "S": C["skin_d"], "b": C["rust_d"], "y": C["gold"], "c": C["cream"],
    "H": C["steel_l"], "h": C["steel"], "d": C["steel_d"], "T": C["steel_d"], "t": C["steel"],
    "U": C["steel_d"], "u": C["steel"], "P": C["steel"], "p": mix(C["steel"], C["steel_l"], 0.6), "Q": C["steel_d"],
    "K": C["rust_d"], "k": C["rust"], "J": mix(C["rust_d"], INK, 0.5), "g": C["sun"],
    "D": C["steel_d"], "E": C["steel"], "F": C["steel_l"], "N": C["black"],
}

# People face right on a canvas 24 wide, the middle of the body between columns 11 and 12, feet on the last row.
# A head (7 rows) and a body (8 rows) stand on a pair of legs (10 rows; a stride's rise and dip changes that).
# The hand that holds the gun is at column 14, 15 rows up from the feet: the actors draw what it holds there.
HEAD = {
    "": [                                   # looking ahead
        "..........HHHH",
        ".........HwwHHHh",
        "........hHHHHHHhh",
        "........dAALLAAAa",
        "........dhaVVwVVV",
        "........dhavVVVVV",
        ".........ddSssss",
    ],
    "u": [                                  # tilted back, to aim up
        "..........HHhAV",
        ".........HwHhAVVw",
        "........hHHHHAVVV",
        "........hHHHHhAVs",
        "........dhHHHhhss",
        ".........dhhhhSs",
        "..........dddS",
    ],
}
HEAD["U"] = [r[2:] for r in HEAD["u"]]      # straight up: leaning back, clear of the barrel
BODY = [                                    # a shoulder pad, the arm bent to the gun, a chest plate, a pack
    "..........UUUu",
    "........aLLLAAAAa",
    "......TtaALAxALAa",
    "......TtaAAAxAAAa",
    "......TTaaLLLaAAa",
    ".......TxaaaaAAa",
    "........bbbbbybb",
    ".........UPPPPp",
]
PACK = ["", "", "...XXX", "...XYX", "...XXX"]     # laid over the body: the grenadier's shells
FOE_HEAD = [                                # a gas mask under a scavenged helmet, one red lens
    "..........aAAa",
    ".........aALLAa",
    "........aALLAAAa",
    ".......aaAAAAAAaa",
    "........mmMVwmMM",
    "........mmMVVmMMMt",
    ".........mmmmmMMt",
]
STRIDE = [                                  # one leg through a stride: heel strike, the weight, the push, the swing
    ["..........PPPp", "...........PPPp", "...........PPPPp", "............ALLA", "............aAAA",
     ".............aAA", ".............aAA", "..............aAA", "..............KKKk", "..............KKKKk"],
    ["..........PPPp", "...........PPPp", "............ALLA", "............aAAA", "............aAA",
     "...........aAA", "...........aAA", "...........KKKk", "...........KKKKk"],
    ["..........PPPp", "..........PPPp", "..........PPPp", "..........ALLA", "..........aAAA",
     "..........aAA", "..........aAA", "..........aAA", "..........KKKk", "..........KKKKk"],
    ["..........PPPp", ".........PPPp", ".........PPPp", "........ALLA", "........aAAA",
     ".......aAA", ".......aAA", "......aAA", ".....KKKA", ".....KKKk", "......KKk"],
    ["..........PPPp", ".........PPPp", "........PPPp", "........ALLA", ".......aAAA",
     "......aAA", "....KKaA", "....KKK", ".....k"],
    ["..........PPPp", "..........PPPPp", "...........PPPp", ".....KK....ALLA", ".....KKaAAAAAAA", ".....kK"],
    ["..........PPPp", "...........PPPp", "............PPPp", ".............ALLA", "............aAAA",
     "...........aAA", "..........KKKA", "..........KKKKk"],
    ["..........PPPp", "...........PPPp", "............PPPp", ".............ALLA", ".............aAAA",
     "..............aAA", "...............aAA", "...............KKKk", "...............KKKKk"],
]
FAR = str.maketrans("PpALkK", "QQaaJJ")     # the far leg: in shade, no highlights


def over(a, b):
    """Text map b laid over text map a."""
    rows = []
    for i in range(max(len(a), len(b))):
        ra, rb = a[i] if i < len(a) else "", b[i] if i < len(b) else ""
        n = max(len(ra), len(rb))
        rows.append("".join(y if y != "." else x for x, y in zip(ra.ljust(n, "."), rb.ljust(n, "."))))
    return rows


LEGS = {
    "stand": [
        "........QQQPPPPp", ".......QQQQ.PPPp", ".......QQQ..PPPp", ".......aaa..ALLA", ".......aaa..aAAA",
        ".......aaa..aAA", ".......aaa..aAA", ".......aaa..aAA", ".......JJJJ.KKKk", ".......JJJJ.KKKKk",
    ],
    "jump": [                               # rising: one knee up, the other leg trailing
        ".........QPPPp", "........QQPPPPPLLA", ".......QQQaPPPPAAA", "......QQaa....aAA", ".....aaa......aAA",
        "...JJaa......KKKk", "...JJJ.......KKKKk", "...J", "", "",
    ],
    "fall": [                               # coming down: legs reaching for the ground
        ".........QPPPp", "........QQQPPPp", ".......QQQQPPPp", ".......aaaa.ALLA", "......aaaa..aAAA",
        "......aaa...aAA", ".....Jaaa...aAA", ".....JJJ....KKKk", "......JJJ...KKKKk", "",
    ],
}
LEGS.update(("run%d" % i, over([r.translate(FAR) for r in STRIDE[(i + 4) % 8]], STRIDE[i])) for i in range(8))

HURT = [                                    # thrown back off the feet: goes under a head moved 2 to the left
    "........UUUu.....Lgg",
    "......aLLLAAAALLLL",
    "....TtaALAAALAaa",
    "....TtaAAAAAAAa",
    ".....TTaAAAAAAa",
    "......TxaaAAAAAa",
    "........bbbbybbb",
    ".........UPPPPPp",
    "..........QQPPPPp",
    "..........QQQPPPPp",
    "...........QQaALLA",
    "...........aaaaAAA",
    "............aaaaAA",
    "............Jaa.aAA",
    "...........JJJ..KKKk",
    "...........JJ...KKKKk",
]
POSES = {                                   # the heroes' whole figures: (canvas width, rows)
    "crouch": (24, [                        # on one knee, the gun at the cheek: 9 rows up, column 14
        "......HHHH",
        ".....HwwHHHh",
        "....hHHHHHHhh",
        "....dAALLAAAa",
        "....dhaVVwVVV",
        "....dhavVVVVV",
        ".....ddSssss",
        "..TtaLLLAAAxLLL",
        "..TtaALLAAAAxLA",
        "..TTxaaAAAAAAaPPp",
        "...bbbbbbybbPPPPLLA",
        "....QQQQQQQQ...aAAA",
        "......QQQQaa...aAA",
        "...JJJaaaaaa..KKKKk",
    ]),
    "slide": (32, [                         # feet first, the gun held up clear of the ground: column 18
        "........HHHH",
        ".......HwwHHHh",
        "......hHHHHHHhh",
        "......dAALLAAAa",
        "......dhaVVwVVV.L",
        "......dhavVVVVVLLL",
        ".......ddSssssLLa..ALL",
        "...TtaLLLAAAAxAa.PPALLA",
        "...TtaALLAAAAAAabPPP.aAA",
        "...TTxaaAAAAAAAabPPP..aAA",
        "....TxxaaaaaaaabQQQaaKKKkJJ",
        ".......xxxxxxxxxQQQaaKKKKkJJJ",
    ]),
    "hurt": (28, HEAD["U"] + HURT),
    "down": (32, [
        "...........aLLLa",
        "....HHHh..aLLAAAAa......ALLA",
        "...HwHHAVVSLAAAyAAAbbPPPPAAAA.kK",
        "..hHHHHAVwsAAAAAAAabyPPPPPAAAAKK",
        "..hhHHhhdSsaaAAAAaabbQQQQQaaaaJJ",
        "...dddd.TTTtaaaaaa..QQQQQaaa.JJJ",
    ]),
}

# Things held in the hands, drawn pointing right: (the hand's place in the map, rows).
GUNS = {
    "P": ((1, 1), ["..FFFFFFF", "gDDDDDDDDEEE", "ggDDDDN", ".gNN"]),
    "H": ((1, 2), ["...FFFFF", "..DDDDDRFFFFFF", "ggDDDDDRDEDEDE", ".gDDDDDRDDDDDD", "...NNN", "...NNN"]),
    "S": ((1, 2), ["...........FF", "..FFFFRFFFFDD", "ggDDDDRDDDDDD", ".gDDDDRDDDDDD", "..NN.......EE"]),
    "R": ((4, 2), ["EFFFFFFFFFFFFFF", "DDDDDDDRRDDDDDDw", "DDDggDDRRDDDDDDR", "NDDDggDDDDDDDDD", "....NN"]),
}
KNIFE = ((5, 1), ["..............w", "aAAAAggFFFFFFFw", ".aaaAgg.EEEE"])      # the sleeve comes with it: a thrust
RIFLE = ((2, 1), ["...FFFFFFFF", "bbDDDDDDDDDEE", "bbgDNg", "..g.N"])
TUBE = ((2, 2), [".FFFFFFFFF", "DDDDDDDDDDN", "DDgDDDgDDDN", "DDDDDDDDDDN", "..N...N"])

HOSTAGE = [                                 # a technician on his knees, roped
    "....yyyyy",
    "...yYYyyyy",
    "...yyyyyyyyy",
    "....Ssssss",
    "....SssKsK",
    "....SSssss",
    ".....Sssss",
    "...CcccccccC",
    "..rrrrrrrrrrr",
    "..CcccccccccC",
    "..rrrrrrrrrrr",
    "...CccccccccC",
    "...PPPPPPPPPp",
    "..PPPPPPPPPPPp",
    ".KKPPP...PPPPp",
    ".KKKk....KKKKk",
]
FREED = [                                   # on his feet, arms up: two beats of a cheer
    [
        ".....ss..........ss",
        ".....ss...yyyy...ss",
        "......cc.yYYyyy.cc",
        "......cc.yyyyyyycc",
        ".......ccSssssscc",
        ".......ccSsKsKscc",
        "........ccSssscc",
        "........cccccccc",
        ".........cccccc",
        ".........cyyyyc",
        ".........cccccc",
        ".........CccccC",
        ".........bbbbbb",
        ".........PPPPPp",
    ],
    [
        "",
        "..........yyyy",
        "...ss....yYYyyy....ss",
        "...ssc...yyyyyyy..css",
        "....ccc..Ssssss.ccc",
        "......cc.SsKsKscc",
        ".......cccSsssccc",
        "........cccccccc",
        ".........cccccc",
        ".........cyyyyc",
        ".........cccccc",
        ".........CccccC",
        ".........bbbbbb",
        ".........PPPPPp",
    ],
]
DRONE_BODY = [
    "...dd....HHHHhh....dd",
    "...ddMMMHHHHHHhhMMMdd",
    ".......hHHHHHHHhhd",
    ".......hyyyyyyyyhd",
    ".......hhHHHHHhhdd",
    "........dhVVwhhdd",
    ".........dVVVhdd",
    "........d..dd..d",
    ".......dd......dd",
    "......ddd......ddd",
]
ROTORS = ["FFEEEEFF........FFEEEEFF", ".EFFFFE..........EFFFFE.", "..FFFF............FFFF.."]


def sprite(rows, pal, width=0):
    """A picture from a text map: one letter a pixel, coloured by pal; '.' and letters pal lacks stay clear."""
    width = max(width, *map(len, rows))
    text = "".join(r.ljust(width, ".") for r in rows)
    table = dict.fromkeys(map(ord, set(text)), "\0\0\0\0")
    table.update((ord(k), "%c%c%c\xff" % tuple(v[:3])) for k, v in pal.items())
    return pygame.image.frombytes(text.translate(table).encode("latin-1"), (width, len(rows)), "RGBA")  # frombytes copies; frombuffer kept a pointer to a freed temporary (Linux segfault)


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


def mirrored(frames):
    return {k: pygame.transform.flip(v, True, False) for k, v in frames.items()}


def _armour(lit, dark, **more):
    return dict(BASE_PAL, L=mix(lit, C["cream"], 0.45), A=lit, a=dark, x=mix(dark, INK, 0.5), **more)


def _people(tops, pal, poses=()):
    """Every top on every pair of legs ('run3', and 'run3u' looking up), plus the whole-figure poses asked for."""
    frames = {name + tag: outlined(sprite(top + legs, pal, 24))
              for tag, top in tops.items() for name, legs in LEGS.items()}
    frames.update((name, outlined(sprite(POSES[name][1], pal, POSES[name][0]))) for name in poses)
    return frames


def player_pal(index):
    p = PLAYER_PAL[index]
    return _armour(p["A"], p["a"], V=p["V"], v=mix(p["V"], INK, 0.45))


def player_frames(index):
    return _people({tag: head + BODY for tag, head in HEAD.items()}, player_pal(index), POSES)


def foe_frames(armour=C["olive"], armour_d=C["olive_d"], pack=False):
    """A Rust Legion trooper: the heroes' build in scavenged plate and dusty cloth, a gas mask where their visor is."""
    cloth = mix(C["skin_d"], C["steel"], 0.5)
    pal = _armour(armour, armour_d, V=C["red"], M=C["steel"], m=mix(C["steel_d"], INK, 0.4), T=armour_d, t=armour,
                  P=cloth, p=mix(cloth, C["cream"], 0.3), Q=mix(cloth, INK, 0.5), U=mix(cloth, INK, 0.5), u=cloth,
                  K=mix(C["steel_d"], C["black"], 0.4), k=C["steel"], J=mix(C["steel_d"], C["black"], 0.7),
                  X=C["steel_d"], Y=C["gold"])
    frames = _people({"": FOE_HEAD + (over(BODY, PACK) if pack else BODY)}, pal)
    frames["hurt"] = outlined(sprite([r[2:] for r in FOE_HEAD] + HURT, pal, 28))
    return frames


def hostage_frames():
    """A captured technician: 'bound0/1' on his knees, 'cheer0/1' freed, 'run0..7' off to the left."""
    denim = mix(C["blue"], C["steel_d"], 0.6)
    pal = dict(BASE_PAL, Y=mix(C["gold"], C["white"], 0.5), C=mix(C["cream"], C["rust"], 0.4), r=C["rust"],
               P=denim, p=mix(denim, C["cream"], 0.3), Q=mix(denim, INK, 0.5), A=denim, L=denim, a=mix(denim, INK, 0.5))
    frames = {"bound0": outlined(sprite(HOSTAGE, pal, 16)),
              "bound1": outlined(sprite(["." + r for r in HOSTAGE[:7]] + HOSTAGE[7:], pal, 16))}
    for i in range(8):
        frames["run%d" % i] = outlined(sprite(FREED[i // 2 % 2] + LEGS["run%d" % i], pal, 24))
    for i in (0, 1):
        frames["cheer%d" % i] = outlined(sprite(FREED[i] + LEGS["stand"], pal, 24))
    return mirrored(frames)


def drone_frames():
    pal = dict(BASE_PAL, M=C["steel_d"], V=C["red"])
    return [outlined(sprite([rotor, ""] + DRONE_BODY, pal, 24)) for rotor in ROTORS]


def held(item, pal, turns=((1, 0, 0),)):
    """A thing in the hand, turned to each aim and centred on the hand: {(aim x, aim y, side): picture}."""
    (px, py), rows = item
    flat = pygame.Surface((29, 29), pygame.SRCALPHA)
    flat.blit(sprite(rows, pal), (14 - px, 14 - py))
    out = {}
    for ax, ay, turn in turns:
        img = outlined(pygame.transform.rotate(flat, turn) if turn else flat)
        out[ax, ay, 1] = img
        out[-ax, ay, -1] = pygame.transform.flip(img, True, False)
    return out


AIMS = ((1, 0, 0), (1, -1, 45), (0, -1, 90), (1, 1, -45), (0, 1, -90))


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


# ---------------------------------------------------------------- machines

def turret():
    """A dug-in gun: (its bolted base, its armoured dome). The barrel swings, so the actor draws it."""
    base = pygame.Surface((22, 9), pygame.SRCALPHA)
    pygame.draw.polygon(base, C["rust_d"], [(0, 8), (2, 3), (5, 0), (16, 0), (19, 3), (21, 8)])
    pygame.draw.polygon(base, C["rust"], [(3, 3), (5, 1), (16, 1), (18, 3)])
    pygame.draw.line(base, mix(C["rust"], C["sun"], 0.4), (5, 0), (16, 0))
    pygame.draw.line(base, mix(C["rust_d"], INK, 0.5), (1, 8), (20, 8))
    for x in range(3, 20, 4):
        base.set_at((x, 5), C["steel_l"])
        base.set_at((x, 6), INK)
    dome = pygame.Surface((11, 11), pygame.SRCALPHA)     # small, so the barrel shows where it points
    pygame.draw.circle(dome, mix(C["steel_d"], INK, 0.5), (5, 5), 5)
    pygame.draw.circle(dome, C["steel_d"], (5, 4), 4)
    pygame.draw.circle(dome, C["steel"], (4, 3), 2)
    dome.set_at((3, 2), C["steel_l"])
    dome.set_at((3, 3), C["steel_l"])
    dome.set_at((2, 2), C["white"])
    for x, y in ((1, 6), (5, 9), (9, 6)):
        dome.set_at((x, y), C["steel"])
    return outlined(base), outlined(dome)


def bastion(broken):
    """BASTION's hull, facing left, its feet at the bottom middle of the picture; `broken` shows the armour cracked.
    The tread links, the chin gun and the light of the core move, so the actor draws those."""
    s = pygame.Surface((104, 72), pygame.SRCALPHA)

    def at(dx, dy):
        return 52 + dx, 70 + dy

    rust, dark, lit = C["rust"], C["rust_d"], mix(C["rust"], C["sun"], 0.45)
    steel, iron = C["steel_d"], mix(C["steel_d"], INK, 0.5)
    # the tracks
    pygame.draw.rect(s, steel, (*at(-46, -16), 92, 16), border_radius=7)
    pygame.draw.rect(s, iron, (*at(-42, -13), 84, 10), border_radius=5)
    for wx in range(-34, 40, 17):
        pygame.draw.circle(s, INK, at(wx, -8), 5)
        pygame.draw.circle(s, C["steel"], at(wx, -8), 4)
        pygame.draw.circle(s, steel, at(wx, -7), 3)
        pygame.draw.circle(s, INK, at(wx, -8), 1)
    # the hull: a glacis in shade at the front, a sunlit slope at the back
    pygame.draw.polygon(s, rust, [at(-48, -17), at(-40, -38), at(30, -40), at(46, -26), at(44, -17)])
    pygame.draw.polygon(s, dark, [at(-48, -17), at(-40, -38), at(-35, -38), at(-42, -17)])
    pygame.draw.polygon(s, lit, [at(30, -40), at(46, -26), at(42, -26), at(27, -39)])
    pygame.draw.line(s, lit, at(-39, -38), at(29, -40))
    pygame.draw.polygon(s, dark, [at(-47, -23), at(45, -23), at(44, -17), at(-48, -17)])
    pygame.draw.line(s, INK, at(-46, -24), at(45, -24))
    for bx in range(-40, 44, 7):                         # bolts along the skirt
        s.set_at(at(bx, -20), lit)
        s.set_at(at(bx + 1, -19), INK)
    for i in range(4):                                   # what is left of the quarry's hazard paint
        x = -47 + i * 4
        pygame.draw.polygon(s, C["gold"] if i % 2 == 0 else INK,
                            [at(x, -17), at(x + 3, -23), at(x + 6, -23), at(x + 3, -17)])
    for sx in (-18, 14):                                 # plate seams and their rivets
        pygame.draw.line(s, dark, at(sx, -38), at(sx, -25))
        for ry in (-36, -31, -27):
            s.set_at(at(sx + 2, ry), lit)
    # the cab: a red-lit slit, and the engine's vents
    pygame.draw.rect(s, INK, (*at(-38, -34), 7, 4))
    pygame.draw.rect(s, C["red"], (*at(-37, -33), 5, 2))
    s.set_at(at(-36, -33), C["sun"])
    pygame.draw.rect(s, INK, (*at(-29, -35), 34, 10))
    pygame.draw.rect(s, steel, (*at(-28, -34), 32, 8))
    pygame.draw.line(s, C["steel"], at(-28, -34), at(3, -34))
    for i in range(5):
        pygame.draw.line(s, INK, at(-25 + i * 6, -32), at(-25 + i * 6, -28))
        pygame.draw.line(s, C["steel"], at(-24 + i * 6, -32), at(-24 + i * 6, -28))
    pygame.draw.polygon(s, C["red"], [at(22, -35), at(26, -31), at(22, -27), at(18, -31)])    # the Legion's mark
    pygame.draw.polygon(s, dark, [at(22, -33), at(24, -31), at(22, -29), at(20, -31)])
    # the mortar's turret and tube, the missile rack, the exhausts
    pygame.draw.rect(s, INK, (*at(-7, -54), 34, 17), border_radius=4)
    pygame.draw.rect(s, steel, (*at(-6, -53), 32, 15), border_radius=3)
    pygame.draw.line(s, C["steel"], at(-4, -53), at(23, -53))
    pygame.draw.line(s, iron, at(-5, -40), at(24, -40))
    pygame.draw.circle(s, INK, at(-1, -46), 3, 1)
    for rx in (6, 20):
        s.set_at(at(rx, -42), C["steel_l"])
    pygame.draw.line(s, INK, at(15, -50), at(9, -64), 7)
    pygame.draw.line(s, C["steel"], at(15, -50), at(9, -64), 5)
    pygame.draw.line(s, C["steel_l"], at(13, -51), at(8, -63))
    pygame.draw.line(s, INK, at(6, -64), at(12, -62), 2)
    pygame.draw.polygon(s, INK, [at(27, -41), at(29, -52), at(45, -48), at(44, -37)])
    pygame.draw.polygon(s, steel, [at(29, -42), at(30, -50), at(43, -47), at(43, -39)])
    for i in range(3):
        pygame.draw.circle(s, INK, at(33 + i * 4, -45 + i), 2)
        s.set_at(at(33 + i * 4, -45 + i), C["red"])
    # the chin gun's mount, the core's housing
    pygame.draw.circle(s, INK, at(-40, -18), 6)
    pygame.draw.circle(s, steel, at(-40, -18), 5)
    pygame.draw.circle(s, C["steel"], at(-41, -19), 2)
    pygame.draw.circle(s, INK, at(34, -30), 7)
    pygame.draw.circle(s, steel, at(34, -30), 6)
    pygame.draw.circle(s, INK, at(34, -30), 4)
    if broken:
        soot = mix(dark, C["black"], 0.6)
        for pts in (((34, -36), (30, -40)), ((28, -30), (20, -26), (16, -30), (8, -25)),
                    ((-10, -38), (-14, -31), (-9, -27)), ((38, -26), (42, -20))):
            pygame.draw.lines(s, C["ember"], False, [at(x + 1, y) for x, y in pts])
            pygame.draw.lines(s, soot, False, [at(x, y) for x, y in pts])
        pygame.draw.circle(s, soot, at(-30, -27), 3)
        pygame.draw.circle(s, soot, at(10, -36), 2)
    return outlined(s)


# ---------------------------------------------------------------- tiles

def _hash(x, y, seed=0):
    return (x * 73856093 ^ y * 19349663 ^ seed * 83492791) & 0xFFFF


def ground_tile(tx, ty, top, left=False, right=False):
    """Scrapyard ground: a riveted steel deck on top, packed rust and slag below, darker with depth.
    left / right: that side stands open (a ledge, a pit wall): it gets an edge, and the deck a hazard stripe."""
    s = pygame.Surface((TILE, TILE))
    rnd = random.Random(_hash(tx, ty))
    deep = {12: 0.3, 13: 0.55}.get(ty, 0)                # under the floor line the earth falls into shadow
    soil, lump, seam = (mix(C[k], C["black"], deep) for k in ("rust_d", "rust", "ink"))
    vein = mix(soil, seam, 0.5)
    s.fill(soil)
    for y in (3, 8, 13):                                 # strata: broken seams of darker slag
        x = rnd.randrange(-6, 4)
        while x < TILE:
            n = rnd.randrange(3, 9)
            pygame.draw.line(s, vein, (x, y), (x + n, y + rnd.randrange(2)))
            x += n + rnd.randrange(3, 8)
    for _ in range(rnd.randrange(1, 4)):                 # lumps of slag, lit from above
        x, y, r = rnd.randrange(2, 14), rnd.randrange(8, 14), rnd.randrange(1, 3)
        pygame.draw.circle(s, vein, (x, y + 1), r)
        pygame.draw.circle(s, mix(soil, lump, 0.6), (x, y), r)
        s.set_at((x, y - r), lump)
    for _ in range(5):
        s.set_at((rnd.randrange(TILE), rnd.randrange(TILE)), lump if rnd.random() < 0.5 else seam)
    if rnd.random() < 0.2:                               # a buried pipe
        y = rnd.randrange(8, 13)
        pygame.draw.line(s, mix(C["steel_d"], C["black"], deep), (0, y), (TILE, y), 2)
        pygame.draw.line(s, mix(C["steel"], C["black"], deep), (0, y), (TILE, y))
    if left:
        pygame.draw.line(s, seam, (0, 0), (0, TILE))
        pygame.draw.line(s, vein, (1, 0), (1, TILE))
    if right:                                            # the side the low sun reaches
        pygame.draw.line(s, lump, (15, 0), (15, TILE))
        pygame.draw.line(s, mix(soil, lump, 0.5), (14, 0), (14, TILE))
    if top:
        pygame.draw.rect(s, C["steel_d"], (0, 0, TILE, 5))
        pygame.draw.line(s, C["steel_l"], (0, 0), (TILE, 0))
        pygame.draw.line(s, C["steel"], (0, 1), (TILE, 1))
        pygame.draw.line(s, mix(C["steel_d"], INK, 0.45), (0, 4), (TILE, 4))
        pygame.draw.line(s, INK, (0, 5), (TILE, 5))
        pygame.draw.line(s, vein, (0, 6), (TILE, 6))     # the deck's shadow on the earth
        for x in range(0, TILE, 4):                      # tread plate
            s.set_at((x + 1, 2), C["steel"])
            s.set_at((x + 3, 3), C["steel"])
        pygame.draw.line(s, INK, (0, 1), (0, 4))         # a joint, and its rivets
        for rx in (3, 12):
            s.set_at((rx, 2), C["steel_l"])
            s.set_at((rx + 1, 3), INK)
        for side, x0 in ((left, 0), (right, TILE - 7)):  # an open end: hazard paint
            if side:
                for x in range(x0, x0 + 7):
                    for y in range(1, 5):
                        s.set_at((x, y), C["gold"] if (x + y) // 2 % 2 else INK)
        if rnd.random() < 0.3:                           # a rust streak
            x = rnd.randrange(2, 14)
            pygame.draw.line(s, lump, (x, 2), (x, 8))
    return s


def crate_tile(kind=0):
    """A Legion supply crate. kind 1 carries the Legion's mark, kind 2 is patched with steel."""
    s = pygame.Surface((TILE, TILE))
    wood, dark, lit = C["rust"], C["rust_d"], mix(C["rust"], C["sun"], 0.45)
    s.fill(wood)
    for y in (5, 10):                                    # planks
        pygame.draw.line(s, dark, (1, y), (14, y))
        pygame.draw.line(s, lit, (1, y + 1), (14, y + 1))
    pygame.draw.line(s, dark, (3, 13), (12, 3), 2)       # a brace
    pygame.draw.line(s, lit, (3, 12), (11, 3))
    pygame.draw.rect(s, INK, (0, 0, TILE, TILE), 1)
    pygame.draw.rect(s, dark, (1, 1, 14, 14), 1)
    pygame.draw.line(s, lit, (1, 1), (14, 1))
    if kind == 1:
        pygame.draw.polygon(s, C["red"], [(8, 4), (12, 8), (8, 12), (4, 8)])
        pygame.draw.polygon(s, wood, [(8, 6), (10, 8), (8, 10), (6, 8)])
    if kind == 2:
        pygame.draw.rect(s, C["steel_d"], (2, 7, 7, 6))
        pygame.draw.line(s, C["steel"], (2, 7), (8, 7))
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):    # steel corners
        pygame.draw.rect(s, C["steel_d"], (min(x, 12), min(y, 12), 3, 3))
        s.set_at((x, y), C["steel_l"])
    return s


def girder_tile(left=False, right=False):
    """A one-way catwalk: a bright deck on an open lattice. You can jump up through it and stand on it."""
    s = pygame.Surface((TILE, 8), pygame.SRCALPHA)
    pygame.draw.line(s, C["steel_l"], (0, 0), (TILE, 0))
    pygame.draw.line(s, C["steel"], (0, 1), (TILE, 1))
    pygame.draw.line(s, INK, (0, 2), (TILE, 2))
    for x in range(TILE):                                # the lattice: a zigzag of struts
        k = x % 8
        s.set_at((x, 3 + (k if k < 3 else 2 if k == 3 else 6 - k if k < 7 else 0)), C["steel_d"])
    pygame.draw.line(s, C["steel_d"], (0, 6), (TILE, 6))
    pygame.draw.line(s, INK, (0, 7), (TILE, 7))
    for side, x in ((left, 0), (right, TILE - 2)):       # an end plate
        if side:
            pygame.draw.rect(s, C["steel"], (x, 0, 2, 7))
            pygame.draw.line(s, C["gold"], (x, 3), (x + 1, 3))
            pygame.draw.line(s, C["gold"], (x, 5), (x + 1, 5))
    return s


# ---------------------------------------------------------------- backgrounds

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def sky():
    """Dusk sky in dithered bands, ash clouds lit from below, a striped low sun. One screen, it does not scroll."""
    bands = [C["black"], C["ink"], C["night"], C["dusk"], C["rose"], C["ember"], C["sun"]]
    horizon, last = 150, len(bands) - 1
    strip = pygame.Surface((4, H))                       # the dither repeats every 4 pixels: one strip, tiled
    for y in range(H):
        t = min(1.0, y / horizon) * last
        i = int(t)
        for x in range(4):
            strip.set_at((x, y), bands[min(last, i + ((t - i) * 16 > BAYER[y % 4][x]))])
    s = pygame.Surface((W, H))
    for x in range(0, W, 4):
        s.blit(strip, (x, 0))
    rnd = random.Random(7)
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(60)
        s.set_at((x, y), C["cream"] if rnd.random() < 0.3 else C["steel"])
    cx, cy, r = 228, 120, 34                             # the sun, cut by horizontal bars like a heat haze
    for y in range(cy - r, cy + r):
        half = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
        if y > cy - 6 and (y - cy) % 6 < (y - cy) // 6 + 1:
            continue
        colour = C["cream"] if y < cy - 16 else C["sun"] if y < cy + 6 else C["ember"]
        pygame.draw.line(s, colour, (cx - half, y), (cx + half, y))
    for _ in range(10):                                  # ash clouds: dark streaks, their undersides lit
        x, y, half = rnd.randrange(W), rnd.randrange(22, 112), rnd.randrange(16, 56)
        i = int(y / horizon * last)
        for k, part in enumerate((0.45, 1.0, 0.8)):
            lean = rnd.randrange(-6, 7)
            pygame.draw.line(s, bands[max(0, i - 1)], (x - half * part + lean, y + k), (x + half * part + lean, y + k))
        pygame.draw.line(s, bands[min(last, i + 2)], (x - half * 0.5, y + 3), (x + half * 0.6, y + 3))
    return s


def _ridge(width, base, amp, rnd, rough):
    pts, y = [], base
    for x in range(0, width + 1, 4):
        y += rnd.uniform(-rough, rough)
        y = max(base - amp, min(base + amp // 3, y))
        pts.append((x, int(y)))
    pts[-1] = (width, pts[0][1])                         # seamless wrap
    return pts


def mountains(width=640):
    """Far layer: two ridges, their sunward slopes lit, and the dead reactor towers of the old grid."""
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(3)
    for base, amp, colour, rim in ((118, 40, C["dusk"], C["rose"]), (140, 30, C["night"], C["dusk"])):
        pts = _ridge(width, base, amp, rnd, 5)
        if rim == C["rose"]:
            for x in range(40, width - 40, 150):         # cooling towers, far off on the first ridge
                tx, w, h = x + rnd.randrange(60), rnd.randrange(14, 22), rnd.randrange(22, 34)
                foot = pts[tx // 4][1] + 6
                pygame.draw.polygon(s, colour, [(tx, foot), (tx + 3, foot - h), (tx + w - 3, foot - h), (tx + w, foot)])
                pygame.draw.line(s, rim, (tx + w - 3, foot - h), (tx + w - 1, foot - 8))
        pygame.draw.polygon(s, colour, pts + [(width, H), (0, H)])
        shade = mix(colour, C["black"], 0.3)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if y1 > y0:                                  # a slope that falls toward the sun
                pygame.draw.line(s, rim, (x0, y0), (x1, y1))
            elif y1 < y0 and x0 % 3 == 0:                # a gully in shade
                pygame.draw.line(s, shade, (x0, y0 + 3), (x0 - 4, y0 + 14))
    return s


def factory(width=640):
    """Mid layer: the Legion's works: sheds with lit windows, cooling towers, stacks and their smoke, tanks, cranes."""
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(11)
    body, rim, edge, lit = C["ink"], C["night"], C["dusk"], (C["sun"], C["ember"])

    def plume(x, y, puffs):                              # smoke leaning on the wind, its sunward side lit
        for i in range(puffs):
            r = 2 + i // 2
            x, y = x - rnd.randrange(1, 5), y - r - 1
            pygame.draw.circle(s, rim, (x, y), r)
            pygame.draw.circle(s, edge, (x, y), r, 1, draw_top_right=True)

    x = 0
    while x < width - 64:
        kind = rnd.choice(("shed", "tower", "stack", "shed", "crane", "tank", "shed", "stack"))
        if kind == "shed":
            w, h = rnd.randrange(34, 64), rnd.randrange(28, 66)
            top = 170 - h
            pygame.draw.rect(s, body, (x, top, w, h + 60))
            if rnd.random() < 0.5:                       # a saw-tooth roof
                for rx in range(x, x + w - 7, 8):
                    pygame.draw.polygon(s, body, [(rx, top), (rx, top - 5), (rx + 8, top)])
                    pygame.draw.line(s, rim, (rx, top - 5), (rx + 7, top - 1))
            else:                                        # a flat one: a water tank, a vent pipe
                pygame.draw.rect(s, body, (x + 4, top - 5, 9, 5))
                pygame.draw.line(s, rim, (x + 4, top - 5), (x + 12, top - 5))
                pygame.draw.line(s, body, (x + w - 8, top), (x + w - 8, top - 10))
            pygame.draw.line(s, rim, (x, top), (x + w - 1, top))
            pygame.draw.line(s, edge, (x + w - 1, top), (x + w - 1, 168))
            for wy in range(top + 5, 164, 6):            # rows of windows: behind some, a shift still at work
                for wx in range(x + 3, x + w - 4, 5):
                    roll = rnd.random()
                    if roll < 0.55:
                        pygame.draw.line(s, rnd.choice(lit) if roll < 0.3 else rim, (wx, wy), (wx + 1, wy))
        elif kind == "tower":
            w, h = rnd.randrange(34, 46), rnd.randrange(60, 80)
            top = 170 - h
            plume(x + w // 2 + 4, top + 2, 7)
            pts = [(x, 170), (x + 6, top + h // 2), (x + 3, top), (x + w - 3, top),
                   (x + w - 6, top + h // 2), (x + w, 170)]
            pygame.draw.polygon(s, body, pts + [(x + w, H), (x, H)])
            pygame.draw.line(s, rim, (x + 3, top), (x + w - 3, top))
            pygame.draw.lines(s, edge, False, [(x + w - 3, top), (x + w - 6, top + h // 2), (x + w, 170)])
            for by in range(top + 8, 168, 12):           # the ribs of the shell
                pygame.draw.line(s, rim, (x + 7, by), (x + w - 8, by))
        elif kind == "stack":
            w, h = 6, rnd.randrange(70, 100)
            top = 170 - h
            if rnd.random() < 0.6:
                plume(x + 3, top, 5)
            else:                                        # a flare: gas burning off
                pygame.draw.polygon(s, C["ember"], [(x + 1, top - 1), (x + 4, top - 1), (x + 1, top - 7)])
                pygame.draw.line(s, C["sun"], (x + 2, top - 1), (x + 2, top - 4))
            pygame.draw.rect(s, body, (x, top, w, h + 60))
            pygame.draw.line(s, edge, (x + w - 1, top), (x + w - 1, 168))
            for by in range(top + 6, 170, 14):
                pygame.draw.line(s, rim, (x, by), (x + w, by))
            s.set_at((x + 4, top - 1), C["red"])         # aircraft light
        elif kind == "tank":
            r = rnd.randrange(9, 14)
            w = 2 * r
            pygame.draw.circle(s, body, (x + r, 160 - r), r)
            pygame.draw.arc(s, edge, (x, 160 - 2 * r, 2 * r + 1, 2 * r + 1), -1.2, 1.0)
            pygame.draw.line(s, rim, (x + 2, 160 - r), (x + 2 * r - 2, 160 - r))
            for lx in (x + 3, x + 2 * r - 3):
                pygame.draw.line(s, body, (lx, 160 - r), (lx, 170), 2)
        else:                                            # a tower crane: mast, jib, a load on its cable
            w, h = 44, rnd.randrange(80, 100)
            top, mast = 170 - h, x + 16
            pygame.draw.line(s, body, (mast, 170), (mast, top), 3)
            pygame.draw.line(s, body, (x, top), (x + w, top), 2)
            for i in range(0, w - 5, 6):
                pygame.draw.line(s, body, (x + i, top), (x + i + 3, top + 3))
                pygame.draw.line(s, body, (x + i + 3, top + 3), (x + i + 6, top))
            pygame.draw.line(s, body, (x, top + 3), (x + w, top + 3))
            pygame.draw.line(s, body, (mast, top - 8), (x, top))
            pygame.draw.line(s, body, (mast, top - 8), (x + w, top))
            pygame.draw.line(s, body, (x + w - 8, top), (x + w - 8, 140 - h // 3))
            pygame.draw.rect(s, body, (x + w - 10, 140 - h // 3, 5, 4))
            s.set_at((mast, top - 9), C["red"])
        x += w + rnd.randrange(-4, 12)
    pygame.draw.rect(s, body, (0, 168, width, H - 168))
    for px in range(0, width, 64):                       # a pipe run along the yard, a lamp at each trestle
        pygame.draw.line(s, rim, (px, 164), (px + 40, 164))
        pygame.draw.line(s, body, (px + 8, 164), (px + 8, 168))
        s.set_at((px + 8, 162), C["sun"])
    return s

def near(width=640):
    """Near layer: dead pylons, wrecked trucks and a broken fence, darkest of all."""
    s = pygame.Surface((width, H), pygame.SRCALPHA)
    rnd = random.Random(19)
    col, hint = C["black"], C["ink"]
    for x in range(0, width, 160):                       # lattice pylons with sagging cables
        px = x + rnd.randrange(20, 60)
        for side in (-1, 1):
            pygame.draw.line(s, col, (px + side * 7, 180), (px + side * 2, 66), 2)
        for y in range(76, 180, 13):
            half = 2 + (y - 66) * 5 // 114
            pygame.draw.line(s, col, (px - half, y), (px + half, y + 13))
            pygame.draw.line(s, col, (px + half, y), (px - half, y + 13))
        for y, arm in ((72, 14), (84, 10), (96, 7)):
            pygame.draw.line(s, col, (px - arm, y), (px + arm, y), 2)
            for dx in (-arm, arm):
                pygame.draw.line(s, col, (px + dx, y), (px + dx, y + 3))
        for dx, y0 in ((-14, 75), (14, 75), (-10, 87)):
            for i in range(0, 160, 3):
                sag = 20 * math.sin(math.pi * i / 160)
                s.set_at(((px + dx + i) % width, int(y0 + sag)), col)
    for x in range(0, width, 2):                         # fence posts and mesh
        if x % 24 == 0:
            pygame.draw.line(s, col, (x, 150), (x, 180), 2)
        if (x // 2) % 2 == 0 and rnd.random() < 0.85:
            s.set_at((x, 152 + (x // 2) % 4), col)
        if x % 96 < 60:
            s.set_at((x, 158 + (x // 2) % 3 * 6), col)
    for _ in range(4):                                   # wrecked trucks
        x = rnd.randrange(0, width - 70)
        pygame.draw.polygon(s, col, [(x, 172), (x + 2, 160), (x + 34, 158), (x + 36, 150), (x + 50, 150),
                                     (x + 56, 160), (x + 62, 164), (x + 62, 172)])
        pygame.draw.polygon(s, hint, [(x + 40, 153), (x + 49, 153), (x + 53, 159), (x + 40, 159)])
        pygame.draw.line(s, hint, (x + 3, 163), (x + 33, 161))
        for wx in (x + 12, x + 48):
            pygame.draw.circle(s, col, (wx, 174), 7)
            pygame.draw.circle(s, hint, (wx, 174), 2)
    pygame.draw.rect(s, col, (0, 178, width, H - 178))
    return s


def pillar():
    """A foreground girder that sweeps past in front of everything (parallax faster than the floor)."""
    s = pygame.Surface((22, H), pygame.SRCALPHA)
    pygame.draw.rect(s, C["black"], (4, 0, 14, H))
    for y in range(0, H, 16):
        pygame.draw.line(s, C["ink"], (4, y), (17, y + 15))
        pygame.draw.line(s, C["ink"], (17, y), (4, y + 15))
        for x in (6, 15):
            s.set_at((x, y + 8), C["night"])
    pygame.draw.line(s, C["ink"], (4, 0), (4, H))
    pygame.draw.line(s, C["night"], (17, 0), (17, H))
    return s


class Atlas:
    """Builds everything once. `convert()` is skipped: it needs a display, and the game also runs headless."""

    def __init__(self):
        self.players = [player_frames(0), player_frames(1)]
        self.players_l = [mirrored(p) for p in self.players]
        self.tall = self.players[0]["stand"].get_height()
        self.guns = {k: held(v, dict(BASE_PAL, R=c), AIMS) for (k, v), c in
                     zip(GUNS.items(), (C["steel"], C["red"], C["blue"], C["olive"]))}
        self.knife = [held(KNIFE, player_pal(i)) for i in (0, 1)]
        self.foe = foe_frames()
        self.foe_l = mirrored(self.foe)
        self.lobber = foe_frames(C["rust"], C["rust_d"], pack=True)
        self.lobber_l = mirrored(self.lobber)
        legion = dict(BASE_PAL, g=mix(C["steel_d"], C["black"], 0.6))
        self.rifle = held(RIFLE, legion)
        self.tube = held(TUBE, legion, ((1, 0, 0), (1, -1, 24)))
        self.white = {}
        self.hostage = hostage_frames()
        self.drone = drone_frames()
        self.turret = turret()
        self.bastion = [bastion(False), bastion(True)]
        self.caps = {"H": capsule("H", C["red"]), "S": capsule("S", C["blue"]), "R": capsule("R", C["olive"]),
                     "B": capsule("B", C["rust"]), "1": capsule("1", C["green"])}
        self.ground = {}
        self.crates = [crate_tile(k) for k in range(3)]
        self.girders = {(a, b): girder_tile(a, b) for a in (False, True) for b in (False, True)}
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

    def ground_at(self, tx, ty, top, left=False, right=False):
        key = (tx % 23, ty, top, left, right)
        if key not in self.ground:
            self.ground[key] = ground_tile(*key)
        return self.ground[key]
