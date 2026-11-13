# Changelog

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
