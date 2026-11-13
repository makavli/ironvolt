"""Fails unless ironvolt.__version__ is above the latest v* tag (run in CI on pull requests)."""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ironvolt  # noqa: E402


def parse(v):
    return tuple(int(x) for x in v.split("."))


if not re.fullmatch(r"\d+\.\d+\.\d+", ironvolt.__version__):
    print("::error::ironvolt.__version__ must look like 1.2.3, not %r." % ironvolt.__version__)
    sys.exit(1)
tags = subprocess.run(["git", "tag", "-l", "v*"], capture_output=True, text=True, check=True).stdout.split()
releases = sorted((parse(t[1:]) for t in tags if re.fullmatch(r"\d+\.\d+\.\d+", t[1:])), reverse=True)
mine = parse(ironvolt.__version__)
last = releases[0] if releases else None
print("version", ironvolt.__version__, "last release", ".".join(map(str, last)) if last else "none")
if last and mine <= last:
    print("::error::Bump the version above %s (ironvolt/__init__.py and CHANGELOG.md)." % ".".join(map(str, last)))
    sys.exit(1)
