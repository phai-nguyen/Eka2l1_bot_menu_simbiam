#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui11_ep94_svcab_msgconstruct1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
if not svc_path.is_file() or not lib_path.is_file():
    raise SystemExit("MENUUI11: required kernel source file missing")

svc = svc_path.read_text(encoding="utf-8")
lib = lib_path.read_text(encoding="utf-8")

# MENUUI11 corrects the target table, not the recovered semantic.  The iOS
# fork used by this project has a different epocver enum from newer upstream:
# integer 10 is epocver::epoc94 (S60v5), while epoc95 is integer 11.  RM-356
# traces therefore execute svc_register_funcs_v94.  Keep all prior diagnostics
# and the earlier MENUUI9/10 experiments intact; only fill the observed v94
# slot 0xAB.
required_svc = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "BRIDGE_FUNC(void, message_construct, std::int32_t msg_handle, service::message2 *msg_to_construct)",
]
required_lib = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:",
]
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI11: missing svc baseline marker: " + marker)
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI11: missing libmanager baseline marker: " + marker)

runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI11 EP94_MSGCONSTRUCT:"
semantic_marker = "MENUUI11 EP94-SVCAB-MSGCONSTRUCT1: epoc94 SVC 0xAB -> MessageConstructFromPtr"

v94_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {"
v93_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v93 = {"
try:
    v94_begin = svc.index(v94_begin_marker)
    v94_end = svc.index(v93_begin_marker, v94_begin)
except ValueError as exc:
    raise SystemExit("MENUUI11: unable to isolate epoc94 SVC table") from exc

v94 = svc[v94_begin:v94_end]
if semantic_marker in svc or runtime_marker in svc:
    if (
        semantic_marker in svc
        and runtime_marker in svc
        and v94.count("BRIDGE_REGISTER(0xAB, message_construct)") == 1
        and v94.count("BRIDGE_REGISTER(0xAC, message_kill)") == 1
        and "BRIDGE_REGISTER(0xAA," not in v94
    ):
        print("MENUUI11 EP94-SVCAB-MSGCONSTRUCT1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI11: partial prior patch detected")

# The frozen iOS fork's v94 IPC block is shifted one slot relative to v93:
# A9=MessageClient, AA remains independently unidentified in this project,
# AB is the observed xnthemeserver MessageConstructFromPtr call, and AC is the
# already-existing MessageKill.  Do not infer/fill AA and do not change AC.
if "BRIDGE_REGISTER(0xAB," in v94:
    raise SystemExit("MENUUI11: epoc94 slot 0xAB unexpectedly already occupied")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI11: epoc94 slot 0xAA unexpectedly occupied; refusing adjacent-slot inference")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI11: epoc94 0xAC message_kill preservation precondition failed")

reg_anchor = """        BRIDGE_REGISTER(0xA8, message_ipc_copy),\n        BRIDGE_REGISTER(0xA9, message_client),\n        BRIDGE_REGISTER(0xAC, message_kill),\n"""
if v94.count(reg_anchor) != 1:
    raise SystemExit(f"MENUUI11: epoc94 IPC registration anchor count={v94.count(reg_anchor)}")
reg_replace = """        BRIDGE_REGISTER(0xA8, message_ipc_copy),\n        BRIDGE_REGISTER(0xA9, message_client),\n        // MENUUI11 EP94-SVCAB-MSGCONSTRUCT1: observed RM-356 S60v5 slot.\n        // Keep 0xAA unmapped and preserve 0xAC=message_kill.\n        BRIDGE_REGISTER(0xAB, message_construct),\n        BRIDGE_REGISTER(0xAC, message_kill),\n"""
v94 = v94.replace(reg_anchor, reg_replace, 1)
svc = svc[:v94_begin] + v94 + svc[v94_end:]

# Add an execution marker to the already recovered message_construct body.  It
# is diagnostic-only and scoped to xnthemeserver on epoc94 so the device test
# can prove that 0xAB reached the intended function rather than merely existing
# in the binary.
construct_anchor = """        msg_to_construct->spare1 = 0;\n\n        kernel::process *menuui9_pr = kern->crr_process();\n"""
if svc.count(construct_anchor) != 1:
    raise SystemExit(f"MENUUI11: message_construct diagnostic anchor count={svc.count(construct_anchor)}")
construct_replace = """        msg_to_construct->spare1 = 0;\n\n        // MENUUI11 EP94-SVCAB-MSGCONSTRUCT1: epoc94 SVC 0xAB -> MessageConstructFromPtr.\n        kernel::process *menuui11_pr = kern->crr_process();\n        if (kern->get_epoc_version() == epocver::epoc94 && menuui11_pr) {\n            const std::uint32_t menuui11_uid3 = static_cast<std::uint32_t>(std::get<2>(menuui11_pr->get_uid_type()));\n            if (menuui11_uid3 == 0x10207254U) {\n                LOG_ERROR(KERNEL,\n                    \"SYMBIAN-SYSTEMAPPS1 MENUUI11 EP94_MSGCONSTRUCT: process={} uid=0x{:08X} thread={} msg_handle={} out_guest=0x{:08X} function={} session=0x{:08X} flags=0x{:08X} spare1={}\",\n                    menuui11_pr->name(), menuui11_uid3, kern->crr_thread()->name(), msg_handle,\n                    kern->get_cpu()->get_reg(1), msg_to_construct->function,\n                    static_cast<std::uint32_t>(msg_to_construct->session_ptr),\n                    static_cast<std::uint32_t>(msg_to_construct->flags), msg_to_construct->spare1);\n            }\n        }\n\n        kernel::process *menuui9_pr = kern->crr_process();\n"""
svc = svc.replace(construct_anchor, construct_replace, 1)

# Hard postconditions: exactly one v94 0xAB mapping, 0xAA remains untouched,
# and 0xAC remains message_kill.  Prior diagnostic chain must survive.
v94_begin = svc.index(v94_begin_marker)
v94_end = svc.index(v93_begin_marker, v94_begin)
v94 = svc[v94_begin:v94_end]
if v94.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI11: epoc94 0xAB mapping postcondition failed")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI11: epoc94 0xAA must remain unmapped")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI11: epoc94 0xAC message_kill preservation failed")
if runtime_marker not in svc or semantic_marker not in svc:
    raise SystemExit("MENUUI11: runtime/semantic marker postcondition failed")
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI11: prior svc diagnostic preservation failed: " + marker)
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI11: prior libmanager diagnostic preservation failed: " + marker)

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI11 EP94-SVCAB-MSGCONSTRUCT1 semantic patch applied")
