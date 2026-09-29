#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B54 TRANSITIONCLEAR1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B54-TRANSITIONCLEAR1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b54_transitionclear1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    state_path=up/"src/emu/ios/src/state.cpp"
    sched_path=up/"src/emu/services/src/window/scheduler.cpp"
    winuser_path=up/"src/emu/services/src/window/classes/winuser.cpp"

    for p in (screen_path,state_path,sched_path,winuser_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    screen=screen_path.read_text(encoding="utf-8")
    state=state_path.read_text(encoding="utf-8")
    sched=sched_path.read_text(encoding="utf-8")
    winuser=winuser_path.read_text(encoding="utf-8")

    need(screen,"[NBOOT2][TRANSITION_CLEAR]","B54 marker")
    need(screen,"b54_previous_startup_focus","one-shot edge state")
    need(screen,"b54_transition_clear","transition clear gate")
    need(screen,'find("100058f4")',"Startup UID gate")
    need(screen,"scope=ONE_STARTUP_FOCUS_EDGE","runtime scope")

    # Predecessor traces remain.
    need(screen,"[NBOOT2][COMPOSITOR_FRAME]","B53 frame")
    need(screen,"[NBOOT2][COMPOSITOR_GROUP]","B53 groups")
    need(screen,"[NBOOT2][COMPOSITOR_CANVAS]","B53 canvas")
    need(screen,"[NBOOT2][DIRECTSCREEN_REDRAW]","B51 redraw")
    need(state,"[NBOOT2][DIRECTSCREEN_PRESENT]","B51 present")
    need(sched,"[NBOOT2][REDRAW_SCHED]","B52 scheduler")

    # Active B28 canvas semantics must match the evidence basis.
    ds=winuser.find("bool redraw_msg_canvas::draw(drivers::graphics_command_builder")
    de=winuser.find("bool redraw_msg_canvas::execute_command",ds)
    if ds<0 or de<0:
        fail("cannot isolate redraw_msg_canvas::draw")
    db=winuser[ds:de]
    need(db,"if (scr->flags_ & screen::FLAG_SERVER_REDRAW_PENDING)","server redraw branch")
    need(db,"if (scr->flags_ & screen::FLAG_CLIENT_REDRAW_PENDING)","client redraw branch")
    need(db,"return true;","ambiguous draw result")

    rs=screen.find("bool screen::redraw(drivers::graphics_command_builder")
    re=screen.find("void screen::redraw(drivers::graphics_driver",rs)
    if rs<0 or re<0:
        fail("cannot isolate compositor redraw")
    rb=screen[rs:re]

    # Still exactly one clear command; B54 only extends its bit mask.
    if rb.count("builder.clear(")!=1:
        fail("B54 must not add a second clear")
    need(rb,"((flags_ & FLAG_SERVER_REDRAW_PENDING) || b54_transition_clear)","one-shot clear bit")
    need(rb,"b54_startup_focus &&","Startup edge gate")
    need(rb,"!b54_previous_startup_focus","edge-only gate")
    need(rb,"((flags_ & FLAG_SERVER_REDRAW_PENDING) == 0)","only when normal clear absent")

    if "flags_ |= FLAG_SERVER_REDRAW_PENDING" in rb:
        fail("B54 must not forge server redraw pending")
    if "builder.present(" in rb:
        fail("B54 must not add present")
    if "set_receive_focus(" in rb or "set_position(" in rb:
        fail("B54 must not modify focus/order")
    if rb.count("root->walk_tree(&adrawwalker, window_tree_walk_style::bonjour_children);")!=1:
        fail("B28 tree traversal changed")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=CONTROLLED_FUNCTIONAL_EXPERIMENT")
    print("trigger=PRIMARY_SCREEN_STARTUP_FOCUS_EDGE")
    print("extra_clear_command=NONE")
    print("existing_clear_color_bit=ONE_SHOT")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("focus_change=NONE")
    print("z_order_change=NONE")
    print("B53_COMPOSITOR_TRACE=PRESERVED")

if __name__=="__main__":
    main()
