#!/usr/bin/env python3
"""Companion trace must preserve B43 TFX CreateSession behavior."""
import importlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SVC = '''    BRIDGE_FUNC(std::int32_t, session_create, eka2l1::ptr<desc8> server_name_des, std::int32_t msg_slot, eka2l1::ptr<void> sec, std::int32_t mode) {
        process_ptr pr = kern->crr_process();

        const std::string server_name = server_name_des.get(pr)->to_std_string(pr);
        const bool b43_tfx = kern->get_config()->native_phone_boot && (server_name == "TfxServer");
        kernel::thread *b43_thr = kern->crr_thread();
        auto *b43_cpu = kern->get_cpu();

        if (b43_tfx && pr && b43_thr && b43_cpu) {
            LOG_WARN(KERNEL, "[NBOOT2][TFX_SESSION] phase=request");
        }

        server_ptr server = kern->get_by_name<service::server>(server_name);

        if (!server) {
            LOG_TRACE(KERNEL, "Create session to unexist server: {}", server_name);
            if (kern->get_config()->native_phone_boot) {
                LOG_WARN(KERNEL, "[NBOOT2][MISSING_SERVER] process={} server={}", pr->name(), server_name);
            }
            if (b43_tfx) {
                b43_tfx_miss.valid = true;
                LOG_WARN(KERNEL, "[NBOOT2][TFX_SESSION] phase=missing");
            }
            return epoc::error_not_found;
        }

        if (b43_tfx) {
            b43_tfx_miss.valid = false;
            LOG_WARN(KERNEL, "[NBOOT2][TFX_SESSION] phase=found");
        }

        return do_create_session_from_server(kern, server, msg_slot, sec, mode);
    }
    BRIDGE_FUNC(std::int32_t, session_create_from_handle, std::int32_t handle) { }
'''
NAME = "src/emu/kernel/src/svc.cpp"


class TfxSessionTests(unittest.TestCase):
    def patcher(self):
        self.assertIsNotNone(importlib.util.find_spec("apply_nativeboot2_directhome_tfxsessiontrace1"),
                             "DirectHome TFX session patcher missing")
        return importlib.import_module("apply_nativeboot2_directhome_tfxsessiontrace1")

    def test_three_phases_same_ids_and_gate(self):
        patcher = self.patcher()
        patched = patcher.apply_to_svc(SVC)
        self.assertEqual(patched.count("[NBOOT2][DIRECTHOME_TFX_SESSION]"), 2)
        for gate in ("native_phone_boot", "compat_menu_probe_mode", "compat_target_kind == 2", 'server_name == "TfxServer"'):
            self.assertIn(gate, patched)
        self.assertEqual(patched.count("directhome_log_tfx_session(\"request\""), 1)
        self.assertEqual(patched.count("directhome_log_tfx_session(\"missing\""), 1)
        self.assertEqual(patched.count("directhome_log_tfx_session(\"found\""), 1)
        self.assertIn("pr->unique_id()", patched)
        self.assertIn("b43_thr->unique_id()", patched)
        self.assertIn("pr->get_uid_type()", patched)
        self.assertLess(patched.index('directhome_log_tfx_session("request"'), patched.index("get_by_name<service::server>"))
        self.assertLess(patched.index('directhome_log_tfx_session("missing"'), patched.index("return epoc::error_not_found;"))
        self.assertLess(patched.index('directhome_log_tfx_session("found"'), patched.index("return do_create_session_from_server"))
        self.assertIn("result=", patched)

    def test_null_context_existing_marker_and_atomicity(self):
        patcher = self.patcher()
        patched = patcher.apply_to_svc(SVC)
        self.assertIn("if (!pr || !b43_thr || b43_thr->owning_process() != pr)", patched)
        self.assertIn("context=missing", patched)
        self.assertEqual(patched.count("[NBOOT2][TFX_SESSION]"), SVC.count("[NBOOT2][TFX_SESSION]"))
        self.assertEqual(patched.count("return epoc::error_not_found;"), 1)
        self.assertEqual(patched.count("return do_create_session_from_server(kern, server, msg_slot, sec, mode);"), 1)
        self.assertNotIn("create_and_add<service::server>", patched)
        self.assertNotIn("ctx.complete(", patched)
        self.assertEqual(patcher.apply_to_svc(patched), patched)
        for bad in (SVC.replace("b43_tfx_miss.valid = true;", ""), SVC + SVC,
                    patched.replace('directhome_log_tfx_session("found"', 'missing_found("found"')):
            with self.subTest(bad=bad[:40]), self.assertRaises(SystemExit):
                patcher.apply_to_svc(bad)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / NAME
            target.parent.mkdir(parents=True)
            target.write_text(SVC + SVC, encoding="utf-8")
            with self.assertRaises(SystemExit):
                patcher.apply(root)
            self.assertEqual(target.read_text(encoding="utf-8"), SVC + SVC)

    def test_manifest_contract_checks_patched_upstream(self):
        patcher = self.patcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / NAME
            target.parent.mkdir(parents=True)
            target.write_text(SVC, encoding="utf-8")
            test_cmd = [sys.executable, str(Path(__file__).resolve()), str(root)]
            self.assertNotEqual(subprocess.run(test_cmd, capture_output=True).returncode, 0)
            patcher.apply(root)
            result = subprocess.run(test_cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def contract(root: Path):
    path = root / NAME
    if not path.is_file():
        raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: missing svc.cpp")
    src = path.read_text(encoding="utf-8")
    start = src.find("BRIDGE_FUNC(std::int32_t, session_create,")
    end = src.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle,", start)
    if start < 0 or end < 0:
        raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: session_create bounds")
    block = src[start:end]
    required = (
        "[NBOOT2][DIRECTHOME_TFX_SESSION]", "[NBOOT2][TFX_SESSION]",
        "native_phone_boot", "compat_menu_probe_mode", "compat_target_kind == 2",
        'server_name == "TfxServer"', "pr->unique_id()", "b43_thr->unique_id()",
        "context=missing", "return epoc::error_not_found;",
        "return do_create_session_from_server(kern, server, msg_slot, sec, mode);",
    )
    if any(value not in block for value in required):
        raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: missing gate/identity/semantic anchor")
    if block.count("[NBOOT2][DIRECTHOME_TFX_SESSION]") != 2:
        raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: duplicate/partial marker")
    for phase, after in (("request", "get_by_name<service::server>"),
                         ("missing", "return epoc::error_not_found;"),
                         ("found", "return do_create_session_from_server")):
        call = f'directhome_log_tfx_session("{phase}"'
        if block.count(call) != 1 or block.index(call) > block.index(after):
            raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: wrong phase order " + phase)
    if "create_and_add<service::server>" in block or "ctx.complete(" in block:
        raise SystemExit("DIRECTHOME-TFXSESSIONTRACE1-TEST: changed guest semantics")
    print("DIRECTHOME-TFXSESSIONTRACE1-TEST: PASS")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        contract(Path(sys.argv[1]).resolve())
    else:
        unittest.main()
