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
    old='''        const bool res = prop->set(value);

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
'''
    new='''        const std::int32_t nboot2_b58_before = prop->get_int();
        const bool res = prop->set_int(value);
        const std::int32_t nboot2_b58_after = prop->get_int();

        if ((static_cast<std::uint32_t>(cage) == 0x100058F4U) &&
            (static_cast<std::uint32_t>(key) == 0x00000001U)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTUP_STATE_PS] category=0x{:08X} key=0x{:08X} before={} requested={} after={} set_result={} path=CATEGORY_KEY_INT behavior=FIX_SET_INT",
                static_cast<std::uint32_t>(cage),
                static_cast<std::uint32_t>(key),
                nboot2_b58_before,
                value,
                nboot2_b58_after,
                res ? 1 : 0);
        }

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
'''
    if block.count(old)!=1:
        fail(f"expected one buggy integer setter anchor, found {block.count(old)}")
    block=block.replace(old,new,1)

    if "prop->set(value)" in block:
        fail("binary-package integer setter still present")
    if block.count("prop->set_int(value)")!=1:
        fail("correct integer setter count mismatch")
    if block.count(marker)!=1:
        fail("marker count mismatch")

    text=text[:b]+block+text[e:]
    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=FUNCTIONAL_PUBLISH_SUBSCRIBE_FIX")
    print("bug=CATEGORY_KEY_INT_USED_BINARY_TEMPLATE_SETTER")
    print("fix=PROPERTY_SET_INT")
    print("startup_probe=100058F4:00000001")
    print("redraw_behavior=UNCHANGED")
    print("focus_behavior=UNCHANGED")
    print("TFX_behavior=UNCHANGED")

if __name__=="__main__":
    main()
