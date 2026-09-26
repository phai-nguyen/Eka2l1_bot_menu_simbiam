#!/usr/bin/env python3
"""NATIVEBOOT2 B50 POSTLOGOCANVAS1.

Diagnostic-only tracing selected from B49 device log + video.

B49 proves:
- S60SplashScreenGroup owns focus when the Nokia logo first appears;
- Startup and Home screen both create focus-requesting WindowGroups while the
  splash group remains in front;
- at ~120 s the splash group is reordered and Startup becomes focus;
- the splash process then exits, but the video still shows the Nokia pixels;
- Home screen does not become focus until emulator teardown.

B50 classifies whether the post-logo failure is:
A) group ordering/focusability; or
B) Home/Startup canvas creation/activation/visibility; or
C) a later redraw/compositor problem.

No result, focus policy, z-order request, visibility request, activation, or
rendering behavior is changed.
"""
from pathlib import Path
import re
import sys

MARK="NATIVEBOOT2-B50-POSTLOGOCANVAS1"

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
        fail("usage: apply_nativeboot2_b50_postlogocanvas1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    window_path=up/"src/emu/services/src/window/window.cpp"
    winbase_path=up/"src/emu/services/src/window/classes/winbase.cpp"
    winuser_path=up/"src/emu/services/src/window/classes/winuser.cpp"
    wingroup_path=up/"src/emu/services/src/window/classes/wingroup.cpp"
    screen_path=up/"src/emu/services/src/window/screen.cpp"

    for p in (window_path,winbase_path,winuser_path,wingroup_path,screen_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    window=window_path.read_text(encoding="utf-8")
    winbase=winbase_path.read_text(encoding="utf-8")
    winuser=winuser_path.read_text(encoding="utf-8")
    wingroup=wingroup_path.read_text(encoding="utf-8")
    screen=screen_path.read_text(encoding="utf-8")

    # Predecessor authority from B49.
    for marker in (
        "[NBOOT2][POSTLOGO_WG_FIND]",
        "[NBOOT2][POSTLOGO_WG_CREATE]",
        "[NBOOT2][POSTLOGO_WG_ORDINAL]",
    ):
        if marker not in window:
            fail("missing B49 window marker: "+marker)
    if "[NBOOT2][POSTLOGO_FOCUS]" not in screen:
        fail("missing B49 focus marker")

    markers=(
        "[NBOOT2][POSTLOGO_ORDERPRI]",
        "[NBOOT2][POSTLOGO_RECEIVEFOCUS]",
        "[NBOOT2][POSTLOGO_CANVAS_CREATE]",
        "[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]",
        "[NBOOT2][POSTLOGO_CANVAS_VISIBLE]",
        "[NBOOT2][POSTLOGO_WG_DESTROY]",
    )
    combined=window+winbase+winuser+wingroup
    if any(m in combined for m in markers):
        if all(m in combined for m in markers):
            print(MARK+": already applied")
            return
        fail("partial B50 patch detected")

    # Relevant actors from B49 visual/focus evidence.
    helper='''    static bool b50_postlogo_uid(const std::uint32_t uid) {
        return uid == 0x100059DEU || uid == 0x100058F4U || uid == 0x102750F0U;
    }

'''
    anchor='''namespace eka2l1::epoc {
'''
    winbase=rep_once(winbase,anchor,anchor+helper,"winbase helper")
    winuser=rep_once(winuser,anchor,anchor+helper,"winuser helper")
    wingroup=rep_once(wingroup,anchor,anchor+helper,"wingroup helper")
    window=rep_once(window,anchor,anchor+helper,"window helper")

    # 1) Trace SetOrdinalPositionPri (window opcode 0x06). This is the exact
    # command whose B49 timestamp coincides with splash -> Startup focus.
    old='''        case EWsWinOpSetOrdinalPositionPri: {
            ws_cmd_ordinal_pos_pri *info = reinterpret_cast<decltype(info)>(cmd.data_ptr);
            priority = info->pri1;
            const int position = info->pri2;

            set_position(position);
            ctx.complete(epoc::error_none);

            return true;
        }
'''
    new='''        case EWsWinOpSetOrdinalPositionPri: {
            ws_cmd_ordinal_pos_pri *info = reinterpret_cast<decltype(info)>(cmd.data_ptr);
            kernel::thread *b50_thr = ctx.msg ? ctx.msg->own_thr : nullptr;
            kernel::process *b50_pr = b50_thr ? b50_thr->owning_process() : nullptr;
            const std::uint32_t b50_uid3 = b50_pr
                ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
            const int b50_old_priority = priority;
            const int b50_old_ordinal = parent ? ordinal_position(true) : -1;

            priority = info->pri1;
            const int position = info->pri2;
            set_position(position);

            if (b50_postlogo_uid(b50_uid3)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][POSTLOGO_ORDERPRI] process={} uid3=0x{:08X} thread={} object_id={} client_handle=0x{:08X} kind={} requested_priority={} requested_position={} old_priority={} new_priority={} old_ordinal={} new_ordinal={} result=0 behavior=OBSERVE_ONLY",
                    b50_pr ? b50_pr->name() : std::string("<null>"),
                    b50_uid3,
                    b50_thr ? b50_thr->name() : std::string("<null>"),
                    id, client_handle, static_cast<int>(type),
                    info->pri1, position, b50_old_priority, priority,
                    b50_old_ordinal, parent ? ordinal_position(true) : -1);
            }

            ctx.complete(epoc::error_none);
            return true;
        }
'''
    winbase=rep_once(winbase,old,new,"ORDERPRI")

    # 2) Trace explicit ReceiveFocus changes on WindowGroups. Keep the
    # insertion anchors narrow because earlier milestones may have touched
    # nearby logging/locking without changing the operation itself.
    old='''    void window_group::receive_focus(service::ipc_context &context, ws_cmd &cmd) {
'''
    new='''    void window_group::receive_focus(service::ipc_context &context, ws_cmd &cmd) {
        kernel::thread *b50_thr = context.msg ? context.msg->own_thr : nullptr;
        kernel::process *b50_pr = b50_thr ? b50_thr->owning_process() : nullptr;
        const std::uint32_t b50_uid3 = b50_pr
            ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
        const bool b50_old_focusable = can_receive_focus();
        const bool b50_requested = (*reinterpret_cast<std::uint32_t *>(cmd.data_ptr)) != 0;
'''
    wingroup=rep_once(wingroup,old,new,"RECEIVEFOCUS entry")

    b=wingroup.find("    void window_group::receive_focus")
    e=wingroup.find("    void window_group::on_owner_process_uid_type_change",b)
    if b<0 or e<0:
        fail("RECEIVEFOCUS result: bounds not found")
    block=wingroup[b:e]
    m=re.search(r'(?m)^(\s+[^\n]*update_focus\([^\n;]*\);\n)',block)
    if not m:
        fail("RECEIVEFOCUS result: update_focus call not found")
    call=m.group(1)
    trace=call+'''        if (b50_postlogo_uid(b50_uid3)) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_RECEIVEFOCUS] process={} uid3=0x{:08X} thread={} group_id={} client_handle=0x{:08X} group_name={} requested={} old_focusable={} new_focusable={} final_focus_id={} behavior=OBSERVE_ONLY",
                b50_pr ? b50_pr->name() : std::string("<null>"),
                b50_uid3,
                b50_thr ? b50_thr->name() : std::string("<null>"),
                id, client_handle, common::ucs2_to_utf8(name),
                b50_requested ? 1 : 0, b50_old_focusable ? 1 : 0,
                can_receive_focus() ? 1 : 0,
                scr->focus ? scr->focus->id : 0);
        }
'''
    block=block[:m.start()]+trace+block[m.end():]
    wingroup=wingroup[:b]+block+wingroup[e:]

    # 3) Trace group destruction. This tells us exactly when the splash group
    # leaves the WindowServer tree and what group becomes focus afterward.
    old='''    window_group::~window_group() {
        if (uid_owner_change_process) {
'''
    new='''    window_group::~window_group() {
        kernel::process *b50_pr = client && client->get_client()
            ? client->get_client()->owning_process() : nullptr;
        const std::uint32_t b50_uid3 = b50_pr
            ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
        if (b50_postlogo_uid(b50_uid3)) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_DESTROY] phase=begin process={} uid3=0x{:08X} group_id={} client_handle=0x{:08X} group_name={} priority={} ordinal={} focusable={} was_focus={} behavior=OBSERVE_ONLY",
                b50_pr ? b50_pr->name() : std::string("<null>"), b50_uid3,
                id, client_handle, common::ucs2_to_utf8(name), priority,
                parent ? ordinal_position(true) : -1,
                can_receive_focus() ? 1 : 0,
                (scr && this == scr->focus) ? 1 : 0);
        }
        if (uid_owner_change_process) {
'''
    wingroup=rep_once(wingroup,old,new,"WG_DESTROY begin")

    old='''        if (scr) {
            scr->need_update_visible_regions(true);
        }
    }
'''
    new='''        if (scr) {
            scr->need_update_visible_regions(true);
        }
        if (b50_postlogo_uid(b50_uid3)) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_DESTROY] phase=end process={} uid3=0x{:08X} group_id={} final_focus_id={} redraw_region_pending=1 behavior=OBSERVE_ONLY",
                b50_pr ? b50_pr->name() : std::string("<null>"), b50_uid3,
                id, (scr && scr->focus) ? scr->focus->id : 0);
        }
    }
'''
    wingroup=rep_between(wingroup,
        "    window_group::~window_group() {",
        "    void window_group::queue_message_data",
        old,new,"WG_DESTROY end")

    # 4) Trace client canvas creation for splash/startup/Home. Locate the
    # completion structurally because the B28 bootstrap source predates some
    # upstream spelling/layout changes.
    b=window.find("    void window_server_client::create_window_base")
    e=window.find("    void window_server_client::create_graphic_context",b)
    if b<0 or e<0:
        fail("CANVAS_CREATE: bounds not found")
    block=window[b:e]
    m=re.search(
        r'(?m)^(\s*)([A-Za-z_]\w*)\.complete\(\s*add_object\(([^\n;]*\bwin\b[^\n;]*)\)\s*\);\s*$',
        block)
    if not m:
        fail("CANVAS_CREATE: direct add_object completion not found")
    indent,ctx_name,add_arg=m.group(1),m.group(2),m.group(3)
    replacement=indent+'''epoc::canvas_base *b50_canvas = reinterpret_cast<epoc::canvas_base *>(win.get());
''' + indent + '''epoc::window_group *b50_group = b50_canvas ? b50_canvas->get_group() : nullptr;
''' + indent + '''kernel::thread *b50_thr = '''+ctx_name+'''.msg ? '''+ctx_name+'''.msg->own_thr : nullptr;
''' + indent + '''kernel::process *b50_pr = b50_thr ? b50_thr->owning_process() : nullptr;
''' + indent + '''const std::uint32_t b50_uid3 = b50_pr
''' + indent + '''    ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
''' + indent + '''const std::uint32_t b50_handle = add_object('''+add_arg+''');
''' + indent + '''if (b50_postlogo_uid(b50_uid3)) {
''' + indent + '''    LOG_WARN(SERVICE_WINDOW,
''' + indent + '''        "[NBOOT2][POSTLOGO_CANVAS_CREATE] process={} uid3=0x{:08X} thread={} object_handle=0x{:08X} client_handle=0x{:08X} win_type={} group_id={} group_handle=0x{:08X} group_name={} behavior=OBSERVE_ONLY",
''' + indent + '''        b50_pr ? b50_pr->name() : std::string("<null>"), b50_uid3,
''' + indent + '''        b50_thr ? b50_thr->name() : std::string("<null>"),
''' + indent + '''        b50_handle,
''' + indent + '''        b50_canvas ? b50_canvas->client_handle : 0,
''' + indent + '''        b50_canvas ? static_cast<int>(b50_canvas->win_type) : -1,
''' + indent + '''        b50_group ? b50_group->id : 0,
''' + indent + '''        b50_group ? b50_group->client_handle : 0,
''' + indent + '''        b50_group ? common::ucs2_to_utf8(b50_group->name) : std::string("<null>"));
''' + indent + '''}
''' + indent + ctx_name + '''.complete(b50_handle);'''
    block=block[:m.start()]+replacement+block[m.end():]
    window=window[:b]+block+window[e:]

    # 5) Trace activation. Source is winuser.cpp (the earlier B49 attempt
    # incorrectly targeted window.cpp; B50 uses the authoritative file).
    old='''    void canvas_base::activate(service::ipc_context &context, ws_cmd &cmd) {
        flags |= flags_active;
        on_activate();

        if (is_visible()) {
            scr->need_update_visible_regions(true);
        }

        context.complete(epoc::error_none);
    }
'''
    new='''    void canvas_base::activate(service::ipc_context &context, ws_cmd &cmd) {
        kernel::thread *b50_thr = context.msg ? context.msg->own_thr : nullptr;
        kernel::process *b50_pr = b50_thr ? b50_thr->owning_process() : nullptr;
        const std::uint32_t b50_uid3 = b50_pr
            ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
        epoc::window_group *b50_group = get_group();
        const std::uint32_t b50_flags_before = flags;

        flags |= flags_active;
        on_activate();

        if (is_visible()) {
            scr->need_update_visible_regions(true);
        }

        if (b50_postlogo_uid(b50_uid3)) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_CANVAS_ACTIVATE] process={} uid3=0x{:08X} thread={} client_handle=0x{:08X} group_id={} group_handle=0x{:08X} group_name={} flags_before=0x{:08X} flags_after=0x{:08X} visible={} physically_seen={} result=0 behavior=OBSERVE_ONLY",
                b50_pr ? b50_pr->name() : std::string("<null>"), b50_uid3,
                b50_thr ? b50_thr->name() : std::string("<null>"),
                client_handle,
                b50_group ? b50_group->id : 0,
                b50_group ? b50_group->client_handle : 0,
                b50_group ? common::ucs2_to_utf8(b50_group->name) : std::string("<null>"),
                b50_flags_before, flags,
                is_visible() ? 1 : 0,
                can_be_physically_seen() ? 1 : 0);
        }

        context.complete(epoc::error_none);
    }
'''
    winuser=rep_once(winuser,old,new,"CANVAS_ACTIVATE")

    # 6) Trace SetVisible requests.
    old='''        case EWsWinOpSetVisible: {
            const std::uint32_t visible = *reinterpret_cast<std::uint32_t *>(cmd.data_ptr);

            set_visible(visible != 0);
            ctx.complete(epoc::error_none);

            break;
        }
'''
    new='''        case EWsWinOpSetVisible: {
            const std::uint32_t visible = *reinterpret_cast<std::uint32_t *>(cmd.data_ptr);
            kernel::thread *b50_thr = ctx.msg ? ctx.msg->own_thr : nullptr;
            kernel::process *b50_pr = b50_thr ? b50_thr->owning_process() : nullptr;
            const std::uint32_t b50_uid3 = b50_pr
                ? static_cast<std::uint32_t>(std::get<2>(b50_pr->get_uid_type())) : 0;
            epoc::window_group *b50_group = get_group();
            const bool b50_before = is_visible();

            set_visible(visible != 0);
            if (b50_postlogo_uid(b50_uid3)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][POSTLOGO_CANVAS_VISIBLE] process={} uid3=0x{:08X} thread={} client_handle=0x{:08X} group_id={} group_handle=0x{:08X} group_name={} requested={} visible_before={} visible_after={} physically_seen_after={} result=0 behavior=OBSERVE_ONLY",
                    b50_pr ? b50_pr->name() : std::string("<null>"), b50_uid3,
                    b50_thr ? b50_thr->name() : std::string("<null>"),
                    client_handle,
                    b50_group ? b50_group->id : 0,
                    b50_group ? b50_group->client_handle : 0,
                    b50_group ? common::ucs2_to_utf8(b50_group->name) : std::string("<null>"),
                    visible ? 1 : 0, b50_before ? 1 : 0,
                    is_visible() ? 1 : 0,
                    can_be_physically_seen() ? 1 : 0);
            }
            ctx.complete(epoc::error_none);

            break;
        }
'''
    winuser=rep_once(winuser,old,new,"CANVAS_VISIBLE")

    # Postconditions.
    combined=window+winbase+winuser+wingroup
    for m in markers:
        if m not in combined:
            fail("missing B50 marker after patch: "+m)
    if "[NBOOT2][POSTLOGO_FOCUS]" not in screen:
        fail("B49 focus marker lost")

    window_path.write_text(window,encoding="utf-8")
    winbase_path.write_text(winbase,encoding="utf-8")
    winuser_path.write_text(winuser,encoding="utf-8")
    wingroup_path.write_text(wingroup,encoding="utf-8")

    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("order_result_change=NONE")
    print("focus_policy_change=NONE")
    print("canvas_create_result_change=NONE")
    print("activation_result_change=NONE")
    print("visibility_result_change=NONE")
    print("rendering_change=NONE")
    print("B49_FOCUS_TRACE=PRESERVED")

if __name__=="__main__":
    main()
