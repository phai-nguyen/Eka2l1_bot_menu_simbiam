#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui17_alfroute1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
window_path = up / "src/emu/services/src/window/window.cpp"
for path in (svc_path, window_path):
    if not path.is_file():
        raise SystemExit(f"MENUUI17 FIX5: required source missing: {path}")

svc = svc_path.read_text(encoding="utf-8")
window = window_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_GET_FULL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI16 ADVFLAG1:",
]
joined = svc + "\n" + window
for marker in required:
    if marker not in joined:
        raise SystemExit("MENUUI17 FIX5: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY:": 2,
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_WORD:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_FRAME:": 1,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI17 ALFROUTE1 FIX5 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI17 FIX5: partial prior patch detected")

behavior_tokens = [
    "kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());",
    "do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset)",
    "msg->unref();",
    "kern->call_ipc_complete_callbacks(msg, val);",
    "msg->own_thr->signal_request();",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

server_name_literal = "10282845_10282845_AppServer"
menu_uid = "0x101F4CD2U"

# 1) Mark the asynchronous Menu -> Alfred pointer request arm (opcode 7).
send_call = "        kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());\n"
if svc.count(send_call) != 1:
    raise SystemExit(f"MENUUI17 FIX5: IPC send anchor count={svc.count(send_call)}")
arm_trace = r'''        // MENUUI17 ALFROUTE1: diagnostic-only EAlfGetPointerEvent arm marker.
        kernel::process *menuui17_arm_pr = kern->crr_process();
        kernel::thread *menuui17_arm_thr = kern->crr_thread();
        if (menuui17_arm_pr && menuui17_arm_thr
            && server_name == "10282845_10282845_AppServer" && ord == 7) {
            const auto menuui17_arm_uids = menuui17_arm_pr->get_uid_type();
            const std::uint32_t menuui17_arm_uid3 =
                static_cast<std::uint32_t>(std::get<2>(menuui17_arm_uids));
            if (menuui17_arm_uid3 == 0x101F4CD2U) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM: client_process={} client_thread={} uid=0x{:08X} server={} opcode={} sync={} status=0x{:08X} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X}",
                    menuui17_arm_pr->name(), menuui17_arm_thr->name(), menuui17_arm_uid3,
                    server_name, ord, sync ? 1 : 0, status.ptr_address(),
                    static_cast<std::uint32_t>(arg.flag),
                    static_cast<std::uint32_t>(arg.args[0]),
                    static_cast<std::uint32_t>(arg.args[1]),
                    static_cast<std::uint32_t>(arg.args[2]),
                    static_cast<std::uint32_t>(arg.args[3]));
            }
        }

'''
svc = svc.replace(send_call, arm_trace + send_call, 1)


def pred(prefix: str) -> str:
    return f'''        kernel::process *{prefix}_client_pr =\n            (msg && msg->own_thr) ? msg->own_thr->owning_process() : nullptr;\n        std::uint32_t {prefix}_client_uid3 = 0;\n        if ({prefix}_client_pr) {{\n            const auto {prefix}_uids = {prefix}_client_pr->get_uid_type();\n            {prefix}_client_uid3 = static_cast<std::uint32_t>(std::get<2>({prefix}_uids));\n        }}\n        const bool {prefix}_match = msg && msg->msg_session && msg->msg_session->get_server()\n            && msg->msg_session->get_server()->name() == "{server_name_literal}"\n            && msg->function == 7 && {prefix}_client_uid3 == {menu_uid};\n'''

# 2) Instrument only EKA2 message_ipc_copy(), never the later EKA1 variant.
eka2_sig = "    BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
eka1_sig = "    BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
eka2_pos = svc.find(eka2_sig)
eka1_pos = svc.find(eka1_sig)
if svc.count(eka2_sig) != 1 or svc.count(eka1_sig) != 1 or eka2_pos < 0 or eka1_pos <= eka2_pos:
    raise SystemExit(
        "MENUUI17 FIX5: message_ipc_copy layout changed: "
        f"eka2_count={svc.count(eka2_sig)} eka1_count={svc.count(eka1_sig)} "
        f"eka2_pos={eka2_pos} eka1_pos={eka1_pos}"
    )
eka2 = svc[eka2_pos:eka1_pos]

ref_anchor = "        msg->ref();\n"
if eka2.count(ref_anchor) != 1:
    raise SystemExit(f"MENUUI17 FIX5: EKA2 msg->ref anchor count={eka2.count(ref_anchor)}")
copy_entry = pred("menuui17_copy") + r'''        if (menuui17_copy_match) {
            kernel::process *menuui17_server_pr = kern->crr_process();
            kernel::thread *menuui17_server_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY: stage=enter msg_id={} msg_handle={} server_process={} server_thread={} client_process={} client_thread={} opcode={} param={} flags=0x{:08X} direction_write={} target_len={} start_offset={} request_status=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X}",
                msg->id, static_cast<std::uint32_t>(h),
                menuui17_server_pr ? menuui17_server_pr->name() : std::string("<null>"),
                menuui17_server_thr ? menuui17_server_thr->name() : std::string("<null>"),
                menuui17_copy_client_pr ? menuui17_copy_client_pr->name() : std::string("<null>"),
                msg->own_thr ? msg->own_thr->name() : std::string("<null>"),
                msg->function, param,
                info_host ? static_cast<std::uint32_t>(info_host->flags) : 0U,
                (info_host && (info_host->flags & IPC_DIR_WRITE)) ? 1 : 0,
                info_host ? info_host->target_length : -1, start_offset,
                msg->request_sts.ptr_address(),
                static_cast<std::uint32_t>(msg->args.args[0]),
                static_cast<std::uint32_t>(msg->args.args[1]),
                static_cast<std::uint32_t>(msg->args.args[2]),
                static_cast<std::uint32_t>(msg->args.args[3]));
        }

'''
eka2 = eka2.replace(ref_anchor, copy_entry + ref_anchor, 1)

result_line = "        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n"
if eka2.count(result_line) != 1:
    raise SystemExit(f"MENUUI17 FIX5: EKA2 result line count={eka2.count(result_line)}")
copy_after_result = r'''        if (menuui17_copy_match) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY: stage=result msg_id={} result={} param={} flags=0x{:08X} direction_write={} target_len={} start_offset={}",
                msg->id, result, param, static_cast<std::uint32_t>(info_host->flags),
                (info_host->flags & IPC_DIR_WRITE) ? 1 : 0,
                info_host->target_length, start_offset);

            // Dump raw TAlfTouchEventS candidate words without changing the copy.
            if ((info_host->flags & IPC_DIR_WRITE) && info_host->target_length > 0) {
                std::uint8_t *menuui17_payload = info_host->target_ptr.get(crr_process);
                if (menuui17_payload) {
                    const std::uint32_t menuui17_raw_words =
                        static_cast<std::uint32_t>(info_host->target_length) / 4U;
                    const std::uint32_t menuui17_words =
                        (menuui17_raw_words < 32U) ? menuui17_raw_words : 32U;
                    for (std::uint32_t menuui17_i = 0; menuui17_i < menuui17_words; ++menuui17_i) {
                        const std::uint32_t menuui17_o = menuui17_i * 4U;
                        const std::uint32_t menuui17_word =
                            static_cast<std::uint32_t>(menuui17_payload[menuui17_o])
                            | (static_cast<std::uint32_t>(menuui17_payload[menuui17_o + 1U]) << 8U)
                            | (static_cast<std::uint32_t>(menuui17_payload[menuui17_o + 2U]) << 16U)
                            | (static_cast<std::uint32_t>(menuui17_payload[menuui17_o + 3U]) << 24U);
                        LOG_WARN(KERNEL,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_WORD: msg_id={} index={} byte_offset={} value=0x{:08X}",
                            msg->id, menuui17_i, menuui17_o, menuui17_word);
                    }
                }
            }
        }
'''
eka2 = eka2.replace(result_line, result_line + copy_after_result, 1)
svc = svc[:eka2_pos] + eka2 + svc[eka1_pos:]

# 3) Instrument message_complete() by function boundary, not a fragile multi-line tail.
complete_sig = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n"
complete_pos = svc.find(complete_sig)
if svc.count(complete_sig) != 1 or complete_pos < 0:
    raise SystemExit(f"MENUUI17 FIX5: message_complete signature count={svc.count(complete_sig)}")
next_bridge = svc.find("\n    BRIDGE_FUNC(", complete_pos + len(complete_sig))
if next_bridge < 0:
    raise SystemExit("MENUUI17 FIX5: cannot find end of message_complete")
complete = svc[complete_pos:next_bridge]
msg_line = "        ipc_msg_ptr msg = kern->get_msg(msg_handle);\n"
if complete.count(msg_line) != 1:
    raise SystemExit(f"MENUUI17 FIX5: message_complete msg anchor count={complete.count(msg_line)}")

complete_trace = pred("menuui17_complete") + r'''        if (menuui17_complete_match) {
            kernel::process *menuui17_server_pr = kern->crr_process();
            kernel::thread *menuui17_server_thr = kern->crr_thread();
            auto *menuui17_cpu = kern->get_cpu();
            const std::uint32_t menuui17_pc = menuui17_cpu ? menuui17_cpu->get_pc() : 0;
            const std::uint32_t menuui17_lr = menuui17_cpu ? menuui17_cpu->get_reg(14) : 0;
            const std::uint32_t menuui17_sp = menuui17_cpu ? menuui17_cpu->get_reg(13) : 0;

            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE: msg_id={} msg_handle={} completion={} server_process={} server_thread={} client_process={} client_thread={} client_uid=0x{:08X} request_status=0x{:08X} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                msg->id, static_cast<std::uint32_t>(msg_handle), val,
                menuui17_server_pr ? menuui17_server_pr->name() : std::string("<null>"),
                menuui17_server_thr ? menuui17_server_thr->name() : std::string("<null>"),
                menuui17_complete_client_pr ? menuui17_complete_client_pr->name() : std::string("<null>"),
                msg->own_thr ? msg->own_thr->name() : std::string("<null>"),
                menuui17_complete_client_uid3, msg->request_sts.ptr_address(),
                static_cast<std::uint32_t>(msg->args.flag),
                static_cast<std::uint32_t>(msg->args.args[0]),
                static_cast<std::uint32_t>(msg->args.args[1]),
                static_cast<std::uint32_t>(msg->args.args[2]),
                static_cast<std::uint32_t>(msg->args.args[3]),
                menuui17_pc, menuui17_lr, menuui17_sp);

            // PC/LR are guest return sites at the SVC boundary; resolve them to
            // guest modules without scanning or modifying guest stack memory.
            auto menuui17_log_frame = [&](const char *menuui17_kind, std::uint32_t menuui17_raw) {
                const std::uint32_t menuui17_addr = menuui17_raw & ~1U;
                if (!menuui17_server_pr || menuui17_addr < 0x10000U) return;
                codeseg_ptr menuui17_seg =
                    get_codeseg_from_addr(kern, menuui17_server_pr, menuui17_addr, false);
                if (!menuui17_seg) return;
                const std::string menuui17_module =
                    common::ucs2_to_utf8(menuui17_seg->get_full_path());
                const std::uint32_t menuui17_base =
                    menuui17_seg->get_code_run_addr(menuui17_server_pr);
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_FRAME: msg_id={} kind={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                    msg->id, menuui17_kind, menuui17_raw, menuui17_module,
                    menuui17_base, menuui17_addr - menuui17_base);
            };
            menuui17_log_frame("pc", menuui17_pc);
            menuui17_log_frame("lr", menuui17_lr);
        }

'''
complete = complete.replace(msg_line, msg_line + "\n" + complete_trace, 1)
svc = svc[:complete_pos] + complete + svc[next_bridge:]

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI17 FIX5: marker postcondition failed: {marker} "
            f"count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI17 FIX5: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI17 ALFROUTE1 FIX5 diagnostic-only traces applied")
print("MENUUI17 target: Menu UID 0x101F4CD2 -> 10282845_10282845_AppServer opcode 7")
print("MENUUI17 FIX5: function-scoped anchors; no IPC/pointer/focus/completion semantics changed")
