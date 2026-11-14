"""The missions: each one's tile map, what happens where, its boss, song, backdrop and briefing.

Tiles: 0 air, 1 ground, 2 crate (solid), 3 catwalk (one-way: stand on it, jump up through it).
"""

from .settings import H, TILE

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
    pit(42, 44)
    block(52, 53, 9, CRATE)
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
    block(126, 127, 9, CRATE)
    block(127, 127, 8, CRATE)
    walk(134, 140, 7)
    walk(142, 148, 4)
    block(152, 156, 9)
    pit(162, 164)                          # pits stay 3 tiles: a running jump clears ~3.4
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
    (1440, "soldier", "edge", None), (1500, "soldier", "edge", None), (1560, "hostage", 122 * TILE, "R"),
    (1640, "turret", 137 * TILE, None), (1660, "drone", "edge", None), (1700, "turret", 145 * TILE, None),
    (1760, "soldier", "edge", None), (1800, "lobber", 154 * TILE, None), (1850, "drone", "edge", None),
    (1900, "soldier", "edge", None), (1940, "soldier", "edge", None), (2000, "hostage", 168 * TILE, "H"),
    (2080, "soldier", "edge", None), (2120, "drone", "edge", None), (2150, "drone", "edge", None),
    (2200, "turret", 188 * TILE, None), (2260, "lobber", 196 * TILE, None), (2300, "soldier", "edge", None),
    (2340, "soldier", "edge", None), (2400, "hostage", 200 * TILE, "1"), (2440, "drone", "edge", None),
    (2480, "soldier", "edge", None), (2520, "soldier", "edge", None),
]


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
    block(98, 103, 8)
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
    block(215, 216, 10, CRATE)
    walk(230, 235, 8)                      # the arena's gantries: above the engine's roof
    walk(239, 244, 8)
    return g


def _waves(placed, edges, kinds, end):
    """Spawns from a plan: `placed` (kind, column, extra) appear in view ahead, `kinds` cycle in from the edge."""
    out = [(c * TILE - 270, kind, c * TILE, extra) for kind, c, extra in placed]
    out += [(cam, kinds[i % len(kinds)], "edge", None) for i, cam in enumerate(range(edges, end, 70))]
    return out


LINE_SPAWNS = _waves(
    [("hostage", 22, "H"), ("lobber", 40, None), ("turret", 50, None), ("hostage", 61, "S"), ("lobber", 87, None),
     ("hostage", 96, "B"), ("turret", 101, None), ("turret", 129, None), ("lobber", 140, None),
     ("hostage", 152, "R"), ("turret", 161, None), ("lobber", 168, None), ("hostage", 170, "H"),
     ("turret", 184, None), ("hostage", 195, "1"), ("lobber", 207, None)],
    60, ["soldier", "shield", "soldier", "soldier", "drone", "soldier", "shield", "soldier"], 3500)


def _pylon_road():
    """Mission 3: the service road under the last high-tension line, across the salt flats. Pylon footings to
    climb, their cross-arms as walkways, wrecked line trucks, washed-out culverts; the arena is open road, nothing
    to stand on under the gunship but the road itself."""
    g, pit, block, walk = _ground(240)
    block(10, 12, 10, CRATE)               # a line truck, nose down in the salt
    block(11, 12, 9, CRATE)
    walk(17, 22, 7)                        # the first pylon's cross-arm
    block(19, 20, 9)                       # ...and its footing
    pit(26, 28)                            # a culvert washed out
    block(33, 33, 10, CRATE)
    walk(36, 43, 8)
    block(38, 41, 9)
    walk(38, 41, 5)
    pit(47, 49)
    block(54, 56, 9, CRATE)
    block(55, 56, 8, CRATE)
    walk(60, 66, 6)
    block(62, 63, 9)
    pit(70, 72)
    walk(69, 73, 8)                        # a fallen arm across the gap
    block(78, 82, 8)
    block(88, 88, 10, CRATE)
    walk(92, 99, 7)
    block(94, 96, 9)
    pit(103, 105)
    block(110, 112, 9, CRATE)
    walk(116, 123, 8)
    walk(119, 122, 5)
    block(120, 121, 9)
    pit(127, 129)
    block(134, 138, 9)
    block(142, 143, 10, CRATE)
    block(143, 143, 9, CRATE)
    walk(148, 155, 6)
    block(150, 152, 9)
    pit(159, 161)
    walk(158, 162, 8)
    block(166, 170, 8)
    block(176, 177, 10, CRATE)
    walk(181, 188, 7)
    block(183, 185, 9)
    pit(192, 194)
    block(199, 201, 9, CRATE)
    block(200, 201, 8, CRATE)
    walk(205, 211, 8)
    block(214, 215, 10, CRATE)
    return g


ROAD_SPAWNS = _waves(
    [("hostage", 21, "S"), ("lobber", 40, None), ("turret", 56, None), ("hostage", 64, "H"), ("lobber", 81, None),
     ("hostage", 95, "B"), ("turret", 111, None), ("hostage", 121, "R"), ("lobber", 137, None),
     ("turret", 151, None), ("hostage", 168, "S"), ("lobber", 169, None), ("turret", 185, None),
     ("hostage", 200, "1"), ("lobber", 210, None)],
    60, ["soldier", "sapper", "soldier", "drone", "shield", "sapper", "soldier", "soldier"], 3400)


class Mission:
    def __init__(self, number, name, build, spawns, boss_col, boss, boss_title, song, theme, briefing, outro):
        self.number, self.name, self.build, self.spawns = number, name, build, spawns
        self.boss_col, self.boss, self.boss_title = boss_col, boss, boss_title
        self.song, self.theme, self.briefing, self.outro = song, theme, briefing, outro


MISSIONS = [
    Mission(1, "SCRAPYARD DUSK", _scrapyard, SCRAPYARD_SPAWNS, 212, "bastion", "BASTION  LEGION GATE CRAWLER",
            ("stage", "boss"), 0, ["FREE THE CAPTURED TECHNICIANS.", "BREAK THE LEGION GATE."],
            ["THE GATE IS DOWN.", "THE PRISONERS WERE MOVED BY RAIL."]),
    Mission(2, "THE PRISONER LINE", _line, LINE_SPAWNS, 228, "warden", "WARDEN  PRISONER LINE ENGINE",
            ("line", "warden"), 1, ["THE LEGION SHIPS ITS PRISONERS BY RAIL.", "STOP THE TRAIN."],
            ["THE PRISONER CARS ARE OPEN.", "KES'S BROTHER WAS NOT ABOARD."]),
    Mission(3, "PYLON ROAD", _pylon_road, ROAD_SPAWNS, 220, "harrow", "HARROW  LINE SURVEY GUNSHIP",
            ("pylon", "harrow"), 2, ["THE LAST LIVE LINE RUNS TO THE CRADLE.", "FOLLOW IT. DOWN THE GUNSHIP."],
            ["HARROW'S LOG CARRIES THE BROTHER'S MAPS.", "GRAIVE IS RELIGHTING THE OLD GRID."]),
]


class Stage:
    def __init__(self, index=0):
        self.index = index
        self.mission = m = MISSIONS[index]
        self.grid = m.build()
        self.cols = len(self.grid[0])
        self.width = self.cols * TILE
        self.boss_x = m.boss_col * TILE
        self.spawns = sorted(m.spawns, key=lambda s: s[0])

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
