#!/usr/bin/env python3
"""NATIVEBOOT2 B64 SASELFTESTRESPONSE1.

B63 DEVICE1 proves:
- SAServer opcode 0x67 is sent by SYSSTART / StarterServer.
- Public identity: StartupAdaptation::EExecuteSelftests (103).
- request ABI:
    types=[4,6,4,4]
    sizes=[12,0,12,0]
    max=[12,0,12,16]
    slot2 response template=[0x00010004,0x01000067,txn]
    slot3 writable response payload buffer (max 16)
- B63's explicit KErrNotSupported is followed by global state 101 -> 117
  (FatalStartupError).

Public Symbian API defines EExecuteSelftests response as TResponsePckg = TInt.
B14 already established the RM-356 SA response transport:
- echo the 12-byte response template in slot 2;
- write command payload in slot 3;
- complete the RMessage with KErrNone.

B64 implements that exact transport for opcode 0x67 with TInt(KErrNone).
It does NOT set KPSGlobalSystemState directly and does NOT force Startup state 2.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B64-SASELFTESTRESPONSE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b64_saselftestresponse1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    gstore=up/"src/emu/services/src/window/classes/gstore.cpp"
    for p in (sa,svc,gstore):
        if not p.is_file():
            fail(f"missing source: {p}")

    text=sa.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    gs=gstore.read_text(encoding="utf-8")

    if "[NBOOT2][SA_SELFTEST_RESPONSE]" in text:
        print(MARK+": already applied")
        return

    for gate in (
        "[NBOOT2][SA_SELFTEST_ABI]",
        "ctx.msg->function == 0x67",
        'REGISTER_IPC(sa_server, unk_op1, 0x67, "NBOOT2::SaExecuteSelftestsAbiProbe");',
        "[NBOOT2][SA_RESPONSE]",
    ):
        if gate not in text:
            fail("B63/B14 gate missing: "+gate)
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in sv:
        fail("B62 global-state trace missing")
    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" not in gs:
        fail("B61 wipeout guard missing")

    old='''            // Preserve server::process_accepted_msg()'s current unknown-opcode
            // guest-visible result exactly.
            ctx.complete(epoc::error_not_supported);
            return;
'''
    new='''            // B64 SASELFTESTRESPONSE1:
            // B63 proves RM-356 supplies the same SA response envelope used by
            // EGlobalStateChange. Echo slot 2's 12-byte template, write
            // TResponsePckg(TInt KErrNone) to slot 3, then complete KErrNone.
            std::uint32_t b64_response_header[3] =
                { 0x00010004U, 0x01000067U, 0U };
            const std::size_t b64_slot2_size =
                ctx.get_argument_data_size(2);
            const std::size_t b64_slot2_max =
                ctx.get_argument_max_data_size(2);
            const std::size_t b64_slot3_max =
                ctx.get_argument_max_data_size(3);

            const std::uint8_t *b64_slot2_ptr =
                ctx.get_descriptor_argument_ptr(2);
            bool b64_template_copied = false;
            if (b64_slot2_ptr &&
                (b64_slot2_size >= sizeof(b64_response_header))) {
                std::memcpy(b64_response_header, b64_slot2_ptr,
                    sizeof(b64_response_header));
                b64_template_copied = true;
            }

            int b64_header_err = epoc::error_none;
            const bool b64_header_ok =
                ctx.write_data_to_descriptor_argument(
                    2,
                    reinterpret_cast<const std::uint8_t *>(
                        b64_response_header),
                    static_cast<std::uint32_t>(
                        sizeof(b64_response_header)),
                    &b64_header_err,
                    false);

            const std::int32_t b64_response = epoc::error_none;
            const bool b64_payload_ok =
                (b64_slot3_max >= sizeof(b64_response)) &&
                ctx.write_data_to_descriptor_argument<std::int32_t>(
                    3, b64_response);

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_SELFTEST_RESPONSE] func=0x67 "
                "header=[0x{:08X},0x{:08X},0x{:08X}] template={} "
                "slot2_size={} slot2_max={} slot3_max={} "
                "header_ok={} header_err={} payload_ok={} payload={} "
                "completion=KErrNone behavior=RM356_RESPONSE_ENVELOPE",
                b64_response_header[0],
                b64_response_header[1],
                b64_response_header[2],
                b64_template_copied,
                b64_slot2_size,
                b64_slot2_max,
                b64_slot3_max,
                b64_header_ok,
                b64_header_err,
                b64_payload_ok,
                b64_response);

            if (!b64_header_ok || !b64_payload_ok) {
                LOG_ERROR(SERVICE_SMS,
                    "[NBOOT2][SA_SELFTEST_RESPONSE_FAIL] "
                    "header_ok={} payload_ok={} slot2_size={} "
                    "slot2_max={} slot3_max={}",
                    b64_header_ok,
                    b64_payload_ok,
                    b64_slot2_size,
                    b64_slot2_max,
                    b64_slot3_max);
            }

            ctx.complete(epoc::error_none);
            return;
'''
    text=rep1(text,old,new,"B63 completion block")

    b0=text.find("// NATIVEBOOT2-B63 SASELFTESTABI1:")
    b1=text.find("// NATIVEBOOT2-B42 SAHWRMABI1:",b0)
    if b0<0 or b1<0:
        fail("cannot isolate selftest block")
    block=text[b0:b1]

    for need in (
        "[NBOOT2][SA_SELFTEST_ABI]",
        "[NBOOT2][SA_SELFTEST_RESPONSE]",
        "b64_response_header",
        "ctx.write_data_to_descriptor_argument<std::int32_t>(\n                    3, b64_response)",
        "ctx.complete(epoc::error_none);",
    ):
        if need not in block:
            fail("B64 gate missing: "+need)

    for forbidden in (
        "set_int(",
        "0x101F8766",
        "0x100058F4",
        "requested=102",
    ):
        if forbidden in block:
            fail("B64 illegally injects state: "+forbidden)

    sa.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("opcode=0x67_EExecuteSelftests")
    print("response_header=ECHO_SLOT2_12_BYTES")
    print("response_payload_slot=3")
    print("response_payload=TInt_KErrNone")
    print("completion=KErrNone")
    print("state_injection=NONE")
    print("B61_B62_B63=PRESERVED")

if __name__=="__main__":
    main()
