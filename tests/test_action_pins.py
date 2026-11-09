"""Regression tests for immutable GitHub Actions references."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.check_action_pins import check_action_references


GOOD_SHA = "a" * 40
GOOD_DIGEST = "b" * 64


class ActionPinPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, path, source):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    def test_pinned_actions_and_local_steps_pass(self):
        self.put(".github/workflows/check.yml", f"""
jobs:
  check:
    steps:
      - uses: actions/checkout@{GOOD_SHA} # v6
      - uses: ./custom-action
      - uses: vendor/repo/.github/workflows/reuse.yml@{GOOD_SHA} # v1.2.3
      - uses: docker://alpine@sha256:{GOOD_DIGEST} # v3.20
""")
        self.assertEqual(check_action_references(self.root), [])

    def test_mutable_tag_and_branch_are_rejected(self):
        self.put(".github/workflows/check.yml", """
steps:
  - uses: actions/setup-python@v6
  - uses: vendor/repo@main
""")
        self.assertEqual(len(check_action_references(self.root)), 2)

    def test_pinned_sha_requires_version_comment(self):
        self.put(".github/workflows/check.yml",
                 f"- uses: actions/checkout@{GOOD_SHA}\n")
        self.assertIn("version comment", check_action_references(self.root)[0][2])

    def test_composite_action_definitions_are_checked(self):
        self.put("custom-action/action.yml",
                 "- runs: composite\n  steps:\n"
                 "    - uses: vendor/unsafe@v1\n")
        failures = check_action_references(self.root)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][:2], ("custom-action/action.yml", 3))

    def test_comments_and_local_actions_do_not_trigger(self):
        self.put(".github/workflows/check.yaml",
                 "# - uses: actions/checkout@v1\n"
                 "- uses: './custom-action'\n")
        self.assertEqual(check_action_references(self.root), [])


if __name__ == "__main__":
    unittest.main()
