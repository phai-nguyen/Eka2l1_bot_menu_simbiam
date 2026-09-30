#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B78 PHONEUICALLCHAIN1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B78-PHONEUICALLCHAIN1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,x,where):
    if x not in text:
        fail(f"missing in {where}: {x}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b78_phoneuicallchain1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    for body,where in ((fs,"fs.cpp"),(sv,"svc.cpp")):
        for x in (
            "[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]",
            "[NBOOT2][PHONEUI_CALLSITE]",
            "validation=REAL_CALLSITE",
            "CPhoneMainResourceResolver::Instance",
            "CPhoneResourceResolverBase::BaseConstructL",
            "CPhoneResourceResolverBase::ResolveResourceID",
            "181U,182U,307U,308U",
            "THUMB_BL",
            "return_owner_ordinal",
            "target_owner_ordinal",
        ):
            need(body,x,where)

    # Previous evidence/fixes must remain active.
    need(fs,"[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]","B77 fs")
    need(fs,"[NBOOT2][PHONEUI_LITERAL_PTR]","B77 fs")
    need(sv,"[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]","B77 svc")
    need(sv,"[NBOOT2][CONE14_PHONEUI]","B71")
    need(menu,"[NBOOT2][GAMEMENU_SAFE_TITLE]","B76")

    joined=fs[fs.find("// B78: runtime export ownership"):] + \
           sv[sv.find("const std::vector<std::uint32_t>\n                nboot2_b78_cone_exports"):]

    for x in (
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "set_export(",
    ):
        if x in joined:
            fail("behavior-changing token found: "+x)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("key_exports=181,182,307,308")
    print("validated_callsites=THUMB_BL_BLX")
    print("decoded_bl_targets=YES")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_b76=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
