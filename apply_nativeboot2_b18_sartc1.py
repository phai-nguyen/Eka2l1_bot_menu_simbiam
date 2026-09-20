#!/usr/bin/env python3
"""NATIVEBOOT2-B18 SARTC1.

Apply on top of B17 SAHIDDENRESET1.

B17 device evidence:
- EGlobalStateChange/0x64 completes successfully.
- EGetGlobalStartupMode/0x66 completes with ENormal(100).
- EGetHiddenReset/0x75 completes with EFalse(0).
- B15 opcode-1 async lifecycle remains stable with one pending event request.
- The first new unsupported SAServer command is 0x6B.

Symbian Startup Adaptation API:
- EValidateRTCTime = 107 decimal = 0x6B.
- TResponsePckg = TPckgBuf<TInt>, i.e. a single 32-bit TInt.
- KErrNone means the RTC time is valid; any other value means invalid.

EKA2L1 already maintains kernel universal/home time, so the RM-356 virtual board
reports a valid RTC for this boot path. B18 preserves the proven RM-356 slot2
response-envelope transport and writes the 4-byte TInt command payload to slot3.
It does not blanket-ack any other StartupAdaptation command.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B18-SARTC1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b18_sartc1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    sa = up / "src/emu/services/src/sms/sa/sa.cpp"
    sah = up / "src/emu/services/include/services/sms/sa/sa.h"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (sa, sah, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing B17 baseline file: {p}")

    text = sa.read_text(encoding="utf-8")
    htext = sah.read_text(encoding="utf-8")

    for gate in (
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_RESPONSE_HIDDEN]",
        'REGISTER_IPC(sa_server, unk_op1, 117, "NBOOT2::SaGetHiddenReset");',
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_RESPONSE_MODE]",
        'REGISTER_IPC(sa_server, unk_op1, 102, "NBOOT2::SaGetGlobalStartupMode");',
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_OP1_CONTROL]",
        "[NBOOT2][SA_OP1_PENDING]",
        "[NBOOT2][SA_OP1_DUP]",
        "[NBOOT2][SA_OP1_CANCEL]",
        "pending_sa_event_.pending();",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in text:
            fail(f"B17 cpp gate missing: {gate}")

    for gate in (
        "pending_sa_event_",
        "pending_sa_event_session_",
        "void disconnect(service::ipc_context &context) override;",
    ):
        if gate not in htext:
            fail(f"B17 header gate missing: {gate}")

    svc_text = svc.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][DM_INIT_SET_INT]",
        "[NBOOT2][DM_INIT_SUBSCRIBE]",
        "[NBOOT2][DM_INIT_GET_INT]",
        "[NBOOT2][RM356_CREATOR_SECURITY]",
        "BRIDGE_REGISTER(0xB1, creator_security_info)",
        "const bool res = prop->set_int(value);",
    ):
        if gate not in svc_text:
            fail(f"B11 gate missing: {gate}")

    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" not in fs.read_text(encoding="utf-8"):
        fail("B10 FSFORMAT1 marker missing")
    if "[NBOOT2][RM356_LOADER_FSY]" not in loader.read_text(encoding="utf-8"):
        fail("B8 LOADERFSY1 marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 BSP startup-reason marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    anchor = """        // NATIVEBOOT2-B15 SAASYNC1:
"""
    rtc_block = """        // NATIVEBOOT2-B18 SARTC1:
        // StartupAdaptation::EValidateRTCTime == 107 (0x6B).
        // Public response package is TPckgBuf<TInt>, so the payload is exactly
        // one 32-bit TInt. KErrNone means the RTC is valid.
        if (ctx.msg && (ctx.msg->function == 107)) {
            const std::int32_t response = epoc::error_none;

            // Preserve the RM-356 transport proven by B14/B16/B17:
            // slot 2 is a 12-byte transaction envelope, slot 3 is the logical
            // command response. Echo the client's exact header template when
            // available to preserve transaction sequence fields.
            std::uint32_t response_header[3] = { 0x00010004U, 0x0100006BU, 0U };
            const std::size_t slot2_size = ctx.get_argument_data_size(2);
            const std::size_t slot2_max = ctx.get_argument_max_data_size(2);
            const std::size_t slot3_max = ctx.get_argument_max_data_size(3);
            const std::uint8_t *slot2_ptr = ctx.get_descriptor_argument_ptr(2);

            bool template_copied = false;
            if (slot2_ptr && (slot2_size >= sizeof(response_header))) {
                std::memcpy(response_header, slot2_ptr, sizeof(response_header));
                template_copied = true;
            }

            int header_err = epoc::error_none;
            const bool header_ok = ctx.write_data_to_descriptor_argument(
                2,
                reinterpret_cast<const std::uint8_t *>(response_header),
                static_cast<std::uint32_t>(sizeof(response_header)),
                &header_err,
                false);

            int payload_err = epoc::error_none;
            const bool payload_ok =
                (slot3_max >= sizeof(response))
                && ctx.write_data_to_descriptor_argument<std::int32_t>(
                    3, response, &payload_err);

            const std::int32_t completion =
                (header_ok && payload_ok) ? epoc::error_none : epoc::error_bad_descriptor;

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_RTC_VALID] source=EKA2L1_KERNEL_CLOCK "
                "rtc_valid=true value={}",
                response);

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_RESPONSE_RTC] func=0x{:X} types=[{},{},{},{}] "
                "sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "header=[0x{:08X},0x{:08X},0x{:08X}] template={} "
                "header_ok={} header_err={} payload_ok={} payload_err={} "
                "payload_size={} response={} completion={}",
                ctx.msg->function,
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                slot2_max, slot3_max,
                response_header[0], response_header[1], response_header[2],
                template_copied,
                header_ok, header_err, payload_ok, payload_err,
                sizeof(response), response, completion);

            if (!header_ok || !payload_ok) {
                LOG_ERROR(SERVICE_SMS,
                    "[NBOOT2][SA_RESPONSE_RTC_FAIL] func=0x{:X} "
                    "slot2_size={} slot2_max={} slot3_max={} "
                    "header_ok={} header_err={} payload_ok={} payload_err={}",
                    ctx.msg->function,
                    slot2_size, slot2_max, slot3_max,
                    header_ok, header_err, payload_ok, payload_err);
            }

            ctx.complete(completion);
            return;
        }

"""
    text = replace_once(text, anchor, rtc_block + anchor, "B15 opcode1 anchor")

    reg_anchor = '        REGISTER_IPC(sa_server, unk_op1, 117, "NBOOT2::SaGetHiddenReset");\n'
    reg_new = reg_anchor + '        REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");\n'
    if 'REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");' not in text:
        text = replace_once(text, reg_anchor, reg_new, "SAServer opcode 107 registration")

    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_RESPONSE_RTC]",
        "[NBOOT2][SA_RESPONSE_RTC_FAIL]",
        "0x00010004U",
        "0x0100006BU",
        'REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");',
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_RESPONSE_HIDDEN]",
        'REGISTER_IPC(sa_server, unk_op1, 117, "NBOOT2::SaGetHiddenReset");',
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_RESPONSE_MODE]",
        'REGISTER_IPC(sa_server, unk_op1, 102, "NBOOT2::SaGetGlobalStartupMode");',
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_OP1_CONTROL]",
        "[NBOOT2][SA_OP1_PENDING]",
        "pending_sa_event_.pending();",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in body:
            fail(f"B18 gate missing: {gate}")

    print("NATIVEBOOT2-B18 SARTC1 applied")
    print("SAServer_opcode_107=EValidateRTCTime")
    print("SA_rtc_response=TResponsePckg_TInt_4_bytes")
    print("SA_rtc_source=EKA2L1_KERNEL_CLOCK")
    print("SA_rtc_value=KErrNone_valid")
    print("SA_opcode107_transport=slot2_12byte_envelope_plus_slot3_4byte_payload")
    print("SA_unknown_commands=NOT_BLANKET_ACKED")
    print("B17_SAHIDDENRESET1=PRESERVED")
    print("B16_SAMODE1=PRESERVED")
    print("B15_SAASYNC1=PRESERVED")
    print("B14_SARESPONSE1=PRESERVED")
    print("B13_SAGLOBALSTATE1=PRESERVED")
    print("B12_SAIPC1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
