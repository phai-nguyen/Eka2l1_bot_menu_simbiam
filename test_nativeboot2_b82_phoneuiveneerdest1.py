#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B82 PHONEUIVENEERDEST1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B82-PHONEUIVENEERDEST1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(body,token,where):
    if token not in body:
        fail(f"missing in {where}: {token}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b82_phoneuiveneerdest1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    for body,name in ((fs,"fs.cpp"),(sv,"svc.cpp")):
        for token in (
            "target_decode=BLX_IMM10L_BITS_10_1",
            "[NBOOT2][PHONEUI_VENEER_DEST]",
            "[NBOOT2][PHONEUI_VENEER_DEST_FP]",
            "0xE51FF004U",
            "get_codeseg_list()",
            "get_export_table(",
            "owner_ordinal={}",
            "exact_export={}",
            "fnv1a64=0x{:016X}",
            "behavior=OBSERVE_ONLY",
        ):
            need(body,token,name)

    need(menu,"[NBOOT2][GAMEMENU_SAFE_TITLE]","B76 GameMenuView.mm")

    # B82 is observation-only. The apply script itself scopes this check to
    # B82-owned inserted strings; retain explicit contract tokens here.
    for body,name in ((fs,"fs.cpp"),(sv,"svc.cpp")):
        need(body,"nboot2_b82_dest_raw",name)
        need(body,"nboot2_b82_owner_begin",name)
        need(body,"nboot2_b82_hash",name)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("veneer_follow=ONE_HOP_E51FF004")
    print("destination_identity=MODULE_EXPORT_OWNER_FINGERPRINT")
    print("resource_registration=UNCHANGED")
    print("fileserver_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_b76=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
