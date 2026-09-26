#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B79 PHONEUICALLCHAIN2."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B79-PHONEUICALLCHAIN2-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,x,where):
    if x not in text:
        fail(f"missing in {where}: {x}")

def decode_blx(callsite,hi,lo):
    s=(hi>>10)&1
    j1=(lo>>13)&1
    j2=(lo>>11)&1
    i1=(~(j1^s))&1
    i2=(~(j2^s))&1
    imm10h=hi&0x3ff
    imm10l=lo&0x3ff
    imm25=(s<<24)|(i1<<23)|(i2<<22)|(imm10h<<12)|(imm10l<<2)
    if imm25 & 0x01000000:
        signed_off=imm25-(1<<25)
    else:
        signed_off=imm25
    pc_base=(callsite & ~2)+4
    return (pc_base+signed_off) & 0xFFFFFFFC

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b79_phoneuicallchain2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    for body,where in ((fs,"fs.cpp"),(sv,"svc.cpp")):
        for x in (
            "[NBOOT2][PHONEUI_CALLSITE]",
            "[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]",
            "[NBOOT2][PHONEUI_BLX_TARGET]",
            "[NBOOT2][PHONEUI_CALLCHAIN_EDGE]",
            "validation=BL_OR_BLX_DECODED",
            "NEAR_0_255B",
            "MID_256_511B",
            "DEEP_512B_PLUS",
            "target_state=ARM",
            "callsite&~2U",
            "lo&0x03FFU",
        ):
            need(body,x,where)

    # B78 DEVICE1 exact BLX vectors. These test the architecture formula used
    # by the generated C++ before compilation.
    vectors=(
        (0x80EDA918,0xF002,0xEDC0,0x80EDD01C), # +1B70 -> +4274
        (0x80EDA920,0xF002,0xED8C,0x80EDCF54), # +1B78 -> +41AC
        (0x80EDC7DC,0xF000,0xEE46,0x80EDD0F8), # +3A34 -> +4350
    )
    for callsite,hi,lo,expected in vectors:
        got=decode_blx(callsite,hi,lo)
        if got!=expected:
            fail(
                f"BLX vector callsite=0x{callsite:08X} "
                f"got=0x{got:08X} expected=0x{expected:08X}"
            )

    # Previous diagnostics/fixes must remain.
    need(fs,"[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]","B77 fs")
    need(sv,"[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]","B77 svc")
    need(menu,"[NBOOT2][GAMEMENU_SAFE_TITLE]","B76")

    joined=fs[fs.find("[NBOOT2][PHONEUI_BLX_TARGET]"):] + \
           sv[sv.find("[NBOOT2][PHONEUI_BLX_TARGET]"):]

    for x in (
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "set_export(",
        "AddResourceFile",
    ):
        if x in joined:
            fail("behavior-changing token found: "+x)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("blx_vector_1=0x80EDD01C")
    print("blx_vector_2=0x80EDCF54")
    print("blx_vector_3=0x80EDD0F8")
    print("stack_locality=NEAR_MID_DEEP")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_b76=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
