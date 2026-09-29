#!/usr/bin/env python3
"""Contract tests for the isolated CompatBoot Direct Home build identity."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APPLY = ROOT / "apply_nativeboot2_compatboot1_directhomefingerprint1.py"
B99_MARKER = "[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1"
DIRECTHOME_MARKER = "[NBOOT2][BUILD_ID] build=COMPATBOOT1_DIRECTHOME1 track=H2_COMPATBOOT1_DIRECTHOME1"
ANCHOR = "- (void)startEmulatorWithCompatTarget:(NSInteger)compatTarget {\n"


class DirectHomeBuildFingerprintTests(unittest.TestCase):
    def make_upstream(self, root: Path, source_text: str) -> Path:
        source = root / "src/emu/ios/app/RootViewController.mm"
        source.parent.mkdir(parents=True)
        source.write_text(source_text, encoding="utf-8")
        return root

    def run_patcher(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(APPLY), str(root)],
            text=True,
            capture_output=True,
        )

    def test_direct_home_fingerprint_patcher_exists(self):
        self.assertTrue(APPLY.is_file(), "Direct Home fingerprint patcher is not implemented")

    def test_replaces_b99_marker_once_at_session_start_and_is_idempotent(self):
        if not APPLY.is_file():
            self.skipTest("Direct Home fingerprint patcher is not implemented yet")
        original = (
            ANCHOR
            + f'    NSLog(@"{B99_MARKER}");\n'
            + "    start_compat_boot();\n}\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            upstream = self.make_upstream(Path(temp), original)
            source = upstream / "src/emu/ios/app/RootViewController.mm"

            first = self.run_patcher(upstream)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            patched = source.read_text(encoding="utf-8")
            self.assertEqual(patched.count(DIRECTHOME_MARKER), 1)
            self.assertEqual(patched.count(B99_MARKER), 0)
            self.assertIn(ANCHOR + f'    NSLog(@"{DIRECTHOME_MARKER}");\n', patched)
            self.assertEqual(
                patched.replace(
                    f'    NSLog(@"{DIRECTHOME_MARKER}");\n',
                    f'    NSLog(@"{B99_MARKER}");\n',
                    1,
                ),
                original,
            )

            second = self.run_patcher(upstream)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(source.read_text(encoding="utf-8"), patched)

    def test_missing_or_ambiguous_session_anchor_is_rejected(self):
        if not APPLY.is_file():
            self.skipTest("Direct Home fingerprint patcher is not implemented yet")
        cases = (
            "@implementation RootViewController\n",
            ANCHOR + "}\n" + ANCHOR + "}\n",
        )
        for body in cases:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                result = self.run_patcher(self.make_upstream(Path(temp), body))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("anchor", result.stdout + result.stderr)

    def test_markers_outside_the_single_session_start_are_rejected(self):
        if not APPLY.is_file():
            self.skipTest("Direct Home fingerprint patcher is not implemented yet")
        wrong_location = (
            f'NSLog(@"{B99_MARKER}");\n'
            + ANCHOR
            + "    start_compat_boot();\n}\n"
        )
        duplicate_directhome = (
            ANCHOR
            + f'    NSLog(@"{DIRECTHOME_MARKER}");\n'
            + f'    NSLog(@"{DIRECTHOME_MARKER}");\n}}\n'
        )
        for body in (wrong_location, duplicate_directhome):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                result = self.run_patcher(self.make_upstream(Path(temp), body))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("marker", result.stdout + result.stderr)

    def test_manifest_style_invocation_accepts_upstream_argument(self):
        if os.environ.get("DIRECTHOME_FINGERPRINT_MANIFEST_CHILD") == "1":
            self.skipTest("nested manifest invocation")
        with tempfile.TemporaryDirectory() as temp:
            env = os.environ.copy()
            env["DIRECTHOME_FINGERPRINT_MANIFEST_CHILD"] = "1"
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), temp],
                text=True,
                capture_output=True,
                env=env,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stderr)


if __name__ == "__main__":
    if len(sys.argv) not in (1, 2):
        raise SystemExit("usage: test_nativeboot2_compatboot1_directhomefingerprint1.py [upstream-root]")
    unittest.main(argv=[sys.argv[0]])
