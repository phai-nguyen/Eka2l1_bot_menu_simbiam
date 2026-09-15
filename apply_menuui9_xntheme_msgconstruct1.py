#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui9_xntheme_msgconstruct1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
if not svc_path.is_file() or not lib_path.is_file():
    raise SystemExit("MENUUI9: required kernel source file missing")

svc = svc_path.read_text(encoding="utf-8")
lib = lib_path.read_text(encoding="utf-8")

# MENUUI9 is intentionally a narrow semantic fix. MENUUI8 captured a real
# S^3/epoc95 SVC 0xAB from xnthemeserver with r0=message handle and
# r1=RMessage2* shape. Symbian's MessageConstructFromPtr ABI is exactly
# (message, output ptr). Do not infer or fill adjacent 0xAC here.
required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "BRIDGE_FUNC(void, message_construct, std::int32_t msg_handle, service::message2 *msg_to_construct)",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI9: missing svc baseline marker: " + marker)

for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_REGFRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_PTR:",
]:
    if marker not in lib:
        raise SystemExit("MENUUI9: missing MENUUI8 baseline marker: " + marker)

runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:"
semantic_marker = "MENUUI9 XNTHEME-MSGCONSTRUCT1: S^3/epoc95 SVC 0xAB is MessageConstructFromPtr"
if runtime_marker in svc or semantic_marker in svc:
    if runtime_marker in svc and semantic_marker in svc and "BRIDGE_REGISTER(0xAB, message_construct)" in svc:
        print("MENUUI9 XNTHEME-MSGCONSTRUCT1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI9: partial prior patch detected")

# EKA2L1 calls this map svc_register_funcs_v10, but svc.h documents it as the
# Symbian S^3 map. MENUUI8's integer epocver=10 is epocver::epoc95; Belle/
# epocver::epoc10 has integer value 11. Patch the table used as the S^3 base.
v10_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v10 = {"
v94_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {"
try:
    v10_begin = svc.index(v10_begin_marker)
    v10_end = svc.index(v94_begin_marker, v10_begin)
except ValueError as exc:
    raise SystemExit("MENUUI9: unable to isolate S^3/v10-base SVC table") from exc

v10 = svc[v10_begin:v10_end]
if "BRIDGE_REGISTER(0xAB," in v10:
    raise SystemExit("MENUUI9: S^3/v10-base slot 0xAB unexpectedly already occupied")
if "BRIDGE_REGISTER(0xAC," in v10:
    raise SystemExit("MENUUI9: S^3/v10-base slot 0xAC unexpectedly occupied; refusing adjacent-slot inference")

reg_anchor = """        BRIDGE_REGISTER(0xA9, message_ipc_copy),\n        BRIDGE_REGISTER(0xAA, message_client),\n        BRIDGE_REGISTER(0xAD, message_kill),\n"""
if v10.count(reg_anchor) != 1:
    raise SystemExit(f"MENUUI9: S^3/v10-base IPC registration anchor count={v10.count(reg_anchor)}")
reg_replace = """        BRIDGE_REGISTER(0xA9, message_ipc_copy),\n        BRIDGE_REGISTER(0xAA, message_client),\n        // MENUUI9 XNTHEME-MSGCONSTRUCT1: S^3/epoc95 SVC 0xAB is MessageConstructFromPtr.\n        BRIDGE_REGISTER(0xAB, message_construct),\n        BRIDGE_REGISTER(0xAD, message_kill),\n"""
v10 = v10.replace(reg_anchor, reg_replace, 1)
svc = svc[:v10_begin] + v10 + svc[v10_end:]

construct_anchor = """        msg_to_construct->ipc_msg_handle = msg_handle;\n        msg_to_construct->session_ptr = msg->session_ptr_lle;\n        msg_to_construct->flags = msg->args.flag;\n        msg_to_construct->function = msg->function;\n        std::copy(msg->args.args, msg->args.args + 4, msg_to_construct->args);\n"""
if svc.count(construct_anchor) != 1:
    raise SystemExit(f"MENUUI9: message_construct body anchor count={svc.count(construct_anchor)}")

construct_replace = """        msg_to_construct->ipc_msg_handle = msg_handle;\n        msg_to_construct->session_ptr = msg->session_ptr_lle;\n        msg_to_construct->flags = msg->args.flag;\n        msg_to_construct->function = msg->function;\n        std::copy(msg->args.args, msg->args.args + 4, msg_to_construct->args);\n        // RMessageU2::iSpare1 is explicitly zeroed by the Symbian kernel.\n        // RMessage2's user-side constructor clears flags/spare3 after this call.\n        msg_to_construct->spare1 = 0;\n\n        kernel::process *menuui9_pr = kern->crr_process();\n        if (kern->get_epoc_version() == epocver::epoc95 && menuui9_pr) {\n            const std::uint32_t menuui9_uid3 = static_cast<std::uint32_t>(std::get<2>(menuui9_pr->get_uid_type()));\n            if (menuui9_uid3 == 0x10207254U) {\n                LOG_ERROR(KERNEL,\n                    \"SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT: process={} uid=0x{:08X} thread={} msg_handle={} out_guest=0x{:08X} function={} session=0x{:08X} flags=0x{:08X} spare1={} arg0=0x{:08X} arg1=0x{:08X} arg2=0x{:08X} arg3=0x{:08X}\",\n                    menuui9_pr->name(), menuui9_uid3, kern->crr_thread()->name(), msg_handle,\n                    kern->get_cpu()->get_reg(1), msg_to_construct->function,\n                    static_cast<std::uint32_t>(msg_to_construct->session_ptr),\n                    static_cast<std::uint32_t>(msg_to_construct->flags), msg_to_construct->spare1,\n                    static_cast<std::uint32_t>(msg_to_construct->args[0]),\n                    static_cast<std::uint32_t>(msg_to_construct->args[1]),\n                    static_cast<std::uint32_t>(msg_to_construct->args[2]),\n                    static_cast<std::uint32_t>(msg_to_construct->args[3]));\n            }\n        }\n"""
svc = svc.replace(construct_anchor, construct_replace, 1)

# Hard gates: only 0xAB is filled in the S^3/v10-base table; 0xAC stays
# deliberately unmapped until independently identified.
v10_begin = svc.index(v10_begin_marker)
v10_end = svc.index(v94_begin_marker, v10_begin)
v10 = svc[v10_begin:v10_end]
if v10.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI9: S^3/v10-base 0xAB mapping postcondition failed")
if "BRIDGE_REGISTER(0xAC," in v10:
    raise SystemExit("MENUUI9: S^3/v10-base 0xAC must remain unmapped")
if "BRIDGE_REGISTER(0xAD, message_kill)" not in v10:
    raise SystemExit("MENUUI9: S^3/v10-base message_kill 0xAD preservation failed")
if "msg_to_construct->spare1 = 0;" not in svc:
    raise SystemExit("MENUUI9: RMessage2 spare1 postcondition failed")
if runtime_marker not in svc or semantic_marker not in svc:
    raise SystemExit("MENUUI9: runtime/semantic marker postcondition failed")
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI9: prior diagnostic preservation failed: " + marker)

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI9 XNTHEME-MSGCONSTRUCT1 semantic patch applied")
