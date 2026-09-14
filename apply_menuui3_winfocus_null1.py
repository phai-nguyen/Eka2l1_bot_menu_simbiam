#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui3_winfocus_null1.py <upstream-root>")

up = Path(sys.argv[1])
path = up / "src/emu/services/src/window/window.cpp"
text = path.read_text(encoding="utf-8")

sig = "    void window_server_client::get_focus_window_group(service::ipc_context &ctx, ws_cmd &cmd) {"
next_sig = "\n    void window_server_client::get_window_group_name_from_id(service::ipc_context &ctx, ws_cmd &cmd) {"

start = text.find(sig)
if start < 0:
    raise SystemExit("MENUUI3: get_focus_window_group signature not found")
end = text.find(next_sig, start)
if end < 0:
    raise SystemExit("MENUUI3: get_focus_window_group end anchor not found")

old = text[start:end]
marker = "SYMBIAN-SYSTEMAPPS1 MENUUI3 WINFOCUS NULL:"

if marker in old:
    print("MENUUI3 WINFOCUS NULL1 already present")
    raise SystemExit(0)

required_old = [
    "ctx.complete(get_ws().get_current_focus_screen()->focus->id);",
    "epoc::screen *scr = get_ws().get_screen(screen_num);",
    "ctx.complete(scr->focus->id);",
]
missing = [item for item in required_old if item not in old]
if missing:
    raise SystemExit("MENUUI3: unexpected pre-patch WINFOCUS body: " + ", ".join(missing))

new = '''    void window_server_client::get_focus_window_group(service::ipc_context &ctx, ws_cmd &cmd) {
        // TODO: Epoc < 9
        if (cmd.header.cmd_len == 0) {
            epoc::screen *scr = get_ws().get_current_focus_screen();

            if (!scr || !scr->focus) {
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI3 WINFOCUS NULL: mode=implicit cmd_len={} screen={} return=0",
                    cmd.header.cmd_len, scr ? scr->number : -1);
                ctx.complete(0);
                return;
            }

            LOG_INFO(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI3 WINFOCUS: mode=implicit cmd_len={} screen={} focus_id={}",
                cmd.header.cmd_len, scr->number, scr->focus->id);
            ctx.complete(scr->focus->id);
            return;
        }

        int screen_num = *reinterpret_cast<int *>(cmd.data_ptr);
        epoc::screen *scr = get_ws().get_screen(screen_num);

        if (!scr) {
            LOG_ERROR(SERVICE_WINDOW, "Invalid screen number {}", screen_num);
            ctx.complete(epoc::error_argument);
            return;
        }

        if (!scr->focus) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI3 WINFOCUS NULL: mode=explicit cmd_len={} screen={} return=0",
                cmd.header.cmd_len, screen_num);
            ctx.complete(0);
            return;
        }

        LOG_INFO(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI3 WINFOCUS: mode=explicit cmd_len={} screen={} focus_id={}",
            cmd.header.cmd_len, screen_num, scr->focus->id);
        ctx.complete(scr->focus->id);
    }
'''

text = text[:start] + new + text[end:]
path.write_text(text, encoding="utf-8")

if marker not in path.read_text(encoding="utf-8"):
    raise SystemExit("MENUUI3: marker verification failed")
print("MENUUI3 WINFOCUS NULL1 patch applied")
