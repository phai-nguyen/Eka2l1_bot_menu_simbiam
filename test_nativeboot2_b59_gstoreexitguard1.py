#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B59 GSTOREEXITGUARD1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B59-GSTOREEXITGUARD1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b59_gstoreexitguard1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    gstore=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    begin="gdi_store_command_segment::~gdi_store_command_segment()"
    end="void gdi_store_command_segment::add_command"
    b=gstore.find(begin)
    e=gstore.find(end,b)
    if b<0 or e<0:
        fail("cannot isolate gdi_store_command_segment destructor")
    block=gstore[b:e]

    need(block,"[NBOOT2][GSTORE_EXIT_GUARD]","guard marker")
    need(block,"kind=font","font guard")
    need(block,"kind=bitmap","bitmap guard")
    need(block,"obj->count <= 0","exhausted-ref guard")
    need(block,"(obj->count == 1) && !obj->owner","ownerless-final-ref guard")
    need(block,"obj->deref();","normal deref preserved")

    if "redraw_segments_.clear()" in block:
        fail("B59 must not suppress/redesign redraw-store contents")
    if "FLAG_SERVER_REDRAW_PENDING" in gstore:
        # gstore itself should never gain startup scheduling behavior.
        fail("B59 must not add server redraw scheduling to gstore")

    need(svc,"[NBOOT2][STARTUP_STATE_PS]","B58 state diagnostic preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=WINDOW_REDRAW_STORE_TEARDOWN_ONLY")
    print("startup_behavior=UNCHANGED")
    print("B58_STATE_TRACE=PRESERVED")

if __name__=="__main__":
    main()
