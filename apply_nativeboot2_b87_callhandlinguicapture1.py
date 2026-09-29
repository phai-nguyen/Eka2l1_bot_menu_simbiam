#!/usr/bin/env python3
"""NATIVEBOOT2 B87 CALLHANDLINGUICAPTURE1.

Retarget B86's read-only candidate capture from VPbk to the ROM resource file
that owns PhoneUI resource ID 0x1099B02D. No guest registration or boot change.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B87-CALLHANDLINGUICAPTURE1"
OLD_FN = "nboot2_b85_dump_vpbk_candidate_rsc"
NEW_FN = "nboot2_b87_dump_callhandling_candidate_rsc"
OLD_PATH = r'if (lower!=uR"(z:\resource\vpbkcntmodelres.r01)") {'
NEW_PATH = (
    r'if (lower!=uR"(z:\resource\apps\callhandlingui.r01)"' + "\n"
    + r'                && lower!=uR"(z:\resource\apps\callhandlingui.r96)") {'
)
OLD_MARKER = "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86]"
NEW_MARKER = "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B87]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b87_callhandlinguicapture1.py <upstream-root>")

    files = Path(sys.argv[1]).resolve() / "src/emu/services/src/fs/files.cpp"
    if not files.is_file():
        fail("FASTBUILD upstream files.cpp is missing")
    source = files.read_text(encoding="utf-8")

    if NEW_MARKER in source:
        if (source.count(NEW_PATH) == 1
                and source.count(NEW_FN) == 2
                and OLD_MARKER not in source
                and OLD_PATH not in source):
            print(MARK + ": already applied")
            return
        fail("partial B87 application detected")

    if source.count(OLD_FN) != 2:
        fail("expected B85 helper definition and call exactly once each")
    if source.count(OLD_PATH) != 1:
        fail("expected the B86 VPbk path predicate exactly once")
    if source.count(OLD_MARKER) != 5:
        fail("expected the five B86 capture log markers")

    source = source.replace(OLD_FN, NEW_FN)
    source = source.replace(OLD_PATH, NEW_PATH, 1)
    source = source.replace(OLD_MARKER, NEW_MARKER)
    source = source.replace(
        "// The B84 stack contains VPbkCntModel/VPbkEng frames. Capture this\n"
        "        // exact file once through a separate read-only handle for offline\n"
        "        // resource-ID ownership analysis.",
        "// RM-356 RPKG confirms UID3 0x1099B and resource index 0x02D\n"
        "        // belong to callhandlingui. Capture either installed locale once\n"
        "        // through a separate read-only handle; do not alter guest state.",
    )
    source = source.replace("owner=UNVERIFIED", "owner=callhandlingui")
    files.write_text(source, encoding="utf-8")

    print(MARK + ": applied")
    print("resource_id=0x1099B02D")
    print("owner=callhandlingui; uid3=0x1099B; resource_count=46")
    print("candidate_paths=Z:\\resource\\apps\\callhandlingui.r01|r96")
    print("read_mode=SEPARATE_READ_ONLY")
    print("guest_registration=UNCHANGED")
    print("boot_behavior=UNCHANGED")


if __name__ == "__main__":
    main()
