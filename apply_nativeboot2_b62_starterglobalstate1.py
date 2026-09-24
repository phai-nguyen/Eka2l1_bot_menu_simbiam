#!/usr/bin/env python3
"""NATIVEBOOT2 B62 STARTERGLOBALSTATE1.

Diagnostic-only follow-up to B61 DEVICE1.

B60/B61 prove Startup's private state 0x100058F4:1 reaches Wait=1 but no
StartAnimations=2 writer appears through either integer P&S write path.

Nokia/Symbian Startup source also subscribes KPSGlobalSystemState:
  category 0x101F8766, key 0x00000041.

Startup considers Starter's critical phase ended only when that state reaches
one of the accepted post-critical values (e.g. CriticalPhaseOK / NormalRf*).

B62 therefore traces the exact lifecycle of 0x101F8766:0x41 across:
- direct category/key Get
- direct category/key Set
- handle-based Set

Each write records caller process/thread plus before/requested/after/result.
No P&S value is changed by B62.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B62-STARTERGLOBALSTATE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b62_starterglobalstate1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/kernel/src/svc.cpp"
    if not p.is_file():
        fail(f"missing source: {p}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" in text:
        print(MARK+": already applied")
        return

    for marker in ("[NBOOT2][STARTUP_STATE_PS]","[NBOOT2][STARTUP_STATE_HANDLE]"):
        if marker not in text:
            fail("missing predecessor marker "+marker)

    # Direct category/key Get.
    begin="    BRIDGE_FUNC(std::int32_t, property_find_get_int, std::int32_t cage, std::int32_t key, eka2l1::ptr<std::int32_t> value) {\n"
    end="\n    BRIDGE_FUNC(std::int32_t, property_find_get_bin"
    b=text.find(begin)
    e=text.find(end,b)
    if b<0 or e<0:
        fail("property_find_get_int bounds not found")
    block=text[b:e]

    anchor='''        *val_ptr = prop->get_int();
        b44_tfx_ps_log(kern, "find_get", "result", cage, key, *val_ptr, *val_ptr, epoc::error_none);

        return epoc::error_none;
'''
    inject='''        *val_ptr = prop->get_int();
        b44_tfx_ps_log(kern, "find_get", "result", cage, key, *val_ptr, *val_ptr, epoc::error_none);

        if ((static_cast<std::uint32_t>(cage) == 0x101F8766U) &&
            (static_cast<std::uint32_t>(key) == 0x00000041U)) {
            kernel::process *b62_pr = kern->crr_process();
            kernel::thread *b62_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_GLOBAL_STATE] op=GET path=CATEGORY_KEY category=0x{:08X} key=0x{:08X} value={} process={} uid3=0x{:08X} thread={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(cage),
                static_cast<std::uint32_t>(key),
                *val_ptr,
                b62_pr ? b62_pr->name() : std::string("<null>"),
                b62_pr ? static_cast<std::uint32_t>(std::get<2>(b62_pr->get_uid_type())) : 0,
                b62_thr ? b62_thr->name() : std::string("<null>"));
        }

        return epoc::error_none;
'''
    if block.count(anchor)!=1:
        fail(f"find_get anchor mismatch: {block.count(anchor)}")
    block=block.replace(anchor,inject,1)
    text=text[:b]+block+text[e:]

    # Direct category/key Set: reuse B58 before/after readback.
    begin="    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {\n"
    end="\n    BRIDGE_FUNC(std::int32_t, property_find_set_bin"
    b=text.find(begin)
    e=text.find(end,b)
    if b<0 or e<0:
        fail("property_find_set_int bounds not found")
    block=text[b:e]

    anchor='''        const std::int32_t nboot2_b58_after = prop->get_int();

        if ((static_cast<std::uint32_t>(cage) == 0x100058F4U) &&
'''
    inject='''        const std::int32_t nboot2_b58_after = prop->get_int();

        if ((static_cast<std::uint32_t>(cage) == 0x101F8766U) &&
            (static_cast<std::uint32_t>(key) == 0x00000041U)) {
            kernel::process *b62_pr = kern->crr_process();
            kernel::thread *b62_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_GLOBAL_STATE] op=SET path=CATEGORY_KEY category=0x{:08X} key=0x{:08X} before={} requested={} after={} set_result={} process={} uid3=0x{:08X} thread={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(cage),
                static_cast<std::uint32_t>(key),
                nboot2_b58_before,
                value,
                nboot2_b58_after,
                res ? 1 : 0,
                b62_pr ? b62_pr->name() : std::string("<null>"),
                b62_pr ? static_cast<std::uint32_t>(std::get<2>(b62_pr->get_uid_type())) : 0,
                b62_thr ? b62_thr->name() : std::string("<null>"));
        }

        if ((static_cast<std::uint32_t>(cage) == 0x100058F4U) &&
'''
    if block.count(anchor)!=1:
        fail(f"find_set B58 anchor mismatch: {block.count(anchor)}")
    block=block.replace(anchor,inject,1)
    text=text[:b]+block+text[e:]

    # Handle-based Set: reuse B44 old value + B60 post-write readback.
    begin="    BRIDGE_FUNC(std::int32_t, property_set_int, kernel::handle h, std::int32_t val) {\n"
    end="\n    BRIDGE_FUNC(std::int32_t, property_set_bin"
    b=text.find(begin)
    e=text.find(end,b)
    if b<0 or e<0:
        fail("property_set_int bounds not found")
    block=text[b:e]

    anchor='''        const std::int32_t b60_after = b44_obj->get_int();

        if ((static_cast<std::uint32_t>(b44_obj->first) == 0x100058F4U) &&
'''
    inject='''        const std::int32_t b60_after = b44_obj->get_int();

        if ((static_cast<std::uint32_t>(b44_obj->first) == 0x101F8766U) &&
            (static_cast<std::uint32_t>(b44_obj->second) == 0x00000041U)) {
            kernel::process *b62_pr = kern->crr_process();
            kernel::thread *b62_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_GLOBAL_STATE] op=SET path=HANDLE_INT category=0x{:08X} key=0x{:08X} before={} requested={} after={} set_result={} process={} uid3=0x{:08X} thread={} handle=0x{:08X} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(b44_obj->first),
                static_cast<std::uint32_t>(b44_obj->second),
                b44_old,
                val,
                b60_after,
                res ? 1 : 0,
                b62_pr ? b62_pr->name() : std::string("<null>"),
                b62_pr ? static_cast<std::uint32_t>(std::get<2>(b62_pr->get_uid_type())) : 0,
                b62_thr ? b62_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(h));
        }

        if ((static_cast<std::uint32_t>(b44_obj->first) == 0x100058F4U) &&
'''
    if block.count(anchor)!=1:
        fail(f"handle-set B60 anchor mismatch: {block.count(anchor)}")
    block=block.replace(anchor,inject,1)
    text=text[:b]+block+text[e:]

    if text.count("[NBOOT2][STARTER_GLOBAL_STATE]")!=3:
        fail("B62 source marker count mismatch")

    p.write_text(text,encoding="utf-8")
    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=KPSGlobalSystemState_101F8766_41")
    print("writer_coverage=CATEGORY_KEY_PLUS_HANDLE_INT")
    print("reader_coverage=CATEGORY_KEY_GET")
    print("behavior_change=NONE")
    print("B61_WIPEOUT_GUARD=PRESERVED")

if __name__=="__main__":
    main()
