#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B60 STARTUPSTATEWRITER1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B60-STARTUPSTATEWRITER1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b60_startupstatewriter1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gstore=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    begin="BRIDGE_FUNC(std::int32_t, property_set_int"
    end="BRIDGE_FUNC(std::int32_t, property_set_bin"
    b=svc.find(begin)
    e=svc.find(end,b)
    if b<0 or e<0:
        fail("cannot isolate property_set_int")
    block=svc[b:e]

    need(block,"[NBOOT2][STARTUP_STATE_HANDLE]","B60 marker")
    need(block,"0x100058F4U","Startup category")
    need(block,"0x00000001U","Startup key")
    need(block,"b44_old","before readback")
    need(block,"b60_after","after readback")
    need(block,"b44_obj->set_int(val)","original B44 handle setter semantics")
    need(block,"process={}","writer process")
    need(block,"thread={}","writer thread")
    need(block,"behavior=OBSERVE_ONLY","diagnostic-only scope")

    need(svc,"[NBOOT2][STARTUP_STATE_PS]","B58 category/key trace")
    need(gstore,"[NBOOT2][GSTORE_EXIT_GUARD]","B59 exit guard")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("writer_coverage=CATEGORY_KEY_PLUS_HANDLE_INT")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
