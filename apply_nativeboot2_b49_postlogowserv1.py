#!/usr/bin/env python3
"""NATIVEBOOT2 B49 POSTLOGOWSERV1.

Diagnostic-only tracing selected from B48 device video + logs.

B48 proves:
- the Nokia startup logo is rendered;
- native Home screen reaches WindowServer event-ready;
- xnthemeserver/FileFlush is healthy;
- the visible screen nevertheless remains on the Nokia logo.

B49 therefore observes the post-logo WindowServer group/focus/activation path
without changing any guest-visible result or ordering.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B49-POSTLOGOWSERV1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b49_postlogowserv1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    win_path=up/"src/emu/services/src/window/window.cpp"
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    files_path=up/"src/emu/services/src/fs/files.cpp"
    svc_path=up/"src/emu/kernel/src/svc.cpp"

    for p in (win_path,screen_path,files_path,svc_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    win=win_path.read_text(encoding="utf-8")
    screen=screen_path.read_text(encoding="utf-8")
    files=files_path.read_text(encoding="utf-8")
    svc=svc_path.read_text(encoding="utf-8")

    # Predecessor authority.
    if "[NBOOT2][XNTHEME_FSFLUSH]" not in files:
        fail("B48 FileFlush marker missing")
    if "[NBOOT2][XNTHEME_IPC]" not in svc:
        fail("B48 xntheme IPC marker missing")

    markers=[
        "[NBOOT2][POSTLOGO_WG_FIND]",
        "[NBOOT2][POSTLOGO_WG_CREATE]",
        "[NBOOT2][POSTLOGO_WG_ORDINAL]",
        "[NBOOT2][POSTLOGO_FOCUS]",
    ]
    if any(m in win or m in screen for m in markers):
        if all((m in win or m in screen) for m in markers):
            print(MARK+": already applied")
            return
        fail("partial B49 patch detected")

    # 1) Trace exact WindowGroup wildcard lookups (client op 0x2B / decimal 43).
    old='''        const char16_t *win_group_name_ptr = reinterpret_cast<char16_t *>(find_info + 1);
        const std::u16string win_group_name(win_group_name_ptr, find_info->length);
        std::wstring win_group_name_w = common::ucs2_to_wstr(win_group_name);
'''
    new='''        const char16_t *win_group_name_ptr = reinterpret_cast<char16_t *>(find_info + 1);
        const std::u16string win_group_name(win_group_name_ptr, find_info->length);
        std::wstring win_group_name_w = common::ucs2_to_wstr(win_group_name);

        kernel::thread *b49_find_thr = ctx.msg ? ctx.msg->own_thr : nullptr;
        kernel::process *b49_find_pr = b49_find_thr ? b49_find_thr->owning_process() : nullptr;
        const std::uint32_t b49_find_uid3 = b49_find_pr
            ? static_cast<std::uint32_t>(std::get<2>(b49_find_pr->get_uid_type())) : 0;
        if (get_ws().get_kernel_system()->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_FIND] phase=request process={} uid3=0x{:08X} thread={} previous_id={} offset={} length={} pattern={} behavior=OBSERVE_ONLY",
                b49_find_pr ? b49_find_pr->name() : std::string("<null>"),
                b49_find_uid3,
                b49_find_thr ? b49_find_thr->name() : std::string("<null>"),
                find_info->previous_id, find_info->offset, find_info->length,
                common::ucs2_to_utf8(win_group_name));
        }
'''
    win=rep_once(win,old,new,"WG_FIND request")

    old='''            if (common::full_wildcard_match(name_copy_raw_w, win_group_name_w, true)) {
                ctx.complete(group->id);
                return;
            }
        }

        ctx.complete(epoc::error_not_found);
'''
    new='''            if (common::full_wildcard_match(name_copy_raw_w, win_group_name_w, true)) {
                if (get_ws().get_kernel_system()->get_config()->native_phone_boot) {
                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][POSTLOGO_WG_FIND] phase=result result={} matched=1 group_id={} group_client_handle=0x{:08X} group_name={} behavior=OBSERVE_ONLY",
                        group->id, group->id, group->client_handle,
                        common::ucs2_to_utf8(group->name));
                }
                ctx.complete(group->id);
                return;
            }
        }

        if (get_ws().get_kernel_system()->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_FIND] phase=result result={} matched=0 pattern={} behavior=OBSERVE_ONLY",
                epoc::error_not_found, common::ucs2_to_utf8(win_group_name));
        }
        ctx.complete(epoc::error_not_found);
'''
    win=rep_once(win,old,new,"WG_FIND result")

    # 2) Trace WindowGroup creation with caller + focus flag.
    old='''        std::uint32_t id = add_object(group);
        ctx.complete(id);
    }

    void window_server_client::create_window_base'''
    new='''        std::uint32_t id = add_object(group);
        if (get_ws().get_kernel_system()->get_config()->native_phone_boot) {
            kernel::thread *b49_create_thr = ctx.msg ? ctx.msg->own_thr : nullptr;
            kernel::process *b49_create_pr = b49_create_thr ? b49_create_thr->owning_process() : nullptr;
            const std::uint32_t b49_create_uid3 = b49_create_pr
                ? static_cast<std::uint32_t>(std::get<2>(b49_create_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_CREATE] process={} uid3=0x{:08X} thread={} id={} client_handle=0x{:08X} focus_request={} parent_id=0x{:08X} screen={} group_name={} current_focus_id={} behavior=OBSERVE_ONLY",
                b49_create_pr ? b49_create_pr->name() : std::string("<null>"),
                b49_create_uid3,
                b49_create_thr ? b49_create_thr->name() : std::string("<null>"),
                id, header->client_handle, header->focus ? 1 : 0, header->parent_id,
                target_screen ? target_screen->number : -1,
                common::ucs2_to_utf8(group_casted->name),
                (target_screen && target_screen->focus) ? target_screen->focus->id : 0);
        }
        ctx.complete(id);
    }

    void window_server_client::create_window_base'''
    win=rep_once(win,old,new,"WG_CREATE")

    # 3) Trace ordinal repositioning, which can change focus/z ordering.
    old='''        group->set_position(set->ord_pos);
        ctx.complete(epoc::error_none);
    }

    struct def_mode_max_num_colors'''
    new='''        const int b49_old_ord = group->ordinal_position(true);
        group->set_position(set->ord_pos);
        const int b49_new_ord = group->ordinal_position(true);
        if (get_ws().get_kernel_system()->get_config()->native_phone_boot) {
            kernel::thread *b49_ord_thr = ctx.msg ? ctx.msg->own_thr : nullptr;
            kernel::process *b49_ord_pr = b49_ord_thr ? b49_ord_thr->owning_process() : nullptr;
            const std::uint32_t b49_ord_uid3 = b49_ord_pr
                ? static_cast<std::uint32_t>(std::get<2>(b49_ord_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_WG_ORDINAL] process={} uid3=0x{:08X} thread={} group_id={} group_name={} requested={} old={} new={} result=0 behavior=OBSERVE_ONLY",
                b49_ord_pr ? b49_ord_pr->name() : std::string("<null>"),
                b49_ord_uid3,
                b49_ord_thr ? b49_ord_thr->name() : std::string("<null>"),
                group->id, common::ucs2_to_utf8(group->name),
                set->ord_pos, b49_old_ord, b49_new_ord);
        }
        ctx.complete(epoc::error_none);
    }

    struct def_mode_max_num_colors'''
    win=rep_once(win,old,new,"WG_ORDINAL")

    # 4) Focus selection is the key post-logo boundary.
    if "#include <common/cvt.h>" not in screen:
        screen=rep_once(screen,"#include <common/rgb.h>\n","#include <common/cvt.h>\n#include <common/rgb.h>\n","screen cvt include")

    old='''        // Iterate through root's childs.
        focus = find_group_to_focus(root.get());
        const bool is_me_currently_focus = (serv->get_current_focus_screen() == this);
'''
    new='''        // Iterate through root's childs.
        focus = find_group_to_focus(root.get());
        const bool is_me_currently_focus = (serv->get_current_focus_screen() == this);

        if (serv->get_kernel_system()->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_FOCUS] phase=select screen={} old_id={} old_handle=0x{:08X} old_name={} new_id={} new_handle=0x{:08X} new_name={} closing_id={} current_focus_screen={} behavior=OBSERVE_ONLY",
                number,
                old_focus ? old_focus->id : 0,
                old_focus ? old_focus->client_handle : 0,
                old_focus ? common::ucs2_to_utf8(old_focus->name) : std::string("<null>"),
                focus ? focus->id : 0,
                focus ? focus->client_handle : 0,
                focus ? common::ucs2_to_utf8(focus->name) : std::string("<null>"),
                closing_group ? closing_group->id : 0,
                is_me_currently_focus ? 1 : 0);
        }
'''
    screen=rep_once(screen,old,new,"FOCUS select")

    old='''        return (new_focus_screen ? alternative_focus : focus);
    }

    epoc::window_group *screen::get_group_chain'''
    new='''        if (serv->get_kernel_system()->get_config()->native_phone_boot) {
            epoc::window_group *b49_final_focus = new_focus_screen ? alternative_focus : focus;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][POSTLOGO_FOCUS] phase=final screen={} focus_id={} focus_handle=0x{:08X} focus_name={} switched_screen={} behavior=OBSERVE_ONLY",
                number,
                b49_final_focus ? b49_final_focus->id : 0,
                b49_final_focus ? b49_final_focus->client_handle : 0,
                b49_final_focus ? common::ucs2_to_utf8(b49_final_focus->name) : std::string("<null>"),
                new_focus_screen ? 1 : 0);
        }
        return (new_focus_screen ? alternative_focus : focus);
    }

    epoc::window_group *screen::get_group_chain'''
    screen=rep_once(screen,old,new,"FOCUS final")

    # Postconditions.
    for m in markers[:4]:
        if m not in win and m not in screen:
            fail("missing marker after patch: "+m)
    if "[NBOOT2][XNTHEME_FSFLUSH]" not in files:
        fail("B48 FileFlush marker lost")
    if "[NBOOT2][XNTHEME_IPC]" not in svc:
        fail("B48 xntheme marker lost")

    win_path.write_text(win,encoding="utf-8")
    screen_path.write_text(screen,encoding="utf-8")

    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("window_group_result_change=NONE")
    print("focus_result_change=NONE")
    print("ordinal_semantics_change=NONE")
    print("B48_FILEFLUSH_HEALTH=PRESERVED")
    print("B47_STOCK_TFX_SUPPRESSION=PRESERVED")

if __name__=="__main__":
    main()
