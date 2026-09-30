#!/usr/bin/env python3
"""NATIVEBOOT2 B81 PHONEUIBLXDECODE1.

Correct the Thumb-2 BLX imm10L extraction in B79's FileServer and CONE
call-chain diagnostics. Keep every runtime path diagnostic-only.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B81-PHONEUIBLXDECODE1"

def fail(message):
    raise SystemExit(f"{MARK}: {message}")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b81_phoneuiblxdecode1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    fs_path = upstream / "src/emu/services/src/fs/fs.cpp"
    svc_path = upstream / "src/emu/kernel/src/svc.cpp"
    for path in (fs_path, svc_path):
        if not path.is_file():
            fail(f"missing source: {path}")

    fs = fs_path.read_text(encoding="utf-8")
    svc = svc_path.read_text(encoding="utf-8")

    for name, body in (("fs.cpp", fs), ("svc.cpp", svc)):
        if "[NBOOT2][PHONEUI_BLX_TARGET]" not in body:
            fail(f"{name}: B79 BLX diagnostic missing")
        if "[NBOOT2][PHONEUI_TARGET_FINGERPRINT]" not in body:
            fail(f"{name}: B80 target fingerprint missing")
        if "[NBOOT2][PHONEUI_CALLCHAIN_EDGE]" not in body:
            fail(f"{name}: B79 call-chain marker missing")

    old_low = "is_bl ? (lo&0x07FFU) : (lo&0x03FFU);"
    new_low = "is_bl ? (lo&0x07FFU) : ((lo>>1U)&0x03FFU);"
    fs = replace_once(fs, old_low, new_low, "FileServer BLX imm10L")
    svc = replace_once(svc, old_low, new_low, "CONE14 BLX imm10L")

    old_marker = "target_state=ARM "
    new_marker = "target_state=ARM target_decode=BLX_IMM10L_BITS_10_1 "
    fs = replace_once(fs, old_marker, new_marker, "FileServer BLX marker")
    svc = replace_once(svc, old_marker, new_marker, "CONE14 BLX marker")

    for name, body in (("fs.cpp", fs), ("svc.cpp", svc)):
        if new_low not in body or "target_decode=BLX_IMM10L_BITS_10_1" not in body:
            fail(f"{name}: B81 post-apply gate missing")
        if "behavior=OBSERVE_ONLY" not in body:
            fail(f"{name}: diagnostic-only contract missing")

    if (upstream / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_path.write_text(fs, encoding="utf-8")
    svc_path.write_text(svc, encoding="utf-8")

    print(MARK + ": applied")
    print("thumb_blx_imm10l=bits_10_1")
    print("runtime_markers=PHONEUI_BLX_TARGET_AND_TARGET_FINGERPRINT")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("guest_behavior=UNCHANGED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
