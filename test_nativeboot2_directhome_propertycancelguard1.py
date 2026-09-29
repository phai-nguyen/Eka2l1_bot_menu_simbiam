import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PATCHER_PATH = ROOT / "apply_nativeboot2_directhome_propertycancelguard1.py"
SPEC = importlib.util.spec_from_file_location("directhome_propertycancel_guard", PATCHER_PATH)
PATCH = importlib.util.module_from_spec(SPEC) if SPEC else None
if SPEC and SPEC.loader:
    SPEC.loader.exec_module(PATCH)


PROPERTY_CPP = '''#include <kernel/kernel.h>
#include <kernel/property.h>
namespace eka2l1::service {
    bool property::cancel(const epoc::notify_info &info) {
        auto subscription_iterator = std::find(subscription_queue.begin(), subscription_queue.end(), &info);
        if (subscription_iterator == subscription_queue.end()) {
            return false;
        }
        (*subscription_iterator)->complete(epoc::error_cancel);
        subscription_queue.erase(subscription_iterator);
        return true;
    }
    void property::notify_request(const std::int32_t err) {
        (void)err;
    }
}
'''


class DirectHomePropertyCancelGuardTests(unittest.TestCase):
    def test_directhome_skips_completion_for_dead_or_exiting_requester(self):
        patched = PATCH.patch_property_cancel(PROPERTY_CPP)
        for needle in (
            "native_phone_boot",
            "compat_menu_probe_mode",
            "compat_target_kind == 2",
            "kern->get_thread_list()",
            "nboot2_directhome_candidate.get() == reinterpret_cast<kernel::kernel_obj *>(nboot2_directhome_requester)",
            "nboot2_directhome_requester->get_exit_type() == kernel::entity_exit_type::pending",
            "nboot2_directhome_process->get_exit_type() == kernel::entity_exit_type::pending",
            "decision={}",
            "requester_exit_state={}",
        ):
            self.assertIn(needle, patched)
        self.assertEqual(patched.count("(*subscription_iterator)->complete(epoc::error_cancel);"), 2)
        self.assertEqual(patched.count("subscription_queue.erase(subscription_iterator);"), 1)
        self.assertLess(
            patched.index("kern->get_thread_list()"),
            patched.index("nboot2_directhome_requester->get_exit_type()"),
        )
        self.assertEqual(PATCH.patch_property_cancel(patched), patched)

    def test_non_directhome_keeps_original_unconditional_completion(self):
        patched = PATCH.patch_property_cancel(PROPERTY_CPP)
        directhome = patched.index("if (nboot2_directhome_mode)")
        fallback = patched.index("} else {", directhome)
        original_call = patched.index("(*subscription_iterator)->complete(epoc::error_cancel);", fallback)
        self.assertGreater(original_call, fallback)
        self.assertEqual(patched.count("if (nboot2_directhome_mode)"), 1)

    def test_directhome_never_dereferences_requester_when_registry_says_dead(self):
        patched = PATCH.patch_property_cancel(PROPERTY_CPP)
        registered = patched.index("kern->get_thread_list()")
        requester_exit = patched.index("nboot2_directhome_requester->get_exit_type()")
        self.assertLess(registered, requester_exit)
        self.assertIn(
            "nboot2_directhome_registered\n                ? nboot2_directhome_requester->owning_process() : nullptr",
            patched,
        )

    def test_existing_upstream_alive_guard_remains_supported(self):
        alive_source = PROPERTY_CPP.replace(
            "        (*subscription_iterator)->complete(epoc::error_cancel);",
            "        if (kern->is_thread_alive((*subscription_iterator)->requester)) {\n"
            "            (*subscription_iterator)->complete(epoc::error_cancel);\n"
            "        }",
        )
        patched = PATCH.patch_property_cancel(alive_source)
        self.assertIn("if (kern->is_thread_alive((*subscription_iterator)->requester))", patched)
        self.assertEqual(patched.count("subscription_queue.erase(subscription_iterator);"), 1)

    def test_apply_is_idempotent_and_adds_config_include(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "src/emu/kernel/src/property.cpp"
            path.parent.mkdir(parents=True)
            path.write_text(PROPERTY_CPP, encoding="utf-8")
            self.assertTrue(PATCH.apply(root))
            after_first = path.read_text(encoding="utf-8")
            self.assertIn("#include <config/config.h>", after_first)
            self.assertFalse(PATCH.apply(root))
            self.assertEqual(path.read_text(encoding="utf-8"), after_first)


def verify_upstream(root):
    path = Path(root).resolve() / "src/emu/kernel/src/property.cpp"
    if not path.is_file():
        raise SystemExit(f"DIRECTHOME-PROPERTYCANCELGUARD1-TEST: missing {path}")
    source = path.read_text(encoding="utf-8")
    start = source.find("bool property::cancel(const epoc::notify_info &info) {")
    end = source.find("void property::notify_request(", start + 1)
    if start < 0 or end < 0:
        raise SystemExit("DIRECTHOME-PROPERTYCANCELGUARD1-TEST: cannot isolate property::cancel")
    body = source[start:end]
    for needle in (
        "[COMPATBOOT][PROP_CANCEL_GUARD]",
        "native_phone_boot",
        "compat_menu_probe_mode",
        "compat_target_kind == 2",
        "kern->get_thread_list()",
        "nboot2_directhome_candidate.get() == reinterpret_cast<kernel::kernel_obj *>(nboot2_directhome_requester)",
        "kernel::entity_exit_type::pending",
        "decision={}",
    ):
        if needle not in body:
            raise SystemExit(f"DIRECTHOME-PROPERTYCANCELGUARD1-TEST: missing {needle}")
    if body.count("(*subscription_iterator)->complete(epoc::error_cancel);") != 2:
        raise SystemExit("DIRECTHOME-PROPERTYCANCELGUARD1-TEST: completion paths changed")
    if body.count("subscription_queue.erase(subscription_iterator);") != 1:
        raise SystemExit("DIRECTHOME-PROPERTYCANCELGUARD1-TEST: subscription erase changed")
    if PATCH.patch_property_cancel(source) != source:
        raise SystemExit("DIRECTHOME-PROPERTYCANCELGUARD1-TEST: patch is not idempotent")
    print("DIRECTHOME-PROPERTYCANCELGUARD1-TEST: PASS")
    print("scope=DirectHome; non_directhome=UNCHANGED; fake_server_or_ipc=NONE")


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        verify_upstream(sys.argv.pop())
    elif len(sys.argv) != 1:
        raise SystemExit("usage: test_nativeboot2_directhome_propertycancelguard1.py [upstream-root]")
    unittest.main(argv=[sys.argv[0]])
