import unittest

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

    def test_visible_marker_accepts_either_selected_target_but_requires_real_window(self):
        visible = PATCH.patch_target_visible(baseline.WINUSER_CPP)

        for condition in ("compat_target_kind != 0", "compat_target_uid3", "is_visible()", "can_be_physically_seen()"):
            with self.subTest(condition=condition):
                self.assertIn(condition, visible)
        self.assertIn("[COMPATBOOT][TARGET_VISIBLE]", visible)


if __name__ == "__main__":
    unittest.main()
