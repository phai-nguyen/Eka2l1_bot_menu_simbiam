#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "tools" / "rm356_firmware_probe.py"
SPEC = importlib.util.spec_from_file_location("rm356_firmware_probe", MODULE_PATH)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)


class RM356FirmwareProbeTests(unittest.TestCase):
    def test_cenrep_key9_classification(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "102818E8.txt"
            p.write_text(
                "cenrep\n0x00000009 int 0x7fffffff 0\n",
                encoding="utf-8",
            )
            got = mod.parse_key9(p)
            self.assertTrue(got["found"])
            self.assertEqual(got["hex_u32"], "0x7FFFFFFF")
            self.assertEqual(got["classification"], "KMaxTInt/theme-effects-disabled")

            p.write_text("0x00000009 int 0x8 0\n", encoding="utf-8")
            got = mod.parse_key9(p)
            self.assertEqual(got["classification"], "enabled-default")

    def test_scan_and_compare(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "A"
            b = root / "B"
            for fw in (a, b):
                (fw / "private" / "10202BE9").mkdir(parents=True)
                (fw / "sys" / "bin").mkdir(parents=True)
                (fw / "private" / "10202BE9" / "102818E8.txt").write_text(
                    "0x00000009 int 0x8 0\n", encoding="utf-8"
                )
                (fw / "sys" / "bin" / "AknSkinSrv.exe").write_bytes(b"same")

            scan_a = mod.scan_root("A", a)
            scan_b = mod.scan_root("B", b)
            self.assertIn("themes_cenrep_102818e8", scan_a["hits"])
            self.assertIn("aknskinsrv.exe", scan_a["hits"])
            comp = mod.compare([scan_a, scan_b])
            self.assertTrue(comp["aknskinsrv.exe"]["present_in_all"])
            self.assertTrue(comp["aknskinsrv.exe"]["identical_sha256_sets"])

            (b / "sys" / "bin" / "AknSkinSrv.exe").write_bytes(b"different")
            scan_b2 = mod.scan_root("B", b)
            comp2 = mod.compare([scan_a, scan_b2])
            self.assertFalse(comp2["aknskinsrv.exe"]["identical_sha256_sets"])


if __name__ == "__main__":
    unittest.main()
