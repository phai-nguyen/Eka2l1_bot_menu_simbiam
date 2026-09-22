#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B36 WSERVNONFADING1.

B35 device evidence resolves the stable guest KErrCancel path to
ws32.dll export ordinal 206, RWindowTreeNode::SetNonFading(TBool).
Upstream EKA2L1 commit 58c4bf51864481b9dce5a82e8d846870f35628ad
fixed this exact service path by completing the IPC with KErrNone.

This first-stage contract intentionally checks only whether the restored
NativeBoot baseline already contains that completion. It is expected to be
RED before the B36 apply patch.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B36-WSERVNONFADING1-TEST"\n# RED rerun: manifest now includes this contract.

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b36_wservnonfading1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    src=up/"src/emu/services/src/window/classes/winuser.cpp"
    if not src.is_file():
        fail(f"missing source file: {src}")

    text=src.read_text(encoding="utf-8")
    m=re.search(
        r"\n    void\s+(?:canvas_base|window_user)::set_non_fading"
        r"\s*\([^\)]*\)\s*\{",
        text,
    )
    if not m:
        fail("set_non_fading function not found")

    next_fn=text.find("\n    void ",m.end())
    if next_fn < 0:
        fail("could not bound set_non_fading function")
    block=text[m.start():next_fn]

    if "context.complete(epoc::error_none);" not in block:
        fail("missing set_non_fading IPC completion: context.complete(epoc::error_none);")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
