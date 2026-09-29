#!/usr/bin/env python3
"""NATIVEBOOT2 B57 STARTUPGDIORIGIN1.

Diagnostic-only follow-up to B56 DEVICE1.

B56 proves the visible Startup 0x100058F4 canvas replays one REDRAW segment
containing five commands in this exact order:

  CLIP_SINGLE full-screen
  DRAW_BITMAP full-screen BLIT
  CLIP_SINGLE full-screen
  DRAW_RECT full-screen white
  DRAW_RECT full-screen white

The two white DRAW_RECT commands explain the B55/B56 white screen.  The
remaining question is where those commands originate in the guest WindowServer
GC stream and when they are recorded.

B57 traces only Startup-group graphics-context calls that can create the B56
stored commands.  It records process/thread, guest GC opcode, source operation,
canvas/group identity, geometry, brush state, and BLIT variant.

No WindowServer behavior is changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B57-STARTUPGDIORIGIN1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_once(text, old, new, label):
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b57_startupgdiorigin1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/services/src/window/classes/gctx.cpp"
    if not p.is_file():
        fail(f"missing source: {p}")

    text=p.read_text(encoding="utf-8")

    if "[NBOOT2][STARTUP_GDI_ORIGIN]" in text:
        print(MARK+": already applied")
        return

    anchor='''namespace eka2l1::epoc {
'''
    helper='''namespace eka2l1::epoc {
    static bool b57_startup_gc(graphic_context *gc, window_group **group_out = nullptr) {
        if (!gc || !gc->attached_window) {
            return false;
        }

        window_group *group = gc->attached_window->get_group();
        if (group_out) {
            *group_out = group;
        }
        if (!group) {
            return false;
        }

        const std::string name = common::ucs2_to_utf8(group->name);
        return (name.find("100058f4") != std::string::npos) ||
               (name.find("100058F4") != std::string::npos) ||
               (name.find("Startup") != std::string::npos);
    }

'''
    text=rep_once(text,anchor,helper,"helper")

    # Trace brush colour state used by CLEAR/CLEAR_RECT/DRAW_RECT.
    old='''        if (!kern->is_eka1()) {
            // From EKA2, color that passed through the server is 0xaarrggbb. R and B channels are swapped
            // The call that makes the color is TRgb::Internal()
            brush_color = (brush_color & 0xFF00FF00) | ((brush_color & 0xFF) << 16) | ((brush_color & 0xFF0000) >> 16);
        }

        context.complete(epoc::error_none);
    }
'''
    new='''        if (!kern->is_eka1()) {
            // From EKA2, color that passed through the server is 0xaarrggbb. R and B channels are swapped
            // The call that makes the color is TRgb::Internal()
            brush_color = (brush_color & 0xFF00FF00) | ((brush_color & 0xFF) << 16) | ((brush_color & 0xFF0000) >> 16);
        }

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=SET_BRUSH_COLOR process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} brush=0x{:08X} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                static_cast<std::uint32_t>(brush_color));
        }

        context.complete(epoc::error_none);
    }
'''
    text=rep_once(text,old,new,"set_brush_color")

    old='''    void graphic_context::set_brush_style(service::ipc_context &context, ws_cmd &cmd) {
        fill_mode = *reinterpret_cast<brush_style *>(cmd.data_ptr);
        context.complete(epoc::error_none);
    }
'''
    new='''    void graphic_context::set_brush_style(service::ipc_context &context, ws_cmd &cmd) {
        fill_mode = *reinterpret_cast<brush_style *>(cmd.data_ptr);

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=SET_BRUSH_STYLE process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} fill_mode={} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                static_cast<std::uint32_t>(fill_mode));
        }

        context.complete(epoc::error_none);
    }
'''
    text=rep_once(text,old,new,"set_brush_style")

    # Trace BLIT source; B56 command flags=0x8 identifies the generic BLIT path.
    old='''        eka2l1::rect dest_rect;
        dest_rect.top = blt_cmd->pos;
        dest_rect.size = eka2l1::vec2(0, 0);

        do_command_draw_bitmap(context, bmp, source_rect, dest_rect, flags);
    }
'''
    new='''        eka2l1::rect dest_rect;
        dest_rect.top = blt_cmd->pos;
        dest_rect.size = eka2l1::vec2(0, 0);

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=GDI_BLT process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} version={} ws_bitmap={} source_handle=0x{:08X} src=[{},{},{},{}] dst=[{},{},{},{}] flags=0x{:02X} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                ver, ws ? 1 : 0, blt_cmd->handle,
                source_rect.top.x, source_rect.top.y, source_rect.size.x, source_rect.size.y,
                dest_rect.top.x, dest_rect.top.y, dest_rect.size.x, dest_rect.size.y,
                flags);
        }

        do_command_draw_bitmap(context, bmp, source_rect, dest_rect, flags);
    }
'''
    text=rep_once(text,old,new,"gdi_blt_impl")

    # Trace explicit DRAW_RECT.
    old='''    void graphic_context::draw_rect(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area = *reinterpret_cast<eka2l1::rect *>(cmd.data_ptr);

        // Symbian rectangle second vector is the bottom right, not the size
        area.transform_from_symbian_rectangle();
'''
    new='''    void graphic_context::draw_rect(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area = *reinterpret_cast<eka2l1::rect *>(cmd.data_ptr);

        // Symbian rectangle second vector is the bottom right, not the size
        area.transform_from_symbian_rectangle();

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=DRAW_RECT process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} rect=[{},{},{},{}] brush=0x{:08X} fill_mode={} pen=0x{:08X} pen_style={} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                area.top.x, area.top.y, area.size.x, area.size.y,
                static_cast<std::uint32_t>(brush_color),
                static_cast<std::uint32_t>(fill_mode),
                static_cast<std::uint32_t>(pen_color),
                static_cast<std::uint32_t>(line_mode));
        }
'''
    text=rep_once(text,old,new,"draw_rect")

    # Trace CLEAR.
    old='''    void graphic_context::clear(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area(attached_window->pos, attached_window->size());

        if (!area.valid()) {
'''
    new='''    void graphic_context::clear(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area(attached_window->pos, attached_window->size());

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=CLEAR process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} rect=[{},{},{},{}] brush=0x{:08X} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                area.top.x, area.top.y, area.size.x, area.size.y,
                static_cast<std::uint32_t>(brush_color));
        }

        if (!area.valid()) {
'''
    text=rep_once(text,old,new,"clear")

    # Trace CLEAR_RECT.
    old='''    void graphic_context::clear_rect(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area = *reinterpret_cast<eka2l1::rect *>(cmd.data_ptr);

        // Symbian rectangle second vector is the bottom right, not the size
        area.transform_from_symbian_rectangle();

        if (!area.valid()) {
'''
    new='''    void graphic_context::clear_rect(service::ipc_context &context, ws_cmd &cmd) {
        eka2l1::rect area = *reinterpret_cast<eka2l1::rect *>(cmd.data_ptr);

        // Symbian rectangle second vector is the bottom right, not the size
        area.transform_from_symbian_rectangle();

        window_group *b57_group = nullptr;
        if (b57_startup_gc(this, &b57_group)) {
            kernel::thread *b57_thr = context.msg ? context.msg->own_thr : nullptr;
            kernel::process *b57_pr = b57_thr ? b57_thr->owning_process() : nullptr;
            const std::uint32_t b57_uid3 = b57_pr
                ? static_cast<std::uint32_t>(std::get<2>(b57_pr->get_uid_type())) : 0;
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][STARTUP_GDI_ORIGIN] source=CLEAR_RECT process={} uid3=0x{:08X} thread={} gc_op=0x{:X} canvas_handle=0x{:08X} group_id={} group_name={} rect=[{},{},{},{}] brush=0x{:08X} behavior=OBSERVE_ONLY",
                b57_pr ? b57_pr->name() : std::string("<null>"), b57_uid3,
                b57_thr ? b57_thr->name() : std::string("<null>"),
                static_cast<std::uint32_t>(cmd.header.op),
                attached_window ? attached_window->client_handle : 0,
                b57_group ? b57_group->id : 0,
                b57_group ? common::ucs2_to_utf8(b57_group->name) : std::string("<null>"),
                area.top.x, area.top.y, area.size.x, area.size.y,
                static_cast<std::uint32_t>(brush_color));
        }

        if (!area.valid()) {
'''
    text=rep_once(text,old,new,"clear_rect")

    if text.count("[NBOOT2][STARTUP_GDI_ORIGIN]") != 6:
        fail("marker source count mismatch")

    p.write_text(text,encoding="utf-8")
    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_GDI_RECORD_ORIGIN")
    print("behavior_change=NONE")
    print("B56_COMMAND_TRACE=PRESERVED")

if __name__=="__main__":
    main()
