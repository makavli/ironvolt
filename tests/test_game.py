"""Headless tests: physics, combat, flow, storage, scaling, and a bot that finishes the stage."""

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

from ironvolt import storage  # noqa: E402
from ironvolt.actors import Foe, Hostage, Pickup  # noqa: E402
from ironvolt.app import integer_fit  # noqa: E402
from ironvolt.art import Atlas  # noqa: E402
from ironvolt.autopilot import BotPad  # noqa: E402
from ironvolt.controls import BUTTONS  # noqa: E402
from ironvolt.game import Game  # noqa: E402
from ironvolt.settings import GROUND_Y, H, TILE, W  # noqa: E402
from ironvolt.stage import WALK  # noqa: E402
from ironvolt.world import World  # noqa: E402

ATLAS = Atlas()


class Pad:
    """A scripted pad: set .now each frame."""

    def __init__(self):
        self.now = dict.fromkeys(BUTTONS, False)
        self.before = dict(self.now)

    def press(self, **held):
        self.before = self.now
        self.now = dict.fromkeys(BUTTONS, False)
        self.now.update(held)

    held = lambda self, b: self.now[b]
    pressed = lambda self, b: self.now[b] and not self.before[b]
    axis = lambda self: (self.now["right"] - self.now["left"], self.now["down"] - self.now["up"])


def run(world, pads, frames, **held):
    for _ in range(frames):
        pads[0].press(**held)
        world.step(pads)


class Physics(unittest.TestCase):
    def setUp(self):
        self.w = World((0,), seed=1)
        self.pads = [Pad(), Pad()]
        self.p = self.w.players[0]

    def test_stands_on_the_floor(self):
        run(self.w, self.pads, 30)
        self.assertTrue(self.p.on_ground)
        self.assertEqual(self.p.y, GROUND_Y)

    def test_jump_height_and_short_hop(self):
        self.pads[0].press()
        run(self.w, self.pads, 5)
        self.pads[0].press(jump=True)
        self.w.step(self.pads)
        top = self.p.y
        for _ in range(40):
            self.pads[0].press(jump=True)
            self.w.step(self.pads)
            top = min(top, self.p.y)
        full = GROUND_Y - top
        run(self.w, self.pads, 40)
        self.pads[0].press(jump=True)
        self.w.step(self.pads)
        top = self.p.y
        for _ in range(40):
            self.pads[0].press()                      # let go at once: a short hop
            self.w.step(self.pads)
            top = min(top, self.p.y)
        hop = GROUND_Y - top
        self.assertGreater(full, 50)
        self.assertLess(hop, full * 0.5)

    def test_buffered_jump_fires_on_landing(self):
        self.p.y, self.p.vy, self.p.on_ground = GROUND_Y - 6, 2.0, False
        self.pads[0].press(jump=True)                 # pressed just before touching down
        self.w.step(self.pads)
        run(self.w, self.pads, 4, jump=True)
        self.assertLess(self.p.vy, 0, "the early press should still jump")

    def test_coyote_jump_after_leaving_a_ledge(self):
        p = self.p
        p.x, p.y = 42 * TILE + 4, GROUND_Y        # 2 px of boot still on the lip of the first pit
        self.w.cam_x = p.x - 100
        run(self.w, self.pads, 1)
        run(self.w, self.pads, 4, right=True)
        self.assertFalse(p.on_ground)
        self.pads[0].press(right=True, jump=True)
        self.w.step(self.pads)
        self.assertLess(p.vy, 0, "a jump a few frames after the ledge still counts")

    def test_walls_stop_you(self):
        p = self.p
        p.x = 13 * TILE                              # left of the crate at column 14
        self.w.cam_x = 0
        run(self.w, self.pads, 60, right=True)
        self.assertLessEqual(p.x + p.w / 2, 14 * TILE + 0.01)

    def test_catwalk_is_one_way(self):
        st = self.w.stage
        tx = 33
        self.assertEqual(st.tile(tx, 7), WALK)
        p = self.p
        p.x, p.y = tx * TILE + 8, 7 * TILE + 40
        p.vy, p.on_ground = -5.0, False               # rising from below: passes through
        self.w.cam_x = p.x - 100
        for _ in range(40):
            self.pads[0].press(jump=True)
            p.step(self.pads[0], self.w)
            if p.vy >= 0:
                break
        self.assertLess(p.y, 7 * TILE + 1)
        run(self.w, self.pads, 60)
        self.assertEqual(p.y, 7 * TILE)               # and then stands on it
        self.pads[0].press(down=True, jump=True)      # down + jump drops through
        self.w.step(self.pads)
        run(self.w, self.pads, 30)
        self.assertGreater(p.y, 7 * TILE)


class Combat(unittest.TestCase):
    def setUp(self):
        self.w = World((0,), seed=2)
        self.pads = [Pad(), Pad()]
        self.p = self.w.players[0]
        run(self.w, self.pads, 10)

    def test_shots_kill_a_soldier_and_score(self):
        foe = Foe(self.p.x + 60, GROUND_Y)
        foe.timer = 10_000
        self.w.foes.append(foe)
        for i in range(60):
            self.pads[0].press(fire=i % 2 == 0)
            self.w.step(self.pads)
        self.assertTrue(foe.dying or foe.dead)
        self.assertEqual(self.p.score, 100)

    def test_hostage_gives_a_weapon(self):
        h = Hostage(self.p.x + 20, GROUND_Y, "H")
        self.w.hostages.append(h)
        run(self.w, self.pads, 60, right=True)
        self.assertTrue(h.freed)
        self.assertEqual(self.w.hostages_freed, 1)
        run(self.w, self.pads, 60, right=True)
        self.assertEqual(self.p.weapon, "H")

    def test_heavy_gun_runs_dry(self):
        Pickup(0, 0, "H").apply(self.p)
        self.p.ammo = 3
        run(self.w, self.pads, 30, fire=True)
        self.assertEqual(self.p.weapon, "P")

    def test_a_hit_costs_a_life(self):
        self.p.safe = 0
        lives = self.p.lives
        self.w.kill_player(self.p)
        run(self.w, self.pads, 120)
        self.assertEqual(self.p.lives, lives - 1)
        self.assertFalse(self.p.out)


class Stage(unittest.TestCase):
    def test_the_bot_finishes_the_stage(self):
        w = World((0,), seed=1, god=True)
        bots = [BotPad(), BotPad()]
        for _ in range(20000):
            bots[0].think(w, w.players[0])
            w.step(bots)
            if w.cleared:
                break
        self.assertTrue(w.cleared, "stage not finished; camera at %d" % w.cam_x)

    def test_every_pit_is_jumpable(self):
        st = World((0,)).stage
        run_len = 0
        for c in range(len(st.grid[0])):
            if st.tile(c, 11) == 0:
                run_len += 1
            else:
                self.assertLessEqual(run_len, 3, "pit ending at column %d" % c)
                run_len = 0


class Flow(unittest.TestCase):
    def test_every_scene_draws(self):
        g = Game(ATLAS)
        s = pygame.Surface((W, H))
        for mode in ("title", "scores"):
            g.mode = mode
            g.draw(s)
        g.start([0, 1])
        g.draw(s)
        g.paused = True
        g.draw(s)
        self.assertGreater(len({tuple(s.get_at((x, 100))) for x in range(0, W, 8)}), 3)

    def test_integer_scaling(self):
        self.assertEqual(integer_fit((3440, 1440))[0], 6)
        self.assertEqual(integer_fit((1920, 1080))[0], 4)
        k, r = integer_fit((1000, 700))
        self.assertEqual((k, r.size), (3, (960, 672)))
        self.assertEqual(r.topleft, (20, 14))


class Storage(unittest.TestCase):
    def test_scores_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["IRONVOLT_HOME"] = d
            try:
                t = storage.load()
                self.assertTrue(storage.qualifies(t, 999999))
                storage.insert(t, "ZZZ", 999999)
                self.assertEqual(storage.load()[0], ["ZZZ", 999999])
                with open(storage.path(), "w") as f:
                    f.write("{broken")
                self.assertEqual(storage.load(), storage.DEFAULT)
            finally:
                del os.environ["IRONVOLT_HOME"]


if __name__ == "__main__":
    unittest.main()
