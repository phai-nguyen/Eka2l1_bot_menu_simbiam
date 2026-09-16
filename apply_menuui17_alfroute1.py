#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui17_alfroute1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
window_path = up / "src/emu/services/src/window/window.cpp"

for path in (svc_path, window_path):
    if not path.is_file():
        raise SystemExit(f"MENUUI17: required source missing: {path}")

svc = svc_path.read_text(encoding="utf-8")
window = window_path.read_text(encoding="utf-8")

# MENUUI17 is diagnostic-only and must layer on the device-tested chain.
required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_GET_FULL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI16 ADVFLAG1:",
]
joined = svc + "\n" + window
for marker in required:
    if marker not in joined:
        raise SystemExit("MENUUI17: missing authority marker: " + marker)

markers = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_WORD:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_FRAME:",
]
if any(marker in svc for marker in markers):
    if all(marker in svc for marker in markers):
        print("MENUUI17 ALFROUTE1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI17: partial prior patch detected")

server_name_literal = "10282845_10282845_AppServer"
menu_uid = "0x101F4CD2U"

# 1) Dedicated marker when Menu arms EAlfGetPointerEvent (TAlfredServerIPC opcode 7).
# Existing MENUUI7 already logs all Menu IPC; this marker only correlates the one
# asynchronous request that should later be written/completed by Alfred/Hui.
send_call = "        kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());\n"
if svc.count(send_call) != 1:
    raise SystemExit(f"MENUUI17: IPC send anchor count={svc.count(send_call)}")

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

# Shared exact predicate is intentionally repeated in the two SVCs so this
# patch does not add state or alter IPC lifetime/ordering.

def pred(prefix: str) -> str:
    return f'''        kernel::process *{prefix}_client_pr =\n            (msg && msg->own_thr) ? msg->own_thr->owning_process() : nullptr;\n        std::uint32_t {prefix}_client_uid3 = 0;\n        if ({prefix}_client_pr) {{\n            const auto {prefix}_uids = {prefix}_client_pr->get_uid_type();\n            {prefix}_client_uid3 = static_cast<std::uint32_t>(std::get<2>({prefix}_uids));\n        }}\n        const bool {prefix}_match = msg && msg->msg_session && msg->msg_session->get_server()\n            && msg->msg_session->get_server()->name() == "{server_name_literal}"\n            && msg->function == 7 && {prefix}_client_uid3 == {menu_uid};\n'''

# 2) Trace RMessage2::Write-style descriptor copy for pending opcode 7.
copy_anchor = '''        ipc_copy_info *info_host = info.get(crr_process);\n        ipc_msg_ptr msg = kern->get_msg(h);\n\n        if (!msg) {\n            return epoc::error_bad_handle;\n        }\n\n        msg->ref();\n'''
if svc.count(copy_anchor) != 1:
    raise SystemExit(f"MENUUI17: message_ipc_copy entry anchor count={svc.count(copy_anchor)}")

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
svc = svc.replace(copy_anchor, copy_anchor.replace("        msg->ref();\n", copy_entry + "        msg->ref();\n"), 1)

copy_result_anchor = '''        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n        msg->unref();\n\n        return result;\n'''
if svc.count(copy_result_anchor) != 1:
    raise SystemExit(f"MENUUI17: message_ipc_copy result anchor count={svc.count(copy_result_anchor)}")

copy_result = r'''        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);
        if (menuui17_copy_match) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY: stage=result msg_id={} result={} param={} flags=0x{:08X} direction_write={} target_len={} start_offset={}",
                msg->id, result, param, static_cast<std::uint32_t>(info_host->flags),
                (info_host->flags & IPC_DIR_WRITE) ? 1 : 0,
                info_host->target_length, start_offset);

            // When Alfred writes TAlfTouchEventS to the Menu client, target_ptr is
            // the source buffer in the current (server) process. Dump up to 32
            // complete 32-bit words without interpreting the firmware-specific ABI.
            if ((info_host->flags & IPC_DIR_WRITE) && info_host->target_length > 0) {
                std::uint8_t *menuui17_payload = info_host->target_ptr.get(crr_process);
                if (menuui17_payload) {
                    const std::uint32_t menuui17_words = std::min<std::uint32_t>(
                        static_cast<std::uint32_t>(info_host->target_length) / 4U, 32U);
                    for (std::uint32_t menuui17_i = 0; menuui17_i < menuui17_words; ++menuui17_i) {
                        std::uint32_t menuui17_word = 0;
                        std::memcpy(&menuui17_word, menuui17_payload + menuui17_i * 4U,
                            sizeof(menuui17_word));
                        LOG_WARN(KERNEL,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_WORD: msg_id={} index={} byte_offset={} value=0x{:08X}",
                            msg->id, menuui17_i, menuui17_i * 4U, menuui17_word);
                    }
                }
            }
        }
        msg->unref();

        return result;
'''
svc = svc.replace(copy_result_anchor, copy_result, 1)

# 3) Trace the exact message completion. Public Alfred source completes the
# pending EAlfGetPointerEvent only after Hui roster/control routing has produced
# a TAlfTouchEventS. Stack scan resolves only ALF/Hui/Hitchcock frames.
complete_anchor = '''    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n        ipc_msg_ptr msg = kern->get_msg(msg_handle);\n\n        if (msg->request_sts) {\n'''
if svc.count(complete_anchor) != 1:
    raise SystemExit(f"MENUUI17: message_complete anchor count={svc.count(complete_anchor)}")

complete_trace = '''    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n        ipc_msg_ptr msg = kern->get_msg(msg_handle);\n\n''' + pred("menuui17_complete") + r'''        if (menuui17_complete_match) {
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

            if (menuui17_cpu && menuui17_server_pr && menuui17_sp) {
                constexpr std::uint32_t menuui17_stack_words = 40;
                for (std::uint32_t menuui17_i = 0; menuui17_i < menuui17_stack_words; ++menuui17_i) {
                    const std::uint32_t menuui17_slot_addr = menuui17_sp + menuui17_i * 4U;
                    if (menuui17_slot_addr < menuui17_sp) break;
                    const std::uint32_t *menuui17_slot =
                        eka2l1::ptr<std::uint32_t>(menuui17_slot_addr).get(menuui17_server_pr);
                    if (!menuui17_slot) break;

                    const std::uint32_t menuui17_raw = *menuui17_slot;
                    const std::uint32_t menuui17_addr = menuui17_raw & ~1U;
                    if (menuui17_addr < 0x10000U) continue;
                    codeseg_ptr menuui17_seg =
                        get_codeseg_from_addr(kern, menuui17_server_pr, menuui17_addr, false);
                    if (!menuui17_seg) continue;

                    const std::string menuui17_module =
                        common::ucs2_to_utf8(menuui17_seg->get_full_path());
                    const bool menuui17_interesting =
                        menuui17_module.find("alf") != std::string::npos
                        || menuui17_module.find("Alf") != std::string::npos
                        || menuui17_module.find("ALF") != std::string::npos
                        || menuui17_module.find("hui") != std::string::npos
                        || menuui17_module.find("Hui") != std::string::npos
                        || menuui17_module.find("HUI") != std::string::npos
                        || menuui17_module.find("hitchcock") != std::string::npos
                        || menuui17_module.find("Hitchcock") != std::string::npos;
                    if (!menuui17_interesting) continue;

                    const std::uint32_t menuui17_base =
                        menuui17_seg->get_code_run_addr(menuui17_server_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_FRAME: msg_id={} stack_index={} slot=0x{:08X} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        msg->id, menuui17_i, menuui17_slot_addr, menuui17_raw,
                        menuui17_module, menuui17_base, menuui17_addr - menuui17_base);
                }
            }
        }

        if (msg->request_sts) {
'''
svc = svc.replace(complete_anchor, complete_trace, 1)

for marker in markers:
    if svc.count(marker) != 1:
        raise SystemExit(f"MENUUI17: marker postcondition failed: {marker} count={svc.count(marker)}")

# Guard the key dispatch/completion semantics: the original calls remain once.
for guard in [
    send_call.strip(),
    "const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);",
    "kern->call_ipc_complete_callbacks(msg, val);",
    "msg->own_thr->signal_request();",
]:
    if guard not in svc:
        raise SystemExit("MENUUI17: behavior-preservation guard missing: " + guard)

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI17 ALFROUTE1 diagnostic-only IPC route traces applied")
print("MENUUI17 target: Menu UID 0x101F4CD2 -> 10282845_10282845_AppServer opcode 7")
print("MENUUI17 behavior: no IPC, pointer, focus, timing, or completion semantics changed")
