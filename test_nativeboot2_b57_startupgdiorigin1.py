#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B57 STARTUPGDIORIGIN1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B57-STARTUPGDIORIGIN1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b57_startupgdiorigin1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    gctx=(up/"src/emu/services/src/window/classes/gctx.cpp").read_text(encoding="utf-8")
    winuser=(up/"src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")

    need(winuser,"[NBOOT2][STARTUP_GDI_SEGMENT]","B56 predecessor")
    need(winuser,"[NBOOT2][STARTUP_GDI_CMD]","B56 predecessor")
    need(gctx,"[NBOOT2][STARTUP_GDI_ORIGIN]","B57 marker")
    need(gctx,"source=GDI_BLT","BLIT origin")
    need(gctx,"source=CLEAR ","CLEAR origin")
    need(gctx,"source=CLEAR_RECT","CLEAR_RECT origin")
    need(gctx,"source=DRAW_RECT","DRAW_RECT origin")
    need(gctx,"source=SET_BRUSH_COLOR","brush color state")
    need(gctx,"source=SET_BRUSH_STYLE","brush style state")
    need(gctx,'find("100058f4")',"Startup UID filter")
    need(gctx,"gc_op=0x{:X}","guest GC opcode")
    need(gctx,"behavior=OBSERVE_ONLY","diagnostic scope")

    # The probe may observe commands but must not add rendering/scheduling mutations.
    if "FLAG_SERVER_REDRAW_PENDING" in gctx:
        fail("B57 gctx probe must not mutate server redraw flag")
    if "[NBOOT2][STARTUP_REPLAY]" in gctx:
        fail("B57 must not relocate B55 replay behavior into gctx")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_GDI_RECORD_ORIGIN")
    print("behavior_change=NONE")
    print("B56_COMMAND_TRACE=PRESERVED")

if __name__=="__main__":
    main()
