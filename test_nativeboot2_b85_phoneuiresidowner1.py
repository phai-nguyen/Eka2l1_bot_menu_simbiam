#!/usr/bin/env python3
"""Contract for B85's evidence-only PhoneUI resource provenance correction."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
APPLY = ROOT / "apply_nativeboot2_b85_phoneuiresidowner1.py"


class B85Contract(unittest.TestCase):
    def fixture(self, root: Path):
        svc = root / "src/emu/kernel/src/svc.cpp"
        svc.parent.mkdir(parents=True)
        svc.write_text(
            '[NBOOT2][PHONEUI_RESID_SOURCE] source=REGISTER '
            'owner=callhandlingui.r01\n'
            '[NBOOT2][PHONEUI_RESID_SUMMARY] '
            'resource_registration=UNCHANGED boot_behavior=UNCHANGED\n',
            encoding="utf-8",
        )
        files = root / "src/emu/services/src/fs/files.cpp"
        files.parent.mkdir(parents=True)
        files.write_text(
            '    static void nboot2_b71_dump_phoneui_rsc(io_system *io,\n'
            '        const std::u16string &path) {}\n'
            '        nboot2_b71_dump_phoneui_rsc(io, *name_res);\n',
            encoding="utf-8",
        )
        return svc, files

    def test_applies_read_only_candidate_dump_and_removes_unverified_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svc, files = self.fixture(root)
            subprocess.run([sys.executable, str(APPLY), str(root)], check=True)
            s = svc.read_text(encoding="utf-8")
            f = files.read_text(encoding="utf-8")
            self.assertIn("source=CPU_REGISTER", s)
            self.assertIn("owner=UNVERIFIED", s)
            self.assertNotIn("owner=callhandlingui.r01", s)
            self.assertIn("nboot2_b85_dump_vpbk_candidate_rsc(io, *name_res);", f)
            self.assertIn(r'uR"(z:\resource\VPbkCntModelRes.r01)"', f)
            self.assertIn("SEPARATE_READ_ONLY", f)
            self.assertIn("0x1099B02D", f)
            self.assertNotIn("write_file(", f)
            self.assertLess(f.index("if (!probe || !probe->valid())"),
                            f.index("captured=true;"))
            subprocess.run([sys.executable, str(APPLY), str(root)], check=True)

    def test_refuses_missing_b84_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svc, files = self.fixture(root)
            svc.write_text("[NBOOT2][PHONEUI_RESID_SOURCE]\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(APPLY), str(root)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("B84 evidence gate missing", result.stderr + result.stdout)


if __name__ == "__main__":
    # FASTBUILD invokes each manifest test with the upstream checkout path.
    # This contract suite uses temporary source fixtures, so consume the
    # manifest argument before unittest parses argv as test selectors.
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
