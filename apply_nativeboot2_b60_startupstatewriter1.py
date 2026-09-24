#!/usr/bin/env python3
"""NATIVEBOOT2 B60 STARTUPSTATEWRITER1.

Diagnostic-only follow-up to B58/B59.

B58 proves category/key RProperty::Set writes Startup state 0 -> Wait(1).
No category/key request for StartAnimations(2) was seen, but Symbian clients
can also Attach() a property and later use handle-based RProperty::Set(TInt).

B60 observes the handle-based integer setter for exactly:
  category 0x100058F4, key 0x00000001

It records process/thread and before/requested/after values. The existing B58
category/key marker remains enabled, giving complete writer coverage across the
two integer P&S write paths.

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
    old='''        bool res = prop->get_property_object()->set_int(val);

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
'''
    if block.count(old)!=1:
        fail(f"handle integer setter anchor mismatch: {block.count(old)}")

    new='''        service::property *b60_obj = prop->get_property_object();
        const std::int32_t b60_before = b60_obj->get_int();
        bool res = b60_obj->set_int(val);
        const std::int32_t b60_after = b60_obj->get_int();

        if ((static_cast<std::uint32_t>(b60_obj->first) == 0x100058F4U) &&
            (static_cast<std::uint32_t>(b60_obj->second) == 0x00000001U)) {
            kernel::thread *b60_thr = kern->crr_thread();
            kernel::process *b60_pr = kern->crr_process();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTUP_STATE_HANDLE] category=0x{:08X} key=0x{:08X} before={} requested={} after={} set_result={} process={} uid3=0x{:08X} thread={} handle=0x{:08X} path=HANDLE_INT behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(b60_obj->first),
                static_cast<std::uint32_t>(b60_obj->second),
                b60_before,
                val,
                b60_after,
                res ? 1 : 0,
                b60_pr ? b60_pr->name() : std::string("<null>"),
                b60_pr ? static_cast<std::uint32_t>(std::get<2>(b60_pr->get_uid_type())) : 0,
                b60_thr ? b60_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(h));
        }

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
'''
    block=block.replace(old,new,1)
    text=text[:b]+block+text[e:]

    if text.count("[NBOOT2][STARTUP_STATE_HANDLE]")!=1:
        fail("marker count mismatch")
    if "[NBOOT2][STARTUP_STATE_PS]" not in text:
        fail("B58 category/key marker missing")

    p.write_text(text,encoding="utf-8")
    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_STATE_HANDLE_INT_WRITER")
    print("category=0x100058F4")
    print("key=0x00000001")
    print("behavior_change=NONE")
    print("B58_CATEGORY_KEY_TRACE=PRESERVED")
    print("B59_EXIT_GUARD=PRESERVED")

if __name__=="__main__":
    main()
