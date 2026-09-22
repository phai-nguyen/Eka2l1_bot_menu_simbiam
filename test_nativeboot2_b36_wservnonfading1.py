#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B36 WSERVHANDLECARRY1.

B35 device evidence correlates the repeated eiksrvs/AknFep Leave(-3) path with:
- ws32.dll export ordinal 206 = RWindowTreeNode::SetNonFading(TBool);
- opcode 0x5D in the immediate guest stack;
- repeated WindowServer "Object handle is invalid" events as EikAppUiServerThread starts.

Symbian WindowServer client/server source defines the command-buffer protocol:
the client omits a destination handle when it is unchanged, and the server must
reuse the destination object from the previous command in the same buffer.

The EKA2L1 baseline reads a new ws_cmd for every command but does not carry the
previous handle when bit 0x8000/EWsOpcodeHandle is absent. B36 fixes only this
generic protocol mismatch and adds narrow SetNonFading trace markers.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B36-WSERVHANDLECARRY1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b36_wservnonfading1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (window,winuser,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # Preserve B35 diagnostics.
    need(sv,"[NBOOT2][EIKCALLSITE]","B35")
    need(sv,"[NBOOT2][EIKCODE16]","B35")

    # Functional protocol correction: value-initialize the command and carry
    # the previous explicit handle into following implicit-handle commands.
    need(ws,"std::uint32_t nboot2_b36_previous_handle = 0;","command parser")
    need(ws,"ws_cmd cmd{};","command parser value initialization")
    need(ws,"nboot2_b36_previous_handle = cmd.obj_handle;","explicit-handle update")
    need(ws,"cmd.obj_handle = nboot2_b36_previous_handle;","implicit-handle reuse")
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","handle carry trace")

    # The SetNonFading handler already completes KErrNone on B35. B36 may trace
    # it but must not change its completion semantics.
    m=re.search(
        r"void\s+(?:canvas_base|window_user)::set_non_fading"
        r"\s*\([^\)]*\)\s*\{",
        wu,
    )
    if not m:
        fail("set_non_fading function not found")
    next_fn=wu.find("\n    void ",m.end())
    if next_fn < 0:
        fail("could not bound set_non_fading function")
    block=wu[m.start():next_fn]

    need(block,"context.complete(epoc::error_none);","SetNonFading baseline completion")
    need(block,"[NBOOT2][WSERV_NONFADING_ENTER]","SetNonFading trace entry")
    need(block,"[NBOOT2][WSERV_NONFADING_COMPLETE]","SetNonFading trace completion")
    need(block,"context.signaled","SetNonFading completion-state trace")

    for bad in (
        "context.complete(epoc::error_cancel);",
        "error_cancel = epoc::error_none",
        "avkonfep_general.dll",
    ):
        if bad in block:
            fail(f"out-of-scope behavior change: {bad}")

    # Do not disturb the host-exit fix or reintroduce Java.
    screen_h=up/"src/emu/services/include/services/window/screen.h"
    if screen_h.is_file():
        sh=screen_h.read_text(encoding="utf-8")
        need(sh,"std::mutex focus_callback_mutex;","B34 focus mutex split")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=WSERV_COMMAND_BUFFER_IMPLICIT_HANDLE_ONLY")
    print("set_non_fading_completion=UNCHANGED")
    print("stock_fep=PRESERVED")
    print("B34_B35=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
