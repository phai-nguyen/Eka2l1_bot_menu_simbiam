#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui10_ep95_svcab_diff1.py <upstream-root>")

up = Path(sys.argv[1])
svc_cpp_path = up / "src/emu/kernel/src/svc.cpp"
svc_h_path = up / "src/emu/kernel/include/kernel/svc.h"
reg_cpp_path = up / "src/emu/kernel/src/reg.cpp"
reg_h_path = up / "src/emu/kernel/include/kernel/reg.h"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"

for p in [svc_cpp_path, svc_h_path, reg_cpp_path, reg_h_path, lib_path]:
    if not p.is_file():
        raise SystemExit("MENUUI10: required kernel source file missing: " + str(p))

svc = svc_cpp_path.read_text(encoding="utf-8")
svc_h = svc_h_path.read_text(encoding="utf-8")
reg = reg_cpp_path.read_text(encoding="utf-8")
reg_h = reg_h_path.read_text(encoding="utf-8")
lib = lib_path.read_text(encoding="utf-8")

required_svc = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:",
    "MENUUI9 XNTHEME-MSGCONSTRUCT1: S^3/epoc95 SVC 0xAB is MessageConstructFromPtr",
    "BRIDGE_REGISTER(0xAB, message_construct)",
    "msg_to_construct->spare1 = 0;",
]
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI10: missing MENUUI9 baseline marker in svc.cpp: " + marker)

required_lib = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_REGFRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_PTR:",
]
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI10: missing MENUUI8 baseline marker in libmanager.cpp: " + marker)

MAP = "svc_register_funcs_menuui10_epoc95_diff"
REG = "register_epocv95_menuui10"
RUNTIME = "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:"

# Use MENUUI10-unique symbols because the long-lived EKA2L1 fork may already
# contain generic epoc95 helpers from older compatibility work. We only care
# that this exact one-slot delta is absent/present, not whether generic v95
# names happen to exist elsewhere.
state = {
    "svc_map": MAP in svc,
    "svc_decl": MAP in svc_h,
    "reg_body": REG in reg,
    "reg_decl": REG in reg_h,
    "runtime": RUNTIME in lib,
}
if any(state.values()):
    if not all(state.values()):
        raise SystemExit("MENUUI10: partial unique patch state: " + repr(state))
    a = svc.index(f"    const eka2l1::hle::func_map {MAP} = {{")
    b = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v94 = {", a)
    part = svc[a:b]
    if part.count("BRIDGE_REGISTER(") != 1 or part.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
        raise SystemExit("MENUUI10: existing unique map is not the expected one-slot delta")
    print("MENUUI10 EP95-SVCAB-DIFF1 unique patch already present")
    raise SystemExit(0)

# 1) One-entry epoc95 map. Do not inherit the whole S^3/v10 map.
svc_h_anchor = """    ///> @brief The SVC map for Symbian S^3.
    extern const eka2l1::hle::func_map svc_register_funcs_v10;
"""
if svc_h.count(svc_h_anchor) != 1:
    raise SystemExit(f"MENUUI10: svc.h v10 declaration anchor count={svc_h.count(svc_h_anchor)}")
svc_h = svc_h.replace(
    svc_h_anchor,
    f"""    ///> @brief MENUUI10 narrow epoc95 compatibility delta for RM-356.
    extern const eka2l1::hle::func_map {MAP};

""" + svc_h_anchor,
    1,
)

svc_anchor = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {\n"
if svc.count(svc_anchor) != 1:
    raise SystemExit(f"MENUUI10: svc.cpp v94 map anchor count={svc.count(svc_anchor)}")
svc_insert = f"""    // MENUUI10 EP95-SVCAB-DIFF1: exactly one independently identified slot.
    const eka2l1::hle::func_map {MAP} = {{
        BRIDGE_REGISTER(0xAB, message_construct)
    }};

""" + svc_anchor
svc = svc.replace(svc_anchor, svc_insert, 1)

# 2) Unique registrar avoids colliding with any pre-existing generic epoc95
# compatibility helper in this fork.
reg_h_anchor = "    void register_epocv10(eka2l1::hle::lib_manager &mngr);\n"
if reg_h.count(reg_h_anchor) != 1:
    raise SystemExit(f"MENUUI10: reg.h v10 declaration anchor count={reg_h.count(reg_h_anchor)}")
reg_h = reg_h.replace(
    reg_h_anchor,
    f"    void {REG}(eka2l1::hle::lib_manager &mngr);\n\n" + reg_h_anchor,
    1,
)

reg_anchor = "    void register_epocv10(eka2l1::hle::lib_manager &mngr) {\n"
if reg.count(reg_anchor) != 1:
    raise SystemExit(f"MENUUI10: reg.cpp v10 registrar anchor count={reg.count(reg_anchor)}")
reg = reg.replace(
    reg_anchor,
    f"""    void {REG}(eka2l1::hle::lib_manager &mngr) {{
        ADD_SVC_REGISTERS(mngr, {MAP});
    }}

""" + reg_anchor,
    1,
)

# 3) Register the delta for epoc95. If this fork already has an epoc95 switch
# case, augment that case; otherwise add a dedicated case. This preserves any
# older epoc95 behavior while adding only 0xAB.
case95 = "        case epocver::epoc95:\n"
if lib.count(case95) > 1:
    raise SystemExit(f"MENUUI10: multiple epoc95 switch cases found: {lib.count(case95)}")
call_block = (
    f'            LOG_ERROR(KERNEL, "{RUNTIME} epoc95 one-slot diff registering svc=0xAB -> message_construct");\n'
    f"            epoc::{REG}(*this);\n"
)
if lib.count(case95) == 1:
    lib = lib.replace(case95, case95 + call_block, 1)
else:
    lib_anchor = """        case epocver::epoc94:
            epoc::register_epocv94(*this);
            break;

        case epocver::epoc91:
"""
    if lib.count(lib_anchor) != 1:
        raise SystemExit(f"MENUUI10: libmanager epoc94/epoc91 anchor count={lib.count(lib_anchor)}")
    lib_insert = """        case epocver::epoc94:
            epoc::register_epocv94(*this);
            break;

        case epocver::epoc95:
""" + call_block + """            break;

        case epocver::epoc91:
"""
    lib = lib.replace(lib_anchor, lib_insert, 1)

# Hard postconditions: the MENUUI10 delta is exactly one slot and prior probes
# remain present.
a = svc.index(f"    const eka2l1::hle::func_map {MAP} = {{")
b = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v94 = {", a)
v95 = svc[a:b]
if v95.count("BRIDGE_REGISTER(") != 1:
    raise SystemExit(f"MENUUI10: one-slot delta bridge count={v95.count('BRIDGE_REGISTER(')}")
if v95.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI10: one-slot 0xAB mapping postcondition failed")
for forbidden in ["0xAC", "0xAD", "message_kill", "message_open_handle"]:
    if forbidden in v95:
        raise SystemExit("MENUUI10: one-slot delta illegally contains " + forbidden)

v10_begin = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v10 = {")
v10_end = svc.index(f"    // MENUUI10 EP95-SVCAB-DIFF1:", v10_begin)
v10 = svc[v10_begin:v10_end]
if v10.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI10: MENUUI9 v10 0xAB preservation failed")
if "BRIDGE_REGISTER(0xAC," in v10:
    raise SystemExit("MENUUI10: MENUUI9 v10 0xAC must remain unmapped")
if "BRIDGE_REGISTER(0xAD, message_kill)" not in v10:
    raise SystemExit("MENUUI10: MENUUI9 v10 0xAD preservation failed")

if svc_h.count(f"extern const eka2l1::hle::func_map {MAP};") != 1:
    raise SystemExit("MENUUI10: unique map declaration postcondition failed")
if reg_h.count(f"void {REG}(eka2l1::hle::lib_manager &mngr);") != 1:
    raise SystemExit("MENUUI10: unique registrar declaration postcondition failed")
if reg.count(f"void {REG}(eka2l1::hle::lib_manager &mngr)") != 1:
    raise SystemExit("MENUUI10: unique registrar body postcondition failed")
if reg.count(f"ADD_SVC_REGISTERS(mngr, {MAP});") != 1:
    raise SystemExit("MENUUI10: unique one-slot registration postcondition failed")
if lib.count(RUNTIME) != 1 or lib.count(f"epoc::{REG}(*this);") != 1:
    raise SystemExit("MENUUI10: epoc95 runtime registration postcondition failed")

for marker in ["SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:", "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:"]:
    if marker not in svc:
        raise SystemExit("MENUUI10: prior svc diagnostic preservation failed: " + marker)
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI10: prior libmanager diagnostic preservation failed: " + marker)

svc_cpp_path.write_text(svc, encoding="utf-8")
svc_h_path.write_text(svc_h, encoding="utf-8")
reg_cpp_path.write_text(reg, encoding="utf-8")
reg_h_path.write_text(reg_h, encoding="utf-8")
lib_path.write_text(lib, encoding="utf-8")
print("MENUUI10 EP95-SVCAB-DIFF1 unique one-slot registration patch applied")
