<div align="center">

<img src="docs/media/title.png" alt="IRONVOLT title screen" width="720">

# IRONVOLT

**Two soldiers. One endless dusk. Every bullet counts.**

A 90s-arcade run-and-gun for one or two players: chunky pixels, screen-shaking explosions,
a tank boss with a second phase, and not a single image or sound file in the repo.
**Every pixel and every note is made by code.**

![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![pygame-ce](https://img.shields.io/badge/pygame--ce-2.5.8-6aa84f)
![Players](https://img.shields.io/badge/players-1%E2%80%932-e8742a)
![Assets](https://img.shields.io/badge/game%20assets-0%20files-8e44ad)
![Status](https://img.shields.io/badge/status-v0.11%20%C2%B7%20missions%201%E2%80%934-c0392b)

<img src="docs/media/run.gif" alt="Two players running and gunning through the scrapyard" width="640">

[![Download for Windows](https://img.shields.io/badge/Download-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/makavli/ironvolt/releases/latest/download/Ironvolt.exe)

</div>

**Windows:** double-click `Ironvolt.exe`. It is not code-signed, so the first time Windows says "Windows protected your
PC": click **More info**, then **Run anyway**.

**Other systems:** from 0.7.1 the releases ship a Windows build only. The macOS and Linux downloads are discontinued:
GitHub's hosted Mac machines kept a release waiting in the queue, and the game is tested on Windows. On macOS or
Linux, play from the source (below); the last macOS and Linux builds are in the 0.6.0 release.

## The Long Dusk

In 2079 the Voltline grid burned in a single night, and the sun has not cleared the horizon since. The **Rust
Legion** holds the last working tower and drags grid technicians from their towns in chains to keep it running.

You are what is left of the **Ironvolt Brigade**, the crews who used to climb those towers. Free every technician
you reach. Break the Legion's gate. Turn the lights back on. *([The full story](docs/STORY.md))*

## What's in the cabinet

| | |
|---|---|
| <img src="docs/media/play_700.png" alt="Catwalks, troopers and drones" width="400"> | <img src="docs/media/play_2600.png" alt="Rockets against the Legion" width="400"> |
| **8-way aim, run, jump, slide, stomp, knife up close, drop through catwalks.** Troopers, grenadiers, shield troopers, sappers, Graive's guards, drones and turrets come from every side. | **Free the prisoners, take their guns:** heavy gun, spread, rockets, grenades, extra lives. |

<div align="center">

<img src="docs/media/boss.gif" alt="Boss fight against BASTION, the Legion's gate crawler" width="640">

**BASTION**, the Legion's gate crawler. Two phases. Bring grenades. Then mission 2, **THE PRISONER LINE**, and
**WARDEN**, an armoured engine that runs down anything on the track. Then mission 3, **PYLON ROAD**, and **HARROW**,
a gunship that bombs the road. Then mission 4, **THE CRADLE**, and **GRAIVE** himself.

Each mission plays its own way: a magnet crane over a flooded pit, car presses, a run along a moving train's roofs
under the signal gantries, live cross-arms that arc on a beat, a storm drain under the road, a cable trolley
over a gully, steam vents that throw you to the high catwalks, crushers, a stretch with the lights out, and a lift
ride up the tower. Between missions, a map of the old grid lights up behind you; every mission ends with a rank,
S to C, and hides a page of the brother's maps.

</div>

- **Two players on one machine**, keyboard or any gamepad (Xbox, PlayStation, Switch Pro), with rumble and light bar.
- **Phones and tablets too:** in the browser, touch controls appear when you touch the screen.
- **Smooth on any screen:** logic at a fixed 60 Hz, drawn blended at your refresh rate (144 Hz, 165 Hz...), scaled
  up in sharp whole steps inside a cabinet bezel (or to fit the window). Optional scanlines. Sharp on high-DPI
  screens too.
- **Arcade to the bone:** hit-stop, screen shake, a kill-chain multiplier up to x8, continues, coins or free
  play, and a high-score table.
- **Relaxed, Easy, Normal or Hard**, chosen before every game. Die too often and the game asks if you are too
  feeble.
- **Options for everyone:** lives, how many enemies and how often they shoot, music and effects volume, rumble, swapped fire and jump, screen shake, flashes
  and a slower game speed, all saved. A controls page shows the keys and the pad.
- **A synthesized stereo soundtrack:** a title theme, and for each mission a stage theme and a boss theme that
  crossfades in when the arena locks.
- **Zero asset files:** sprites, tiles, the font, every sound effect and the music are generated at start-up.

## Play from the source

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python run.py
```

| | Player 1 | Player 2 | Gamepad |
|---|---|---|---|
| Move / aim | Arrows | WASD | Stick or D-pad |
| Fire | Z | G | X or RT |
| Jump | X | H | A |
| Grenade | C | J | B or RB |
| Start / join / pause | Enter or 1 | 2 | Start |

Down + jump drops through a catwalk. Up, diagonals, and down in the air aim your shot.
Coin: 5 (or Back) when free play is off. F11 or Alt+Enter: fullscreen. F2: scanlines. F3: free play on/off.
Esc: pause (or back out of a menu). The pause menu has the options and the way back to the title.

Free the prisoners: each one drops a weapon (H heavy gun, S spread, R rockets, B grenades, 1 extra life).
Crouch on a grate in the road to go under it.

## Develop

`bash tools/test_local.sh` runs every check on your machine: unit tests, a bot that plays every mission to the end,
screenshots in `shots/`, and a real window for a few seconds. `--exe` also builds `Ironvolt.exe`; `--web` builds
the browser version and plays it in headless Chrome (`bash tools/web_build.sh --serve` to play it yourself).

`IRONVOLT_STAGE=4 python run.py` starts on mission 4 (or 2, 3), to try it without playing the ones before.

`python tools/media.py` re-records the GIFs and pictures in this README (needs ffmpeg).

## Licence

Source available, all rights reserved: see [LICENSE](LICENSE). Credits: [CREDITS.md](CREDITS.md).
