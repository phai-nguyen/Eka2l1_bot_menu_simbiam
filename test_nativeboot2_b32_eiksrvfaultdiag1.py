#!/usr/bin/env python3
"""Source contract for B32 EIKSRVFAULTDIAG1.

B31 device evidence removes the native scheduler crash and exposes a repeatable
guest-side boundary: after the B31 stale-ready drop, 16 eiksrvs instances are
spawned and 16 EikAppUiServerThread instances terminate KERN-EXEC 3 after guest
access violations.

B32 is diagnostic-only. It must correlate:
- missing SVCs with the current process/thread,
- KErrCancel (-3) leave/trap state with code frames/stack,
- access violations with the current process/thread and CPU context.

It must not implement SVC 0x2D/0xE3, suppress exceptions, or change leave logic.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B32-EIKSRVFAULTDIAG1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b32_eiksrvfaultdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    for p in (lib,svc,kern,sched):
        if not p.is_file():
            fail(f"missing source file: {p}")

    lm=lib.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=sched.read_text(encoding="utf-8")

    # Preserve B31 and the known B30 loader baseline.
    need(sc,"[NBOOT2][SCHED_STALE_READY_DROP]","scheduler.cpp B31 preservation")
    need(lm,"[NBOOT2][LDR_ROOT_RESOLVED]","libmanager.cpp B30 preservation")

    # Missing-SVC correlation: no behavior change, just ownership + registers.
    for needle in (
        "[NBOOT2][EIKFAULT_SVCMISS]",
        "kern_->crr_process()",
        "kern_->crr_thread()",
        "kern_->get_cpu()",
    ):
        need(lm,needle,"libmanager.cpp B32 SVC diagnostics")

    # KErrCancel leave correlation and code/stack resolution.
    for needle in (
        "[NBOOT2][EIKFAULT_LEAVE]",
        "[NBOOT2][EIKFAULT_LEAVE_FRAME]",
        "[NBOOT2][EIKFAULT_LEAVE_STACK]",
        "epoc::error_cancel",
        "current_local_data(kern)->trap_handler",
        "get_codeseg_from_addr(kern",
    ):
        need(sv,needle,"svc.cpp B32 leave diagnostics")

    # Access-violation boundary with current owner and CPU state.
    for needle in (
        "[NBOOT2][EIKFAULT_AV]",
        "crr_process()",
        "crr_thread()",
        "core->get_pc()",
        "core->get_reg(14)",
        "core->get_reg(13)",
    ):
        need(ke,needle,"kernel.cpp B32 access-violation diagnostics")

    # Diagnostic-only invariants.
    need(ke,"cpu_exception_thread_handle(core);","kernel.cpp exception behavior")
    need(ke,"return false;","kernel.cpp exception behavior")
    need(sv,"thr->increase_leave_depth();","svc.cpp leave behavior")
    need(sv,"return current_local_data(kern)->trap_handler;","svc.cpp leave behavior")

    # Do not silently turn the observed executive gaps into B32 fixes.
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94")
    v94_end=sv.find("const eka2l1::hle::func_map svc_register_funcs_v93",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("cannot isolate EPOC94 SVC table")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0x2D," in v94:
        fail("out-of-scope EPOC94 SVC 0x2D implementation detected")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope GetModuleNameFromAddress backport detected")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
