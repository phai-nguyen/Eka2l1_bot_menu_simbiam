#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B65 STARTERRENDEZVOUS1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B65-STARTERRENDEZVOUS1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(t,n,w):
    if n not in t:
        fail(f"missing in {w}: {n}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b65_starterrendezvous1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gs=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    need(p,"[NBOOT2][STARTER_RENDEZVOUS]","B65 marker")
    for phase in ("phase=arm ","phase=queued ","phase=complete ","phase=cancel ","phase=cancel_miss ","phase=arm_dead_target "):
        need(p,phase,"B65 phases")
    need(p,"get_uid() == 0x100059C9U","SYSSTART-only filter")
    need(p,'LOG_TRACE(KERNEL, "Rendezvous to: {}", ren.requester->name());',"legacy trace preserved")
    need(p,"ren.complete(rendezvous_reason);","completion preserved")
    need(p,"find_result->complete(-3);","cancel completion preserved")

    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 preserved")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 preserved")
    need(gs,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 preserved")

    # B65 is trace-only: it must not alter startup/P&S or manufacture
    # rendezvous results.
    if "0x101F8766" in p or "0x100058F4" in p:
        fail("P&S state injection/reference found in process trace")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=SYSSTART_RENDEZVOUS_DIAGNOSTIC_ONLY")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
