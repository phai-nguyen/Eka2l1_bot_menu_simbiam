#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B66 CRITICALAPPWAIT1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-CRITICALAPPWAIT1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(t,n,w):
    if n not in t:
        fail(f"missing in {w}: {n}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b66_criticalappwait1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gs=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    need(p,"[NBOOT2][CRITICAL_APP_WAIT]","B66 marker")
    for phase in ("phase=arm ","phase=cancel_request ","phase=target_signal ","phase=deliver_rendezvous ","phase=finish "):
        need(p,phase,"B66 phases")

    need(p,"0x100058F3U","SysAp UID")
    need(p,"0x10207B7DU","ProfileSettingsMonitor UID")
    need(p,"0x102750F0U","AI/Home launch UID")
    need(p,'nboot2_b66_target_name == "cfserver"',"cfserver target")
    need(p,'rendezvous ? "RENDEZVOUS" : "LOGON"',"wait mode")
    need(p,"rendezvous_requests.size()","rendezvous queue")
    need(p,"logon_requests.size()","logon queue")

    need(p,"[NBOOT2][STARTER_RENDEZVOUS]","B65 preserved")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 preserved")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 preserved")
    need(gs,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 preserved")

    # Trace-only invariants.
    if "0x101F8766" in p or "0x100058F4" in p:
        fail("P&S state reference/injection found in process.cpp")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=CRITICAL_APP_TARGET_WAIT_DIAGNOSTIC_ONLY")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
