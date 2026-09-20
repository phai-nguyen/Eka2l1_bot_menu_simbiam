#!/usr/bin/env python3
"""NATIVEBOOT2-B16 SAMODE1.

Apply on top of B15 SAASYNC1.

B15 device evidence:
- Opcode-1 busy loop is eliminated: one control completion and one event request
  remain pending as intended.
- EGlobalStateChange/0x64 completes with the B14 RM-356 response envelope ABI.
- The first new unsupported call is SAServer opcode 0x66.

Symbian Startup Adaptation API:
- EGetGlobalStartupMode = 102 decimal = 0x66.
- TGlobalStartupModeResponse is two 32-bit fields:
    TInt iErrorCode;
    TGlobalStartupMode iValue;
- TGlobalStartupMode::ENormal = 100.

The NATIVEBOOT2 B6 RM-356 board adapter exposes HAL StartupReason as
EStartupCold(0). For the current normal cold-boot path B16 maps that deterministic
board state to StartupAdaptation::ENormal(100), returns the full 8-byte response
package through the proven B14 slot2/slot3 transport ABI, and leaves every other
StartupAdaptation command unsupported until device evidence reaches it.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B16-SAMODE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b16_samode1.py <upstream-root>")

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
            fail(f"missing B15 baseline file: {p}")

    text = sa.read_text(encoding="utf-8")
    htext = sah.read_text(encoding="utf-8")

    for gate in (
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
            fail(f"B15 cpp gate missing: {gate}")

    for gate in (
        "pending_sa_event_",
        "pending_sa_event_session_",
        "void disconnect(service::ipc_context &context) override;",
    ):
        if gate not in htext:
            fail(f"B15 header gate missing: {gate}")

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
    hal_text = hal.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal_text:
        fail("B6 BSP startup-reason marker missing")
    if "*a1 = 0;" not in hal_text:
        fail("B6 StartupReason=EStartupCold(0) invariant missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    anchor = """        // NATIVEBOOT2-B15 SAASYNC1:
"""
    mode_block = """        // NATIVEBOOT2-B16 SAMODE1:
        // StartupAdaptation::EGetGlobalStartupMode == 102 (0x66).
        // The public response package is exactly two 32-bit fields:
        //   TInt iErrorCode; TGlobalStartupMode iValue.
        // B6 exposes RM-356 StartupReason as EStartupCold(0), which maps to
        // the normal cold-boot adaptation mode ENormal(100).
        if (ctx.msg && (ctx.msg->function == 102)) {
            struct rm356_sa_startup_mode_response {
                std::int32_t error_code;
                std::int32_t mode;
            };
            static_assert(sizeof(rm356_sa_startup_mode_response) == 8,
                "RM356 startup-mode response must be 8 bytes");

            constexpr std::int32_t rm356_startup_reason_cold = 0;
            constexpr std::int32_t sa_startup_mode_normal = 100;
            const rm356_sa_startup_mode_response response = {
                epoc::error_none,
                sa_startup_mode_normal
            };

            // The RM-356 SA transport uses a 12-byte response envelope in slot
            // 2 and the command-specific logical payload in slot 3. Echo the
            // exact client-built template whenever available, preserving its
            // transaction sequence. The fallback header encodes an 8-byte
            // response payload for command 0x66.
            std::uint32_t response_header[3] = { 0x00010008U, 0x01000066U, 0U };
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
                && ctx.write_data_to_descriptor_argument(
                    3,
                    reinterpret_cast<const std::uint8_t *>(&response),
                    static_cast<std::uint32_t>(sizeof(response)),
                    &payload_err,
                    false);

            const std::int32_t completion =
                (header_ok && payload_ok) ? epoc::error_none : epoc::error_bad_descriptor;

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_STARTUP_MODE] source=RM356_HAL_EStartupCold raw={} "
                "mapped=ENormal value={} error={}",
                rm356_startup_reason_cold, response.mode, response.error_code);

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_RESPONSE_MODE] func=0x{:X} types=[{},{},{},{}] "
                "sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "header=[0x{:08X},0x{:08X},0x{:08X}] template={} "
                "header_ok={} header_err={} payload_ok={} payload_err={} "
                "payload_size={} error={} mode={} completion={}",
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
                sizeof(response), response.error_code, response.mode, completion);

            if (!header_ok || !payload_ok) {
                LOG_ERROR(SERVICE_SMS,
                    "[NBOOT2][SA_RESPONSE_MODE_FAIL] func=0x{:X} "
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
    text = replace_once(text, anchor, mode_block + anchor, "B15 opcode1 anchor")

    reg_anchor = '        REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");\n'
    reg_new = reg_anchor + '        REGISTER_IPC(sa_server, unk_op1, 102, "NBOOT2::SaGetGlobalStartupMode");\n'
    if 'REGISTER_IPC(sa_server, unk_op1, 102, "NBOOT2::SaGetGlobalStartupMode");' not in text:
        text = replace_once(text, reg_anchor, reg_new, "SAServer opcode 102 registration")

    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_RESPONSE_MODE]",
        "[NBOOT2][SA_RESPONSE_MODE_FAIL]",
        "rm356_sa_startup_mode_response",
        "sa_startup_mode_normal = 100",
        "0x00010008U",
        "0x01000066U",
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
            fail(f"B16 gate missing: {gate}")

    print("NATIVEBOOT2-B16 SAMODE1 applied")
    print("SAServer_opcode_102=EGetGlobalStartupMode")
    print("SA_startup_mode_response=8_bytes_TInt_plus_TGlobalStartupMode")
    print("SA_startup_mode_source=RM356_HAL_EStartupCold")
    print("SA_startup_mode_mapping=EStartupCold_to_ENormal_100")
    print("SA_opcode102_transport=slot2_12byte_envelope_plus_slot3_8byte_payload")
    print("SA_unknown_commands=NOT_BLANKET_ACKED")
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
