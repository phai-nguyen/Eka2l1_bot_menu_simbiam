#!/usr/bin/env python3
"""NATIVEBOOT2 B54 TRANSITIONCLEAR1.

Controlled functional experiment selected from B53 DEVICE1.

B53 proves that after the natural Splash -> Startup handoff:
- Startup is focus;
- visible regions are recalculated;
- exactly one full-screen Startup canvas is physically visible;
- canvas draw() returns true;
- server/client redraw pending are both zero;
- color_clear=0;
- iOS presents four new frames;
- Nokia pixels remain unchanged.

Inspection of the active B28 redraw_msg_canvas::draw() shows that draw() returns
true whenever the window is physically visible and non-zero-sized, even if
neither FLAG_SERVER_REDRAW_PENDING nor FLAG_CLIENT_REDRAW_PENDING is set. In
that state it can return true without emitting any pixel-writing command.

B54 therefore adds one narrowly-scoped color-buffer clear to the EXISTING
screen::redraw clear command on the first primary-screen transition into
Startup 0x100058F4 when SERVER_REDRAW_PENDING is absent.

This is a diagnostic experiment, not a permanent policy.

It does NOT:
- force a redraw;
- force a present;
- alter focus or z-order;
- alter visibility/activation;
- change scheduler timing;
- add an extra clear command.

Marker:
  [NBOOT2][TRANSITION_CLEAR]
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B54-TRANSITIONCLEAR1"

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
        fail("usage: apply_nativeboot2_b54_transitionclear1.py <upstream-root>")

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

    for marker,where in (
        ("[NBOOT2][COMPOSITOR_FRAME]",screen),
        ("[NBOOT2][COMPOSITOR_CANVAS]",screen),
        ("[NBOOT2][DIRECTSCREEN_REDRAW]",screen),
        ("[NBOOT2][DIRECTSCREEN_PRESENT]",state),
        ("[NBOOT2][REDRAW_SCHED]",sched),
    ):
        if marker not in where:
            fail("missing predecessor marker: "+marker)

    marker="[NBOOT2][TRANSITION_CLEAR]"
    if marker in screen:
        print(MARK+": already applied")
        return

    # Validate the B28 canvas behavior which makes B53 draw_result=1 ambiguous.
    draw_begin="    bool redraw_msg_canvas::draw(drivers::graphics_command_builder &builder) {"
    draw_end="\n    bool redraw_msg_canvas::execute_command"
    db=winuser.find(draw_begin)
    de=winuser.find(draw_end,db+1)
    if db<0 or de<0:
        fail("cannot isolate B28 redraw_msg_canvas::draw")
    draw_block=winuser[db:de]
    for gate in (
        "if (scr->flags_ & screen::FLAG_SERVER_REDRAW_PENDING)",
        "if (scr->flags_ & screen::FLAG_CLIENT_REDRAW_PENDING)",
        "return true;",
    ):
        if gate not in draw_block:
            fail("B28 canvas semantic gate missing: "+gate)

    begin="    bool screen::redraw(drivers::graphics_command_builder &builder, const bool need_bind) {"
    end="\n    void screen::redraw(drivers::graphics_driver *driver) {"

    old='''        static std::uint64_t b53_frame_seq = 0;
        const std::uint64_t b53_frame = b53_frame_seq++;
        const bool b53_visible_recalc_before = need_update_visible_regions();
        const std::string b53_focus_name =
            focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>");
        const bool b53_trace =
            (number == 0) &&
            ((b53_focus_name.find("100058f4") != std::string::npos) ||
             (b53_focus_name.find("102750f0") != std::string::npos) ||
             (b53_focus_name.find("Startup") != std::string::npos) ||
             (b53_focus_name.find("Home screen") != std::string::npos));

        if (need_update_visible_regions()) {
'''

    new='''        static std::uint64_t b53_frame_seq = 0;
        static bool b54_previous_startup_focus = false;
        const std::uint64_t b53_frame = b53_frame_seq++;
        const bool b53_visible_recalc_before = need_update_visible_regions();
        const std::string b53_focus_name =
            focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>");
        const bool b54_startup_focus =
            (number == 0) &&
            ((b53_focus_name.find("100058f4") != std::string::npos) ||
             (b53_focus_name.find("Startup") != std::string::npos));

        bool b54_transition_clear = false;
        if (number == 0) {
            b54_transition_clear =
                b54_startup_focus &&
                !b54_previous_startup_focus &&
                ((flags_ & FLAG_SERVER_REDRAW_PENDING) == 0);
            b54_previous_startup_focus = b54_startup_focus;
        }

        const bool b53_trace =
            (number == 0) &&
            (b54_startup_focus ||
             (b53_focus_name.find("102750f0") != std::string::npos) ||
             (b53_focus_name.find("Home screen") != std::string::npos));

        if (b54_transition_clear) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][TRANSITION_CLEAR] frame={} screen={} focus_id={} focus_handle=0x{:08X} focus_name={} flags=0x{:08X} visible_recalc_before={} server_redraw_pending=0 action=ADD_COLOR_BIT_TO_EXISTING_CLEAR scope=ONE_STARTUP_FOCUS_EDGE",
                b53_frame, number,
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                b53_focus_name,
                static_cast<std::uint32_t>(flags_),
                b53_visible_recalc_before ? 1 : 0);
        }

        if (need_update_visible_regions()) {
'''
    screen=rep_between(screen,begin,end,old,new,"B54 Startup edge")

    old='''            const bool b53_color_clear =
                (flags_ & FLAG_SERVER_REDRAW_PENDING) != 0;
'''
    new='''            const bool b53_color_clear =
                ((flags_ & FLAG_SERVER_REDRAW_PENDING) != 0) ||
                b54_transition_clear;
'''
    screen=rep_between(screen,begin,end,old,new,"B54 compositor clear report")

    old='''        builder.clear(eka2l1::vecx<float, 6>({ 0.0, 0.0, 0.0, 0.0, 1.0, 0.0 }), drivers::draw_buffer_bit_depth_buffer
            | drivers::draw_buffer_bit_stencil_buffer | ((flags_ & FLAG_SERVER_REDRAW_PENDING) ? drivers::draw_buffer_bit_color_buffer : 0));
'''
    new='''        builder.clear(eka2l1::vecx<float, 6>({ 0.0, 0.0, 0.0, 0.0, 1.0, 0.0 }), drivers::draw_buffer_bit_depth_buffer
            | drivers::draw_buffer_bit_stencil_buffer
            | (((flags_ & FLAG_SERVER_REDRAW_PENDING) || b54_transition_clear)
                ? drivers::draw_buffer_bit_color_buffer : 0));
'''
    screen=rep_between(screen,begin,end,old,new,"B54 existing clear color bit")

    rb=screen[screen.find(begin):screen.find(end,screen.find(begin)+1)]
    if rb.count("builder.clear(")!=1:
        fail("B54 must preserve exactly one compositor clear command")
    if rb.count(marker)!=1:
        fail("B54 marker count mismatch")
    if "flags_ |= FLAG_SERVER_REDRAW_PENDING" in rb:
        fail("B54 must not forge SERVER_REDRAW_PENDING")
    if "screen::redraw(" in rb.replace(begin,"",1):
        fail("B54 must not recursively force redraw")
    if "builder.present(" in rb:
        fail("B54 must not add present")

    screen_path.write_text(screen,encoding="utf-8")

    print(MARK+": applied")
    print("scope=CONTROLLED_FUNCTIONAL_EXPERIMENT")
    print("trigger=PRIMARY_SCREEN_STARTUP_FOCUS_EDGE")
    print("server_redraw_pending_required=0")
    print("extra_clear_command=NONE")
    print("existing_clear_color_bit=ONE_SHOT")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("focus_change=NONE")
    print("z_order_change=NONE")
    print("B53_COMPOSITOR_TRACE=PRESERVED")

if __name__=="__main__":
    main()
