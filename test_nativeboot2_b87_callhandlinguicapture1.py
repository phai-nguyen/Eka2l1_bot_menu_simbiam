#!/usr/bin/env python3
"""B87 contract: capture the confirmed callhandlingui resource owner only."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
B87 = ROOT / "apply_nativeboot2_b87_callhandlinguicapture1.py"


class B87Contract(unittest.TestCase):
    def fixture(self, root: Path):
        files = root / "src/emu/services/src/fs/files.cpp"
        files.parent.mkdir(parents=True)
        files.write_text(
            '    static void nboot2_b85_dump_vpbk_candidate_rsc(\n'
            '        io_system *io,const std::u16string &path) {\n'
            '        const std::u16string lower=\n'
            '            common::lowercase_ucs2_string(path);\n'
            '        if (lower!=uR"(z:\\resource\\vpbkcntmodelres.r01)") {\n'
            '            return;\n'
            '        }\n'
            '        // The B84 stack contains VPbkCntModel/VPbkEng frames. Capture this\n'
            '        // exact file once through a separate read-only handle for offline\n'
            '        // resource-ID ownership analysis.\n'
            '        LOG_WARN(SERVICE_EFSRV,\n'
            '            "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86] phase=begin "\n'
            '            "owner=UNVERIFIED handle=SEPARATE_READ_ONLY");\n'
            '        LOG_WARN(SERVICE_EFSRV,\n'
            '            "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86] phase=data");\n'
            '        LOG_WARN(SERVICE_EFSRV,\n'
            '            "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86] phase=end");\n'
            '    }\n'
            '    nboot2_b85_dump_vpbk_candidate_rsc(io, *name_res);\n',
            encoding="utf-8",
        )
        # Mirror the five B86 marker occurrences enforced by the build patch.
        with files.open("a", encoding="utf-8") as stream:
            stream.write(
                '    const char *b86_open_fail = "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86]";\n'
                '    const char *b86_empty = "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86]";\n'
            )
        return files

    def test_targets_both_rom_locale_files_and_keeps_capture_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = self.fixture(root)
            subprocess.run([sys.executable, str(B87), str(root)], check=True)
            source = files.read_text(encoding="utf-8")
            self.assertIn(r'z:\resource\apps\callhandlingui.r01', source)
            self.assertIn(r'z:\resource\apps\callhandlingui.r96', source)
            self.assertIn("PHONEUI_RESID_CANDIDATE_DUMP_B87", source)
            self.assertIn("SEPARATE_READ_ONLY", source)
            self.assertIn("owner=callhandlingui", source)
            self.assertNotIn("vpbkcntmodelres.r01", source)
            subprocess.run([sys.executable, str(B87), str(root)], check=True)

    def test_refuses_when_b86_capture_contract_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = root / "src/emu/services/src/fs/files.cpp"
            files.parent.mkdir(parents=True)
            files.write_text("unrelated source\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(B87), str(root)], text=True, capture_output=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected B85 helper", result.stderr + result.stdout)


if __name__ == "__main__":
    if len(sys.argv) == 2 and Path(sys.argv[1]).is_dir():
        sys.argv = [sys.argv[0]]
    unittest.main()
