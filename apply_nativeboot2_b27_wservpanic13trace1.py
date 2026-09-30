#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B27 WSERVPANIC13TRACE1 on top of B26.

Diagnostic-only instrumentation of thread_kill for native ewsrv/Wserv-related
panic categories. No panic suppression, no category/reason rewrite, no SVC or
P&S behavior change.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B27-WSERVPANIC13TRACE1"

def fail(m:str)->None:
    raise SystemExit(f"{MARK}: {m}")

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b27_wservpanic13trace1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    fbs=up/"src/emu/services/src/fbs/fbs.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"
    for p in (svc,fbs,root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    s=svc.read_text(encoding="utf-8")
    f=fbs.read_text(encoding="utf-8")
    r=root.read_text(encoding="utf-8")
    if "[NBOOT2][FBS_SHARED_HEAP_READY]" not in f:
        fail("B25 checkpoint missing")
    if "[NBOOT2][IOS_EXIT_UI] phase=library_show_done" not in r:
        fail("B26 checkpoint missing")
    if "[NBOOT2][WSERV_TRACE]" in s:
        print("NATIVEBOOT2-B27 WSERVPANIC13TRACE1 already present")
        return

    sig="    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h, kernel::entity_exit_type etype, std::int32_t reason, eka2l1::ptr<desc8> reason_des) {"
    start=s.find(sig)
    if start<0:
        fail("thread_kill signature not found")
    end=s.find("\n    BRIDGE_FUNC(", start+len(sig))
    if end<0:
        fail("thread_kill end anchor not found")
    body=s[start:end]
    anchor="        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"
    if body.count(anchor)!=1:
        fail(f"thread_kill kill anchor count={body.count(anchor)}")

    if "static codeseg_ptr get_codeseg_from_addr(" not in s:
        fail("get_codeseg_from_addr helper missing")

    inject=r'''        // NATIVEBOOT2-B27 WSERVPANIC13TRACE1: diagnostic-only.
        // Capture native Window Server panic context without modifying guest state.
        if (cpu && caller_thr && caller_pr && target_pr) {
            const bool nboot2_wserv_category =
                (exit_category == "WSERV-INTERNAL") || (exit_category == "Domino");
            const std::string nboot2_caller_name = caller_pr->name();
            const std::string nboot2_target_name = target_pr->name();
            const std::string nboot2_thread_name = thr->name();
            const bool nboot2_wserv_name =
                (nboot2_caller_name.find("ewsrv") != std::string::npos) ||
                (nboot2_target_name.find("ewsrv") != std::string::npos) ||
                (nboot2_thread_name.find("Wserv") != std::string::npos) ||
                (nboot2_thread_name.find("NearlyIdleKickBack") != std::string::npos);

            if (nboot2_wserv_category || nboot2_wserv_name) {
                const std::uint32_t pc = cpu->get_pc();
                const std::uint32_t lr = cpu->get_reg(14);
                const std::uint32_t sp = cpu->get_reg(13);
                const std::uint32_t cpsr = cpu->get_cpsr();

                LOG_WARN(KERNEL,
                    "[NBOOT2][WSERV_TRACE] caller_process={} caller_thread={} target_process={} target_thread={} handle=0x{:X} exit_type={} reason={} category={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                    caller_pr->name(), caller_thr->name(), target_pr->name(), thr->name(),
                    h, static_cast<std::int32_t>(etype), reason, exit_category,
                    pc, lr, sp, cpsr,
                    cpu->get_reg(0), cpu->get_reg(1), cpu->get_reg(2), cpu->get_reg(3),
                    cpu->get_reg(4), cpu->get_reg(5), cpu->get_reg(6), cpu->get_reg(7),
                    cpu->get_reg(8), cpu->get_reg(9), cpu->get_reg(10), cpu->get_reg(11),
                    cpu->get_reg(12));

                auto nboot2_log_code = [&](const char *kind, std::uint32_t raw) {
                    const std::uint32_t addr = raw & ~1U;
                    codeseg_ptr seg = get_codeseg_from_addr(kern, caller_pr, addr, false);
                    if (seg) {
                        const std::uint32_t base = seg->get_code_run_addr(caller_pr);
                        LOG_WARN(KERNEL,
                            "[NBOOT2][WSERV_FRAME] kind={} raw=0x{:08X} addr=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                            kind, raw, addr, common::ucs2_to_utf8(seg->get_full_path()), base, addr - base);
                    } else {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][WSERV_FRAME] kind={} raw=0x{:08X} addr=0x{:08X} module=<unresolved>",
                            kind, raw, addr);
                    }
                };

                nboot2_log_code("pc", pc);
                nboot2_log_code("lr", lr);

                for (std::uint32_t i = 0; i < 48; ++i) {
                    const std::uint32_t slot_addr = sp + i * sizeof(std::uint32_t);
                    if (slot_addr < sp) break;
                    const std::uint32_t *slot = eka2l1::ptr<std::uint32_t>(slot_addr).get(caller_pr);
                    if (!slot) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][WSERV_STACK] index={} slot=0x{:08X} mapped=0 stopping=1",
                            i, slot_addr);
                        break;
                    }
                    const std::uint32_t value = *slot;
                    const std::uint32_t candidate = value & ~1U;
                    codeseg_ptr seg = candidate >= 0x10000U
                        ? get_codeseg_from_addr(kern, caller_pr, candidate, false)
                        : nullptr;
                    if (seg) {
                        const std::uint32_t base = seg->get_code_run_addr(caller_pr);
                        LOG_WARN(KERNEL,
                            "[NBOOT2][WSERV_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                            i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()), base, candidate - base);
                    } else {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][WSERV_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                            i, slot_addr, value);
                    }
                }

                LOG_WARN(KERNEL,
                    "[NBOOT2][WSERV_PANIC_CONTEXT] process={} thread={} category={} reason={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X}",
                    caller_pr->name(), caller_thr->name(), exit_category, reason, pc, lr, sp, cpsr);
            }
        }

'''
    body=body.replace(anchor,inject+anchor,1)
    s=s[:start]+body+s[end:]
    svc.write_text(s,encoding="utf-8")

    check=svc.read_text(encoding="utf-8")
    for n in ("[NBOOT2][WSERV_TRACE]","[NBOOT2][WSERV_FRAME]","[NBOOT2][WSERV_STACK]","[NBOOT2][WSERV_PANIC_CONTEXT]"):
        if n not in check:
            fail(f"post-apply marker missing: {n}")
    if anchor.strip() not in check:
        fail("original thr->kill behavior lost")

    print("NATIVEBOOT2-B27 WSERVPANIC13TRACE1 applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("panic_behavior=UNCHANGED")
    print("B25_FBSSHAREDHEAP1=PRESERVED")
    print("B26_IOSLIBRARYEXIT1=PRESERVED")

if __name__=="__main__":
    main()
