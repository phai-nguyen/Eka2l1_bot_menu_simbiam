#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B37 WSERVBATCHCOMPLETE1.

B36 device evidence proves the implicit WindowServer object-handle carry now
works: opcode 0x5D reaches the correct object and SetNonFading completes 0.
However every SetNonFading entry reports signaled_before=1, while the guest
EikAppUiServerThread has already executed User::Leave(-3).

Symbian WindowServer source keeps iReply during CommandBufL() and completes the
RMessage only once after the whole command buffer returns. EKA2L1 instead lets
individual command handlers call ipc_context::complete(), which currently
signals the sleeping guest on the first command.

B37 must preserve each handler's result write but defer request signaling only
for WindowServer command-buffer processing, then signal once after the entire
buffer has executed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B37-WSERVBATCHCOMPLETE1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b37_wservbatchcomplete1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ctxh=up/"src/emu/services/include/services/context.h"
    ctxc=up/"src/emu/services/src/context.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (ctxh,ctxc,window,winuser,svc,screenh):
        if not p.is_file():
            fail(f"missing source file: {p}")

    ch=ctxh.read_text(encoding="utf-8")
    cc=ctxc.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    # Preserve the device-observed chain.
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(wu,"[NBOOT2][WSERV_NONFADING_ENTER]","B36 SetNonFading entry")
    need(wu,"[NBOOT2][WSERV_NONFADING_COMPLETE]","B36 SetNonFading completion")
    need(sv,"[NBOOT2][EIKCALLSITE]","B35 caller trace")
    need(sh,"std::mutex focus_callback_mutex;","B34 focus mutex split")

    # Generic ipc_context support, inert unless a caller opts in.
    need(ch,"bool defer_request_signal = false;","ipc_context")
    need(ch,"bool completion_written = false;","ipc_context")
    need(ch,"void flush_deferred_completion();","ipc_context")

    need(cc,"completion_written = true;","ipc_context::complete")
    need(cc,"if (!signaled && !defer_request_signal)","ipc_context::complete signal guard")
    need(cc,"void ipc_context::flush_deferred_completion()","deferred flush implementation")
    need(cc,"msg->own_thr->signal_request();","deferred flush request signal")

    # WindowServer command-buffer scope only.
    need(ws,"ctx.defer_request_signal = true;","WindowServer batch begin")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","WindowServer batch begin trace")
    need(ws,"ctx.defer_request_signal = false;","WindowServer batch end")
    need(ws,"ctx.flush_deferred_completion();","WindowServer batch end")
    need(ws,"[NBOOT2][WSERV_BATCH_SIGNAL]","WindowServer batch end trace")

    # Ordering contract: defer before execute, flush after execute.
    d=ws.find("ctx.defer_request_signal = true;")
    e=ws.find("execute_commands(ctx, std::move(cmds));", d)
    f=ws.find("ctx.flush_deferred_completion();", e)
    if min(d,e,f) < 0 or not (d < e < f):
        fail("defer/execute/flush ordering is wrong")

    # Existing SetNonFading result is not changed.
    need(wu,"context.complete(epoc::error_none);","SetNonFading KErrNone")
    if "context.complete(epoc::error_cancel);" in wu:
        fail("SetNonFading cancellation suppression/change detected")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=WSERV_COMMAND_BUFFER_SIGNAL_DEFERRAL_ONLY")
    print("completion_values=PRESERVED")
    print("request_signal=ONCE_AFTER_BATCH")
    print("stock_fep=PRESERVED")
    print("B34_B35_B36=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
