#!/usr/bin/env python3
"""NATIVEBOOT2 B66 STARTERIPC1.

B65 DEVICE1:
- after global state 101, SYSSTART only arms profilesettingsmonitor through the
  normal process rendezvous path;
- profilesettingsmonitor completes reason=0;
- no later SYSSTART process-rendezvous remains unresolved;
- global state nevertheless stays at 101.

Therefore the remaining StartingCriticalApps blocker is not a normal process
rendezvous. B66 traces HLE IPC requests owned by SYSSTART UID3 0x100059C9.

For each accepted IPC, log:
- dispatch: server, function, session, requester process/thread, async status
- complete: server, function, result, session, requester process/thread

A dispatch with no matching completion is the exact pending HLE IPC boundary.
No IPC result or scheduling behavior is changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-STARTERIPC1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b66_starteripc1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/services/src/context.cpp"
    proc=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    gs=up/"src/emu/services/src/window/classes/gstore.cpp"

    for f in (p,proc,sa,svc,gs):
        if not f.is_file():
            fail(f"missing source: {f}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTER_IPC]" in text:
        print(MARK+": already applied")
        return

    if "[NBOOT2][STARTER_RENDEZVOUS]" not in proc.read_text(encoding="utf-8"):
        fail("B65 rendezvous trace missing")
    if "[NBOOT2][SA_SELFTEST_RESPONSE]" not in sa.read_text(encoding="utf-8"):
        fail("B64 self-test response missing")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B62 global-state trace missing")
    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" not in gs.read_text(encoding="utf-8"):
        fail("B61 wipeout guard missing")

    old='''        void ipc_context::complete(int res) {
            if (msg->request_sts) {
                kernel_system *kern = sys->get_kernel_system();
                (msg->request_sts.get(msg->own_thr->owning_process()))->set(res, kern->is_eka1());

                // Avoid signal twice to cause undefined behavior
                if (!signaled) {
                    msg->own_thr->signal_request();
                    signaled = true;
                }
            }
        }
'''
    new='''        void ipc_context::complete(int res) {
            kernel::process *nboot2_b66_pr =
                (msg && msg->own_thr) ? msg->own_thr->owning_process() : nullptr;
            if (nboot2_b66_pr && (nboot2_b66_pr->get_uid() == 0x100059C9U)) {
                std::string nboot2_b66_server = "<null>";
                std::uint64_t nboot2_b66_session = 0;
                if (msg->msg_session) {
                    nboot2_b66_session = msg->msg_session->unique_id();
                    if (msg->msg_session->get_server()) {
                        nboot2_b66_server =
                            msg->msg_session->get_server()->name();
                    }
                }

                LOG_WARN(SERVICE_TRACK,
                    "[NBOOT2][STARTER_IPC] phase=complete "
                    "server={} func=0x{:08X} result={} session={} "
                    "process={} thread={} has_request_status={} "
                    "signaled_before={} behavior=OBSERVE_ONLY",
                    nboot2_b66_server,
                    static_cast<std::uint32_t>(msg->function),
                    res,
                    nboot2_b66_session,
                    nboot2_b66_pr->raw_name(),
                    msg->own_thr ? msg->own_thr->name()
                                 : std::string("<null>"),
                    static_cast<bool>(msg->request_sts),
                    signaled);
            }

            if (msg->request_sts) {
                kernel_system *kern = sys->get_kernel_system();
                (msg->request_sts.get(msg->own_thr->owning_process()))->set(res, kern->is_eka1());

                // Avoid signal twice to cause undefined behavior
                if (!signaled) {
                    msg->own_thr->signal_request();
                    signaled = true;
                }
            }
        }
'''
    text=rep1(text,old,new,"ipc_context::complete")

    old='''            int func = process_msg->function;

            auto func_ite = ipc_funcs.find(func);
'''
    new='''            int func = process_msg->function;

            kernel::process *nboot2_b66_pr =
                process_msg->own_thr
                    ? process_msg->own_thr->owning_process()
                    : nullptr;
            if (nboot2_b66_pr &&
                (nboot2_b66_pr->get_uid() == 0x100059C9U)) {
                LOG_WARN(SERVICE_TRACK,
                    "[NBOOT2][STARTER_IPC] phase=dispatch "
                    "server={} func=0x{:08X} session={} process={} thread={} "
                    "has_request_status={} ipc_flag=0x{:08X} behavior=OBSERVE_ONLY",
                    obj_name,
                    static_cast<std::uint32_t>(func),
                    process_msg->msg_session
                        ? process_msg->msg_session->unique_id() : 0,
                    nboot2_b66_pr->raw_name(),
                    process_msg->own_thr
                        ? process_msg->own_thr->name()
                        : std::string("<null>"),
                    static_cast<bool>(process_msg->request_sts),
                    static_cast<std::uint32_t>(process_msg->args.flag));
            }

            auto func_ite = ipc_funcs.find(func);
'''
    text=rep1(text,old,new,"server::process_accepted_msg dispatch")

    if text.count("[NBOOT2][STARTER_IPC]")!=2:
        fail("B66 marker count mismatch")
    if "0x101F8766" in text or "0x100058F4" in text:
        # context.cpp should remain completely generic.
        fail("state injection/reference found in context.cpp")

    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=SYSSTART_HLE_IPC_DIAGNOSTIC_ONLY")
    print("target_uid3=0x100059C9")
    print("phases=dispatch_complete")
    print("ipc_semantics=UNCHANGED")
    print("state_injection=NONE")
    print("B61_B62_B64_B65=PRESERVED")

if __name__=="__main__":
    main()
