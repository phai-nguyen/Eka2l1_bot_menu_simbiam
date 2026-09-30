#!/usr/bin/env python3
"""Contract tests for the read-only CompatBoot Menu3 FileServer Entry trace."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UPSTREAM: Path | None = None
SPEC = importlib.util.spec_from_file_location(
    "b98_menu3_entry_status1", ROOT / "apply_nativeboot2_b98_menu3entrystatus1.py"
)
B98 = importlib.util.module_from_spec(SPEC) if SPEC and SPEC.loader else None
if SPEC and SPEC.loader and B98:
    SPEC.loader.exec_module(B98)


ENTRY_CPP = r'''    void fs_server_client::entry(service::ipc_context *ctx) {
        std::optional<std::u16string> fname_op = ctx->get_argument_value<std::u16string>(0);

        if (!fname_op) {
            ctx->complete(epoc::error_argument);
            return;
        }

        std::u16string fname = std::move(*fname_op);
        fname = get_full_symbian_path(ss_path, fname);
        bool dir = false;
        io_system *io = ctx->sys->get_io_system();
        std::optional<entry_info> entry_hle = io->get_entry_info(fname);

        if (!entry_hle) {
            ctx->complete(epoc::error_not_found);
            return;
        }

        epoc::fs::entry entry;
        epoc::fs::build_symbian_entry_from_emulator_entry(io, entry_hle.value(), entry);
        ctx->write_data_to_descriptor_argument<epoc::fs::entry>(1, entry, nullptr, true);
        ctx->complete(epoc::error_none);
    }
    void fs_server_client::set_entry(service::ipc_context *ctx) {
    }
'''


class B98Menu3EntryStatusContracts(unittest.TestCase):
    def test_logs_normalized_path_and_exact_entry_status_after_lookup(self):
        self.assertIsNotNone(B98, "B98 patcher is missing")
        patched = B98.patch_entry_status(ENTRY_CPP)

        marker = "[COMPATBOOT][MENU3_ENTRY]"
        self.assertEqual(patched.count(marker), 1)
        self.assertIn("common::ucs2_to_utf8(fname)", patched)
        self.assertIn("? epoc::error_none : epoc::error_not_found", patched)
        self.assertLess(patched.index("io->get_entry_info(fname)"), patched.index(marker))
        self.assertLess(patched.index(marker), patched.index("if (!entry_hle)"))
        self.assertIn("compat_menu_entry_uid3 == compat_menu_entry_cfg->compat_target_uid3", patched)
        self.assertIn("compat_menu_entry_cfg->compat_menu_probe_mode", patched)

    def test_trace_does_not_change_either_entry_completion_branch(self):
        self.assertIsNotNone(B98, "B98 patcher is missing")
        patched = B98.patch_entry_status(ENTRY_CPP)
        self.assertEqual(patched.count("ctx->complete(epoc::error_not_found);"), 1)
        self.assertEqual(patched.count("ctx->complete(epoc::error_none);"), 1)
        self.assertEqual(patched.count("build_symbian_entry_from_emulator_entry(io, entry_hle.value(), entry);"), 1)

    def test_patch_is_idempotent(self):
        self.assertIsNotNone(B98, "B98 patcher is missing")
        once = B98.patch_entry_status(ENTRY_CPP)
        self.assertEqual(B98.patch_entry_status(once), once)

    def test_fastbuild_checks_marker_and_manifest_applies_contract(self):
        self.assertIsNotNone(B98, "B98 patcher is missing")
        workflow = (ROOT / ".github/workflows/build-ios-nativeboot2-current-fast.yml").read_text()
        manifest = (ROOT / "ci/fastbuild1_manifest.txt").read_text()
        self.assertIn("grep -Fq '[COMPATBOOT][MENU3_ENTRY]'", workflow)
        self.assertIn(
            "apply_nativeboot2_b98_menu3entrystatus1.py|test_nativeboot2_b98_menu3entrystatus1.py",
            manifest,
        )

    def test_applied_upstream_has_scoped_read_only_trace(self):
        if UPSTREAM is None:
            self.skipTest("no FASTBUILD upstream path supplied")
        source = (UPSTREAM / "src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
        marker = "[COMPATBOOT][MENU3_ENTRY]"
        self.assertEqual(source.count(marker), 1)
        trace_start = source.index("const bool compat_menu_entry")
        trace_end = source.index("if (!entry_hle)", trace_start)
        trace = source[trace_start:trace_end]
        self.assertIn("compat_menu_probe_mode", trace)
        self.assertIn("compat_target_uid3", trace)
        self.assertIn("? epoc::error_none : epoc::error_not_found", trace)
        self.assertIn("behavior=OBSERVE_ONLY", trace)


def main() -> None:
    global UPSTREAM
    if len(sys.argv) > 2:
        raise SystemExit("usage: test_nativeboot2_b98_menu3entrystatus1.py [upstream-root]")
    if len(sys.argv) == 2:
        UPSTREAM = Path(sys.argv[1]).resolve()
    unittest.main(argv=[sys.argv[0]])


if __name__ == "__main__":
    main()
