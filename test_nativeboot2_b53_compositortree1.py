#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B53 COMPOSITORTREE1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B53-COMPOSITORTREE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b53_compositortree1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    state_path=up/"src/emu/ios/src/state.cpp"
    sched_path=up/"src/emu/services/src/window/scheduler.cpp"

    for p in (screen_path,state_path,sched_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    screen=screen_path.read_text(encoding="utf-8")
    state=state_path.read_text(encoding="utf-8")
    sched=sched_path.read_text(encoding="utf-8")

    need(screen,"[NBOOT2][COMPOSITOR_FRAME]","frame trace")
    need(screen,"[NBOOT2][COMPOSITOR_GROUP]","group trace")
    need(screen,"[NBOOT2][COMPOSITOR_CANVAS]","canvas trace")
    need(screen,'find("100058f4")',"Startup name tracking")
    need(screen,'find("102750f0")',"Home name tracking")
    need(screen,"visible_region.empty()","physical visibility evidence")
    need(screen,"draw_result={}","draw result evidence")

    # B51/B52 predecessors remain.
    need(screen,"[NBOOT2][DIRECTSCREEN_REDRAW]","B51 redraw")
    need(state,"[NBOOT2][DIRECTSCREEN_PRESENT]","B51 present")
    need(sched,"[NBOOT2][REDRAW_SCHED]","B52 scheduler")
    need(screen,"[NBOOT2][POSTLOGO_FOCUS]","focus trace")

    # The compositor must still call each canvas draw exactly once inside walker.
    ws=screen.find("struct window_drawer_walker")
    we=screen.find("struct window_dsa_abort_walker",ws)
    if ws<0 or we<0:
        fail("cannot isolate window_drawer_walker")
    wb=screen[ws:we]
    if wb.count("cv->draw(builder_)")!=1:
        fail("canvas draw call count changed")
    need(wb,"total_redrawed_++;","original drawn counter")

    # Original color clear remains conditional on SERVER_REDRAW_PENDING.
    rs=screen.find("bool screen::redraw(drivers::graphics_command_builder")
    re=screen.find("void screen::redraw(drivers::graphics_driver",rs)
    if rs<0 or re<0:
        fail("cannot isolate compositor redraw")
    rb=screen[rs:re]
    clear='''((flags_ & FLAG_SERVER_REDRAW_PENDING) ? drivers::draw_buffer_bit_color_buffer : 0)'''
    need(rb,clear,"conditional color clear")
    if rb.count("builder.clear(")!=1:
        fail("B53 must not add another clear")
    if rb.count("root->walk_tree_back_to_front(&adrawwalker);")!=1:
        fail("window tree draw traversal count changed")
    need(rb,"return adrawwalker.total_redrawed_;","original return")

    # Observe only: no direct state mutation introduced by B53 markers.
    if "flags_ |= FLAG_SERVER_REDRAW_PENDING" in rb:
        fail("B53 must not force server redraw pending")
    if "set_receive_focus(" in rb or "set_position(" in rb:
        fail("B53 must not modify focus/order")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("group_tracking=NAME_UID_BASED")
    print("color_clear_change=NONE")
    print("guest_focus_change=NONE")
    print("guest_z_order_change=NONE")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("B52_SCHED_TRACE=PRESERVED")

if __name__=="__main__":
    main()
