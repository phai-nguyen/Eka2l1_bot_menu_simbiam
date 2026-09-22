#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B36 WSERVNONFADINGTRACE1.

B35 device evidence proves the first stable guest caller is:
- ws32.dll + 0x370A
- export ordinal 206 = RWindowTreeNode::SetNonFading(TBool)
- command opcode 0x5D is present on the guest stack at User::Leave(-3).

The B28/B35 WindowServer baseline already contains
context.complete(epoc::error_none) inside set_non_fading(), so B36 must not
pretend that adding the completion is a functional fix.

B36 is diagnostic-only. It must prove whether opcode 0x5D:
1) reaches object dispatch;
2) enters set_non_fading with a valid payload;
3) completes/signals the HLE IPC context;
4) returns from object dispatch.

No FEP, Leave/trap, IPC result, or WindowServer semantics may be changed.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B36-WSERVNONFADINGTRACE1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b36_wservnonfading1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (winuser,window,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    wu=winuser.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # B35 evidence must remain present.
    need(sv,"[NBOOT2][EIKCALLSITE]","B35")
    need(sv,"[NBOOT2][EIKCODE16]","B35")

    # The existing completion is baseline behavior, not the B36 change.
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
    need(block,"context.complete(epoc::error_none);","set_non_fading baseline completion")

    # New B36 trace points.
    need(ws,"[NBOOT2][WSERV_NONFADING_DISPATCH]","window dispatch")
    need(wu,"[NBOOT2][WSERV_NONFADING_ENTER]","set_non_fading entry")
    need(wu,"[NBOOT2][WSERV_NONFADING_COMPLETE]","set_non_fading completion")
    need(ws,"[NBOOT2][WSERV_NONFADING_RETURN]","window dispatch return")

    # Diagnostic-only behavior gates.
    for bad in (
        "context.complete(epoc::error_cancel);",
        "ctx.complete(epoc::error_cancel);",
        "error_cancel = epoc::error_none",
        "avkonfep_general.dll",
    ):
        if bad in block:
            fail(f"B36 changed SetNonFading behavior: {bad}")

    need(ws,"if (cmd.header.op == EWsWinOpSetNonFading)","0x5D dispatch guard")
    need(wu,"context.signaled","completion-state trace")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
