#!/usr/bin/env python3
"""Contract for the B99 H2 no-bypass runtime build identity marker."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APPLY = ROOT / "apply_nativeboot2_b99_buildfingerprint1.py"
MARKER = '[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1'


class B99BuildFingerprintTests(unittest.TestCase):
    def make_upstream(self, root: Path) -> Path:
        source = root / "src/emu/ios/app/RootViewController.mm"
        source.parent.mkdir(parents=True)
        source.write_text(
            """- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {
    if (compatProbe) {
        eka2l1::ios::bridge::start_compat_phone();
    } else {
        eka2l1::ios::bridge::start_native_phone();
    }
}
""",
            encoding="utf-8",
        )
        return root

    def test_marker_is_inserted_once_at_emulator_session_start(self) -> None:
        self.assertTrue(APPLY.is_file(), "B99 fingerprint patcher is not implemented")
        with tempfile.TemporaryDirectory() as temp:
            upstream = self.make_upstream(Path(temp))
            source = upstream / "src/emu/ios/app/RootViewController.mm"
            original = source.read_text(encoding="utf-8")
            first = subprocess.run(
                [sys.executable, str(APPLY), str(upstream)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            text = source.read_text(encoding="utf-8")
            self.assertEqual(text.replace(f'    NSLog(@"{MARKER}");\n', "", 1), original)
            self.assertEqual(text.count(MARKER), 1)
            self.assertLess(
                text.index(MARKER),
                text.index("eka2l1::ios::bridge::start_native_phone();"),
            )
            self.assertIn(
                '- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {\n'
                f'    NSLog(@"{MARKER}");',
                text,
            )

            second = subprocess.run(
                [sys.executable, str(APPLY), str(upstream)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(source.read_text(encoding="utf-8").count(MARKER), 1)

    def test_missing_or_ambiguous_session_anchor_is_rejected(self) -> None:
        if not APPLY.is_file():
            self.skipTest("B99 fingerprint patcher is not implemented yet")
        for body in ("@implementation RootViewController\n", "\n".join(
            ["- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {", "}"] * 2
        )):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source = root / "src/emu/ios/app/RootViewController.mm"
                source.parent.mkdir(parents=True)
                source.write_text(body, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(APPLY), str(root)],
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("anchor", result.stdout + result.stderr)

    def test_existing_marker_outside_unique_session_anchor_is_rejected(self) -> None:
        if not APPLY.is_file():
            self.skipTest("B99 fingerprint patcher is not implemented yet")
        invalid_sources = (
            f'NSLog(@"{MARKER}");\n@implementation RootViewController\n',
            f'void unrelated() {{ NSLog(@"{MARKER}"); }}\n'
            '- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {\n}\n',
            f'- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {{\n'
            f'    NSLog(@"{MARKER}");\n}}\n'
            f'- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {{\n}}\n',
        )
        for body in invalid_sources:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source = root / "src/emu/ios/app/RootViewController.mm"
                source.parent.mkdir(parents=True)
                source.write_text(body, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(APPLY), str(root)],
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("anchor", result.stdout + result.stderr)

    def test_manifest_style_invocation_accepts_upstream_argument(self) -> None:
        if os.environ.get("B99_MANIFEST_INVOCATION_CHILD") == "1":
            self.skipTest("nested manifest invocation")
        with tempfile.TemporaryDirectory() as temp:
            env = os.environ.copy()
            env["B99_MANIFEST_INVOCATION_CHILD"] = "1"
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
        raise SystemExit("usage: test_nativeboot2_b99_buildfingerprint1.py [upstream-root]")
    # FASTBUILD passes the upstream root to every contract test. These tests
    # use isolated fixtures, so remove that positional argument from unittest.
    unittest.main(argv=[sys.argv[0]])
