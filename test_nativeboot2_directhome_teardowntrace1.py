#!/usr/bin/env python3
"""Contract tests for DirectHome-only teardown tracing."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(sys.argv[1]).resolve() if __name__ == "__main__" and len(sys.argv) == 2 else None
PATCHER_PATH = ROOT / "apply_nativeboot2_directhome_teardowntrace1.py"
if PATCHER_PATH.is_file():
    SPEC = importlib.util.spec_from_file_location("directhome_teardown_trace", PATCHER_PATH)
    PATCH = importlib.util.module_from_spec(SPEC)
    assert SPEC and SPEC.loader
    sys.modules[SPEC.name] = PATCH
    SPEC.loader.exec_module(PATCH)
else:
    PATCH = None


PROCESS_CPP = '''#include <kernel/kernel.h>
namespace eka2l1::kernel {
    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {
        if (exit_type != entity_exit_type::pending) {
            return;
        }

        exit_type = ext;
        exit_reason = reason;
        exit_category = category;

        while (!thread_list.empty()) {
            kernel::thread *thr = E_LOFF(thread_list.first()->deque(), kernel::thread, process_thread_link);
            if (thr->exit_type == kernel::entity_exit_type::pending) {
                thr->kill(ext, u"Domino", reason);
            }
        }

        if (!kern->wipeout_in_progress()) {
            kern->call_process_exit_callbacks(this);
            finish_logons();
            process_handles.reset();
        }

        kern->destroy(dll_lock);
    }
}
'''

KERNEL_CPP = '''#include <kernel/kernel.h>
namespace eka2l1 {
    bool kernel_system::destroy(kernel_obj_ptr obj) {
        if (!obj || wiping_) {
            return true;
        }

        switch (obj->get_object_type()) {
#define OBJECT_SEARCH(obj_type, obj_map) \\
    case kernel::object_type::obj_type: { \\
        return destroy_object_in_container(obj_map, obj); \\
    }

            OBJECT_SEARCH(prop, props_)
            OBJECT_SEARCH(prop_ref, prop_refs_)

#undef OBJECT_SEARCH

        default:
            break;
        }

        return false;
    }
}
'''

PROPERTY_CPP = '''#include <kernel/kernel.h>
namespace eka2l1::service {
        property_reference::~property_reference() {
            cancel();
        }

        bool property_reference::cancel() {
            return prop_->cancel(nof_);
        }
}
'''


class DirectHomeTeardownTraceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PATCH, "DirectHome teardown trace patcher has not been implemented")

    def test_process_kill_trace_distinguishes_accept_and_already_exiting(self):
        traced = PATCH.patch_process_kill(PROCESS_CPP)
        for needle in (
            "[COMPATBOOT][DIRECTHOME_TEARDOWN]",
            "phase=process_kill_entry",
            "phase=process_kill_decision decision=already_exiting",
            "phase=process_kill_decision decision=accepted",
            "process_ptr",
            "uid3",
            "exit_state",
            "reason",
            "native_phone_boot",
            "compat_menu_probe_mode",
            "compat_target_kind == 2",
        ):
            self.assertIn(needle, traced)
        self.assertEqual(traced.count("if (exit_type != entity_exit_type::pending)"), 1)
        self.assertEqual(traced.count("return;"), 1)
        self.assertEqual(traced.count("kern->destroy(dll_lock);"), 1)
        self.assertLess(traced.index("decision=already_exiting"), traced.index("return;"))
        self.assertLess(traced.index("decision=accepted"), traced.index("exit_type = ext;"))
        self.assertEqual(PATCH.patch_process_kill(traced), traced)

    def test_kernel_destroy_trace_identifies_property_reference(self):
        traced = PATCH.patch_kernel_destroy(KERNEL_CPP)
        self.assertIn("phase=kernel_destroy", traced)
        self.assertIn("object_ptr", traced)
        self.assertIn("object_type", traced)
        self.assertIn("static_cast<const void *>(obj)", traced)
        self.assertNotIn("obj.get()", traced)
        self.assertIn("native_phone_boot", traced)
        self.assertIn("compat_menu_probe_mode", traced)
        self.assertIn("compat_target_kind == 2", traced)
        self.assertLess(traced.index("phase=kernel_destroy"), traced.index("switch (obj->get_object_type())"))
        self.assertEqual(traced.count("OBJECT_SEARCH(prop_ref, prop_refs_)"), 1)
        self.assertEqual(traced.count("destroy_object_in_container(obj_map, obj)"), 1)
        self.assertEqual(PATCH.patch_kernel_destroy(traced), traced)

    def test_property_reference_destructor_trace_correlates_fields(self):
        traced = PATCH.patch_property_reference_destructor(PROPERTY_CPP)
        for needle in (
            "phase=property_reference_destructor",
            "object_ptr",
            "property_ptr",
            "requester_ptr",
            "guest_status",
            "nof_.sts.ptr_address()",
            "native_phone_boot",
            "compat_menu_probe_mode",
            "compat_target_kind == 2",
        ):
            self.assertIn(needle, traced)
        self.assertLess(traced.index("phase=property_reference_destructor"), traced.index("cancel();"))
        self.assertNotIn("requester_ptr->", traced)
        self.assertNotIn("property_ptr->", traced)
        self.assertEqual(traced.count("cancel();"), 1)
        self.assertEqual(PATCH.patch_property_reference_destructor(traced), traced)

    def test_property_destructor_only_reads_requester_for_initialized_status(self):
        traced = PATCH.patch_property_reference_destructor(PROPERTY_CPP)
        self.assertIn("nof_.sts.ptr_address()", traced)
        self.assertIn(
            "const bool nboot2_directhome_requester_known = nboot2_directhome_guest_status != 0",
            traced,
        )
        trace_gate = traced.index("if (nboot2_directhome_trace)")
        status_read = traced.index(
            "const auto nboot2_directhome_guest_status = static_cast<std::uint32_t>(nof_.sts.ptr_address())"
        )
        requester_read = traced.index("nof_.requester")
        self.assertLess(trace_gate, status_read)
        self.assertLess(status_read, requester_read)
        self.assertRegex(
            traced,
            r"nboot2_directhome_requester_known\s+\?\s+static_cast<const void \*>\(nof_\.requester\) : nullptr",
        )
        self.assertIn("requester_known={}", traced)

    def test_trace_patch_preserves_original_teardown_semantics(self):
        kill = PATCH.patch_process_kill(PROCESS_CPP)
        destroy = PATCH.patch_kernel_destroy(KERNEL_CPP)
        destructor = PATCH.patch_property_reference_destructor(PROPERTY_CPP)
        self.assertEqual(kill.count("return;"), PROCESS_CPP.count("return;"))
        self.assertEqual(kill.count("kern->destroy(dll_lock);"), PROCESS_CPP.count("kern->destroy(dll_lock);"))
        self.assertEqual(destroy.count("return destroy_object_in_container(obj_map, obj);"), KERNEL_CPP.count("return destroy_object_in_container(obj_map, obj);"))
        self.assertEqual(destroy.count("return false;"), KERNEL_CPP.count("return false;"))
        self.assertEqual(destructor.count("cancel();"), PROPERTY_CPP.count("cancel();"))
        for source in (kill, destroy, destructor):
            self.assertEqual(source.count("phase="), source.count("LOG_INFO("))

    def test_full_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/emu/kernel/src").mkdir(parents=True)
            (root / "src/emu/kernel/include/kernel").mkdir(parents=True)
            (root / "src/emu/kernel/src/process.cpp").write_text(PROCESS_CPP, encoding="utf-8")
            (root / "src/emu/kernel/src/kernel.cpp").write_text(KERNEL_CPP, encoding="utf-8")
            (root / "src/emu/kernel/src/property.cpp").write_text(PROPERTY_CPP, encoding="utf-8")
            PATCH.apply(root)
            after_first = {
                p: (root / p).read_text(encoding="utf-8")
                for p in (
                    "src/emu/kernel/src/process.cpp",
                    "src/emu/kernel/src/kernel.cpp",
                    "src/emu/kernel/src/property.cpp",
                )
            }
            PATCH.apply(root)
            after_second = {
                p: (root / p).read_text(encoding="utf-8")
                for p in after_first
            }
            self.assertEqual(after_first, after_second)
            self.assertTrue((root / "src/emu/kernel/include/kernel/directhome_teardown_trace.h").is_file())

    def test_supplied_upstream_root_is_checked_after_manifest_patch(self):
        if UPSTREAM_ROOT is None:
            return
        self.assertTrue(UPSTREAM_ROOT.is_dir(), f"missing upstream root: {UPSTREAM_ROOT}")
        paths = {
            "process": UPSTREAM_ROOT / "src/emu/kernel/src/process.cpp",
            "kernel": UPSTREAM_ROOT / "src/emu/kernel/src/kernel.cpp",
            "property": UPSTREAM_ROOT / "src/emu/kernel/src/property.cpp",
            "thread": UPSTREAM_ROOT / "src/emu/kernel/src/thread.cpp",
            "header": UPSTREAM_ROOT / "src/emu/kernel/include/kernel/directhome_teardown_trace.h",
        }
        for path in paths.values():
            self.assertTrue(path.is_file(), f"missing patched upstream file: {path}")
        process = paths["process"].read_text(encoding="utf-8")
        kernel = paths["kernel"].read_text(encoding="utf-8")
        prop = paths["property"].read_text(encoding="utf-8")
        thread = paths["thread"].read_text(encoding="utf-8")
        header = paths["header"].read_text(encoding="utf-8")
        self.assertEqual(process.count("phase=process_kill_entry"), 1)
        self.assertEqual(process.count("phase=process_kill_decision"), 2)
        self.assertEqual(kernel.count("phase=kernel_destroy"), 1)
        self.assertEqual(prop.count("phase=property_reference_destructor"), 1)
        self.assertNotIn("nboot2_b94_requester->name()", prop)
        self.assertRegex(
            prop,
            r"nboot2_directhome_requester_known\s+\?\s+static_cast<const void \*>\(nof_\.requester\) : nullptr",
        )
        for source in (process, kernel, prop):
            self.assertIn("compat_target_kind == 2", source)
        self.assertIn("std::atomic<std::uint64_t> sequence", header)
        self.assertIn("sts_real->set(err_code, kern->is_eka1());", thread)
        self.assertIn("sts = 0;", thread)
        self.assertIn("requester->signal_request();", thread)
        self.assertEqual(prop.count("(*subscription_iterator)->complete(epoc::error_cancel);"), 1)
        self.assertIn("subscription_queue.erase(subscription_iterator);", prop)
        self.assertEqual(PATCH.patch_process_kill(process), process)
        self.assertEqual(PATCH.patch_kernel_destroy(kernel), kernel)
        self.assertEqual(PATCH.patch_property_reference_destructor(prop), prop)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: test_nativeboot2_directhome_teardowntrace1.py [upstream-root]")
    unittest.main(argv=[sys.argv[0]])
