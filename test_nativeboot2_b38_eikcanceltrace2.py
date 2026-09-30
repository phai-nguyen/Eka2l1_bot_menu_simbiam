#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B38 EIKCANCELTRACE2.

B37 device evidence proves WindowServer batch request signaling is now deferred
correctly, but the same 16 EikAppUiServerThread User::Leave(-3) failures remain.
The first Leave occurs before the later batch that dispatches SetNonFading, so
B38 is diagnostic-only.

B38 must:
1) expose every WindowServer command's opcode/object within a batch and the
   effective completion result at batch end;
2) resolve the direct KErrCancel leave PC/LR to nearest exports and bounded
   code windows, not only stack candidates;
3) preserve all B36/B37 behavior and guest error semantics.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B38-EIKCANCELTRACE2-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b38_eikcanceltrace2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ctxh=up/"src/emu/services/include/services/context.h"
    ctxc=up/"src/emu/services/src/context.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (ctxh,ctxc,window,svc,winuser,screenh):
        if not p.is_file():
            fail(f"missing source file: {p}")

    ch=ctxh.read_text(encoding="utf-8")
    cc=ctxc.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    # Preserve the already-device-observed chain.
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral")
    need(ws,"[NBOOT2][WSERV_BATCH_SIGNAL]","B37 batch signal")
    need(wu,"[NBOOT2][WSERV_NONFADING_ENTER]","B36 SetNonFading")
    need(sv,"[NBOOT2][EIKFAULT_LEAVE]","B32 leave trace")
    need(sv,"[NBOOT2][EIKCALLSITE]","B35 stack callsite")
    need(sh,"std::mutex focus_callback_mutex;","B34 focus mutex")

    # B38 completion-value diagnostics. This field is diagnostic state only.
    need(ch,"int nboot2_b38_last_completion_result = 0;","ipc_context diagnostic state")
    need(cc,"nboot2_b38_last_completion_result = res;","ipc_context::complete result capture")
    need(cc,"nboot2_b38_last_completion_result = epoc::error_none;","deferred default result capture")

    # Exact WindowServer command stream + effective batch result.
    need(ws,"[NBOOT2][WSERV_BATCH_CMD]","WindowServer command trace")
    need(ws,"[NBOOT2][WSERV_BATCH_RESULT]","WindowServer batch result trace")
    need(ws,"nboot2_b38_cmd_index","WindowServer command index")
    need(ws,"nboot2_b38_last_op","WindowServer last opcode")
    need(ws,"nboot2_b38_last_handle","WindowServer last object")
    need(ws,"ctx.nboot2_b38_last_completion_result","WindowServer result capture")

    # Direct leave PC/LR must be resolved independently of stack candidates.
    need(sv,"[NBOOT2][EIKDIRECT_FRAME]","direct PC/LR resolver")
    need(sv,"[NBOOT2][EIKDIRECT_CODE16]","direct PC/LR code window")
    need(sv,"nboot2_b38_log_direct_frame","direct frame helper")
    need(sv,'nboot2_b38_log_direct_frame("pc", pc);',"direct PC call")
    need(sv,'nboot2_b38_log_direct_frame("lr", lr);',"direct LR call")
    need(sv,"nearest_export_ordinal","nearest export resolution")
    need(sv,"relative_halfword","bounded code window")

    # Diagnostic-only: no error/completion suppression.
    need(sv,"thr->increase_leave_depth();","leave semantics")
    need(sv,"return current_local_data(kern)->trap_handler;","trap semantics")
    need(wu,"context.complete(epoc::error_none);","SetNonFading KErrNone")
    if "context.complete(epoc::error_cancel);" in wu:
        fail("SetNonFading behavior changed")
    if "epoc::error_cancel = epoc::error_none" in sv:
        fail("KErrCancel suppression detected")

    # Preserve B37 deferral ordering.
    d=ws.find("ctx.defer_request_signal = true;")
    e=ws.find("execute_commands(ctx, std::move(cmds));",d)
    f=ws.find("ctx.flush_deferred_completion();",e)
    if min(d,e,f) < 0 or not (d < e < f):
        fail("B37 defer/execute/flush ordering changed")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("wserv_behavior=UNCHANGED")
    print("completion_values=UNCHANGED")
    print("leave_trap_behavior=UNCHANGED")
    print("B34_B35_B36_B37=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
