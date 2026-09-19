#!/usr/bin/env python3
"""NATIVEBOOT2-B8 LOADERFSY1.

Apply on top of B7 LOCALEABI1.

Observed B7 runtime:
  RM356 SetGlobalUserData index 0/1 succeeds.
  ESTART_6 disappears.
  Immediately after:
    Unimplemented IPC call: 0x6 for server: !Loader
  and EStart waits until the user exits Emulator.

Symbian loader ABI:
  ELoadFileSystem = 6
  RFs::AddFileSystem -> RLoader::SendReceive(ELoadFileSystem,
      TIpcArgs(0, &aFileName, 0))

On real Symbian the Loader loads the .fsy library and asks FileServer to
install it. NATIVEBOOT2 deliberately keeps FileServer HLE, so B8 models the
same startup contract by acknowledging the requested .fsy as installed.
It logs the exact requested name so later RM-356 startup mapping can stay
firmware-driven.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B8-LOADERFSY1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_loader_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "void load_file_system(service::ipc_context &context);" in text:
        return
    old = """        void load_locale(service::ipc_context &context);

    public:
"""
    new = """        void load_locale(service::ipc_context &context);

        // NATIVEBOOT2-B8: RM-356 EStart RFs::AddFileSystem startup contract.
        void load_file_system(service::ipc_context &context);

    public:
"""
    text = replace_once(text, old, new, "loader header load_file_system")
    path.write_text(text, encoding="utf-8")

def patch_loader_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_LOADER_FSY]" in text:
        return

    old_func = """    void loader_server::load_locale(service::ipc_context &context) {
        context.complete(epoc::error_not_found);
    }

    loader_server::loader_server(system *sys)
"""
    new_func = """    void loader_server::load_locale(service::ipc_context &context) {
        context.complete(epoc::error_not_found);
    }

    void loader_server::load_file_system(service::ipc_context &context) {
        // Symbian ELoadFileSystem (opcode 6):
        // arg1 is the requested FSY filename. Native EStart expects this call
        // to complete before continuing LocalDriveInit(). The actual backing
        // filesystem is provided by EKA2L1's HLE FileServer in NATIVEBOOT2.
        std::optional<utf16_str> fsy_name = context.get_argument_value<utf16_str>(1);
        if (!fsy_name.has_value()) {
            LOG_ERROR(SERVICE_LOADER,
                "[NBOOT2][RM356_LOADER_FSY_BADARGS] arg1 is not a valid descriptor");
            context.complete(epoc::error_argument);
            return;
        }

        LOG_WARN(SERVICE_LOADER,
            "[NBOOT2][RM356_LOADER_FSY] request='{}' action=HLE_FileServer_install completion=KErrNone",
            common::ucs2_to_utf8(fsy_name.value()));
        context.complete(epoc::error_none);
    }

    loader_server::loader_server(system *sys)
"""
    text = replace_once(text, old_func, new_func, "loader fsy implementation")

    old_reg = """        REGISTER_IPC(loader_server, load_locale, ELoadLocale, "Loader::LoadLocale");
        REGISTER_IPC(loader_server, load_logical_device, ELoadLogicalDevice, "Loader::LoadLogicalDevice");
"""
    new_reg = """        REGISTER_IPC(loader_server, load_locale, ELoadLocale, "Loader::LoadLocale");
        // NATIVEBOOT2-B8: EStart LocalDriveInit() uses opcode 6.
        REGISTER_IPC(loader_server, load_file_system, ELoadFileSystem, "Loader::LoadFileSystem");
        REGISTER_IPC(loader_server, load_logical_device, ELoadLogicalDevice, "Loader::LoadLogicalDevice");
"""
    text = replace_once(text, old_reg, new_reg, "loader fsy registration")

    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b8_loaderfsy1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    loader_h = up / "src/emu/services/include/services/loader/loader.h"
    loader_cpp = up / "src/emu/services/src/loader/loader.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (loader_h, loader_cpp, svc, hal, fs, state, root):
        if not p.is_file():
            fail(f"missing B7 baseline file: {p}")

    if "[NBOOT2][RM356_SET_GLOBAL_USERDATA]" not in svc.read_text(encoding="utf-8"):
        fail("B7 locale ABI marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 StartupReason marker missing")
    if "[NBOOT2][RM356_FS_MAPPING]" not in fs.read_text(encoding="utf-8"):
        fail("B6 FileServer BSP marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_loader_header(loader_h)
    patch_loader_cpp(loader_cpp)

    h = loader_h.read_text(encoding="utf-8")
    c = loader_cpp.read_text(encoding="utf-8")
    for gate in (
        "void load_file_system(service::ipc_context &context);",
        "[NBOOT2][RM356_LOADER_FSY]",
        "REGISTER_IPC(loader_server, load_file_system, ELoadFileSystem",
        "context.complete(epoc::error_none)",
    ):
        if gate not in (h + c):
            fail(f"Loader FSY gate missing: {gate}")

    svc_body = svc.read_text(encoding="utf-8")
    a = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = svc_body.find("\n    };", a)
    v94 = svc_body[a:b]
    for gate in (
        "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)",
        "BRIDGE_REGISTER(0x83, logical_channel_create_v95)",
        "BRIDGE_REGISTER(0xE4, set_global_userdata)",
        "BRIDGE_REGISTER(0xAB, message_construct)",
        "BRIDGE_REGISTER(0xAC, message_kill)",
    ):
        if gate not in v94:
            fail(f"EPOC94 invariant lost: {gate}")
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")

    print("NATIVEBOOT2-B8 LOADERFSY1 applied")
    print("Loader_IPC_0x6=ELoadFileSystem")
    print("Loader_FSY=HLE_FileServer_install_ack")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
