#!/usr/bin/env python3
"""Source contract for B35 EIKLEAVECALLER1.

B34 device evidence preserves one stable guest failure family:
EikAppUiServerThread -> User::Leave(KErrCancel/-3), with the same four code
candidates on all 16 occurrences:
- ws32.dll + 0x370A
- avkonfep.dll + 0xF104
- avkonfep.dll + 0xF16E
- avkonfep.dll + 0x03D8

B35 is diagnostic-only. For each B32 code candidate it resolves the nearest
export/ordinal and dumps a bounded 16-bit code window around the return address
so the immediate guest caller can be identified without changing IPC, FEP,
WindowServer, completion, leave, or exception semantics.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B35-EIKLEAVECALLER1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b35_eikleavecaller1.py <upstream-root>")

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
            fail(f"missing source file: {p}")

    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=screen.read_text(encoding="utf-8")
    sh=screen_h.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    sch=sched.read_text(encoding="utf-8")
    cx=ctx.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    rt=root.read_text(encoding="utf-8")

    # Preserve B30-B34 evidence/fixes.
    need(lm,"[NBOOT2][LDR_ROOT_RESOLVED]","B30")
    need(sch,"[NBOOT2][SCHED_STALE_READY_DROP]","B31")
    need(sv,"[NBOOT2][EIKFAULT_LEAVE]","B32")
    need(ke,"[NBOOT2][EIKFAULT_AV]","B32")
    need(sv,"[NBOOT2][EIKCANCEL_LLE]","B33")
    need(cx,"[NBOOT2][EIKCANCEL_HLE]","B33")
    need(th,"[NBOOT2][EIKCANCEL_NOTIFY]","B33")
    need(sc,"[NBOOT2][FOCUS_MUTEX_SPLIT]","B34")
    need(sh,"std::mutex focus_callback_mutex;","B34 dedicated mutex")
    need(rt,"[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested","B26/B34 exit")

    # B35 diagnostics: source-level identity.
    need(sv,"[NBOOT2][EIKCALLSITE]","B35 callsite marker")
    need(sv,"[NBOOT2][EIKCODE16]","B35 code-window marker")
    need(sv,"get_export_table(nboot2_b32_pr)","B35 export table lookup")
    need(sv,"nearest_export_ordinal","B35 nearest ordinal")
    need(sv,"nearest_export_delta","B35 export delta")
    need(sv,"thumb={}","B35 ISA marker")
    need(sv,"relative_halfword={}","B35 bounded code window")
    need(sv,"code16=0x{:04X}","B35 code halfword")

    # B35 must be attached to the already-proven B32 stack candidate path.
    need(sv,"[NBOOT2][EIKFAULT_LEAVE_STACK]","B32 stack marker")
    need(sv,"if (seg) {","B32 stack candidate branch")

    # Diagnostic-only: original leave/trap semantics remain.
    need(sv,"thr->increase_leave_depth();","leave semantics")
    need(sv,"return current_local_data(kern)->trap_handler;","trap semantics")
    if "epoc::error_cancel = epoc::error_none" in sv:
        fail("KErrCancel suppression detected")

    # No speculative guest fix.
    combined=(sv+"\n"+ke+"\n"+sc+"\n"+sh).lower()
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
        if forbidden in combined:
            fail(f"target-specific B35 behavior detected: {forbidden}")

    # Preserve B34 lock behavior.
    need(sc,"const std::lock_guard<std::mutex> guard(focus_callback_mutex);","B34 focus lock")
    if "std::recursive_mutex" in sh or "std::recursive_mutex" in sc:
        fail("recursive mutex regression")

    # Preserve executive invariant.
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    v94_end=sv.find("\n    };",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("EPOC94 map missing")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")
    need(v94,"BRIDGE_REGISTER(0xAB, message_construct)","EPOC94 0xAB")
    need(v94,"BRIDGE_REGISTER(0xAC, message_kill)","EPOC94 0xAC")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
