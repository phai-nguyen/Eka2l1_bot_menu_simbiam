#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ci.fastbuild1_manifest as fb
import apply_nativeboot2_directhome_tfxdllprobe1 as dh_tfx_dll_probe


def directhome_tfx_svc_fixture():
    return (
        "// [NBOOT2][AKNSKIN_TFX_ECOM]\n"
        "// [NBOOT2][TFX_SESSION]\n"
        "    BRIDGE_FUNC(void, message_construct, std::int32_t msg_handle, service::message2 *msg_to_construct) {\n"
        "    }\n"
        "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n"
        "        ipc_msg_ptr msg = kern->get_msg(msg_handle);\n\n"
        "        status->set(val, kern->is_eka1());\n"
        "        kern->call_ipc_complete_callbacks(msg, val);\n"
        "        msg->unref();\n"
        "    }\n"
        "    BRIDGE_FUNC(void, message_complete_handle, std::int32_t msg_handle, std::int32_t val) { }\n"
        "    BRIDGE_FUNC(std::int32_t, message_ipc_copy, std::int32_t msg_handle, std::int32_t param) {\n"
        "        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n"
        "        msg->unref();\n\n"
        "        return result;\n"
        "    }\n"
        "    BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1, std::int32_t msg_handle, std::int32_t param) { }\n"
        "    BRIDGE_FUNC(std::int32_t, session_create, std::int32_t a, std::int32_t b) {\n"
        "        return epoc::error_not_found;\n"
        "    }\n"
        "    BRIDGE_FUNC(std::int32_t, session_create_from_handle, std::int32_t a) { }\n"
    )


def directhome_tfx_cenrep_fixture():
    return (
        '#include "config/config.h"\n'
        "    void central_repo_client_subsession::get_value(service::ipc_context *ctx) {\n"
        "    const std::string b47_process_name = b47_pr ? b47_pr->name() : std::string(\"<null>\");\n"
        "    const bool b47_tfx_state = ctx->sys->get_config()->native_phone_boot\n"
        "        && b47_aknskin_process && ctx->msg->function == cen_rep_get_int\n"
        "        && attach_repo && attach_repo->uid == static_cast<std::uint32_t>(0x102818E8)\n"
        "        && the_key.value() == static_cast<std::uint32_t>(0x00000009);\n"
        '    LOG_WARN(SERVICE_CENREP, "[NBOOT2][AKNSKIN_TFX_STATE] behavior=OBSERVE_ONLY");\n'
        "    switch (ctx->msg->function) {\n"
        "        case cen_rep_get_int: {\n"
        "            if (entry->data.etype != central_repo_entry_type::integer) {\n"
        "                complete_central_repo_ipc(ctx, epoc::error_argument);\n"
        "                return;\n"
        "            }\n"
        "            const std::uint32_t result_int = static_cast<std::uint32_t>(entry->data.intd);\n"
        "            if (b47_tfx_state) {\n"
        '                LOG_WARN(SERVICE_CENREP, "[NBOOT2][AKNSKIN_TFX_STATE] value=0x{:08X} behavior=OBSERVE_ONLY", result_int);\n'
        "            }\n"
        "            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, result_int);\n"
        "            break;\n"
        "        }\n"
        "    }\n"
        "}\n"
        "    void central_repo_client_subsession::append_new_key_to_found_eq_list() { }\n"
    )


def directhome_tfx_dll_fixture():
    return (
        "// [NBOOT2][DIRECTHOME_TFX_SESSION]\n"
        "    BRIDGE_FUNC(std::int32_t, library_attach, kernel::handle h, eka2l1::ptr<std::int32_t> num_eps, eka2l1::ptr<std::uint32_t> ep_list) {\n"
        "        library_ptr lib = kern->get<kernel::library>(h);\n"
        "        if (!lib) { return epoc::error_bad_handle; }\n"
        "        process_ptr pr = kern->crr_process();\n"
        "        std::vector<uint32_t> entries = lib->attach(kern->crr_process());\n"
        "        const std::uint32_t num_to_copy = common::min<std::uint32_t>(*num_eps.get(pr), static_cast<std::uint32_t>(entries.size()));\n"
        "        *num_eps.get(pr) = num_to_copy;\n"
        "        address *entry_points = ep_list.cast<address>().get(pr);\n"
        "        std::memcpy(entry_points, entries.data(), num_to_copy * sizeof(address));\n"
        "        return epoc::error_none;\n"
        "    }\n"
        "    BRIDGE_FUNC(std::int32_t, library_lookup, kernel::handle h, std::uint32_t ord_index) {\n"
        "        library_ptr lib = kern->get<kernel::library>(h);\n"
        "        if (!lib) { return 0; }\n"
        "        std::optional<uint32_t> func_addr = lib->get_ordinal_address(kern->crr_process(),\n"
        "            ord_index);\n"
        "        if (!func_addr) { return 0; }\n"
        "        return *func_addr;\n"
        "    }\n"
        "    BRIDGE_FUNC(std::int32_t, library_attached, kernel::handle h) { return epoc::error_none; }\n"
    )


class FastbuildManifestTests(unittest.TestCase):
    def test_directhome_tfx_dll_probe_records_attach_and_ordinal_without_changing_results(self):
        source = directhome_tfx_dll_fixture()
        patched = dh_tfx_dll_probe.apply_to_svc(source)
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH]", patched)
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_DLL_LOOKUP]", patched)
        self.assertIn("compat_target_kind != 2", patched)
        self.assertIn("process_uid3 == 0x10207114", patched)
        self.assertIn("library_uid3 == 0x10282DBA", patched)
        self.assertEqual(patched.count("lib->attach(kern->crr_process())"), 1)
        self.assertEqual(patched.count("lib->get_ordinal_address(kern->crr_process(),\n            ord_index)"), 1)
        self.assertIn("entries_available={}", patched)
        self.assertIn("ordinal={} success={} address=0x{:08X}", patched)
        self.assertIn("return *func_addr;", patched)
        self.assertIn("behavior=OBSERVE_ONLY", patched)

    def test_directhome_tfx_dll_probe_is_idempotent_and_fails_closed_on_missing_anchor(self):
        patched = dh_tfx_dll_probe.apply_to_svc(directhome_tfx_dll_fixture())
        self.assertEqual(dh_tfx_dll_probe.apply_to_svc(patched), patched)
        with self.assertRaisesRegex(SystemExit, "library_lookup"):
            dh_tfx_dll_probe.apply_to_svc(patched.replace("return *func_addr;", "return 0;"))

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

    def test_checked_in_manifest_includes_latest_compatboot_diagnostics(self):
        root = Path(__file__).resolve().parent
        post, regressions = fb.parse_manifest(root / "ci/fastbuild1_manifest.txt")
        applied = "\n".join(apply for apply, _ in post)
        self.assertNotIn("apply_nativeboot2_b88_phoneuicone14continue1.py", applied)
        self.assertNotIn("apply_nativeboot2_b89_fatalstatebypass1.py", applied)
        self.assertIn("apply_nativeboot2_compatboot1_menuprobe1.py", applied)
        self.assertEqual(
            post[-7:],
            [
                ("apply_nativeboot2_directhome_tfxecomtrace1.py", "test_nativeboot2_directhome_tfxecomtrace1.py"),
                ("apply_nativeboot2_directhome_tfxcallsiteprobe1.py", "test_nativeboot2_directhome_tfxcallsiteprobe1.py"),
                ("apply_nativeboot2_directhome_tfxsessiontrace1.py", "test_nativeboot2_directhome_tfxsessiontrace1.py"),
                ("apply_nativeboot2_directhome_tfxdllprobe1.py", "test_nativeboot2_directhome_tfxdllprobe1.py"),
                ("apply_nativeboot2_directhome_propertycancelguard1.py", "test_nativeboot2_directhome_propertycancelguard1.py"),
                ("apply_nativeboot2_directhome_codesegcollectorunlink1.py", "test_nativeboot2_directhome_codesegcollectorunlink1.py"),
                ("apply_nativeboot2_directhome_halpagesizeguard1.py", "test_nativeboot2_directhome_halpagesizeguard1.py"),
            ],
        )
        self.assertEqual(
            post[-9],
            (
                "apply_nativeboot2_compatboot1_directhomefingerprint1.py",
                "test_nativeboot2_compatboot1_directhomefingerprint1.py",
            ),
        )
        self.assertEqual(
            post[-10],
            (
                "apply_nativeboot2_b99_buildfingerprint1.py",
                "test_nativeboot2_b99_buildfingerprint1.py",
            ),
        )
        self.assertEqual(
            post[-11],
            (
                "apply_nativeboot2_b96_estorleaveexports1.py",
                "test_nativeboot2_b96_estorleaveexports1.py",
            ),
        )
        self.assertEqual(
            post[-12],
            (
                "apply_nativeboot2_directhome_teardowntrace1.py",
                "test_nativeboot2_directhome_teardowntrace1.py",
            ),
        )
        self.assertEqual(
            post[-13],
            (
                "apply_nativeboot2_b94_teardownprobe1.py",
                "test_nativeboot2_b94_teardownprobe1.py",
            ),
        )
        self.assertEqual(
            post[-14],
            (
                "apply_nativeboot2_b92_cenrepfindeqdiag1.py",
                "test_nativeboot2_b92_cenrepfindeqdiag1.py",
            ),
        )
        self.assertEqual(
            post[-15],
            (
                "apply_nativeboot2_b91_ipcteardown1.py",
                "test_nativeboot2_b91_ipcteardown1.py",
            ),
        )
        self.assertEqual(
            post[-16],
            (
                "apply_nativeboot2_compatboot1_menuprobe1.py",
                "test_nativeboot2_compatboot1_menuprobe1.py",
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
                "test_nativeboot2_compatboot1_directhome1.py",
            ],
        )

    def test_directhome_contract_accepts_manifest_upstream_argument(self):
        root = Path(__file__).resolve().parent
        script = root / "test_nativeboot2_compatboot1_directhome1.py"
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                ["python3", str(script), td],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_directhome_tfx_trace_applies_without_legacy_dll_marker(self):
        root = Path(__file__).resolve().parent
        patcher = root / "apply_nativeboot2_directhome_tfxecomtrace1.py"
        contract = root / "test_nativeboot2_directhome_tfxecomtrace1.py"
        source = directhome_tfx_svc_fixture()
        with tempfile.TemporaryDirectory() as td:
            upstream = Path(td)
            svc = upstream / "src/emu/kernel/src/svc.cpp"
            svc.parent.mkdir(parents=True)
            svc.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patcher), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            contract_result = subprocess.run(
                ["python3", str(contract), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                contract_result.returncode,
                0,
                contract_result.stdout + contract_result.stderr,
            )
            patched = svc.read_text(encoding="utf-8")
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_ECOM_COPY]", patched)
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_ECOM_COMPLETE]", patched)

    def test_tfx_trace_reports_copy_context_when_anchor_is_missing(self):
        root = Path(__file__).resolve().parent
        patcher = root / "apply_nativeboot2_directhome_tfxecomtrace1.py"
        source = directhome_tfx_svc_fixture().replace(
            "const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);",
            "const std::int32_t result = epoc::error_none;",
        )
        with tempfile.TemporaryDirectory() as td:
            upstream = Path(td)
            svc = upstream / "src/emu/kernel/src/svc.cpp"
            svc.parent.mkdir(parents=True)
            svc.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patcher), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_context:", result.stderr)
        self.assertIn("return result;", result.stderr)

    def test_tfx_trace_accepts_copy_anchor_without_blank_line(self):
        root = Path(__file__).resolve().parent
        patcher = root / "apply_nativeboot2_directhome_tfxecomtrace1.py"
        source = directhome_tfx_svc_fixture().replace(
            "msg->unref();\n\n        return result;",
            "msg->unref();\n        return result;",
        )
        with tempfile.TemporaryDirectory() as td:
            upstream = Path(td)
            svc = upstream / "src/emu/kernel/src/svc.cpp"
            svc.parent.mkdir(parents=True)
            svc.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patcher), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            patched = svc.read_text(encoding="utf-8")
        self.assertIn("directhome_tfx_ecom_log_copy(kern, msg, param, *info_host, result)", patched)

    def test_directhome_tfx_override_changes_only_scoped_cenrep_response(self):
        root = Path(__file__).resolve().parent
        patcher = root / "apply_nativeboot2_directhome_tfxenable1.py"
        contract = root / "test_nativeboot2_directhome_tfxenable1.py"
        with tempfile.TemporaryDirectory() as td:
            upstream = Path(td)
            repo = upstream / "src/emu/services/src/centralrepo/repo.cpp"
            repo.parent.mkdir(parents=True)
            repo.write_text(directhome_tfx_cenrep_fixture(), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patcher), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            repeated = subprocess.run(
                ["python3", str(patcher), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertIn("already applied", repeated.stdout)
            contract_result = subprocess.run(
                ["python3", str(contract), str(upstream)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                contract_result.returncode,
                0,
                contract_result.stdout + contract_result.stderr,
            )
            patched = repo.read_text(encoding="utf-8")
        self.assertIn("guest_result_int", patched)
        self.assertIn("DIRECTHOME_TFX_ENABLE_OVERRIDE", patched)


if __name__ == "__main__":
    unittest.main()
