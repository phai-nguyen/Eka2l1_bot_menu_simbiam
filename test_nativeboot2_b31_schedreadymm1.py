#!/usr/bin/env python3
"""Source contract for B31 SCHEDREADYMM1.

B30 device evidence proves ROOTEDLIBPATH1 works, then the host crashes with
EXC_BAD_ACCESS at address 0 in thread_scheduler::switch_context(). Upstream
EKA2L1 437b290 fixes the matching failure class by removing ready threads whose
owning process (or its memory model) is already gone before switch_context().

B31 deliberately backports only that scheduler guard and adds one generic
diagnostic marker. SVC 0xE3 and the rest of upstream 437b290 remain out of scope.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B31-SCHEDREADYMM1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b31_schedreadymm1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (sched,lib,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    sc=sched.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # B30 device-validated baseline must remain present.
    for needle in (
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_RESOLVED]",
        "[NBOOT2][LDR_ROOT_EXHAUSTED]",
        "load_depend_on_drive(candidate, is_driver_lib)",
    ):
        need(lm,needle,"libmanager.cpp B30 preservation")

    # B31: exact narrow upstream scheduler semantics.
    for needle in (
        "while (next_thread) {",
        "kernel::process *owner = next_thread->owning_process();",
        "if (owner && owner->get_mem_model()) {",
        "dequeue_thread_from_ready(next_thread);",
        "next_thread = next_ready_thread();",
        "[NBOOT2][SCHED_STALE_READY_DROP]",
    ):
        need(sc,needle,"scheduler.cpp B31 stale-ready guard")

    marker_pos=sc.find("[NBOOT2][SCHED_STALE_READY_DROP]")
    switch_pos=sc.find("switch_context(crr_thread, next_thread);")
    if marker_pos < 0 or switch_pos < 0 or marker_pos >= switch_pos:
        fail("B31 stale-ready filtering must execute before switch_context")

    # Keep B31 single-cause: do not absorb the newly observed 0xE3 executive.
    if "get_module_name_from_address" in sv:
        fail("out-of-scope SVC 0xE3 GetModuleNameFromAddress backport detected")

    # Do not absorb the upstream timer batch either.
    if "TIMER_ACTIVATE_DEFER_US" in sc:
        fail("out-of-scope timer changes detected in scheduler.cpp")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
