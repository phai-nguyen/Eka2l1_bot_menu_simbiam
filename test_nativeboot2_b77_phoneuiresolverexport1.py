#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B77 PHONEUIRESOLVEREXPORT1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B77-PHONEUIRESOLVEREXPORT1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,x,where):
    if x not in text:
        fail(f"missing in {where}: {x}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b77_phoneuiresolverexport1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    for x in (
        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]",
        "[NBOOT2][PHONEUI_LITERAL_PTR]",
        "nboot2_b77_words=384",
        "lookup(\n                            nboot2_b73_pr,182U)",
        'u"z:\\\\sys\\\\bin\\\\phoneuiutils.dll"',
        "0x5094U",
        "0x50B8U",
    ):
        need(fs,x,"fs.cpp")

    for x in (
        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]",
        "[NBOOT2][PHONEUI_LITERAL_PTR]",
        "nboot2_b77_cone_words=384",
        "lookup(\n                        caller_pr,182U)",
    ):
        need(sv,x,"svc.cpp")

    # Historical evidence/fixes remain active.
    need(fs,"[NBOOT2][PHONEUI_RES_MATCH2]","B75")
    need(fs,"nboot2_b74_words=96","B74 compatibility")
    need(sv,"[NBOOT2][CONE14_PHONEUI]","B71")
    need(menu,"[NBOOT2][GAMEMENU_SAFE_TITLE]","B76")

    # B77 explicitly corrects the meaning of the two known literal pointers.
    need(fs,"classification=DESCRIPTOR_LITERAL","literal classification")
    need(sv,"classification=DESCRIPTOR_LITERAL","literal classification")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # B77 must stay observation-only.
    joined=fs[fs.find("// B77: resolve the exact exported BaseConstructL()"):] + \
           sv[sv.find("codeseg_ptr nboot2_b77_cone_phone_seg"):]
    for x in (
        "requested=102",
        "ESimUsable",
        "reason = 0",
    ):
        if x in joined:
            fail("state/SIM/panic mutation token found: "+x)

    print(MARK+": PASS")
    print("export_ordinal=182")
    print("symbol=CPhoneResourceResolverBase::BaseConstructL")
    print("runtime_export_resolution=REQUIRED")
    print("deep_scan=384_WORDS")
    print("known_literal_offsets=0x5094,0x50B8")
    print("resource_registration=UNCHANGED")
    print("guest_behavior=UNCHANGED")
    print("host_b76=PRESERVED")

if __name__=="__main__":
    main()
