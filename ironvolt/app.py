"""The window and the loop.

The game draws into a 320x224 surface. The GPU scales it by the largest whole number that fits (sharp pixels,
no shimmer), centres it, frames it with a cabinet bezel, and lays optional scanlines over it. Logic steps at a
fixed 60 Hz; presentation is vsynced.
"""

import os
import sys

import pygame

from . import __version__, audio
from .art import Atlas
from .controls import Controls
from .game import Game
from .settings import C, H, MAX_DT, STEP, W


def integer_fit(window, game=(W, H)):
    """The whole-number scale and the centred rectangle for the game inside a window of this size."""
    k = max(1, min(window[0] // game[0], window[1] // game[1]))
    gw, gh = game[0] * k, game[1] * k
    return k, pygame.Rect((window[0] - gw) // 2, (window[1] - gh) // 2, gw, gh)


def bezel(size, rect):
    """Side panels like a cabinet's: dark metal, a lit trim around the screen."""
    s = pygame.Surface(size)
    s.fill(C["black"])
    for x in range(0, size[0], 4):
        pygame.draw.line(s, (14, 11, 24), (x, 0), (x, size[1]))
    pygame.draw.rect(s, C["ink"], rect.inflate(12, 12))
    pygame.draw.rect(s, C["night"], rect.inflate(8, 8), 2)
    pygame.draw.rect(s, C["dusk"], rect.inflate(4, 4), 1)
    return s


def scanlines(k, rect):
    """A dark line under every scaled pixel row (only when pixels are big enough for it to read as CRT)."""
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    if k >= 3:
        for y in range(k - 1, rect.height, k):
            pygame.draw.line(s, (0, 0, 0, 70), (0, y), (rect.width, y))
    return s


class App:
    def __init__(self):
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "0")      # nearest: crisp pixels
        pygame.init()
        audio.init()
        from pygame._sdl2.video import Renderer, Texture
        self.Texture = Texture
        desk = pygame.display.get_desktop_sizes()[0]
        k, _ = integer_fit((desk[0] - 80, desk[1] - 120))
        self.window = pygame.Window("IRONVOLT " + __version__, (W * k, H * k), resizable=True)
        self.window.minimum_size = (W, H)
        self.renderer = Renderer(self.window, vsync=True)
        self.screen = pygame.Surface((W, H))
        self.tex = Texture.from_surface(self.renderer, self.screen)
        self.atlas = Atlas()
        self.window.set_icon(self.atlas.players[0]["stand"])
        self.game = Game(self.atlas)
        self.controls = Controls()
        self.crt = True
        self.full = False
        self.frame_cache = None

    def layout(self):
        size = self.window.size
        k, rect = integer_fit(size)
        key = (size, self.crt)
        if self.frame_cache is None or self.frame_cache[0] != key:
            self.frame_cache = (key, k, rect, self.Texture.from_surface(self.renderer, bezel(size, rect)),
                                self.Texture.from_surface(self.renderer, scanlines(k, rect)) if self.crt else None)
        return self.frame_cache[1:]

    def toggle_full(self):
        self.full = not self.full
        if self.full:
            self.window.set_fullscreen(desktop=True)
        else:
            self.window.set_windowed()
        self.frame_cache = None

    def handle(self, e):
        if e.type == pygame.QUIT:
            return False
        if e.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self.controls.refresh()
        if e.type == pygame.KEYDOWN:
            alt_enter = e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT
            if e.key == pygame.K_F11 or alt_enter:
                self.toggle_full()
            elif e.key == pygame.K_F2:
                self.crt = not self.crt
            elif e.key == pygame.K_F3:
                self.game.free_play = not self.game.free_play
            elif e.key == pygame.K_ESCAPE:
                g = self.game
                if g.mode == "play" and g.paused:
                    g.to_title()
                elif g.mode == "play":
                    g.toggle_pause()
                elif g.mode in ("title", "scores", "demo"):
                    return False
            elif e.key == pygame.K_RETURN and self.game.paused:
                self.game.toggle_pause()
        return True

    def run(self):
        clock = pygame.time.Clock()
        acc = 0.0
        running = True
        limit = int(os.environ.get("IRONVOLT_FRAMES", "0"))    # the local smoke test quits by itself
        shown = 0
        while running and not (limit and shown >= limit):
            acc += min(clock.tick() / 1000, MAX_DT)
            events = pygame.event.get()
            for e in events:
                running = self.handle(e) and running
            stepped = False
            while acc >= STEP:
                self.controls.read(events)
                events = ()                                  # a coin or button event counts once
                self.game.step(self.controls)
                acc -= STEP
                stepped = True
            if stepped:
                self.game.draw(self.screen)
                self.tex.update(self.screen)
            k, rect, frame, lines = self.layout()
            self.renderer.clear()
            frame.draw()
            self.tex.draw(dstrect=rect)
            if lines:
                lines.draw(dstrect=rect)
            self.renderer.present()
            shown += 1
        pygame.quit()


def main():
    App().run()
    sys.exit(0)
