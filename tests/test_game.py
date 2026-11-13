"""Headless tests: physics, combat, flow, storage, scaling, and a bot that finishes the stage."""

import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

from ironvolt import storage  # noqa: E402
from ironvolt.actors import Foe, Hostage, Pickup  # noqa: E402
from ironvolt.app import integer_fit, pace  # noqa: E402
from ironvolt.art import Atlas  # noqa: E402
from ironvolt.autopilot import BotPad  # noqa: E402
from ironvolt.controls import BUTTONS  # noqa: E402
from ironvolt.game import Game  # noqa: E402
from ironvolt.settings import GROUND_Y, H, MAX_FALL, RUN, STEP, TILE, W  # noqa: E402
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
        p.vy, p.on_ground = -6.5, False               # rising from below: passes through
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

    def test_a_held_jump_clears_the_slabs_and_falls_faster_than_it_rises(self):
        run(self.w, self.pads, 5)
        ys = []
        while not ys or not self.p.on_ground:
            self.pads[0].press(jump=True)
            self.w.step(self.pads)
            ys.append(self.p.y)
        up = ys.index(min(ys)) + 1
        self.assertGreater(GROUND_Y - min(ys), 3 * TILE + 8)      # the stage's slabs are 3 tiles high
        self.assertLess(len(ys) - up, up)

    def test_a_fall_at_full_speed_still_lands_on_a_catwalk(self):
        p = self.p
        p.x, p.y, p.vy, p.on_ground = 33 * TILE + 8.0, 7 * TILE - 61.0, MAX_FALL, False
        self.w.cam_x = p.x - 100
        run(self.w, self.pads, 30)
        self.assertEqual(p.y, 7 * TILE)

    def test_a_toe_on_the_ledge_makes_the_jump(self):
        p = self.p
        for under, makes_it in ((3, True), (7, False)):           # px from the feet up to the crate's top
            p.x, p.y, p.vx, p.vy, p.on_ground = 14 * TILE - 6.0, 10 * TILE + under, RUN, 1.0, False
            run(self.w, self.pads, 6, right=True)
            self.assertEqual(p.on_ground and p.y == 10 * TILE, makes_it)

    def test_down_and_jump_drops_from_the_very_end_of_a_catwalk(self):
        p = self.p
        p.x, p.y = 32 * TILE - 3.0, 7 * TILE          # two pixels of boot on the catwalk, the rest over air
        self.w.cam_x = p.x - 100
        run(self.w, self.pads, 2)
        self.assertEqual(p.y, 7 * TILE)
        self.pads[0].press(down=True, jump=True)
        self.w.step(self.pads)
        run(self.w, self.pads, 5, down=True, jump=True)
        self.assertGreater(p.y, 7 * TILE + 8)         # a plain fall, button held or not: the float is for jumps

    def test_the_screen_edge_never_shoves_a_player_into_a_wall(self):
        w, pads = World((0, 1), seed=5), [Pad(), Pad()]
        run(w, pads, 5)
        lead, tail = w.players
        tail.x = 14 * TILE - tail.w / 2               # against the crate
        lead.x = tail.x + 271                         # far ahead, pulling the screen along
        run(w, pads, 30)
        self.assertEqual(tail.x, 14 * TILE - tail.w / 2)
        self.assertLessEqual(w.cam_x, tail.x - 6)


class Feel(unittest.TestCase):
    """What the hands and eyes are promised: no swallowed press, fair hits, room to dodge, even motion."""

    def setUp(self):
        self.w = World((0,), seed=3)
        self.pads = [Pad(), Pad()]
        self.p = self.w.players[0]
        run(self.w, self.pads, 10)

    def test_running_starts_stops_and_turns_in_a_few_frames(self):
        p = self.p
        run(self.w, self.pads, 3, right=True)
        self.assertEqual(p.vx, RUN)
        run(self.w, self.pads, 4, left=True)
        self.assertEqual(p.vx, -RUN)
        run(self.w, self.pads, 3)
        self.assertEqual(p.vx, 0)

    def test_a_tap_between_shots_is_not_swallowed(self):
        self.pads[0].press(fire=True)
        self.w.step(self.pads)                        # a shot: the pistol now waits
        run(self.w, self.pads, 1)
        self.pads[0].press(fire=True)
        self.w.step(self.pads)                        # tapped again, too early...
        self.assertEqual(len(self.w.shots), 1)
        run(self.w, self.pads, 4)
        self.assertEqual(len(self.w.shots), 2, "...it fires as soon as the gun allows")

    def test_a_press_during_a_hit_stop_still_counts(self):
        self.w.hitstop(3)
        self.pads[0].press(jump=True)
        self.w.step(self.pads)                        # pressed while the action is held
        run(self.w, self.pads, 3, jump=True)
        self.assertLess(self.p.vy, 0)

    def test_a_crouch_ducks_rifle_fire(self):
        for crouch in (True, False):
            w, pads = World((0,), seed=4), [Pad(), Pad()]
            p = w.players[0]
            run(w, pads, 5)
            p.safe = 0
            foe = Foe(p.x + 90, GROUND_Y)
            foe.timer = 1
            w.foes.append(foe)
            run(w, pads, 150, down=crouch)
            self.assertEqual(p.lives == 3 and not p.dying, crouch)

    def test_a_hit_staggers_a_soldier_out_of_its_shot(self):
        foe = Foe(self.p.x + 60, GROUND_Y)
        foe.timer = 1
        self.w.foes.append(foe)
        run(self.w, self.pads, 5)
        self.assertTrue(foe.aiming)
        x = foe.x
        foe.damage(1, self.w, self.p, push=1)
        run(self.w, self.pads, 30)
        self.assertGreater(foe.x, x)                  # knocked back...
        self.assertFalse(self.w.bolts)                # ...and the shot it was winding up never comes

    def test_a_grenade_bursts_on_the_first_soldier_it_touches(self):
        foe = Foe(self.p.x + 90, GROUND_Y)
        foe.timer = 10_000
        self.w.foes.append(foe)
        self.pads[0].press(bomb=True)
        self.w.step(self.pads)
        run(self.w, self.pads, 40)                    # well before its fuse (75 frames) or its third bounce
        self.assertTrue(foe.dying or foe.dead)

    def test_a_respawn_never_drops_into_a_pit(self):
        p, w = self.p, self.w
        w.spawn_i = len(w.stage.spawns)               # nobody else around
        p.x, w.cam_x = 43 * TILE + 100.0, 43 * TILE - 40.0     # 40 px into the screen, the old drop point, is a pit
        p.safe = 0
        w.kill_player(p)
        run(w, self.pads, 200)
        self.assertEqual(p.lives, 2)
        self.assertTrue(p.on_ground)

    def test_the_boss_leaves_room_and_lands_one_blast_at_a_time(self):
        w, pads = World((0,), seed=6, god=True), [Pad(), Pad()]
        w.spawn_i = len(w.stage.spawns)               # the boss alone
        w.players[0].x = w.stage.boss_x + 40.0
        w.cam_x = float(w.stage.boss_x)
        room, landed = W, {"shell": [], "missile": []}
        for _ in range(1500):
            flying = list(w.bolts)
            run(w, pads, 1)
            if w.boss.state == "fight":
                w.boss.hp = min(w.boss.hp, w.boss.HP // 2)        # straight to the angry phase
                room = min(room, w.boss.hitbox().left - w.cam_x)
            for b in flying:
                if b.dead and b.kind in landed:
                    landed[b.kind].append(w.frame)
        self.assertGreaterEqual(room, 80)
        self.assertTrue(landed["shell"] and landed["missile"])
        self.assertGreaterEqual(min(abs(a - b) for a in landed["shell"] for b in landed["missile"]), 30)

    def test_the_pad_is_told_of_a_shot_a_landing_and_a_death(self):
        p, w, felt = self.p, self.w, []
        p.y, p.on_ground, p.safe = GROUND_Y - 8.0, False, 0
        for i in range(8):
            self.pads[0].press(fire=i == 0)
            w.step(self.pads)
            felt += w.felt
        self.assertEqual(felt, [(0, "shot"), (0, "land")])
        w.kill_player(p)
        self.assertIn((0, "hurt"), w.felt)

    def test_drawing_blends_between_steps_and_changes_nothing(self):
        w, p = self.w, self.p
        run(w, self.pads, 8, right=True)
        state = (p.x, p.y, w.cam_x, random.getstate())
        seen = []
        p.draw = lambda surf, atlas, cam: seen.append(p.x)
        w.blend = 0.5
        w.draw(pygame.Surface((W, H)), ATLAS)
        self.assertAlmostEqual(seen[0], (p.ox + state[0]) / 2)
        self.assertEqual((p.x, p.y, w.cam_x, random.getstate()), state)


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

    def test_motion_is_even_at_any_refresh_rate(self):
        for hz in (60, 75, 144, 164, 240):
            acc, steps, seen = 0.0, 0, []
            for _ in range(500):
                n, acc = pace(acc, 1 / hz)
                steps += n
                seen.append((steps - 1 + acc / STEP) * 1.5)       # where a 1.5 px/frame scroll is painted
            gaps = [b - a for a, b in zip(seen, seen[1:])]
            self.assertAlmostEqual(min(gaps), max(gaps), places=6, msg="%d Hz" % hz)
            self.assertAlmostEqual(gaps[0], 1.5 * 60 / hz, places=6)


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
                for bad in ("[]", '[["A", Infinity]]', "[" * 100000):
                    with open(storage.path(), "w") as f:
                        f.write(bad)
                    self.assertEqual(storage.load(), storage.DEFAULT)
            finally:
                del os.environ["IRONVOLT_HOME"]



class Rumble(unittest.TestCase):
    def test_weak_buzz_does_not_cut_a_boom(self):
        from ironvolt.controls import Controls

        class Dev:
            def __init__(self):
                self.calls = []

            def rumble(self, *a):
                self.calls.append(a)

        c = Controls.__new__(Controls)
        c.devices, c.rumble_on = [Dev()], True
        c.feel(0, "big_boom")
        c.feel(0, "shot")
        self.assertEqual(len(c.devices[0].calls), 1)
        c.feel(0, "hurt")          # 1.6 < 1.9: the boom still wins
        self.assertEqual(len(c.devices[0].calls), 1)

if __name__ == "__main__":
    unittest.main()
