#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B55 STARTUPREPLAY1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B55-STARTUPREPLAY1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b55_startupreplay1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen=(up/"src/emu/services/src/window/screen.cpp").read_text(encoding="utf-8")
    winuser=(up/"src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")
    state=(up/"src/emu/ios/src/state.cpp").read_text(encoding="utf-8")
    sched=(up/"src/emu/services/src/window/scheduler.cpp").read_text(encoding="utf-8")

    need(screen,"[NBOOT2][STARTUP_REPLAY]","screen replay marker")
    need(winuser,"[NBOOT2][STARTUP_REPLAY_CANVAS]","canvas replay marker")
    need(screen,"[NBOOT2][TRANSITION_CLEAR]","B54 predecessor")
    need(screen,"[NBOOT2][COMPOSITOR_FRAME]","B53 predecessor")
    need(state,"[NBOOT2][DIRECTSCREEN_PRESENT]","B51 predecessor")
    need(sched,"[NBOOT2][REDRAW_SCHED]","B52 predecessor")

    rs=screen.find("bool screen::redraw(drivers::graphics_command_builder")
    re=screen.find("void screen::redraw(drivers::graphics_driver",rs)
    if rs<0 or re<0:
        fail("cannot isolate compositor redraw")
    rb=screen[rs:re]

    if rb.count("flags_ |= FLAG_SERVER_REDRAW_PENDING;")!=1:
        fail("one-shot server redraw pending mutation count is not one")
    need(rb,"if (b54_transition_clear)","must reuse B54 proven transition edge")
    if rb.count("builder.clear(")!=1:
        fail("B55 must preserve exactly one clear command")
    if "builder.present(" in rb:
        fail("B55 must not add present")
    if "set_position(" in rb or "set_receive_focus(" in rb:
        fail("B55 must not alter order/focus")
    if rb.count("root->walk_tree(&adrawwalker, window_tree_walk_style::bonjour_children);")!=1:
        fail("B28 tree traversal changed")

    ds=winuser.find("bool redraw_msg_canvas::draw(drivers::graphics_command_builder")
    de=winuser.find("bool redraw_msg_canvas::execute_command",ds)
    if ds<0 or de<0:
        fail("cannot isolate redraw_msg_canvas::draw")
    db=winuser[ds:de]

    need(db,"if (scr->flags_ & screen::FLAG_SERVER_REDRAW_PENDING)","server replay branch")
    need(db,"segments.size()","segment count observation")
    need(db,"b55_drawable_segments","drawable segment observation")
    need(db,'find("100058f4")',"Startup UID filter")
    if db.count("gdi_builder.build_segment(*segments[i]);")!=1:
        fail("stored segment replay call count changed")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=CONTROLLED_FUNCTIONAL_EXPERIMENT")
    print("trigger=B54_ONE_STARTUP_FOCUS_EDGE")
    print("server_redraw_pending=ONE_SHOT_SET")
    print("stored_segments=REPLAY_THROUGH_EXISTING_PATH")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("extra_clear_command=NONE")
    print("focus_change=NONE")
    print("z_order_change=NONE")
    print("B54_TRANSITION_CLEAR=PRESERVED")

if __name__=="__main__":
    main()
