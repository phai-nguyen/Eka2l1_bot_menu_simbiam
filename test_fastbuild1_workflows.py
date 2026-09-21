#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAST = ROOT / ".github/workflows/build-ios-nativeboot2-current-fast.yml"
SEED = ROOT / ".github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml"
B28 = ROOT / ".github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml"
B28_GIT_BLOB = "44d1c8aaa7ff5f0ff97271396b8bf771ad125b54"
BOOTSTRAP_KEY = "eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class FastbuildWorkflowContract(unittest.TestCase):
    def test_b28_workflow_is_untouched(self):
        self.assertEqual(git_blob_sha(B28), B28_GIT_BLOB)

    def test_fast_workflow_scope_and_cache(self):
        text = FAST.read_text(encoding="utf-8")
        self.assertIn("nativeboot2-current", text)
        self.assertIn(BOOTSTRAP_KEY, text)
        self.assertIn("eka2l1-nativeboot2-b19-salangabi1-nojava-manic3-macos15-v1", text)
        self.assertNotIn("actions/cache/save", text)

    def test_sccache_is_optional_acceleration(self):
        text = FAST.read_text(encoding="utf-8")
        self.assertIn("mozilla-actions/sccache-action@v0.0.11", text)
        self.assertIn('SCCACHE_GHA_ENABLED: "true"', text)
        self.assertIn('SCCACHE_IGNORE_SERVER_IO_ERROR: "1"', text)
        self.assertIn('SCCACHE_BASEDIRS=$UPSTREAM', text)
        self.assertIn("-DCMAKE_C_COMPILER_LAUNCHER=sccache", text)
        self.assertIn("-DCMAKE_CXX_COMPILER_LAUNCHER=sccache", text)
        self.assertIn("sccache --show-stats", text)

    def test_b28_contract_runs_before_post_bootstrap_apply(self):
        text = FAST.read_text(encoding="utf-8")
        verify = text.index('python3 test_nativeboot2_b28_wservlibtype1.py "$UPSTREAM"')
        apply_current = text.index('fastbuild1_manifest.py apply "$GITHUB_WORKSPACE" "$UPSTREAM"')
        self.assertLess(verify, apply_current)

    def test_probe_is_transient_and_never_uploads_ipa(self):
        text = FAST.read_text(encoding="utf-8")
        self.assertIn("probe_svc_change", text)
        self.assertIn("#define NBOOT2_FASTBUILD1_PROBE 1", text)
        self.assertIn("if: inputs.probe_svc_change != true", text)
        self.assertIn("FASTBUILD1_PROBE=1", text)

    def test_timing_and_packaging_invariants_are_present(self):
        text = FAST.read_text(encoding="utf-8")
        for marker in (
            "bootstrap_restore_seconds=",
            "patch_regression_seconds=",
            "cmake_build_seconds=",
            "package_seconds=",
            "total_seconds=",
            "--parallel 4",
            "Payload/EKA2L1.app",
            "_CodeSignature",
            "embedded.mobileprovision",
            "shasum -a 256",
        ):
            self.assertIn(marker, text)

    def test_seed_workflow_is_manual_only_and_saves_exact_bootstrap(self):
        text = SEED.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("push:", text)
        self.assertIn(BOOTSTRAP_KEY, text)
        self.assertIn("actions/cache/save@v4", text)
        self.assertIn("test_nativeboot2_b28_wservlibtype1.py", text)
        self.assertIn("xcodebuild -version", text)
        self.assertIn("clang --version", text)


if __name__ == "__main__":
    unittest.main()
