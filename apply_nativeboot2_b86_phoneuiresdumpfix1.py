#!/usr/bin/env python3
"""NATIVEBOOT2 B86 PHONEUIRESDUMPFIX1.

Fix B85's case-folded VPbk resource path predicate so the read-only candidate
dump runs. Do not change emulator shutdown, guest boot, panic, or registration.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B86-PHONEUIRESDUMPFIX1"
OLD_PATH = r'if (lower!=uR"(z:\resource\VPbkCntModelRes.r01)") {'
NEW_PATH = r'if (lower!=uR"(z:\resource\vpbkcntmodelres.r01)") {'
OLD_LOG_MARKER = "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP]"
NEW_LOG_MARKER = "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b86_phoneuiresdumpfix1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    files = upstream / "src/emu/services/src/fs/files.cpp"
    if not files.is_file():
        fail("B85 files.cpp is missing")

    source = files.read_text(encoding="utf-8")
    if NEW_LOG_MARKER in source:
        if (source.count(NEW_PATH) == 1
                and OLD_PATH not in source
                and OLD_LOG_MARKER not in source):
            print(MARK + ": already applied")
            return
        fail("partial B86 application detected")

    if "nboot2_b85_dump_vpbk_candidate_rsc" not in source:
        fail("B85 dump helper gate missing")
    if source.count(OLD_PATH) != 1:
        fail("expected one mixed-case B85 path predicate")
    if source.count(OLD_LOG_MARKER) != 5:
        fail("expected five B85 runtime log markers")

    source = source.replace(OLD_PATH, NEW_PATH, 1)
    source = source.replace(OLD_LOG_MARKER, NEW_LOG_MARKER)
    files.write_text(source, encoding="utf-8")

    print(MARK + ": applied")
    print("candidate_path_match=CASEFOLDED_LOWERCASE")
    print("candidate=Z:\\resource\\VPbkCntModelRes.r01")
    print("runtime_marker=PHONEUI_RESID_CANDIDATE_DUMP_B86")
    print("read_mode=SEPARATE_READ_ONLY")
    print("guest_behavior=UNCHANGED")
    print("host_exit_behavior=UNCHANGED")


if __name__ == "__main__":
    main()
