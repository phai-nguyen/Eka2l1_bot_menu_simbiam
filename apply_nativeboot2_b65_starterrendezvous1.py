#!/usr/bin/env python3
"""NATIVEBOOT2 B65 STARTERRENDEZVOUS1.

B64 DEVICE1 proves EExecuteSelftests/0x67 now returns a valid RM-356
TResponsePckg(KErrNone) envelope and prevents the B63 101->117 fatal path.
However KPSGlobalSystemState remains at 101 StartingCriticalApps and never
reaches 102 SelfTestOK.

After the self-test response, SYSSTART launches multiple critical/UI services.
The existing process.cpp trace only says "Rendezvous to: StarterServer"; it does
not identify the target process Starter armed or which target completed.

B65 is diagnostic-only. It instruments process rendezvous/logon for requests
owned by SYSSTART UID3 0x100059C9:
- arm / queue / immediate-complete
- target process and UID3
- requester thread
- rendezvous completion reason
- cancellation

No process/rendezvous semantics are changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B65-STARTERRENDEZVOUS1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b65_starterrendezvous1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    gs=up/"src/emu/services/src/window/classes/gstore.cpp"

    for f in (p,sa,svc,gs):
        if not f.is_file():
            fail(f"missing source: {f}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTER_RENDEZVOUS]" in text:
        print(MARK+": already applied")
        return

    if "[NBOOT2][SA_SELFTEST_RESPONSE]" not in sa.read_text(encoding="utf-8"):
        fail("B64 self-test response missing")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B62 global-state trace missing")
    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" not in gs.read_text(encoding="utf-8"):
        fail("B61 wipeout guard missing")

    old='''    void process::logon(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        if (!thread_count) {
            (logon_request.get(kern->crr_process()))->set(exit_reason, kern->is_eka1());
            kern->crr_thread()->signal_request();

            return;
        }
        epoc::notify_info info(logon_request, kern->crr_thread());

        if (rendezvous) {
            if (handle_rendezvous_request(info)) {
                return;
            }

            rendezvous_requests.push_back(info);
            return;
        }

        logon_requests.push_back(info);
    }
'''
    new='''    void process::logon(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        kernel::process *nboot2_b65_requester_process = kern->crr_process();
        kernel::thread *nboot2_b65_requester_thread = kern->crr_thread();
        const bool nboot2_b65_starter =
            rendezvous && nboot2_b65_requester_process &&
            (nboot2_b65_requester_process->get_uid() == 0x100059C9U);

        if (!thread_count) {
            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_RENDEZVOUS] phase=arm_dead_target "
                    "target_process={} target_uid3=0x{:08X} thread_count={} "
                    "requester_process={} requester_thread={} exit_reason={} "
                    "action=COMPLETE_IMMEDIATE behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), thread_count,
                    nboot2_b65_requester_process->raw_name(),
                    nboot2_b65_requester_thread
                        ? nboot2_b65_requester_thread->name()
                        : std::string("<null>"),
                    exit_reason);
            }

            (logon_request.get(kern->crr_process()))->set(exit_reason, kern->is_eka1());
            kern->crr_thread()->signal_request();

            return;
        }
        epoc::notify_info info(logon_request, kern->crr_thread());

        if (rendezvous) {
            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_RENDEZVOUS] phase=arm "
                    "target_process={} target_uid3=0x{:08X} thread_count={} "
                    "queued_before={} requester_process={} requester_thread={} "
                    "behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), thread_count,
                    rendezvous_requests.size(),
                    nboot2_b65_requester_process->raw_name(),
                    nboot2_b65_requester_thread
                        ? nboot2_b65_requester_thread->name()
                        : std::string("<null>"));
            }

            if (handle_rendezvous_request(info)) {
                if (nboot2_b65_starter) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][STARTER_RENDEZVOUS] phase=handled_immediate "
                        "target_process={} target_uid3=0x{:08X} "
                        "requester_process={} requester_thread={} "
                        "behavior=OBSERVE_ONLY",
                        raw_name(), get_uid(),
                        nboot2_b65_requester_process->raw_name(),
                        nboot2_b65_requester_thread
                            ? nboot2_b65_requester_thread->name()
                            : std::string("<null>"));
                }
                return;
            }

            rendezvous_requests.push_back(info);
            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_RENDEZVOUS] phase=queued "
                    "target_process={} target_uid3=0x{:08X} queued_after={} "
                    "requester_process={} requester_thread={} "
                    "behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), rendezvous_requests.size(),
                    nboot2_b65_requester_process->raw_name(),
                    nboot2_b65_requester_thread
                        ? nboot2_b65_requester_thread->name()
                        : std::string("<null>"));
            }
            return;
        }

        logon_requests.push_back(info);
    }
'''
    text=rep1(text,old,new,"process::logon")

    old='''    bool process::logon_cancel(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        decltype(rendezvous_requests) *container = rendezvous ? &rendezvous_requests : &logon_requests;

        const auto find_result = std::find(container->begin(), container->end(), epoc::notify_info(logon_request, kern->crr_thread()));

        if (find_result == container->end()) {
            return false;
        }

        find_result->complete(-3);
        container->erase(find_result);
        return true;
    }
'''
    new='''    bool process::logon_cancel(eka2l1::ptr<epoc::request_status> logon_request, bool rendezvous) {
        decltype(rendezvous_requests) *container = rendezvous ? &rendezvous_requests : &logon_requests;

        const auto find_result = std::find(container->begin(), container->end(), epoc::notify_info(logon_request, kern->crr_thread()));

        kernel::process *nboot2_b65_requester_process = kern->crr_process();
        kernel::thread *nboot2_b65_requester_thread = kern->crr_thread();
        const bool nboot2_b65_starter =
            rendezvous && nboot2_b65_requester_process &&
            (nboot2_b65_requester_process->get_uid() == 0x100059C9U);

        if (find_result == container->end()) {
            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_RENDEZVOUS] phase=cancel_miss "
                    "target_process={} target_uid3=0x{:08X} queued={} "
                    "requester_process={} requester_thread={} behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), container->size(),
                    nboot2_b65_requester_process->raw_name(),
                    nboot2_b65_requester_thread
                        ? nboot2_b65_requester_thread->name()
                        : std::string("<null>"));
            }
            return false;
        }

        if (nboot2_b65_starter) {
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_RENDEZVOUS] phase=cancel "
                "target_process={} target_uid3=0x{:08X} queued_before={} "
                "requester_process={} requester_thread={} completion=-3 "
                "behavior=OBSERVE_ONLY",
                raw_name(), get_uid(), container->size(),
                nboot2_b65_requester_process->raw_name(),
                nboot2_b65_requester_thread
                    ? nboot2_b65_requester_thread->name()
                    : std::string("<null>"));
        }

        find_result->complete(-3);
        container->erase(find_result);
        return true;
    }
'''
    text=rep1(text,old,new,"process::logon_cancel")

    old='''    void process::rendezvous(int rendezvous_reason) {
        exit_reason = rendezvous_reason;
        exit_type = entity_exit_type::pending;

        for (auto &ren : rendezvous_requests) {
            ren.complete(rendezvous_reason);
            LOG_TRACE(KERNEL, "Rendezvous to: {}", ren.requester->name());
        }

        rendezvous_requests.clear();
    }
'''
    new='''    void process::rendezvous(int rendezvous_reason) {
        exit_reason = rendezvous_reason;
        exit_type = entity_exit_type::pending;

        for (auto &ren : rendezvous_requests) {
            kernel::process *nboot2_b65_requester_process =
                ren.requester ? ren.requester->owning_process() : nullptr;
            const bool nboot2_b65_starter =
                nboot2_b65_requester_process &&
                (nboot2_b65_requester_process->get_uid() == 0x100059C9U);

            if (nboot2_b65_starter) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_RENDEZVOUS] phase=complete "
                    "target_process={} target_uid3=0x{:08X} reason={} "
                    "queued_before={} requester_process={} requester_thread={} "
                    "behavior=OBSERVE_ONLY",
                    raw_name(), get_uid(), rendezvous_reason,
                    rendezvous_requests.size(),
                    nboot2_b65_requester_process->raw_name(),
                    ren.requester ? ren.requester->name()
                                  : std::string("<null>"));
            }

            ren.complete(rendezvous_reason);
            LOG_TRACE(KERNEL, "Rendezvous to: {}", ren.requester->name());
        }

        rendezvous_requests.clear();
    }
'''
    text=rep1(text,old,new,"process::rendezvous")

    if text.count("[NBOOT2][STARTER_RENDEZVOUS]") < 6:
        fail("marker count too low")

    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=SYSSTART_RENDEZVOUS_DIAGNOSTIC_ONLY")
    print("target_uid3=0x100059C9")
    print("phases=arm_queued_complete_cancel")
    print("process_semantics=UNCHANGED")
    print("state_injection=NONE")
    print("B61_B62_B64=PRESERVED")

if __name__=="__main__":
    main()
