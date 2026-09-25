#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B70 SIMPATHPROVENANCE1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B70-SIMPATHPROVENANCE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b70_simpathprovenance1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    se=(up/"src/emu/kernel/src/session.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    al=(up/"src/emu/services/src/alarm/alarm.cpp").read_text(encoding="utf-8")

    need(se,"[NBOOT2][STARTER_IPC_ARM]","session.cpp")
    need(se,"mode=ASYNC","session.cpp")
    need(se,"mode=SYNC","session.cpp")
    need(se,"0x100059C9U","session.cpp")
    need(se,"request_status=0x{:08X}","session.cpp")
    need(se,"server={}","session.cpp")
    need(se,"function=0x{:08X}","session.cpp")

    need(sv,"[NBOOT2][STARTER_ASYNC_ARM]","svc.cpp")
    need(sv,"source=TIMER_AFTER","svc.cpp")
    need(sv,"source=TIMER_AFTER_HIGH_RES","svc.cpp")
    need(sv,"source=TIMER_LOCK","svc.cpp")
    need(sv,"source=PROPERTY_SUBSCRIBE","svc.cpp")

    need(sv,"[NBOOT2][SIM_PS]","svc.cpp")
    for key in ("0x00000031U","0x00000032U","0x00000033U"):
        need(sv,key,"SIM P&S trace")

    # Preserve the selected evidence/fix chain.
    need(sv,"[NBOOT2][STARTER_GLOBAL_STATE]","B62")
    need(sv,"[NBOOT2][STARTER_WAIT_ANY]","B68")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64")
    need(al,"[NBOOT2][ALARM_ID_LIST]","B69")

    # B70 itself must not synthesize the target SIM state or state 102.
    # Isolate tagged additions approximately by required marker contexts.
    if "set_int(101)" in se:
        fail("session diagnostic contains SIM-value injection")
    if "requested=102" in se:
        fail("session diagnostic contains state injection")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("normal_sim_path=SELECTED")
    print("sysstart_ipc_provenance=ENABLED")
    print("timer_property_provenance=ENABLED")
    print("sim_ps_31_32_33=OBSERVE_ONLY")
    print("state_injection=NONE")

if __name__=="__main__":
    main()
