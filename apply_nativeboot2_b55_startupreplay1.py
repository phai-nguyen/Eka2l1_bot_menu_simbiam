#!/usr/bin/env python3
"""NATIVEBOOT2 B55 STARTUPREPLAY1.

Controlled functional experiment selected from B54 DEVICE1.

B54 proves the retained Nokia image is old color-buffer content:
- the one-shot Startup transition clear fires exactly once;
- color_clear=1 on the first Startup compositor frame;
- the device video changes from Nokia white/logo to black at the same moment;
- subsequent Startup frames remain black.

The active B28 redraw_msg_canvas::draw() only replays stored redraw segments
when FLAG_SERVER_REDRAW_PENDING is set. B53/B54 showed that after the natural
Splash -> Startup handoff, Startup is physically visible but both server and
client redraw pending are zero. In that state draw() returns true without
necessarily emitting any pixel-writing commands.

B55 therefore sets FLAG_SERVER_REDRAW_PENDING for exactly the same first
Startup-focus edge already proven by B54. This causes the existing compositor
path to:
- clear the old screen through its normal server-redraw path;
- replay stored redraw segments for physically visible canvases.

No new redraw, present, focus, z-order, visibility or activation is forced.

Markers:
  [NBOOT2][STARTUP_REPLAY]
  [NBOOT2][STARTUP_REPLAY_CANVAS]
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B55-STARTUPREPLAY1"

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
        fail("usage: apply_nativeboot2_b55_startupreplay1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    winuser_path=up/"src/emu/services/src/window/classes/winuser.cpp"
    state_path=up/"src/emu/ios/src/state.cpp"
    sched_path=up/"src/emu/services/src/window/scheduler.cpp"

    for p in (screen_path,winuser_path,state_path,sched_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    screen=screen_path.read_text(encoding="utf-8")
    winuser=winuser_path.read_text(encoding="utf-8")
    state=state_path.read_text(encoding="utf-8")
    sched=sched_path.read_text(encoding="utf-8")

    for marker,where in (
        ("[NBOOT2][TRANSITION_CLEAR]",screen),
        ("[NBOOT2][COMPOSITOR_FRAME]",screen),
        ("[NBOOT2][DIRECTSCREEN_PRESENT]",state),
        ("[NBOOT2][REDRAW_SCHED]",sched),
    ):
        if marker not in where:
            fail("missing predecessor marker: "+marker)

    screen_marker="[NBOOT2][STARTUP_REPLAY]"
    canvas_marker="[NBOOT2][STARTUP_REPLAY_CANVAS]"
    if screen_marker in screen or canvas_marker in winuser:
        if screen_marker in screen and canvas_marker in winuser:
            print(MARK+": already applied")
            return
        fail("partial B55 patch detected")

    # ------------------------------------------------------------------
    # 1) On the exact one-shot edge already selected by B54, set the native
    #    server-redraw-pending bit. No extra redraw is scheduled.
    # ------------------------------------------------------------------
    begin="    bool screen::redraw(drivers::graphics_command_builder &builder, const bool need_bind) {"
    end="\n    void screen::redraw(drivers::graphics_driver *driver) {"

    old='''        if (b54_transition_clear) {
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

    new='''        if (b54_transition_clear) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][TRANSITION_CLEAR] frame={} screen={} focus_id={} focus_handle=0x{:08X} focus_name={} flags=0x{:08X} visible_recalc_before={} server_redraw_pending=0 action=ADD_COLOR_BIT_TO_EXISTING_CLEAR scope=ONE_STARTUP_FOCUS_EDGE",
                b53_frame, number,
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                b53_focus_name,
                static_cast<std::uint32_t>(flags_),
                b53_visible_recalc_before ? 1 : 0);

            const std::uint32_t b55_flags_before = flags_;
            flags_ |= FLAG_SERVER_REDRAW_PENDING;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_REPLAY] frame={} screen={} focus_id={} focus_handle=0x{:08X} focus_name={} flags_before=0x{:08X} flags_after=0x{:08X} action=SET_SERVER_REDRAW_PENDING scope=ONE_STARTUP_FOCUS_EDGE behavior=CONTROLLED_EXPERIMENT",
                b53_frame, number,
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                b53_focus_name,
                b55_flags_before,
                static_cast<std::uint32_t>(flags_));
        }

        if (need_update_visible_regions()) {
'''
    screen=rep_between(screen,begin,end,old,new,"B55 Startup replay edge")

    # B54's explicit clear override remains harmless; once B55 sets the normal
    # pending flag the same existing clear command is selected naturally.
    rb=screen[screen.find(begin):screen.find(end,screen.find(begin)+1)]
    if rb.count("flags_ |= FLAG_SERVER_REDRAW_PENDING;")!=1:
        fail("B55 must set SERVER_REDRAW_PENDING exactly once")
    if rb.count("builder.clear(")!=1:
        fail("B55 must not add another clear command")
    if "builder.present(" in rb:
        fail("B55 must not add present")
    if "set_position(" in rb or "set_receive_focus(" in rb:
        fail("B55 must not alter order/focus")

    # ------------------------------------------------------------------
    # 2) Log the exact stored redraw-segment count used by the visible Startup
    #    canvas when the server replay branch runs.
    # ------------------------------------------------------------------
    begin="    bool redraw_msg_canvas::draw(drivers::graphics_command_builder &builder) {"
    end="\n    bool redraw_msg_canvas::execute_command"

    old='''        if (scr->flags_ & screen::FLAG_SERVER_REDRAW_PENDING) {
            auto &segments = redraw_segments_.get_segments();

            if (!segments.empty()) {
'''

    new='''        if (scr->flags_ & screen::FLAG_SERVER_REDRAW_PENDING) {
            auto &segments = redraw_segments_.get_segments();

            epoc::window_group *b55_group = get_group();
            const std::string b55_group_name =
                b55_group ? common::ucs2_to_utf8(b55_group->name) : std::string("<null>");
            const bool b55_startup =
                (b55_group_name.find("100058f4") != std::string::npos) ||
                (b55_group_name.find("Startup") != std::string::npos);
            if (b55_startup && can_be_physically_seen()) {
                std::size_t b55_drawable_segments = 0;
                for (std::size_t b55_i = 0; b55_i < segments.size(); b55_i++) {
                    if (segments[b55_i]->type_ != gdi_store_command_segment_pending_redraw) {
                        b55_drawable_segments++;
                    }
                }

                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][STARTUP_REPLAY_CANVAS] group_id={} group_handle=0x{:08X} group_name={} canvas_handle=0x{:08X} abs=[{},{},{},{}] visible_region_empty={} segments={} drawable_segments={} background_region_empty={} clear_color_enable={} action=SERVER_SEGMENT_REPLAY behavior=CONTROLLED_EXPERIMENT",
                    b55_group ? b55_group->id : 0,
                    b55_group ? b55_group->client_handle : 0,
                    b55_group_name,
                    client_handle,
                    abs_rect.top.x, abs_rect.top.y,
                    abs_rect.size.x, abs_rect.size.y,
                    visible_region.empty() ? 1 : 0,
                    segments.size(),
                    b55_drawable_segments,
                    background_region.empty() ? 1 : 0,
                    clear_color_enable ? 1 : 0);
            }

            if (!segments.empty()) {
'''
    winuser=rep_between(winuser,begin,end,old,new,"B55 Startup segment trace")

    db=winuser[winuser.find(begin):winuser.find(end,winuser.find(begin)+1)]
    if db.count("gdi_builder.build_segment(*segments[i]);")!=1:
        fail("B55 must preserve original stored segment replay call")
    if db.count(canvas_marker)!=1:
        fail("B55 canvas marker mismatch")

    screen_path.write_text(screen,encoding="utf-8")
    winuser_path.write_text(winuser,encoding="utf-8")

    print(MARK+": applied")
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
