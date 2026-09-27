#!/usr/bin/env python3
"""Source contract for the CompatBoot-only B94 teardown diagnostics."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "b94_teardown_probe", ROOT / "apply_nativeboot2_b94_teardownprobe1.py"
)
PATCH = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = PATCH
SPEC.loader.exec_module(PATCH)


THREAD_CPP = '''#include <kernel/kernel.h>
namespace eka2l1 {
    namespace epoc {
        void notify_info::complete(int err_code) {
            if (sts.ptr_address() == 0) {
                return;
            }

            kernel_system *kern = requester->get_kernel_object_owner();

            epoc::request_status *sts_real = sts.get(requester->owning_process());
            if (sts_real)
                sts_real->set(err_code, kern->is_eka1());

            sts = 0;
            requester->signal_request();
        }
    }
}
'''

PROPERTY_CPP = '''#include <kernel/kernel.h>
namespace eka2l1::service {
    bool property::cancel(const epoc::notify_info &info) {
        auto subscription_iterator = std::find(subscription_queue.begin(), subscription_queue.end(), &info);
        if (subscription_iterator == subscription_queue.end()) {
            return false;
        }

        if (kern->is_thread_alive((*subscription_iterator)->requester)) {
            (*subscription_iterator)->complete(epoc::error_cancel);
        }

        subscription_queue.erase(subscription_iterator);
        return true;
    }
}
'''

PROCESS_CPP = '''#include <kernel/process.h>
namespace eka2l1::kernel {
    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {
        if (exit_type != entity_exit_type::pending) {
            return;
        }

        exit_type = ext;
        exit_reason = reason;
    }

    void *process::get_ptr_on_addr_space(address addr) {
        if (!mm_impl_) {
            return nullptr;
        }

        return mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);
    }
}
'''


class B94TeardownProbeTests(unittest.TestCase):
    def test_notify_patch_ignores_identical_anchor_outside_target_function(self):
        unrelated = '''
void unrelated_notify() {
            epoc::request_status *sts_real = sts.get(requester->owning_process());
            if (sts_real)
                sts_real->set(err_code, kern->is_eka1());
        }
'''
        traced = PATCH.patch_notify_complete(THREAD_CPP + unrelated)
        self.assertEqual(traced.count("sts.get("), 2)
        self.assertIn(unrelated, traced)
        self.assertEqual(PATCH.patch_notify_complete(traced), traced)

    def test_notify_trace_records_requester_and_status_translation_without_changing_completion(self):
        traced = PATCH.patch_notify_complete(THREAD_CPP)
        for needle in (
            "compat_menu_probe_mode",
            "[COMPATBOOT][NOTIFY_STATUS] phase=before_resolve",
            "[COMPATBOOT][NOTIFY_STATUS] phase=after_resolve",
            "requester_ptr",
            "requester_process",
            "requester_uid3",
            "request_status",
            "notify_status_scope",
        ):
            self.assertIn(needle, traced)
        self.assertEqual(traced.count("sts.get("), 1)
        self.assertEqual(traced.count("sts_real->set(err_code, kern->is_eka1());"), 1)
        self.assertEqual(traced.count("requester->signal_request();"), 1)
        self.assertLess(traced.index("phase=before_resolve"), traced.index("sts.get("))
        self.assertLess(traced.index("sts.get("), traced.index("phase=after_resolve"))
        self.assertEqual(PATCH.patch_notify_complete(traced), traced)

    def test_property_cancel_reuses_liveness_result_and_identifies_reference(self):
        traced = PATCH.patch_property_cancel(PROPERTY_CPP)
        for needle in (
            "[COMPATBOOT][PROP_CANCEL] phase=before_complete",
            "property_ref_ptr",
            "property_ptr",
            "requester_ptr",
            "requester_alive",
            "request_status",
            "compat_menu_probe_mode",
        ):
            self.assertIn(needle, traced)
        self.assertEqual(traced.count("kern->is_thread_alive("), 1)
        self.assertEqual(traced.count("(*subscription_iterator)->complete(epoc::error_cancel);"), 1)
        self.assertIn("if (nboot2_b94_requester_alive)", traced)
        self.assertEqual(PATCH.patch_property_cancel(traced), traced)

    def test_property_cancel_without_liveness_guard_only_logs_unknown_state(self):
        no_guard = PROPERTY_CPP.replace(
            "        if (kern->is_thread_alive((*subscription_iterator)->requester)) {\n"
            "            (*subscription_iterator)->complete(epoc::error_cancel);\n"
            "        }\n",
            "        (*subscription_iterator)->complete(epoc::error_cancel);\n",
        )
        traced = PATCH.patch_property_cancel(no_guard)
        self.assertIn("requester_alive=-1", traced)
        self.assertEqual(traced.count("kern->is_thread_alive("), 0)
        self.assertEqual(traced.count("(*subscription_iterator)->complete(epoc::error_cancel);"), 1)
        self.assertIn("subscription_queue.erase(subscription_iterator);", traced)
        self.assertEqual(PATCH.patch_property_cancel(traced), traced)

    def test_process_kill_trace_is_profile_scoped_and_before_teardown(self):
        traced = PATCH.patch_process_kill(PROCESS_CPP)
        self.assertIn("[COMPATBOOT][PROCESS_KILL] phase=begin", traced)
        self.assertIn("compat_menu_probe_mode", traced)
        self.assertIn("exit_type != entity_exit_type::pending", traced)
        self.assertLess(traced.index("phase=begin"), traced.index("exit_type = ext;"))
        self.assertEqual(PATCH.patch_process_kill(traced), traced)

    def test_address_space_trace_only_observes_scoped_notify_status_translation(self):
        traced = PATCH.patch_process_address_space(PROCESS_CPP)
        self.assertIn("notify_status_resolution_matches(this, addr)", traced)
        self.assertIn("[COMPATBOOT][NOTIFY_STATUS_MAP] phase=begin", traced)
        self.assertIn("[COMPATBOOT][NOTIFY_STATUS_MAP] phase=result", traced)
        self.assertIn("mm_impl_->address_space_id()", traced)
        self.assertEqual(traced.count("get_host_pointer(mm_impl_->address_space_id(), addr)"), 1)
        self.assertEqual(PATCH.patch_process_address_space(traced), traced)

    def test_diagnostics_do_not_touch_ipc_results_or_leave_behavior(self):
        notify = PATCH.patch_notify_complete(THREAD_CPP)
        cancel = PATCH.patch_property_cancel(PROPERTY_CPP)
        process = PATCH.patch_process_kill(PROCESS_CPP)
        translated = PATCH.patch_process_address_space(PROCESS_CPP)
        self.assertIn("sts_real->set(err_code, kern->is_eka1());", notify)
        self.assertIn("sts = 0;", notify)
        self.assertIn("requester->signal_request();", notify)
        self.assertIn("subscription_queue.erase(subscription_iterator);", cancel)
        self.assertIn("exit_reason = reason;", process)
        self.assertIn("void *nboot2_b94_host_pointer = mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);", translated)
        self.assertIn("return nboot2_b94_host_pointer;", translated)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: test_nativeboot2_b94_teardownprobe1.py [upstream-root]")
    unittest.main(argv=[sys.argv[0]])
