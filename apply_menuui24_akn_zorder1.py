#!/usr/bin/env python3
"""MENUUI24 AKN-ZORDER1: implement Avkon application switching opcodes 58/68.

Baseline: MENUUI23 APPTYPE1 + MENUUI22 SCHEDRUN1 + NOJAVA FULL1 + MANIC3.

Device EXIT1 + EXIT-CONTROL1 show both Messaging and Contacts receive the Exit
softkey but remain foreground. Immediately afterwards AknCapServer opcodes
0x3A (HideApplicationFromFSW) and 0x44 (MoveAppInZOrder) are fake-success
stubs in EKA2L1.

Symbian source semantics:
- HideApplicationFromFsw(aHide, aUid): maintain Fast Swap Window hidden state.
- MoveAppInZOrder(wg, ESgcMoveAppToForeground=0): SetWindowGroupOrdinalPosition(wg, 0)
- MoveAppInZOrder(wg, ESgcMoveAppToBackground=1): SetWindowGroupOrdinalPosition(wg, -1)

EKA2L1 already implements window::set_position(), including focus recalculation,
so reuse that authority. Do not force-kill processes, patch the scheduler, or
alter APPTYPE1.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI24 AKN-ZORDER1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui24_akn_zorder1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    oom = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    oom_h = up / "src/emu/services/include/services/ui/cap/oom_app.h"
    winbase = up / "src/emu/services/src/window/classes/winbase.cpp"
    applist = up / "src/emu/services/src/applist/applist.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (oom, oom_h, winbase, applist, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    applist_text = applist.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:" not in applist_text:
        fail("MENUUI23 APPTYPE1 baseline marker missing")
    if "case applist_request_get_app_type:" not in applist_text:
        fail("MENUUI23 GetAppType implementation missing")

    kernel_text = kernel.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:" not in kernel_text:
        fail("MENUUI22 SCHEDRUN1 marker missing")

    svc_text = svc.read_text(encoding="utf-8")
    for marker in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_SEND:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER:",
    ):
        if marker not in svc_text:
            fail("MENUUI22 diagnostic marker missing: " + marker)

    root_text = root.read_text(encoding="utf-8")
    if "MANIC_MODALFIX1" not in root_text:
        fail("MANIC3 MODALFIX1 baseline missing")

    header = oom_h.read_text(encoding="utf-8")
    for required in (
        "akns_hide_app_from_fws = 58,",
        "akn_eik_app_ui_move_app_in_z_order = 68,",
    ):
        if required not in header:
            fail("AknCap opcode authority missing: " + required)

    winbase_text = winbase.read_text(encoding="utf-8")
    if "void window::set_position(const int new_pos)" not in winbase_text:
        fail("window::set_position authority missing")
    if "scr->update_focus(&serv, nullptr);" not in winbase_text:
        fail("window::set_position focus recalculation missing")

    text = oom.read_text(encoding="utf-8")
    zmarker = "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER:"
    hmarker = "SYMBIAN-SYSTEMAPPS1 MENUUI24 HIDE_FSW:"
    if zmarker in text or hmarker in text:
        if text.count(zmarker) == 4 and text.count(hmarker) == 3:
            print("MENUUI24 AKN-ZORDER1 already present")
            return
        fail("partial prior MENUUI24 patch detected")

    include_anchor = "#include <utils/err.h>\n"
    include_new = "#include <utils/err.h>\n\n#include <unordered_set>\n"
    text = replace_once(text, include_anchor, include_new, "unordered_set include")

    ns_anchor = "namespace eka2l1 {\n"
    ns_new = """namespace eka2l1 {
    // MENUUI24: AknCapServer Fast Swap Window visibility state.
    // Symbian stores this in AknCapServer; keep it host-side and process-lifetime.
    static std::mutex menuui24_hidden_fsw_lock;
    static std::unordered_set<std::uint32_t> menuui24_hidden_fsw_uids;

"""
    text = replace_once(text, ns_anchor, ns_new, "MENUUI24 FSW state")

    switch_anchor = """        case akns_unblank_screen: {
            unblank_screen(ctx);
            break;
        }

        case akn_eik_app_ui_redraw_server_status_pane: {
"""
    switch_new = """        case akns_unblank_screen: {
            unblank_screen(ctx);
            break;
        }

        case akns_hide_app_from_fws: {
            // RAknUiServer::HideApplicationFromFsw sends TIpcArgs(uid, hide).
            const std::optional<std::uint32_t> app_uid =
                ctx->get_argument_value<std::uint32_t>(0);
            const std::optional<std::int32_t> hide =
                ctx->get_argument_value<std::int32_t>(1);

            if (!app_uid.has_value() || !hide.has_value()) {
                LOG_WARN(SERVICE_UI,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI24 HIDE_FSW: result=bad_argument opcode=58");
                ctx->complete(epoc::error_argument);
                break;
            }

            {
                const std::lock_guard<std::mutex> guard(menuui24_hidden_fsw_lock);
                if (hide.value()) {
                    menuui24_hidden_fsw_uids.insert(app_uid.value());
                } else {
                    menuui24_hidden_fsw_uids.erase(app_uid.value());
                }
            }

            LOG_WARN(SERVICE_UI,
                "SYMBIAN-SYSTEMAPPS1 MENUUI24 HIDE_FSW: result=ok opcode=58 app_uid=0x{:08X} hidden={}",
                app_uid.value(), hide.value() ? 1 : 0);
            ctx->complete(epoc::error_none);
            break;
        }

        case akn_eik_app_ui_move_app_in_z_order: {
            // Symbian TSgcMoveAppToWhere:
            //   0 = foreground -> SetWindowGroupOrdinalPosition(wg, 0)
            //   1 = background -> SetWindowGroupOrdinalPosition(wg, -1)
            const std::optional<std::int32_t> window_group_id =
                ctx->get_argument_value<std::int32_t>(0);
            const std::optional<std::int32_t> where =
                ctx->get_argument_value<std::int32_t>(1);

            if (!window_group_id.has_value() || !where.has_value()
                || (where.value() != 0 && where.value() != 1)) {
                LOG_WARN(SERVICE_UI,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER: result=bad_argument opcode=68");
                ctx->complete(epoc::error_argument);
                break;
            }

            kernel_system *kern = ctx->sys->get_kernel_system();
            auto winsrv_obj = kern->get_by_name<service::server>(
                get_winserv_name_by_epocver(ctx->sys->get_symbian_version_use()));
            if (!winsrv_obj) {
                LOG_WARN(SERVICE_UI,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER: result=no_window_server opcode=68 wg_id={}",
                    window_group_id.value());
                ctx->complete(epoc::error_not_found);
                break;
            }

            window_server *winsrv =
                reinterpret_cast<window_server *>(&(*winsrv_obj));
            epoc::window_group *group = winsrv->get_group_from_id(
                static_cast<epoc::ws::uid>(window_group_id.value()));
            if (!group || !group->scr) {
                LOG_WARN(SERVICE_UI,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER: result=group_not_found opcode=68 wg_id={} where={}",
                    window_group_id.value(), where.value());
                ctx->complete(epoc::error_not_found);
                break;
            }

            const int before_pos = group->ordinal_position(true);
            const std::uint32_t focus_before =
                group->scr->focus ? group->scr->focus->id : 0U;

            group->set_position(where.value() == 0 ? 0 : -1);

            const int after_pos = group->ordinal_position(true);
            const std::uint32_t focus_after =
                group->scr->focus ? group->scr->focus->id : 0U;

            LOG_WARN(SERVICE_UI,
                "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER: result=ok opcode=68 wg_id={} where={} before_pos={} after_pos={} focus_before={} focus_after={}",
                window_group_id.value(), where.value(), before_pos, after_pos,
                focus_before, focus_after);
            ctx->complete(epoc::error_none);
            break;
        }

        case akn_eik_app_ui_redraw_server_status_pane: {
"""
    text = replace_once(text, switch_anchor, switch_new, "AknCap switch implementation")

    info_anchor = """            info.flags_ = the_name_parts[0].as_int<std::uint32_t>(0, 16);
            info.screen_number_ = group->scr->number;
            info.associated_ = group->client->get_client()->owning_process();

            if (info.app_uid_ != 0) {
"""
    info_new = """            info.flags_ = the_name_parts[0].as_int<std::uint32_t>(0, 16);
            info.screen_number_ = group->scr->number;
            info.associated_ = group->client->get_client()->owning_process();

            {
                const std::lock_guard<std::mutex> guard(menuui24_hidden_fsw_lock);
                if (menuui24_hidden_fsw_uids.find(info.app_uid_)
                    != menuui24_hidden_fsw_uids.end()) {
                    info.flags_ |= akn_running_app_info::FLAG_IS_HIDDEN;
                } else {
                    info.flags_ &= ~akn_running_app_info::FLAG_IS_HIDDEN;
                }
            }

            if (info.app_uid_ != 0) {
"""
    text = replace_once(text, info_anchor, info_new, "FSW hidden flag reflection")

    # Gates: only explicit opcode handling, using existing window authority.
    for required in (
        "case akns_hide_app_from_fws:",
        "case akn_eik_app_ui_move_app_in_z_order:",
        "group->set_position(where.value() == 0 ? 0 : -1);",
        "menuui24_hidden_fsw_uids.insert(app_uid.value());",
        "akn_running_app_info::FLAG_IS_HIDDEN",
    ):
        if required not in text:
            fail("implementation gate missing: " + required)

    if text.count(zmarker) != 4:
        fail(f"AKN_ZORDER marker gate failed: {text.count(zmarker)}")
    if text.count(hmarker) != 3:
        fail(f"HIDE_FSW marker gate failed: {text.count(hmarker)}")

    oom.write_text(text, encoding="utf-8")
    print("MENUUI24 AKN-ZORDER1 applied")
    print("MENUUI24 opcode58=HideApplicationFromFSW tracked")
    print("MENUUI24 opcode68 foreground=>ordinal0 background=>ordinal-1")
    print("MENUUI24 process_kill=NOT_ADDED scheduler_change=NONE")
    print("MENUUI24 APPTYPE1/SCHEDRUN1/NOJAVA/MANIC3=PRESERVED")


if __name__ == "__main__":
    main()
