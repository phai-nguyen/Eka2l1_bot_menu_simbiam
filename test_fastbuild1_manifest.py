#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ci.fastbuild1_manifest as fb


class FastbuildManifestTests(unittest.TestCase):
    def test_parse_manifest_sections(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.txt"
            p.write_text(
                "[post_bootstrap]\n"
                "apply_b29.py|test_b29.py\n"
                "[regressions]\n"
                "test_b20.py\n"
                "test_b29.py\n",
                encoding="utf-8",
            )
            post, regressions = fb.parse_manifest(p)
            self.assertEqual(post, [("apply_b29.py", "test_b29.py")])
            self.assertEqual(regressions, ["test_b20.py", "test_b29.py"])

    def test_validate_rejects_missing_referenced_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "manifest.txt"
            manifest.write_text(
                "[post_bootstrap]\n"
                "missing_apply.py|missing_test.py\n"
                "[regressions]\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "missing_apply.py"):
                fb.validate_manifest(root, manifest)

    def test_apply_runs_patcher_then_its_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            upstream = root / "upstream"
            upstream.mkdir()
            for name in ("apply_b29.py", "test_b29.py"):
                (root / name).write_text("print('ok')\n", encoding="utf-8")
            manifest = root / "manifest.txt"
            manifest.write_text(
                "[post_bootstrap]\n"
                "apply_b29.py|test_b29.py\n"
                "[regressions]\n",
                encoding="utf-8",
            )
            with mock.patch.object(subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess([], 0)
                fb.apply_post_bootstrap(root, upstream, manifest)
                self.assertEqual(
                    [call.args[0] for call in run.call_args_list],
                    [
                        ["python3", str(root / "apply_b29.py"), str(upstream)],
                        ["python3", str(root / "test_b29.py"), str(upstream)],
                    ],
                )

    def test_checked_in_manifest_includes_current_b84_milestone(self):
        root = Path(__file__).resolve().parent
        post, regressions = fb.parse_manifest(root / "ci/fastbuild1_manifest.txt")
        self.assertEqual(
            post[-1],
            (
                "apply_nativeboot2_b84_phoneuiresidwindow1.py",
                "test_nativeboot2_b84_phoneuiresidwindow1.py",
            ),
        )
        self.assertEqual(
            regressions,
            [
                "test_nativeboot2_b20_cenresetall1.py",
                "test_nativeboot2_b21_fbsfontalias1.py",
                "test_nativeboot2_b22_fbsdefaulttypeface1.py",
                "test_nativeboot2_b23_fbsfontspecv2abi1.py",
                "test_nativeboot2_b24_fbsvtableabi1.py",
                "test_nativeboot2_b25_fbssharedheap1.py",
                "test_nativeboot2_b26_ioslibraryexit1.py",
                "test_nativeboot2_b27_wservpanic13trace1.py",
                "test_nativeboot2_b28_wservlibtype1.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
