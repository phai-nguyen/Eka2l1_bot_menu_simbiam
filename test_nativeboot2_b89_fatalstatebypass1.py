#!/usr/bin/env python3
"""Contract tests for B89's narrowly scoped fatal-startup state bypass."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "b89_patch", ROOT / "apply_nativeboot2_b89_fatalstatebypass1.py"
)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


SVC = r'''namespace eka2l1::kernel::svc {
    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h,
        kernel::entity_exit_type etype, std::int32_t reason,
        eka2l1::ptr<desc8> reason_des) {
        if (nboot2_b71_phoneui_cone14) {
            LOG_WARN(KERNEL, "[NBOOT2][CONE14_PHONEUI]");
        }
        // B88 intentionally lets native startup continue after the one
        // proven Telephone/PhoneUI CONE 14 resource panic. This does not
        // repair the missing guest resource; all other exits are unchanged.
        if (nboot2_b71_phoneui_cone14) {
            LOG_WARN(KERNEL, "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88] phase=before");
            etype = kernel::entity_exit_type::terminate;
            exit_category = "None";
            reason = 0;
            LOG_WARN(KERNEL, "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88] phase=after");
        }
        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);
    }

    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
        const std::int32_t nboot2_b58_before = prop->get_int();
        const bool res = prop->set_int(value);
        const std::int32_t nboot2_b58_after = prop->get_int();
        LOG_WARN(KERNEL, "[NBOOT2][STARTER_GLOBAL_STATE]");
    }

    BRIDGE_FUNC(std::int32_t, property_find_set_bin, std::int32_t cage,
        std::int32_t key, eka2l1::ptr<desc8> value) {
    }
}
'''


class B89FatalStateBypassTests(unittest.TestCase):
    def test_rewrites_only_sysstart_101_to_fatal_116_after_b88_phone_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = root / "src/emu/kernel/src/svc.cpp"
            svc.parent.mkdir(parents=True)
            svc.write_text(SVC, encoding="utf-8")

            PATCH.apply(root)
            changed = svc.read_text(encoding="utf-8")

            self.assertIn("[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]", changed)
            self.assertIn("nboot2_b89_phoneui_bypass_seen() = true", changed)
            self.assertIn("nboot2_b89_effective = 109", changed)
            self.assertIn("nboot2_b58_before == 101", changed)
            self.assertIn("value == 116", changed)
            self.assertIn("uid3 == 0x100059C9U", changed)
            self.assertIn("prop->set_int(nboot2_b89_effective)", changed)
            self.assertIn("[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]", changed)

    def test_patch_is_idempotent_and_requires_b88_and_b62_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = root / "src/emu/kernel/src/svc.cpp"
            svc.parent.mkdir(parents=True)
            svc.write_text(SVC, encoding="utf-8")
            PATCH.apply(root)
            first = svc.read_text(encoding="utf-8")
            PATCH.apply(root)
            self.assertEqual(svc.read_text(encoding="utf-8"), first)

        for source in (
            SVC.replace("PHONEUI_CONE14_CONTINUE_B88", "B88_REMOVED"),
            SVC.replace("STARTER_GLOBAL_STATE", "B62_REMOVED"),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                svc = root / "src/emu/kernel/src/svc.cpp"
                svc.parent.mkdir(parents=True)
                svc.write_text(source, encoding="utf-8")
                with self.assertRaises(SystemExit):
                    PATCH.apply(root)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
