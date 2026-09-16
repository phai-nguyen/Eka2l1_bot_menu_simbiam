#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui13_fs_diruid1.py <upstream-root>")

up = Path(sys.argv[1])
dirs_path = up / "src/emu/services/src/fs/dirs.cpp"
svc_path = up / "src/emu/kernel/src/svc.cpp"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
for p in (dirs_path, svc_path, lib_path):
    if not p.is_file():
        raise SystemExit("MENUUI13: required source file missing: " + str(p))

dirs = dirs_path.read_text(encoding="utf-8")
svc = svc_path.read_text(encoding="utf-8")
lib = lib_path.read_text(encoding="utf-8")

# MENUUI13 must be applied on top of the validated MENUUI12 diagnostic build.
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
    if marker not in svc:
        raise SystemExit("MENUUI13: missing svc baseline marker: " + marker)
for marker in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI10 EP95_SVCAB_REG:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:",
]:
    if marker not in lib:
        raise SystemExit("MENUUI13: missing libmanager baseline marker: " + marker)

# Preserve the real-device-validated EPOC94 SVC authority exactly.
v94_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v94 = {"
v93_begin_marker = "    const eka2l1::hle::func_map svc_register_funcs_v93 = {"
try:
    a = svc.index(v94_begin_marker)
    b = svc.index(v93_begin_marker, a)
except ValueError as exc:
    raise SystemExit("MENUUI13: unable to isolate epoc94 SVC table") from exc
v94 = svc[a:b]
if v94.count("BRIDGE_REGISTER(0xAB, message_construct)") != 1:
    raise SystemExit("MENUUI13: epoc94 0xAB authority missing")
if "BRIDGE_REGISTER(0xAA," in v94:
    raise SystemExit("MENUUI13: epoc94 0xAA must remain unmapped")
if v94.count("BRIDGE_REGISTER(0xAC, message_kill)") != 1:
    raise SystemExit("MENUUI13: epoc94 0xAC authority missing")

semantic_marker = "MENUUI13 FS-DIRUID1: KEntryAttAllowUid preserves directory entries"
runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:"
if semantic_marker in dirs or runtime_marker in dirs:
    if semantic_marker in dirs and runtime_marker in dirs:
        print("MENUUI13 FS-DIRUID1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI13: partial prior patch detected")

old = '''        if (attrib_raw & epoc::fs::entry_att_allow_uid) {
            attrib |= io_attrib_allow_uid;
            attrib &= ~io_attrib_include_dir;
        }
'''
new = '''        if (attrib_raw & epoc::fs::entry_att_allow_uid) {
            // MENUUI13 FS-DIRUID1: KEntryAttAllowUid preserves directory entries.
            // Symbian FileServer uses this flag to request/read UID information for
            // non-directory entries; it does not remove directories from RDir.
            attrib |= io_attrib_allow_uid;

            // Diagnostic only: keep MENUUI12's xntheme IPC traces and expose the
            // FileServer mask that reaches this corrected semantic path.
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1: path={} attrib_raw=0x{:08X} allow_uid=1 include_file={} include_dir={}",
                common::ucs2_to_utf8(*dir), static_cast<std::uint32_t>(attrib_raw),
                (attrib & io_attrib_include_file) ? 1 : 0,
                (attrib & io_attrib_include_dir) ? 1 : 0);
        }
'''
if dirs.count(old) != 1:
    raise SystemExit(f"MENUUI13: allow_uid semantic anchor count={dirs.count(old)}")
dirs = dirs.replace(old, new, 1)

# Hard postconditions: the obsolete directory suppression must be gone, the
# semantic change must exist exactly once, and all SVC/diagnostic authority is
# untouched.
if "attrib &= ~io_attrib_include_dir;" in dirs[dirs.index("void fs_server_client::open_dir"):dirs.index("void fs_server_client::close_dir")]:
    raise SystemExit("MENUUI13: obsolete allow_uid directory suppression survived")
if dirs.count(semantic_marker) != 1 or dirs.count(runtime_marker) != 1:
    raise SystemExit("MENUUI13: source/runtime marker postcondition failed")

# Re-check frozen SVC authority after the service-only edit.
a = svc.index(v94_begin_marker)
b = svc.index(v93_begin_marker, a)
v94 = svc[a:b]
assert v94.count("BRIDGE_REGISTER(0xAB, message_construct)") == 1
assert "BRIDGE_REGISTER(0xAA," not in v94
assert v94.count("BRIDGE_REGISTER(0xAC, message_kill)") == 1

dirs_path.write_text(dirs, encoding="utf-8")
print("MENUUI13 FS-DIRUID1 semantic patch applied")
