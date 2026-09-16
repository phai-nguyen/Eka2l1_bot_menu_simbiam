#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui15_eventsem1.py <upstream-root>")

up = Path(sys.argv[1])
paths = {
    "window": up / "src/emu/services/src/window/window.cpp",
    "io": up / "src/emu/services/src/window/io.cpp",
    "winuser": up / "src/emu/services/src/window/classes/winuser.cpp",
    "op": up / "src/emu/services/include/services/window/op.h",
}
for name, path in paths.items():
    if not path.is_file():
        raise SystemExit(f"MENUUI15: required source missing ({name}): {path}")

src = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}

# MENUUI15 must layer on the device-tested MENUUI14 diagnostic build without
# changing input/event semantics.
for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_HIT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_GET:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_POINTER:",
]:
    if marker not in "\n".join(src.values()):
        raise SystemExit("MENUUI15: missing MENUUI14 authority marker: " + marker)

if "EWsWinOpEnableAdvancedPointers" not in src["op"]:
    raise SystemExit("MENUUI15: frozen op.h has no EWsWinOpEnableAdvancedPointers declaration")
if "case EWsWinOpEnableAdvancedPointers:" in src["winuser"]:
    raise SystemExit("MENUUI15: EnableAdvancedPointers is already handled; static premise changed")

master = "MENUUI15 EVENTSEM1: diagnostic-only post-GetEvent/pointer-semantics trace"
if master in "\n".join(src.values()):
    print("MENUUI15 EVENTSEM1 already present")
    raise SystemExit(0)

# 1) Log the complete pointer payload at the selected HLE target.  This records
# the target window, its parent/group, geometry, filter state and the advanced
# pointer modifier without changing the event.
io = src["io"]
hit_marker = '"SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_HIT:'
hit_pos = io.find(hit_marker)
if hit_pos < 0:
    raise SystemExit("MENUUI15: MENUUI14 INPUT_HIT anchor missing")
lock_pos = io.find("        kern->lock();", hit_pos)
if lock_pos < 0:
    raise SystemExit("MENUUI15: target kern->lock anchor missing")

target_trace = '''        // MENUUI15 EVENTSEM1: diagnostic-only target/event semantics trace.
        epoc::window_group *menuui15_group = user->get_group();
        const std::uint64_t menuui15_group_thread =
            (menuui15_group && menuui15_group->client->get_client())
                ? menuui15_group->client->get_client()->unique_id() : 0;
        const eka2l1::rect menuui15_abs = user->absolute_rect();
        const std::uint32_t menuui15_parent_id = win->parent ? win->parent->id : 0;
        const std::uint32_t menuui15_parent_handle = win->parent ? win->parent->get_client_handle() : 0;
        const int menuui15_parent_kind = win->parent ? static_cast<int>(win->parent->type) : -1;
        const bool menuui15_adv =
            (evt.adv_pointer_evt_.modifier & epoc::event_modifier_adv_pointer) != 0;
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_TARGET: win_id={} handle={} client_thread={} kind={} priority={} flags=0x{:X} abs=({}, {}) size=({}, {}) filter=0x{:X} visible_rects={} parent_id={} parent_handle={} parent_kind={} group_id={} group_handle={} group_priority={} group_thread={} modifier=0x{:X} advanced={} evtype={} pointer={} global=({}, {}) local=({}, {}) parent_pos=({}, {})",
            win->id, evt.handle, menuui14_thread, static_cast<int>(win->type), win->priority, win->flags,
            menuui15_abs.top.x, menuui15_abs.top.y, menuui15_abs.size.x, menuui15_abs.size.y,
            user->filter, user->visible_region.rects_.size(),
            menuui15_parent_id, menuui15_parent_handle, menuui15_parent_kind,
            menuui15_group ? menuui15_group->id : 0,
            menuui15_group ? menuui15_group->get_client_handle() : 0,
            menuui15_group ? menuui15_group->priority : 0,
            menuui15_group_thread,
            evt.adv_pointer_evt_.modifier, menuui15_adv ? 1 : 0,
            static_cast<int>(evt.adv_pointer_evt_.evtype), evt.adv_pointer_evt_.ptr_num,
            scr_coord_.x, scr_coord_.y,
            evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
            evt.adv_pointer_evt_.parent_pos.x, evt.adv_pointer_evt_.parent_pos.y);

'''
io = io[:lock_pos] + target_trace + io[lock_pos:]
src["io"] = io

# 2) Log the full pointer payload exactly when RWsSession::GetEvent dequeues it.
window = src["window"]
get_marker = '"SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_GET:'
get_pos = window.find(get_marker)
if get_pos < 0:
    raise SystemExit("MENUUI15: MENUUI14 INPUT_GET anchor missing")
write_comment = window.find("        // Allow the context to shrink if needed", get_pos)
if write_comment < 0:
    raise SystemExit("MENUUI15: GetEvent descriptor-write anchor missing")

get_trace = '''        // MENUUI15 EVENTSEM1: preserve the event and expose all pointer fields
        // immediately before descriptor copy to the guest.
        if (evt.type == epoc::event_code::touch) {
            const bool menuui15_adv =
                (evt.adv_pointer_evt_.modifier & epoc::event_modifier_adv_pointer) != 0;
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_GET_FULL: client_thread={} sizeof_event={} type={} handle={} time={} evtype={} modifier=0x{:X} advanced={} pos=({}, {}) parent=({}, {}) pos_z={} pointer={}",
                menuui14_client_thread, sizeof(epoc::event), static_cast<int>(evt.type), evt.handle,
                evt.time, static_cast<int>(evt.adv_pointer_evt_.evtype), evt.adv_pointer_evt_.modifier,
                menuui15_adv ? 1 : 0,
                evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
                evt.adv_pointer_evt_.parent_pos.x, evt.adv_pointer_evt_.parent_pos.y,
                evt.adv_pointer_evt_.pos_z, evt.adv_pointer_evt_.ptr_num);
        }

'''
window = window[:write_comment] + get_trace + window[write_comment:]
src["window"] = window

# 3) Observe whether S60v5 clients actually issue EnableAdvancedPointers or
# SendAdvancedPointerEvent.  Do not complete or consume the command here; the
# existing implementation continues unchanged into its normal switch/default path.
winuser = src["winuser"]
func = winuser.find("    bool canvas_base::execute_command_detail(service::ipc_context &ctx, ws_cmd &cmd, bool &did_it) {")
if func < 0:
    raise SystemExit("MENUUI15: canvas_base::execute_command_detail anchor missing")
op_decl = winuser.find("        TWsWindowOpcodes op = static_cast<decltype(op)>(cmd.header.op);", func)
if op_decl < 0:
    raise SystemExit("MENUUI15: TWsWindowOpcodes declaration anchor missing")
switch_pos = winuser.find("        switch (op) {", op_decl)
if switch_pos < 0:
    raise SystemExit("MENUUI15: canvas_base opcode switch anchor missing")

opcode_trace = '''        // MENUUI15 EVENTSEM1: diagnostic-only.  The frozen fork declares
        // EWsWinOpEnableAdvancedPointers but has no case handler for it.
        if ((op == EWsWinOpEnableAdvancedPointers) || (op == EWsWinOpSendAdvancedPointerEvent)) {
            const std::uint64_t menuui15_thread =
                (client && client->get_client()) ? client->get_client()->unique_id() : 0;
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI15 ADV_OPCODE: win_id={} handle={} client_thread={} opcode={} cmd_len={} enable_adv={} send_adv={} base_handler_present=0",
                id, get_client_handle(), menuui15_thread, static_cast<int>(op), cmd.header.cmd_len,
                op == EWsWinOpEnableAdvancedPointers ? 1 : 0,
                op == EWsWinOpSendAdvancedPointerEvent ? 1 : 0);
        }

'''
winuser = winuser[:switch_pos] + opcode_trace + winuser[switch_pos:]
src["winuser"] = winuser

# Add a durable marker next to the first runtime trace.
src["io"] = src["io"].replace(
    "        // MENUUI15 EVENTSEM1: diagnostic-only target/event semantics trace.\n",
    f"        // {master}\n        // MENUUI15 EVENTSEM1: diagnostic-only target/event semantics trace.\n",
    1,
)

expected = {
    "io": ["MENUUI15 EVENT_TARGET:", master],
    "window": ["MENUUI15 EVENT_GET_FULL:"],
    "winuser": ["MENUUI15 ADV_OPCODE:"],
}
for name, markers in expected.items():
    for marker in markers:
        count = src[name].count(marker)
        if count != 1:
            raise SystemExit(f"MENUUI15: marker postcondition failed {name}: {marker} count={count}")

# This patch intentionally must not add a handler for EnableAdvancedPointers.
if "case EWsWinOpEnableAdvancedPointers:" in src["winuser"]:
    raise SystemExit("MENUUI15: diagnostic patch accidentally implemented EnableAdvancedPointers")

for name, path in paths.items():
    if name in src:
        path.write_text(src[name], encoding="utf-8")

print("MENUUI15 EVENTSEM1 diagnostic-only traces applied")
print("MENUUI15 static gate: EWsWinOpEnableAdvancedPointers declared, base handler absent")
