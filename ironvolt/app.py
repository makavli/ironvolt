"""The window and the loop.

The game draws into a 320x224 surface. The GPU scales it by the largest whole number that fits (sharp pixels,
no shimmer; or, with the FIT option, as large as the window allows), centres it, frames it with a cabinet bezel, and lays optional scanlines over it. Logic steps at a
fixed 60 Hz; every refresh of the screen paints the blend of the last two steps, so motion is even at any rate.
In a browser (pygbag) there is no GPU renderer: the same picture is scaled on the CPU into the page's canvas, and
the loop hands the browser back control once per frame.
"""

import os
import sys
import time

import pygame

from . import __version__, audio, font
from .art import Atlas
from .controls import Controls
from .game import Game
from .settings import C, H, MAX_DT, STEP, W

WEB = sys.platform == "emscripten"
WEB_SCALE = 3                                     # the canvas is 960x672; the page fits it to the browser window
# In the browser, a lifted finger asks for fullscreen, then landscape. Only touchend counts as a user gesture (touchstart
# does not), so it is a page listener, not the game's finger events. iPhone Safari has neither (iPad and Android do).
FULL_JS = ("document.addEventListener('touchend',()=>{const d=document.documentElement;"
           "if(document.fullscreenElement||!d.requestFullscreen)return;"
           "d.requestFullscreen({navigationUI:'hide'})"
           ".then(()=>screen.orientation&&screen.orientation.lock&&screen.orientation.lock('landscape'))"
           ".catch(e=>console.log('fullscreen: '+e));},true)")


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


def fit(window, whole=True, game=(W, H)):
    """The scale and centred rectangle for the game: whole steps (pixel perfect), or as big as fits (FIT)."""
    if whole:
        return integer_fit(window, game)
    s = min(window[0] / game[0], window[1] / game[1])
    gw, gh = max(1, round(game[0] * s)), max(1, round(game[1] * s))
    return max(1, int(s)), pygame.Rect((window[0] - gw) // 2, (window[1] - gh) // 2, gw, gh)


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


def scanlines(rect, rows=H):
    """A dark line under every scaled pixel row (only when pixels are big enough for it to read as CRT)."""
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    if rect.height >= 3 * rows:
        for row in range(rows):
            y = (row + 1) * rect.height // rows - 1
            pygame.draw.line(s, (0, 0, 0, 70), (0, y), (rect.width, y))
    return s


class App:
    def __init__(self):
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "0")      # nearest: crisp pixels
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")   # real pixels at 125%, 150%...
        pygame.init()
        audio.init()
        self.screen = pygame.Surface((W, H))
        self.atlas = Atlas()
        if WEB:
            self.canvas = pygame.display.set_mode((W * WEB_SCALE, H * WEB_SCALE))
            self.texture = lambda surf: surf             # the browser path draws surfaces as they are
            try:
                import platform
                platform.window.eval(FULL_JS)
            except Exception as err:                     # a JS proxy raises its own error types
                print("fullscreen:", err)
        else:
            from pygame._sdl2.video import Renderer, Texture
            desk = pygame.display.get_desktop_sizes()[0]
            k, _ = integer_fit((desk[0] - 80, desk[1] - 120))
            self.window = pygame.Window("IRONVOLT " + __version__, (W * k, H * k), resizable=True)
            self.window.minimum_size = (W, H)
            self.renderer = Renderer(self.window, vsync=True)
            self.texture = lambda surf: Texture.from_surface(self.renderer, surf)
            self.tex = self.texture(self.screen)
            self.window.set_icon(self.atlas.players[0]["stand"])
        self.game = Game(self.atlas)
        self.controls = Controls()
        self.game.controls = self.controls              # the prompts follow the device in use
        self.full = False
        self.speed = 1.0
        self.frame_cache = None
        self.game.on_option = self.option
        self.controls.touch.to_game = self.touch_map
        self.portrait = False
        for key in ("fullscreen", "music", "sfx", "rumble", "swap", "speed"):
            self.option(key)

    def option(self, key):
        """The options the app applies, as soon as they change."""
        o = self.game.opts
        if key == "fullscreen" and (o["fullscreen"] == "ON") != self.full:
            self.toggle_full()
        elif key in ("crt", "scale"):
            self.frame_cache = None
        elif key in ("music", "sfx"):
            audio.set_volume(int(o["music"]) / 10, int(o["sfx"]) / 10)
        elif key == "rumble":
            self.controls.rumble_on = o["rumble"] == "ON"
        elif key == "swap":
            self.controls.swap = o["swap"] == "ON"
        elif key == "speed":
            self.speed = int(o["speed"].rstrip("%")) / 100      # slower logic for players who need it

    @property
    def crt(self):
        return self.game.opts["crt"] == "ON"

    def touch_map(self, nx, ny):
        """A finger's 0..1 position on the window or canvas -> game pixels."""
        size = self.canvas.get_size() if WEB else self.window.size
        rect = self.layout()[1]
        return (nx * size[0] - rect.x) * W / rect.w, (ny * size[1] - rect.y) * H / rect.h

    def turned(self):
        """In a browser held upright, the game is a strip: ask for landscape."""
        if WEB and self.shown % 30 == 0:
            try:
                import platform
                self.portrait = platform.window.innerHeight > platform.window.innerWidth
            except Exception:                    # a JS proxy raises its own error types
                self.portrait = False
        if self.portrait and self.controls.touch.used:
            self.screen.fill(C["black"], (0, 96, W, 30))
            font.draw(self.screen, "TURN YOUR PHONE SIDEWAYS", (W // 2, 107), C["sun"], center=True)

    def layout(self):
        size = self.canvas.get_size() if WEB else self.window.size
        whole = self.game.opts["scale"] == "PIXEL PERFECT"
        key = (size, self.crt, whole)
        if self.frame_cache is None or self.frame_cache[0] != key:
            k, rect = fit(size, whole)
            self.frame_cache = (key, k, rect, self.texture(bezel(size, rect)),
                                self.texture(scanlines(rect)) if self.crt else None)
        return self.frame_cache[1:]

    def toggle_full(self):
        if WEB:
            return                                # the page's own fullscreen button does it
        self.full = not self.full
        if self.game.opts["fullscreen"] != ("ON" if self.full else "OFF"):
            self.game.set_option("fullscreen", "ON" if self.full else "OFF")
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
                self.game.set_option("crt", "OFF" if self.crt else "ON")
            elif e.key == pygame.K_F3:
                self.game.set_option("free_play", "OFF" if self.game.free_play else "ON")
            elif e.key == pygame.K_ESCAPE:
                return self.game.back()
        return True

    def start(self):
        self.clock = pygame.time.Clock()
        self.last = time.perf_counter()            # pygame's clock counts whole milliseconds: too coarse to blend by
        self.acc = 0.0
        self.moving = False                        # did the world step on the latest tick?
        self.waiting = []                          # events no step has read yet: a fast screen refreshes between steps
        self.running = True
        self.limit = int(os.environ.get("IRONVOLT_FRAMES", "0"))    # the local smoke test quits by itself
        self.shown = 0

    def frame(self):
        """One screen refresh: due logic steps, then the picture. Returns False once the game should end."""
        if not WEB:
            self.clock.tick(400)                   # a brake, for a driver that ignores vsync
        now = time.perf_counter()
        steps, self.acc = pace(self.acc, (now - self.last) * self.speed)
        self.last = now
        for e in pygame.event.get():
            self.running = self.handle(e) and self.running
            self.waiting.append(e)
        for _ in range(steps):
            self.controls.read(self.waiting)
            self.waiting = []                                # a coin event counts once, and none is dropped
            world = self.game.world or self.game.demo
            seen = world and world.frame
            self.game.step(self.controls)
            self.moving = bool(world) and world.frame != seen
            if self.moving and world is self.game.world:     # a played world shakes the pads; the demo does not
                for i, moment in world.felt:
                    self.controls.feel(i, moment)
        world = self.game.world or self.game.demo
        if world:                                  # a world that did not step (pause, game over) holds its picture
            world.blend = self.acc / STEP if self.moving else 1.0
        self.game.draw(self.screen)
        self.controls.touch.draw(self.screen)
        self.turned()
        self.present()
        audio.tick()
        self.shown += 1
        return self.running and not self.game.quit and not (self.limit and self.shown >= self.limit)

    def present(self):
        k, rect, frame, lines = self.layout()
        if WEB:
            self.canvas.blit(frame, (0, 0))
            self.canvas.blit(pygame.transform.scale(self.screen, rect.size), rect)
            if lines:
                self.canvas.blit(lines, rect)
            pygame.display.flip()
            return
        self.tex.update(self.screen)
        self.renderer.clear()
        frame.draw()
        self.tex.draw(dstrect=rect)
        if lines:
            lines.draw(dstrect=rect)
        self.renderer.present()

    def run(self):
        self.start()
        while self.frame():
            pass
        self.controls.close()
        pygame.quit()

    async def run_web(self):
        import asyncio
        self.start()
        while self.frame():
            await asyncio.sleep(0)                 # the browser paints the canvas and runs its events here


def main():
    App().run()
    sys.exit(0)
