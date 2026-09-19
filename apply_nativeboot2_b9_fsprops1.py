#!/usr/bin/env python3
"""NATIVEBOOT2-B9 FSPROPS1.

Apply on top of B8 LOADERFSY1.

Observed B8 runtime:
  Loader::ELoadFileSystem(6) succeeds for:
    erofs.fsy
    ecomp.fsy
  EStart opens Z:\SYS\DATA\ESTARTCOMP.TXT
  FileServer then receives opcode 128 and stalls.

Symbian FileServer ABI identifies opcode 128 as EFsInitialisePropertiesFile.
EStart passes the ROM address + length of ESTARTCOMP.TXT and a boolean indicating
that the address is ROM-backed. Native F32 uses this to initialise its cache/
properties subsystem. NATIVEBOOT2 keeps FileServer HLE, so the correct hybrid
contract is to validate/trace the request and acknowledge KErrNone. The actual
drive mapping remains driven by EStart's subsequent SetLocalDriveMapping call.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B9-FSPROPS1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_fs_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "rm356_init_properties_file" in text:
        return

    anchor = """        void rm356_set_system_drive(service::ipc_context *ctx);
"""
    replacement = anchor + """        void rm356_init_properties_file(service::ipc_context *ctx);
"""
    text = replace_once(text, anchor, replacement, "fs header init properties declaration")
    path.write_text(text, encoding="utf-8")

def patch_fs_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_FS_PROPERTIES]" in text:
        return

    dispatch_anchor = """            HANDLE_CLIENT_IPC(rm356_set_system_drive, epoc::fs_msg_set_system_drive, "RM356::SetSystemDrive");

            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    dispatch_new = """            HANDLE_CLIENT_IPC(rm356_set_system_drive, epoc::fs_msg_set_system_drive, "RM356::SetSystemDrive");
            // NATIVEBOOT2-B9: EStart passes ESTARTCOMP.TXT ROM pointer/length here.
            HANDLE_CLIENT_IPC(rm356_init_properties_file, epoc::fs_msg_init_properties_file, "RM356::InitialisePropertiesFile");

            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    text = replace_once(text, dispatch_anchor, dispatch_new, "fs dispatch properties file")

    impl_anchor = """    void fs_server_client::file_lock(service::ipc_context *ctx) {
"""
    impl = r'''    void fs_server_client::rm356_init_properties_file(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto rom_ptr = ctx->get_argument_value<address>(0);
        const auto length = ctx->get_argument_value<std::int32_t>(1);
        const auto is_rom = ctx->get_argument_value<std::int32_t>(2);

        if (!rom_ptr || !length || !is_rom || (*length < 0)) {
            LOG_ERROR(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_PROPERTIES_BAD] ptr=0x{:08X} len={} is_rom={}",
                rom_ptr.value_or(0), length.value_or(-1), is_rom.value_or(-1));
            ctx->complete(epoc::error_argument);
            return;
        }

        // Native F32 parses cache/properties directives from the ROM-resident
        // ESTARTCOMP.TXT buffer. EKA2L1's HLE FileServer has no native F32 cache
        // manager to initialise; acknowledging this request is the correct board
        // adapter boundary. Subsequent drive topology still comes from EStart.
        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_PROPERTIES] rom_ptr=0x{:08X} len={} is_rom={} completion=KErrNone",
            *rom_ptr, *length, *is_rom);
        ctx->complete(epoc::error_none);
    }

'''
    text = replace_once(text, impl_anchor, impl + impl_anchor, "fs properties implementation")
    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b9_fsprops1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fs_h = up / "src/emu/services/include/services/fs/fs.h"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    loader_cpp = up / "src/emu/services/src/loader/loader.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (fs_h, fs_cpp, loader_cpp, svc, hal, state, root):
        if not p.is_file():
            fail(f"missing B8 baseline file: {p}")

    if "[NBOOT2][RM356_LOADER_FSY]" not in loader_cpp.read_text(encoding="utf-8"):
        fail("B8 Loader FSY marker missing")
    if "[NBOOT2][RM356_SET_GLOBAL_USERDATA]" not in svc.read_text(encoding="utf-8"):
        fail("B7 locale ABI marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 StartupReason marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_fs_header(fs_h)
    patch_fs_cpp(fs_cpp)

    h = fs_h.read_text(encoding="utf-8")
    c = fs_cpp.read_text(encoding="utf-8")
    for gate in (
        "void rm356_init_properties_file(service::ipc_context *ctx);",
        "[NBOOT2][RM356_FS_PROPERTIES]",
        "epoc::fs_msg_init_properties_file",
        "RM356::InitialisePropertiesFile",
    ):
        if gate not in (h + c):
            fail(f"FileServer properties gate missing: {gate}")

    # Preserve previous startup contract markers.
    for gate in (
        "[NBOOT2][RM356_FS_MAPPING]",
        "[NBOOT2][RM356_FS_STARTUP_COMPLETE]",
        "[NBOOT2][RM356_FS_SYSTEM_DRIVE]",
        "[NBOOT2][RM356_FS_UNKNOWN]",
    ):
        if gate not in c:
            fail(f"B6 FileServer gate lost: {gate}")

    print("NATIVEBOOT2-B9 FSPROPS1 applied")
    print("FileServer_opcode_128=EFsInitialisePropertiesFile")
    print("ESTARTCOMP_ROM_properties=ACK_KErrNone")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
