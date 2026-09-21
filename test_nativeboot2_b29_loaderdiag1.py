#!/usr/bin/env python3
"""Source contract for B29-LOADERDIAG1.

Diagnostic-only instrumentation for rooted RLibrary loads. It must distinguish:
- loader request path;
- per-drive rooted candidate existence;
- file open;
- ROM/E32 classification;
- parser failure;
- ROFS staging failure;
- image->codeseg result;
- first missing E32 dependency;
- final loader success/failure.

No loader semantics or EiksrvUi-specific hardcode is allowed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B29-LOADERDIAG1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b29_loaderdiag1.py <upstream-root>")

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

    # Preserve device-validated B29/B28 baselines.
    for needle in (
        "[NBOOT2][CEN_TX_START]",
        "[NBOOT2][CEN_TX_COMMIT]",
    ):
        need(cr,needle,"repo.cpp B29 preservation")
    need(sv,"[NBOOT2][WSERV_LIBRARY_TYPE]","svc.cpp B28 preservation")

    # Loader-service request/result boundary.
    for needle in (
        "[NBOOT2][LDR_LIB_REQUEST]",
        "[NBOOT2][LDR_LIB_RESULT]",
        "request_path=",
        "process=",
        "completion=",
    ):
        need(ls,needle,"loader.cpp")

    # lib_manager path/format/parser/staging/codeseg boundaries.
    for needle in (
        "[NBOOT2][LDR_ROOT_BEGIN]",
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_MISS]",
        "[NBOOT2][LDR_OPEN_FAIL]",
        "[NBOOT2][LDR_FORMAT]",
        "[NBOOT2][LDR_PARSE_FAIL]",
        "[NBOOT2][LDR_STAGE_FAIL]",
        "[NBOOT2][LDR_CODESEG_RESULT]",
        "[NBOOT2][LDR_DEP_FAIL]",
        "exists=",
        "is_e32=",
        "is_rom=",
        "in_rom=",
        "format=",
        "dependency=",
        "parent=",
    ):
        need(lm,needle,"libmanager.cpp")

    # Diagnostics must stay generic.
    lower=(lm+"\n"+ls).lower()
    if "eiksrvui.dll" in lower:
        fail("EiksrvUi.dll hardcoded into generic loader diagnostics")
    if "0x100053d0" in lower:
        fail("EiksrvUi UID hardcoded into generic loader diagnostics")

    # Original loader decisions must remain present.
    for needle in (
        "if (io_->exist(candidate))",
        "loader::parse_romimg",
        "loader::parse_e32img",
        "return load_as_romimg(*romimg, lib_path, is_driver_lib);",
        "return load_as_e32img(*e32img, lib_path);",
    ):
        need(lm,needle,"libmanager.cpp semantic preservation")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
