#!/usr/bin/env python3
"""NATIVEBOOT2 B68 STARTERWAKE1.

RM-356 SYM.RPKG analysis resolves the normal-mode StartingCriticalApps list
(RID6) and B66 DEVICE1 proves its final process, profilesettingsmonitor.exe,
rendezvouses successfully. No global-state request for 102 follows.

B66 also shows a KErrCancel completion for SYSSTART/StarterServer immediately
after each successful WaitForStart rendezvous, including the final RID6 item.
Earlier identical cancel completions do not stop Starter, so B68 must compare
request/scheduler accounting rather than treating KErrCancel itself as causal.

B68 is diagnostic-only and traces:
- SYSSTART notify_info completion before/after request semaphore signaling;
- the B65 rendezvous completion boundary with request status/count/state;
- SYSSTART WaitForAnyRequest before/after the semaphore wait operation;
- scheduler switch-to SYSSTART/StarterServer;
- every SYSSTART SVC number after wakeup.

No request status value, signal count, scheduler decision, process behavior,
P&S value, IPC result, rendezvous behavior, graphics, or teardown behavior is
changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B68-STARTERWAKE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b68_starterwake1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    proc=up/"src/emu/kernel/src/process.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    fs=up/"src/emu/services/src/fs/files.cpp"

    for p in (proc,thr,svc,sched,lib,sa,fs):
        if not p.is_file():
            fail(f"missing source: {p}")

    pr=proc.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sc=sched.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")

    combined="\n".join((pr,th,sv,sc,lm))
    if "[NBOOT2][STARTER_WAKE]" in combined:
        print(MARK+": already applied")
        return

    # Preserve the evidence-producing chain.
    gates=(
        ("[NBOOT2][STARTER_RENDEZVOUS]",pr,"B65"),
        ("[NBOOT2][EIKCANCEL_NOTIFY]",th,"B33"),
        ("[NBOOT2][SCHED_STALE_READY_DROP]",sc,"B31"),
        ("[NBOOT2][STARTER_GLOBAL_STATE]",sv,"B62"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sa.read_text(encoding="utf-8"),"B64"),
        ("[NBOOT2][STARTER_SSC_DUMP]",fs.read_text(encoding="utf-8"),"B67"),
    )
    for needle,text,name in gates:
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # 1) B65 rendezvous boundary: capture the exact request status and the
    # StarterServer request-semaphore/thread state before and after complete().
    old='''            ren.complete(rendezvous_reason);
            LOG_TRACE(KERNEL, "Rendezvous to: {}", ren.requester->name());
'''
    new='''            const std::uint32_t nboot2_b68_rendezvous_sts =
                ren.sts.ptr_address();
            const int nboot2_b68_request_count_before =
                ren.requester ? ren.requester->request_count() : -9999;
            const int nboot2_b68_thread_state_before =
                ren.requester
                    ? static_cast<int>(ren.requester->current_state())
                    : -1;

            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_WAKE] phase=rendezvous_before "
                    "target_process={} target_uid3=0x{:08X} reason={} "
                    "request_status=0x{:08X} requester_thread={} "
                    "request_count={} thread_state={} behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), rendezvous_reason,
                    nboot2_b68_rendezvous_sts,
                    ren.requester ? ren.requester->name()
                                  : std::string("<null>"),
                    nboot2_b68_request_count_before,
                    nboot2_b68_thread_state_before);
            }

            ren.complete(rendezvous_reason);

            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_WAKE] phase=rendezvous_after "
                    "target_process={} target_uid3=0x{:08X} reason={} "
                    "request_status=0x{:08X} requester_thread={} "
                    "request_count_before={} request_count_after={} "
                    "thread_state_before={} thread_state_after={} "
                    "behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), rendezvous_reason,
                    nboot2_b68_rendezvous_sts,
                    ren.requester ? ren.requester->name()
                                  : std::string("<null>"),
                    nboot2_b68_request_count_before,
                    ren.requester ? ren.requester->request_count() : -9999,
                    nboot2_b68_thread_state_before,
                    ren.requester
                        ? static_cast<int>(ren.requester->current_state())
                        : -1);
            }

            LOG_TRACE(KERNEL, "Rendezvous to: {}", ren.requester->name());
'''
    pr=rep1(pr,old,new,"B68 rendezvous wake boundary")

    # 2) Generic notify completion: this catches both rendezvous status and the
    # timeout/cancel TRequestStatus used by Starter's WaitForStart helper.
    old='''            epoc::request_status *sts_real = sts.get(requester->owning_process());
            if (sts_real)
                sts_real->set(err_code, kern->is_eka1());

            sts = 0;
            requester->signal_request();
'''
    new='''            kernel::process *nboot2_b68_requester_process =
                requester ? requester->owning_process() : nullptr;
            const bool nboot2_b68_starter =
                nboot2_b68_requester_process &&
                (nboot2_b68_requester_process->get_uid() == 0x100059C9U);
            const std::uint32_t nboot2_b68_notify_sts = sts.ptr_address();
            const int nboot2_b68_request_count_before =
                requester ? requester->request_count() : -9999;
            const int nboot2_b68_thread_state_before =
                requester
                    ? static_cast<int>(requester->current_state())
                    : -1;

            if (nboot2_b68_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_NOTIFY_WAKE] phase=before "
                    "result={} request_status=0x{:08X} requester_thread={} "
                    "request_count={} thread_state={} behavior=OBSERVE_ONLY",
                    err_code, nboot2_b68_notify_sts,
                    requester ? requester->name() : std::string("<null>"),
                    nboot2_b68_request_count_before,
                    nboot2_b68_thread_state_before);
            }

            epoc::request_status *sts_real = sts.get(requester->owning_process());
            if (sts_real)
                sts_real->set(err_code, kern->is_eka1());

            sts = 0;
            requester->signal_request();

            if (nboot2_b68_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_NOTIFY_WAKE] phase=after "
                    "result={} request_status=0x{:08X} requester_thread={} "
                    "status_ptr_valid={} request_count_before={} "
                    "request_count_after={} thread_state_before={} "
                    "thread_state_after={} behavior=OBSERVE_ONLY",
                    err_code, nboot2_b68_notify_sts,
                    requester ? requester->name() : std::string("<null>"),
                    sts_real != nullptr,
                    nboot2_b68_request_count_before,
                    requester ? requester->request_count() : -9999,
                    nboot2_b68_thread_state_before,
                    requester
                        ? static_cast<int>(requester->current_state())
                        : -1);
            }
'''
    th=rep1(th,old,new,"B68 notify wake accounting")

    # 3) WaitForAnyRequest: show whether Starter consumes an already queued
    # request signal or actually blocks on its private request semaphore.
    old='''    BRIDGE_FUNC(void, wait_for_any_request) {
        kern->crr_thread()->wait_for_any_request();
    }
'''
    new='''    BRIDGE_FUNC(void, wait_for_any_request) {
        kernel::thread *nboot2_b68_thr = kern->crr_thread();
        kernel::process *nboot2_b68_pr = kern->crr_process();
        const bool nboot2_b68_starter =
            nboot2_b68_pr && (nboot2_b68_pr->get_uid() == 0x100059C9U);

        if (nboot2_b68_starter && nboot2_b68_thr) {
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_WAIT_ANY] phase=before thread={} "
                "request_count={} thread_state={} behavior=OBSERVE_ONLY",
                nboot2_b68_thr->name(),
                nboot2_b68_thr->request_count(),
                static_cast<int>(nboot2_b68_thr->current_state()));
        }

        kern->crr_thread()->wait_for_any_request();

        if (nboot2_b68_starter && nboot2_b68_thr) {
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_WAIT_ANY] phase=after_call thread={} "
                "request_count={} thread_state={} behavior=OBSERVE_ONLY",
                nboot2_b68_thr->name(),
                nboot2_b68_thr->request_count(),
                static_cast<int>(nboot2_b68_thr->current_state()));
        }
    }
'''
    sv=rep1(sv,old,new,"B68 WaitForAnyRequest trace")

    # 4) Scheduler: prove whether StarterServer is selected again after a notify
    # completion. This does not alter the selected thread.
    old='''        if (newt) {
            // cancel wake up
'''
    new='''        if (newt) {
            kernel::process *nboot2_b68_new_owner = newt->owning_process();
            if (nboot2_b68_new_owner &&
                (nboot2_b68_new_owner->get_uid() == 0x100059C9U)) {
                kernel::process *nboot2_b68_old_owner =
                    oldt ? oldt->owning_process() : nullptr;
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_SCHED] phase=switch_to "
                    "from_process={} from_thread={} to_process={} "
                    "to_thread={} to_request_count={} to_state_before={} "
                    "behavior=OBSERVE_ONLY",
                    nboot2_b68_old_owner
                        ? nboot2_b68_old_owner->raw_name()
                        : std::string("<none>"),
                    oldt ? oldt->name() : std::string("<none>"),
                    nboot2_b68_new_owner->raw_name(),
                    newt->name(),
                    newt->request_count(),
                    static_cast<int>(newt->current_state()));
            }

            // cancel wake up
'''
    sc=rep1(sc,old,new,"B68 scheduler switch trace")

    # 5) SVC boundary: after a wakeup, this gives the first guest kernel call
    # made by SYSSTART and proves whether guest code actually resumed.
    old='''    bool lib_manager::call_svc(sid svcnum) {
        // Lock the kernel so SVC call can operate in safety
        kern_->lock();
        
        // Trampoline lookup here
'''
    new='''    bool lib_manager::call_svc(sid svcnum) {
        // Lock the kernel so SVC call can operate in safety
        kern_->lock();

        kernel::process *nboot2_b68_pr = kern_->crr_process();
        kernel::thread *nboot2_b68_thr = kern_->crr_thread();
        if (nboot2_b68_pr && nboot2_b68_thr &&
            (nboot2_b68_pr->get_uid() == 0x100059C9U)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_SVC] svc=0x{:X} process={} thread={} "
                "request_count={} thread_state={} behavior=OBSERVE_ONLY",
                svcnum,
                nboot2_b68_pr->raw_name(),
                nboot2_b68_thr->name(),
                nboot2_b68_thr->request_count(),
                static_cast<int>(nboot2_b68_thr->current_state()));
        }
        
        // Trampoline lookup here
'''
    lm=rep1(lm,old,new,"B68 SYSSTART SVC trace")

    # Diagnostic-only scope guards.
    patched="\n".join((pr,th,sv,sc,lm))
    for need in (
        "[NBOOT2][STARTER_WAKE]",
        "[NBOOT2][STARTER_NOTIFY_WAKE]",
        "[NBOOT2][STARTER_WAIT_ANY]",
        "[NBOOT2][STARTER_SCHED]",
        "[NBOOT2][STARTER_SVC]",
        "0x100059C9U",
        "behavior=OBSERVE_ONLY",
    ):
        if need not in patched:
            fail("post-apply marker/semantic missing: "+need)

    # Never change the operations under observation.
    for forbidden in (
        "requested=102",
        "ESwStateSelfTestOK",
        "set_int(0x101F8766",
        "signal_request(2",
        "signal_request(0",
        "error_cancel = error_none",
    ):
        if forbidden in patched:
            fail("B68 behavior injection detected: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    proc.write_text(pr,encoding="utf-8")
    thr.write_text(th,encoding="utf-8")
    svc.write_text(sv,encoding="utf-8")
    sched.write_text(sc,encoding="utf-8")
    lib.write_text(lm,encoding="utf-8")

    print(MARK+": applied")
    print("scope=SYSSTART_REQUEST_WAKE_SCHED_SVC_DIAGNOSTIC")
    print("target_process_uid3=0x100059C9")
    print("state_injection=NONE")
    print("signal_count_change=NONE")
    print("scheduler_behavior_change=NONE")
    print("rendezvous_behavior_change=NONE")
    print("B31_B33_B62_B64_B65_B67=PRESERVED")

if __name__=="__main__":
    main()
