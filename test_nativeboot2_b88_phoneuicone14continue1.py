import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "apply_nativeboot2_b88_phoneuicone14continue1.py"
SPEC = importlib.util.spec_from_file_location("b88_patch", SCRIPT)
PATCH = importlib.util.module_from_spec(SPEC)
if SPEC and SPEC.loader:
    SPEC.loader.exec_module(PATCH)


SVC_SOURCE = r'''#include <kernel/kernel.h>
namespace eka2l1::kernel::svc {
    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h,
        kernel::entity_exit_type etype, std::int32_t reason,
        eka2l1::ptr<desc8> reason_des) {
        thread_ptr thr = kern->get<kernel::thread>(h);
        std::string exit_category = "None";
        kernel::process *pr = kern->crr_process();
        kernel::thread *caller_thr = kern->crr_thread();
        kernel::process *caller_pr = kern->crr_process();
        kernel::process *target_pr = thr->owning_process();
        auto *cpu = kern->get_cpu();
        const std::uint32_t nboot2_b71_target_uid3 = target_pr
            ? static_cast<std::uint32_t>(
                std::get<2>(target_pr->get_uid_type())) : 0;
        const bool nboot2_b71_phoneui_cone14 =
            target_pr && nboot2_b71_target_uid3 == 0x100058B3U &&
            reason == 14 && exit_category == "CONE";
        if (nboot2_b71_phoneui_cone14) {
            LOG_WARN(KERNEL, "[NBOOT2][CONE14_PHONEUI] confirmed");
        }
        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);
    }
}
'''


class B88PhoneUiContinueTests(unittest.TestCase):
    def make_tree(self, source=SVC_SOURCE):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        svc = root / "src/emu/kernel/src/svc.cpp"
        fs = root / "src/emu/services/src/fs/files.cpp"
        svc.parent.mkdir(parents=True)
        fs.parent.mkdir(parents=True)
        svc.write_text(source, encoding="utf-8")
        fs.write_text(
            '[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B87] owner=callhandlingui\n',
            encoding="utf-8",
        )
        return temp, root, svc

    def test_only_confirmed_telephone_cone14_is_reclassified_for_startup(self):
        temp, root, svc = self.make_tree()
        with temp:
            PATCH.apply(root)
            changed = svc.read_text(encoding="utf-8")
            self.assertIn("[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]", changed)
            self.assertIn("== 0x100058B3U", changed)
            self.assertIn("uid3=0x{:08X}", changed)
            self.assertIn("reason==14", changed.replace(" ", ""))
            self.assertIn('exit_category=="CONE"', changed.replace(" ", ""))
            self.assertIn("kernel::entity_exit_type::terminate", changed)
            self.assertIn("reason=0", changed.replace(" ", ""))
            self.assertEqual(changed.count("thr->kill("), 1)
            self.assertLess(
                changed.index("[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]"),
                changed.index("thr->kill("),
            )

    def test_patch_is_idempotent_and_refuses_missing_b87_evidence(self):
        temp, root, svc = self.make_tree()
        with temp:
            PATCH.apply(root)
            first = svc.read_text(encoding="utf-8")
            PATCH.apply(root)
            self.assertEqual(svc.read_text(encoding="utf-8"), first)

        temp, root, _ = self.make_tree(source=SVC_SOURCE.replace(
            "[NBOOT2][CONE14_PHONEUI]", "[NBOOT2][CONE14_OTHER]"
        ))
        with temp:
            with self.assertRaises(SystemExit):
                PATCH.apply(root)


if __name__ == "__main__":
    unittest.main()
