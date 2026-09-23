#!/usr/bin/env python3
"""NATIVEBOOT2 B51 DIRECTSCREEN1.

Visual + log diagnostic selected from B50 device evidence.

B50 proves that Startup and Home screen create many canvases, some canvases
become visible and activate successfully, yet every observed activation/
SetVisible event reports physically_seen=0 while the splash group is still in
front. Later the splash group is demoted and destroyed with a visible-region
recalc pending, but the device video remains pixel-identical to the Nokia logo.

B51 therefore probes two layers without modifying guest WindowServer state:

1. WindowServer redraw execution:
   [NBOOT2][DIRECTSCREEN_REDRAW]
2. iOS host present path, with a tiny animated rectangle drawn directly on the
   host swapchain after the guest screen texture:
   [NBOOT2][DIRECTSCREEN_PRESENT]

The rectangle is intentionally outside guest composition. It moves among four
small slots and changes color according to the existing present count. It only
advances when EKA2L1 already submits a frame; B51 does NOT add a timer, force a
present, call screen::redraw(), change guest focus, or clear/modify the guest
screen texture.

Interpretation:
- moving host marker + stale Nokia pixels => host present is alive but the guest
  screen_texture/composition is stale;
- marker freezes after splash teardown and no present logs follow => redraw/
  present scheduling stopped;
- DIRECTSCREEN_REDRAW continues but performed=0 => redraw runs but no drawable
  guest content is emitted;
- DIRECTSCREEN_REDRAW performed=1 + moving marker + stale Nokia => compositor
  commands run, but the guest screen texture still preserves stale splash pixels.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B51-DIRECTSCREEN1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_between(text, begin, end, old, new, label):
    b=text.find(begin)
    e=text.find(end,b+1)
    if b<0 or e<0:
        fail(f"{label}: bounds not found")
    region=text[b:e]
    n=region.count(old)
    if n!=1:
        fail(f"{label}: expected one bounded anchor, found {n}")
    region=region.replace(old,new,1)
    return text[:b]+region+text[e:]

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b51_directscreen1.py <upstream-root>")

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

    # Preserve the B50 device-classification instrumentation.
    for marker,where in (
        ("[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]",winuser),
        ("[NBOOT2][POSTLOGO_CANVAS_VISIBLE]",winuser),
        ("[NBOOT2][POSTLOGO_WG_DESTROY]",wingroup),
        ("[NBOOT2][POSTLOGO_FOCUS]",screen),
    ):
        if marker not in where:
            fail("missing predecessor marker: "+marker)

    present_marker="[NBOOT2][DIRECTSCREEN_PRESENT]"
    redraw_marker="[NBOOT2][DIRECTSCREEN_REDRAW]"
    if present_marker in ios or redraw_marker in screen:
        if present_marker in ios and redraw_marker in screen:
            print(MARK+": already applied")
            return
        fail("partial B51 patch detected")

    # ------------------------------------------------------------------
    # 1) Host-direct marker in submit_screen_frame.
    #    The guest screen texture is drawn first. Then B51 draws a tiny marker
    #    directly to swapchain bitmap 0. No guest texture/framebuffer mutation.
    # ------------------------------------------------------------------
    submit_begin="    static void submit_screen_frame(emulator *state, eka2l1::epoc::screen *scr) {"
    submit_end="\n    // Re-present the primary screen's current texture"
    draw_anchor='''        builder.draw_bitmap(scr->screen_texture, 0, dest, src, eka2l1::vec2(0, 0),
            static_cast<float>(rotation), flags);

        builder.load_backup_state();
'''
    draw_block='''        builder.draw_bitmap(scr->screen_texture, 0, dest, src, eka2l1::vec2(0, 0),
            static_cast<float>(rotation), flags);

        // NATIVEBOOT2 B51 DIRECTSCREEN1:
        // Host-only moving marker. This is deliberately drawn after the guest
        // screen texture while bitmap 0 (the iOS swapchain) is bound.
        // It does not touch scr->screen_texture and does not request a frame.
        const std::uint64_t b51_frame =
            state->rendered_frame_count.load(std::memory_order_relaxed);
        if (state->conf.native_phone_boot) {
            static const char b51_present_marker[] = "[NBOOT2][DIRECTSCREEN_PRESENT]";
            const int b51_phase = static_cast<int>(b51_frame & 3ULL);
            const int b51_box = common::max(8, common::min(18,
                common::min(external_crop.size.x, external_crop.size.y) / 20));
            eka2l1::rect b51_marker;
            b51_marker.size = eka2l1::vec2(b51_box, b51_box);
            b51_marker.top = external_crop.top + eka2l1::vec2(
                6 + b51_phase * (b51_box + 3), 6);

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

            LOG_WARN(eka2l1::FRONTEND_CMDLINE,
                "{} frame={} phase={} slot={} screen_texture=0x{:08X} screen_flags=0x{:08X} crop=[{},{},{},{}] marker=[{},{},{},{}] behavior=HOST_OVERLAY_ONLY",
                b51_present_marker, b51_frame, b51_phase, slot,
                static_cast<std::uint32_t>(scr->screen_texture),
                static_cast<std::uint32_t>(scr->flags_),
                external_crop.top.x, external_crop.top.y,
                external_crop.size.x, external_crop.size.y,
                b51_marker.top.x, b51_marker.top.y,
                b51_marker.size.x, b51_marker.size.y);
        }

        builder.load_backup_state();
'''
    ios=rep_between(ios,submit_begin,submit_end,draw_anchor,draw_block,
                    "B51 host direct marker")

    # ------------------------------------------------------------------
    # 2) Observe the guest WindowServer compositor itself.
    # ------------------------------------------------------------------
    redraw_begin="    void screen::redraw(drivers::graphics_driver *driver) {"
    redraw_end="\n    void screen::deinit(drivers::graphics_driver *driver) {"

    entry_anchor='''    void screen::redraw(drivers::graphics_driver *driver) {
        if (!screen_texture) {
'''
    entry_block='''    void screen::redraw(drivers::graphics_driver *driver) {
        static const char b51_redraw_marker[] = "[NBOOT2][DIRECTSCREEN_REDRAW]";
        const std::uint32_t b51_flags_before = flags_;
        const bool b51_visible_recalc_before = need_update_visible_regions();
        const int b51_focus_id = focus ? focus->id : 0;
        const std::uint32_t b51_focus_handle = focus ? focus->client_handle : 0;
        const std::string b51_focus_name =
            focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>");
        LOG_WARN(SERVICE_WINDOW,
            "{} phase=enter screen={} texture=0x{:08X} flags=0x{:08X} visible_recalc={} focus_id={} focus_handle=0x{:08X} focus_name={} behavior=OBSERVE_ONLY",
            b51_redraw_marker, number, static_cast<std::uint32_t>(screen_texture),
            b51_flags_before, b51_visible_recalc_before ? 1 : 0,
            b51_focus_id, b51_focus_handle, b51_focus_name);

        if (!screen_texture) {
'''
    screen=rep_between(screen,redraw_begin,redraw_end,entry_anchor,entry_block,
                       "B51 redraw entry")

    exit_anchor='''        if (performed && sync_screen_buffer && (display_scale_factor == 1.0f)) {
            sync_screen_buffer_data(driver);
        }

        fire_screen_redraw_callbacks(false);
    }
'''
    exit_block='''        if (performed && sync_screen_buffer && (display_scale_factor == 1.0f)) {
            sync_screen_buffer_data(driver);
        }

        LOG_WARN(SERVICE_WINDOW,
            "{} phase=result screen={} performed={} flags_before=0x{:08X} flags_after=0x{:08X} visible_recalc_after={} focus_id={} focus_handle=0x{:08X} focus_name={} callback_next=1 behavior=OBSERVE_ONLY",
            b51_redraw_marker, number, performed ? 1 : 0,
            b51_flags_before, static_cast<std::uint32_t>(flags_),
            need_update_visible_regions() ? 1 : 0,
            focus ? focus->id : 0,
            focus ? focus->client_handle : 0,
            focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>"));

        fire_screen_redraw_callbacks(false);
    }
'''
    screen=rep_between(screen,redraw_begin,redraw_end,exit_anchor,exit_block,
                       "B51 redraw result")

    # Postconditions.
    if ios.count(present_marker)!=1:
        fail(f"expected one DIRECTSCREEN_PRESENT source marker, got {ios.count(present_marker)}")
    if screen.count(redraw_marker)!=1:
        fail(f"expected one retained DIRECTSCREEN_REDRAW source marker, got {screen.count(redraw_marker)}")
    if "submit_screen_frame(state, scr);" not in ios:
        fail("screen callback present path lost")
    if "scr->redraw(" in ios[ios.find(submit_begin):ios.find(submit_end,ios.find(submit_begin))]:
        fail("B51 submit_screen_frame must not force guest redraw")

    ios_path.write_text(ios,encoding="utf-8")
    screen_path.write_text(screen,encoding="utf-8")

    print(MARK+": applied")
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
