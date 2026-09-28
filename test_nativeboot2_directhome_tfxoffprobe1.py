#!/usr/bin/env python3
"""Contract for the DirectHome stock-TFX response feasibility probe."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = None
if __name__ == "__main__" and len(sys.argv) == 2:
    UPSTREAM_ROOT = Path(sys.argv.pop()).resolve()
PATCHER_PATH = ROOT / "apply_nativeboot2_directhome_tfxoffprobe1.py"
if PATCHER_PATH.is_file():
    SPEC = importlib.util.spec_from_file_location("directhome_tfx_off_probe", PATCHER_PATH)
    PATCH = importlib.util.module_from_spec(SPEC)
    assert SPEC and SPEC.loader
    sys.modules[SPEC.name] = PATCH
    SPEC.loader.exec_module(PATCH)
else:
    PATCH = None


REPO_CPP = '''
    void central_repo_client_subsession::get_value(service::ipc_context *ctx) {
        const auto *b47_config = ctx->sys->get_config();
        const bool b47_directhome_tfx_scope =
            b47_config->native_phone_boot
            && b47_config->compat_menu_probe_mode
            && b47_config->compat_target_uid3 == static_cast<std::uint32_t>(0x102750F0);
            const bool b47_directhome_tfx_override =
                b47_tfx_state && b47_directhome_tfx_scope
                && result_int == static_cast<std::uint32_t>(0x7FFFFFFF);
            const std::uint32_t guest_result_int = b47_directhome_tfx_override ? 0U : result_int;
            if (b47_directhome_tfx_override) {
                LOG_WARN(SERVICE_CENREP, "[NBOOT2][DIRECTHOME_TFX_ENABLE_OVERRIDE]");
            }
            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int);
    }

    std::int32_t session_create() {
        return epoc::error_not_found;
    }
'''


class DirectHomeTfxOffProbeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PATCH, "DirectHome TFX-off probe patcher has not been implemented")

    def test_getint_returns_the_original_firmware_value(self):
        patched, changed = PATCH.apply_to_source(REPO_CPP)
        self.assertTrue(changed)
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_OFF_PROBE]", patched)
        self.assertIn("const std::uint32_t guest_result_int = result_int;", patched)
        self.assertIn("write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int)", patched)
        self.assertNotIn("guest_result_int = b47_directhome_tfx_override ? 0U : result_int", patched)
        self.assertEqual(PATCH.apply_to_source(patched), (patched, False))

    def test_probe_does_not_invent_server_or_change_missing_server_result(self):
        patched, _ = PATCH.apply_to_source(REPO_CPP)
        self.assertNotIn("create_and_add<service::server>", patched)
        self.assertIn("return epoc::error_not_found;", patched)

    def test_probe_only_changes_directhome_getint_response(self):
        patched, _ = PATCH.apply_to_source(REPO_CPP)
        self.assertIn("compat_target_uid3 == static_cast<std::uint32_t>(0x102750F0)", patched)
        self.assertIn("native_phone_boot", patched)
        self.assertIn("compat_menu_probe_mode", patched)
        self.assertIn("ctx->write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int)", patched)
        self.assertNotIn("entry->data.intd =", patched)

    def test_patched_upstream_keeps_real_tfxserver_missing_result(self):
        if UPSTREAM_ROOT is None:
            self.skipTest("upstream root is supplied by FASTBUILD")
        repo_cpp = UPSTREAM_ROOT / "src/emu/services/src/centralrepo/repo.cpp"
        svc_cpp = UPSTREAM_ROOT / "src/emu/kernel/src/svc.cpp"
        self.assertTrue(repo_cpp.is_file(), f"missing source: {repo_cpp}")
        self.assertTrue(svc_cpp.is_file(), f"missing source: {svc_cpp}")
        repo_source = repo_cpp.read_text(encoding="utf-8")
        svc_source = svc_cpp.read_text(encoding="utf-8")
        self.assertEqual(repo_source.count("[NBOOT2][DIRECTHOME_TFX_OFF_PROBE]"), 1)
        self.assertIn("const std::uint32_t guest_result_int = result_int;", repo_source)
        session_start = svc_source.find("BRIDGE_FUNC(std::int32_t, session_create,")
        session_end = svc_source.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle,", session_start + 1)
        self.assertGreaterEqual(session_start, 0)
        self.assertGreater(session_end, session_start)
        session_create = svc_source[session_start:session_end]
        self.assertIn("return epoc::error_not_found;", session_create)
        self.assertNotIn("create_and_add<service::server>", session_create)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
