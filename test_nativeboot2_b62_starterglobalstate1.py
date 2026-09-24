#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B62 STARTERGLOBALSTATE1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B62-STARTERGLOBALSTATE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b62_starterglobalstate1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gstore=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 marker")
    need(svc,"0x101F8766U","Startup domain category")
    need(svc,"0x00000041U","KPSGlobalSystemState key")
    need(svc,"op=GET path=CATEGORY_KEY","global state read")
    need(svc,"op=SET path=CATEGORY_KEY","direct global state write")
    need(svc,"op=SET path=HANDLE_INT","handle global state write")
    need(svc,"before={} requested={} after={}","write transition detail")
    need(svc,"process={} uid3=0x{:08X} thread={}","writer identity")
    need(svc,"[NBOOT2][STARTUP_STATE_PS]","B58 marker preserved")
    need(svc,"[NBOOT2][STARTUP_STATE_HANDLE]","B60 marker preserved")
    need(gstore,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 guard preserved")

    if "set_int(104)" in svc or "set_int(2)" in svc:
        fail("B62 must not inject Starter/Startup state values")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=KPSGlobalSystemState_101F8766_41")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
