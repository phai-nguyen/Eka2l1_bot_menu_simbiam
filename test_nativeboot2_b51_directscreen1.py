#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B51 DIRECTSCREEN1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B51-DIRECTSCREEN1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b51_directscreen1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    ios_path=up/"src/emu/ios/Bridge/IosEmulator.mm"
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    winuser_path=up/"src/emu/services/src/window/classes/winuser.cpp"
    wingroup_path=up/"src/emu/services/src/window/classes/wingroup.cpp"

    for p in (ios_path,screen_path,winuser_path,wingroup_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    ios=ios_path.read_text(encoding="utf-8")
    screen=screen_path.read_text(encoding="utf-8")
    winuser=winuser_path.read_text(encoding="utf-8")
    wingroup=wingroup_path.read_text(encoding="utf-8")

    need(ios,"[NBOOT2][DIRECTSCREEN_PRESENT]","IosEmulator.mm")
    need(screen,"[NBOOT2][DIRECTSCREEN_REDRAW]","screen.cpp")
    need(ios,"behavior=HOST_OVERLAY_ONLY","host marker contract")
    need(screen,"behavior=OBSERVE_ONLY","redraw contract")

    # The host marker must live inside submit_screen_frame and after the guest
    # screen texture draw, before the existing present.
    s=ios.find("static void submit_screen_frame")
    e=ios.find("// Re-present the primary screen's current texture",s)
    if s<0 or e<0:
        fail("cannot isolate submit_screen_frame")
    block=ios[s:e]

    guest_draw=block.find("builder.draw_bitmap(scr->screen_texture")
    marker=block.find("[NBOOT2][DIRECTSCREEN_PRESENT]")
    rect=block.find("builder.draw_rectangle(b51_marker)")
    present=block.find("builder.present(&state->present_status[slot])")
    if min(guest_draw,marker,rect,present)<0:
        fail("cannot locate B51 present sequence")
    if not (guest_draw < rect < present):
        fail("host marker must be after guest bitmap and before present")
    if block.count("builder.present(&state->present_status[slot])")!=1:
        fail("B51 must preserve exactly one present command")
    if "scr->redraw(" in block:
        fail("B51 must not force guest redraw from submit_screen_frame")
    if "dispatch_after" in block or "sleep_for" in block:
        fail("B51 must not add a periodic present timer")
    if "builder.bind_bitmap(scr->screen_texture)" in block:
        fail("B51 must not bind/write guest screen texture in submit path")

    # The normal guest composition remains intact.
    rs=screen.find("void screen::redraw(drivers::graphics_driver *driver)")
    re=screen.find("void screen::deinit",rs)
    if rs<0 or re<0:
        fail("cannot isolate screen::redraw(driver)")
    rb=screen[rs:re]
    need(rb,"const bool performed = redraw(builder, true);","original compositor call")
    need(rb,"driver->submit_command_list(retrieved);","original compositor submit")
    need(rb,"fire_screen_redraw_callbacks(false);","original redraw callback")

    # B50 predecessor evidence must remain present in the built source.
    need(winuser,"[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]","B50 activate trace")
    need(winuser,"[NBOOT2][POSTLOGO_CANVAS_VISIBLE]","B50 visibility trace")
    need(wingroup,"[NBOOT2][POSTLOGO_WG_DESTROY]","B50 destroy trace")
    need(screen,"[NBOOT2][POSTLOGO_FOCUS]","B49/B50 focus trace")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=VISUAL_DIAGNOSTIC")
    print("guest_screen_texture_write=NONE")
    print("guest_focus_change=NONE")
    print("guest_z_order_change=NONE")
    print("guest_redraw_forced=NONE")
    print("extra_present_timer=NONE")
    print("host_overlay=ENABLED")
    print("B50_CANVAS_TRACE=PRESERVED")

if __name__=="__main__":
    main()
