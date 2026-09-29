#!/usr/bin/env python3
"""NATIVEBOOT2 B63 SASELFTESTABI1.

B62 clean-install device evidence proves:
  KPSGlobalSystemState 0 -> 100 -> 101, then stalls.
  101 == ESwStateStartingCriticalApps.
Immediately after StarterServer publishes 101, SAServer receives unimplemented
opcode 0x67.

Public Symbian Startup Adaptation API identifies:
  StartupAdaptation::EExecuteSelftests = 103 decimal = 0x67
and its response type as TResponsePckg (TInt).

B63 is diagnostic-only:
- register exactly SAServer opcode 0x67;
- log caller process/thread/session and all four IPC slots/descriptors;
- preserve current guest-visible behavior by completing KErrNotSupported;
- do not synthesize self-test success;
- do not force global state 102 or Startup state 2.

This establishes the exact RM-356 transport ABI before B64 can safely implement
the standard TResponsePckg success response if supported by device evidence.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B63-SASELFTESTABI1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b63_saselftestabi1.py <upstream-root>")

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

    if "[NBOOT2][SA_SELFTEST_ABI]" in text:
        print(MARK+": already applied")
        return

    for gate in (
        "[NBOOT2][SA_LANG_ABI]",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
        "[NBOOT2][SA_HWRM_ABI]",
        'REGISTER_IPC(sa_server, unk_op1, 0x2000000A, "NBOOT2::SaHwrmAbiProbe");',
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_RESPONSE_MODE]",
        "[NBOOT2][SA_RESPONSE_RTC]",
    ):
        if gate not in text:
            fail("SA predecessor gate missing: "+gate)

    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in sv:
        fail("B62 Starter global-state trace missing")
    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" not in gs:
        fail("B61 wipeout guard missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # B42 already introduced caller identity includes. Verify them rather than
    # mutating include order again.
    for inc in ("#include <kernel/process.h>","#include <kernel/thread.h>"):
        if inc not in text:
            fail("B42 caller include missing: "+inc)

    anchor='''        // NATIVEBOOT2-B42 SAHWRMABI1:
'''
    block='''        // NATIVEBOOT2-B63 SASELFTESTABI1:
        // StartupAdaptation::EExecuteSelftests == 103 / 0x67.
        // Public API says response type is TResponsePckg (TInt), but B63
        // deliberately preserves today's KErrNotSupported behavior until the
        // proprietary RM-356 transport shape is observed on-device.
        if (ctx.msg && (ctx.msg->function == 0x67)) {
            const std::uint32_t raw_func =
                static_cast<std::uint32_t>(ctx.msg->function);

            std::string process_name = "<null>";
            std::string thread_name = "<null>";
            std::uint64_t session_id = 0;

            if (ctx.msg->own_thr) {
                thread_name = ctx.msg->own_thr->name();
                if (ctx.msg->own_thr->owning_process()) {
                    process_name =
                        ctx.msg->own_thr->owning_process()->raw_name();
                }
            }
            if (ctx.msg->msg_session) {
                session_id = ctx.msg->msg_session->unique_id();
            }

            std::uint32_t preview[4][8] = {};
            bool has_desc[4] = { false, false, false, false };

            for (int slot = 0; slot < 4; ++slot) {
                const std::uint8_t *ptr =
                    ctx.get_descriptor_argument_ptr(slot);
                const std::size_t size =
                    ctx.get_argument_data_size(slot);
                if (ptr) {
                    has_desc[slot] = true;
                    const std::size_t copy_size =
                        common::min<std::size_t>(
                            size, sizeof(preview[slot]));
                    if (copy_size > 0) {
                        std::memcpy(preview[slot], ptr, copy_size);
                    }
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_SELFTEST_ABI] raw_func=0x{:08X} logical=EExecuteSelftests command_id=103 "
                "process={} thread={} session={} ipc_flag=0x{:X} "
                "raw_args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "types=[{},{},{},{}] sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "has_desc=[{},{},{},{}] "
                "preview0=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview1=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview2=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview3=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "public_response=TResponsePckg_TInt completion=KErrNotSupported behavior=OBSERVE_ONLY",
                raw_func,
                process_name, thread_name, session_id,
                static_cast<std::uint32_t>(ctx.flag()),
                static_cast<std::uint32_t>(ctx.msg->args.args[0]),
                static_cast<std::uint32_t>(ctx.msg->args.args[1]),
                static_cast<std::uint32_t>(ctx.msg->args.args[2]),
                static_cast<std::uint32_t>(ctx.msg->args.args[3]),
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0),
                ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2),
                ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0),
                ctx.get_argument_max_data_size(1),
                ctx.get_argument_max_data_size(2),
                ctx.get_argument_max_data_size(3),
                has_desc[0], has_desc[1], has_desc[2], has_desc[3],
                preview[0][0], preview[0][1], preview[0][2], preview[0][3],
                preview[0][4], preview[0][5], preview[0][6], preview[0][7],
                preview[1][0], preview[1][1], preview[1][2], preview[1][3],
                preview[1][4], preview[1][5], preview[1][6], preview[1][7],
                preview[2][0], preview[2][1], preview[2][2], preview[2][3],
                preview[2][4], preview[2][5], preview[2][6], preview[2][7],
                preview[3][0], preview[3][1], preview[3][2], preview[3][3],
                preview[3][4], preview[3][5], preview[3][6], preview[3][7]);

            // Preserve server::process_accepted_msg()'s current unknown-opcode
            // guest-visible result exactly.
            ctx.complete(epoc::error_not_supported);
            return;
        }

'''
    text=rep1(text,anchor,block+anchor,"B42 SA anchor")

    reg_anchor='''        REGISTER_IPC(sa_server, unk_op1, 0x2000000A, "NBOOT2::SaHwrmAbiProbe");
'''
    reg_new=reg_anchor+'''        REGISTER_IPC(sa_server, unk_op1, 0x67, "NBOOT2::SaExecuteSelftestsAbiProbe");
'''
    text=rep1(text,reg_anchor,reg_new,"B42 registration anchor")

    # Isolate B63 block and prohibit semantic changes beyond matching today's
    # generic unknown-opcode KErrNotSupported completion.
    bs=text.find("// NATIVEBOOT2-B63 SASELFTESTABI1:")
    be=text.find("// NATIVEBOOT2-B42 SAHWRMABI1:",bs)
    if bs<0 or be<0 or be<=bs:
        fail("cannot isolate B63 block")
    b=text[bs:be]

    for forbidden in (
        "epoc::error_none",
        "write_data_to_descriptor_argument",
        "set_descriptor_argument_length",
        "pending_sa_event_.complete(",
        "set_int(",
    ):
        if forbidden in b:
            fail("B63 changes guest semantics: "+forbidden)

    for need in (
        "[NBOOT2][SA_SELFTEST_ABI]",
        "ctx.msg->function == 0x67",
        "logical=EExecuteSelftests",
        "public_response=TResponsePckg_TInt",
        "completion=KErrNotSupported",
        "ctx.complete(epoc::error_not_supported);",
        'REGISTER_IPC(sa_server, unk_op1, 0x67, "NBOOT2::SaExecuteSelftestsAbiProbe");',
    ):
        if need not in text:
            fail("post-apply B63 gate missing: "+need)

    sa.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("command=StartupAdaptation::EExecuteSelftests")
    print("opcode=0x67")
    print("public_response=TResponsePckg_TInt")
    print("scope=ABI_CALLER_DIAGNOSTIC_ONLY")
    print("completion=KErrNotSupported_PRESERVED")
    print("state_injection=NONE")
    print("B61_B62=PRESERVED")

if __name__=="__main__":
    main()
