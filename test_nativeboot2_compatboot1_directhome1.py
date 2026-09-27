import unittest
import sys
from pathlib import Path

import test_nativeboot2_compatboot1_menuprobe1 as baseline


PATCH = baseline.PATCH


class DirectHomeSelectionContracts(unittest.TestCase):
    def test_emulator_action_sheet_keeps_native_default_and_adds_explicit_targets(self):
        routed = PATCH.patch_emulator_choice(baseline.ROOT_VIEW)

        self.assertEqual(routed.count("[choice addAction:"), 4)
        self.assertIn('actionWithTitle:EKAL(@"Native Boot")', routed)
        self.assertIn('actionWithTitle:EKAL(@"CompatBoot Menu Probe")', routed)
        self.assertIn('actionWithTitle:EKAL(@"CompatBoot vào Home")', routed)
        self.assertIn("start_native_phone()", routed)
        self.assertIn("startEmulatorWithCompatTarget:static_cast<NSInteger>(eka2l1::ios::bridge::compatboot_target::menu3_probe)", routed)
        self.assertIn("startEmulatorWithCompatTarget:static_cast<NSInteger>(eka2l1::ios::bridge::compatboot_target::direct_home)", routed)
        self.assertIn("start_compat_boot(", routed)
        self.assertIn("static_cast<eka2l1::ios::bridge::compatboot_target>(compatTarget)", routed)

    def test_direct_home_only_runs_from_its_explicit_menu_handler(self):
        routed = PATCH.patch_emulator_choice(baseline.ROOT_VIEW)
        self.assertIn('actionWithTitle:EKAL(@"CompatBoot vào Home")', routed)
        action = routed.index('actionWithTitle:EKAL(@"CompatBoot vào Home")')
        handler = routed.index("handler:^(UIAlertAction *) {", action)
        call = routed.index(
            "startEmulatorWithCompatTarget:static_cast<NSInteger>(eka2l1::ios::bridge::compatboot_target::direct_home)",
            handler,
        )
        next_action = routed.find("[choice addAction:", action + 1)

        self.assertGreater(call, handler)
        self.assertTrue(next_action < 0 or call < next_action)
        self.assertIn('actionWithTitle:EKAL(@"Cancel")', routed)

    def test_target_bridge_preserves_native_api_and_exposes_explicit_target_values(self):
        header = PATCH.patch_bridge_header(baseline.BRIDGE_H)

        self.assertIn("bool start_native_phone();", header)
        self.assertIn("enum class compatboot_target", header)
        self.assertIn("menu3_probe = 1", header)
        self.assertIn("direct_home = 2", header)
        self.assertIn("bool start_compat_boot(compatboot_target target);", header)

    def test_direct_home_menu_label_has_vietnamese_localization(self):
        localized = PATCH.patch_localization('            @"Add Mode" : @"Thêm chế độ",\n')

        self.assertIn('@"CompatBoot vào Home" : @"CompatBoot vào Home"', localized)
        self.assertEqual(PATCH.patch_localization(localized), localized)

    def test_runtime_target_is_transient_and_reset_on_native_rollback_and_stop(self):
        state = PATCH.patch_state_header(baseline.STATE_H)
        bridge = PATCH.patch_bridge_cpp(baseline.BRIDGE_CPP)

        self.assertIn("bool native_phone_mode = false;", state)
        self.assertIn("int compat_target_kind = 0;", state)
        self.assertIn("g_state->compat_target_kind = g_compat_target_kind", bridge)
        self.assertIn("g_compat_target_kind = static_cast<int>(target);", bridge)
        self.assertIn("target == compatboot_target::direct_home", bridge)
        self.assertIn('"direct_home" : "menu3_probe"', bridge)
        self.assertIn("[COMPATBOOT][MODE] explicit=1 profile={}", bridge)
        self.assertGreaterEqual(bridge.count("g_compat_target_kind = 0;"), 3)
        self.assertIn("g_compat_target_kind = 0;", bridge[bridge.index("bool start_native_phone()") :])
        self.assertIn("g_compat_target_kind = 0;", bridge[bridge.index("void stop_native_phone()") :])

    def test_service_barrier_selects_one_real_target_and_logs_both_launch_failures(self):
        svc = PATCH.patch_svc(baseline.SVC_CPP)

        self.assertIn("cfg->compat_target_kind == 2", svc)
        self.assertIn('u"Z:\\\\sys\\\\bin\\\\ailaunch.exe"', svc)
        self.assertIn('u"Z:\\\\sys\\\\bin\\\\menu3.exe"', svc)
        self.assertEqual(svc.count("spawn_new_process("), 1)
        self.assertIn("target={} path={} result=CREATE_FAILED", svc)
        self.assertIn("target={} path={} result=RUN_FAILED", svc)
        self.assertIn("target={} path={} result=RUNNING", svc)
        self.assertIn("compat_target_uid3 = static_cast<std::uint32_t>", svc)
        self.assertIn("[COMPATBOOT][FIRST_FAILURE] source=TARGET_CREATE", svc)
        self.assertIn("[COMPATBOOT][FIRST_FAILURE] source=TARGET_RUN", svc)

    def test_barrier_requires_selected_target_and_timeout_path_never_spawns(self):
        svc = PATCH.patch_svc(baseline.SVC_CPP)
        state = PATCH.patch_state_cpp(baseline.STATE_CPP)
        self.assertIn("cfg->compat_target_kind == 0 || cfg->compat_menu_probe_finished", svc)
        missing = svc.index("if (!missing.empty())")
        ready = svc.index('[COMPATBOOT][BARRIER_READY]')
        spawn = svc.index("spawn_new_process(")

        self.assertLess(missing, ready)
        self.assertLess(ready, spawn)
        self.assertIn("if (!missing.empty())", svc[missing:ready])
        self.assertIn("return;", svc[missing:ready])
        self.assertIn("compat_target_kind != 0", state)
        self.assertIn("[COMPATBOOT][BARRIER_TIMEOUT]", state)

    def test_menu3_diagnostics_are_limited_to_menu3_target(self):
        leave = PATCH.patch_menu3_leave5(baseline.LEAVE_START_CPP)
        flush = PATCH.patch_menu3_file_flush(baseline.FS_FLUSH_CPP)
        missing = PATCH.patch_missing_server(baseline.MISSING_SERVER_CPP)

        self.assertIn("compat_leave_cfg->compat_target_kind == 1", leave)
        self.assertIn("compat_menu_flush_cfg->compat_target_kind == 1", flush)
        self.assertIn("compat_target_kind != 0", missing)
        self.assertIn("[COMPATBOOT][FIRST_FAILURE]", missing)

    def test_visible_marker_is_direct_home_only_and_requires_real_window(self):
        visible = PATCH.patch_target_visible(baseline.WINUSER_CPP)

        for condition in ("compat_target_kind == 2", "compat_target_uid3", "is_visible()", "can_be_physically_seen()"):
            with self.subTest(condition=condition):
                self.assertIn(condition, visible)
        self.assertNotIn("compat_target_kind != 0", visible)
        self.assertIn("[COMPATBOOT][TARGET_VISIBLE]", visible)

    def test_combined_svc_patch_keeps_missing_server_trace_and_is_idempotent(self):
        combined = PATCH.patch_missing_server(PATCH.patch_svc(baseline.SVC_CPP))

        self.assertIn("[COMPATBOOT][MISSING_SERVER]", combined)
        self.assertIn("[COMPATBOOT][FIRST_FAILURE] source=MISSING_SERVER", combined)
        self.assertEqual(
            combined.count("[COMPATBOOT][MISSING_SERVER]"),
            PATCH.patch_missing_server(combined).count("[COMPATBOOT][MISSING_SERVER]"),
        )

    def test_timeout_uses_same_server_readiness_predicate_as_barrier(self):
        svc = PATCH.patch_svc(baseline.SVC_CPP)
        state = PATCH.patch_state_cpp(baseline.STATE_CPP)

        self.assertIn("std::string compatboot1_missing_services(kernel_system *kern, config::state *cfg)", state)
        self.assertIn("compatboot1_missing_services(compat_kern, compat_cfg)", state)
        self.assertIn("[COMPATBOOT][BARRIER_TIMEOUT] missing={}", state)
        self.assertIn("registered->is_hle() || guest_ready", svc)
        self.assertNotIn("missing_or_unobserved", state)

    def test_timeout_registration_failure_fails_barrier_closed(self):
        state = PATCH.patch_state_cpp(baseline.STATE_CPP)

        failure_branch = state[state.index("if (compat_event >= 0)"):state.index("LOG_WARN(FRONTEND_CMDLINE,\n                                    \"[COMPATBOOT][DEADLINE_START]")]
        self.assertIn("conf.compat_menu_probe_finished = true;", failure_branch)
        self.assertIn("conf.compat_menu_probe_timed_out = true;", failure_branch)
        self.assertIn("[COMPATBOOT][BARRIER_TIMEOUT_REGISTER_FAIL]", failure_branch)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
