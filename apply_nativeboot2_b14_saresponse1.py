#!/usr/bin/env python3
"""NATIVEBOOT2-B14 SARESPONSE1.

Apply on top of B13 SAGLOBALSTATE1.

B13 device evidence:
- SAServer opcode 0x64 is reached and completed, but SysStart stalls afterwards.
- Logged ABI: types=[des8,desc8,des8,des8], sizes=[4,4,12,0].

RM-356 reverse engineering (StartupAdaptation.DLL + SAClient.DLL + SAServer.DLL):
- StartupAdaptation commands are sent asynchronously through
  RSessionBase::DoSendReceive(..., TRequestStatus&).
- The real SAServer completes a command response by writing a 12-byte
  response-message header to IPC slot 2, writing the response payload to
  IPC slot 3, then completing the RMessage2 with KErrNone.
- For EGlobalStateChange (0x64), the payload is TResponsePckg = TInt,
  and KErrNone (0) means success.
- B13 incorrectly wrote the TInt response into slot 0, leaving slot 3 empty.

B14 preserves/echoes the prebuilt 12-byte response template from slot 2,
writes TInt(KErrNone) to slot 3, and completes KErrNone. Opcode 1 keeps the
B12 behavior for this iteration but gains ABI tracing for the next stage.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B14-SARESPONSE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b14_saresponse1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    sa = up / "src/emu/services/src/sms/sa/sa.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (sa, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing B13 baseline file: {p}")

    text = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_GLOBAL_STATE]",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
        "NATIVEBOOT2-B13 SAGLOBALSTATE1",
    ):
        if gate not in text:
            fail(f"B13 gate missing: {gate}")

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
        fail("B6 BSP marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    if "#include <cstring>" not in text:
        text = replace_once(
            text,
            "#include <utils/err.h>\n",
            "#include <utils/err.h>\n\n#include <cstring>\n",
            "cstring include",
        )

    old = """        // NATIVEBOOT2-B13 SAGLOBALSTATE1:
        // RM-356 StartupAdaptation.dll sends StartupAdaptation::EGlobalStateChange
        // directly as SAServer IPC function 100 (0x64). Its response type is
        // TPckgBuf<TInt>; zero/KErrNone means the state transition succeeded.
        if (ctx.msg && (ctx.msg->function == 100)) {
            const std::int32_t response = epoc::error_none;
            int response_slot = -1;

            for (int i = 0; i < 4; ++i) {
                const ipc_arg_type type = ctx.msg->args.get_arg_type(i);
                if (type == ipc_arg_type::des8) {
                    if ((ctx.get_argument_max_data_size(i) >= sizeof(response))
                        && ctx.write_data_to_descriptor_argument<std::int32_t>(i, response)) {
                        response_slot = i;
                        break;
                    }
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_GLOBAL_STATE] func=0x{:X} arg_types=[{},{},{},{}] "
                "arg_sizes=[{},{},{},{}] response_slot={} response={} completion=KErrNone",
                ctx.msg->function,
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                response_slot, response);

            // Complete even if the proprietary plugin provided no separate
            // writable response descriptor; the trace above will expose its ABI.
            ctx.complete(epoc::error_none);
            return;
        }

        ctx.complete(epoc::error_none);
"""
    new = """        // NATIVEBOOT2-B14 SARESPONSE1:
        // RM-356 uses SAServer as its System Adaptation transport.  SAClient
        // prebuilds the expected response-message envelope in IPC slot 2.
        // The real SAServer writes that 12-byte envelope to slot 2, writes the
        // command-specific payload to slot 3, and only then completes RMessage2.
        if (ctx.msg && (ctx.msg->function == 100)) {
            std::uint32_t response_header[3] = { 0x00010004U, 0x01000064U, 0U };
            const std::size_t slot2_size = ctx.get_argument_data_size(2);
            const std::size_t slot2_max = ctx.get_argument_max_data_size(2);
            const std::size_t slot3_max = ctx.get_argument_max_data_size(3);

            // Echo the exact response template prepared by SAClient.  This
            // preserves the transaction sequence number and any RM-356-specific
            // message envelope fields instead of hard-coding them.
            const std::uint8_t *slot2_ptr = ctx.get_descriptor_argument_ptr(2);
            bool template_copied = false;
            if (slot2_ptr && (slot2_size >= sizeof(response_header))) {
                std::memcpy(response_header, slot2_ptr, sizeof(response_header));
                template_copied = true;
            }

            int header_err = epoc::error_none;
            const bool header_ok = ctx.write_data_to_descriptor_argument(
                2, reinterpret_cast<const std::uint8_t *>(response_header),
                static_cast<std::uint32_t>(sizeof(response_header)),
                &header_err, false);

            const std::int32_t response = epoc::error_none;
            const bool payload_ok = (slot3_max >= sizeof(response))
                && ctx.write_data_to_descriptor_argument<std::int32_t>(3, response);

            std::uint32_t slot0_word = 0;
            std::uint32_t slot1_word = 0;
            const std::uint8_t *slot0_ptr = ctx.get_descriptor_argument_ptr(0);
            const std::uint8_t *slot1_ptr = ctx.get_descriptor_argument_ptr(1);
            if (slot0_ptr && (ctx.get_argument_data_size(0) >= sizeof(slot0_word))) {
                std::memcpy(&slot0_word, slot0_ptr, sizeof(slot0_word));
            }
            if (slot1_ptr && (ctx.get_argument_data_size(1) >= sizeof(slot1_word))) {
                std::memcpy(&slot1_word, slot1_ptr, sizeof(slot1_word));
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_RESPONSE] func=0x{:X} types=[{},{},{},{}] "
                "sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "slot0=0x{:08X} input=0x{:08X} "
                "header=[0x{:08X},0x{:08X},0x{:08X}] template={} "
                "header_ok={} header_err={} payload_ok={} payload={} completion=KErrNone",
                ctx.msg->function,
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                slot2_max, slot3_max,
                slot0_word, slot1_word,
                response_header[0], response_header[1], response_header[2],
                template_copied, header_ok, header_err, payload_ok, response);

            if (!header_ok || !payload_ok) {
                LOG_ERROR(SERVICE_SMS,
                    "[NBOOT2][SA_RESPONSE_FAIL] func=0x{:X} header_ok={} payload_ok={} "
                    "slot2_size={} slot2_max={} slot3_max={}",
                    ctx.msg->function, header_ok, payload_ok,
                    slot2_size, slot2_max, slot3_max);
            }

            ctx.complete(epoc::error_none);
            return;
        }

        // Opcode 1 is used by the RM-356 SAClient control/event path.  B14
        // intentionally preserves B12's completion behaviour, but records its
        // real ABI so the long-lived notification request can be separated from
        // the synchronous registration call in the next iteration if needed.
        if (ctx.msg && (ctx.msg->function == 1)) {
            std::uint32_t words[4] = {};
            for (int i = 0; i < 4; ++i) {
                const std::uint8_t *ptr = ctx.get_descriptor_argument_ptr(i);
                if (ptr && (ctx.get_argument_data_size(i) >= sizeof(std::uint32_t))) {
                    std::memcpy(&words[i], ptr, sizeof(std::uint32_t));
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_OP1] types=[{},{},{},{}] sizes=[{},{},{},{}] "
                "max=[{},{},{},{}] words=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] completion=KErrNone",
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                ctx.get_argument_max_data_size(2), ctx.get_argument_max_data_size(3),
                words[0], words[1], words[2], words[3]);
        }

        ctx.complete(epoc::error_none);
"""
    text = replace_once(text, old, new, "B13 GlobalState response block")
    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_RESPONSE_FAIL]",
        "[NBOOT2][SA_OP1]",
        "std::memcpy(response_header, slot2_ptr, sizeof(response_header));",
        "ctx.write_data_to_descriptor_argument<std::int32_t>(3, response)",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in body:
            fail(f"B14 gate missing: {gate}")

    print("NATIVEBOOT2-B14 SARESPONSE1 applied")
    print("SAServer_opcode_100=response_header_slot2_plus_payload_slot3")
    print("EGlobalStateChange_payload=TInt_KErrNone")
    print("SA_response_template=echo_slot2_12_bytes")
    print("SA_opcode1=behavior_preserved_plus_trace")
    print("B13_SAGLOBALSTATE1=SUPERSEDED_RESPONSE_LAYOUT")
    print("B12_SAIPC1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
