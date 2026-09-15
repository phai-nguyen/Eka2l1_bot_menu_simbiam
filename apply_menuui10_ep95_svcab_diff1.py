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

# MENUUI10 is a registration-only correction on top of MENUUI9.
# MENUUI9 proved that patching svc_register_funcs_v10 is insufficient for the
# RM-356 runtime: the observed integer epocver=10 corresponds to epocver::epoc95,
# and lib_manager does not register the v10 map for epoc95. Do not import the
# whole v10 table into epoc95; expose only the independently identified 0xAB
# MessageConstructFromPtr bridge as a one-entry epoc95 delta.
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

semantic_marker = "MENUUI10 EP95-SVCAB-DIFF1"
runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:"

already = [
    semantic_marker in svc,
    "svc_register_funcs_v95_diff" in svc_h,
    "svc_register_funcs_v95_diff" in reg,
    "register_epocv95" in reg_h,
    runtime_marker in lib,
]
if any(already):
    if all(already):
        # Verify the existing patch is complete before treating it as idempotent.
        a = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v95_diff = {")
        b = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v94 = {", a)
        v95 = svc[a:b]
        if v95.count("BRIDGE_REGISTER(") == 1 and v95.count("BRIDGE_REGISTER(0xAB, message_construct)") == 1:
            print("MENUUI10 EP95-SVCAB-DIFF1 already present")
            raise SystemExit(0)
    raise SystemExit("MENUUI10: partial prior patch detected")

# 1) Declare a one-entry epoc95 delta map. Keep the existing MENUUI9 v10 map
# untouched so the full validated diagnostic chain remains reproducible.
svc_h_anchor = """    ///> @brief The SVC map for Symbian S^3.
    extern const eka2l1::hle::func_map svc_register_funcs_v10;
"""
if svc_h.count(svc_h_anchor) != 1:
    raise SystemExit(f"MENUUI10: svc.h v10 declaration anchor count={svc_h.count(svc_h_anchor)}")
svc_h_insert = """    ///> @brief Narrow epocver::epoc95 compatibility delta observed on RM-356.
    extern const eka2l1::hle::func_map svc_register_funcs_v95_diff;

    ///> @brief The SVC map for Symbian S^3.
    extern const eka2l1::hle::func_map svc_register_funcs_v10;
"""
svc_h = svc_h.replace(svc_h_anchor, svc_h_insert, 1)

svc_anchor = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {\n"
if svc.count(svc_anchor) != 1:
    raise SystemExit(f"MENUUI10: svc.cpp v94 map anchor count={svc.count(svc_anchor)}")
svc_insert = """    // MENUUI10 EP95-SVCAB-DIFF1: epoc95 gets only the independently
    // identified MessageConstructFromPtr slot. Do not inherit the whole v10 map.
    const eka2l1::hle::func_map svc_register_funcs_v95_diff = {
        BRIDGE_REGISTER(0xAB, message_construct)
    };

    const eka2l1::hle::func_map svc_register_funcs_v94 = {
"""
svc = svc.replace(svc_anchor, svc_insert, 1)

# 2) Add an explicit epoc95 registrar that installs only the one-entry delta.
reg_h_anchor = """    /**
     * @brief Register Symbian S^3 supervisor calls.
     * @param mngr Reference to library manager.
     **/
    void register_epocv10(eka2l1::hle::lib_manager &mngr);
"""
if reg_h.count(reg_h_anchor) != 1:
    raise SystemExit(f"MENUUI10: reg.h v10 declaration anchor count={reg_h.count(reg_h_anchor)}")
reg_h_insert = """    /**
     * @brief Register the narrow epocver::epoc95 compatibility SVC delta.
     * @param mngr Reference to library manager.
     **/
    void register_epocv95(eka2l1::hle::lib_manager &mngr);

    /**
     * @brief Register Symbian S^3 supervisor calls.
     * @param mngr Reference to library manager.
     **/
    void register_epocv10(eka2l1::hle::lib_manager &mngr);
"""
reg_h = reg_h.replace(reg_h_anchor, reg_h_insert, 1)

reg_anchor = """    void register_epocv94(eka2l1::hle::lib_manager &mngr) {
        ADD_SVC_REGISTERS(mngr, svc_register_funcs_v94);
    }

    void register_epocv10(eka2l1::hle::lib_manager &mngr) {
"""
if reg.count(reg_anchor) != 1:
    raise SystemExit(f"MENUUI10: reg.cpp v94/v10 anchor count={reg.count(reg_anchor)}")
reg_insert = """    void register_epocv94(eka2l1::hle::lib_manager &mngr) {
        ADD_SVC_REGISTERS(mngr, svc_register_funcs_v94);
    }

    void register_epocv95(eka2l1::hle::lib_manager &mngr) {
        ADD_SVC_REGISTERS(mngr, svc_register_funcs_v95_diff);
    }

    void register_epocv10(eka2l1::hle::lib_manager &mngr) {
"""
reg = reg.replace(reg_anchor, reg_insert, 1)

# 3) The actual bug exposed by MENUUI9: epoc95 has no registration case.
# Add a dedicated case and a runtime marker so the device log proves that the
# delta map was installed before xnthemeserver issues SVC 0xAB.
lib_anchor = """        case epocver::epoc94:
            epoc::register_epocv94(*this);
            break;

        case epocver::epoc91:
"""
if lib.count(lib_anchor) != 1:
    raise SystemExit(f"MENUUI10: libmanager epoc94/epoc91 registration anchor count={lib.count(lib_anchor)}")
lib_insert = """        case epocver::epoc94:
            epoc::register_epocv94(*this);
            break;

        case epocver::epoc95:
            LOG_ERROR(KERNEL, "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG: epoc95 diff registering svc=0xAB -> message_construct");
            epoc::register_epocv95(*this);
            break;

        case epocver::epoc91:
"""
lib = lib.replace(lib_anchor, lib_insert, 1)

# Hard postconditions.
a = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v95_diff = {")
b = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v94 = {", a)
v95 = svc[a:b]
if v95.count("BRIDGE_REGISTER(") != 1:
    raise SystemExit(f"MENUUI10: epoc95 delta must contain exactly one bridge, got {v95.count('BRIDGE_REGISTER(')}")
if v95.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI10: epoc95 delta 0xAB mapping postcondition failed")
for forbidden in ["0xAC", "0xAD", "message_kill", "message_open_handle"]:
    if forbidden in v95:
        raise SystemExit("MENUUI10: epoc95 delta illegally contains " + forbidden)

# MENUUI9's v10 table remains byte-semantically intact: 0xAB construct,
# 0xAC unmapped, 0xAD message_kill.
v10_begin = svc.index("    const eka2l1::hle::func_map svc_register_funcs_v10 = {")
v10_end = svc.index("    // MENUUI10 EP95-SVCAB-DIFF1:", v10_begin)
v10 = svc[v10_begin:v10_end]
if v10.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI10: MENUUI9 v10 0xAB preservation failed")
if "BRIDGE_REGISTER(0xAC," in v10:
    raise SystemExit("MENUUI10: MENUUI9 v10 0xAC must remain unmapped")
if "BRIDGE_REGISTER(0xAD, message_kill)" not in v10:
    raise SystemExit("MENUUI10: MENUUI9 v10 message_kill preservation failed")

if svc_h.count("extern const eka2l1::hle::func_map svc_register_funcs_v95_diff;") != 1:
    raise SystemExit("MENUUI10: svc.h v95 delta declaration postcondition failed")
if reg_h.count("void register_epocv95(eka2l1::hle::lib_manager &mngr);") != 1:
    raise SystemExit("MENUUI10: reg.h epoc95 declaration postcondition failed")
if reg.count("void register_epocv95(eka2l1::hle::lib_manager &mngr)") != 1:
    raise SystemExit("MENUUI10: reg.cpp epoc95 registrar postcondition failed")
if reg.count("ADD_SVC_REGISTERS(mngr, svc_register_funcs_v95_diff);") != 1:
    raise SystemExit("MENUUI10: reg.cpp v95 delta registration postcondition failed")
if lib.count(runtime_marker) != 1:
    raise SystemExit("MENUUI10: runtime registration marker postcondition failed")
if 'epoc::register_epocv95(*this);' not in lib:
    raise SystemExit("MENUUI10: libmanager epoc95 registration call postcondition failed")

# Preserve all earlier causal probes.
for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
]:
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

print("MENUUI10 EP95-SVCAB-DIFF1 registration patch applied")
