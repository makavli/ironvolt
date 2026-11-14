"""A 5x7 arcade bitmap font, drawn from bits (no font files, nothing to license)."""

import math

import pygame

_GLYPHS = {
    "A": "0E 11 11 1F 11 11 11", "B": "1E 11 11 1E 11 11 1E", "C": "0E 11 10 10 10 11 0E",
    "D": "1E 11 11 11 11 11 1E", "E": "1F 10 10 1E 10 10 1F", "F": "1F 10 10 1E 10 10 10",
    "G": "0E 11 10 17 11 11 0F", "H": "11 11 11 1F 11 11 11", "I": "0E 04 04 04 04 04 0E",
    "J": "07 02 02 02 02 12 0C", "K": "11 12 14 18 14 12 11", "L": "10 10 10 10 10 10 1F",
    "M": "11 1B 15 15 11 11 11", "N": "11 11 19 15 13 11 11", "O": "0E 11 11 11 11 11 0E",
    "P": "1E 11 11 1E 10 10 10", "Q": "0E 11 11 11 15 12 0D", "R": "1E 11 11 1E 14 12 11",
    "S": "0F 10 10 0E 01 01 1E", "T": "1F 04 04 04 04 04 04", "U": "11 11 11 11 11 11 0E",
    "V": "11 11 11 11 11 0A 04", "W": "11 11 11 15 15 15 0A", "X": "11 11 0A 04 0A 11 11",
    "Y": "11 11 0A 04 04 04 04", "Z": "1F 01 02 04 08 10 1F",
    "0": "0E 11 13 15 19 11 0E", "1": "04 0C 04 04 04 04 0E", "2": "0E 11 01 02 04 08 1F",
    "3": "1F 02 04 02 01 11 0E", "4": "02 06 0A 12 1F 02 02", "5": "1F 10 1E 01 01 11 0E",
    "6": "06 08 10 1E 11 11 0E", "7": "1F 01 02 04 08 08 08", "8": "0E 11 11 0E 11 11 0E",
    "9": "0E 11 11 0F 01 02 0C", " ": "00 00 00 00 00 00 00", "!": "04 04 04 04 04 00 04",
    ".": "00 00 00 00 00 0C 0C", ",": "00 00 00 00 0C 04 08", "-": "00 00 00 1F 00 00 00",
    ":": "00 0C 0C 00 0C 0C 00", "?": "0E 11 01 02 04 00 04", "'": "04 04 08 00 00 00 00",
    "/": "01 01 02 04 08 10 10", ">": "08 04 02 01 02 04 08", "<": "02 04 08 10 08 04 02",
    "=": "00 00 1F 00 1F 00 00", "+": "00 04 04 1F 04 04 00", "(": "02 04 08 08 08 04 02",
    ")": "08 04 02 02 02 04 08", "#": "0A 1F 0A 0A 1F 0A 00", "*": "00 15 0E 1F 0E 15 00",
    "%": "18 19 02 04 08 13 03",
}
GLYPH_W, GLYPH_H, ADVANCE = 5, 7, 6
_cache = {}


def _glyph(ch, colour):
    key = (ch, colour)
    if key not in _cache:
        surf = pygame.Surface((GLYPH_W, GLYPH_H), pygame.SRCALPHA)
        for y, row in enumerate(_GLYPHS.get(ch, _GLYPHS["?"]).split()):
            bits = int(row, 16)
            for x in range(GLYPH_W):
                if bits & (0x10 >> x):
                    surf.set_at((x, y), colour)
        _cache[key] = surf
    return _cache[key]


def width(text, scale=1):
    return (len(text) * ADVANCE - 1) * scale


def draw(surf, text, pos, colour=(255, 255, 255), scale=1, shadow=(8, 6, 14), center=False):
    """Draws upper-case text with a one-pixel drop shadow. pos is the top-left (or top-centre)."""
    text = text.upper()
    x, y = pos
    if center:
        x -= width(text, scale) // 2
    for i, ch in enumerate(text):
        gx = x + i * ADVANCE * scale
        for col, off in (((shadow, scale), (colour, 0)) if shadow else ((colour, 0),)):
            g = _glyph(ch, col)
            if scale != 1:
                g = pygame.transform.scale(g, (GLYPH_W * scale, GLYPH_H * scale))
            surf.blit(g, (gx + off, y + off))
    return x


def wobble(surf, text, centre, frame, colours=((255, 214, 64), (255, 255, 255))):
    """A sign that bounces: each letter bobs on its own beat and the colours take turns. For "GO DOWN!" moments."""
    text = text.upper()
    x = centre[0] - width(text) // 2
    for i, ch in enumerate(text):
        dy = round(2.5 * math.sin(frame * 0.25 - i * 0.7))
        draw(surf, ch, (x + i * ADVANCE, centre[1] + dy), colours[(i + frame // 8) % len(colours)])


def logo(text, scale, top, bottom, outline):
    """Big title text: a vertical gradient fill with a hard outline, like a marquee."""
    w, h = width(text, scale) + 4, GLYPH_H * scale + 4
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    draw(mask, text, (2, 2), (255, 255, 255), scale, shadow=None)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    m = pygame.mask.from_surface(mask)
    edge = m.to_surface(setcolor=outline, unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1), (2, 2)):
        out.blit(edge, (dx, dy))
    fill = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        band = 0.15 if (y // scale) % 3 == 1 else 0.0        # a bright stripe through each pixel row
        c = [min(255, int(top[i] + (bottom[i] - top[i]) * t + 255 * band)) for i in range(3)]
        pygame.draw.line(fill, c, (0, y), (w, y))
    fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    out.blit(fill, (0, 0))
    return out
