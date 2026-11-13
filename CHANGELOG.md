# Changelog

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
