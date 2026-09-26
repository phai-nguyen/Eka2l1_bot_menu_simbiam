#!/usr/bin/env python3
"""Source contract for B30 ROOTEDLIBPATH1.

B30 is a narrow backport of upstream EKA2L1's drive-less absolute image-path
resolution. A rooted Symbian path such as \\sys\\bin\\foo.dll has a directory
root but no drive; the loader must try drive-qualified candidates instead of
opening that path verbatim.

The first B30 device build deliberately preserves B29 LOADERDIAG1 and adds
generic B30 candidate/resolution markers. No parser, ROM/E32 classification,
dependency, SVC, or target-DLL special case belongs here.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B30-ROOTEDLIBPATH1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b30_rootedlibpath1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    ldr=up/"src/emu/services/src/loader/loader.cpp"
    cen=up/"src/emu/services/src/centralrepo/repo.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (lib,ldr,cen,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    lm=lib.read_text(encoding="utf-8")
    ls=ldr.read_text(encoding="utf-8")
    cr=cen.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # Preserve the already device-observed diagnostic and functional baseline.
    for needle in (
        "[NBOOT2][LDR_ROOT_BEGIN]",
        "[NBOOT2][LDR_ROOT_DIRECT]",
        "[NBOOT2][LDR_ROOT_MISS]",
        "[NBOOT2][LDR_OPEN_FAIL]",
        "[NBOOT2][LDR_FORMAT]",
        "[NBOOT2][LDR_PARSE_FAIL]",
        "[NBOOT2][LDR_CODESEG_RESULT]",
        "[NBOOT2][LDR_DEP_FAIL]",
    ):
        need(lm,needle,"libmanager.cpp B29 LOADERDIAG1 preservation")
    for needle in ("[NBOOT2][LDR_LIB_REQUEST]","[NBOOT2][LDR_LIB_RESULT]"):
        need(ls,needle,"loader.cpp B29 LOADERDIAG1 preservation")
    for needle in ("[NBOOT2][CEN_TX_START]","[NBOOT2][CEN_TX_COMMIT]"):
        need(cr,needle,"repo.cpp B29 preservation")
    need(sv,"[NBOOT2][WSERV_LIBRARY_TYPE]","svc.cpp B28 preservation")

    # Narrow rooted-no-drive drive resolution, matching the upstream fix's
    # lib_manager::load() behavior without importing unrelated loader changes.
    for needle in (
        "if (nativeboot2_root_diag) {",
        "for (drive_number drv = drive_a; drv <= drive_z;",
        "std::u16string candidate(1, drive_to_char16(drv));",
        "candidate += u':';",
        "candidate += lib_path;",
        "const bool candidate_exists = io_->exist(candidate);",
        "if (candidate_exists) {",
        "load_depend_on_drive(candidate, is_driver_lib)",
        "result->set_full_path(candidate);",
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_RESOLVED]",
        "[NBOOT2][LDR_ROOT_EXHAUSTED]",
    ):
        need(lm,needle,"libmanager.cpp B30 rooted-no-drive resolution")

    # The old direct VFS block stays in source for ordinary rooted paths and
    # keeps LOADERDIAG1 strings, but B30's rooted-no-drive branch must return
    # before reaching it.
    search_pos=lm.find("[NBOOT2][LDR_ROOT_CANDIDATE]")
    direct_pos=lm.find("[NBOOT2][LDR_ROOT_DIRECT]")
    if search_pos < 0 or direct_pos < 0 or search_pos >= direct_pos:
        fail("B30 drive search must precede B29 direct rooted-path block")

    # Do not silently backport the upstream ROM/E32 classification change.
    if "loader::is_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream))" in lm:
        fail("out-of-scope ROM/E32 classification backport detected")

    lower=(lm+"\n"+ls).lower()
    if "eiksrvui.dll" in lower or "0x100053d0" in lower:
        fail("target EiksrvUi DLL/UID hardcoded into generic loader fix")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
