"""The high-score table, saved as JSON in the user's app-data folder (IRONVOLT_HOME overrides it)."""

import json
import os

DEFAULT = [["VLT", 50000], ["RVT", 40000], ["ARC", 30000], ["BLT", 25000], ["GUN", 20000],
           ["IRN", 15000], ["ZAP", 10000], ["MAX", 8000], ["DSK", 6000], ["AAA", 4000]]


def folder():
    base = os.environ.get("IRONVOLT_HOME") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"), "Ironvolt")
    return base


def path():
    return os.path.join(folder(), "scores.json")


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
    try:
        os.makedirs(folder(), exist_ok=True)
        tmp = path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(table, f)
        os.replace(tmp, path())                  # never leaves a half-written table
    except OSError:
        pass
    return table
