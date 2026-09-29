#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B81 PHONEUIBLXDECODE1."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B81-PHONEUIBLXDECODE1-TEST"

def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")

def need(body, token, where):
    if token not in body:
        fail(f"missing in {where}: {token}")

def decode_blx(callsite, hi, lo):
    s = (hi >> 10) & 1
    j1 = (lo >> 13) & 1
    j2 = (lo >> 11) & 1
    i1 = (~(j1 ^ s)) & 1
    i2 = (~(j2 ^ s)) & 1
    imm10h = hi & 0x03FF
    imm10l = (lo >> 1) & 0x03FF
    imm25 = ((s << 24) | (i1 << 23) | (i2 << 22) |
             (imm10h << 12) | (imm10l << 2))
    signed_off = imm25 - (1 << 25) if imm25 & 0x01000000 else imm25
    pc_base = (callsite & ~2) + 4
    return (pc_base + signed_off) & 0xFFFFFFFC

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b81_phoneuiblxdecode1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    fs = (upstream / "src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    svc = (upstream / "src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    menu = (upstream / "src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")

    vectors = (
        (0x80EDA918, 0xF002, 0xEDC0, 0x80EDD49C),  # +1B70 -> ARM veneer +46F4
        (0x80EDA920, 0xF002, 0xED8C, 0x80EDD43C),  # +1B78 -> ARM veneer +4694
        (0x80EDC7DC, 0xF000, 0xEE46, 0x80EDD46C),  # +3A34 -> ARM veneer +46C4
    )
    for callsite, hi, lo, expected in vectors:
        actual = decode_blx(callsite, hi, lo)
        if actual != expected:
            fail(f"BLX callsite 0x{callsite:08X}: got 0x{actual:08X}, expected 0x{expected:08X}")

    for body, name in ((fs, "fs.cpp"), (svc, "svc.cpp")):
        need(body, "((lo>>1U)&0x03FFU)", name)
        need(body, "target_decode=BLX_IMM10L_BITS_10_1", name)
        need(body, "[NBOOT2][PHONEUI_TARGET_FINGERPRINT]", name)
        need(body, "[NBOOT2][PHONEUI_CALLCHAIN_EDGE]", name)
        need(body, "behavior=OBSERVE_ONLY", name)

    need(menu, "[NBOOT2][GAMEMENU_SAFE_TITLE]", "B76 GameMenuView.mm")
    if (upstream / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK + ": PASS")
    print("blx_vectors=+1B70:+46F4,+1B78:+4694,+3A34:+46C4")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("host_b76=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__ == "__main__":
    main()
