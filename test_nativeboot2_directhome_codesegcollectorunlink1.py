import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
PATCHER_PATH = ROOT / "apply_nativeboot2_directhome_codesegcollectorunlink1.py"


VULNERABLE_CODESEG = '''
void codeseg::free_attached_data(attached_info &info) {
    if (info.data_chunk) {
        kern->destroy(info.data_chunk);
    }
    info.closing_lib_link.deque();
    info.process_link.deque();
    attaches.erase(ite);
}
bool codeseg::detach(process *process, bool process_dead) {
    return process_dead;
}
'''


def load_patcher():
    spec = importlib.util.spec_from_file_location("codeseg_collector_unlink", PATCHER_PATH)
    if not spec or not spec.loader:
        raise AssertionError(f"cannot load patcher at {PATCHER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_upstream(root):
    source_path = Path(root).resolve() / "src/emu/kernel/src/codeseg.cpp"
    if not source_path.is_file():
        raise SystemExit(f"DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: missing {source_path}")
    source = source_path.read_text(encoding="utf-8")
    patcher = load_patcher()
    start = source.find(patcher.SIGNATURE)
    end = source.find(patcher.NEXT_FUNCTION, start + len(patcher.SIGNATURE))
    if start < 0 or end < 0:
        raise SystemExit("DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: cannot isolate free_attached_data")
    function = source[start:end]
    unlink = function.find(patcher.UNLINK)
    closing = function.find(patcher.ANCHOR)
    erase = function.find(patcher.ERASE)
    if min(unlink, closing, erase) < 0 or not (unlink < closing < erase):
        raise SystemExit("DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: unlink must precede attach teardown")
    if function.count(patcher.UNLINK) != 1:
        raise SystemExit("DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: duplicate collector unlink")
    if patcher.patch_free_attached_data(source) != source:
        raise SystemExit("DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: patch is not idempotent")
    print("DIRECTHOME-CODESEG-COLLECTOR-UNLINK1-TEST: PASS")
    print("invariant=collector_link_removed_before_attached_info_erase")


class DirectHomeCodeSegCollectorUnlinkTests(unittest.TestCase):
    def test_removes_collector_link_before_erasing_attached_info(self):
        patcher = load_patcher()
        patched = patcher.patch_free_attached_data(VULNERABLE_CODESEG)

        unlink = "kern->get_codedump_collector().remove(info);"
        self.assertEqual(patched.count(unlink), 1)
        self.assertLess(patched.index(unlink), patched.index("attaches.erase(ite);"))
        self.assertLess(patched.index(unlink), patched.index("info.closing_lib_link.deque();"))

    def test_patch_is_idempotent(self):
        patcher = load_patcher()
        patched = patcher.patch_free_attached_data(VULNERABLE_CODESEG)
        self.assertEqual(patcher.patch_free_attached_data(patched), patched)

    def test_rejects_collector_unlink_after_attach_erase(self):
        patcher = load_patcher()
        malformed = VULNERABLE_CODESEG.replace(
            "    attaches.erase(ite);",
            "    attaches.erase(ite);\n    kern->get_codedump_collector().remove(info);",
        )
        with self.assertRaises(SystemExit):
            patcher.patch_free_attached_data(malformed)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        verify_upstream(sys.argv.pop())
    elif len(sys.argv) != 1:
        raise SystemExit("usage: test_nativeboot2_directhome_codesegcollectorunlink1.py [upstream-root]")
    else:
        unittest.main()
