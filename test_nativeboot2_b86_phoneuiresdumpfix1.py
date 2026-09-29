#!/usr/bin/env python3
"""B86 contract: the B85 VPbk capture predicate must match case-folded paths."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
B85 = ROOT / "apply_nativeboot2_b85_phoneuiresidowner1.py"
B86 = ROOT / "apply_nativeboot2_b86_phoneuiresdumpfix1.py"


class B86Contract(unittest.TestCase):
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
        return files

    def test_corrects_casefolded_candidate_match_and_marks_b86(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self.fixture(root)
            subprocess.run([sys.executable, str(B85), str(root)], check=True)
            subprocess.run([sys.executable, str(B86), str(root)], check=True)
            source = files.read_text(encoding="utf-8")
            self.assertIn(r'uR"(z:\resource\vpbkcntmodelres.r01)"', source)
            self.assertNotIn(r'uR"(z:\resource\VPbkCntModelRes.r01)"', source)
            self.assertIn("PHONEUI_RESID_CANDIDATE_DUMP_B86", source)
            self.assertNotIn("PHONEUI_RESID_RSC_CANDIDATE_DUMP]", source)
            subprocess.run([sys.executable, str(B86), str(root)], check=True)

    def test_refuses_when_b85_dump_gate_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self.fixture(root)
            files.write_text("no B85 dump helper here\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(B86), str(root)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("B85 dump helper gate missing", result.stderr + result.stdout)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
