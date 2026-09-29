#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B38 EIKCANCELTRACE2 after B37.

B37 device evidence proves WindowServer request-signal deferral works as
designed, but the same EikAppUiServerThread User::Leave(-3) chain remains.
The first Leave occurs before the later batch that dispatches SetNonFading,
so B38 is diagnostic-only.

B38 adds:
- generic per-command WindowServer batch tracing plus effective batch completion
  result capture;
- direct PC/LR nearest-export resolution and bounded 16-bit code windows for
  KErrCancel leaves.

No FEP, WindowServer dispatch, completion value, request signaling, leave/trap,
SVC, scheduler, loader, or host-exit behavior is changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B38-EIKCANCELTRACE2"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b38_eikcanceltrace2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ctxh=up/"src/emu/services/include/services/context.h"
    ctxc=up/"src/emu/services/src/context.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (ctxh,ctxc,window,svc,winuser,screenh):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    ch=ctxh.read_text(encoding="utf-8")
    cc=ctxc.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    for needle,name,text in (
        ("[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry",ws),
        ("[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral",ws),
        ("[NBOOT2][WSERV_BATCH_SIGNAL]","B37 batch signal",ws),
        ("[NBOOT2][WSERV_NONFADING_ENTER]","B36 SetNonFading",wu),
        ("[NBOOT2][EIKFAULT_LEAVE]","B32 leave trace",sv),
        ("[NBOOT2][EIKCALLSITE]","B35 stack callsite",sv),
        ("std::mutex focus_callback_mutex;","B34 focus mutex",sh),
        ("bool defer_request_signal = false;","B37 context state",ch),
        ("bool completion_written = false;","B37 context state",ch),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][WSERV_BATCH_CMD]",
        "[NBOOT2][WSERV_BATCH_RESULT]",
        "[NBOOT2][EIKDIRECT_FRAME]",
        "[NBOOT2][EIKDIRECT_CODE16]",
    )
    combined=ch+"\n"+cc+"\n"+ws+"\n"+sv
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers) and "nboot2_b38_last_completion_result" in combined:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B38 state: "+", ".join(present))

    header_old="""            bool defer_request_signal = false;
            bool completion_written = false;

"""
    header_new="""            bool defer_request_signal = false;
            bool completion_written = false;

            // B38 EIKCANCELTRACE2: diagnostic mirror of the most recent
            // completion value written by this IPC context.
            int nboot2_b38_last_completion_result = 0;

"""
    ch=replace_once(ch,header_old,header_new,"B38 context diagnostic state")

    complete_old="""                completion_written = true;

                // Avoid signal twice to cause undefined behavior. B37 keeps
"""
    complete_new="""                completion_written = true;
                nboot2_b38_last_completion_result = res;

                // Avoid signal twice to cause undefined behavior. B37 keeps
"""
    cc=replace_once(cc,complete_old,complete_new,"B38 complete result capture")

    flush_old="""                (msg->request_sts.get(msg->own_thr->owning_process()))->set(
                    epoc::error_none, kern->is_eka1());
                completion_written = true;
"""
    flush_new="""                (msg->request_sts.get(msg->own_thr->owning_process()))->set(
                    epoc::error_none, kern->is_eka1());
                completion_written = true;
                nboot2_b38_last_completion_result = epoc::error_none;
"""
    cc=replace_once(cc,flush_old,flush_new,"B38 deferred-default result capture")

    exec_old="""    void window_server_client::execute_commands(service::ipc_context &ctx, std::vector<ws_cmd> cmds) {
        for (auto &cmd : cmds) {
            if (cmd.obj_handle == guest_session->unique_id()) {
                if (last_obj) {
                    last_obj->on_command_batch_done(ctx);
                    last_obj = nullptr;
                }

                execute_command(ctx, cmd);
            } else {
                if (auto obj = get_object(cmd.obj_handle)) {
                    if (last_obj != obj) {
                        if (last_obj != nullptr) {
                            last_obj->on_command_batch_done(ctx);
                        }

                        last_obj = obj;
                    }

                    if (obj->execute_command(ctx, cmd)) {
                        // The command batch is silently flushed...
                        last_obj = nullptr;
                    }
                }
            }
        }

        if (last_obj) {
            last_obj->on_command_batch_done(ctx);
            last_obj = nullptr;
        }
    }
"""
    exec_new="""    void window_server_client::execute_commands(service::ipc_context &ctx, std::vector<ws_cmd> cmds) {
        std::uint32_t nboot2_b38_cmd_index = 0;
        std::uint32_t nboot2_b38_last_op = 0;
        std::uint32_t nboot2_b38_last_handle = 0;

        for (auto &cmd : cmds) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][WSERV_BATCH_CMD] index={} op=0x{:X} obj_handle=0x{:08X} cmd_len={} completion_written_before={} last_result_before={} signaled_before={}",
                nboot2_b38_cmd_index, cmd.header.op, cmd.obj_handle,
                cmd.header.cmd_len, ctx.completion_written ? 1 : 0,
                ctx.nboot2_b38_last_completion_result, ctx.signaled ? 1 : 0);

            nboot2_b38_last_op = cmd.header.op;
            nboot2_b38_last_handle = cmd.obj_handle;

            if (cmd.obj_handle == guest_session->unique_id()) {
                if (last_obj) {
                    last_obj->on_command_batch_done(ctx);
                    last_obj = nullptr;
                }

                execute_command(ctx, cmd);
            } else {
                if (auto obj = get_object(cmd.obj_handle)) {
                    if (last_obj != obj) {
                        if (last_obj != nullptr) {
                            last_obj->on_command_batch_done(ctx);
                        }

                        last_obj = obj;
                    }

                    if (obj->execute_command(ctx, cmd)) {
                        // The command batch is silently flushed...
                        last_obj = nullptr;
                    }
                }
            }

            ++nboot2_b38_cmd_index;
        }

        if (last_obj) {
            last_obj->on_command_batch_done(ctx);
            last_obj = nullptr;
        }

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WSERV_BATCH_RESULT] commands={} last_op=0x{:X} last_handle=0x{:08X} completion_written={} last_result={} signaled={}",
            nboot2_b38_cmd_index, nboot2_b38_last_op, nboot2_b38_last_handle,
            ctx.completion_written ? 1 : 0,
            ctx.nboot2_b38_last_completion_result, ctx.signaled ? 1 : 0);
    }
"""
    ws=replace_once(ws,exec_old,exec_new,"B38 WindowServer command/result tracing")

    direct_anchor="""            nboot2_b32_log_frame("pc", pc);
            nboot2_b32_log_frame("lr", lr);
            nboot2_b32_log_frame("trap", trap);

            for (std::uint32_t i=0; i<32; ++i) {
"""
    direct_new=r"""            nboot2_b32_log_frame("pc", pc);
            nboot2_b32_log_frame("lr", lr);
            nboot2_b32_log_frame("trap", trap);

            // B38 EIKCANCELTRACE2: direct PC/LR symbol/code context.
            auto nboot2_b38_log_direct_frame =
                [&](const char *kind, std::uint32_t raw) {
                const std::uint32_t candidate=raw & ~1U;
                codeseg_ptr seg=get_codeseg_from_addr(
                    kern,nboot2_b32_pr,candidate,false);
                if (!seg) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKDIRECT_FRAME] kind={} raw=0x{:08X} module=<unresolved>",
                        kind,raw);
                    return;
                }

                const std::uint32_t base=
                    seg->get_code_run_addr(nboot2_b32_pr);
                const auto exports=seg->get_export_table(nboot2_b32_pr);
                std::uint32_t nearest_export_ordinal=0;
                std::uint32_t nearest_export_address=0;
                std::uint32_t nearest_export_delta=0xFFFFFFFFU;
                const std::uint32_t code_end=base+seg->get_code_size();

                for (std::size_t export_index=0;
                     export_index<exports.size(); ++export_index) {
                    const std::uint32_t export_raw=exports[export_index];
                    const std::uint32_t export_address=export_raw & ~1U;
                    if ((export_address < base) || (export_address >= code_end)
                        || (export_address > candidate)) {
                        continue;
                    }

                    const std::uint32_t export_delta=
                        candidate-export_address;
                    if (export_delta < nearest_export_delta) {
                        nearest_export_delta=export_delta;
                        nearest_export_address=export_raw;
                        nearest_export_ordinal=
                            static_cast<std::uint32_t>(export_index+1);
                    }
                }

                LOG_WARN(KERNEL,
                    "[NBOOT2][EIKDIRECT_FRAME] kind={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X} thumb={} nearest_export_ordinal={} nearest_export=0x{:08X} nearest_export_delta=0x{:08X}",
                    kind,raw,common::ucs2_to_utf8(seg->get_full_path()),
                    base,candidate-base,(raw & 1U) ? 1 : 0,
                    nearest_export_ordinal,nearest_export_address,
                    nearest_export_delta);

                for (std::int32_t relative_halfword=-8;
                     relative_halfword<=4; ++relative_halfword) {
                    const std::int64_t signed_code_address=
                        static_cast<std::int64_t>(candidate)
                        + static_cast<std::int64_t>(relative_halfword)*2;
                    if ((signed_code_address < 0)
                        || (signed_code_address > 0xFFFFFFFFLL)) {
                        continue;
                    }

                    const std::uint32_t code_address=
                        static_cast<std::uint32_t>(signed_code_address);
                    const std::uint16_t *code16=
                        eka2l1::ptr<std::uint16_t>(code_address).get(
                            nboot2_b32_pr);
                    if (!code16) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKDIRECT_CODE16] kind={} relative_halfword={} address=0x{:08X} mapped=0",
                            kind,relative_halfword,code_address);
                        continue;
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKDIRECT_CODE16] kind={} relative_halfword={} address=0x{:08X} code16=0x{:04X}",
                        kind,relative_halfword,code_address,*code16);
                }
            };

            nboot2_b38_log_direct_frame("pc", pc);
            nboot2_b38_log_direct_frame("lr", lr);

            for (std::uint32_t i=0; i<32; ++i) {
"""
    sv=replace_once(sv,direct_anchor,direct_new,"B38 direct leave-frame diagnostics")

    if "context.complete(epoc::error_cancel);" in wu:
        fail("SetNonFading cancellation behavior change detected")
    if "avkonfep_general.dll" in (ws+"\n"+sv+"\n"+cc):
        fail("stock FEP invariant violated")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope SVC backport detected")
    if "epoc::error_cancel = epoc::error_none" in sv:
        fail("KErrCancel suppression detected")

    d=ws.find("ctx.defer_request_signal = true;")
    e=ws.find("execute_commands(ctx, std::move(cmds));",d)
    f=ws.find("ctx.flush_deferred_completion();",e)
    if min(d,e,f) < 0 or not (d < e < f):
        fail("B37 defer/execute/flush ordering changed")

    ctxh.write_text(ch,encoding="utf-8")
    ctxc.write_text(cc,encoding="utf-8")
    window.write_text(ws,encoding="utf-8")
    svc.write_text(sv,encoding="utf-8")

    final=ch+"\n"+cc+"\n"+ws+"\n"+sv
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")
    for needle in (
        "nboot2_b38_last_completion_result = res;",
        "nboot2_b38_last_completion_result = epoc::error_none;",
        'nboot2_b38_log_direct_frame("pc", pc);',
        'nboot2_b38_log_direct_frame("lr", lr);',
        "thr->increase_leave_depth();",
        "return current_local_data(kern)->trap_handler;",
    ):
        if needle not in final:
            fail(f"post-apply semantic missing: {needle}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("wserv_dispatch=UNCHANGED")
    print("completion_values=UNCHANGED")
    print("request_signal_timing=UNCHANGED_FROM_B37")
    print("leave_trap_behavior=UNCHANGED")
    print("stock_fep=PRESERVED")
    print("B34_B35_B36_B37=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
