"""Headless tests: physics, combat, flow, storage, scaling, and a bot that finishes the stage."""

import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HOME = tempfile.mkdtemp()
os.environ["IRONVOLT_HOME"] = HOME                 # never the player's own scores and options

import pygame  # noqa: E402

pygame.init()

from ironvolt import storage  # noqa: E402
from ironvolt.actors import SAPPER_FUSE, Bolt, Foe, Graive, Harrow, Hostage, Pickup, Shot, Warden  # noqa: E402
from ironvolt.app import fit, integer_fit, pace, scanlines  # noqa: E402
from ironvolt.art import Atlas  # noqa: E402
from ironvolt.autopilot import BotPad  # noqa: E402
from ironvolt.controls import BUTTONS  # noqa: E402
from ironvolt.game import Game  # noqa: E402
from ironvolt.settings import GROUND_Y, H, MAX_FALL, RUN, STEP, TILE, W  # noqa: E402
from ironvolt.stage import MISSIONS, WALK  # noqa: E402
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

    def test_fire_up_close_is_a_knife(self):
        run(self.w, self.pads, 5)
        foe = Foe(self.p.x + 12, GROUND_Y)
        foe.timer = 10_000
        self.w.foes.append(foe)
        self.pads[0].press(fire=True)
        self.w.step(self.pads)
        self.assertTrue(foe.dying)                    # one stab downs a trooper...
        self.assertFalse(self.w.shots)                # ...and no bullet left the gun
        self.assertEqual(self.p.score, 100)

    def test_down_and_jump_on_the_ground_slides_low_and_fast(self):
        run(self.w, self.pads, 30, right=True)
        x = self.p.x
        self.pads[0].press(down=True, jump=True)
        self.w.step(self.pads)
        run(self.w, self.pads, 15)
        self.assertGreater(self.p.x - x, 16 * RUN)    # farther than 16 frames of running
        self.assertEqual(self.p.h, 12)                # low enough to pass under rifle fire
        run(self.w, self.pads, 30)
        self.assertFalse(self.p.slide)
        self.assertEqual(self.p.h, 21)

    def test_landing_on_a_head_stomps_and_bounces(self):
        run(self.w, self.pads, 5)
        foe = Foe(self.p.x + 30, GROUND_Y)
        foe.timer, foe.hp = 10_000, 2
        self.w.foes.append(foe)
        self.p.x, self.p.y, self.p.vy = foe.x, GROUND_Y - 40, 0.0
        self.p.on_ground, self.p.coyote = False, 0           # dropped from above, not standing
        bounced = False
        for _ in range(30):
            self.pads[0].press(jump=True)
            self.w.step(self.pads)
            bounced = bounced or (foe.dying and self.p.vy < 0)
        self.assertTrue(bounced)

    def test_every_hostage_appears_ahead_of_the_player(self):
        for m in MISSIONS:
            for cam, kind, x, _ in m.spawns:
                if kind == "hostage":
                    self.assertGreater(x - cam, 200, x)  # the player runs ~130 px into the screen

    def test_the_first_hostage_is_reached_on_foot(self):
        self.p.god = True
        for i in range(600):
            self.pads[0].press(right=True, jump=i % 40 < 20)    # hops the crates on the way
            self.w.step(self.pads)
            if any(h.freed for h in self.w.hostages):
                break
        self.assertTrue(any(h.freed for h in self.w.hostages))

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

    def test_kill_chain_multiplies_then_expires(self):
        from ironvolt.settings import CHAIN_FRAMES
        for _ in range(3):
            self.w.award(self.p, 100, 0, 0)
        self.assertEqual((self.p.score, self.p.chain), (100 + 200 + 300, 3))
        self.w.award(self.p, 1000, 0, 0, "THANK YOU!")        # a rescue scores plain and keeps the chain
        self.assertEqual((self.p.score, self.p.chain), (1600, 3))
        run(self.w, self.pads, CHAIN_FRAMES + 5)
        self.assertEqual(self.p.chain, 0)
        for _ in range(12):
            self.w.award(self.p, 10, 0, 0)
        self.assertEqual(self.p.score, 1600 + 10 * (1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 * 5))   # capped at x8

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
    def test_the_bot_finishes_every_mission(self):
        for i, m in enumerate(MISSIONS):
            w = World((0,), seed=1, god=True, stage=i)
            bots = [BotPad(), BotPad()]
            for _ in range(20000):
                bots[0].think(w, w.players[0])
                w.step(bots)
                if w.cleared:
                    break
            self.assertTrue(w.cleared, "%s not finished; camera at %d" % (m.name, w.cam_x))

    def test_every_pit_is_jumpable(self):
        for i in range(len(MISSIONS)):
            st = World((0,), stage=i).stage
            run_len = 0
            for c in range(len(st.grid[0])):
                if st.tile(c, 11) == 0:
                    run_len += 1
                else:
                    self.assertLessEqual(run_len, 3, "pit ending at column %d" % c)
                    run_len = 0


class Missions(unittest.TestCase):
    def test_a_riot_shield_stops_shots_at_its_face_only(self):
        w = World((0,), seed=2)
        w.spawn_i = len(w.stage.spawns)
        foe = Foe(200.0, GROUND_Y, "shield")
        foe.facing, foe.aiming, foe.timer = -1, 0, 10 ** 6
        w.foes.append(foe)
        front = Shot(198.0, GROUND_Y - 12, 6.0, 0.0, 1, w.players[0], "bullet")
        self.assertTrue(foe.blocks(front))
        back = Shot(210.0, GROUND_Y - 12, -6.0, 0.0, 1, w.players[0], "bullet")
        self.assertFalse(foe.blocks(back))
        above = Shot(195.0, GROUND_Y - 20, 3.0, 4.0, 1, w.players[0], "bullet")
        self.assertFalse(foe.blocks(above))
        foe.aiming = 6                                   # it lowers the shield to fire
        self.assertFalse(foe.blocks(front))
        foe.aiming = 0
        w.shots.append(front)
        w.collide()
        self.assertEqual(foe.hp, 4)
        self.assertTrue(front.dead)

    def sapper_beside(self):
        w, pads = World((0,), seed=4), [Pad(), Pad()]
        w.spawn_i = len(w.stage.spawns)
        p = w.players[0]
        run(w, pads, 5)
        p.safe, p.facing = 0, 1
        foe = Foe(p.x + 12, GROUND_Y, "sapper")
        w.foes.append(foe)
        run(w, pads, 2)
        self.assertTrue(foe.fuse)                        # up close it lights the fuse instead of shooting
        return w, pads, p, foe

    def test_a_sapper_left_alone_blows_up_beside_you(self):
        w, pads, p, foe = self.sapper_beside()
        run(w, pads, SAPPER_FUSE + 2)
        self.assertTrue(p.dying)
        self.assertNotIn(foe, w.foes)

    def test_a_knife_stops_a_lit_sapper(self):
        w, pads, p, foe = self.sapper_beside()
        pads[0].press(fire=True)
        w.step(pads)
        self.assertTrue(foe.dying)
        self.assertFalse(w.shots)
        run(w, pads, SAPPER_FUSE + 2)
        self.assertFalse(p.dying)

    def test_the_gunship_flies_out_of_jumping_reach_over_open_road(self):
        self.assertLess(Harrow.FLY + 3, GROUND_Y - 58 - 21)          # bob included, a full jump's head stays under
        for i, m in enumerate(MISSIONS):
            if m.boss == "harrow":
                st = World((0,), stage=i).stage
                for c in range(m.boss_col, st.cols - 1):
                    self.assertFalse(any(st.tile(c, r) for r in range(11)), "something to stand on at %d" % c)

    def test_the_gunship_bombs_the_road_on_its_run(self):
        w = World((0,), seed=5)
        w.spawn_i = len(w.stage.spawns)
        w.cam_x, w.locked = 100.0, True
        w.boss = Harrow(w.cam_x + W - 90, GROUND_Y, w.cam_x, w.cam_x + W)
        w.boss.state, w.boss.mode = "fight", "run"
        w.players[0].x = w.cam_x + 40
        for _ in range(40):
            w.boss.step(w)
        self.assertTrue(any(b.kind == "shell" for b in w.bolts))

    def test_a_guard_fires_two_shots_at_once(self):
        w = World((0,), seed=6)
        foe = Foe(200.0, GROUND_Y, "guard")
        foe.fire(w, w.players[0])
        self.assertEqual(len(w.bolts), 2)

    def graive_fight(self):
        w = World((0,), seed=7)
        w.spawn_i = len(w.stage.spawns)
        w.cam_x, w.locked = 100.0, True
        w.boss = Graive(w.cam_x + W - 70, GROUND_Y, w.cam_x, w.cam_x + W)
        w.boss.state = "fight"
        w.players[0].x, w.players[0].safe = w.cam_x + 60, 0
        return w, w.boss

    def test_graive_leaps_where_you_stand_and_lands_a_shockwave_both_ways(self):
        w, g = self.graive_fight()
        g.mode, g.mt = "crouch", 27
        for _ in range(120):
            g.step(w)
            if g.mode == "land":
                break
        self.assertEqual(g.mode, "land")
        self.assertLess(abs(g.x - w.players[0].x), 4)
        waves = [b for b in w.bolts if b.kind == "wave"]
        self.assertEqual(sorted(b.vx > 0 for b in waves), [False, True])

    def test_graive_never_leaps_at_a_player_on_a_catwalk(self):
        w, g = self.graive_fight()
        w.players[0].y = 8 * TILE                        # standing on an arena catwalk
        g.mode, g.mt = "stride", 1000
        g.step(w)
        self.assertEqual(g.mode, "stride")

    def test_a_jump_clears_the_shockwave_and_standing_does_not(self):
        for jump in (False, True):
            w, g = self.graive_fight()
            p, pads = w.players[0], [Pad(), Pad()]
            run(w, pads, 30)
            w.boss = None
            w.bolts.append(Bolt(p.x + 40, GROUND_Y - 4, -2.2, 0, 0, "wave"))
            for f in range(60):
                run(w, pads, 1, jump=jump and 4 <= f < 30)
            self.assertEqual(bool(p.dying), not jump)

    def test_the_graive_arena_catwalks_are_above_the_rig(self):
        for i, m in enumerate(MISSIONS):
            if m.boss == "graive":
                st = World((0,), stage=i).stage
                rows = {r for c in range(m.boss_col, st.cols) for r in range(11) if st.tile(c, r) == WALK}
                self.assertTrue(rows)
                self.assertLessEqual(max(rows) * TILE, GROUND_Y - Graive.h - 1)

    def warden_charging(self, x, y):
        w, pads = World((0,), seed=3), [Pad(), Pad()]
        w.spawn_i = len(w.stage.spawns)
        w.cam_x, w.locked = 100.0, True
        w.boss = Warden(w.cam_x + W - 66, GROUND_Y, w.cam_x, w.cam_x + W)
        w.boss.state, w.boss.mode = "fight", "charge"
        p = w.players[0]
        p.x, p.y, p.safe, p.vy = w.cam_x + x, y, 0, 0.0
        for _ in range(120):
            run(w, pads, 1)
            if p.dying:
                break
        return w, p

    def test_the_warden_runs_down_whoever_stays_on_the_track(self):
        w, p = self.warden_charging(60, GROUND_Y)
        self.assertTrue(p.dying)

    def test_a_gantry_is_above_the_warden_roof(self):
        top = GROUND_Y - Warden.h
        for m in MISSIONS:
            if m.boss != "warden":
                continue
            st = World((0,), stage=MISSIONS.index(m)).stage
            arena = range(m.boss_col, st.cols)
            rows = {r for c in arena for r in range(11) if st.tile(c, r) == WALK}
            self.assertTrue(rows, "no gantry in the arena")
            self.assertTrue(all(r * TILE <= top - 4 for r in rows))    # feet on it clear the roof

    def test_the_next_mission_keeps_the_team(self):
        w = World((0, 1), seed=4)
        a, b = w.players
        a.score, a.lives, a.weapon, a.ammo = 12340, 1, "S", 30
        b.out, b.continue_t = True, 0
        nxt = w.advance()
        self.assertEqual(nxt.stage.index, 1)
        self.assertIs(nxt.players[0], a)
        self.assertEqual((a.score, a.lives, a.weapon), (12340, 1, "S"))
        self.assertGreater(b.continue_t, 0)              # a fresh chance to continue

    def test_the_tally_leads_to_the_next_mission_then_the_scores(self):
        g = Game(ATLAS)
        g.start([0])
        g.world.players[0].score = 0
        for i in range(1, len(MISSIONS)):
            g.mode, g.t = "clear", 1000
            g.step(Ctl())
            self.assertEqual((g.mode, g.world.stage.index), ("play", i))
        g.mode, g.t = "clear", 1000
        g.step(Ctl())
        self.assertIn(g.mode, ("entry", "scores"))

    def test_every_mission_draws(self):
        s = pygame.Surface((W, H))
        for i in range(len(MISSIONS)):
            w = World((0,), seed=5, stage=i)
            w.spawn_i = len(w.stage.spawns)
            w.players[0].x = w.stage.boss_x + 40.0
            w.cam_x = float(w.stage.boss_x)
            for _ in range(120):
                w.step([Pad(), Pad()])
            self.assertIsNotNone(w.boss)
            riot = Foe(w.cam_x + 60, GROUND_Y, "shield")
            w.foes.append(riot)
            w.draw(s, ATLAS)
            riot.aiming = 6                              # the shield lowered to fire
            w.draw(s, ATLAS)


class Flow(unittest.TestCase):
    def test_every_scene_draws(self):
        g = Game(ATLAS)
        s = pygame.Surface((W, H))
        for mode in ("title", "scores", "select"):
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

    def test_every_screen_shape_fits(self):
        shapes = [(320, 224), (640, 480), (800, 600), (1024, 768), (1280, 720), (1366, 768), (1440, 900),
                  (1920, 1080), (1920, 1200), (2560, 1080), (2560, 1440), (3440, 1440), (3840, 2160), (5120, 1440),
                  (1080, 1920), (1170, 2532), (2048, 1536), (500, 250), (321, 900), (2732, 2048)]
        for size in shapes:
            for whole in (True, False):
                k, r = fit(size, whole)
                msg = "%s %s" % (size, whole)
                self.assertTrue(pygame.Rect((0, 0), size).contains(r), msg)
                self.assertLessEqual(abs(r.centerx - size[0] / 2), 1, msg)
                self.assertLessEqual(abs(r.centery - size[1] / 2), 1, msg)
                if whole:
                    self.assertEqual(r.size, (W * k, H * k), msg)
                else:
                    self.assertAlmostEqual(r.width / r.height, W / H, delta=0.02, msg=msg)
                    self.assertTrue(r.width == size[0] or r.height == size[1], msg)     # fills one side
        self.assertEqual(fit((3440, 1440), False)[1].height, 1440)

    def test_scanlines_follow_the_pixel_rows(self):
        k, r = fit((1920, 1080))
        lines = scanlines(r)
        self.assertEqual(lines.get_at((5, k - 1)).a, 70)
        self.assertEqual(lines.get_at((5, 0)).a, 0)
        self.assertEqual(scanlines(pygame.Rect(0, 0, W * 2, H * 2)).get_at((5, 1)).a, 0)   # too small: none

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
                with open(storage.path(), "w") as f:
                    f.write('[["ss", 1e400], ["abcdef", -5], ["Q", 12345678901234567890]]')
                self.assertEqual(storage.load(), storage.DEFAULT)              # 1e400 is infinity: refused
                with open(storage.path(), "w") as f:
                    f.write('[["ss", 10], ["abcdef", -5], ["Q", 12345678901234567890]]')
                self.assertEqual(storage.load(), [["SS", 10], ["ABC", 0], ["Q", 9999999]])
                for bad in ("[]", '[["A", Infinity]]', "[" * 100000):
                    with open(storage.path(), "w") as f:
                        f.write(bad)
                    self.assertEqual(storage.load(), storage.DEFAULT)
            finally:
                os.environ["IRONVOLT_HOME"] = HOME

    def test_options_keep_only_known_values(self):
        o = storage.load_options()
        self.assertEqual((o["level"], o["music"], o["speed"]), ("NORMAL", "8", "100%"))
        storage.save_options(dict(o, music="3", crt="OFF"))
        self.assertEqual(storage.load_options()["music"], "3")
        for bad in ('{"music": "99", "evil": "x", "crt": 1}', "[1, 2]", "{broken", "[" * 100000):
            with open(storage.path("options.json"), "w") as f:
                f.write(bad)
            o = storage.load_options()
            self.assertEqual(o, storage.DEFAULTS)
        os.remove(storage.path("options.json"))



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


class BrowserPad(unittest.TestCase):
    def test_standard_order_start_dpad_and_buttons(self):
        from ironvolt.controls import _Device

        class Joy:                  # a browser pad: 17 buttons, 4 axes, no hat
            def __init__(self, *down):
                self.down = down

            def get_numaxes(self):
                return 4

            def get_axis(self, n):
                return 0.0

            def get_numhats(self):
                return 0

            def get_numbuttons(self):
                return 17

            def get_button(self, n):
                return n in self.down

        d = _Device.__new__(_Device)
        d.ctl, d.web, d.coin_was = None, True, False
        for down, want in (((9,), "start"), ((0,), "jump"), ((2,), "fire"), ((7,), "fire"), ((1,), "bomb"),
                           ((12,), "up"), ((15,), "right")):
            d.joy = Joy(*down)
            s, touched, _ = d.state()
            self.assertTrue(s[want] and touched, (down, want))
            self.assertEqual(sum(s.values()), 1, (down, s))
        d.joy = Joy(8)
        self.assertTrue(d.state()[2])          # BACK is the coin


class Music(unittest.TestCase):
    def test_song_never_clips(self):
        from ironvolt import music
        data = music.render("title")
        self.assertEqual(len(data) % 2, 0)                     # stereo, interleaved
        self.assertLess(max(map(abs, data)), 30000)
        self.assertGreater(max(map(abs, data[1::2])), 10000)    # the right side is not silent

    def test_every_lead_bar_is_sixteen_steps_of_real_notes(self):
        from ironvolt import music
        for name, (bpm, sections) in music.SONGS.items():
            for chords, style, lead in sections:
                self.assertIn(style, music.STYLES)
                for c in chords.split():
                    self.assertIn(c, music.CHORDS)
                if lead:
                    self.assertEqual(len(lead[0]), len(chords.split()), name)
                    for bar in lead[0]:
                        self.assertEqual(len(bar.split()), 16, bar)
                        for tok in bar.split():
                            if tok not in "-.":
                                music.midi(tok)


class Ctl:
    def __init__(self):
        self.pads, self.coin = [Pad(), Pad()], False

    def any_start(self):
        return [i for i, p in enumerate(self.pads) if p.pressed("start")]

    def tap(self, game, frames=1, **held):
        self.pads[0].press()                                    # let go first: two taps are two presses
        for _ in range(frames):
            self.pads[0].press(**held)
            game.step(self)
            held = {}


class Difficulty(unittest.TestCase):
    def test_chosen_before_play(self):
        g, c = Game(ATLAS), Ctl()
        c.tap(g, start=True)
        self.assertEqual(g.mode, "select")
        c.tap(g, down=True)
        c.tap(g, down=True)
        c.tap(g, down=True)                                     # past the end: stays on HARD
        self.assertEqual(g.level, "HARD")
        c.tap(g, 20)
        c.tap(g, fire=True)
        self.assertEqual(g.mode, "play")
        self.assertEqual((g.world.level, g.world.players[0].lives), ("HARD", 2))

    def test_too_feeble_offers_a_lower_level(self):
        g, c = Game(ATLAS), Ctl()
        g.start([0], "HARD")
        g.world.deaths = 3
        c.tap(g)
        self.assertEqual(g.feeble, 0)
        frame = g.world.frame
        c.tap(g, 50)
        self.assertEqual(g.world.frame, frame)                  # the game waits for an answer
        g.draw(pygame.Surface((W, H)))
        c.tap(g, fire=True)
        self.assertIsNone(g.feeble)
        self.assertEqual((g.world.level, g.world.windup), ("NORMAL", 24))
        g.world.deaths = 7                                      # NORMAL asks after 4 more
        c.tap(g)
        self.assertEqual(g.feeble, 0)                           # asked again after as many deaths
        c.tap(g, 50)
        c.tap(g, right=True)
        c.tap(g, fire=True)
        self.assertEqual(g.world.level, "NORMAL")               # "I can take it"

    def test_easy_never_asks(self):
        g, c = Game(ATLAS), Ctl()
        g.start([0], "EASY")
        g.world.deaths = 20
        c.tap(g)
        self.assertIsNone(g.feeble)
        self.assertEqual(g.world.players[0].lives, 5)

class Menus(unittest.TestCase):
    def setUp(self):
        if os.path.exists(storage.path("options.json")):
            os.remove(storage.path("options.json"))

    def test_main_menu_options_page_saves(self):
        g, c = Game(ATLAS), Ctl()
        changed = []
        g.on_option = changed.append
        c.tap(g, down=True)
        c.tap(g, fire=True)                                     # OPTIONS
        self.assertIsNotNone(g.sub)
        g.draw(pygame.Surface((W, H)))
        while g.sub.key != "music":
            c.tap(g, down=True)
        c.tap(g, left=True)
        self.assertEqual((g.opts["music"], changed[-1]), ("7", "music"))
        c.tap(g, bomb=True)
        self.assertIsNone(g.sub)
        self.assertEqual(storage.load_options()["music"], "7")
        c.tap(g, down=True)
        c.tap(g, jump=True)                                     # CONTROLS
        g.draw(pygame.Surface((W, H)))
        c.tap(g, right=True)
        g.draw(pygame.Surface((W, H)))
        c.tap(g, fire=True)
        self.assertIsNone(g.sub)
        c.tap(g, down=True)
        c.tap(g, down=True)
        c.tap(g, fire=True)                                     # QUIT
        self.assertTrue(g.quit)

    def test_idle_menu_runs_the_attract_loop_and_a_button_comes_back(self):
        g, c = Game(ATLAS), Ctl()
        c.tap(g, 601)
        self.assertEqual(g.mode, "story")
        c.tap(g, 40)
        c.tap(g, fire=True)
        self.assertEqual(g.mode, "title")

    def test_start_pauses_and_the_pause_menu_quits_to_title(self):
        g, c = Game(ATLAS), Ctl()
        g.start([0])
        c.tap(g, 5)
        c.tap(g, start=True)
        self.assertTrue(g.paused)
        frame = g.world.frame
        c.tap(g, 10)
        self.assertEqual(g.world.frame, frame)
        g.draw(pygame.Surface((W, H)))
        c.tap(g, down=True)
        c.tap(g, fire=True)                                     # OPTIONS over the frozen stage
        g.draw(pygame.Surface((W, H)))
        self.assertTrue(g.back())                               # Esc closes the page...
        self.assertIsNone(g.sub)
        self.assertTrue(g.back())                               # ...then resumes
        self.assertFalse(g.paused)
        c.tap(g, start=True)
        for _ in range(3):
            c.tap(g, down=True)
        c.tap(g, fire=True)                                     # QUIT TO TITLE
        self.assertEqual((g.mode, g.world), ("title", None))
        self.assertFalse(g.back())                              # Esc on the title quits the desktop game

    def test_lives_shake_and_flashes_options(self):
        g = Game(ATLAS)
        g.opts.update(lives="9", shake="OFF", flashes="REDUCED")
        g.start([0], "HARD")
        w = g.world
        self.assertEqual(w.players[0].lives, 9)
        w.shake = 10
        w.flash(100, 100)
        w.step([Pad(), Pad()])
        self.assertEqual(w.jolt, (0, 0))
        self.assertFalse(w.flashes_on)
        g.opts["lives"] = "AUTO"
        g.start([0], "HARD")
        self.assertEqual(g.world.players[0].lives, 2)
        self.assertEqual(storage.load_options()["level"], "HARD")    # offered first next time

    def test_swap_trades_the_face_buttons_and_their_names(self):
        from ironvolt.controls import Controls, _Device

        class Joy:
            def __init__(self, held):
                self.held = held
            get_numaxes = get_numhats = lambda self: 0
            get_numbuttons = lambda self: 16
            get_button = lambda self, n: n in self.held

        dev = _Device.__new__(_Device)
        dev.ctl, dev.joy, dev.web, dev.coin_was, dev.swap = None, Joy({0}), True, False, True
        s, _, _ = dev.state()
        self.assertEqual((s["fire"], s["jump"]), (True, False))
        c = Controls()
        c.device[0], c.swap = "xbox", True
        self.assertEqual((c.prompt("fire"), c.prompt("jump")), ("A / RT", "X"))


class TouchControls(unittest.TestCase):
    def finger(self, t, kind, x, y, fid=1):
        ev = {"down": pygame.FINGERDOWN, "move": pygame.FINGERMOTION, "up": pygame.FINGERUP}[kind]
        t.handle(pygame.event.Event(ev, x=x / W, y=y / H, dx=0, dy=0, touch_id=0, finger_id=fid))

    def test_stick_and_buttons_drive_player_one(self):
        from ironvolt.touch import KEYS, Touch
        t = Touch()
        self.assertFalse(t.used)
        self.finger(t, "down", 60, 150)                          # the stick appears under the thumb
        self.finger(t, "move", 80, 136)                          # right and up
        s = t.state()
        self.assertEqual((s["right"], s["up"], s["left"], s["down"]), (True, True, False, False))
        self.finger(t, "move", 140, 150)                         # far past the rim: the base follows
        self.finger(t, "move", 110, 150)
        self.assertTrue(t.state()["left"])                       # so turning back answers at once
        jx, jy = KEYS["jump"][0]
        fx, fy = KEYS["fire"][0]
        self.finger(t, "down", fx, fy, 2)
        self.assertTrue(t.state()["fire"])
        self.finger(t, "move", jx, jy, 2)                        # slide from fire to jump
        self.assertEqual((t.state()["fire"], t.state()["jump"]), (False, True))
        self.finger(t, "up", jx, jy, 2)
        self.finger(t, "up", 0, 0, 1)
        self.assertFalse(any(t.state().values()))
        surf = pygame.Surface((W, H))
        t.draw(surf)
        self.assertTrue(t.used)

    def test_a_tap_on_pause_pauses_through_the_controls(self):
        from ironvolt.controls import Controls
        from ironvolt.touch import KEYS
        c = Controls()
        x, y = KEYS["start"][0]
        c.handle(pygame.event.Event(pygame.FINGERDOWN, x=x / W, y=y / H, dx=0, dy=0, touch_id=0, finger_id=5))
        c.read()
        self.assertEqual((c.pads[0].pressed("start"), c.device[0], c.prompt("fire")), (True, "touch", "FIRE"))

    def test_browser_saves_go_to_local_storage(self):
        class Store(dict):
            getItem = dict.get
            setItem = dict.__setitem__

        store, real = Store(), storage.local
        storage.local = lambda: store
        try:
            self.assertEqual(storage.load(), storage.DEFAULT)
            storage.insert(storage.load(), "WEB", 999999)
            storage.save_options(dict(storage.DEFAULTS, music="2"))
            self.assertEqual((storage.load()[0], storage.load_options()["music"]), (["WEB", 999999], "2"))
            self.assertEqual(sorted(store), ["ironvolt/options.json", "ironvolt/scores.json"])
            store["ironvolt/options.json"] = '{"music": "eleven"}'
            self.assertEqual(storage.load_options()["music"], "8")
        finally:
            storage.local = real


class Art(unittest.TestCase):
    """What the actors' drawing is promised by the atlas."""

    def test_every_pose_has_a_picture_standing_on_its_feet(self):
        s = pygame.Surface((W, H))
        states = [dict(run_t=i / 2.4) for i in range(1, 9)] + [
            {}, dict(crouch=True), dict(crouch=True, slide=5), dict(slash=8), dict(crouch=True, slash=1),
            dict(dying=9), dict(on_ground=False, vy=-2.0), dict(on_ground=False, vy=2.0),
            dict(on_ground=False, dying=9)]
        for p in World((0, 1), seed=1).players:
            for state in states:
                for facing in (1, -1):
                    for aim in ((facing, 0), (facing, -1), (0, -1), (facing, 1), (0, 1)):
                        vars(p).update(dict(run_t=0.0, crouch=False, slide=0, slash=0, dying=0, on_ground=True, vy=0.0,
                                            safe=0, facing=facing, aim=aim), **state)
                        img = p.frame(ATLAS)
                        if p.on_ground:                 # nothing under the boots but the ground
                            self.assertEqual(img.get_bounding_rect().bottom, img.get_height(), state)
                        p.draw(s, ATLAS, 0)
        for kind in ("soldier", "lobber"):
            for state in ({}, dict(run_t=1.3), dict(aiming=4), dict(stun=5), dict(dying=3), dict(hurt=2)):
                for facing in (1, -1):
                    foe = Foe(100, GROUND_Y, kind)
                    vars(foe).update(state, facing=facing)
                    foe.draw(s, ATLAS, 0)

    def test_the_gun_is_drawn_out_to_the_muzzle(self):
        p = World((0,), seed=1).players[0]
        p.safe, p.x, p.y = 0, 40.0, 60.0
        bare = pygame.Surface(ATLAS.players[0]["stand"].get_size(), pygame.SRCALPHA)
        p.frame = lambda atlas: bare                    # no body: only what the hand holds is painted
        for weapon in ATLAS.guns:
            for facing in (1, -1):
                for aim in ((facing, 0), (facing, -1), (0, -1), (facing, 1), (0, 1), "crouch"):
                    p.crouch = aim == "crouch"
                    p.weapon, p.facing, p.aim = weapon, facing, (facing, 0) if p.crouch else aim
                    s = pygame.Surface((80, 80), pygame.SRCALPHA)
                    p.draw(s, ATLAS, 0)
                    mx, my, ux, uy = p.muzzle()
                    past = [(x + 0.5 - mx) * ux + (y + 0.5 - my) * uy       # how far past the muzzle, on the aim's line
                            for x in range(round(mx) - 5, round(mx) + 6) for y in range(round(my) - 5, round(my) + 6)
                            if s.get_at((x, y)).a and abs((x + 0.5 - mx) * uy - (y + 0.5 - my) * ux) < 1.5]
                    self.assertTrue(past and -1 <= max(past) <= 3, (weapon, facing, aim, past and max(past)))


if __name__ == "__main__":
    unittest.main()
