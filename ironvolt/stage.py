"""The missions: each one's tile map, what happens where, its boss, song, backdrop and briefing.

Tiles: 0 air, 1 ground, 2 crate (solid), 3 catwalk (one-way: stand on it, jump up through it).
"""

from .settings import H, TILE, W

ROWS = H // TILE                  # 14
FLOOR_ROW = 11                    # ground fills rows 11..13
AIR, GROUND, CRATE, WALK = 0, 1, 2, 3


def _ground(cols):
    """A flat floor and the tools that carve it; the arena wall closes the right end."""
    g = [[AIR] * cols for _ in range(ROWS)]
    for c in range(cols):
        for r in range(FLOOR_ROW, ROWS):
            g[r][c] = GROUND
    for r in range(0, FLOOR_ROW):          # arena wall: off-screen bounds the camera never shows
        g[r][cols - 1] = GROUND

    def pit(a, b):
        for c in range(a, b + 1):
            for r in range(FLOOR_ROW, ROWS):
                g[r][c] = AIR

    def block(c0, c1, top, kind=GROUND):
        for c in range(c0, c1 + 1):
            for r in range(top, FLOOR_ROW):
                g[r][c] = kind

    def walk(c0, c1, r):
        for c in range(c0, c1 + 1):
            g[r][c] = WALK
    return g, pit, block, walk


def _scrapyard():
    g, pit, block, walk = _ground(232)
    block(14, 14, 10, CRATE)
    block(15, 15, 9, CRATE)
    block(15, 15, 10, CRATE)
    block(24, 29, 9)                       # a raised slab
    walk(32, 37, 7)
    pit(42, 53)                            # the flooded pit: the magnet crane carries you over (SCRAPYARD_PROPS)
    walk(58, 63, 8)
    walk(64, 69, 5)
    block(72, 74, 8)
    pit(80, 82)
    walk(79, 84, 8)                        # a catwalk over the pit
    block(92, 92, 10, CRATE)
    block(100, 105, 8)
    walk(106, 112, 8)
    block(113, 118, 8)
    pit(108, 110)
    block(126, 127, 9, CRATE)              # 119..124: the car presses
    block(127, 127, 8, CRATE)
    pit(128, 133)                          # a rotten catwalk at 130..131 (SCRAPYARD_PROPS)
    walk(134, 140, 7)
    walk(142, 148, 4)
    block(152, 156, 9)
    pit(162, 164)                          # 3 tiles (a running jump clears ~3.4); the grate at 157 leads down
    block(170, 171, 10, CRATE)
    walk(176, 182, 8)
    block(186, 190, 9)
    walk(194, 199, 6)
    block(203, 204, 10, CRATE)
    return g


# (camera x that triggers it, kind, x, extra). x "edge" = just off the right side of the screen.
SCRAPYARD_SPAWNS = [
    (40, "soldier", "edge", None), (100, "hostage", 21 * TILE, "H"),     # in view ahead, not behind the player
    (140, "soldier", "edge", None), (200, "soldier", "edge", None), (300, "soldier", "edge", None), (330, "lobber", 27 * TILE, None),
    (420, "drone", "edge", None), (470, "soldier", "edge", None), (500, "soldier", "edge", None),
    (560, "turret", 36 * TILE, None), (640, "drone", "edge", None), (660, "hostage", 56 * TILE, "B"),
    (700, "soldier", "edge", None), (720, "soldier", "edge", None), (830, "turret", 67 * TILE, None),
    (860, "soldier", "edge", None), (900, "lobber", 73 * TILE, None), (960, "drone", "edge", None),
    (980, "drone", "edge", None), (1040, "soldier", "edge", None), (1100, "soldier", "edge", None),
    (1140, "hostage", 88 * TILE, "S"), (1200, "soldier", "edge", None), (1260, "lobber", 103 * TILE, None),
    (1300, "turret", 116 * TILE, None), (1380, "drone", "edge", None), (1420, "soldier", "edge", None),
    (1440, "soldier", "edge", None), (1500, "soldier", "edge", None), (1560, "hostage", 125 * TILE, "R"),
    (1640, "turret", 137 * TILE, None), (1660, "drone", "edge", None), (1700, "turret", 145 * TILE, None),
    (1760, "soldier", "edge", None), (1800, "lobber", 154 * TILE, None), (1850, "drone", "edge", None),
    (1900, "soldier", "edge", None), (1940, "soldier", "edge", None), (2000, "hostage", 168 * TILE, "H"),
    (2080, "soldier", "edge", None), (2120, "drone", "edge", None), (2150, "drone", "edge", None),
    (2200, "turret", 188 * TILE, None), (2260, "lobber", 196 * TILE, None), (2300, "soldier", "edge", None),
    (2340, "soldier", "edge", None), (2400, "hostage", 200 * TILE, "1"), (2440, "drone", "edge", None),
    (2480, "soldier", "edge", None), (2520, "soldier", "edge", None),
    (50, "barrel", 20 * TILE, None), (962, "barrel", 77 * TILE, None), (2402, "barrel", 167 * TILE, None),
    (1460, "soldier", "edge", None), (1980, "soldier", "edge", None), (2280, "soldier", "edge", None),
    (1230, "trike", "edge", None), (2180, "trike", "edge", None),
]


def _waves(placed, edges, kinds, end):
    """Spawns from a plan: `placed` (kind, column, extra) appear in view ahead, `kinds` cycle in from the edge."""
    out = [(c * TILE - 270, kind, c * TILE, extra) for kind, c, extra in placed]
    out += [(cam, kinds[i % len(kinds)], "edge", None) for i, cam in enumerate(range(edges, end, 70))]
    return out


SCRAPYARD_PROPS = [("crane", 42, 51, 11), ("shutter", 96), ("crusher", 119, 0), ("crusher", 122, 50),
                   ("crumble", 130, 131, 11), ("drain", 157, "stash", 165)]


def _stash():
    """Under the scrapyard: an old tunnel the Legion fills with what it strips from the wrecks. Prisoners kept here,
    and the brother's first map page."""
    g, pit, block, walk = _ground(60)
    for c in range(60):
        for r in range(0, 4):
            g[r][c] = AIR if (1 <= c <= 4 or 54 <= c <= 57) else GROUND
    block(12, 13, 9, CRATE)
    walk(18, 24, 7)
    pit(27, 29)
    block(33, 36, 9)
    block(35, 36, 8, CRATE)
    walk(40, 46, 6)                        # a shelf of scrap, the map page on it
    pit(48, 49)
    return g


STASH_SPAWNS = _waves([("hostage", 16, "S"), ("lobber", 30, None), ("hostage", 38, "1"), ("page", 44, 4),
                       ("hostage", 51, "B"), ("barrel", 25, None)], 40, ["soldier", "soldier", "shield"], 850)


def _line():
    """Mission 2: a rail yard and its viaduct. Containers to climb, gantries over the gaps, a long straight
    track for the arena, and two gantries there to climb when the engine charges."""
    g, pit, block, walk = _ground(248)
    block(12, 14, 9, CRATE)                # a container
    walk(18, 23, 8)
    pit(27, 29)                            # the first gap in the viaduct
    block(34, 35, 10, CRATE)
    block(36, 38, 9, CRATE)                # a stack, stepped
    block(39, 41, 8, CRATE)
    walk(44, 52, 6)
    pit(47, 49)
    block(58, 63, 9)                       # a signal box
    walk(67, 71, 8)                        # a gantry over the gap
    pit(68, 70)
    block(76, 76, 10, CRATE)
    block(84, 89, 8)                       # the loading platform
    walk(90, 97, 8)
    pit(93, 95)
    block(98, 103, 8)                      # the boxcar's ladder at 104: up onto the train's roofs
    block(110, 111, 9, CRATE)
    block(112, 113, 10, CRATE)
    walk(118, 124, 7)
    pit(121, 123)
    walk(126, 132, 4)
    block(138, 142, 9)
    block(148, 149, 10, CRATE)
    block(150, 151, 9, CRATE)
    block(152, 153, 8, CRATE)
    walk(156, 163, 8)
    pit(158, 160)
    block(166, 170, 9)
    pit(175, 177)
    block(180, 181, 9, CRATE)
    walk(181, 187, 6)
    block(192, 197, 8)
    walk(198, 204, 8)
    pit(201, 203)
    block(205, 209, 8)
    pit(210, 214)                          # a rotten catwalk at 211..213 (LINE_PROPS)
    block(215, 216, 10, CRATE)
    walk(230, 235, 8)                      # the arena's gantries: above the engine's roof
    walk(239, 244, 8)
    return g


LINE_SPAWNS = _waves(
    [("hostage", 22, "H"), ("lobber", 40, None), ("turret", 50, None), ("hostage", 61, "S"), ("lobber", 87, None),
     ("hostage", 96, "B"), ("turret", 101, None), ("turret", 129, None), ("lobber", 140, None),
     ("hostage", 152, "R"), ("turret", 161, None), ("lobber", 168, None), ("hostage", 170, "H"),
     ("turret", 184, None), ("hostage", 195, "1"), ("lobber", 207, None), ("sniper", 41, None),
     ("sniper", 130, None), ("barrel", 31, None), ("barrel", 74, None), ("barrel", 135, None)],
    60, ["soldier", "shield", "soldier", "soldier", "drone", "soldier", "trike", "shield", "soldier", "soldier"], 3500)


LINE_PROPS = [("shutter", 80), ("ladder", 104, "roofs", 144), ("crumble", 211, 213, 11)]


def _roofs():
    """On the moving train: one screen of boxcar roofs; the yard rushes past and the gantries come at head height."""
    g, _, _, _ = _ground(21)
    return g


ROOFS_SPAWNS = [(540, "soldier", 290, None), (1000, "soldier", 30, None), (80, "soldier", 280, None), (200, "shield", 260, None), (300, "gift", 160, "S"),
                (420, "soldier", 40, None), (480, "drone", 300, None), (620, "soldier", 270, None),
                (700, "page", 200, 2), (760, "lobber", 60, None), (880, "soldier", 290, None),
                (980, "drone", 20, None), (1060, "shield", 250, None), (1180, "soldier", 60, None)]


def _pylon_road():
    """Mission 3: the service road under the last high-tension line, across the salt flats. Live cross-arms that
    arc on a beat, a storm drain under the road, a gully crossed on the linemen's cable trolley; the arena is open
    road, nothing to stand on under the gunship but the road itself."""
    g, pit, block, walk = _ground(240)
    block(10, 12, 10, CRATE)               # a line truck, nose down in the salt
    block(11, 12, 9, CRATE)
    walk(17, 22, 7)                        # the first pylon's cross-arm, dead
    block(19, 20, 9)                       # ...and its footing
    pit(26, 28)                            # a culvert washed out
    block(33, 33, 10, CRATE)
    walk(36, 43, 8)                        # a live arm (ROAD_PROPS), a dead one above it
    block(38, 41, 9)
    walk(38, 41, 5)
    pit(47, 49)                            # the drain's grate is at 52: under the road from here to 86
    block(56, 58, 9, CRATE)
    block(57, 58, 8, CRATE)
    walk(62, 68, 6)                        # live
    block(64, 65, 9)
    pit(72, 74)
    walk(71, 75, 8)                        # a fallen arm across the gap, still live
    block(80, 84, 8)
    block(90, 90, 10, CRATE)
    pit(100, 129)                          # the gully: the cable trolley crosses it
    block(134, 138, 9)
    walk(142, 149, 7)                      # live
    block(144, 146, 9)
    pit(153, 155)
    block(160, 161, 10, CRATE)
    block(161, 161, 9, CRATE)
    walk(166, 173, 6)                      # live
    block(168, 170, 9)
    pit(177, 179)
    walk(176, 180, 8)                      # live
    block(185, 189, 8)
    block(195, 196, 10, CRATE)
    walk(200, 206, 8)
    block(210, 211, 10, CRATE)
    return g


ROAD_PROPS = [("arc", 36, 43, 8, 0), ("drain", 52, "drain", 86), ("arc", 62, 68, 6, 60), ("arc", 71, 75, 8, 140),
              ("laser", 94), ("trolley", 100, 127, 11), ("arc", 142, 149, 7, 70), ("arc", 166, 173, 6, 140), ("arc", 176, 180, 8, 0),
              ("laser", 192)]
ROAD_SPAWNS = _waves(
    [("hostage", 21, "S"), ("lobber", 40, None), ("hostage", 44, "B"), ("turret", 58, None), ("lobber", 81, None),
     ("hostage", 93, "H"), ("hostage", 136, "R"), ("lobber", 137, None), ("turret", 146, None),
     ("hostage", 158, "S"), ("lobber", 169, None), ("turret", 188, None), ("hostage", 203, "1"),
     ("lobber", 210, None), ("sniper", 40, None), ("sniper", 187, None), ("barrel", 15, None),
     ("barrel", 131, None)],
    60, ["soldier", "sapper", "trike", "soldier", "drone", "soldier", "shield", "sapper", "trike", "soldier"], 3400) + \
    [(cam, "drone", "edge", None) for cam in range(1380, 1860, 80)]      # over the gully, only the air comes at you


def _drain():
    """Under the pylon road: a storm drain, the road for a roof. A water channel, pipe runs, and a way up again."""
    g, pit, block, walk = _ground(72)
    for c in range(72):
        for r in range(0, 4):
            g[r][c] = AIR if (1 <= c <= 4 or 66 <= c <= 69) else GROUND     # the shafts in and out
    pit(14, 16)
    walk(13, 17, 8)                        # a pipe over the channel
    block(24, 25, 9, CRATE)
    walk(30, 40, 7)
    pit(44, 46)
    block(50, 54, 9)
    walk(56, 60, 6)                        # a pipe run, a map page on it
    pit(62, 63)
    return g


DRAIN_SPAWNS = _waves([("hostage", 22, "R"), ("lobber", 36, None), ("hostage", 48, "1"), ("page", 58, 4),
                       ("lobber", 60, None)], 40, ["soldier", "soldier", "shield"], 1000)


def _cradle():
    """Mission 4: the Cradle's outer works, up to the tower that still turns. Steam vents that throw you up to the
    high catwalks, a row of crushers, a stretch where the lights are out, and the lift up the tower; the arena under
    it has two catwalks, high enough that GRAIVE's rig lands under them."""
    g, pit, block, walk = _ground(240)
    block(10, 11, 9, CRATE)
    walk(15, 21, 8)
    pit(25, 27)
    block(31, 35, 9)                       # a reactor block
    block(33, 35, 7)
    walk(36, 52, 4)                        # a high catwalk: the vent at 40 throws you up to it, over the pit
    pit(49, 51)
    block(55, 56, 10, CRATE)
    walk(57, 84, 4)                        # the skyway: vents at 60 and 72, a map page; off its end over the pit
    walk(64, 68, 8)
    pit(81, 83)
    block(86, 90, 8)
    block(114, 115, 10, CRATE)             # 96..109: the crushers (CRADLE_PROPS)
    walk(122, 128, 7)                      # 120..192: the lights are out
    pit(131, 133)
    block(137, 141, 9)
    block(139, 141, 7)
    walk(145, 152, 8)
    pit(156, 158)
    walk(155, 159, 8)
    block(163, 164, 10, CRATE)
    walk(168, 175, 6)
    block(170, 172, 9)
    pit(179, 181)
    block(185, 188, 9)
    pit(192, 197)                          # a rotten catwalk at 194..195, at the end of the dark (CRADLE_PROPS)
    walk(222, 226, 8)                      # the arena's catwalks: above the rig's head
    walk(233, 237, 8)
    return g


CRADLE_PROPS = [("vent", 40), ("vent", 60), ("vent", 72), ("piston", 96, 0), ("piston", 100, 28), ("piston", 104, 56),
                ("piston", 108, 84), ("laser", 118), ("dark", 120, 192), ("crumble", 194, 195, 11), ("door", 198, "lift", 214)]
CRADLE_SPAWNS = _waves(
    [("hostage", 20, "H"), ("turret", 34, None), ("hostage", 44, "B"), ("guard", 66, None), ("page", 77, 2),
     ("turret", 88, None), ("hostage", 87, "S"), ("guard", 140, None), ("hostage", 150, "R"), ("turret", 171, None),
     ("guard", 186, None), ("hostage", 188, "1"), ("sniper", 45, None), ("sniper", 80, None),
     ("barrel", 92, None), ("barrel", 190, None)],
    60, ["guard", "guard", "sapper", "shield", "guard", "drone", "guard", "soldier", "sapper"], 3150)


def _lift():
    """The Cradle's freight lift: one screen of deck, riding up the tower while the guard drops in on it."""
    g, _, _, _ = _ground(21)
    return g


# timed: (frame, kind, x, extra); troopers drop in from above
LIFT_SPAWNS = [(60, "guard", 250, None), (120, "soldier", 70, None), (220, "drone", 300, None),
               (300, "gift", 160, "H"), (360, "guard", 60, None), (380, "sapper", 280, None),
               (520, "drone", 300, None), (560, "guard", 240, None), (600, "shield", 90, None),
               (760, "sapper", 40, None), (780, "guard", 270, None), (900, "drone", 300, None),
               (940, "drone", 20, None), (1000, "guard", 160, None), (1100, "soldier", 280, None),
               (1120, "soldier", 40, None), (460, "guard", 200, None), (840, "guard", 100, None)]

def _hanakiri():
    """Mission 5: HANAKIRI, the Kagenui's temple island. Stone steps up the mountain, rope bridges over the ravines
    (rotten: they drop), a petal-dark grove, the gate to the bell tower; the courtyard at the top has two roofs over
    SORAKAGE's dash."""
    g, pit, block, walk = _ground(248)
    block(10, 12, 10)                      # the first temple steps
    block(11, 12, 9)
    walk(16, 21, 8)                        # a gate's crossbeam
    pit(25, 27)
    block(31, 34, 9)
    walk(36, 41, 6)                        # a pagoda roof
    pit(44, 49)                            # a ravine: the rope bridge at 46..47
    block(53, 54, 10, CRATE)
    walk(58, 64, 7)
    pit(68, 70)
    block(74, 78, 8)                       # the shrine terrace; the gate at 82 leads up the bell tower
    block(90, 92, 9)
    pit(96, 98)
    block(112, 113, 10, CRATE)
    pit(118, 123)                          # the second ravine: a bridge at 120..121
    walk(127, 133, 8)
    block(137, 141, 9)                     # 136..168: the grove, dark under the blossom
    block(139, 141, 7)
    walk(145, 151, 5)
    pit(155, 157)
    walk(154, 158, 8)
    block(163, 166, 9)
    pit(170, 175)                          # the third ravine: a bridge at 172..173
    walk(180, 186, 7)
    block(190, 192, 10, CRATE)
    block(196, 200, 8)
    pit(204, 206)
    block(210, 211, 10, CRATE)
    walk(232, 236, 8)                      # the courtyard's roofs: above the blademaster's dash
    walk(240, 244, 8)
    return g


HANAKIRI_PROPS = [("crumble", 46, 47, 11), ("gate", 82, "bell", 110), ("crumble", 120, 121, 11),
                  ("dark", 136, 168, "BLADES IN THE PETALS!"), ("crumble", 172, 173, 11)]
HANAKIRI_SPAWNS = _waves(
    [("hostage", 20, "S"), ("sniper", 39, None), ("barrel", 52, None), ("hostage", 57, "B"), ("lobber", 76, None),
     ("barrel", 115, None), ("hostage", 130, "H"), ("sniper", 149, None), ("hostage", 165, "R"),
     ("lobber", 188, None), ("hostage", 198, "1"), ("turret", 199, None)],
    60, ["cutter", "soldier", "cutter", "drone", "shield", "cutter", "sapper", "cutter"], 3500)

# the bell tower: one screen of floor, climbing while the clan drops in on it; the map page is in the bell
BELL_SPAWNS = [(60, "cutter", 250, None), (140, "cutter", 60, None), (220, "soldier", 280, None),
               (300, "gift", 160, "S"), (380, "cutter", 280, None), (420, "hostage", 200, "H"),
               (460, "shield", 60, None), (540, "page", 160, 3), (600, "cutter", 60, None), (680, "drone", 300, None),
               (760, "cutter", 250, None), (840, "cutter", 40, None), (920, "soldier", 280, None),
               (1000, "cutter", 160, None)]


def _harbour():
    """Mission 6: YAMIMINATO, the port where the Tide cable comes ashore, at night in the rain. Fire escapes, live
    neon cables over the awnings, the harbour crane over the flooded dock, Legion checkpoints, the sewers, a rotten
    pier; the quay at the end has two gantries level with TIDEBREAKER's cab."""
    g, pit, block, walk = _ground(248)
    block(10, 12, 9, CRATE)                # a container
    walk(16, 22, 7)                        # a fire escape
    pit(26, 28)                            # a flooded gutter
    block(32, 33, 10, CRATE)
    walk(36, 44, 8)                        # a live neon cable along the awnings (HARBOUR_PROPS)
    block(48, 52, 9)                       # the shutter at 56
    pit(64, 77)                            # the flooded dock: the harbour crane carries you over
    block(82, 84, 9, CRATE)
    block(85, 87, 8, CRATE)
    walk(91, 97, 6)                        # the laser fence at 101
    pit(109, 111)
    block(115, 119, 9)                     # the sewer grate at 123: under the street to 150
    block(128, 131, 9)
    pit(136, 138)
    walk(142, 147, 7)
    block(152, 153, 10, CRATE)
    walk(157, 164, 7)                      # live
    block(159, 162, 9)
    pit(168, 170)                          # the shutter at 175
    block(183, 187, 8)
    pit(191, 196)                          # a rotten pier: planks at 193..194
    walk(200, 206, 6)
    block(202, 204, 9)
    block(210, 211, 10, CRATE)
    walk(229, 233, 6)                      # the quay's gantries: level with the crane's cab
    walk(238, 242, 6)
    return g


HARBOUR_PROPS = [("arc", 36, 44, 8, 0), ("shutter", 56), ("crane", 64, 75, 11), ("laser", 101),
                 ("drain", 123, "sewer", 150), ("arc", 157, 164, 7, 90), ("shutter", 175), ("crumble", 193, 194, 11)]
HARBOUR_SPAWNS = _waves(
    [("hostage", 24, "H"), ("barrel", 34, None), ("sniper", 42, None), ("hostage", 47, "S"), ("turret", 86, None),
     ("hostage", 90, "B"), ("sniper", 95, None), ("lobber", 118, None), ("hostage", 156, "R"), ("barrel", 172, None),
     ("lobber", 186, None), ("hostage", 199, "1"), ("sniper", 204, None)],
    60, ["soldier", "trike", "cutter", "soldier", "drone", "shield", "trike", "sapper", "cutter", "soldier"], 3500)


def _sewer():
    """Under Yamiminato: the storm sewers, the cable's old service tunnel among them."""
    g, pit, block, walk = _ground(64)
    for c in range(64):
        for r in range(0, 4):
            g[r][c] = AIR if (1 <= c <= 4 or 58 <= c <= 61) else GROUND
    block(10, 11, 9, CRATE)
    pit(16, 18)
    walk(15, 19, 8)
    walk(24, 31, 6)                        # a pipe run
    block(36, 39, 9)
    pit(44, 46)
    walk(48, 54, 7)                        # the switchboard ledge, the map page on it
    return g


SEWER_SPAWNS = _waves([("hostage", 22, "S"), ("lobber", 38, None), ("hostage", 42, "1"), ("page", 51, 4),
                       ("hostage", 55, "B")], 40, ["soldier", "cutter", "shield"], 900)

# Rooms: places off the main road, entered by a prop (drain, door). theme: art.backdrop; dark: 0..255; lamps: x of
# the lights in a dark room; timed: frames it lasts (spawns by frame, not by camera); ceil: feet y under its roof.
ROOMS = {
    "drain": dict(build=_drain, spawns=DRAIN_SPAWNS, theme=4, dark=150, lamps=(40, 330, 640, 900, 1080), ceil=86),
    "lift": dict(build=_lift, spawns=LIFT_SPAWNS, theme=5, timed=1200, shout="GOING UP!"),
    "stash": dict(build=_stash, spawns=STASH_SPAWNS, theme=4, dark=110, lamps=(40, 300, 560, 820), ceil=86),
    "bell": dict(build=_lift, spawns=BELL_SPAWNS, theme=7, timed=1100, shout="UP THE BELL TOWER!", sound="bell"),
    "sewer": dict(build=_sewer, spawns=SEWER_SPAWNS, theme=4, dark=150, lamps=(40, 330, 620, 860), ceil=86),
    "roofs": dict(build=_roofs, spawns=ROOFS_SPAWNS, theme=6, timed=1300, run=6, shout="RIDE THE TRAIN!",
                  sound="whistle", props=[("gantries", 150, 190, 1200)]),
}


def _section(n):
    """A stretch of road to splice into a mission: a flat floor and the same tools, no arena wall."""
    g, pit, block, walk = _ground(n)
    for r in range(FLOOR_ROW):
        g[r][n - 1] = AIR
    return g, pit, block, walk


def _gate_yard():
    """Mission 1's last stretch before the gate: a shutter, a rotten catwalk over the slurry, a car press."""
    g, pit, block, walk = _section(32)
    block(4, 5, 10, CRATE)
    pit(16, 21)                            # the rotten catwalk at 18..19
    walk(23, 26, 8)
    return g


def _signal_gantry():
    """Mission 2's last stretch: a signal gantry over a gap, a shutter at the yard's gate, a stepped stack."""
    g, pit, block, walk = _section(32)
    block(3, 5, 9, CRATE)
    walk(8, 13, 8)
    pit(10, 12)
    block(24, 25, 10, CRATE)
    block(26, 27, 9, CRATE)
    return g


def _last_pylon():
    """Mission 3's last stretch: one more live arm, the Legion's checkpoint fences either side of a culvert."""
    g, pit, block, walk = _section(32)
    walk(3, 10, 8)                         # live
    block(5, 8, 9)
    pit(20, 22)
    return g


def _turbine_hall():
    """Mission 4's last stretch: a vent up to a catwalk over a pit, a crusher, a fence, the hall's last gap."""
    g, pit, block, walk = _section(32)
    walk(4, 14, 4)
    pit(9, 11)
    pit(26, 28)
    return g


SPAN = ("crane", "arc", "trolley", "dark", "crumble")      # props whose second number is a column too
INTO = ("drain", "door", "ladder", "gate")                         # props whose third number is the room's exit column


def _moved(spec, move):
    cols = {1} | ({2} if spec[0] in SPAN else set()) | ({3} if spec[0] in INTO else set())
    return tuple(move(v) if i in cols else v for i, v in enumerate(spec))


class Mission:
    def __init__(self, number, name, build, spawns, boss_col, boss, boss_title, song, theme, briefing, outro,
                 props=(), more=None):
        """more: (column, section, placed spawns, edge kinds, props) a stretch spliced in at that column; what
        lies past it (the arena, the boss, spawns, props) moves along. Section columns count from its start."""
        props, spawns = list(props), list(spawns)
        if more:
            at, section, placed, kinds, extra = more
            n, road = len(section()[0]), build

            def build():
                g, sec = road(), section()
                for r in range(ROWS):
                    g[r][at:at] = sec[r]
                return g
            boss_col += n
            props = [_moved(p, lambda c: c + n if c >= at else c) for p in props] +                 [_moved(p, lambda c: c + at) for p in extra]
            x0, dx = at * TILE, n * TILE
            spawns = [(c + dx, k, x if x == "edge" else x + dx, e)
                      if (x == "edge" and c + W >= x0) or (x != "edge" and x >= x0) else (c, k, x, e)
                      for c, k, x, e in spawns]
            spawns += _waves([(k, c + at, e) for k, c, e in placed], x0 - W, kinds, x0 + dx - W)
        self.number, self.name, self.build, self.spawns, self.props = number, name, build, spawns, props
        self.boss_col, self.boss, self.boss_title = boss_col, boss, boss_title
        self.song, self.theme, self.briefing, self.outro = song, theme, briefing, outro


MISSIONS = [
    Mission(1, "SCRAPYARD DUSK", _scrapyard, SCRAPYARD_SPAWNS, 212, "bastion", "BASTION  LEGION GATE CRAWLER",
            ("stage", "boss"), 0, ["FREE THE CAPTURED TECHNICIANS.", "BREAK THE LEGION GATE."],
            ["THE GATE IS DOWN.", "THE PRISONERS WERE MOVED BY RAIL."], SCRAPYARD_PROPS,
            (206, _gate_yard, [("hostage", 12, "S"), ("lobber", 25, None), ("barrel", 27, None)],
             ["soldier", "soldier", "drone"],
             [("shutter", 9), ("crumble", 18, 19, 11), ("crusher", 29, 40)])),
    Mission(2, "THE PRISONER LINE", _line, LINE_SPAWNS, 228, "warden", "WARDEN  PRISONER LINE ENGINE",
            ("line", "warden"), 1, ["THE LEGION SHIPS ITS PRISONERS BY RAIL.", "STOP THE TRAIN."],
            ["THE PRISONER CARS ARE OPEN.", "KES'S BROTHER WAS NOT ABOARD."], LINE_PROPS,
            (218, _signal_gantry, [("hostage", 20, "B"), ("turret", 12, None), ("lobber", 27, None)],
             ["soldier", "shield", "soldier"], [("shutter", 17)])),
    Mission(3, "PYLON ROAD", _pylon_road, ROAD_SPAWNS, 220, "harrow", "HARROW  LINE SURVEY GUNSHIP",
            ("pylon", "harrow"), 2, ["THE LAST LIVE LINE RUNS TO THE CRADLE.", "FOLLOW IT. DOWN THE GUNSHIP."],
            ["HARROW'S LOG CARRIES THE BROTHER'S MAPS.", "GRAIVE IS RELIGHTING THE OLD GRID."], ROAD_PROPS,
            (213, _last_pylon, [("hostage", 16, "R"), ("lobber", 29, None)], ["trike", "sapper", "soldier"],
             [("arc", 3, 10, 8, 30), ("laser", 13), ("laser", 27)])),
    Mission(4, "THE CRADLE", _cradle, CRADLE_SPAWNS, 220, "graive", "GRAIVE  WARLORD OF THE CRADLE",
            ("cradle", "graive"), 3, ["THE CRADLE STILL TURNS. GRAIVE IS INSIDE.", "TAKE THE TOWER. FIND KES'S BROTHER."],
            ["GRAIVE IS DOWN. THE CRADLE IS OURS.", "KES'S BROTHER IS AT THE CONTROLS."], CRADLE_PROPS,
            (216, _turbine_hall, [("hostage", 19, "H"), ("guard", 24, None)], ["guard", "soldier", "guard"],
             [("vent", 2), ("piston", 16, 0), ("laser", 21)])),
    Mission(5, "HANAKIRI", _hanakiri, HANAKIRI_SPAWNS, 228, "sorakage", "SORAKAGE  CLAN BLADEMASTER",
            ("sakura", "blademaster"), 7, ["THE CRADLE'S POWER RUNS EAST BY SEA.", "CLIMB HANAKIRI. BREAK THE KAGENUI."],
            ["SORAKAGE LOWERS HIS SWORD.", "THE ROAD TO THE HARBOUR IS OPEN."], HANAKIRI_PROPS),
    Mission(6, "YAMIMINATO", _harbour, HARBOUR_SPAWNS, 226, "tidebreaker", "TIDEBREAKER  GANTRY WALKER",
            ("harbour", "leviathan"), 8, ["THE CABLE COMES ASHORE IN THE RAIN.", "CUT GRAIVE'S FEED AT THE QUAY."],
            ["THE CABLE STATION IS OURS.", "THE RAIN HAS STOPPED."], HARBOUR_PROPS),
]


class Stage:
    """A mission's main road, or one of its rooms (ROOMS): the tiles, the spawns, the props, how it is lit."""

    def __init__(self, index=0, room=None):
        self.index, self.room = index, room
        self.mission = m = MISSIONS[index]
        r = ROOMS[room] if room else dict(build=m.build, spawns=m.spawns, theme=m.theme, props=m.props)
        self.grid = r["build"]()
        self.cols = len(self.grid[0])
        self.width = self.cols * TILE
        self.boss_x = m.boss_col * TILE if not room else 10 ** 6
        self.spawns = sorted(r["spawns"], key=lambda s: s[0])
        self.theme, self.props = r["theme"], r.get("props", ())
        self.dark, self.lamps, self.timed = r.get("dark", 0), r.get("lamps", ()), r.get("timed", 0)
        self.run, self.shout = r.get("run", 0), r.get("shout", "DOWN WE GO!")      # run: px a frame the world rushes past
        self.sound = r.get("sound", "lift" if self.timed else "drop")
        self.drop_y = r.get("ceil", -10)          # where a player drops back in: from the sky, or under the roof

    def hostage_count(self):
        """Every prisoner in the mission: on the road and in its rooms."""
        rooms = [ROOMS[p[2]] for p in self.mission.props if p[0] in INTO]
        return sum(s[1] == "hostage" for r in [dict(spawns=self.mission.spawns)] + rooms for s in r["spawns"])

    @property
    def last(self):
        return self.index == len(MISSIONS) - 1

    def tile(self, tx, ty):
        if tx < 0 or tx >= self.cols:
            return GROUND                       # the stage ends are walls
        if ty < 0 or ty >= ROWS:
            return AIR                          # open sky above, pits below
        return self.grid[ty][tx]

    def solid(self, tx, ty):
        return self.tile(tx, ty) in (GROUND, CRATE)

    def floor_y(self, x, from_y=0):
        """The top of the first standable tile below from_y in this column (pits give None)."""
        tx = int(x) // TILE
        for ty in range(max(0, int(from_y) // TILE), ROWS):
            if self.tile(tx, ty) != AIR:
                return ty * TILE
        return None
