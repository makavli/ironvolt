"""The high-score table and the options, saved as JSON in the user's app-data folder (IRONVOLT_HOME overrides it)."""

import json
import os

DEFAULT = [["VLT", 50000], ["RVT", 40000], ["ARC", 30000], ["BLT", 25000], ["GUN", 20000],
           ["IRN", 15000], ["ZAP", 10000], ["MAX", 8000], ["DSK", 6000], ["AAA", 4000]]


def folder():
    base = os.environ.get("IRONVOLT_HOME") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"), "Ironvolt")
    return base


def path(name="scores.json"):
    return os.path.join(folder(), name)


def load():
    try:
        with open(path(), encoding="utf-8") as f:
            table = json.load(f)
        if isinstance(table, list) and table and all(isinstance(r, list) and len(r) == 2 for r in table):
            return [[str(n)[:3], int(s)] for n, s in table][:10]
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):   # a planted or broken file
        pass
    return [row[:] for row in DEFAULT]


def qualifies(table, score):
    return score > table[-1][1]


def insert(table, name, score):
    table = sorted(table + [[name[:3], score]], key=lambda r: -r[1])[:10]
    _save(table, path())
    return table


def _save(data, where):
    try:
        os.makedirs(folder(), exist_ok=True)
        tmp = where + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, where)                   # never leaves a half-written file
    except OSError:
        pass


# Every option and its choices, in the order the options screen shows them. Only these are ever loaded.
OPTIONS = {
    "level": ("EASY", "NORMAL", "HARD"),         # offered first on the difficulty screen
    "lives": ("AUTO", "1", "2", "3", "5", "7", "9"),
    "feeble": ("ON", "OFF"),                     # the "too feeble, soldier?" offer
    "free_play": ("ON", "OFF"),
    "fullscreen": ("OFF", "ON"),
    "scale": ("PIXEL PERFECT", "FIT"),
    "crt": ("ON", "OFF"),
    "music": ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
    "sfx": ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
    "rumble": ("ON", "OFF"),
    "swap": ("OFF", "ON"),                       # pads: fire and jump trade places
    "shake": ("ON", "OFF"),
    "flashes": ("FULL", "REDUCED"),
    "speed": ("70%", "80%", "90%", "100%"),
}
DEFAULTS = {k: v[0] for k, v in OPTIONS.items()} | {"level": "NORMAL", "music": "8", "sfx": "8", "speed": "100%"}


def load_options():
    opts = dict(DEFAULTS)
    try:
        with open(path("options.json"), encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            opts.update({k: v for k, v in saved.items() if k in OPTIONS and v in OPTIONS[k]})
    except (OSError, ValueError, TypeError, RecursionError):
        pass
    return opts


def save_options(opts):
    _save(opts, path("options.json"))
