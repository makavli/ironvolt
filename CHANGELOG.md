# Changelog

## 0.11.1

- **macOS and Linux builds are back**, built on demand: a manual workflow (Actions -> macOS and Linux) builds a
  release's own source on GitHub's macOS and Linux machines, checks each build starts and plays, adds
  `Ironvolt-macos.zip` and `Ironvolt-linux.tar.gz` to that release, and can push them to itch.io too. The Windows and
  browser builds still come with every release, so a slow Mac queue never holds one up.

## 0.11.0

Missions 1 and 2 get set pieces of their own, and a hidden map page each: all four pages can now be found.
- **Mission 1, SCRAPYARD DUSK:**
  - **The magnet crane:** the first pit is now wide and flooded. Hop on the car wreck hanging from the crane's
    magnet and it carries the team over. Its magnet holds your boots; empty at the far side, it swings back.
  - **The car presses:** two presses stamp the yard floor on a beat. Run under between blows; troopers caught under
    one get SQUASHED.
  - **The scrap tunnel:** a grate near the end of the yard leads down to where the Legion keeps what it strips from
    the wrecks: three prisoners and the brother's first map page, up on a shelf of scrap.
- **Mission 2, THE PRISONER LINE:**
  - **The train roofs:** halfway along the yard, a boxcar rolls by with its ladder down. Climb on and the team rides
    the moving train's roofs while the yard rushes past and troopers drop in. Signal gantries sweep the roof at head
    height: a bell, a DUCK! sign, then the beam. Crouch under it; troopers who stand get BONKED off. A map page rides
    along too.
- **Shouts:** WHEE! off a steam vent, SQUASHED! under a crusher, and a bouncing sign over the crane.
- The demo bot ducks under the gantries.

## 0.10.0

Missions 3 and 4 play differently, not only look different, and there is more to do between missions.
- **Mission 3, PYLON ROAD:**
  - **Live cross-arms:** the line's current jumps along some arms on a beat. They crackle first, then burn anyone
    standing on them. Cross between beats.
  - **The storm drain:** crouch on the grate in the road and the team drops into the drain under it. It is dark and
    wet, it holds two prisoners and a map page, and it comes up past the hardest stretch of road.
  - **The gully:** a lineman's cable trolley carries the team across while drones come at it. It waits until
    everyone is aboard, and its cage keeps you on.
- **Mission 4, THE CRADLE:**
  - **Steam vents:** stand on one and it throws you up to the high catwalks, where a prisoner and a map page wait.
  - **The crushers:** four rams slam the floor in a rolling wave. Run under them between blows; they crush troopers
    too.
  - **Lights out:** a long stretch in the dark. Only your lamp, muzzle flashes, fire and the Legion's red lenses
    show.
  - **The lift:** the team rides the freight lift up the tower while Graive's guard drops onto it, then steps out
    into the arena.
- **Between missions:** a map of the old grid, the Voltline. The route you fought along lights up, the towns around
  the mission you won get their power back one by one, and the next mission's node blinks.
- **A rank for every mission (S, A, B, C)** on the tally, with a bonus up to 30,000: S means every prisoner,
  secrets included, and nobody down.
- **The brother's map pages:** one is hidden in missions 3 and 4. Each is worth 5,000, and the map screen keeps
  count.
- **Gentler choices:**
  - **RELAXED**, a new level below EASY: nine lives, half the troopers, half as many shots, a weaker boss.
  - EASY now sends fewer troopers and shoots less often too.
  - **Two new options**, ENEMIES (fewer, normal, more) and ENEMY FIRE (less, normal, more), override the
    difficulty. The options page scrolls.
- **Grenades:** six at the start, at each respawn and from each B capsule (was ten), so the bosses are no longer a
  grenade spam.
- New mission art: the salt road has its own near layer (poles, salt mounds, a bucket truck), and the Cradle its
  own (pipe racks, tanks, a venting stack). New sounds for the arcs, vents, the drain and the lift.
- **The knife reaches further:** fire with a trooper in your face or a long arm away and it is a stab, not a shot.
- **Bouncing signs:** "DUCK HERE: GO DOWN!" over the drain grate and "WALK IN: GOING UP!" at the lift, and a shout
  as you go down, up and back out.
- In the storm drain, prisoners and troopers stand on its floor (they appeared on top of its ceiling).
- Mission 4's high catwalks now run on over the pits beyond them: walking off the end no longer drops you in one.

## 0.9.0

Mission 4, the last one.
- **Mission 4, THE CRADLE:** the outer works of the one reactor tower that still turns, under a high, pale dusk
  where the ash is torn open. Reactor blocks, coolant housings, catwalks in tiers, floor plates fallen in.
- **Guards:** Graive's own troopers in his red plate. They take three hits and fire two shots at a time.
- **GRAIVE**, the warlord himself, in the Cradle's lineman rig: it strides in firing its arm cannon, crouches, and
  leaps at you, and its landing sends a shockwave along the floor both ways. Jump the waves, watch for the shadow
  where it lands, or get up on a catwalk, where it cannot leap at you. Broken, it leaps sooner and lands two waves.
- **Two new songs:** the Cradle's theme and GRAIVE's.
- The bot that tests every mission turns to face a boss that walks in, and stands its ground in a corner.

## 0.8.0

Mission 3.
- **Mission 3, PYLON ROAD:** the service road under the last live high-tension line, across the salt flats toward
  the Cradle. A clearer, warmer dusk (the ash is thinning), pylon footings to climb and their cross-arms to run
  along, wrecked line trucks and washed-out culverts.
- **Sappers:** hazard-yellow troopers with no gun and a satchel charge. They run straight at you and light it up
  close: shoot them early, or knife them before the fuse burns down.
- **HARROW**, the grid company's old line-survey gunship under Legion plate: it hangs over the road out of jumping
  reach and fires aimed bursts; when its siren sounds it climbs and makes a bomb run down the road. Shoot up and run
  out from under the bombs. Once a rotor is hit it runs faster and drops drones.
- **Two new songs:** the pylon road's theme and HARROW's.
- `python tools/sim.py god 3` plays any mission with the bot.

## 0.7.1

The first release with mission 2 (all of 0.7.0 below: its own release run was cancelled).
- **Windows only:** the releases now ship `Ironvolt.exe` alone. The macOS and Linux builds are discontinued: GitHub's
  hosted Mac machines kept a release waiting in the queue, and the game is tested on Windows. On macOS or Linux, play
  from the source (`python run.py`); the last macOS and Linux builds are in the 0.6.0 release.

## 0.7.0

Mission 2, and a game that goes on after the first boss.
- **Missions:** clearing a mission now leads to the next one with the same team: scores, lives, guns and grenades
  carry over, and a player who is out gets a fresh chance to continue. Each mission has its own map, briefing, boss,
  backdrop and music.
- **Mission 2, THE PRISONER LINE:** the Legion's rail yard and viaduct under a colder dusk, with container stacks,
  gantries over the gaps and signal masts.
- **Shield troopers:** a riot shield stops level shots at its face. Get behind them, shoot from above, throw a
  grenade, use the knife, or wait for them to lower the shield to fire.
- **WARDEN**, the prisoner line's armoured engine: its roof gun fires in bursts, and when the whistle blows it charges
  down the track. Climb a gantry or jump it. Once its armour splits it charges faster and troopers jump from its back
  door.
- **Two new songs:** the prisoner line's theme and WARDEN's.
- The boss's name over its health bar follows the mission.
- Fixed: the Linux build crashed on quitting.

## 0.6.0

New moves and a new look.
- **Knife:** fire with a trooper within reach and you stab instead of shooting. One stab downs any trooper.
- **Slide:** down + jump on solid ground is a fast, low dash under rifle fire; jump out of it to keep the speed. On a
  catwalk, down + jump still drops through.
- **Stomp:** land on a foe's head to hurt it and bounce off; hold jump to bounce high.
- **Art:** bigger, more detailed heroes and troopers, 8-frame runs, jump and fall, slide, stab, hurt and down poses,
  guns that turn with the aim, a new drone, turret, hostage and BASTION. Riveted decks, hazard stripes at the edges,
  lattice catwalks, and a deeper dusk skyline behind them.
- **Hostages** now appear ahead of you, never behind or on top of you.
- The controls page lists the slide and the knife.
- The local checks play the game silently (they used to sound through the speakers).

## 0.5.1

Fullscreen on phones and tablets.
- **Fullscreen:** in the browser, the first touch puts the game in fullscreen and turns it to landscape (Android and
  iPad; iPhone Safari allows neither, so there it stays in the page). Leave fullscreen and the next touch comes back.
- `tools/web_check.py` checks that a touch asks for fullscreen inside its gesture (headless Chrome itself never grants it).

## 0.5.0

Play on a phone or a tablet, in the browser.
- **Touch controls:** touch the left half of the screen and a stick appears under your thumb (it follows a thumb
  that runs past its edge). FIRE, JUMP and GRenade sit on the right; slide a thumb from one to another. The II
  button pauses. They drive player 1, work in every menu, and stay hidden until the screen is touched.
- **Turn your phone:** held upright, the game asks to be turned sideways.
- **Browser saves:** the options and the high scores now live in the browser's storage and survive a reload.
  Before, the browser version forgot them with the page.
- `tools/web_check.py` now really starts a game (it held keys too briefly before) and plays a moment with an
  emulated touchscreen.

## 0.4.1

Clean music in the browser, for real this time.
- **Fix:** 0.4.0's smaller build slices did not stop the browser's ticking. A browser runs the sound on the game's
  own thread, and one step of the title song's build alone takes longer than a frame. The browser build now ships
  the songs baked to Ogg at build time, made by the same code (`tools/music_bake.py`, needs ffmpeg), and builds
  nothing while you play. The desktop game is unchanged.
- `tools/web_check.py` fails if the page builds its music instead of loading the baked songs.

## 0.4.0

A real menu, options for everyone, and clean sound in the browser.
- **Main menu:** start, options, controls, high scores, quit. Left alone, it still runs the story, the scores and
  the demo like a cabinet; any button brings it back.
- **Options, saved between games:** difficulty, lives, the "too feeble" offer, free play; fullscreen, pixel-perfect
  or fit-to-window scaling, scanlines; music and effects volume; rumble, swap fire and jump on pads; and for
  accessibility, screen shake off, reduced flashes, and a game speed down to 70%.
- **Controls page:** every key for both players, and a drawn pad with what each button does (Xbox or PlayStation
  names, following the pad you use).
- **Pause menu:** Start on a pad now pauses too. Resume, options, controls, or quit to the title.
- **Sharp on high-DPI screens:** Windows no longer blurs the window at 125% or 150% display scaling.
- **Fix:** the browser version ticked until all the music was built. The build now takes smaller slices of each
  frame and the sound has a deeper buffer.
- README: the gamepad buttons in the controls table were wrong; fixed.

## 0.3.0

Choose your fight, and a new soundtrack.
- **Difficulty:** Easy, Normal or Hard, picked after Start and before play. It sets lives (5, 3, 2), how long
  enemies take to aim, how fast their shots fly, the boss's armour and the safety after a respawn.
- **"Too feeble, soldier?"** Die often on Normal or Hard and the game stops to offer one level lower. Refuse, and
  it asks again later.
- **New music, in stereo:** a title theme, a stage theme with a full song structure (intro, hook, lift, breakdown,
  final chorus) and a boss theme that crossfades in when the gate locks. Every song is still made in code. The
  browser builds it a few milliseconds a frame, so the page never stalls.
- **Kill chain:** kills less than 2.5 seconds apart chain up. Each one scores x2, x3... up to x8, shown under
  your score with the time left to keep it going. Dying breaks the chain.
- `tools/music_check.py` renders every song to `shots/` and reports build time, loudness and peak.

## 0.2.1

Smoother sound, pads in the browser.
- **Music:** a calmer 120 bpm loop, quieter, easing in over four seconds when a game starts; a cleaner mix that never
  distorts.
- **Gamepads in the browser:** Start, the d-pad and every button now work in the web version (press any button once
  so the browser shows the pad to the game).
- Store art: `tools/cover.py` draws the itch.io cover and page banner from the game's own frames.

## 0.2.0

IRONVOLT on every desk and in the browser.
- **Play in the browser:** the same game, built with pygbag, runs in a web page with nothing to install (the itch.io
  page plays it in place). Sound starts on the first click or key.
- **One file for Windows:** the release carries `Ironvolt.exe`, a single file to double-click, instead of a zip.
- Download buttons for Windows, macOS and Linux at the top of the README.

## 0.1.0

The first playable mission.
- Mission 1, Scrapyard Dusk: pits, catwalks, Legion troopers, grenadiers, drones, turrets, five technicians to free,
  and BASTION, the Legion's gate crawler, with a second phase.
- One or two players on keyboard or any gamepad (Xbox, PlayStation, Switch Pro), switching seamlessly; rumble and
  light bar on pads that have them.
- 8-way aim, grenades, heavy gun, spread gun, rockets; continues and a high-score table.
- The story of the Long Dusk in the attract loop.
- Everything drawn and synthesized in code: sharp whole-step scaling, a cabinet bezel and optional scanlines.
