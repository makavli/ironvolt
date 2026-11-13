# IRONVOLT

An arcade run-and-gun in the spirit of 90s cabinets: a 320×224 screen scaled up in whole steps, layered parallax
at dusk, chunky sprites, big explosions, one or two players on one machine. Everything you see and hear is
drawn and synthesized in code.

**Status:** v0.1, one complete stage with a boss. More missions to come.

## Play

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python run.py
```

| | Player 1 | Player 2 | Gamepad |
|---|---|---|---|
| Move / aim | Arrows | WASD | Stick or D-pad |
| Fire | Z | G | B or X |
| Jump | X | H | A |
| Grenade | C | J | Y or RB |
| Start / join | Enter or 1 | 2 | Start |

Down + jump drops through a catwalk. Up, diagonals, and down in the air aim your shot.
Coin: 5 (or Back) when free play is off. F11 or Alt+Enter: fullscreen. F2: scanlines. F3: free play on/off.
Esc: pause, then Esc again for the title.

Free the prisoners: each one drops a weapon (H heavy gun, S spread, R rockets, B grenades, 1 extra life).

## Develop

`bash tools/test_local.sh` runs every check on your machine: unit tests, a bot that plays the stage to the end,
screenshots in `shots/`, and a real window for a few seconds (`--exe` also builds the Windows app).

## Licence

Source available, all rights reserved: see [LICENSE](LICENSE). Credits: [CREDITS.md](CREDITS.md).
