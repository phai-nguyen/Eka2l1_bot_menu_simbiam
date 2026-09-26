#!/usr/bin/env python3
"""NATIVEBOOT2 B51 DIRECTSCREEN1.

Selected from B50 device evidence.

B50 proves that Startup/Home WindowServer groups and canvases are created and
activated, splash demotes and is destroyed, focus moves to Startup, and a
visible-region recalculation is pending — yet the device video keeps displaying
the same Nokia splash pixels.

B51 probes the first unresolved boundary without changing guest focus, z-order
or window state:

1. [NBOOT2][DIRECTSCREEN_REDRAW]
   Observes screen::redraw(driver) while focus is one of the boot actors
   (splash=3, Startup=63, Home=75), including whether redraw emitted drawable
   content and whether visible-region recomputation was pending.

2. [NBOOT2][DIRECTSCREEN_PRESENT]
   Adds a tiny four-phase host-only marker to the existing iOS redraw callback,
   after launcher::draw has copied scr->screen_texture to the host surface and
   before the already-existing present command.

The marker is drawn only in transient native_phone_mode. It does not touch the
guest screen texture and does not add a timer, force a redraw, or force a
present. It advances only when the existing WindowServer redraw callback fires.

Interpretation:
- moving marker + stale Nokia pixels => host present path is alive, guest
  screen_texture/composition is stale;
- no marker/present activity after splash teardown => redraw->present scheduling
  stopped;
- DIRECTSCREEN_REDRAW performed=0 => redraw runs but emits no drawable guest
  content;
- performed=1 + moving marker + stale Nokia => inspect compositor/tree output or
  stale guest texture content next.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B51-DIRECTSCREEN1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def replace_bounded(text: str, begin: str, end: str, old: str, new: str, label: str) -> str:
    b = text.find(begin)
    e = text.find(end, b + 1)
    if b < 0 or e < 0:
        fail(f"{label}: bounds not found")
    region = text[b:e]
    count = region.count(old)
    if count != 1:
        fail(f"{label}: expected one bounded anchor, found {count}")
    region = region.replace(old, new, 1)
    return text[:b] + region + text[e:]

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b51_directscreen1.py <upstream-root>")

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

    for marker, where in (
        ("[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]", winuser),
        ("[NBOOT2][POSTLOGO_CANVAS_VISIBLE]", winuser),
        ("[NBOOT2][POSTLOGO_WG_DESTROY]", wingroup),
        ("[NBOOT2][POSTLOGO_FOCUS]", screen),
        ("[NBOOT2][ESTART_RUN]", state),
    ):
        if marker not in where:
            fail("missing predecessor marker: " + marker)

    present_marker = "[NBOOT2][DIRECTSCREEN_PRESENT]"
    redraw_marker = "[NBOOT2][DIRECTSCREEN_REDRAW]"
    if present_marker in state or redraw_marker in screen:
        if present_marker in state and redraw_marker in screen:
            print(MARK + ": already applied")
            return
        fail("partial B51 patch detected")

    # ------------------------------------------------------------------
    # 1) iOS host present probe.
    #
    # The B28-era iOS frontend presents in emulator::register_draw_callback():
    # WindowServer redraw -> callback -> launcher_->draw(screen_texture) ->
    # builder.present().
    #
    # B51 inserts a tiny host-only marker between launcher_->draw and present.
    # ------------------------------------------------------------------
    callback_begin = "    void emulator::register_draw_callback() {"
    callback_end = "\n    void emulator::on_system_reset(system *the_sys) {"

    host_anchor = '''                    state_ptr->launcher_->draw(builder, scr, state_ptr->window->window_fb_size().x,
                        state_ptr->window->window_fb_size().y);

                    state_ptr->present_status = -100;
                    builder.present(&state_ptr->present_status);
'''

    host_block = '''                    state_ptr->launcher_->draw(builder, scr, state_ptr->window->window_fb_size().x,
                        state_ptr->window->window_fb_size().y);

                    // NATIVEBOOT2-B51 DIRECTSCREEN1:
                    // Draw only on host bitmap 0 after the guest screen texture
                    // has already been copied by launcher_->draw(). This does
                    // not mutate scr->screen_texture and does not request any
                    // extra redraw/present.
                    if (state_ptr->native_phone_mode) {
                        static std::uint64_t b51_present_frame = 0;
                        const std::uint64_t b51_frame = b51_present_frame++;
                        const int b51_phase = static_cast<int>(b51_frame & 3ULL);
                        const eka2l1::vec2 b51_fb = state_ptr->window->window_fb_size();

                        builder.bind_bitmap(0);
                        builder.set_feature(drivers::graphics_feature::cull, false);
                        builder.set_feature(drivers::graphics_feature::depth_test, false);
                        builder.set_feature(drivers::graphics_feature::blend, false);
                        builder.set_feature(drivers::graphics_feature::clipping, false);

                        eka2l1::rect b51_viewport;
                        b51_viewport.size = b51_fb;
                        builder.set_viewport(b51_viewport);

                        eka2l1::rect b51_marker;
                        b51_marker.top = eka2l1::vec2(6 + b51_phase * 19, 6);
                        b51_marker.size = eka2l1::vec2(15, 15);

                        switch (b51_phase) {
                        case 0:
                            builder.set_brush_color_detail(eka2l1::vec4(255, 0, 255, 255));
                            break;
                        case 1:
                            builder.set_brush_color_detail(eka2l1::vec4(0, 255, 255, 255));
                            break;
                        case 2:
                            builder.set_brush_color_detail(eka2l1::vec4(255, 255, 0, 255));
                            break;
                        default:
                            builder.set_brush_color_detail(eka2l1::vec4(0, 255, 0, 255));
                            break;
                        }
                        builder.draw_rectangle(b51_marker);

                        LOG_WARN(FRONTEND_CMDLINE,
                            "[NBOOT2][DIRECTSCREEN_PRESENT] frame={} phase={} fb={}x{} screen_texture=0x{:08X} screen_flags=0x{:08X} marker=[{},{},{},{}] behavior=HOST_OVERLAY_ONLY",
                            b51_frame, b51_phase, b51_fb.x, b51_fb.y,
                            static_cast<std::uint32_t>(scr->screen_texture),
                            static_cast<std::uint32_t>(scr->flags_),
                            b51_marker.top.x, b51_marker.top.y,
                            b51_marker.size.x, b51_marker.size.y);
                    }

                    state_ptr->present_status = -100;
                    builder.present(&state_ptr->present_status);
'''

    state = replace_bounded(
        state, callback_begin, callback_end, host_anchor, host_block,
        "B51 host callback marker")

    # ------------------------------------------------------------------
    # 2) WindowServer compositor probe.
    # ------------------------------------------------------------------
    redraw_begin = "    void screen::redraw(drivers::graphics_driver *driver) {"
    redraw_end = "\n    void screen::deinit(drivers::graphics_driver *driver) {"

    entry_anchor = '''    void screen::redraw(drivers::graphics_driver *driver) {
        if (!screen_texture) {
'''

    entry_block = '''    void screen::redraw(drivers::graphics_driver *driver) {
        const std::uint32_t b51_flags_before = flags_;
        const bool b51_visible_recalc_before = need_update_visible_regions();
        const int b51_focus_id = focus ? focus->id : 0;
        const bool b51_track =
            (number == 0) &&
            ((b51_focus_id == 3) || (b51_focus_id == 63) || (b51_focus_id == 75));

        if (b51_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][DIRECTSCREEN_REDRAW] phase=enter screen={} texture=0x{:08X} flags=0x{:08X} visible_recalc={} focus_id={} focus_handle=0x{:08X} focus_name={} behavior=OBSERVE_ONLY",
                number, static_cast<std::uint32_t>(screen_texture),
                b51_flags_before, b51_visible_recalc_before ? 1 : 0,
                b51_focus_id, focus ? focus->client_handle : 0,
                focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>"));
        }

        if (!screen_texture) {
'''

    screen = replace_bounded(
        screen, redraw_begin, redraw_end, entry_anchor, entry_block,
        "B51 redraw entry")

    exit_anchor = '''        if (performed && sync_screen_buffer && (display_scale_factor == 1.0f)) {
            sync_screen_buffer_data(driver);
        }

        fire_screen_redraw_callbacks(false);
    }
'''

    exit_block = '''        if (performed && sync_screen_buffer && (display_scale_factor == 1.0f)) {
            sync_screen_buffer_data(driver);
        }

        if (b51_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][DIRECTSCREEN_REDRAW] phase=result screen={} performed={} flags_before=0x{:08X} flags_after=0x{:08X} visible_recalc_before={} visible_recalc_after={} focus_id={} focus_handle=0x{:08X} focus_name={} callback_next=1 behavior=OBSERVE_ONLY",
                number, performed ? 1 : 0, b51_flags_before,
                static_cast<std::uint32_t>(flags_),
                b51_visible_recalc_before ? 1 : 0,
                need_update_visible_regions() ? 1 : 0,
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>"));
        }

        fire_screen_redraw_callbacks(false);
    }
'''

    screen = replace_bounded(
        screen, redraw_begin, redraw_end, exit_anchor, exit_block,
        "B51 redraw result")

    # Postconditions.
    if state.count(present_marker) != 1:
        fail(f"expected one DIRECTSCREEN_PRESENT source marker, got {state.count(present_marker)}")
    if screen.count(redraw_marker) != 2:
        fail(f"expected two DIRECTSCREEN_REDRAW log sites, got {screen.count(redraw_marker)}")

    cb_start = state.find(callback_begin)
    cb_end = state.find(callback_end, cb_start)
    callback = state[cb_start:cb_end]
    for gate in (
        "state_ptr->launcher_->draw(builder, scr",
        "builder.bind_bitmap(0);",
        "builder.draw_rectangle(b51_marker);",
        "builder.present(&state_ptr->present_status);",
    ):
        if gate not in callback:
            fail("host callback gate missing: " + gate)

    if callback.find("builder.draw_rectangle(b51_marker);") > callback.find("builder.present(&state_ptr->present_status);"):
        fail("host marker must be emitted before existing present")
    if "scr->redraw(" in callback or "screen::redraw(" in callback:
        fail("B51 must not force guest redraw from iOS callback")

    state_path.write_text(state, encoding="utf-8")
    screen_path.write_text(screen, encoding="utf-8")

    print(MARK + ": applied")
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
