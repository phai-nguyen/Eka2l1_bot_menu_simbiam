#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B42 SAHWRMABI1 after B41.

B41 device evidence exposes a new earlier boot boundary:
- HWRMServer loads Nokia lightsadaptation.dll;
- the plugin sends raw SAServer function 0x2000000A;
- the historical generic dispatcher logs it as unimplemented and leaves the
  request outstanding;
- roughly 30 seconds later SYSSTART starts HWRM failure recovery.

Public Symbian/Nokia sources do not define the proprietary raw transport ABI
for 0x2000000A. B42 is therefore diagnostic-only. It registers exactly this raw
function so the request can be inspected, logs caller/process/session and all
four IPC slots, and deliberately returns without completing or writing any
descriptor. This preserves the old outstanding-request behavior while replacing
only the low-information generic warning with a precise ABI probe.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B42-SAHWRMABI1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b42_sahwrmabi1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    sah=up/"src/emu/services/include/services/sms/sa/sa.h"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for p in (sa,sah,loader,messagewin,window,svc):
        if not p.is_file():
            fail(f"missing B41 baseline file: {p}")

    text=sa.read_text(encoding="utf-8")
    htext=sah.read_text(encoding="utf-8")

    for needle in (
        "[NBOOT2][SA_LANG_ABI]",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
        "[NBOOT2][SA_OP1_PENDING]",
        "pending_sa_event_.pending();",
    ):
        if needle not in text:
            fail(f"SA baseline gate missing: {needle}")
    for needle in (
        "pending_sa_event_",
        "pending_sa_event_session_",
        "void disconnect(service::ipc_context &context) override;",
    ):
        if needle not in htext:
            fail(f"SA header baseline gate missing: {needle}")
    if "[NBOOT2][LOADER_PDD]" not in loader.read_text(encoding="utf-8"):
        fail("B40 Loader PDD checkpoint missing")
    if "[NBOOT2][WSERV_MESSAGEWIN_EXIT]" not in messagewin.read_text(encoding="utf-8"):
        fail("B41 MessageWin exit checkpoint missing")
    wtext=window.read_text(encoding="utf-8")
    if "[NBOOT2][WSERV_HANDLE_CARRY]" not in wtext:
        fail("B36 handle-carry checkpoint missing")
    if "[NBOOT2][WSERV_BATCH_DEFER_BEGIN]" not in wtext:
        fail("B37 batch-deferral checkpoint missing")
    if "[NBOOT2][EIKFEP_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B39 diagnostic checkpoint missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    marker="[NBOOT2][SA_HWRM_ABI]"
    registration='REGISTER_IPC(sa_server, unk_op1, 0x2000000A, "NBOOT2::SaHwrmAbiProbe");'
    if marker in text:
        if registration in text and "completion=UNCHANGED_PENDING" in text:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B42 state")

    if "#include <kernel/process.h>" not in text:
        inc_old='''#include <system/epoc.h>
#include <utils/err.h>
'''
        inc_new='''#include <system/epoc.h>
#include <utils/err.h>

#include <kernel/process.h>
#include <kernel/thread.h>
'''
        text=replace_once(text,inc_old,inc_new,"B42 kernel caller includes")

    anchor='''        // NATIVEBOOT2-B19 SALANGABI1:
'''
    block='''        // NATIVEBOOT2-B42 SAHWRMABI1:
        // RM-356 HWRMServer/lightsadaptation.dll sends this exact proprietary
        // raw SAServer function. The transport encoding and response contract
        // are not public, so this probe must not invent either. Preserve the
        // historical unknown-IPC behavior by returning with the request still
        // outstanding after recording its full caller/slot ABI.
        if (ctx.msg && (ctx.msg->function == 0x2000000A)) {
            const std::uint32_t raw_func =
                static_cast<std::uint32_t>(ctx.msg->function);
            const std::uint32_t logical_func = raw_func & 0xFFFFU;
            const std::uint32_t transport_bits = raw_func & 0xFFFF0000U;

            std::string process_name = "<null>";
            std::string thread_name = "<null>";
            std::uint64_t session_id = 0;

            if (ctx.msg->own_thr) {
                thread_name = ctx.msg->own_thr->name();
                if (ctx.msg->own_thr->owning_process()) {
                    process_name = ctx.msg->own_thr->owning_process()->raw_name();
                }
            }
            if (ctx.msg->msg_session) {
                session_id = ctx.msg->msg_session->unique_id();
            }

            std::uint32_t preview[4][8] = {};
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
                "[NBOOT2][SA_HWRM_ABI] raw_func=0x{:08X} logical_func=0x{:X} "
                "transport_bits=0x{:08X} ipc_flag=0x{:X} "
                "process={} thread={} session={} "
                "raw_args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "types=[{},{},{},{}] sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "has_desc=[{},{},{},{}] "
                "preview0=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview1=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview2=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "preview3=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "completion=UNCHANGED_PENDING",
                raw_func, logical_func, transport_bits,
                static_cast<std::uint32_t>(ctx.flag()),
                process_name, thread_name, session_id,
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
                preview[0][4], preview[0][5], preview[0][6], preview[0][7],
                preview[1][0], preview[1][1], preview[1][2], preview[1][3],
                preview[1][4], preview[1][5], preview[1][6], preview[1][7],
                preview[2][0], preview[2][1], preview[2][2], preview[2][3],
                preview[2][4], preview[2][5], preview[2][6], preview[2][7],
                preview[3][0], preview[3][1], preview[3][2], preview[3][3],
                preview[3][4], preview[3][5], preview[3][6], preview[3][7]);

            // Intentionally no completion call and no descriptor writes.
            // The old generic unknown-IPC path also left this request pending.
            return;
        }

'''
    text=replace_once(text,anchor,block+anchor,"B42 diagnostic block anchor")

    reg_anchor='        REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");\n'
    reg_new=reg_anchor+f'        {registration}\n'
    text=replace_once(text,reg_anchor,reg_new,"B42 exact raw opcode registration")

    start=text.find("// NATIVEBOOT2-B42 SAHWRMABI1:")
    end=text.find("// NATIVEBOOT2-B19 SALANGABI1:",start)
    if start < 0 or end < 0 or end <= start:
        fail("cannot isolate post-apply B42 block")
    b=text[start:end]
    for forbidden in (
        "ctx.complete(",
        "write_data_to_descriptor_argument",
        "set_descriptor_argument_length",
        "pending_sa_event_.complete(",
    ):
        if forbidden in b:
            fail(f"B42 diagnostic block changes guest semantics: {forbidden}")

    for needle in (
        marker,
        "ctx.msg->function == 0x2000000A",
        "completion=UNCHANGED_PENDING",
        registration,
        "own_thr->owning_process()->raw_name()",
        "own_thr->name()",
        "msg_session->unique_id()",
    ):
        if needle not in text:
            fail(f"post-apply B42 gate missing: {needle}")

    sa.write_text(text,encoding="utf-8")

    print(f"{MARK}: applied")
    print("scope=EXACT_RAW_SASERVER_0x2000000A_DIAGNOSTIC_ONLY")
    print("caller_identity=PROCESS_THREAD_SESSION")
    print("descriptor_preview=32_BYTES_PER_SLOT")
    print("descriptor_writes=NONE")
    print("completion=UNCHANGED_PENDING")
    print("B19_B36_B37_B40_B41=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
