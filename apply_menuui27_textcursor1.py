#!/usr/bin/env python3
"""MENUUI27 TEXTCURSOR1: implement S60 text-cursor window-group operations.

MENUUI26 device evidence:
- UniEditor opens successfully.
- Editor repeatedly issues WindowServer group op 0x2F while laying out/focusing
  editable controls.
- EKA2L1 currently implements only 0x2E SetTextCursor; 0x2F
  SetTextCursorClipped and 0x30 CancelTextCursor fall through fake-success.
- Symbian WindowServer maps:
    0x2E EWsWinOpSetTextCursor        -> iTextCursor.SetL(..., EFalse)
    0x2F EWsWinOpSetTextCursorClipped -> iTextCursor.SetL(..., ETrue)
    0x30 EWsWinOpCancelTextCursor     -> iTextCursor.Cancel()

EKA2L1 renders a text cursor through canvas_base::cursor_pos. Preserve the
currently associated client-window handle in the group so CancelTextCursor can
clear the same canvas. The full TTextCursor style/clip geometry is not rendered
by EKA2L1 yet; this patch implements the lifecycle/target semantics without
inventing font/FEP behavior.

Preserves MENUUI26 FSRESERVE1, MENUUI25 APPSERVICE1, MENUUI24 AKN-ZORDER1,
MENUUI23 APPTYPE1, MENUUI22 SCHEDRUN1, MANIC3 and NOJAVA.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI27 TEXTCURSOR1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n = text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui27_textcursor1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    wg_h = up / "src/emu/services/include/services/window/classes/wingroup.h"
    wg_cpp = up / "src/emu/services/src/window/classes/wingroup.cpp"
    op_h = up / "src/emu/services/include/services/window/op.h"
    winuser_cpp = up / "src/emu/services/src/window/classes/winuser.cpp"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    applist = up / "src/emu/services/src/applist/applist.cpp"
    oom = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (wg_h, wg_cpp, op_h, winuser_cpp, fs_cpp, applist, oom, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    cpp = wg_cpp.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR:" in cpp:
        print("MENUUI27 TEXTCURSOR1 already present")
        return

    # Proven lineage.
    if "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE:" not in fs_cpp.read_text(encoding="utf-8"):
        fail("MENUUI26 FSRESERVE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI25 APPSERVICE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER:" not in oom.read_text(encoding="utf-8"):
        fail("MENUUI24 AKN-ZORDER1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI23 APPTYPE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:" not in kernel.read_text(encoding="utf-8"):
        fail("MENUUI22 SCHEDRUN1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI22 sync diagnostics missing")
    if "MANIC_MODALFIX1" not in root.read_text(encoding="utf-8"):
        fail("MANIC3 baseline missing")
    if "cursor_pos(-1, -1)" not in winuser_cpp.read_text(encoding="utf-8"):
        fail("canvas text cursor sentinel authority missing")

    op = op_h.read_text(encoding="utf-8")
    for name in ("EWsWinOpSetTextCursor", "EWsWinOpSetTextCursorClipped", "EWsWinOpCancelTextCursor"):
        if name not in op:
            fail(f"window opcode enum missing: {name}")

    # Header: remember the active cursor's target window.
    h = wg_h.read_text(encoding="utf-8")
    old = """        kernel::process *uid_owner_change_process;
        ws::uid screen_change_event_handle;

        bool can_receive_focus() {
"""
    new = """        kernel::process *uid_owner_change_process;
        ws::uid screen_change_event_handle;

        // Symbian CWsWindowGroup owns one text cursor at a time. EKA2L1 stores
        // the rendered cursor position on the target client canvas, so retain
        // that canvas handle for CancelTextCursor.
        std::uint32_t text_cursor_window_handle;

        bool can_receive_focus() {
"""
    h = replace_once(h, old, new, "text cursor handle field")

    old = """        void set_text_cursor(service::ipc_context &context, ws_cmd &cmd);
        void receive_focus(service::ipc_context &context, ws_cmd &cmd);
"""
    new = """        void set_text_cursor(service::ipc_context &context, ws_cmd &cmd);
        void cancel_text_cursor(service::ipc_context &context);
        void receive_focus(service::ipc_context &context, ws_cmd &cmd);
"""
    h = replace_once(h, old, new, "cancel cursor declaration")
    wg_h.write_text(h, encoding="utf-8")

    # Constructor initialization.
    text = cpp
    old = """        , uid_owner_change_process(nullptr)
        , screen_change_event_handle(0) {
"""
    new = """        , uid_owner_change_process(nullptr)
        , screen_change_event_handle(0)
        , text_cursor_window_handle(0) {
"""
    text = replace_once(text, old, new, "cursor handle init")

    # Replace the old mostly-stub implementation.
    old = """    void window_group::set_text_cursor(service::ipc_context &context, ws_cmd &cmd) {
        // Warn myself in the future!
        LOG_WARN(SERVICE_WINDOW, "Set cursor text is mostly a stubbed now");

        ws_cmd_set_text_cursor *cmd_set = reinterpret_cast<decltype(cmd_set)>(cmd.data_ptr);
        auto canvas_base_to_set = reinterpret_cast<canvas_base *>(client->get_object(cmd_set->win));

        if (!canvas_base_to_set || (canvas_base_to_set->type != window_kind::client)) {
            LOG_ERROR(SERVICE_WINDOW, "Window not found or not client kind to set text cursor");
            context.complete(epoc::error_not_found);
            return;
        }

        canvas_base_to_set->cursor_pos = cmd_set->pos + canvas_base_to_set->pos;
        context.complete(epoc::error_none);
    }
"""
    new = """    void window_group::set_text_cursor(service::ipc_context &context, ws_cmd &cmd) {
        ws_cmd_set_text_cursor *cmd_set = reinterpret_cast<decltype(cmd_set)>(cmd.data_ptr);
        auto canvas_base_to_set = reinterpret_cast<canvas_base *>(client->get_object(cmd_set->win));

        if (!canvas_base_to_set || (canvas_base_to_set->type != window_kind::client)) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR: result=window_not_found op=0x{:X} win={}",
                cmd.header.op, cmd_set->win);
            context.complete(epoc::error_not_found);
            return;
        }

        // Clear a cursor left on a previous editor/window in this group.
        if (text_cursor_window_handle && text_cursor_window_handle != cmd_set->win) {
            auto previous = reinterpret_cast<canvas_base *>(
                client->get_object(text_cursor_window_handle));
            if (previous && previous->type == window_kind::client) {
                previous->cursor_pos = eka2l1::vec2(-1, -1);
            }
        }

        text_cursor_window_handle = cmd_set->win;
        canvas_base_to_set->cursor_pos = cmd_set->pos + canvas_base_to_set->pos;

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR: result=set op=0x{:X} clipped={} win={} local=({}, {}) absolute=({}, {})",
            cmd.header.op,
            cmd.header.op == EWsWinOpSetTextCursorClipped ? 1 : 0,
            cmd_set->win,
            cmd_set->pos.x, cmd_set->pos.y,
            canvas_base_to_set->cursor_pos.x, canvas_base_to_set->cursor_pos.y);
        context.complete(epoc::error_none);
    }

    void window_group::cancel_text_cursor(service::ipc_context &context) {
        const std::uint32_t old_handle = text_cursor_window_handle;
        bool cleared = false;

        if (old_handle) {
            auto canvas = reinterpret_cast<canvas_base *>(client->get_object(old_handle));
            if (canvas && canvas->type == window_kind::client) {
                canvas->cursor_pos = eka2l1::vec2(-1, -1);
                cleared = true;
            }
        }

        text_cursor_window_handle = 0;

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR: result=cancel op=0x{:X} win={} cleared={}",
            static_cast<std::uint32_t>(EWsWinOpCancelTextCursor),
            old_handle, cleared ? 1 : 0);
        context.complete(epoc::error_none);
    }
"""
    text = replace_once(text, old, new, "text cursor implementation")

    old = """        case EWsWinOpSetTextCursor: {
            set_text_cursor(ctx, cmd);
            break;
        }

        case EWsWinOpOrdinalPosition: {
"""
    new = """        case EWsWinOpSetTextCursor:
        case EWsWinOpSetTextCursorClipped: {
            set_text_cursor(ctx, cmd);
            break;
        }

        case EWsWinOpCancelTextCursor: {
            cancel_text_cursor(ctx);
            break;
        }

        case EWsWinOpOrdinalPosition: {
"""
    text = replace_once(text, old, new, "text cursor dispatch")

    for gate in (
        "case EWsWinOpSetTextCursorClipped:",
        "case EWsWinOpCancelTextCursor:",
        "void window_group::cancel_text_cursor",
        "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR:",
        "text_cursor_window_handle = cmd_set->win;",
        "cursor_pos = eka2l1::vec2(-1, -1);",
    ):
        if gate not in text:
            fail(f"implementation gate missing: {gate}")

    wg_cpp.write_text(text, encoding="utf-8")

    print("MENUUI27 TEXTCURSOR1 applied")
    print("0x2E=SetTextCursor_IMPLEMENTED")
    print("0x2F=SetTextCursorClipped_IMPLEMENTED")
    print("0x30=CancelTextCursor_IMPLEMENTED")
    print("clip_rendering=NOT_INVENTED lifecycle_target_semantics=IMPLEMENTED")
    print("CNTSRV=UNCHANGED PenInputAnim=UNCHANGED scheduler=UNCHANGED")
    print("MENUUI26/MENUUI25/MENUUI24/MENUUI23/SCHEDRUN1/MANIC3/NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
