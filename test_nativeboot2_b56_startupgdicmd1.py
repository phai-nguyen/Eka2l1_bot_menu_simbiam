#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B56 STARTUPGDICMD1."""

from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B56-STARTUPGDICMD1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b56_startupgdicmd1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    winuser = (up / "src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")
    screen = (up / "src/emu/services/src/window/screen.cpp").read_text(encoding="utf-8")

    need(winuser, "[NBOOT2][STARTUP_REPLAY_CANVAS]", "B55 predecessor")
    need(screen, "[NBOOT2][STARTUP_REPLAY]", "B55 predecessor")
    need(winuser, "[NBOOT2][STARTUP_GDI_SEGMENT]", "B56 segment marker")
    need(winuser, "[NBOOT2][STARTUP_GDI_CMD]", "B56 command marker")
    need(winuser, "[NBOOT2][STARTUP_GDI_DETAIL]", "B56 detail marker")
    need(winuser, "gdi_store_command_draws_pixels(b56_cmd.opcode_)", "actual pixel-op classification")
    need(winuser, "b56_seg.commands_.size()", "stored command enumeration")
    need(winuser, "kind=DRAW_RECT", "draw-rect detail")
    need(winuser, "kind=DRAW_BITMAP", "draw-bitmap detail")
    need(winuser, "kind=DRAW_TEXT", "draw-text detail")
    need(winuser, "kind=CLIP_SINGLE", "clip detail")
    need(winuser, "kind=UPDATE_TEXTURE", "texture detail")

    ds = winuser.find("bool redraw_msg_canvas::draw(drivers::graphics_command_builder")
    de = winuser.find("bool redraw_msg_canvas::execute_command", ds)
    if ds < 0 or de < 0:
        fail("cannot isolate redraw_msg_canvas::draw")
    db = winuser[ds:de]

    if db.count("gdi_builder.build_segment(*segments[i]);") != 1:
        fail("B55/B28 stored replay call changed")
    if "flags_ |= screen::FLAG_SERVER_REDRAW_PENDING" in db:
        fail("B56 must not introduce redraw flag mutation inside draw()")
    if "set_position(" in db or "set_receive_focus(" in db:
        fail("B56 must not alter focus/z-order")
    if "builder.present(" in db:
        fail("B56 must not add present")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK + ": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_STORED_GDI_COMMAND_STREAM")
    print("behavior_change=NONE")
    print("B55_STARTUP_REPLAY=PRESERVED")

if __name__ == "__main__":
    main()
