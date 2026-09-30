#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B32 EIKSRVFAULTDIAG1 after B31 SCHEDREADYMM1.

B31 device evidence confirms the host scheduler crash is fixed and exposes a
repeatable guest boundary: 16 eiksrvs spawns followed by 16
EikAppUiServerThread KERN-EXEC 3 access violations.

B32 is diagnostic-only. It adds generic correlation at three boundaries:
- missing SVC -> current process/thread + CPU registers;
- KErrCancel (-3) leave -> process/thread/trap + code frames + stack words;
- access violation -> process/thread + CPU registers.

No SVC is implemented, no leave/trap behavior changes, and no guest exception
is suppressed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B32-EIKSRVFAULTDIAG1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b32_eiksrvfaultdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    for p in (lib,svc,kern,sched):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    lm=lib.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=sched.read_text(encoding="utf-8")

    # Require the exact causal baseline that was device-validated in B31.
    if "[NBOOT2][SCHED_STALE_READY_DROP]" not in sc:
        fail("B31 SCHEDREADYMM1 marker missing")
    if "[NBOOT2][LDR_ROOT_RESOLVED]" not in lm:
        fail("B30 ROOTEDLIBPATH1 marker missing")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope GetModuleNameFromAddress backport already present")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][EIKFAULT_SVCMISS]",
        "[NBOOT2][EIKFAULT_LEAVE]",
        "[NBOOT2][EIKFAULT_LEAVE_FRAME]",
        "[NBOOT2][EIKFAULT_LEAVE_STACK]",
        "[NBOOT2][EIKFAULT_AV]",
    )
    present=[m for m in markers if m in (lm+"\n"+sv+"\n"+ke)]
    if present:
        if len(present)==len(markers):
            print(f"{MARK}: already applied")
            return
        fail("partial B32 markers present: "+", ".join(present))

    # ------------------------------------------------------------------
    # 1) Missing-SVC ownership correlation.
    # Keep the existing missing-SVC logger and return-false behavior below.
    # ------------------------------------------------------------------
    svc_miss_anchor='''        if (res == svc_funcs_.end()) {
'''
    svc_miss_inject='''        if (res == svc_funcs_.end()) {
            kernel::process *nboot2_b32_pr = kern_->crr_process();
            kernel::thread *nboot2_b32_thr = kern_->crr_thread();
            arm::core *nboot2_b32_cpu = kern_->get_cpu();
            if (nboot2_b32_cpu) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][EIKFAULT_SVCMISS] process={} thread={} svc=0x{:X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X}",
                    nboot2_b32_pr ? nboot2_b32_pr->name() : "<none>",
                    nboot2_b32_thr ? nboot2_b32_thr->name() : "<none>",
                    svcnum, nboot2_b32_cpu->get_pc(), nboot2_b32_cpu->get_reg(14),
                    nboot2_b32_cpu->get_reg(13), nboot2_b32_cpu->get_cpsr(),
                    nboot2_b32_cpu->get_reg(0), nboot2_b32_cpu->get_reg(1),
                    nboot2_b32_cpu->get_reg(2), nboot2_b32_cpu->get_reg(3));
            }
'''
    lm=replace_once(lm,svc_miss_anchor,svc_miss_inject,"missing-SVC diagnostics")

    # ------------------------------------------------------------------
    # 2) KErrCancel leave/trap correlation. Insert immediately before the
    # original leave-depth increment, keeping all original control flow.
    # ------------------------------------------------------------------
    leave_sig="    BRIDGE_FUNC(eka2l1::ptr<void>, leave_start) {"
    leave_start=sv.find(leave_sig)
    leave_end=sv.find("\n    BRIDGE_FUNC(",leave_start+len(leave_sig))
    if leave_start < 0 or leave_end < 0:
        fail("leave_start block not found")
    leave_body=sv[leave_start:leave_end]
    leave_anchor="        thr->increase_leave_depth();\n"
    if leave_body.count(leave_anchor)!=1:
        fail(f"leave-depth anchor count={leave_body.count(leave_anchor)}")

    leave_diag=r'''        // B32 EIKSRVFAULTDIAG1: diagnostic-only KErrCancel trace.
        auto *nboot2_b32_cpu = kern->get_cpu();
        kernel::process *nboot2_b32_pr = kern->crr_process();
        const std::int32_t nboot2_b32_leave =
            nboot2_b32_cpu ? static_cast<std::int32_t>(nboot2_b32_cpu->get_reg(0)) : 0;

        if (nboot2_b32_cpu && nboot2_b32_pr && thr
            && (nboot2_b32_leave == epoc::error_cancel)) {
            const std::uint32_t pc = nboot2_b32_cpu->get_pc();
            const std::uint32_t lr = nboot2_b32_cpu->get_reg(14);
            const std::uint32_t sp = nboot2_b32_cpu->get_reg(13);
            const std::uint32_t cpsr = nboot2_b32_cpu->get_cpsr();
            const std::uint32_t trap = current_local_data(kern)->trap_handler.ptr_address();

            LOG_WARN(KERNEL,
                "[NBOOT2][EIKFAULT_LEAVE] process={} thread={} leave={} trap=0x{:08X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                nboot2_b32_pr->name(), thr->name(), nboot2_b32_leave, trap,
                pc, lr, sp, cpsr,
                nboot2_b32_cpu->get_reg(0), nboot2_b32_cpu->get_reg(1),
                nboot2_b32_cpu->get_reg(2), nboot2_b32_cpu->get_reg(3),
                nboot2_b32_cpu->get_reg(4), nboot2_b32_cpu->get_reg(5),
                nboot2_b32_cpu->get_reg(6), nboot2_b32_cpu->get_reg(7),
                nboot2_b32_cpu->get_reg(8), nboot2_b32_cpu->get_reg(9),
                nboot2_b32_cpu->get_reg(10), nboot2_b32_cpu->get_reg(11),
                nboot2_b32_cpu->get_reg(12));

            auto nboot2_b32_log_frame = [&](const char *kind, std::uint32_t raw) {
                const std::uint32_t addr = raw & ~1U;
                codeseg_ptr seg = get_codeseg_from_addr(kern, nboot2_b32_pr, addr, false);
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(nboot2_b32_pr);
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_FRAME] kind={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        kind, raw, common::ucs2_to_utf8(seg->get_full_path()),
                        base, addr - base);
                } else {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_FRAME] kind={} raw=0x{:08X} module=<unresolved>",
                        kind, raw);
                }
            };

            nboot2_b32_log_frame("pc", pc);
            nboot2_b32_log_frame("lr", lr);
            nboot2_b32_log_frame("trap", trap);

            for (std::uint32_t i=0; i<32; ++i) {
                const std::uint32_t slot_addr=sp+i*sizeof(std::uint32_t);
                if (slot_addr < sp) break;
                const std::uint32_t *slot=eka2l1::ptr<std::uint32_t>(slot_addr).get(nboot2_b32_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_STACK] index={} slot=0x{:08X} mapped=0 stopping=1",
                        i, slot_addr);
                    break;
                }

                const std::uint32_t value=*slot;
                const std::uint32_t candidate=value & ~1U;
                codeseg_ptr seg=candidate>=0x10000U
                    ? get_codeseg_from_addr(kern,nboot2_b32_pr,candidate,false)
                    : nullptr;
                if (seg) {
                    const std::uint32_t base=seg->get_code_run_addr(nboot2_b32_pr);
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i,slot_addr,value,common::ucs2_to_utf8(seg->get_full_path()),
                        base,candidate-base);
                } else {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_LEAVE_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                        i,slot_addr,value);
                }
            }
        }

'''
    leave_body=leave_body.replace(leave_anchor,leave_diag+leave_anchor,1)
    sv=sv[:leave_start]+leave_body+sv[leave_end:]

    # ------------------------------------------------------------------
    # 3) Guest access-violation ownership + CPU context.
    # Existing exception termination remains immediately afterward.
    # ------------------------------------------------------------------
    av_anchor='''            LOG_ERROR(KERNEL, "Access violation {} address 0x{:X} in thread {}", (exception_type == arm::exception_type_access_violation_read) ? "reading" : "writing", exception_data, crr_thread()->name());
'''
    av_diag='''            {
                kernel::process *nboot2_b32_pr = crr_process();
                kernel::thread *nboot2_b32_thr = crr_thread();
                if (core) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKFAULT_AV] process={} thread={} operation={} address=0x{:08X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                        nboot2_b32_pr ? nboot2_b32_pr->name() : "<none>",
                        nboot2_b32_thr ? nboot2_b32_thr->name() : "<none>",
                        (exception_type == arm::exception_type_access_violation_read) ? "read" : "write",
                        exception_data, core->get_pc(), core->get_reg(14), core->get_reg(13),
                        core->get_cpsr(),
                        core->get_reg(0), core->get_reg(1), core->get_reg(2), core->get_reg(3),
                        core->get_reg(4), core->get_reg(5), core->get_reg(6), core->get_reg(7),
                        core->get_reg(8), core->get_reg(9), core->get_reg(10), core->get_reg(11),
                        core->get_reg(12));
                }
            }

''' + av_anchor
    ke=replace_once(ke,av_anchor,av_diag,"access-violation diagnostics")

    # Explicit scope gates before writing.
    if "BRIDGE_REGISTER(0x2D," in sv[sv.find("const eka2l1::hle::func_map svc_register_funcs_v94"):sv.find("const eka2l1::hle::func_map svc_register_funcs_v93")]:
        fail("out-of-scope EPOC94 SVC 0x2D implementation detected")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope GetModuleNameFromAddress implementation detected")

    lib.write_text(lm,encoding="utf-8")
    svc.write_text(sv,encoding="utf-8")
    kern.write_text(ke,encoding="utf-8")

    combined=lm+"\n"+sv+"\n"+ke
    for marker in markers:
        if marker not in combined:
            fail(f"post-apply marker missing: {marker}")

    # Semantics must stay intact.
    for needle in (
        "thr->increase_leave_depth();",
        "return current_local_data(kern)->trap_handler;",
    ):
        if needle not in sv:
            fail(f"leave semantics lost: {needle}")
    for needle in (
        "cpu_exception_thread_handle(core);",
        "return false;",
    ):
        if needle not in ke:
            fail(f"exception semantics lost: {needle}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("svc_behavior=UNCHANGED")
    print("leave_behavior=UNCHANGED")
    print("access_violation_behavior=UNCHANGED")
    print("SVC_0x2D=UNCHANGED")
    print("SVC_0xE3=UNCHANGED")
    print("B30_ROOTEDLIBPATH1=PRESERVED")
    print("B31_SCHEDREADYMM1=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
