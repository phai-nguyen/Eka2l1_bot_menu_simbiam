import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PATCHER_PATH = ROOT / "apply_nativeboot2_directhome_halpagesizeguard1.py"


def load_patcher():
    spec = importlib.util.spec_from_file_location("hal_page_size_guard", PATCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_upstream(upstream: Path):
    patcher = load_patcher()
    hal = (upstream / "src/emu/system/src/hal.cpp").read_text()
    svc = (upstream / "src/emu/kernel/src/svc.cpp").read_text()
    assert patcher.PAGE_SIZE_AFTER in hal
    assert patcher.BRIDGE_AFTER in svc
    assert svc.count("#include <atomic>\n") == 1
    assert patcher.patch_once(hal, patcher.PAGE_SIZE_BEFORE, patcher.PAGE_SIZE_AFTER, "hal.cpp") == hal
    assert patcher.patch_once(svc, patcher.BRIDGE_BEFORE, patcher.BRIDGE_AFTER, "svc.cpp") == svc
    print("DIRECTHOME-HAL-PAGESIZE-GUARD1-TEST: PASS")


class HalPageSizeGuardTests(unittest.TestCase):
    def test_null_destination_returns_argument_error_and_valid_destination_writes_page_size(self):
        patcher = load_patcher()
        original = patcher.PAGE_SIZE_BEFORE + "            return epoc::error_none;\n        }\n"
        patched = patcher.patch_once(original, patcher.PAGE_SIZE_BEFORE, patcher.PAGE_SIZE_AFTER, "hal.cpp")
        method = patched.replace("sys->get_memory_system()->get_page_size()", "4096")
        program = """#include <cassert>
#include <cstdint>
namespace epoc { constexpr int error_argument = -6; constexpr int error_none = 0; }
struct TestHal {
""" + method + """};
int main() {
    TestHal hal;
    int value = -1;
    assert(hal.page_size(nullptr, nullptr, 0) == epoc::error_argument);
    assert(hal.page_size(&value, nullptr, 0) == epoc::error_none);
    assert(value == 4096);
}
"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "test.cpp"
            binary = Path(directory) / "test"
            source.write_text(program)
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Werror", str(source), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_bridge_diagnostic_is_bounded_and_keeps_other_hal_calls_unchanged(self):
        patcher = load_patcher()
        patched = patcher.patch_once(patcher.BRIDGE_BEFORE, patcher.BRIDGE_BEFORE, patcher.BRIDGE_AFTER, "svc.cpp")
        self.assertIn("reported_bad_page_size_destination.exchange(true)", patched)
        self.assertIn("cage == 0 && func == 7 && !arg1", patched)
        self.assertIn("guest_a1=0x{:08X}", patched)
        self.assertTrue(patched.rstrip().endswith("return do_hal(kern->get_system(), cage, func, arg1, arg2);"))
        self.assertEqual(patcher.patch_once(patched, patcher.BRIDGE_BEFORE, patcher.BRIDGE_AFTER, "svc.cpp"), patched)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        verify_upstream(Path(sys.argv[1]))
    else:
        unittest.main()
