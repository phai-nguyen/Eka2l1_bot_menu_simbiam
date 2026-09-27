#!/usr/bin/env python3
"""Contract tests for the narrowly scoped B91 IPC teardown neutralization."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "b91_patch", ROOT / "apply_nativeboot2_b91_ipcteardown1.py"
)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


KERNEL = r'''namespace eka2l1 {
    void kernel_system::wipeout() {
        wiping_ = true;
        OBJECT_CONTAINER_CLEANUP(sessions_);
        OBJECT_CONTAINER_CLEANUP(servers_);
        OBJECT_CONTAINER_CLEANUP(timers_);
        for (std::size_t i = 0; i < msgs_.size(); i++) {
            msgs_[i].reset();
        }
        OBJECT_CONTAINER_CLEANUP_KEEP_OBJECTS(threads_);
    }
}
'''
KERNEL = KERNEL.replace(
    "            msgs_[i].reset();\n",
    "            msgs_[i].reset();" + (" " * 3) + "\n",
)


class B91IpcTeardownTests(unittest.TestCase):
    def test_neutralizes_each_message_before_reset_after_sessions_are_gone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "src/emu/kernel/src/kernel.cpp"
            kernel.parent.mkdir(parents=True)
            kernel.write_text(KERNEL, encoding="utf-8")

            PATCH.apply(root)
            patched = kernel.read_text(encoding="utf-8")
            session_destroy = patched.index("OBJECT_CONTAINER_CLEANUP(sessions_);")
            neutralize = patched.index("own_thr = nullptr;", session_destroy)
            reset = patched.index("msgs_[i].reset();", neutralize)
            thread_destroy = patched.index("OBJECT_CONTAINER_CLEANUP_KEEP_OBJECTS(threads_);")

            self.assertLess(session_destroy, neutralize)
            self.assertLess(neutralize, reset)
            self.assertLess(reset, thread_destroy)
            self.assertIn("msg_session = nullptr;", patched[neutralize:reset])
            self.assertIn("ref_count = 0;", patched[neutralize:reset])
            self.assertEqual(patched.count("msgs_[i].reset();"), 1)

    def test_patch_is_idempotent_and_rejects_an_unexpected_teardown_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "src/emu/kernel/src/kernel.cpp"
            kernel.parent.mkdir(parents=True)
            kernel.write_text(KERNEL, encoding="utf-8")
            PATCH.apply(root)
            first = kernel.read_text(encoding="utf-8")
            PATCH.apply(root)
            self.assertEqual(kernel.read_text(encoding="utf-8"), first)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "src/emu/kernel/src/kernel.cpp"
            kernel.parent.mkdir(parents=True)
            kernel.write_text(KERNEL.replace("sessions_", "removed_sessions_"), encoding="utf-8")
            with self.assertRaises(SystemExit):
                PATCH.apply(root)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
