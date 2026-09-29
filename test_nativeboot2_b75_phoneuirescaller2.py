#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B75 PHONEUIRESCALLER2."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B75-PHONEUIRESCALLER2-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b75_phoneuirescaller2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    corrected_phone = r'u"z:\\resource\\apps\\phoneui.r01"'
    corrected_call = r'u"z:\\resource\\apps\\callhandlingui.r01"'
    malformed_phone = r'u"z:\resource\apps\phoneui.r01"'
    malformed_call = r'u"z:\resource\apps\callhandlingui.r01"'

    need(fs, corrected_phone, "correct PhoneUI C++ literal")
    need(fs, corrected_call, "correct CallHandlingUI C++ literal")
    if malformed_phone in fs:
        fail("malformed PhoneUI single-backslash literal remains")
    if malformed_call in fs:
        fail("malformed CallHandlingUI single-backslash literal remains")

    for marker in (
        "[NBOOT2][PHONEUI_RES_MATCH2]",
        "[NBOOT2][PHONEUI_RES_CALLER]",
        "[NBOOT2][PHONEUI_RES_FRAME]",
        "[NBOOT2][PHONEUI_RES_ID]",
        "[NBOOT2][PHONEUI_RES_CONTEXT_DONE]",
    ):
        need(fs, marker, "B75/B74 diagnostic")

    need(fs, "nboot2_b74_words=96", "bounded B74 stack scan")
    need(fs, "0x1099B02DU", "CallHandlingUI resource ID")
    need(sv, "[NBOOT2][CONE14_PHONEUI]", "B71 CONE14 evidence")

    b=fs.find('if (nboot2_b74_phoneui || nboot2_b74_callhandling) {')
    e=fs.find('if ((nboot2_b74_phoneui || nboot2_b74_callhandling) &&', b)
    if b < 0 or e < 0:
        fail("cannot isolate B75 exact-path marker block")
    block=fs[b:e]

    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "set_int(",
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "kill(",
    ):
        if forbidden in block:
            fail("behavior-changing token: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=B74_PATH_LITERAL_FIX_PLUS_EXACT_MATCH_MARKER")
    print("exact_path_match_marker=REQUIRED")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_teardown_fix=DEFERRED")
    print("state_injection=NONE")
    print("sim_injection=NONE")

if __name__ == "__main__":
    main()
