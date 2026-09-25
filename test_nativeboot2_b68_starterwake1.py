#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B68 STARTERWAKE1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B68-STARTERWAKE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b68_starterwake1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    proc=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    thr=(up/"src/emu/kernel/src/thread.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    sched=(up/"src/emu/kernel/src/scheduler.cpp").read_text(encoding="utf-8")
    lib=(up/"src/emu/kernel/src/libmanager.cpp").read_text(encoding="utf-8")
    timer=(up/"src/emu/kernel/src/timer.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    fs=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")

    need(proc,"[NBOOT2][STARTER_WAKE]","process rendezvous boundary")
    need(proc,"phase=rendezvous_before","process rendezvous boundary")
    need(proc,"phase=rendezvous_after","process rendezvous boundary")
    need(proc,"request_status=0x{:08X}","rendezvous request identity")

    need(thr,"[NBOOT2][STARTER_NOTIFY_WAKE]","notify accounting")
    need(thr,"request_count_before","notify accounting")
    need(thr,"request_count_after","notify accounting")
    need(thr,"requester->signal_request();","original notify signal")

    need(svc,"[NBOOT2][STARTER_WAIT_ANY]","WaitForAnyRequest")
    need(svc,"phase=before","WaitForAnyRequest")
    need(svc,"phase=after_call","WaitForAnyRequest")
    need(svc,"kern->crr_thread()->wait_for_any_request();","original wait")

    need(sched,"[NBOOT2][STARTER_SCHED]","scheduler selection")
    need(sched,"phase=switch_to","scheduler selection")
    need(sched,"switch_context(crr_thread, next_thread);","scheduler semantics")

    need(lib,"[NBOOT2][STARTER_SVC]","SYSSTART SVC trace")
    need(lib,"bool lib_manager::call_svc(sid svcnum)","SVC dispatcher")

    need(timer,"[NBOOT2][STARTER_TIMER]","Starter timer trace")
    need(timer,"phase=arm","Starter timer trace")
    need(timer,"phase=cancel_before","Starter timer trace")
    need(timer,"phase=cancel_after","Starter timer trace")
    need(timer,"info.done_nof.complete(epoc::error_cancel);","original timer cancel")

    # Previous evidence gates stay in chain.
    need(proc,"[NBOOT2][STARTER_RENDEZVOUS]","B65")
    need(thr,"[NBOOT2][EIKCANCEL_NOTIFY]","B33")
    need(sched,"[NBOOT2][SCHED_STALE_READY_DROP]","B31")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64")
    need(fs,"[NBOOT2][STARTER_SSC_DUMP]","B67")

    combined="\n".join((proc,thr,svc,sched,lib,timer))
    for forbidden in (
        "requested=102",
        "ESwStateSelfTestOK",
        "signal_request(2",
        "signal_request(0",
        "error_cancel = error_none",
    ):
        if forbidden in combined:
            fail("diagnostic scope violation: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=SYSSTART_REQUEST_WAKE_TIMER_SCHED_SVC_DIAGNOSTIC")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
