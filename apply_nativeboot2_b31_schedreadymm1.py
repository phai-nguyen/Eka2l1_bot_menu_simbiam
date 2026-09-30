#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B31 SCHEDREADYMM1 after B30 ROOTEDLIBPATH1.

B30 device evidence reaches and loads EiksrvUi.dll, then later host-crashes with
EXC_BAD_ACCESS at address 0 in thread_scheduler::switch_context(). Upstream
EKA2L1 commit 437b29006bd8a0186f4070c9445f43e98e5c7435 fixes the matching
scheduler failure class: a ready thread can outlive the memory model of its
owning process during teardown.

This backport is intentionally narrow:
- only thread_scheduler::reschedule() is changed;
- stale ready entries lacking an owning process/memory model are dequeued;
- one generic diagnostic marker is added;
- B30 loader behavior remains untouched;
- SVC 0xE3, timer, IPC lifetime, teardown-order and other upstream changes are
  deliberately not imported.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B31-SCHEDREADYMM1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b31_schedreadymm1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (sched,lib,svc):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sc=sched.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # Require the device-validated B30 baseline before applying B31.
    for needle in (
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_RESOLVED]",
        "[NBOOT2][LDR_ROOT_EXHAUSTED]",
        "load_depend_on_drive(candidate, is_driver_lib)",
    ):
        if needle not in lm:
            fail(f"B30 ROOTEDLIBPATH1 baseline missing: {needle}")

    if "get_module_name_from_address" in sv:
        fail("out-of-scope SVC 0xE3 backport already present")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    if "[NBOOT2][SCHED_STALE_READY_DROP]" in sc:
        print(f"{MARK}: already applied")
        return

    old='''        switch_context(crr_thread, next_thread);
    }

    void thread_scheduler::queue_thread_ready(kernel::thread *thr) {
'''
    new='''        // B31 SCHEDREADYMM1: a ready thread may briefly outlive the
        // address space of its owning process during multi-step teardown.
        // Never pass such a stale entry into switch_context().
        while (next_thread) {
            kernel::process *owner = next_thread->owning_process();
            if (owner && owner->get_mem_model()) {
                break;
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][SCHED_STALE_READY_DROP] thread={} owner_present={} mem_model_present={}",
                next_thread->name(), owner != nullptr, owner && owner->get_mem_model());
            dequeue_thread_from_ready(next_thread);
            next_thread = next_ready_thread();
        }

        switch_context(crr_thread, next_thread);
    }

    void thread_scheduler::queue_thread_ready(kernel::thread *thr) {
'''
    sc=replace_once(sc,old,new,"reschedule stale-ready guard")

    # Scope guards against accidentally absorbing adjacent upstream work.
    if "get_module_name_from_address" in sv:
        fail("out-of-scope SVC 0xE3 change detected")
    if "TIMER_ACTIVATE_DEFER_US" in sc:
        fail("out-of-scope timer change detected")

    sched.write_text(sc,encoding="utf-8")

    for needle in (
        "while (next_thread) {",
        "kernel::process *owner = next_thread->owning_process();",
        "if (owner && owner->get_mem_model()) {",
        "[NBOOT2][SCHED_STALE_READY_DROP]",
        "dequeue_thread_from_ready(next_thread);",
        "next_thread = next_ready_thread();",
        "switch_context(crr_thread, next_thread);",
    ):
        if needle not in sc:
            fail(f"post-apply B31 semantic missing: {needle}")

    print(f"{MARK}: applied")
    print("scope=THREAD_SCHEDULER_RESCHEDULE_ONLY")
    print("upstream_reference=437b29006bd8a0186f4070c9445f43e98e5c7435")
    print("stale_ready_filter=OWNER_AND_MEMORY_MODEL_REQUIRED")
    print("B30_ROOTEDLIBPATH1=PRESERVED")
    print("SVC_0xE3=UNCHANGED")
    print("TIMER_IPC_LIFETIME=UNCHANGED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
