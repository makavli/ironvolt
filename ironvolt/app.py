"""The window and the loop.

The game draws into a 320x224 surface. The GPU scales it by the largest whole number that fits (sharp pixels,
no shimmer), centres it, frames it with a cabinet bezel, and lays optional scanlines over it. Logic steps at a
fixed 60 Hz; every refresh of the screen paints the blend of the last two steps, so motion is even at any rate.
"""

import os
import sys
import time

import pygame

from . import __version__, audio
from .art import Atlas
from .controls import Controls
from .game import Game
from .settings import C, H, MAX_DT, STEP, W


def pace(acc, dt):
    """Banks one screen refresh's time. Returns (logic steps now due, time left over): the rest is the blend."""
    acc += min(dt, MAX_DT)
    steps = int(acc / STEP)
    return steps, max(0.0, acc - steps * STEP)


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
        self.game.controls = self.controls              # the prompts follow the device in use
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
        self.controls.handle(e)                             # pads plugged in or pulled out
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
        last = time.perf_counter()                 # pygame's clock counts whole milliseconds: too coarse to blend by
        acc = 0.0
        moving = False                             # did the world step on the latest tick?
        waiting = []                               # events no step has read yet: a fast screen refreshes between steps
        running = True
        limit = int(os.environ.get("IRONVOLT_FRAMES", "0"))    # the local smoke test quits by itself
        shown = 0
        while running and not (limit and shown >= limit):
            clock.tick(400)                        # a brake, for a driver that ignores vsync
            now = time.perf_counter()
            steps, acc = pace(acc, now - last)
            last = now
            for e in pygame.event.get():
                running = self.handle(e) and running
                waiting.append(e)
            for _ in range(steps):
                self.controls.read(waiting)
                waiting = []                                 # a coin event counts once, and none is dropped
                world = self.game.world or self.game.demo
                seen = world and world.frame
                self.game.step(self.controls)
                moving = bool(world) and world.frame != seen
                if moving and world is self.game.world:      # a played world shakes the pads; the demo does not
                    for i, moment in world.felt:
                        self.controls.feel(i, moment)
            world = self.game.world or self.game.demo
            if world:                              # a world that did not step (pause, game over) holds its picture
                world.blend = acc / STEP if moving else 1.0
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
        self.controls.close()
        pygame.quit()


def main():
    App().run()
    sys.exit(0)
