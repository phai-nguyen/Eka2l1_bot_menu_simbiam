#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B37 WSERVBATCHCOMPLETE1 after B36.

B36 device evidence proves:
- implicit destination handle carry works for opcode 0x5D;
- SetNonFading reaches the correct object and writes KErrNone;
- every SetNonFading entry already has context.signaled == true;
- the corresponding guest User::Leave(-3) occurs before the host reaches
  SetNonFading.

Symbian WindowServer source keeps an iReply value while CommandBufL() executes
and completes the client RMessage once after the whole command buffer returns.
EKA2L1 instead lets every individual command call ipc_context::complete(),
which writes the request status and immediately signals the client thread.

B37 adds a generic opt-in request-signal deferral to ipc_context and enables it
only around WindowServer command-buffer execution. Completion/result writes are
preserved. The guest is signaled once, after the whole buffer has executed.

No FEP, Leave/trap, SVC, scheduler, loader, or exit behavior is changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B37-WSERVBATCHCOMPLETE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b37_wservbatchcomplete1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ctxh=up/"src/emu/services/include/services/context.h"
    ctxc=up/"src/emu/services/src/context.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (ctxh,ctxc,window,winuser,svc,screenh):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    ch=ctxh.read_text(encoding="utf-8")
    cc=ctxc.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    for needle,name,text in (
        ("[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry",ws),
        ("[NBOOT2][WSERV_NONFADING_ENTER]","B36 SetNonFading entry",wu),
        ("[NBOOT2][WSERV_NONFADING_COMPLETE]","B36 SetNonFading completion",wu),
        ("[NBOOT2][EIKCALLSITE]","B35 caller trace",sv),
        ("std::mutex focus_callback_mutex;","B34 focus mutex split",sh),
        ("[NBOOT2][EIKCANCEL_HLE]","B33 HLE completion trace",cc),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][WSERV_BATCH_DEFER_BEGIN]",
        "[NBOOT2][WSERV_BATCH_SIGNAL]",
    )
    combined=ch+"\n"+cc+"\n"+ws
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers) and "void ipc_context::flush_deferred_completion()" in cc:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B37 state: "+", ".join(present))

    # 1) Add opt-in state to ipc_context. Default false preserves every other
    # HLE service exactly.
    header_anchor='''            bool signaled = false; ///< A safe-check if a request status is set. This allow setting multiple
                ///< time with only one time it signaled the client.

'''
    header_new='''            bool signaled = false; ///< A safe-check if a request status is set. This allow setting multiple
                ///< time with only one time it signaled the client.

            // B37 WSERVBATCHCOMPLETE1: opt-in completion signal deferral.
            // Result/status writes still happen in complete(); only the request
            // signal is postponed while this flag is true.
            bool defer_request_signal = false;
            bool completion_written = false;

'''
    ch=replace_once(ch,header_anchor,header_new,"ipc_context deferral fields")

    decl_anchor='''            void complete(int res);

'''
    decl_new='''            void complete(int res);
            void flush_deferred_completion();

'''
    ch=replace_once(ch,decl_anchor,decl_new,"ipc_context deferred flush declaration")

    # 2) Preserve result writes in complete(), but suppress only the wakeup when
    # a caller explicitly enabled deferral.
    signal_old='''                // Avoid signal twice to cause undefined behavior
                if (!signaled) {
                    msg->own_thr->signal_request();
                    signaled = true;
                }
'''
    signal_new='''                completion_written = true;

                // Avoid signal twice to cause undefined behavior. B37 keeps
                // this exact behavior unless a caller explicitly defers the
                // signal while processing a multi-command server batch.
                if (!signaled && !defer_request_signal) {
                    msg->own_thr->signal_request();
                    signaled = true;
                }
'''
    cc=replace_once(cc,signal_old,signal_new,"ipc_context signal deferral")

    flag_anchor='''        int ipc_context::flag() const {
'''
    flush_impl='''        void ipc_context::flush_deferred_completion() {
            if (!msg || !msg->request_sts || signaled) {
                return;
            }

            kernel_system *kern = sys->get_kernel_system();

            // Symbian WindowServer initializes iReply to KErrNone before a
            // command buffer. If no command wrote a result, mirror that
            // default without waking the guest until the end of the batch.
            if (!completion_written) {
                (msg->request_sts.get(msg->own_thr->owning_process()))->set(
                    epoc::error_none, kern->is_eka1());
                completion_written = true;
            }

            msg->own_thr->signal_request();
            signaled = true;
        }

'''
    cc=replace_once(cc,flag_anchor,flush_impl+flag_anchor,"deferred completion flush implementation")

    # 3) Enable deferral only for WindowServer command-buffer execution.
    exec_anchor='''        execute_commands(ctx, std::move(cmds));
'''
    exec_new='''        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WSERV_BATCH_DEFER_BEGIN] commands={} signaled_before={} completion_written_before={}",
            cmds.size(), ctx.signaled ? 1 : 0, ctx.completion_written ? 1 : 0);

        ctx.defer_request_signal = true;
        execute_commands(ctx, std::move(cmds));
        ctx.defer_request_signal = false;
        ctx.flush_deferred_completion();

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WSERV_BATCH_SIGNAL] signaled_after={} completion_written_after={}",
            ctx.signaled ? 1 : 0, ctx.completion_written ? 1 : 0);
'''
    ws=replace_once(ws,exec_anchor,exec_new,"WindowServer batch signal deferral")

    # Scope gates.
    if "context.complete(epoc::error_cancel);" in wu:
        fail("SetNonFading cancellation behavior change detected")
    if "avkonfep_general.dll" in (ws+"\n"+wu+"\n"+cc):
        fail("stock FEP invariant violated")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope SVC backport detected")
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94")
    v94_end=sv.find("const eka2l1::hle::func_map svc_register_funcs_v93",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("cannot isolate EPOC94 SVC table")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0x2D," in v94:
        fail("out-of-scope EPOC94 SVC 0x2D implementation detected")

    # Deferral must remain generic and opt-in.
    if cc.count("defer_request_signal") != 1:
        fail(f"unexpected context.cpp defer_request_signal count={cc.count('defer_request_signal')}")
    if ws.count("ctx.defer_request_signal = true;") != 1:
        fail("WindowServer defer begin count is not one")
    if ws.count("ctx.flush_deferred_completion();") != 1:
        fail("WindowServer deferred flush count is not one")

    ctxh.write_text(ch,encoding="utf-8")
    ctxc.write_text(cc,encoding="utf-8")
    window.write_text(ws,encoding="utf-8")

    final=ch+"\n"+cc+"\n"+ws+"\n"+wu
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")
    for needle in (
        "completion_written = true;",
        "if (!signaled && !defer_request_signal)",
        "void ipc_context::flush_deferred_completion()",
        "ctx.defer_request_signal = true;",
        "ctx.defer_request_signal = false;",
        "ctx.flush_deferred_completion();",
        "context.complete(epoc::error_none);",
    ):
        if needle not in final:
            fail(f"post-apply semantic missing: {needle}")

    print(f"{MARK}: applied")
    print("scope=WSERV_COMMAND_BUFFER_SIGNAL_DEFERRAL_ONLY")
    print("completion_values=PRESERVED")
    print("request_signal=ONCE_AFTER_BATCH")
    print("symbian_reference=iReply_THEN_CompleteMessage")
    print("stock_fep=PRESERVED")
    print("leave_trap_behavior=UNCHANGED")
    print("B34_B35_B36=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
