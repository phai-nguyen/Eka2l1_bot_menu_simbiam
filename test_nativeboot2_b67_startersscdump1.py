#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B67 STARTERSSCDUMP1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B67-STARTERSSCDUMP1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(t,n,w):
    if n not in t:
        fail(f"missing in {w}: {n}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b67_startersscdump1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    proc=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    need(fs,"[NBOOT2][STARTER_SSC_DUMP]","B67 marker")
    need(fs,'u"z:\\\\resource\\\\starter_arm.rsc"',"exact RM-356 SSC path")
    need(fs,"io->open_file(path, READ_MODE | BIN_MODE)","separate read-only VFS handle")
    need(fs,"constexpr std::size_t max_capture = 262144","bounded full-resource capture")
    need(fs,"constexpr std::size_t chunk_bytes = 512","bounded hex chunks")
    need(fs,"encoding=HEX","unambiguous binary encoding")
    need(fs,"nboot2_b67_dump_starter_ssc(io, *name_res);","EFsrv open hook")
    need(fs,"behavior=OBSERVE_ONLY","diagnostic contract")

    need(fs,"[NBOOT2][STARTER_SCRIPT_DUMP]","B66 preserved")
    need(proc,"[NBOOT2][STARTER_RENDEZVOUS]","B65 preserved")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 preserved")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=RM356_STARTER_ARM_RSC_READ_ONLY_HEX_DUMP")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
