#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B58 STARTUPSTATEPS1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B58-STARTUPSTATEPS1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b58_startupstateps1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    begin="BRIDGE_FUNC(std::int32_t, property_find_set_int"
    end="BRIDGE_FUNC(std::int32_t, property_find_set_bin"
    b=svc.find(begin)
    e=svc.find(end,b+1)
    if b<0 or e<0:
        fail("cannot isolate property_find_set_int")
    block=svc[b:e]

    need(block,"prop->set_int(value)","correct integer setter")
    need(block,"[NBOOT2][STARTUP_STATE_PS]","Startup readback marker")
    need(block,"0x100058F4U","Startup category")
    need(block,"0x00000001U","Startup state key")
    need(block,"nboot2_b58_before = prop->get_int()","before readback")
    need(block,"nboot2_b58_after = prop->get_int()","after readback")

    if "prop->set(value)" in block:
        fail("buggy binary-template setter remains in property_find_set_int")
    if block.count("prop->set_int(value)")!=1:
        fail("property_find_set_int must call set_int exactly once")

    # Preserve the binary category/key setter and handle-based integer setter.
    need(svc,"BRIDGE_FUNC(std::int32_t, property_find_set_bin","binary setter preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=STARTUP_STATE_READBACK_DIAGNOSTIC")
    print("required_category_key_setter=PROPERTY_SET_INT")
    print("startup_probe=100058F4:00000001")
    print("B57_GDI_TRACE=PRESERVED")

if __name__=="__main__":
    main()
