#!/usr/bin/env python3
"""NATIVEBOOT2 B66 CRITICALAPPWAIT1.

B65 DEVICE1 resolves all direct SYSSTART/StarterServer process rendezvous waits.
After state 101 + successful selftest:
- profilesettingsmonitor is armed directly by SYSSTART and completes reason 0;
- sysap.exe is spawned but has no direct SYSSTART rendezvous arm;
- global state remains 101.

Reference Symbian critical-app startup uses deferred StartApplication for SysAp
and a MultipleWait barrier, so an indirect application-start helper/StartSafe
wait may exist outside the SYSSTART requester filter.

B66 is diagnostic-only. It traces target-side wait/signal lifecycle regardless
of requester identity for:
- sysap (UID3 0x100058F3)
- profilesettingsmonitor (UID3 0x10207B7D)
- ailaunch/Home-screen launch path (UID3 0x102750F0)
- cfserver (name match)

It logs:
- target arm: rendezvous vs logon, requester identity, queue state
- target signal: Rendezvous(reason), including zero-waiter signals
- target completion delivery to requester
- target cancel
- pending queue sizes at process finish

No process or startup semantics are modified.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-CRITICALAPPWAIT1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b66_criticalappwait1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    gs=up/"src/emu/services/src/window/classes/gstore.cpp"

    for f in (p,sa,svc,gs):
        if not f.is_file():
            fail(f"missing source: {f}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][CRITICAL_APP_WAIT]" in text:
        print(MARK+": already applied")
        return

    for gate in (
        "[NBOOT2][STARTER_RENDEZVOUS]",
    ):
        if gate not in text:
            fail("B65 gate missing: "+gate)
    if "[NBOOT2][SA_SELFTEST_RESPONSE]" not in sa.read_text(encoding="utf-8"):
        fail("B64 selftest response missing")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B62 global-state trace missing")
    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" not in gs.read_text(encoding="utf-8"):
        fail("B61 wipeout guard missing")

    # Add helper local predicate at top of process::logon.
    anchor='''    void process::logon(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        kernel::process *nboot2_b65_requester_process = kern->crr_process();
'''
    inject='''    void process::logon(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        const std::string nboot2_b66_target_name = raw_name();
        const std::uint32_t nboot2_b66_target_uid = get_uid();
        const bool nboot2_b66_target =
            (nboot2_b66_target_uid == 0x100058F3U) ||
            (nboot2_b66_target_uid == 0x10207B7DU) ||
            (nboot2_b66_target_uid == 0x102750F0U) ||
            (nboot2_b66_target_name == "cfserver") ||
            (nboot2_b66_target_name == "!cfserver");
        kernel::process *nboot2_b66_req_process = kern->crr_process();
        kernel::thread *nboot2_b66_req_thread = kern->crr_thread();

        if (nboot2_b66_target) {
            LOG_WARN(KERNEL,
                "[NBOOT2][CRITICAL_APP_WAIT] phase=arm "
                "target_process={} target_uid3=0x{:08X} mode={} "
                "thread_count={} rendezvous_q={} logon_q={} "
                "requester_process={} requester_uid3=0x{:08X} requester_thread={} "
                "behavior=OBSERVE_ONLY",
                nboot2_b66_target_name,
                nboot2_b66_target_uid,
                rendezvous ? "RENDEZVOUS" : "LOGON",
                thread_count,
                rendezvous_requests.size(),
                logon_requests.size(),
                nboot2_b66_req_process ? nboot2_b66_req_process->raw_name()
                                       : std::string("<null>"),
                nboot2_b66_req_process ? nboot2_b66_req_process->get_uid() : 0,
                nboot2_b66_req_thread ? nboot2_b66_req_thread->name()
                                      : std::string("<null>"));
        }

        kernel::process *nboot2_b65_requester_process = kern->crr_process();
'''
    text=rep1(text,anchor,inject,"logon entry")

    # Add target-side cancel trace after B65 requester setup.
    anchor='''        const bool nboot2_b65_starter =
            rendezvous && nboot2_b65_requester_process &&
            (nboot2_b65_requester_process->get_uid() == 0x100059C9U);

        if (find_result == container->end()) {
'''
    inject='''        const bool nboot2_b65_starter =
            rendezvous && nboot2_b65_requester_process &&
            (nboot2_b65_requester_process->get_uid() == 0x100059C9U);

        const std::string nboot2_b66_target_name = raw_name();
        const std::uint32_t nboot2_b66_target_uid = get_uid();
        const bool nboot2_b66_target =
            (nboot2_b66_target_uid == 0x100058F3U) ||
            (nboot2_b66_target_uid == 0x10207B7DU) ||
            (nboot2_b66_target_uid == 0x102750F0U) ||
            (nboot2_b66_target_name == "cfserver") ||
            (nboot2_b66_target_name == "!cfserver");
        if (nboot2_b66_target) {
            LOG_WARN(KERNEL,
                "[NBOOT2][CRITICAL_APP_WAIT] phase=cancel_request "
                "target_process={} target_uid3=0x{:08X} mode={} "
                "found={} queued={} requester_process={} requester_uid3=0x{:08X} "
                "requester_thread={} behavior=OBSERVE_ONLY",
                nboot2_b66_target_name,
                nboot2_b66_target_uid,
                rendezvous ? "RENDEZVOUS" : "LOGON",
                find_result != container->end(),
                container->size(),
                nboot2_b65_requester_process
                    ? nboot2_b65_requester_process->raw_name()
                    : std::string("<null>"),
                nboot2_b65_requester_process
                    ? nboot2_b65_requester_process->get_uid() : 0,
                nboot2_b65_requester_thread
                    ? nboot2_b65_requester_thread->name()
                    : std::string("<null>"));
        }

        if (find_result == container->end()) {
'''
    text=rep1(text,anchor,inject,"cancel trace")

    # Log target's own Rendezvous call even when there are no waiters.
    anchor='''    void process::rendezvous(int rendezvous_reason) {
        exit_reason = rendezvous_reason;
        exit_type = entity_exit_type::pending;

        for (auto &ren : rendezvous_requests) {
'''
    inject='''    void process::rendezvous(int rendezvous_reason) {
        exit_reason = rendezvous_reason;
        exit_type = entity_exit_type::pending;

        const std::string nboot2_b66_target_name = raw_name();
        const std::uint32_t nboot2_b66_target_uid = get_uid();
        const bool nboot2_b66_target =
            (nboot2_b66_target_uid == 0x100058F3U) ||
            (nboot2_b66_target_uid == 0x10207B7DU) ||
            (nboot2_b66_target_uid == 0x102750F0U) ||
            (nboot2_b66_target_name == "cfserver") ||
            (nboot2_b66_target_name == "!cfserver");
        if (nboot2_b66_target) {
            LOG_WARN(KERNEL,
                "[NBOOT2][CRITICAL_APP_WAIT] phase=target_signal "
                "target_process={} target_uid3=0x{:08X} reason={} "
                "rendezvous_waiters={} logon_waiters={} behavior=OBSERVE_ONLY",
                nboot2_b66_target_name,
                nboot2_b66_target_uid,
                rendezvous_reason,
                rendezvous_requests.size(),
                logon_requests.size());
        }

        for (auto &ren : rendezvous_requests) {
'''
    text=rep1(text,anchor,inject,"rendezvous signal")

    # Log target completion delivery regardless of requester identity.
    anchor='''        for (auto &ren : rendezvous_requests) {
            kernel::process *nboot2_b65_requester_process =
                ren.requester ? ren.requester->owning_process() : nullptr;
'''
    inject='''        for (auto &ren : rendezvous_requests) {
            if (nboot2_b66_target) {
                kernel::process *nboot2_b66_rp =
                    ren.requester ? ren.requester->owning_process() : nullptr;
                LOG_WARN(KERNEL,
                    "[NBOOT2][CRITICAL_APP_WAIT] phase=deliver_rendezvous "
                    "target_process={} target_uid3=0x{:08X} reason={} "
                    "requester_process={} requester_uid3=0x{:08X} requester_thread={} "
                    "behavior=OBSERVE_ONLY",
                    nboot2_b66_target_name,
                    nboot2_b66_target_uid,
                    rendezvous_reason,
                    nboot2_b66_rp ? nboot2_b66_rp->raw_name()
                                  : std::string("<null>"),
                    nboot2_b66_rp ? nboot2_b66_rp->get_uid() : 0,
                    ren.requester ? ren.requester->name()
                                  : std::string("<null>"));
            }

            kernel::process *nboot2_b65_requester_process =
                ren.requester ? ren.requester->owning_process() : nullptr;
'''
    text=rep1(text,anchor,inject,"rendezvous delivery")

    # Log pending queues at finish before completing/clearing them.
    anchor='''    void process::finish_logons() {
        // The thread that armed a Logon/Rendezvous lives in another process and may
'''
    inject='''    void process::finish_logons() {
        const std::string nboot2_b66_target_name = raw_name();
        const std::uint32_t nboot2_b66_target_uid = get_uid();
        const bool nboot2_b66_target =
            (nboot2_b66_target_uid == 0x100058F3U) ||
            (nboot2_b66_target_uid == 0x10207B7DU) ||
            (nboot2_b66_target_uid == 0x102750F0U) ||
            (nboot2_b66_target_name == "cfserver") ||
            (nboot2_b66_target_name == "!cfserver");
        if (nboot2_b66_target) {
            LOG_WARN(KERNEL,
                "[NBOOT2][CRITICAL_APP_WAIT] phase=finish "
                "target_process={} target_uid3=0x{:08X} exit_reason={} "
                "rendezvous_waiters={} logon_waiters={} behavior=OBSERVE_ONLY",
                nboot2_b66_target_name,
                nboot2_b66_target_uid,
                exit_reason,
                rendezvous_requests.size(),
                logon_requests.size());
        }

        // The thread that armed a Logon/Rendezvous lives in another process and may
'''
    text=rep1(text,anchor,inject,"finish trace")

    if text.count("[NBOOT2][CRITICAL_APP_WAIT]") < 5:
        fail("marker count too low")

    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=CRITICAL_APP_TARGET_WAIT_DIAGNOSTIC_ONLY")
    print("targets=sysap_profilesettingsmonitor_ailaunch_cfserver")
    print("phases=arm_cancel_target_signal_deliver_finish")
    print("process_semantics=UNCHANGED")
    print("state_injection=NONE")
    print("B61_B62_B64_B65=PRESERVED")

if __name__=="__main__":
    main()
