#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B80 PHONEUITARGETFP1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B80-PHONEUITARGETFP1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,x,where):
    if x not in text:
        fail(f"missing in {where}: {x}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b80_phoneuitargetfp1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    for body,where in ((fs,"fs.cpp"),(sv,"svc.cpp")):
        for x in (
            "[NBOOT2][PHONEUI_CALLCHAIN_EDGE]",
            "[NBOOT2][PHONEUI_BLX_TARGET]",
            "[NBOOT2][PHONEUI_TARGET_FINGERPRINT]",
            "fnv1a64=0x{:016X}",
            "bytes=64",
            "1469598103934665603ULL",
            "1099511628211ULL",
        ):
            need(body,x,where)

    for x in (
        "[NBOOT2][PHONEUI_EXPORT_IDENTITY_CAUTION]",
        "[NBOOT2][PHONEUI_EXPORT_SURFACE]",
        "production_export_count={}",
        "public_symbiansource_def_count=387",
        "rm612_control_export_count=462",
        "ordinal_symbol_mapping=UNVERIFIED",
        "ord=170U;ord<=190U",
        "ord=290U;ord<=310U",
    ):
        need(sv,x,"svc.cpp")

    need(menu,"[NBOOT2][GAMEMENU_SAFE_TITLE]","B76")

    # Diagnostic-only: no resource/SIM/panic/lifecycle mutation.
    joined=fs[fs.find("[NBOOT2][PHONEUI_TARGET_FINGERPRINT]"):] + \
           sv[sv.find("[NBOOT2][PHONEUI_TARGET_FINGERPRINT]"):]
    for x in (
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "set_export(",
        "AddResourceFile",
        "ctx->complete(",
        "WRITE_MODE",
    ):
        if x in joined:
            fail("behavior-changing token found: "+x)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("fingerprint=64_BYTE_FNV1A_PLUS_RAW_WORDS")
    print("export_surface=170_190_290_310")
    print("public_def_symbol_mapping=UNVERIFIED")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_b76=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
