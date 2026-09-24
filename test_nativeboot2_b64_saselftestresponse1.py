#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B64 SASELFTESTRESPONSE1."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B64-SASELFTESTRESPONSE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b64_saselftestresponse1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    gs=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")

    b0=sa.find("// NATIVEBOOT2-B63 SASELFTESTABI1:")
    b1=sa.find("// NATIVEBOOT2-B42 SAHWRMABI1:",b0)
    if b0<0 or b1<0:
        fail("cannot isolate selftest block")
    block=sa[b0:b1]

    need(block,"[NBOOT2][SA_SELFTEST_ABI]","B63 ABI marker")
    need(block,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64 response marker")
    need(block,"0x01000067U","response command envelope")
    need(block,"sizeof(b64_response_header)","12-byte response header")
    need(block,"b64_slot3_max >= sizeof(b64_response)","slot3 capacity check")
    need(block,"write_data_to_descriptor_argument<std::int32_t>","TInt payload write")
    need(block,"3, b64_response","slot3 payload destination")
    need(block,"ctx.complete(epoc::error_none);","successful RMessage completion")
    need(block,"payload=TInt_KErrNone","response log semantics")

    if "ctx.complete(epoc::error_not_supported);" in block:
        fail("old B63 KErrNotSupported completion remains in selftest path")
    for forbidden in ("set_int(","0x101F8766","0x100058F4"):
        if forbidden in block:
            fail("state injection found: "+forbidden)

    need(svc,"[NBOOT2][STARTER_GLOBAL_STATE]","B62 trace preserved")
    need(gs,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 guard preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("opcode=0x67_EExecuteSelftests")
    print("transport=RM356_SLOT2_HEADER_SLOT3_TINT")
    print("state_injection=NONE")

if __name__=="__main__":
    main()
