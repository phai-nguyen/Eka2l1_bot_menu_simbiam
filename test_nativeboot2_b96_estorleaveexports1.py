#!/usr/bin/env python3
"""Contract tests for the CompatBoot-only Menu3 EStor Leave stack resolver."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UPSTREAM: Path | None = None


def load_module(name: str, path: Path):
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
    if spec and spec.loader and module:
        spec.loader.exec_module(module)
    return module


B90 = load_module(
    "compatboot1_menuprobe1",
    ROOT / "apply_nativeboot2_compatboot1_menuprobe1.py",
)
B96 = load_module(
    "b96_estorleaveexports1",
    ROOT / "apply_nativeboot2_b96_estorleaveexports1.py",
)

LEAVE_START_CPP = r'''    BRIDGE_FUNC(eka2l1::ptr<void>, leave_start) {
        kernel::thread *thr = kern->crr_thread();
        thr->increase_leave_depth();
        return current_local_data(kern)->trap_handler;
    }
}
'''


class B96EStorLeaveExportContracts(unittest.TestCase):
    def test_resolves_nearest_export_and_bounded_code_window_for_menu3_stack(self):
        self.assertIsNotNone(B90, "B90 patcher is missing")
        self.assertIsNotNone(B96, "B96 patcher is missing")

        b90 = B90.patch_menu3_leave5(LEAVE_START_CPP)
        traced = B96.patch_menu3_leave5_exports(b90)

        self.assertIn("[COMPATBOOT][MENU3_LEAVE5_EXPORT]", traced)
        self.assertIn("seg->get_export_table(compat_leave_pr)", traced)
        self.assertIn("nearest_export_ordinal", traced)
        self.assertIn("nearest_export_delta", traced)
        self.assertIn("relative_halfword = -8", traced)
        self.assertIn("relative_halfword <= 4", traced)
        self.assertIn("eka2l1::ptr<std::uint16_t>(code_address).get(compat_leave_pr)", traced)

        gate = traced.index("if (compat_leave_cfg && compat_leave_pr")
        trace = traced.index("[COMPATBOOT][MENU3_LEAVE5_EXPORT]")
        original_leave = traced.index("thr->increase_leave_depth();")
        self.assertLess(gate, trace)
        self.assertLess(trace, original_leave)
        self.assertEqual(traced.count("thr->increase_leave_depth();"), 1)
        self.assertEqual(traced.count("return current_local_data(kern)->trap_handler;"), 1)

    def test_export_probe_is_idempotent(self):
        self.assertIsNotNone(B90, "B90 patcher is missing")
        self.assertIsNotNone(B96, "B96 patcher is missing")

        b90 = B90.patch_menu3_leave5(LEAVE_START_CPP)
        once = B96.patch_menu3_leave5_exports(b90)
        twice = B96.patch_menu3_leave5_exports(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("[COMPATBOOT][MENU3_LEAVE5_EXPORT]"), 1)

    def test_fastbuild_checks_export_and_code_window_markers(self):
        workflow = (ROOT / ".github/workflows/build-ios-nativeboot2-current-fast.yml").read_text()
        self.assertIn("grep -Fq '[COMPATBOOT][MENU3_LEAVE5_EXPORT]'", workflow)
        self.assertIn("grep -Fq '[COMPATBOOT][MENU3_LEAVE5_CODE16]'", workflow)

    def test_applied_upstream_contains_scoped_observation_only_probe(self):
        if UPSTREAM is None:
            self.skipTest("no FASTBUILD upstream path supplied")
        source = (UPSTREAM / "src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
        marker = "[COMPATBOOT][MENU3_LEAVE5_EXPORT]"
        self.assertEqual(source.count(marker), 1)
        trace_start = source.index("const auto compat_leave_exports")
        trace_end = source.index("thr->increase_leave_depth();", trace_start)
        trace = source[trace_start:trace_end]
        self.assertIn("compat_menu_probe_mode", source[:trace_start])
        self.assertIn("compat_target_uid3", source[:trace_start])
        self.assertIn("compat_leave_code == epoc::error_not_supported", source[:trace_start])
        self.assertIn("seg->get_export_table(compat_leave_pr)", trace)
        self.assertIn("[COMPATBOOT][MENU3_LEAVE5_CODE16]", trace)
        self.assertIn("behavior=OBSERVE_ONLY", trace)


def main() -> None:
    global UPSTREAM
    if len(sys.argv) > 2:
        raise SystemExit("usage: test_nativeboot2_b96_estorleaveexports1.py [upstream-root]")
    if len(sys.argv) == 2:
        UPSTREAM = Path(sys.argv[1]).resolve()
    unittest.main(argv=[sys.argv[0]])


if __name__ == "__main__":
    main()
