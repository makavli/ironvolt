"""The version in the code and the top CHANGELOG entry agree, once each."""

import os
import re
import unittest

import ironvolt

CHANGELOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHANGELOG.md")


class Release(unittest.TestCase):
    def setUp(self):
        with open(CHANGELOG, encoding="utf-8") as f:
            self.versions = re.findall(r"^## (\S+)", f.read(), re.M)

    def test_changelog_top_is_this_version(self):
        self.assertRegex(ironvolt.__version__, r"^\d+\.\d+\.\d+$")
        self.assertEqual(self.versions[0], ironvolt.__version__)

    def test_one_entry_per_version(self):
        self.assertEqual(len(self.versions), len(set(self.versions)))


if __name__ == "__main__":
    unittest.main()
