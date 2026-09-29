#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B35 EIKLEAVECALLER1 after B34 FOCUSMUTEXSPLIT1.

B34 device evidence closes the independent host Exit Emulator deadlock but
preserves a stable guest failure:
- 16 KErrCancel User::Leave events in EikAppUiServerThread;
- each B32 stack has the same ws32 + stock avkonfep code candidates.

B35 is diagnostic-only. It extends the existing generic B32 KErrCancel stack
candidate logging with:
1) nearest export ordinal/address within the candidate code segment;
2) a bounded 16-bit code window around each candidate return address.

This lets the next device log resolve the immediate guest API/callsite without
changing FEP, WindowServer, CentralRepository, IPC completion, leave/trap, or
exception behavior.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B35-EIKLEAVECALLER1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b35_eikleavecaller1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    screen=up/"src/emu/services/src/window/screen.cpp"
    screen_h=up/"src/emu/services/include/services/window/screen.h"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    ctx=up/"src/emu/services/src/context.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"

    for p in (svc,kern,screen,screen_h,lib,sched,ctx,thr,root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=screen.read_text(encoding="utf-8")
    sh=screen_h.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    sch=sched.read_text(encoding="utf-8")
    cx=ctx.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    rt=root.read_text(encoding="utf-8")

    for needle,text,name in (
        ("[NBOOT2][LDR_ROOT_RESOLVED]",lm,"B30"),
        ("[NBOOT2][SCHED_STALE_READY_DROP]",sch,"B31"),
        ("[NBOOT2][EIKFAULT_LEAVE]",sv,"B32 leave"),
        ("[NBOOT2][EIKFAULT_LEAVE_STACK]",sv,"B32 stack"),
        ("[NBOOT2][EIKFAULT_AV]",ke,"B32 AV"),
        ("[NBOOT2][EIKCANCEL_LLE]",sv,"B33 LLE"),
        ("[NBOOT2][EIKCANCEL_HLE]",cx,"B33 HLE"),
        ("[NBOOT2][EIKCANCEL_NOTIFY]",th,"B33 notify"),
        ("[NBOOT2][FOCUS_MUTEX_SPLIT]",sc,"B34"),
        ("std::mutex focus_callback_mutex;",sh,"B34 mutex"),
        ("[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested",rt,"B26/B34 exit"),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=("[NBOOT2][EIKCALLSITE]","[NBOOT2][EIKCODE16]")
    present=[m for m in markers if m in sv]
    if present:
        if len(present)==len(markers):
            print(f"{MARK}: already applied")
            return
        fail("partial B35 markers present: "+", ".join(present))

    # Replace only the code-candidate half of B32's KErrCancel stack logger.
    old=r'''                if (seg) {
                    const std::uint32_t base=seg->get_code_run_addr(nboot2_b32_pr);
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i,slot_addr,value,common::ucs2_to_utf8(seg->get_full_path()),
                        base,candidate-base);
                } else {
'''
    new=r'''                if (seg) {
                    const std::uint32_t base=seg->get_code_run_addr(nboot2_b32_pr);
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i,slot_addr,value,common::ucs2_to_utf8(seg->get_full_path()),
                        base,candidate-base);

                    // B35 EIKLEAVECALLER1: diagnostic-only symbol/callsite
                    // context. EKA2L1 already has the relocated export table
                    // for this exact codeseg/process, so resolve the nearest
                    // preceding code export without any target-specific map.
                    const auto nboot2_b35_exports=seg->get_export_table(nboot2_b32_pr);
                    std::uint32_t nearest_export_ordinal=0;
                    std::uint32_t nearest_export_address=0;
                    std::uint32_t nearest_export_delta=0xFFFFFFFFU;
                    const std::uint32_t code_end=base+seg->get_code_size();

                    for (std::size_t export_index=0;
                         export_index<nboot2_b35_exports.size(); ++export_index) {
                        const std::uint32_t export_raw=nboot2_b35_exports[export_index];
                        const std::uint32_t export_address=export_raw & ~1U;
                        if ((export_address < base) || (export_address >= code_end)
                            || (export_address > candidate)) {
                            continue;
                        }

                        const std::uint32_t export_delta=candidate-export_address;
                        if (export_delta < nearest_export_delta) {
                            nearest_export_delta=export_delta;
                            nearest_export_address=export_raw;
                            nearest_export_ordinal=
                                static_cast<std::uint32_t>(export_index+1);
                        }
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKCALLSITE] stack_index={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X} thumb={} nearest_export_ordinal={} nearest_export=0x{:08X} nearest_export_delta=0x{:08X}",
                        i,value,common::ucs2_to_utf8(seg->get_full_path()),
                        base,candidate-base,(value & 1U) ? 1 : 0,
                        nearest_export_ordinal,nearest_export_address,
                        nearest_export_delta);

                    // A Thumb BL/BLX return address points immediately after
                    // the call. Dump a small symmetric halfword window around
                    // every generic code candidate; no instruction execution
                    // or guest memory is modified.
                    for (std::int32_t relative_halfword=-8;
                         relative_halfword<=4; ++relative_halfword) {
                        const std::int64_t signed_code_address=
                            static_cast<std::int64_t>(candidate)
                            + static_cast<std::int64_t>(relative_halfword)*2;
                        if ((signed_code_address < 0)
                            || (signed_code_address > 0xFFFFFFFFLL)) {
                            continue;
                        }

                        const std::uint32_t code_address=
                            static_cast<std::uint32_t>(signed_code_address);
                        const std::uint16_t *code16=
                            eka2l1::ptr<std::uint16_t>(code_address).get(nboot2_b32_pr);
                        if (!code16) {
                            LOG_WARN(KERNEL,
                                "[NBOOT2][EIKCODE16] stack_index={} relative_halfword={} address=0x{:08X} mapped=0",
                                i,relative_halfword,code_address);
                            continue;
                        }

                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKCODE16] stack_index={} relative_halfword={} address=0x{:08X} code16=0x{:04X}",
                            i,relative_halfword,code_address,*code16);
                    }
                } else {
'''
    sv=replace_once(sv,old,new,"B32 code candidate diagnostics")

    # Explicit diagnostic-only and preserved-semantics gates.
    for needle in (
        "thr->increase_leave_depth();",
        "return current_local_data(kern)->trap_handler;",
        "[NBOOT2][EIKFAULT_LEAVE]",
        "[NBOOT2][EIKFAULT_LEAVE_STACK]",
        "[NBOOT2][EIKCANCEL_LLE]",
    ):
        if needle not in sv:
            fail(f"leave/B32/B33 semantics lost: {needle}")
    if "std::recursive_mutex" in sh or "std::recursive_mutex" in sc:
        fail("B34 mutex regression")
    if "const std::lock_guard<std::mutex> guard(focus_callback_mutex);" not in sc:
        fail("B34 dedicated focus mutex behavior lost")

    # No target-specific workaround belongs in B35. Check only the
    # diagnostic replacement block: earlier NativeBoot milestones legitimately
    # contain device-family text in unrelated code.
    b35_block=new.lower()
    for forbidden in (
        "avkonfep_general.dll",
        "rm-356",
        "10003a4a",
        "eikappuiserverthread",
        "0x101f876e",
        "0x101f8780",
        "0x101f877c",
        "0x10282df0",
    ):
        if forbidden in b35_block:
            fail(f"target-specific behavior detected: {forbidden}")

    # EPOC94 ABI invariant.
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    v94_end=sv.find("\n    };",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("EPOC94 map missing")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA unexpectedly mapped")
    for needle in (
        "BRIDGE_REGISTER(0xAB, message_construct)",
        "BRIDGE_REGISTER(0xAC, message_kill)",
    ):
        if needle not in v94:
            fail(f"EPOC94 invariant missing: {needle}")

    svc.write_text(sv,encoding="utf-8")

    final=svc.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("leave_behavior=UNCHANGED")
    print("trap_behavior=UNCHANGED")
    print("ipc_completion=UNCHANGED")
    print("fep_behavior=UNCHANGED")
    print("windowserver_behavior=UNCHANGED")
    print("centralrepository_behavior=UNCHANGED")
    print("B30_B31_B32_B33_B34=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
