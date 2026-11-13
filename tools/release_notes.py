"""Prints the CHANGELOG entry of the current version (the release notes)."""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ironvolt  # noqa: E402

with open(os.path.join(os.path.dirname(__file__), "..", "CHANGELOG.md"), encoding="utf-8") as f:
    text = f.read()
m = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(ironvolt.__version__), text, re.M | re.S)
if not m:
    sys.exit("no CHANGELOG entry for " + ironvolt.__version__)
print(m[1].strip())
