#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui12_xntheme_ipcresult1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
if not svc_path.is_file() or not lib_path.is_file():
    raise SystemExit("MENUUI12: required kernel source file missing")

svc = svc_path.read_text(encoding="utf-8")
lib = lib_path.read_text(encoding="utf-8")

required_svc = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI11 EP94_MSGCONSTRUCT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=LLE",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
]
required_lib = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:",
]
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI12: missing svc baseline marker: " + marker)
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI12: missing libmanager baseline marker: " + marker)

complete_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE:"
copy_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COPY:"
semantic_marker = "MENUUI12 XNTHEME-IPCRESULT1: diagnostic-only completion/copy trace"

if complete_marker in svc or copy_marker in svc or semantic_marker in svc:
    if complete_marker in svc and copy_marker in svc and semantic_marker in svc:
        print("MENUUI12 XNTHEME-IPCRESULT1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI12: partial prior patch detected")

# Guard the validated MENUUI11 EPOC94 mapping. MENUUI12 is diagnostics only.
v94_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {"
v93_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v93 = {"
try:
    v94_begin = svc.index(v94_begin_marker)
    v94_end = svc.index(v93_begin_marker, v94_begin)
except ValueError as exc:
    raise SystemExit("MENUUI12: unable to isolate epoc94 SVC table") from exc
v94 = svc[v94_begin:v94_end]
if v94.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI12: MENUUI11 epoc94 0xAB authority missing")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI12: epoc94 0xAA must remain unmapped")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI12: epoc94 0xAC message_kill preservation failed")

# 1) Trace every completion of xnthemeserver function 7/9 back to Menu.
# MENUUI6 already traces negative completions; this deliberately records zero
# and positive completion codes too, because the MENUUI11 device log showed a
# Menu Leave(-1) without a corresponding xnthemeserver NEGIPC line.
complete_sig = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {"
complete_start = svc.find(complete_sig)
complete_end = svc.find("\n    BRIDGE_FUNC(", complete_start + len(complete_sig))
if complete_start < 0 or complete_end < 0:
    raise SystemExit("MENUUI12: message_complete block not found")
complete_body = svc[complete_start:complete_end]
complete_anchor = "        kern->call_ipc_complete_callbacks(msg, val);\n"
if complete_body.count(complete_anchor) != 1:
    raise SystemExit(f"MENUUI12: message_complete callback anchor count={complete_body.count(complete_anchor)}")

complete_inject = r'''        // MENUUI12 XNTHEME-IPCRESULT1: diagnostic-only completion result trace.
        if (msg && msg->own_thr) {
            kernel::process *menuui12_server_pr = kern->crr_process();
            kernel::process *menuui12_client_pr = msg->own_thr->owning_process();
            if (menuui12_server_pr && menuui12_client_pr) {
                const std::uint32_t menuui12_server_uid = static_cast<std::uint32_t>(std::get<2>(menuui12_server_pr->get_uid_type()));
                const std::uint32_t menuui12_client_uid = static_cast<std::uint32_t>(std::get<2>(menuui12_client_pr->get_uid_type()));
                if (menuui12_server_uid == 0x10207254U && menuui12_client_uid == 0x101F4CD2U
                    && (msg->function == 7 || msg->function == 9)) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE: server_process={} server_uid=0x{:08X} client_process={} client_uid=0x{:08X} client_thread={} function={} result={} msg_id={} request_status=0x{:08X} session=0x{:08X} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X}",
                        menuui12_server_pr->name(), menuui12_server_uid,
                        menuui12_client_pr->name(), menuui12_client_uid, msg->own_thr->name(),
                        msg->function, val, msg->id, msg->request_sts.ptr_address(),
                        static_cast<std::uint32_t>(msg->session_ptr_lle), static_cast<std::uint32_t>(msg->args.flag),
                        static_cast<std::uint32_t>(msg->args.args[0]), static_cast<std::uint32_t>(msg->args.args[1]),
                        static_cast<std::uint32_t>(msg->args.args[2]), static_cast<std::uint32_t>(msg->args.args[3]));
                }
            }
        }

'''
complete_body = complete_body.replace(complete_anchor, complete_inject + complete_anchor, 1)
svc = svc[:complete_start] + complete_body + svc[complete_end:]

# 2) Trace descriptor traffic for the same xnthemeserver requests. For writes,
# the sampled words are the server-side source payload before it is copied to
# the Menu descriptor. For reads, they are the server target buffer after the
# client descriptor was copied in. This does not alter either buffer.
copy_sig = "    BRIDGE_FUNC(std::int32_t, message_ipc_copy, kernel::handle h, std::int32_t param, eka2l1::ptr<ipc_copy_info> info,"
copy_start = svc.find(copy_sig)
copy_end = svc.find("\n    BRIDGE_FUNC(", copy_start + len(copy_sig))
if copy_start < 0 or copy_end < 0:
    raise SystemExit("MENUUI12: message_ipc_copy block not found")
copy_body = svc[copy_start:copy_end]
copy_anchor = "        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n        msg->unref();\n"
if copy_body.count(copy_anchor) != 1:
    raise SystemExit(f"MENUUI12: message_ipc_copy result anchor count={copy_body.count(copy_anchor)}")

copy_replace = r'''        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);

        // MENUUI12 XNTHEME-IPCRESULT1: diagnostic-only descriptor transfer trace.
        kernel::process *menuui12_copy_server_pr = kern->crr_process();
        kernel::process *menuui12_copy_client_pr = msg->own_thr ? msg->own_thr->owning_process() : nullptr;
        if (menuui12_copy_server_pr && menuui12_copy_client_pr) {
            const std::uint32_t menuui12_copy_server_uid = static_cast<std::uint32_t>(std::get<2>(menuui12_copy_server_pr->get_uid_type()));
            const std::uint32_t menuui12_copy_client_uid = static_cast<std::uint32_t>(std::get<2>(menuui12_copy_client_pr->get_uid_type()));
            if (menuui12_copy_server_uid == 0x10207254U && menuui12_copy_client_uid == 0x101F4CD2U
                && (msg->function == 7 || msg->function == 9)) {
                const bool menuui12_copy_write = (info_host->flags & IPC_DIR_WRITE) != 0;
                std::uint8_t *menuui12_copy_sample_ptr = (info_host->flags & IPC_HLE_EKA1)
                    ? info_host->target_host_ptr : info_host->target_ptr.get(crr_process);
                std::uint32_t menuui12_w0 = 0, menuui12_w1 = 0, menuui12_w2 = 0, menuui12_w3 = 0;
                if (menuui12_copy_sample_ptr && info_host->target_length >= 4)
                    std::memcpy(&menuui12_w0, menuui12_copy_sample_ptr, 4);
                if (menuui12_copy_sample_ptr && info_host->target_length >= 8)
                    std::memcpy(&menuui12_w1, menuui12_copy_sample_ptr + 4, 4);
                if (menuui12_copy_sample_ptr && info_host->target_length >= 12)
                    std::memcpy(&menuui12_w2, menuui12_copy_sample_ptr + 8, 4);
                if (menuui12_copy_sample_ptr && info_host->target_length >= 16)
                    std::memcpy(&menuui12_w3, menuui12_copy_sample_ptr + 12, 4);
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COPY: server_process={} client_process={} function={} msg_id={} param={} arg_type=0x{:X} dir={} copy_flags=0x{:08X} target=0x{:08X} target_len={} start={} result={} sample0=0x{:08X} sample1=0x{:08X} sample2=0x{:08X} sample3=0x{:08X}",
                    menuui12_copy_server_pr->name(), menuui12_copy_client_pr->name(), msg->function, msg->id,
                    param, static_cast<std::uint32_t>(arg_type), menuui12_copy_write ? "WRITE_TO_CLIENT" : "READ_FROM_CLIENT",
                    static_cast<std::uint32_t>(info_host->flags), info_host->target_ptr.ptr_address(),
                    info_host->target_length, start_offset, result,
                    menuui12_w0, menuui12_w1, menuui12_w2, menuui12_w3);
            }
        }

        msg->unref();
'''
copy_body = copy_body.replace(copy_anchor, copy_replace, 1)
svc = svc[:copy_start] + copy_body + svc[copy_end:]

# Add a stable semantic marker as a source comment only.
marker_anchor = "        // MENUUI12 XNTHEME-IPCRESULT1: diagnostic-only completion result trace.\n"
if marker_anchor not in svc:
    raise SystemExit("MENUUI12: completion diagnostic injection missing")
svc = svc.replace(marker_anchor, "        // " + semantic_marker + "\n" + marker_anchor, 1)

# Hard postconditions: validated MENUUI11 mapping and all earlier diagnostics
# must survive exactly; MENUUI12 may only add diagnostics.
v94_begin = svc.index(v94_begin_marker)
v94_end = svc.index(v93_begin_marker, v94_begin)
v94 = svc[v94_begin:v94_end]
if v94.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI12: epoc94 0xAB mapping changed")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI12: epoc94 0xAA must remain unmapped")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI12: epoc94 0xAC mapping changed")
if svc.count(complete_marker) != 1 or svc.count(copy_marker) != 1 or semantic_marker not in svc:
    raise SystemExit("MENUUI12: diagnostic marker postcondition failed")
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI12: prior svc diagnostic preservation failed: " + marker)
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI12: prior libmanager diagnostic preservation failed: " + marker)

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI12 XNTHEME-IPCRESULT1 diagnostic patch applied")
