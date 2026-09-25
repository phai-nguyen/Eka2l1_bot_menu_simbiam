#!/usr/bin/env python3
"""NATIVEBOOT2 B71 PHONEUICONE14RES1.

B70 DEVICE1 proves the immediate normal-boot blocker is not yet SIM
adaptation. Telephone[0x100058B3] opens Z:\\resource\\apps\\phoneui.r01,
then self-panics CONE 14. Starter receives result 14 and transitions
101 -> 116 through SAServer 0x64.

Symbian CONE 14 means the environment cannot find the requested resource in
any loaded resource file. B71 is diagnostic-only: at the exact Telephone
CONE14 self-panic boundary, capture all registers, code frames and a bounded
guest-stack scan, with explicit PhoneUI resource-ID candidate tagging for the
RSC signature range 0x4E738xxx.

No panic, rendezvous, Starter, SAServer, P&S, SIM, resource, scheduler,
graphics or teardown behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B71-PHONEUICONE14RES1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b71_phoneuicone14res1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    sess=up/"src/emu/kernel/src/session.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    alarm=up/"src/emu/services/src/alarm/alarm.cpp"
    for p in (svc,sess,sa,alarm):
        if not p.is_file():
            fail(f"missing source: {p}")

    sv=svc.read_text(encoding="utf-8")
    se=sess.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    al=alarm.read_text(encoding="utf-8")

    if "[NBOOT2][CONE14_PHONEUI]" in sv:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",sv,"MENUUI4"),
        ("static codeseg_ptr get_codeseg_from_addr(",sv,"codeseg helper"),
        ("[NBOOT2][STARTER_GLOBAL_STATE]",sv,"B62"),
        ("[NBOOT2][STARTER_WAIT_ANY]",sv,"B68"),
        ("[NBOOT2][STARTER_IPC_ARM]",se,"B70"),
        ("[NBOOT2][SIM_PS]",sv,"B70 SIM P&S"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sat,"B64"),
        ("[NBOOT2][ALARM_ID_LIST]",al,"B69"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    sig="    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h, kernel::entity_exit_type etype, std::int32_t reason, eka2l1::ptr<desc8> reason_des) {"
    start=sv.find(sig)
    end=sv.find("\n    BRIDGE_FUNC(",start+len(sig))
    if start<0 or end<0:
        fail("thread_kill block not found")
    body=sv[start:end]

    anchor="        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"
    if body.count(anchor)!=1:
        fail(f"thread_kill dispatch anchor count={body.count(anchor)}")

    # MENUUI4 creates these exact variables before the dispatch anchor.
    for need in (
        "kernel::thread *caller_thr = kern->crr_thread();",
        "kernel::process *caller_pr = kern->crr_process();",
        "kernel::process *target_pr = thr->owning_process();",
        "auto *cpu = kern->get_cpu();",
    ):
        if need not in body:
            fail("MENUUI4 variable missing: "+need)

    inject=r'''        // B71 PHONEUICONE14RES1: observe only the proven Telephone
        // self-panic. Preserve the original thr->kill() call below verbatim.
        const std::uint32_t nboot2_b71_target_uid3 = target_pr
            ? static_cast<std::uint32_t>(
                std::get<2>(target_pr->get_uid_type())) : 0;
        const bool nboot2_b71_phoneui_cone14 =
            cpu && caller_thr && caller_pr && target_pr
            && (caller_thr->unique_id() == thr->unique_id())
            && (nboot2_b71_target_uid3 == 0x100058B3U)
            && (reason == 14)
            && (exit_category == "CONE");

        if (nboot2_b71_phoneui_cone14) {
            const std::uint32_t pc=cpu->get_pc();
            const std::uint32_t lr=cpu->get_reg(14);
            const std::uint32_t sp=cpu->get_reg(13);
            const std::uint32_t cpsr=cpu->get_cpsr();

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
                "thread={} reason={} category={} pc=0x{:08X} lr=0x{:08X} "
                "sp=0x{:08X} cpsr=0x{:08X} "
                "r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} "
                "r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} "
                "r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} "
                "r12=0x{:08X} behavior=OBSERVE_ONLY",
                target_pr->name(),nboot2_b71_target_uid3,thr->name(),
                reason,exit_category,pc,lr,sp,cpsr,
                cpu->get_reg(0),cpu->get_reg(1),cpu->get_reg(2),
                cpu->get_reg(3),cpu->get_reg(4),cpu->get_reg(5),
                cpu->get_reg(6),cpu->get_reg(7),cpu->get_reg(8),
                cpu->get_reg(9),cpu->get_reg(10),cpu->get_reg(11),
                cpu->get_reg(12));

            auto nboot2_b71_log_frame =
                [&](const char *kind,const std::uint32_t raw) {
                    const std::uint32_t addr=raw & ~1U;
                    codeseg_ptr seg=get_codeseg_from_addr(
                        kern,caller_pr,addr,false);
                    if (seg) {
                        const std::uint32_t base=
                            seg->get_code_run_addr(caller_pr);
                        LOG_WARN(KERNEL,
                            "[NBOOT2][CONE14_FRAME] kind={} raw=0x{:08X} "
                            "module={} base=0x{:08X} offset=0x{:08X}",
                            kind,raw,
                            common::ucs2_to_utf8(seg->get_full_path()),
                            base,addr-base);
                    } else {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][CONE14_FRAME] kind={} raw=0x{:08X} "
                            "module=<unresolved>",kind,raw);
                    }
                };
            nboot2_b71_log_frame("pc",pc);
            nboot2_b71_log_frame("lr",lr);

            std::uint32_t nboot2_b71_phoneui_candidates=0;
            constexpr std::uint32_t nboot2_b71_stack_words=128;
            for (std::uint32_t i=0;i<nboot2_b71_stack_words;++i) {
                const std::uint32_t slot_addr=
                    sp+i*sizeof(std::uint32_t);
                if (slot_addr<sp) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} "
                        "slot=<overflow> stopping=1",i);
                    break;
                }
                const std::uint32_t *slot=
                    eka2l1::ptr<std::uint32_t>(slot_addr).get(caller_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "mapped=0 stopping=1",i,slot_addr);
                    break;
                }

                const std::uint32_t value=*slot;
                const std::uint32_t candidate=value & ~1U;
                const bool phoneui_res_base=
                    ((value & 0xFFFFF000U) == 0x4E738000U);
                const std::uint32_t phoneui_res_index=value & 0xFFFU;
                const bool phoneui_res_in_file=
                    phoneui_res_base && (phoneui_res_index>=1U)
                    && (phoneui_res_index<=0x170U);
                if (phoneui_res_base) {
                    ++nboot2_b71_phoneui_candidates;
                }

                codeseg_ptr seg=candidate>=0x10000U
                    ? get_codeseg_from_addr(
                        kern,caller_pr,candidate,false)
                    : nullptr;
                if (seg) {
                    const std::uint32_t base=
                        seg->get_code_run_addr(caller_pr);
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "value=0x{:08X} code_candidate=1 module={} "
                        "base=0x{:08X} offset=0x{:08X} "
                        "phoneui_res_base={} phoneui_res_index=0x{:03X} "
                        "phoneui_res_in_file={}",
                        i,slot_addr,value,
                        common::ucs2_to_utf8(seg->get_full_path()),
                        base,candidate-base,phoneui_res_base?1:0,
                        phoneui_res_index,phoneui_res_in_file?1:0);
                } else {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "value=0x{:08X} code_candidate=0 "
                        "phoneui_res_base={} phoneui_res_index=0x{:03X} "
                        "phoneui_res_in_file={}",
                        i,slot_addr,value,phoneui_res_base?1:0,
                        phoneui_res_index,phoneui_res_in_file?1:0);
                }
            }

            for (std::uint32_t r=0;r<13;++r) {
                const std::uint32_t value=cpu->get_reg(r);
                const bool phoneui_res_base=
                    ((value & 0xFFFFF000U) == 0x4E738000U);
                if (phoneui_res_base) {
                    const std::uint32_t idx=value & 0xFFFU;
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_RESID_CANDIDATE] source=REG "
                        "reg=r{} value=0x{:08X} res_index=0x{:03X} "
                        "in_phoneui_r01={}",
                        r,value,idx,
                        ((idx>=1U)&&(idx<=0x170U))?1:0);
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_SUMMARY] phoneui_signature_base=0x4E738000 "
                "phoneui_resource_count=368 expected_last_index=0x170 "
                "stack_candidates={} stack_words_scanned={} "
                "panic_behavior=UNCHANGED behavior=OBSERVE_ONLY",
                nboot2_b71_phoneui_candidates,nboot2_b71_stack_words);
        }

'''
    body=body.replace(anchor,inject+anchor,1)
    sv=sv[:start]+body+sv[end:]

    for need in (
        "[NBOOT2][CONE14_PHONEUI]",
        "[NBOOT2][CONE14_FRAME]",
        "[NBOOT2][CONE14_STACK]",
        "[NBOOT2][CONE14_RESID_CANDIDATE]",
        "[NBOOT2][CONE14_SUMMARY]",
        "0x100058B3U",
        "0x4E738000U",
        "0x170U",
        "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
    ):
        if need not in sv:
            fail("post-apply gate missing: "+need)

    # Explicitly prohibit the tempting but invalid shortcuts.
    b71=inject
    for forbidden in (
        "reason = 0",
        "reason=0",
        "set_int(101)",
        "requested=102",
        "ESimUsable",
        "error_none)",
        "return 0;",
    ):
        if forbidden in b71:
            fail("behavior-changing token in B71 block: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    svc.write_text(sv,encoding="utf-8")
    print(MARK+": applied")
    print("scope=TELEPHONE_CONE14_DIAGNOSTIC_ONLY")
    print("telephone_uid3=0x100058B3")
    print("phoneui_resource_base=0x4E738000")
    print("phoneui_resource_count=368")
    print("stack_words=128")
    print("panic_behavior=UNCHANGED")
    print("starter_state=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("B61_B64_B68_B69_B70=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
