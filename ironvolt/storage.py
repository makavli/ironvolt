"""The high-score table and the options, saved as JSON in the user's app-data folder (IRONVOLT_HOME overrides it).
In a browser the files would vanish with the page, so they go to its localStorage instead."""

import json
import os
import sys

WEB = sys.platform == "emscripten"

DEFAULT = [["VLT", 50000], ["RVT", 40000], ["ARC", 30000], ["BLT", 25000], ["GUN", 20000],
           ["IRN", 15000], ["ZAP", 10000], ["MAX", 8000], ["DSK", 6000], ["AAA", 4000]]


def folder():
    base = os.environ.get("IRONVOLT_HOME") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"), "Ironvolt")
    return base


def path(name="scores.json"):
    return os.path.join(folder(), name)


def local():
    """The browser's localStorage, or None (not a browser, or storage blocked)."""
    if not WEB:
        return None
    try:
        import platform
        return platform.window.localStorage
    except Exception:                            # a JS proxy raises its own error types
        return None


def _read(where):
    store = local()
    if store is not None:
        try:
            raw = store.getItem("ironvolt/" + os.path.basename(where))
        except Exception:
            raw = None
        if raw is None:
            raise OSError("not saved yet")
        return json.loads(str(raw))
    with open(where, encoding="utf-8") as f:
        return json.load(f)


def load():
    try:
        table = _read(path())
        if isinstance(table, list) and table and all(isinstance(r, list) and len(r) == 2 for r in table):
            return [[str(n).upper()[:3], max(0, min(int(s), 9999999))] for n, s in table][:10]   # 7 digits shown
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
    store = local()
    if store is not None:
        try:
            store.setItem("ironvolt/" + os.path.basename(where), json.dumps(data))
        except Exception:                        # private browsing or a full quota: never crash over a save
            pass
        return
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
        saved = _read(path("options.json"))
        if isinstance(saved, dict):
            opts.update({k: v for k, v in saved.items() if k in OPTIONS and v in OPTIONS[k]})
    except (OSError, ValueError, TypeError, RecursionError):
        pass
    return opts


def save_options(opts):
    _save(opts, path("options.json"))
