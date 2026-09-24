#!/usr/bin/env python3
"""NATIVEBOOT2 B58 STARTUPSTATEPS1.

Functional fix selected from B57 DEVICE1 plus Nokia/Symbian Startup source.

Nokia Startup UID 0x100058F4 defines integer P&S key 1 and immediately calls
RProperty::Set(KPSUidStartupApp, KPSStartupAppState, EStartupAppStateWait),
where EStartupAppStateWait == 1.

EKA2L1's category/key integer SVC property_find_set_int currently calls
property::set(value). That resolves to the templated binary-package setter and
copies sizeof(int) bytes into bindata; it does not update the integer member
ndata. The call returns success and notifies subscribers while get_int()
continues returning the old value (initially 0).

The handle-based integer setter already uses property::set_int(). B58 makes
the category/key integer setter use the same correct integer API.

Marker (only Startup category/key):
  [NBOOT2][STARTUP_STATE_PS]

No other P&S, WindowServer, redraw, focus, scheduler, TFX, FBS or loader
behavior is changed.
"""
from pathlib import Path
import sys
import re

MARK="NATIVEBOOT2-B58-STARTUPSTATEPS1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b58_startupstateps1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/kernel/src/svc.cpp"
    if not p.is_file():
        fail(f"missing source: {p}")

    text=p.read_text(encoding="utf-8")
    marker="[NBOOT2][STARTUP_STATE_PS]"
    if marker in text:
        print(MARK+": already applied")
        return

    begin='''    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
'''
    end='''    BRIDGE_FUNC(std::int32_t, property_find_set_bin'''
    b=text.find(begin)
    e=text.find(end,b+1)
    if b<0 or e<0:
        fail("property_find_set_int bounds not found")

    block=text[b:e]
    fixed_existing=False
    m=re.search(r'(?m)^(\s*)(?:const\s+)?bool\s+([A-Za-z_]\w*)\s*=\s*prop->set_int\(value\);\s*$', block)
    if m:
        fixed_existing=True
    else:
        m=re.search(r'(?m)^(\s*)(?:const\s+)?bool\s+([A-Za-z_]\w*)\s*=\s*prop->set\(value\);\s*$', block)

    if not m:
        fail("category/key integer setter call not found")

    indent=m.group(1)
    res_name=m.group(2)
    behavior="PRESERVE_EXISTING_SET_INT" if fixed_existing else "FIX_SET_INT"
    setter_expr="prop->set_int(value)"

    new=f'''{indent}const std::int32_t nboot2_b58_before = prop->get_int();
{indent}const bool {res_name} = {setter_expr};
{indent}const std::int32_t nboot2_b58_after = prop->get_int();

{indent}if ((static_cast<std::uint32_t>(cage) == 0x100058F4U) &&
{indent}    (static_cast<std::uint32_t>(key) == 0x00000001U)) {{
{indent}    LOG_WARN(KERNEL,
{indent}        "[NBOOT2][STARTUP_STATE_PS] category=0x{{:08X}} key=0x{{:08X}} before={{}} requested={{}} after={{}} set_result={{}} path=CATEGORY_KEY_INT behavior={behavior}",
{indent}        static_cast<std::uint32_t>(cage),
{indent}        static_cast<std::uint32_t>(key),
{indent}        nboot2_b58_before,
{indent}        value,
{indent}        nboot2_b58_after,
{indent}        {res_name} ? 1 : 0);
{indent}}}
'''
    block=block[:m.start()]+new+block[m.end():]

    if "prop->set(value)" in block:
        fail("binary-package integer setter still present")
    if block.count("prop->set_int(value)")!=1:
        fail("correct integer setter count mismatch")
    if block.count(marker)!=1:
        fail("marker count mismatch")

    text=text[:b]+block+text[e:]
    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=" + ("DIAGNOSTIC_READBACK" if fixed_existing else "FUNCTIONAL_PUBLISH_SUBSCRIBE_FIX"))
    print("baseline_setter=" + ("SET_INT_ALREADY_PRESENT" if fixed_existing else "BINARY_TEMPLATE_SET"))
    print("fix=" + ("NONE" if fixed_existing else "PROPERTY_SET_INT"))
    print("startup_probe=100058F4:00000001")
    print("redraw_behavior=UNCHANGED")
    print("focus_behavior=UNCHANGED")
    print("TFX_behavior=UNCHANGED")

if __name__=="__main__":
    main()
