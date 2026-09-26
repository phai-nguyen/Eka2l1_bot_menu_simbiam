import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "b90_patch", ROOT / "apply_nativeboot2_compatboot1_menuprobe1.py"
)
PATCH = importlib.util.module_from_spec(SPEC) if SPEC and SPEC.origin and Path(SPEC.origin).is_file() else None
if SPEC and SPEC.loader and PATCH:
    SPEC.loader.exec_module(PATCH)


STATE_H = """        bool native_phone_mode = false;
        bool native_boot_handoff_ok = false;
"""

BRIDGE_H = "    bool start_native_phone();\n    void stop_native_phone();\n"
BRIDGE_CPP = """        bool g_native_phone_mode = false;
        bool start_locked();
        void shutdown_locked();
        bool g_running = true;
        bool g_has_device = true;
        std::unique_ptr<emulator> g_state;
        // global anchors fixture
        void start() {
            g_state->native_phone_mode = g_native_phone_mode;
        }
        bool start_native_phone() {
            g_native_phone_mode = true;
            shutdown_locked();
            const bool has_device = start_locked();
            const bool handoff_ok = has_device && g_state && g_state->native_boot_handoff_ok;
            if (!handoff_ok) {
                g_native_phone_mode = false;
                shutdown_locked();
                start_locked();
                return false;
            }
            return true;
        }
        void stop_native_phone() {
            g_native_phone_mode = false;
            shutdown_locked();
            start_locked();
        }
"""

CONFIG_H = "        bool native_phone_boot{ false };\n"
STATE_CPP = """#include <kernel/process.h>
        conf.native_phone_boot = native_phone_mode;
        if (compat_mode) {
                            native_boot_handoff_ok = true;
                        }
"""
SVC_CPP = """#include <kernel/kernel.h>
namespace eka2l1::epoc {
    BRIDGE_FUNC(void, server_receive, kernel::handle h, eka2l1::ptr<epoc::request_status> req_sts, eka2l1::ptr<void> data_ptr) {
        server_ptr server = kern->get<service::server>(h);

        if (!server) {
            return;
        }
    }
    void missing_server_fixture() {
        if (!server) {
            if (kern->get_config()->native_phone_boot) {
                LOG_WARN(KERNEL, "[NBOOT2][MISSING_SERVER] process={} server={} msg_slots={} mode={}",
                    pr->name(), server_name, msg_slot, mode);
            }
            return epoc::error_not_found;
        }
    }
}
"""
MISSING_SERVER_CPP = '''        if (!server) {
            if (kern->get_config()->native_phone_boot) {
                LOG_WARN(KERNEL, "[NBOOT2][MISSING_SERVER] process={} server={} msg_slots={} mode={}",
                    pr->name(), server_name, msg_slot, mode);
            }
            return epoc::error_not_found;
        }
'''
WINUSER_CPP = '''            set_visible(visible != 0);
            if (b50_postlogo_uid(b50_uid3)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][POSTLOGO_CANVAS_VISIBLE] visible_after={} physically_seen_after={}",
                    is_visible() ? 1 : 0, can_be_physically_seen() ? 1 : 0);
            }
            ctx.complete(epoc::error_none);
'''

ROOT_VIEW = """- (void)onEmulator {
    // NATIVEBOOT2 EMUHUB1: native Nokia startup is explicit.
    if (!eka2l1::ios::bridge::has_device()) {
        [self showAlert:EKAL(@\"Emulator unavailable\")
                 message:EKAL(@\"Install a Symbian device before starting Emulator.\")];
        return;
    }
    if (self.phoneRunning) { return; }
    // Existing NATIVEBOOT2 launch body
}

- (void)onShowApps { [self showAppsScreen]; }
"""


class CompatBootModeContracts(unittest.TestCase):
    def test_compat_mode_is_opt_in_and_does_not_change_native_default(self):
        self.assertIsNotNone(PATCH, "B90 patcher is not present")
        state = PATCH.patch_state_header(STATE_H)
        self.assertIn("bool native_phone_mode = false;", state)
        self.assertIn("bool compat_menu_probe_mode = false;", state)

    def test_emulator_choice_routes_to_native_or_compat_bridge(self):
        self.assertIsNotNone(PATCH, "B90 patcher is not present")
        routed = PATCH.patch_emulator_choice(ROOT_VIEW)
        self.assertIn("start_native_phone()", routed)
        self.assertIn("start_compat_menu_probe()", routed)
        self.assertEqual(routed.count("start_compat_menu_probe()"), 1)
        self.assertIn("CompatBoot Menu Probe", routed)

    def test_compat_start_failure_restores_normal_frontend(self):
        self.assertIsNotNone(PATCH, "B90 patcher is not present")
        routed = PATCH.patch_emulator_choice(ROOT_VIEW)
        self.assertIn("if (!ok)", routed)
        self.assertIn("[self showAppsScreen]", routed)
        self.assertIn("compatbootstartfailed", routed.lower().replace(" ", ""))
        self.assertIn("has_device()", routed)

    def test_bridge_keeps_compat_mode_separate_and_resets_it_on_failure_and_exit(self):
        header = PATCH.patch_bridge_header(BRIDGE_H)
        bridge = PATCH.patch_bridge_cpp(BRIDGE_CPP)
        self.assertIn("start_compat_menu_probe", header)
        self.assertIn("g_state->compat_menu_probe_mode = g_compat_menu_probe_mode", bridge)
        self.assertIn("g_compat_menu_probe_mode = true", bridge)
        self.assertGreaterEqual(bridge.count("g_compat_menu_probe_mode = false"), 3)
        self.assertIn("[COMPATBOOT][ROLLBACK]", bridge)

    def test_localization_and_transformations_are_idempotent(self):
        localized = PATCH.patch_localization('            @"Add Mode" : @"Thêm chế độ",\n')
        self.assertIn('"Chọn chế độ khởi động"', localized)
        self.assertEqual(PATCH.patch_localization(localized), localized)
        state = PATCH.patch_state_header(STATE_H)
        root = PATCH.patch_emulator_choice(ROOT_VIEW)
        bridge_h = PATCH.patch_bridge_header(BRIDGE_H)
        bridge_cpp = PATCH.patch_bridge_cpp(BRIDGE_CPP)
        self.assertEqual(PATCH.patch_state_header(state), state)
        self.assertEqual(PATCH.patch_emulator_choice(root), root)
        self.assertEqual(PATCH.patch_bridge_header(bridge_h), bridge_h)
        self.assertEqual(PATCH.patch_bridge_cpp(bridge_cpp), bridge_cpp)

    def test_each_required_service_blocks_launch_until_ready(self):
        self.assertTrue(hasattr(PATCH, "patch_svc"), "service barrier patch is absent")
        svc = PATCH.patch_svc(SVC_CPP)
        for service in ("FileServer", "FBS", "WindowServer", "CenRep", "AppArc", "AknCapServer"):
            with self.subTest(service=service):
                self.assertIn(service, svc)
        self.assertIn("epoc::get_fbs_server_name_by_epocver(ver)", svc)
        self.assertNotIn("#include <services/", svc)
        self.assertIn('"!CentralRepository"', svc)
        self.assertIn('"101fdfae_10207218_AppServer"', svc)
        self.assertIn("if (!missing.empty())", svc)
        self.assertIn("return;", svc[svc.index("if (!missing.empty())"):])

    def test_service_helpers_close_namespace_before_original_svc_namespace(self):
        svc = PATCH.patch_svc(SVC_CPP)
        original_namespace = svc.index("namespace eka2l1::epoc {\n    BRIDGE_FUNC")
        prefix = svc[:original_namespace]
        code_only = re.sub(
            r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
            "",
            prefix,
            flags=re.DOTALL,
        )
        self.assertEqual(code_only.count("{"), code_only.count("}"))

    def test_service_probe_uses_kernel_version_without_system_definition(self):
        svc = PATCH.patch_svc(SVC_CPP)
        self.assertIn("kern->get_epoc_version()", svc)
        self.assertNotIn("kern->get_system()->get_symbian_version_use()", svc)

    def test_live_process_without_ready_server_does_not_release_barrier(self):
        self.assertTrue(hasattr(PATCH, "patch_svc"), "service barrier patch is absent")
        svc = PATCH.patch_svc(SVC_CPP)
        self.assertIn("kern->get_by_name<service::server>(name)", svc)
        self.assertIn("registered->is_hle() || guest_ready", svc)
        self.assertNotIn("find_process", svc)
        self.assertNotIn("process_alive", svc)

    def test_barrier_timeout_reports_exact_missing_services(self):
        self.assertTrue(hasattr(PATCH, "patch_svc"), "service barrier patch is absent")
        self.assertTrue(hasattr(PATCH, "patch_state_cpp"), "deadline initialization patch is absent")
        svc = PATCH.patch_svc(SVC_CPP)
        state = PATCH.patch_state_cpp(STATE_CPP)
        self.assertNotIn("get_ntimer()->register_event", svc)
        self.assertIn("[COMPATBOOT][BARRIER_TIMEOUT]", state)
        self.assertIn("get_ntimer()->register_event", state)
        self.assertIn("schedule_event(60000000", state)
        self.assertIn("missing_or_unobserved", state)
        self.assertIn("services=6", state)
        self.assertIn("static_cast<std::uint64_t>(now_ms) + 60000", state)

    def test_menu3_launches_once_after_all_services_ready(self):
        self.assertTrue(hasattr(PATCH, "patch_svc"), "service barrier patch is absent")
        svc = PATCH.patch_svc(SVC_CPP)
        self.assertIn("if (!cfg->compat_menu_probe_mode", svc)
        self.assertIn("cfg->compat_menu_probe_launched = true;", svc)
        self.assertLess(svc.index("cfg->compat_menu_probe_launched = true;"), svc.index("spawn_new_process(menu_path"))
        self.assertIn('u"Z:\\\\sys\\\\bin\\\\menu3.exe"', svc)
        self.assertIn("menu->run()", svc)

    def test_config_and_deadline_state_are_transient_and_profile_scoped(self):
        self.assertTrue(hasattr(PATCH, "patch_config_header"), "transient barrier state patch is absent")
        self.assertTrue(hasattr(PATCH, "patch_state_cpp"), "deadline initialization patch is absent")
        config = PATCH.patch_config_header(CONFIG_H)
        state = PATCH.patch_state_cpp(STATE_CPP)
        self.assertIn("compat_menu_probe_mode{ false }", config)
        self.assertIn("conf.compat_menu_probe_mode = compat_menu_probe_mode", state)
        self.assertIn("[COMPATBOOT][DEADLINE_START] after=EStart_run", state)

    def test_full_patcher_application_is_idempotent(self):
        self.assertTrue(hasattr(PATCH, "apply"), "B90 apply entry point is absent")
        with tempfile.TemporaryDirectory() as temp_dir:
            upstream = Path(temp_dir)
            files = {
                "src/emu/ios/include/ios/state.h": STATE_H,
                "src/emu/ios/app/RootViewController.mm": ROOT_VIEW,
                "src/emu/ios/include/ios/emu_bridge.h": BRIDGE_H,
                "src/emu/ios/src/emu_bridge.mm": BRIDGE_CPP,
                "src/emu/ios/app/EKALocalization.mm": '            @"Add Mode" : @"Thêm chế độ",\n',
                "src/emu/config/include/config/config.h": CONFIG_H,
                "src/emu/ios/src/state.cpp": STATE_CPP,
                "src/emu/kernel/src/svc.cpp": SVC_CPP,
                "src/emu/services/src/window/classes/winuser.cpp": WINUSER_CPP,
            }
            for relpath, body in files.items():
                path = upstream / relpath
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            PATCH.apply(upstream)
            first = {
                relpath: (upstream / relpath).read_text(encoding="utf-8")
                for relpath in files
            }
            PATCH.apply(upstream)
            second = {
                relpath: (upstream / relpath).read_text(encoding="utf-8")
                for relpath in files
            }
            self.assertEqual(first, second)

    def test_compat_markers_are_profile_gated(self):
        self.assertTrue(hasattr(PATCH, "patch_missing_server"), "CompatTrace forwarding is absent")
        traced = PATCH.patch_missing_server(MISSING_SERVER_CPP)
        self.assertIn("kern->get_config()->compat_menu_probe_mode && pr", traced)
        self.assertIn("[COMPATBOOT][MISSING_SERVER]", traced)

    def test_first_target_failure_is_logged_without_semantic_override(self):
        self.assertTrue(hasattr(PATCH, "patch_missing_server"), "CompatTrace forwarding is absent")
        traced = PATCH.patch_missing_server(MISSING_SERVER_CPP)
        self.assertEqual(traced.count("return epoc::error_not_found;"), 1)
        self.assertIn("[NBOOT2][MISSING_SERVER]", traced)
        self.assertIn("[COMPATBOOT][FIRST_FAILURE]", traced)
        self.assertIn("compat_uid3 == kern->get_config()->compat_target_uid3", traced)
        self.assertIn("compat_first_failure_logged.compare_exchange_strong", traced)

    def test_visible_marker_requires_menu3_window_surface(self):
        self.assertTrue(hasattr(PATCH, "patch_target_visible"), "Menu3 visibility trace is absent")
        traced = PATCH.patch_target_visible(WINUSER_CPP)
        for condition in ("compat_menu_probe_mode", "compat_target_uid3", "is_visible()", "can_be_physically_seen()"):
            self.assertIn(condition, traced)
        self.assertIn("[COMPATBOOT][TARGET_VISIBLE]", traced)

    def test_visibility_probe_uses_window_server_kernel_config_accessor(self):
        traced = PATCH.patch_target_visible(WINUSER_CPP)
        self.assertIn(
            "eka2l1::config::state *compat_cfg = client->get_ws().get_kernel_system()->get_config();",
            traced,
        )
        self.assertNotIn("ctx.sys->get_kernel_system()", traced)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
