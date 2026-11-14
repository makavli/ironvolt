# Changelog

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
