#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B66 STARTERSCRIPTDUMP1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-STARTERSCRIPTDUMP1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(t,n,w):
    if n not in t:
        fail(f"missing in {w}: {n}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b66_starterscriptdump1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    proc=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    need(fs,"[NBOOT2][STARTER_SCRIPT_DUMP]","B66 marker")
    need(fs,'u"scriptinit.txt"',"ScriptInit")
    need(fs,'u"script0.txt"',"script0")
    need(fs,'u"script1.txt"',"script1")
    need(fs,'u"plg_script"',"generated plugin script")
    need(fs,"io->open_file(path, READ_MODE | BIN_MODE)","separate read-only VFS handle")
    need(fs,"constexpr std::size_t max_capture = 65536","bounded capture")
    need(fs,"nboot2_b66_dump_starter_script(io, *name_res);","EFsrv open hook")
    need(fs,"behavior=OBSERVE_ONLY","diagnostic contract")

    b0=fs.find("// NATIVEBOOT2-B66 STARTERSCRIPTDUMP1:")
    b1=fs.find("// Whether the directory is exactly",b0)
    if b0<0 or b1<0:
        fail("cannot isolate B66 block")
    block=fs[b0:b1]
    for forbidden in ("WRITE_MODE","write_file(","resize(","ctx->complete(","set_int("):
        if forbidden in block:
            fail("behavior-changing code found: "+forbidden)

    need(proc,"[NBOOT2][STARTER_RENDEZVOUS]","B65 preserved")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 preserved")
    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=RM356_STARTER_SCRIPT_READ_ONLY_DUMP")
    print("behavior_change=NONE")

if __name__=="__main__":
    main()
