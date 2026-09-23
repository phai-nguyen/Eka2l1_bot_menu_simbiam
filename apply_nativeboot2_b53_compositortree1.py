#!/usr/bin/env python3
"""NATIVEBOOT2 B53 COMPOSITORTREE1.

Diagnostic-only follow-up to B52 DEVICE1.

B52 proves that the natural splash demotion reaches the iOS host present path:
four new presents occur during the Splash -> Startup handoff, yet the Nokia
pixels remain unchanged. The unresolved boundary is therefore the guest
WindowServer compositor output itself.

B53 observes:
- primary-screen compositor frame flags / color-clear decision;
- top-level WindowGroup order using names rather than unstable object IDs;
- every client canvas that is visible, physically visible, or emits draw()
  commands during Startup/Home-focused redraws;
- total client/visible/physically-visible/drawn canvas counts.

B53 does NOT clear the color buffer, force redraw, force focus, change z-order,
or modify any guest-visible WindowServer result.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B53-COMPOSITORTREE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

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
        fail("usage: apply_nativeboot2_b53_compositortree1.py <upstream-root>")

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

    for marker,where in (
        ("[NBOOT2][DIRECTSCREEN_REDRAW]",screen),
        ("[NBOOT2][POSTLOGO_FOCUS]",screen),
        ("[NBOOT2][DIRECTSCREEN_PRESENT]",state),
        ("[NBOOT2][REDRAW_SCHED]",sched),
    ):
        if marker not in where:
            fail("missing predecessor marker: "+marker)

    frame_marker="[NBOOT2][COMPOSITOR_FRAME]"
    group_marker="[NBOOT2][COMPOSITOR_GROUP]"
    canvas_marker="[NBOOT2][COMPOSITOR_CANVAS]"
    if any(m in screen for m in (frame_marker,group_marker,canvas_marker)):
        if all(m in screen for m in (frame_marker,group_marker,canvas_marker)):
            print(MARK+": already applied")
            return
        fail("partial B53 patch detected")

    # --------------------------------------------------------------
    # 1) Extend the existing window_drawer_walker with diagnostic
    # counters and per-canvas tracing. draw() is still called once.
    # --------------------------------------------------------------
    begin="    struct window_drawer_walker : public window_tree_walker {"
    end="\n    struct window_dsa_abort_walker"

    old='''    struct window_drawer_walker : public window_tree_walker {
        drivers::graphics_command_builder &builder_;
        std::uint32_t total_redrawed_;

        explicit window_drawer_walker(drivers::graphics_command_builder &builder)
            : builder_(builder)
            , total_redrawed_(0) {
        }

        bool do_it(window *win) {
            if (win->type != window_kind::client) {
                return false;
            }

            epoc::canvas_base *cv = reinterpret_cast<epoc::canvas_base*>(win);

            if (cv->draw(builder_))
                total_redrawed_++;

            return false;
        }
    };
'''

    new='''    struct window_drawer_walker : public window_tree_walker {
        drivers::graphics_command_builder &builder_;
        std::uint32_t total_redrawed_;
        std::uint32_t total_clients_;
        std::uint32_t total_visible_;
        std::uint32_t total_physically_seen_;
        bool trace_;
        std::uint64_t frame_id_;

        explicit window_drawer_walker(drivers::graphics_command_builder &builder,
            const bool trace = false, const std::uint64_t frame_id = 0)
            : builder_(builder)
            , total_redrawed_(0)
            , total_clients_(0)
            , total_visible_(0)
            , total_physically_seen_(0)
            , trace_(trace)
            , frame_id_(frame_id) {
        }

        bool do_it(window *win) {
            if (win->type != window_kind::client) {
                return false;
            }

            epoc::canvas_base *cv = reinterpret_cast<epoc::canvas_base*>(win);
            epoc::window_group *group = cv->get_group();

            const bool visible = cv->is_visible();
            const bool physically_seen = cv->can_be_physically_seen();
            total_clients_++;
            if (visible) {
                total_visible_++;
            }
            if (physically_seen) {
                total_physically_seen_++;
            }

            const bool drawn = cv->draw(builder_);
            if (drawn) {
                total_redrawed_++;
            }

            if (trace_ && (visible || physically_seen || drawn)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][COMPOSITOR_CANVAS] frame={} group_id={} group_handle=0x{:08X} group_name={} group_priority={} canvas_handle=0x{:08X} canvas_priority={} flags=0x{:08X} win_type={} abs=[{},{},{},{}] visible={} visible_region_empty={} physically_seen={} draw_result={} behavior=OBSERVE_ONLY",
                    frame_id_,
                    group ? group->id : 0,
                    group ? group->client_handle : 0,
                    group ? common::ucs2_to_utf8(group->name) : std::string("<null>"),
                    group ? group->priority : 0,
                    cv->client_handle, cv->priority,
                    static_cast<std::uint32_t>(cv->flags),
                    static_cast<int>(cv->win_type),
                    cv->abs_rect.top.x, cv->abs_rect.top.y,
                    cv->abs_rect.size.x, cv->abs_rect.size.y,
                    visible ? 1 : 0,
                    cv->visible_region.empty() ? 1 : 0,
                    physically_seen ? 1 : 0,
                    drawn ? 1 : 0);
            }

            return false;
        }
    };
'''

    screen=rep_between(screen,begin,end,old,new,"B53 drawer walker")

    # --------------------------------------------------------------
    # 2) Frame-level trace in the builder redraw path.
    # Use group names/UIDs rather than run-specific object IDs.
    # --------------------------------------------------------------
    begin="    bool screen::redraw(drivers::graphics_command_builder &builder, const bool need_bind) {"
    end="\n    void screen::redraw(drivers::graphics_driver *driver) {"

    old='''    bool screen::redraw(drivers::graphics_command_builder &builder, const bool need_bind) {
        if (need_update_visible_regions()) {
            recalculate_visible_regions();
        }

        if (need_bind) {
'''

    new='''    bool screen::redraw(drivers::graphics_command_builder &builder, const bool need_bind) {
        static std::uint64_t b53_frame_seq = 0;
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
            recalculate_visible_regions();
        }

        if (b53_trace) {
            const bool b53_color_clear =
                (flags_ & FLAG_SERVER_REDRAW_PENDING) != 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][COMPOSITOR_FRAME] phase=begin frame={} screen={} focus_id={} focus_handle=0x{:08X} focus_name={} flags=0x{:08X} visible_recalc_before={} visible_recalc_after={} server_redraw_pending={} client_redraw_pending={} color_clear={} need_bind={} behavior=OBSERVE_ONLY",
                b53_frame, number,
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                b53_focus_name,
                static_cast<std::uint32_t>(flags_),
                b53_visible_recalc_before ? 1 : 0,
                need_update_visible_regions() ? 1 : 0,
                (flags_ & FLAG_SERVER_REDRAW_PENDING) ? 1 : 0,
                (flags_ & FLAG_CLIENT_REDRAW_PENDING) ? 1 : 0,
                b53_color_clear ? 1 : 0,
                need_bind ? 1 : 0);

            epoc::window *b53_node = root ? root->child : nullptr;
            int b53_group_index = 0;
            while (b53_node) {
                if (b53_node->type == window_kind::group) {
                    epoc::window_group *b53_group =
                        reinterpret_cast<epoc::window_group *>(b53_node);
                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][COMPOSITOR_GROUP] frame={} index={} group_id={} client_handle=0x{:08X} priority={} ordinal={} flags=0x{:08X} focusable={} is_focus={} name={} has_child={} behavior=OBSERVE_ONLY",
                        b53_frame, b53_group_index,
                        b53_group->id, b53_group->client_handle,
                        b53_group->priority,
                        b53_group->ordinal_position(true),
                        static_cast<std::uint32_t>(b53_group->flags),
                        b53_group->can_receive_focus() ? 1 : 0,
                        (b53_group == focus) ? 1 : 0,
                        common::ucs2_to_utf8(b53_group->name),
                        b53_group->child ? 1 : 0);
                    b53_group_index++;
                }
                b53_node = b53_node->sibling;
            }
        }

        if (need_bind) {
'''
    screen=rep_between(screen,begin,end,old,new,"B53 frame begin")

    old='''        window_drawer_walker adrawwalker(builder);
        root->walk_tree(&adrawwalker, window_tree_walk_style::bonjour_children);
'''

    new='''        window_drawer_walker adrawwalker(builder, b53_trace, b53_frame);
        root->walk_tree(&adrawwalker, window_tree_walk_style::bonjour_children);
'''
    screen=rep_between(screen,begin,end,old,new,"B53 walker call")

    old='''        return adrawwalker.total_redrawed_;
    }
'''

    new='''        if (b53_trace) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][COMPOSITOR_FRAME] phase=end frame={} screen={} focus_id={} focus_name={} total_clients={} total_visible={} total_physically_seen={} total_drawn={} flags_after=0x{:08X} behavior=OBSERVE_ONLY",
                b53_frame, number,
                focus ? focus->id : 0,
                focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>"),
                adrawwalker.total_clients_,
                adrawwalker.total_visible_,
                adrawwalker.total_physically_seen_,
                adrawwalker.total_redrawed_,
                static_cast<std::uint32_t>(flags_));
        }

        return adrawwalker.total_redrawed_;
    }
'''
    screen=rep_between(screen,begin,end,old,new,"B53 frame end")

    # Guard: preserve original clear semantics exactly.
    clear_anchor='''        builder.clear(eka2l1::vecx<float, 6>({ 0.0, 0.0, 0.0, 0.0, 1.0, 0.0 }), drivers::draw_buffer_bit_depth_buffer
            | drivers::draw_buffer_bit_stencil_buffer | ((flags_ & FLAG_SERVER_REDRAW_PENDING) ? drivers::draw_buffer_bit_color_buffer : 0));
'''
    if screen.count(clear_anchor)!=1:
        fail("original conditional color clear was modified")

    for marker in (frame_marker,group_marker,canvas_marker):
        if marker not in screen:
            fail("missing B53 marker: "+marker)

    screen_path.write_text(screen,encoding="utf-8")

    print(MARK+": applied")
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
