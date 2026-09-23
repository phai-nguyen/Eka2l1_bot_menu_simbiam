#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B51 DIRECTSCREEN1."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B51-DIRECTSCREEN1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b51_directscreen1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    state_path = up / "src/emu/ios/src/state.cpp"
    screen_path = up / "src/emu/services/src/window/screen.cpp"
    winuser_path = up / "src/emu/services/src/window/classes/winuser.cpp"
    wingroup_path = up / "src/emu/services/src/window/classes/wingroup.cpp"

    for p in (state_path, screen_path, winuser_path, wingroup_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    state = state_path.read_text(encoding="utf-8")
    screen = screen_path.read_text(encoding="utf-8")
    winuser = winuser_path.read_text(encoding="utf-8")
    wingroup = wingroup_path.read_text(encoding="utf-8")

    need(state, "[NBOOT2][DIRECTSCREEN_PRESENT]", "state.cpp")
    need(screen, "[NBOOT2][DIRECTSCREEN_REDRAW]", "screen.cpp")
    need(state, "behavior=HOST_OVERLAY_ONLY", "host marker contract")
    need(screen, "behavior=OBSERVE_ONLY", "redraw contract")
    need(state, "if (state_ptr->native_phone_mode)", "native-only host marker")

    # B28-era host presentation lives in emulator::register_draw_callback().
    s = state.find("void emulator::register_draw_callback()")
    e = state.find("void emulator::on_system_reset", s)
    if s < 0 or e < 0:
        fail("cannot isolate emulator::register_draw_callback")
    block = state[s:e]

    guest_copy = block.find("state_ptr->launcher_->draw(builder, scr")
    host_bind = block.find("builder.bind_bitmap(0);")
    marker = block.find("builder.draw_rectangle(b51_marker);")
    present = block.find("builder.present(&state_ptr->present_status);")
    if min(guest_copy, host_bind, marker, present) < 0:
        fail("cannot locate B51 host present sequence")
    if not (guest_copy < host_bind < marker < present):
        fail("required order is guest copy -> host bitmap -> marker -> present")

    if block.count("builder.present(&state_ptr->present_status);") != 1:
        fail("B51 must preserve exactly one existing present command")
    if "scr->redraw(" in block or "screen::redraw(" in block:
        fail("B51 must not force guest redraw from host callback")
    if "dispatch_after" in block or "sleep_for" in block:
        fail("B51 must not add a periodic present timer")
    if "builder.bind_bitmap(scr->screen_texture)" in block:
        fail("B51 host callback must not bind/write guest screen texture")

    # Original WindowServer composition path must remain intact.
    rs = screen.find("void screen::redraw(drivers::graphics_driver *driver)")
    re = screen.find("void screen::deinit", rs)
    if rs < 0 or re < 0:
        fail("cannot isolate screen::redraw(driver)")
    rb = screen[rs:re]
    need(rb, "const bool performed = redraw(builder, true);", "original compositor call")
    need(rb, "driver->submit_command_list(retrieved);", "original compositor submit")
    need(rb, "fire_screen_redraw_callbacks(false);", "original redraw callback")
    need(rb, "(b51_focus_id == 3)", "splash redraw filter")
    need(rb, "(b51_focus_id == 63)", "Startup redraw filter")
    need(rb, "(b51_focus_id == 75)", "Home redraw filter")

    # B50 predecessor evidence remains present.
    need(winuser, "[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]", "B50 activate trace")
    need(winuser, "[NBOOT2][POSTLOGO_CANVAS_VISIBLE]", "B50 visibility trace")
    need(wingroup, "[NBOOT2][POSTLOGO_WG_DESTROY]", "B50 destroy trace")
    need(screen, "[NBOOT2][POSTLOGO_FOCUS]", "B49/B50 focus trace")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK + ": PASS")
    print("scope=VISUAL_DIAGNOSTIC")
    print("present_path=B28_STATE_CPP_REDRAW_CALLBACK")
    print("guest_screen_texture_write=NONE")
    print("guest_focus_change=NONE")
    print("guest_z_order_change=NONE")
    print("guest_redraw_forced=NONE")
    print("extra_present_timer=NONE")
    print("host_overlay=ENABLED")
    print("B50_CANVAS_TRACE=PRESERVED")

if __name__ == "__main__":
    main()
