#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B63 SASELFTESTABI1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B63-SASELFTESTABI1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b63_saselftestabi1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gs=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    need(sa,"[NBOOT2][SA_SELFTEST_ABI]","B63 marker")
    need(sa,"ctx.msg->function == 0x67","exact selftest opcode")
    need(sa,"logical=EExecuteSelftests","public command identity")
    need(sa,"command_id=103","public command id")
    need(sa,"public_response=TResponsePckg_TInt","public response contract")
    need(sa,"process={} thread={} session={}","caller identity")
    need(sa,"types=[{},{},{},{}] sizes=[{},{},{},{}] max=[{},{},{},{}]","slot ABI")
    need(sa,"ctx.complete(epoc::error_not_supported);","old unknown-op result preserved")
    need(sa,'REGISTER_IPC(sa_server, unk_op1, 0x67, "NBOOT2::SaExecuteSelftestsAbiProbe");',"exact registration")

    b0=sa.find("// NATIVEBOOT2-B63 SASELFTESTABI1:")
    b1=sa.find("// NATIVEBOOT2-B42 SAHWRMABI1:",b0)
    if b0<0 or b1<0:
        fail("cannot isolate B63 block")
    block=sa[b0:b1]

    for forbidden in (
        "epoc::error_none",
        "write_data_to_descriptor_argument",
        "set_descriptor_argument_length",
        "pending_sa_event_.complete(",
        "set_int(",
    ):
        if forbidden in block:
            fail("B63 behavior-changing code found: "+forbidden)

    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 trace preserved")
    need(svc,"[NBOOT2][STARTUP_STATE_PS]","B58 trace preserved")
    need(gs,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 guard preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("opcode=0x67_EExecuteSelftests")
    print("behavior=DIAGNOSTIC_ONLY")
    print("completion=KErrNotSupported_PRESERVED")

if __name__=="__main__":
    main()
