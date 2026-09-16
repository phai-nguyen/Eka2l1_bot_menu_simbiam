#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui14_inputdispatch1.py <upstream-root>")

up = Path(sys.argv[1])

paths = {
    "emulator_view": up / "src/emu/ios/app/EmulatorView.mm",
    "bridge": up / "src/emu/ios/src/emu_bridge.mm",
    "thread": up / "src/emu/ios/src/thread.cpp",
    "launcher": up / "src/emu/ios/src/launcher.cpp",
    "window": up / "src/emu/services/src/window/window.cpp",
    "io": up / "src/emu/services/src/window/io.cpp",
    "fifo": up / "src/emu/services/src/window/fifo.cpp",
    "svc": up / "src/emu/kernel/src/svc.cpp",
    "lib": up / "src/emu/kernel/src/libmanager.cpp",
    "dirs": up / "src/emu/services/src/fs/dirs.cpp",
    "vfs": up / "src/emu/vfs/src/vfs.cpp",
}
for name, p in paths.items():
    if not p.is_file():
        raise SystemExit(f"MENUUI14: required source file missing ({name}): {p}")

src = {name: p.read_text(encoding="utf-8") for name, p in paths.items()}

# Authority gates: MENUUI14 must sit on the real-device-passed MENUUI13 chain.
for marker in [
    "MENUUI13 FS-DIRUID1: KEntryAttAllowUid preserves directory entries",
    "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:",
]:
    if marker not in src["dirs"]:
        raise SystemExit("MENUUI14: missing MENUUI13 FileServer authority marker: " + marker)
if "MENUUI13 FS-DIRUID1: UID probing applies only to regular files" not in src["vfs"]:
    raise SystemExit("MENUUI14: missing MENUUI13 VFS authority marker")

for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COPY:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI11 EP94_MSGCONSTRUCT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=LLE",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
]:
    if marker not in src["svc"]:
        raise SystemExit("MENUUI14: missing preserved svc marker: " + marker)
for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:",
]:
    if marker not in src["lib"]:
        raise SystemExit("MENUUI14: missing preserved libmanager marker: " + marker)

v94_begin = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {"
v93_begin = "    const eka2l1::hle::func_map svc_register_funcs_v93 = {"
a = src["svc"].index(v94_begin)
b = src["svc"].index(v93_begin, a)
v94 = src["svc"][a:b]
if v94.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI14: epoc94 0xAB MessageConstruct authority missing")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI14: epoc94 0xAA must remain unmapped")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI14: epoc94 0xAC MessageKill authority missing")

master_marker = "MENUUI14 INPUTDISPATCH1: diagnostic-only input/event dispatch trace"
if master_marker in "\n".join(src.values()):
    print("MENUUI14 INPUTDISPATCH1 already present")
    raise SystemExit(0)

def replace_once(name, old, new, desc):
    text = src[name]
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"MENUUI14: anchor {desc} in {name} count={count}")
    src[name] = text.replace(old, new, 1)

# 1) UIKit source. This build-time check also tells us whether the frozen MENUUI13
# source really contains the small contiguous _touchSlots fix.
ev = src["emulator_view"]
has_touchslots = "_touchSlots" in ev
if "#include <common/log.h>" not in ev:
    replace_once(
        "emulator_view",
        "#include <ios/emu_bridge.h>\n",
        "#include <ios/emu_bridge.h>\n#include <common/log.h>\n",
        "EmulatorView common/log include",
    )

m = re.search(
    r'(?m)^(?P<indent>\s*)eka2l1::ios::bridge::touch\(x,\s*y,\s*action,\s*(?P<pid>[A-Za-z_][A-Za-z0-9_]*)\);\s*$',
    src["emulator_view"],
)
if not m:
    raise SystemExit("MENUUI14: EmulatorView bridge::touch call anchor not found")
indent = m.group("indent")
pid = m.group("pid")
call = m.group(0).strip()
insert = (
    f'{indent}// {master_marker}\n'
    f'{indent}LOG_WARN(eka2l1::FRONTEND_CMDLINE,\n'
    f'{indent}    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_SRC: x={{}} y={{}} action={{}} pointer={{}} scale={{}} touchslots={1 if has_touchslots else 0}",\n'
    f'{indent}    x, y, static_cast<int>(action), {pid}, static_cast<double>(scale));\n'
    f'{indent}{call}'
)
src["emulator_view"] = src["emulator_view"][:m.start()] + insert + src["emulator_view"][m.end():]

# 2) bridge::touch
old = '''    void touch(int x, int y, touch_action action, int pointer_id) {
        std::lock_guard<std::mutex> guard(g_mutex);
'''
new = '''    void touch(int x, int y, touch_action action, int pointer_id) {
        // MENUUI14 INPUTDISPATCH1: bridge trace only; no input semantics changed.
        LOG_WARN(FRONTEND_CMDLINE,
            "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_BRIDGE: x={} y={} action={} pointer={} running={} state={}",
            x, y, static_cast<int>(action), pointer_id, g_running ? 1 : 0, g_state ? 1 : 0);
        std::lock_guard<std::mutex> guard(g_mutex);
'''
replace_once("bridge", old, new, "bridge touch")

# 3) iOS driver event construction.
old = '''    void touch_screen(emulator &state, int x, int y, int z, int action, int pointer_id) {
        if (!state.winserv) {
            return;
        }
        eka2l1::drivers::input_event evt;
'''
new = '''    void touch_screen(emulator &state, int x, int y, int z, int action, int pointer_id) {
        if (!state.winserv) {
            LOG_WARN(FRONTEND_CMDLINE,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_DRIVER: drop=no_winserv x={} y={} action={} pointer={}",
                x, y, action, pointer_id);
            return;
        }
        // MENUUI14 INPUTDISPATCH1: diagnostic-only driver event construction trace.
        LOG_WARN(FRONTEND_CMDLINE,
            "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_DRIVER: x={} y={} z={} action={} pointer={} winserv=1",
            x, y, z, action, pointer_id);
        eka2l1::drivers::input_event evt;
'''
replace_once("thread", old, new, "touch_screen entry")

# 4) Rendered destination rect. Log only when geometry changes to avoid per-frame spam.
old = '''            drivers::advance_draw_pos_around_origin(dest, scr->ui_rotation);

            if (scr->ui_rotation % 180 != 0) {
'''
new = '''            drivers::advance_draw_pos_around_origin(dest, scr->ui_rotation);

            // MENUUI14 INPUTDISPATCH1: compare actual post-rotation draw origin with
            // WindowServer's pre-rotation absolute_pos used by host touch hit-testing.
            static int menuui14_last_abs_x = -0x7fffffff;
            static int menuui14_last_abs_y = -0x7fffffff;
            static int menuui14_last_dest_x = -0x7fffffff;
            static int menuui14_last_dest_y = -0x7fffffff;
            static int menuui14_last_rot = -1;
            const int menuui14_dest_x = static_cast<int>(dest.top.x);
            const int menuui14_dest_y = static_cast<int>(dest.top.y);
            if (menuui14_last_abs_x != scr->absolute_pos.x ||
                menuui14_last_abs_y != scr->absolute_pos.y ||
                menuui14_last_dest_x != menuui14_dest_x ||
                menuui14_last_dest_y != menuui14_dest_y ||
                menuui14_last_rot != scr->ui_rotation) {
                LOG_WARN(FRONTEND_CMDLINE,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_RENDER: abs=({}, {}) dest_after_rotate=({}, {}) size_before_swap=({}, {}) rot={} logic_scale=({}, {}) fb=({}, {})",
                    scr->absolute_pos.x, scr->absolute_pos.y,
                    menuui14_dest_x, menuui14_dest_y,
                    static_cast<int>(dest.size.x), static_cast<int>(dest.size.y),
                    scr->ui_rotation,
                    static_cast<double>(scr->logic_scale_factor_x),
                    static_cast<double>(scr->logic_scale_factor_y),
                    window_width, window_height);
                menuui14_last_abs_x = scr->absolute_pos.x;
                menuui14_last_abs_y = scr->absolute_pos.y;
                menuui14_last_dest_x = menuui14_dest_x;
                menuui14_last_dest_y = menuui14_dest_y;
                menuui14_last_rot = scr->ui_rotation;
            }

            if (scr->ui_rotation % 180 != 0) {
'''
replace_once("launcher", old, new, "launcher post-rotation destination")

# 5a) WindowServer driver ingress.
old = '''    void window_server::queue_input_from_driver(drivers::input_event &evt) {
        if (!loaded) {
            return;
        }

        evt.time_ = kern->universal_time();

        handle_input_from_driver(evt);
    }
'''
new = '''    void window_server::queue_input_from_driver(drivers::input_event &evt) {
        if (!loaded) {
            if (evt.type_ == drivers::input_event_type::touch) {
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_QUEUE: drop=server_not_loaded host=({}, {}) action={} pointer={}",
                    evt.mouse_.pos_x_, evt.mouse_.pos_y_, static_cast<int>(evt.mouse_.action_), evt.mouse_.mouse_id);
            }
            return;
        }

        evt.time_ = kern->universal_time();

        if (evt.type_ == drivers::input_event_type::touch) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_QUEUE: host=({}, {}) action={} pointer={} raw={} loaded=1",
                evt.mouse_.pos_x_, evt.mouse_.pos_y_, static_cast<int>(evt.mouse_.action_), evt.mouse_.mouse_id,
                evt.mouse_.raw_screen_pos_ ? 1 : 0);
        }

        handle_input_from_driver(evt);
    }
'''
replace_once("window", old, new, "queue_input_from_driver")

# 5b) Guest pointer mapping after scale/rotation.
old = '''        // use on debugging
        // LOG_TRACE(SERVICE_WINDOW, "touch position ({}, {}), type {}", guest_evt_.adv_pointer_evt_.pos.x, guest_evt_.adv_pointer_evt_.pos.y, guest_evt_.adv_pointer_evt_.evtype);
        scr->screen_mutex.unlock();
'''
new = '''        // MENUUI14 INPUTDISPATCH1: record the exact guest pointer produced by
        // scale + rotation mapping. Diagnostic only.
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_POINTER: guest=({}, {}) original=({}, {}) evtype={} pointer={} rot={} raw={}",
            guest_evt_.adv_pointer_evt_.pos.x, guest_evt_.adv_pointer_evt_.pos.y,
            orgx, orgy, static_cast<int>(guest_evt_.adv_pointer_evt_.evtype),
            guest_evt_.adv_pointer_evt_.ptr_num, scr->ui_rotation,
            driver_evt_.mouse_.raw_screen_pos_ ? 1 : 0);

        // use on debugging
        // LOG_TRACE(SERVICE_WINDOW, "touch position ({}, {}), type {}", guest_evt_.adv_pointer_evt_.pos.x, guest_evt_.adv_pointer_evt_.pos.y, guest_evt_.adv_pointer_evt_.evtype);
        scr->screen_mutex.unlock();
'''
replace_once("window", old, new, "make_mouse_event mapped pointer")

# 5c) Host-space screen rect decision.
old = '''            eka2l1::rect screen_rect(scr->absolute_pos, screen_size_scaled);

            if (!input_event.mouse_.raw_screen_pos_ && (input_event.mouse_.action_ == drivers::mouse_action_release)) {
'''
new = '''            eka2l1::rect screen_rect(scr->absolute_pos, screen_size_scaled);

            // MENUUI14 INPUTDISPATCH1: host-space hit rectangle before any release clamp.
            const bool menuui14_inside_before_clamp = input_event.mouse_.raw_screen_pos_ ||
                screen_rect.contains(eka2l1::point(input_event.mouse_.pos_x_, input_event.mouse_.pos_y_));
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_SCREEN: host=({}, {}) abs=({}, {}) scaled=({}, {}) mode=({}, {}) scale=({}, {}) rot={} action={} raw={} inside_before_clamp={}",
                input_event.mouse_.pos_x_, input_event.mouse_.pos_y_,
                scr->absolute_pos.x, scr->absolute_pos.y,
                screen_size_scaled.x, screen_size_scaled.y,
                scr->current_mode().size.x, scr->current_mode().size.y,
                static_cast<double>(scr->logic_scale_factor_x),
                static_cast<double>(scr->logic_scale_factor_y),
                scr->ui_rotation, static_cast<int>(input_event.mouse_.action_),
                input_event.mouse_.raw_screen_pos_ ? 1 : 0,
                menuui14_inside_before_clamp ? 1 : 0);

            if (!input_event.mouse_.raw_screen_pos_ && (input_event.mouse_.action_ == drivers::mouse_action_release)) {
'''
replace_once("window", old, new, "touch screen_rect")

# 5d) If touch is rejected after clamp/hit test, state it explicitly.
old = '''                shipped = true;
            }

            break;
        }
'''
new = '''                shipped = true;
            } else {
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_SCREEN_DROP: host=({}, {}) action={} pointer={} reason=outside_screen_rect",
                    input_event.mouse_.pos_x_, input_event.mouse_.pos_y_,
                    static_cast<int>(input_event.mouse_.action_), input_event.mouse_.mouse_id);
            }

            break;
        }
'''
replace_once("window", old, new, "touch outside-screen branch")

# 6) HLE hit-test and target selection.
if "#include <common/log.h>" not in src["io"]:
    replace_once(
        "io",
        "#include <kernel/kernel.h>\n",
        "#include <kernel/kernel.h>\n#include <common/log.h>\n",
        "io common/log include",
    )

old = '''        evt.handle = win->get_client_handle();

        kernel_system *kern = win->client->get_ws().get_kernel_system();

        kern->lock();
        win->queue_event(evt);
        kern->unlock();
'''
new = '''        evt.handle = win->get_client_handle();

        kernel_system *kern = win->client->get_ws().get_kernel_system();
        const std::uint64_t menuui14_thread =
            win->client->get_client() ? win->client->get_client()->unique_id() : 0;

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_HIT: target_handle={} client_thread={} global=({}, {}) local=({}, {}) parent=({}, {}) evtype={} pointer={}",
            evt.handle, menuui14_thread,
            scr_coord_.x, scr_coord_.y,
            evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
            evt.adv_pointer_evt_.parent_pos.x, evt.adv_pointer_evt_.parent_pos.y,
            static_cast<int>(evt.adv_pointer_evt_.evtype), evt.adv_pointer_evt_.ptr_num);
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_FIFO_ENQUEUE: target_handle={} client_thread={} event_type={} evtype={} pointer={}",
            evt.handle, menuui14_thread, static_cast<int>(evt.type),
            static_cast<int>(evt.adv_pointer_evt_.evtype), evt.adv_pointer_evt_.ptr_num);

        kern->lock();
        win->queue_event(evt);
        kern->unlock();
'''
replace_once("io", old, new, "pointer target queue")

old = '''        for (auto &[evt, sent_to_highest_z] : evts_) {
            // Is this event really in the pointer area, if area exists. If not, pass
            if (contain_area && !contain_area->contains(evt.adv_pointer_evt_.pos)) {
                continue;
            }
'''
new = '''        for (auto &[evt, sent_to_highest_z] : evts_) {
            const bool menuui14_pointer_area_ok =
                !contain_area || contain_area->contains(evt.adv_pointer_evt_.pos);
            const bool menuui14_visible_hit =
                user->visible_region.contains(evt.adv_pointer_evt_.pos);
            const std::uint64_t menuui14_thread =
                win->client->get_client() ? win->client->get_client()->unique_id() : 0;
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_HITTEST: handle={} client_thread={} pos=({}, {}) sent={} pointer_area_ok={} visible_hit={} filter=0x{:X}",
                win->get_client_handle(), menuui14_thread,
                evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
                sent_to_highest_z ? 1 : 0,
                menuui14_pointer_area_ok ? 1 : 0,
                menuui14_visible_hit ? 1 : 0,
                static_cast<std::uint32_t>(user->filter));

            // Keep MENUUI13 behavior unchanged: this currently drops an event outside
            // PointerCursorArea, even though real WSERV clamps coordinates. MENUUI14 only traces it.
            if (contain_area && !contain_area->contains(evt.adv_pointer_evt_.pos)) {
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_POINTERAREA_DROP: handle={} client_thread={} pos=({}, {})",
                    win->get_client_handle(), menuui14_thread,
                    evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y);
                continue;
            }
'''
replace_once("io", old, new, "pointer walker hit-test")

# 7) FIFO queue + listener wake. Preserve queueing semantics apart from logging.
old = '''        std::uint32_t result = queue_event_dont_care(evt);
        trigger_notification();

        return result;
'''
new = '''        std::uint32_t result = queue_event_dont_care(evt);
        if (evt.type == epoc::event_code::touch) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_FIFO: handle={} evtype={} pointer={} qsize={} listener_pending={}",
                evt.handle, static_cast<int>(evt.adv_pointer_evt_.evtype),
                evt.adv_pointer_evt_.ptr_num, q_.size(), nof.empty() ? 0 : 1);
        }
        trigger_notification();
        if (evt.type == epoc::event_code::touch) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_WAKE: handle={} evtype={} pointer={} trigger_notification=1",
                evt.handle, static_cast<int>(evt.adv_pointer_evt_.evtype),
                evt.adv_pointer_evt_.ptr_num);
        }

        return result;
'''
replace_once("fifo", old, new, "event fifo trigger")

# 8a) EventReady arm on the owning WindowServer client.
old = '''        switch (list_type) {
        case event_listener_type_redraw:
'''
new = '''        if (list_type == event_listener_type_event) {
            const std::uint64_t menuui14_client_thread =
                client_thread ? client_thread->unique_id() : 0;
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_EVENTREADY_ARM: client_thread={} inline_status={} cmd_len={}",
                menuui14_client_thread, should_finish ? 1 : 0,
                cmd ? static_cast<int>(cmd->header.cmd_len) : -1);
        }

        switch (list_type) {
        case event_listener_type_redraw:
'''
replace_once("window", old, new, "EventReady arm")

# 8b) GetEvent result, including client identity.
old = '''    void window_server_client::get_event(service::ipc_context &ctx, ws_cmd &cmd) {
        auto evt = events.get_event();

        // Allow the context to shrink if needed, since the struct certainly got larger as Symbian
'''
new = '''    void window_server_client::get_event(service::ipc_context &ctx, ws_cmd &cmd) {
        auto evt = events.get_event();

        const std::uint64_t menuui14_client_thread =
            client_thread ? client_thread->unique_id() : 0;
        if (evt.type == epoc::event_code::touch) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_GET: client_thread={} type={} handle={} evtype={} pointer={} pos=({}, {}) parent=({}, {})",
                menuui14_client_thread, static_cast<int>(evt.type), evt.handle,
                static_cast<int>(evt.adv_pointer_evt_.evtype), evt.adv_pointer_evt_.ptr_num,
                evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
                evt.adv_pointer_evt_.parent_pos.x, evt.adv_pointer_evt_.parent_pos.y);
        } else if (evt.type != epoc::event_code::null) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_GET: client_thread={} type={} handle={} non_touch=1",
                menuui14_client_thread, static_cast<int>(evt.type), evt.handle);
        }

        // Allow the context to shrink if needed, since the struct certainly got larger as Symbian
'''
replace_once("window", old, new, "GetEvent trace")

# Postconditions: diagnostic-only marker coverage and preserved authority.
expected = {
    "emulator_view": ["MENUUI14 INPUT_SRC:"],
    "bridge": ["MENUUI14 INPUT_BRIDGE:"],
    "thread": ["MENUUI14 INPUT_DRIVER:"],
    "launcher": ["MENUUI14 INPUT_RENDER:"],
    "window": [
        "MENUUI14 INPUT_QUEUE:", "MENUUI14 INPUT_POINTER:", "MENUUI14 INPUT_SCREEN:",
        "MENUUI14 INPUT_SCREEN_DROP:", "MENUUI14 INPUT_EVENTREADY_ARM:", "MENUUI14 INPUT_GET:",
    ],
    "io": [
        "MENUUI14 INPUT_HITTEST:", "MENUUI14 INPUT_HIT:", "MENUUI14 INPUT_FIFO_ENQUEUE:",
        "MENUUI14 INPUT_POINTERAREA_DROP:",
    ],
    "fifo": ["MENUUI14 INPUT_FIFO:", "MENUUI14 INPUT_WAKE:"],
}
for name, markers in expected.items():
    for marker in markers:
        if src[name].count(marker) != 1:
            raise SystemExit(f"MENUUI14: marker postcondition failed {name}: {marker}")

# Re-check authority in unmodified SVC table.
a = src["svc"].index(v94_begin)
b = src["svc"].index(v93_begin, a)
v94_after = src["svc"][a:b]
assert v94_after.count("BRIDGE_REGISTER(0xAB, message_construct)") == 1
assert "BRIDGE_REGISTER(0xAA," not in v94_after
assert v94_after.count("BRIDGE_REGISTER(0xAC, message_kill)") == 1

# Only write files that MENUUI14 intentionally instruments.
for name in ("emulator_view", "bridge", "thread", "launcher", "window", "io", "fifo"):
    paths[name].write_text(src[name], encoding="utf-8")

print("MENUUI14 INPUTDISPATCH1 diagnostic-only patch applied")
print(f"MENUUI14 frozen-source audit: EmulatorView _touchSlots={'PRESENT' if has_touchslots else 'ABSENT'}")
