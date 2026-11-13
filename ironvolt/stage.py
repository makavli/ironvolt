"""Stage 1, SCRAPYARD DUSK: the tile map and what happens where.

Tiles: 0 air, 1 ground, 2 crate (solid), 3 catwalk (one-way: stand on it, jump up through it).
"""

from .settings import H, TILE

ROWS = H // TILE                  # 14
FLOOR_ROW = 11                    # ground fills rows 11..13
COLS = 232
BOSS_COL = 212                    # the arena: the camera locks here and the boss rolls in
NAME = "STAGE 1  SCRAPYARD DUSK"

AIR, GROUND, CRATE, WALK = 0, 1, 2, 3


def _build():
    g = [[AIR] * COLS for _ in range(ROWS)]
    for c in range(COLS):
        for r in range(FLOOR_ROW, ROWS):
            g[r][c] = GROUND

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
    for r in range(0, FLOOR_ROW):          # arena walls: off-screen bounds the camera never shows
        g[r][COLS - 1] = GROUND
    return g


# (camera x that triggers it, kind, x, extra). x "edge" = just off the right side of the screen.
SPAWNS = [
    (40, "soldier", "edge", None), (140, "soldier", "edge", None), (200, "soldier", "edge", None),
    (260, "hostage", 21 * TILE, "H"), (300, "soldier", "edge", None), (330, "lobber", 27 * TILE, None),
    (420, "drone", "edge", None), (470, "soldier", "edge", None), (500, "soldier", "edge", None),
    (560, "turret", 36 * TILE, None), (640, "drone", "edge", None), (700, "soldier", "edge", None),
    (720, "soldier", "edge", None), (760, "hostage", 56 * TILE, "B"), (830, "turret", 67 * TILE, None),
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


class Stage:
    def __init__(self):
        self.grid = _build()
        self.width = COLS * TILE
        self.boss_x = BOSS_COL * TILE
        self.spawns = sorted(SPAWNS, key=lambda s: s[0])

    def tile(self, tx, ty):
        if tx < 0 or tx >= COLS:
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
