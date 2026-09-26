#!/usr/bin/env python3
"""NATIVEBOOT2 B60 STARTUPSTATEWRITER1.

Diagnostic-only follow-up to B58/B59.

B58 proves category/key RProperty::Set writes Startup state 0 -> Wait(1).
B44 already wraps the handle-based integer setter through b44_obj for TFX P&S
diagnostics. B60 observes that existing setter for exactly:
  category 0x100058F4, key 0x00000001

No P&S semantics or guest behavior changes.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B60-STARTUPSTATEWRITER1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b60_startupstatewriter1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/kernel/src/svc.cpp"
    if not p.is_file():
        fail(f"missing source: {p}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTUP_STATE_HANDLE]" in text:
        print(MARK+": already applied")
        return

    begin="    BRIDGE_FUNC(std::int32_t, property_set_int, kernel::handle h, std::int32_t val) {\n"
    end="\n    BRIDGE_FUNC(std::int32_t, property_set_bin"
    b=text.find(begin)
    e=text.find(end,b)
    if b<0 or e<0:
        fail("property_set_int bounds not found")

    block=text[b:e]
    anchor="""        service::property *b44_obj = prop->get_property_object();
        const std::int32_t b44_old = b44_obj->get_int();
        bool res = b44_obj->set_int(val);
"""
    if block.count(anchor)!=1:
        fail(f"B44 handle setter anchor mismatch: {block.count(anchor)}")

    inject="""        service::property *b44_obj = prop->get_property_object();
        const std::int32_t b44_old = b44_obj->get_int();
        bool res = b44_obj->set_int(val);
        const std::int32_t b60_after = b44_obj->get_int();

        if ((static_cast<std::uint32_t>(b44_obj->first) == 0x100058F4U) &&
            (static_cast<std::uint32_t>(b44_obj->second) == 0x00000001U)) {
            kernel::thread *b60_thr = kern->crr_thread();
            kernel::process *b60_pr = kern->crr_process();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTUP_STATE_HANDLE] category=0x{:08X} key=0x{:08X} before={} requested={} after={} set_result={} process={} uid3=0x{:08X} thread={} handle=0x{:08X} path=HANDLE_INT behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(b44_obj->first),
                static_cast<std::uint32_t>(b44_obj->second),
                b44_old,
                val,
                b60_after,
                res ? 1 : 0,
                b60_pr ? b60_pr->name() : std::string("<null>"),
                b60_pr ? static_cast<std::uint32_t>(std::get<2>(b60_pr->get_uid_type())) : 0,
                b60_thr ? b60_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(h));
        }
"""
    block=block.replace(anchor,inject,1)
    text=text[:b]+block+text[e:]

    if text.count("[NBOOT2][STARTUP_STATE_HANDLE]")!=1:
        fail("marker count mismatch")
    if "[NBOOT2][STARTUP_STATE_PS]" not in text:
        fail("B58 category/key marker missing")

    p.write_text(text,encoding="utf-8")
    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_STATE_HANDLE_INT_WRITER")
    print("behavior_change=NONE")
    print("B44_TFX_HANDLE_SET=PRESERVED")
    print("B58_CATEGORY_KEY_TRACE=PRESERVED")
    print("B59_EXIT_GUARD=PRESERVED")

if __name__=="__main__":
    main()
