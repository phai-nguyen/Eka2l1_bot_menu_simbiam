#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B66 STARTERIPC1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-STARTERIPC1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(t,n,w):
    if n not in t:
        fail(f"missing in {w}: {n}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b66_starteripc1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ctx=(up/"src/emu/services/src/context.cpp").read_text(encoding="utf-8")
    proc=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gs=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    need(ctx,"[NBOOT2][STARTER_IPC] phase=dispatch","dispatch marker")
    need(ctx,"[NBOOT2][STARTER_IPC] phase=complete","complete marker")
    need(ctx,"get_uid() == 0x100059C9U","SYSSTART filter")
    need(ctx,"server={} func=0x{:08X}","server/function detail")
    need(ctx,"has_request_status={}","async status detail")
    need(ctx,"obj_name","dispatch server identity")
    need(ctx,"msg->msg_session->get_server()->name()","completion server identity")

    # Preserve original completion mechanics.
    need(ctx,"msg->request_sts.get(msg->own_thr->owning_process())","request status write")
    need(ctx,"msg->own_thr->signal_request();","request signal")

    need(proc,"[NBOOT2][STARTER_RENDEZVOUS]","B65 preserved")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 preserved")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 preserved")
    need(gs,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 preserved")

    if "0x101F8766" in ctx or "0x100058F4" in ctx:
        fail("state injection/reference in generic IPC trace")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=SYSSTART_HLE_IPC_DIAGNOSTIC_ONLY")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
