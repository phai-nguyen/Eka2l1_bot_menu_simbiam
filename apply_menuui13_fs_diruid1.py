#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui13_fs_diruid1.py <upstream-root>")

up = Path(sys.argv[1])
dirs_path = up / "src/emu/services/src/fs/dirs.cpp"
vfs_path = up / "src/emu/vfs/src/vfs.cpp"
svc_path = up / "src/emu/kernel/src/svc.cpp"
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
for p in (dirs_path, vfs_path, svc_path, lib_path):
    if not p.is_file():
        raise SystemExit("MENUUI13: required source file missing: " + str(p))

dirs = dirs_path.read_text(encoding="utf-8")
vfs = vfs_path.read_text(encoding="utf-8")
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

dirs_marker = "MENUUI13 FS-DIRUID1: KEntryAttAllowUid preserves directory entries"
vfs_marker = "MENUUI13 FS-DIRUID1: UID probing applies only to regular files"
runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:"
if dirs_marker in dirs or runtime_marker in dirs or vfs_marker in vfs:
    if dirs_marker in dirs and runtime_marker in dirs and vfs_marker in vfs:
        print("MENUUI13 FS-DIRUID1 FIX2 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI13: partial prior patch detected")

# Part 1: KEntryAttAllowUid must not remove directory entries at FileServer open.
old_dirs = '''        if (attrib_raw & epoc::fs::entry_att_allow_uid) {
            attrib |= io_attrib_allow_uid;
            attrib &= ~io_attrib_include_dir;
        }
'''
new_dirs = '''        if (attrib_raw & epoc::fs::entry_att_allow_uid) {
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
if dirs.count(old_dirs) != 1:
    raise SystemExit(f"MENUUI13: allow_uid open_dir anchor count={dirs.count(old_dirs)}")
dirs = dirs.replace(old_dirs, new_dirs, 1)

# Part 2: even when include_dir is preserved, the physical-directory iterator
# must not try to open a directory as a file to read TUidType. Symbian ROM,
# ROFS and FAT all gate UID reads to non-directory entries.
old_vfs = '''                    if ((attribute & io_attrib_include_file) && (attribute & io_attrib_allow_uid)) {
                        epoc::uid_type temp_uid;
'''
new_vfs = '''                    // MENUUI13 FS-DIRUID1: UID probing applies only to regular files.
                    if ((entry.type == common::FILE_REGULAR) && (attribute & io_attrib_include_file) && (attribute & io_attrib_allow_uid)) {
                        epoc::uid_type temp_uid;
'''
if vfs.count(old_vfs) != 1:
    raise SystemExit(f"MENUUI13: physical_directory UID anchor count={vfs.count(old_vfs)}")
vfs = vfs.replace(old_vfs, new_vfs, 1)

# Hard postconditions: both independent directory-suppression mechanisms are
# gone, the semantic change exists exactly once at each layer, and all prior
# SVC/diagnostic authority is untouched.
open_dir_block = dirs[dirs.index("void fs_server_client::open_dir"):dirs.index("void fs_server_client::close_dir")]
if "attrib &= ~io_attrib_include_dir;" in open_dir_block[open_dir_block.index("entry_att_allow_uid"):]:
    raise SystemExit("MENUUI13: obsolete open_dir directory suppression survived")
if dirs.count(dirs_marker) != 1 or dirs.count(runtime_marker) != 1:
    raise SystemExit("MENUUI13: FileServer source/runtime marker postcondition failed")
if vfs.count(vfs_marker) != 1:
    raise SystemExit("MENUUI13: VFS marker postcondition failed")
if "if ((attribute & io_attrib_include_file) && (attribute & io_attrib_allow_uid))" in vfs:
    raise SystemExit("MENUUI13: unguarded physical_directory UID probe survived")

# Re-check frozen SVC authority after the service/VFS-only edit.
a = svc.index(v94_begin_marker)
b = svc.index(v93_begin_marker, a)
v94 = svc[a:b]
assert v94.count("BRIDGE_REGISTER(0xAB, message_construct)") == 1
assert "BRIDGE_REGISTER(0xAA," not in v94
assert v94.count("BRIDGE_REGISTER(0xAC, message_kill)") == 1

dirs_path.write_text(dirs, encoding="utf-8")
vfs_path.write_text(vfs, encoding="utf-8")
print("MENUUI13 FS-DIRUID1 FIX2 semantic patch applied")
