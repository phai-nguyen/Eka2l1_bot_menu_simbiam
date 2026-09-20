#!/usr/bin/env python3
"""NATIVEBOOT2-B19 SALANGABI1 diagnostic probe.

Apply on top of B18 SARTC1.

B18 device evidence:
- EValidateRTCTime/0x6B completes successfully.
- Immediately after languages.txt/CenRep language-policy activity, RM-356 sends
  the exact SAServer function 0x01100068.
- Low 16 bits are 0x0068 == StartupAdaptation::EGetSIMLanguages (104), but the
  meaning of transport bits 0x01100000 is not yet proven.
- Public EGetSIMLanguages response contains RLanguageListResponse/RArray and is
  therefore unsafe to synthesize before the proprietary SA transport ABI is
  observed.

B19 is intentionally diagnostic only:
- register the exact raw function 0x01100068;
- log raw function decomposition, IPC argument types, raw values, lengths,
  maximum lengths, and up to the first 16 descriptor bytes per slot;
- do not write or resize any descriptor;
- preserve current guest-visible failure behavior by completing
  KErrNotSupported.

No other SAServer opcode is aliased or blanket-acknowledged.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B19-SALANGABI1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b19_salangabi1.py <upstream-root>")

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
            fail(f"missing B18 baseline file: {p}")

    text = sa.read_text(encoding="utf-8")
    htext = sah.read_text(encoding="utf-8")

    for gate in (
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_RESPONSE_RTC]",
        'REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");',
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_RESPONSE_HIDDEN]",
        'REGISTER_IPC(sa_server, unk_op1, 117, "NBOOT2::SaGetHiddenReset");',
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_RESPONSE_MODE]",
        'REGISTER_IPC(sa_server, unk_op1, 102, "NBOOT2::SaGetGlobalStartupMode");',
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_OP1_PENDING]",
        "pending_sa_event_.pending();",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in text:
            fail(f"B18 cpp gate missing: {gate}")

    for gate in (
        "pending_sa_event_",
        "pending_sa_event_session_",
        "void disconnect(service::ipc_context &context) override;",
    ):
        if gate not in htext:
            fail(f"B18 header gate missing: {gate}")

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

    anchor = """        // NATIVEBOOT2-B18 SARTC1:
"""
    diag_block = """        // NATIVEBOOT2-B19 SALANGABI1:
        // RM-356 sends the exact raw SAServer function 0x01100068 after
        // language-policy initialization. Low 16 bits are 0x68, matching
        // StartupAdaptation::EGetSIMLanguages, but the 0x01100000 transport
        // bits and dynamic RLanguageListResponse ABI are not yet proven.
        // Diagnostic-only: inspect the request and preserve KErrNotSupported.
        if (ctx.msg && (ctx.msg->function == 0x01100068)) {
            const std::uint32_t raw_func = static_cast<std::uint32_t>(ctx.msg->function);
            const std::uint32_t logical_func = raw_func & 0xFFFFU;
            const std::uint32_t transport_bits = raw_func & 0xFFFF0000U;

            std::uint32_t preview[4][4] = {};
            bool has_desc[4] = { false, false, false, false };

            for (int slot = 0; slot < 4; ++slot) {
                const std::uint8_t *ptr = ctx.get_descriptor_argument_ptr(slot);
                const std::size_t size = ctx.get_argument_data_size(slot);
                if (ptr) {
                    has_desc[slot] = true;
                    const std::size_t copy_size =
                        common::min<std::size_t>(size, sizeof(preview[slot]));
                    if (copy_size > 0) {
                        std::memcpy(preview[slot], ptr, copy_size);
                    }
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_LANG_ABI] raw_func=0x{:X} logical_func=0x{:X} "
                "transport_bits=0x{:X} ipc_flag=0x{:X} "
                "raw_args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "types=[{},{},{},{}] sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "has_desc=[{},{},{},{}] "
                "preview0=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview1=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview2=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview3=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "completion=KErrNotSupported",
                raw_func, logical_func, transport_bits,
                static_cast<std::uint32_t>(ctx.flag()),
                static_cast<std::uint32_t>(ctx.msg->args.args[0]),
                static_cast<std::uint32_t>(ctx.msg->args.args[1]),
                static_cast<std::uint32_t>(ctx.msg->args.args[2]),
                static_cast<std::uint32_t>(ctx.msg->args.args[3]),
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                ctx.get_argument_max_data_size(2), ctx.get_argument_max_data_size(3),
                has_desc[0], has_desc[1], has_desc[2], has_desc[3],
                preview[0][0], preview[0][1], preview[0][2], preview[0][3],
                preview[1][0], preview[1][1], preview[1][2], preview[1][3],
                preview[2][0], preview[2][1], preview[2][2], preview[2][3],
                preview[3][0], preview[3][1], preview[3][2], preview[3][3]);

            ctx.complete(epoc::error_not_supported);
            return;
        }

"""
    text = replace_once(text, anchor, diag_block + anchor, "B18 SARTC1 anchor")

    reg_anchor = '        REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");\n'
    reg_new = reg_anchor + '        REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");\n'
    if 'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");' not in text:
        text = replace_once(text, reg_anchor, reg_new, "SAServer raw opcode 0x01100068 registration")

    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_LANG_ABI]",
        "raw_func=0x{:X}",
        "logical_func=0x{:X}",
        "transport_bits=0x{:X}",
        "completion=KErrNotSupported",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_RESPONSE_RTC]",
        'REGISTER_IPC(sa_server, unk_op1, 107, "NBOOT2::SaValidateRTCTime");',
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
        "[NBOOT2][SA_RESPONSE]",
    ):
        if gate not in body:
            fail(f"B19 gate missing: {gate}")

    print("NATIVEBOOT2-B19 SALANGABI1 applied")
    print("SAServer_raw_opcode=0x01100068")
    print("logical_low16=0x0068_EGetSIMLanguages_candidate")
    print("transport_high_bits=0x01100000_UNRESOLVED")
    print("behavior=DIAGNOSTIC_ONLY")
    print("descriptor_writes=NONE")
    print("completion=KErrNotSupported")
    print("B18_SARTC1=PRESERVED")
    print("B17_SAHIDDENRESET1=PRESERVED")
    print("B16_SAMODE1=PRESERVED")
    print("B15_SAASYNC1=PRESERVED")
    print("B14_SARESPONSE1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
