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
        self.assertGreaterEqual(bridge.count("g_compat_target_kind = 0;"), 3)
        self.assertIn("g_compat_target_kind = 0;", bridge[bridge.index("bool start_native_phone()") :])
        self.assertIn("g_compat_target_kind = 0;", bridge[bridge.index("void stop_native_phone()") :])


if __name__ == "__main__":
    unittest.main()
