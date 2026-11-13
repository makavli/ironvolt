"""Renders the itch.io cover (630x500) from the game's own art: the bot plays to a moment of the boss fight, the
action is cropped and drawn 4x, and the logo goes over the sky. Headless.

    python tools/cover.py            candidates in shots/cover_*.png plus shots/cover_sheet.png to choose from
    python tools/cover.py 4321       renders that frame number as docs/media/cover.png
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pygame
pygame.init()
from ironvolt import font
from ironvolt.art import Atlas
from ironvolt.autopilot import BotPad
from ironvolt.settings import C, H, W
from ironvolt.world import World

CW, CH = 315, 250                                   # a sheet tile: the cover at half size
ROOT = os.path.join(os.path.dirname(__file__), "..")
atlas = Atlas()
logo = font.logo("IRONVOLT", 4, C["cream"], C["ember"], C["ink"])


def compose(frame, cx):
    """The action around screen x `cx`, cropped and drawn 4x (whole pixels), with the logo drawn 3x over the sky."""
    zw, zh = 158, 125                                        # 158x125 game pixels above most of the dirt, 4x, is itch's 630x500 plus 2
    x = max(0, min(W - zw, int(cx) - zw // 2))
    scene = pygame.transform.scale(frame.subsurface((x, H - zh - 30, zw, zh)), (zw * 4, zh * 4))
    cover = pygame.Surface((630, 500))
    cover.blit(scene, (-1, 0))
    shade = pygame.Surface((630, 190), pygame.SRCALPHA)      # darkens the sky under the logo, fading downwards
    for y in range(190):
        pygame.draw.line(shade, (8, 6, 14, int(170 * (1 - y / 190) ** 1.5)), (0, y), (630, y))
    cover.blit(shade, (0, 0))
    big = pygame.transform.scale(logo, (logo.get_width() * 3, logo.get_height() * 3))
    cover.blit(big, ((630 - big.get_width()) // 2, 18))
    tag = pygame.Surface((font.width("ARCADE RUN AND GUN") + 2, 10), pygame.SRCALPHA)
    font.draw(tag, "ARCADE RUN AND GUN", (0, 0), C["ember"])
    tag = pygame.transform.scale(tag, (tag.get_width() * 3, tag.get_height() * 3))
    cover.blit(tag, ((630 - tag.get_width()) // 2, 18 + big.get_height() + 6))
    return cover


def play(wanted):
    """Steps the bot's two-player run; returns {frame number: picture without HUD} for the wanted frames."""
    w, bots = World((0, 1), seed=3, god=True), [BotPad(), BotPad()]
    out, fight = {}, None
    for f in range(12000):
        for i in (0, 1):
            bots[i].think(w, w.players[i])
        w.step(bots)
        if fight is None and w.boss and w.boss.state == "fight":
            fight = f
        auto = wanted == "auto"
        if (auto and fight and (f - fight) % 50 == 0 and f - fight <= 750) or (not auto and f in wanted):
            s = pygame.Surface((W, H))
            w.draw(s, atlas)
            cam = w.cam_x
            xs = [p.x - cam for p in w.players if not p.out] + ([w.boss.x - cam] * 2 if w.boss else [])
            out[f] = (s, sum(xs) / len(xs) if xs else W / 2)
        if w.cleared > 5 or (wanted != "auto" and f > max(wanted)):
            break
    return out


if len(sys.argv) > 1:
    n = int(sys.argv[1])
    path = os.path.join(ROOT, "docs", "media", "cover.png")
    pygame.image.save(compose(*play({n})[n]), path)
    print("saved", path)
else:
    pics = play("auto")
    shots = os.path.join(ROOT, "shots")
    os.makedirs(shots, exist_ok=True)
    cols = 4
    sheet = pygame.Surface((cols * CW, ((len(pics) + cols - 1) // cols) * CH))
    for i, (f, shot) in enumerate(sorted(pics.items())):
        c = compose(*shot)
        pygame.image.save(c, os.path.join(shots, "cover_%d.png" % f))
        small = pygame.transform.scale(c, (CW, CH))
        font.draw(small, str(f), (4, CH - 12), C["cream"])
        sheet.blit(small, ((i % cols) * CW, (i // cols) * CH))
    pygame.image.save(sheet, os.path.join(shots, "cover_sheet.png"))
    print(len(pics), "candidates: shots/cover_sheet.png")
