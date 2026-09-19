#!/usr/bin/env python3
"""NATIVEBOOT2-B10 FSFORMAT1.

Apply on top of B9 FSPROPS1.

Observed B9 runtime:
  erofs.fsy/ecomp.fsy load contract OK
  EFsInitialisePropertiesFile(128) OK
  SetLocalDriveMapping(94) OK
  elocal + MountFileSystem('fat') startup contract OK
  then FileServer opcode 52 stalls.

EKA2 FileServer ABI:
  52 = EFsFormatOpen    (RFormat::Open)
  53 = EFsFormatNext    (RFormat::Next)
  26 = EFsFormatSubClose on EKA2

RM-356 EStart calls FormatDrive() for mappings whose startup flags require a
format (notably cold-boot paths). NATIVEBOOT2 uses host-backed virtual drives;
performing a destructive raw format would be wrong. B10 therefore implements
the real RFormat subsession contract while making formatting a non-destructive
virtual-board operation:
  Open: create a format subsession handle, return count=1
  Next: write count=0 and complete KErrNone
  Close: release the format subsession
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B10-FSFORMAT1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_fs_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "struct rm356_format_node" not in text:
        anchor = """    struct fs_path_case_insensitive_hasher {
"""
        insert = """    // NATIVEBOOT2-B10: lightweight EKA2 RFormat subsession state.
    struct rm356_format_node : public epoc::ref_count_object {
        std::u16string drive_name;
        std::uint32_t format_mode{ 0 };
        std::int32_t remaining_steps{ 0 };
    };

""" + anchor
        text = replace_once(text, anchor, insert, "format node declaration")

    if "void rm356_format_open(service::ipc_context *ctx);" not in text:
        anchor = """        void rm356_init_properties_file(service::ipc_context *ctx);
"""
        insert = anchor + """        void rm356_format_open(service::ipc_context *ctx);
        void rm356_format_next(service::ipc_context *ctx);
        void rm356_format_close(service::ipc_context *ctx);
"""
        text = replace_once(text, anchor, insert, "format method declarations")

    path.write_text(text, encoding="utf-8")

def patch_fs_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" in text:
        return

    # Register Open/Next in the normal client dispatch.
    dispatch_anchor = """            HANDLE_CLIENT_IPC(rm356_init_properties_file, epoc::fs_msg_init_properties_file, "RM356::InitialisePropertiesFile");

            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    dispatch_new = """            HANDLE_CLIENT_IPC(rm356_init_properties_file, epoc::fs_msg_init_properties_file, "RM356::InitialisePropertiesFile");
            // NATIVEBOOT2-B10: EKA2 RFormat startup contract.
            HANDLE_CLIENT_IPC(rm356_format_open, epoc::fs_msg_format_open, "RM356::FormatOpen");
            HANDLE_CLIENT_IPC(rm356_format_next, epoc::fs_msg_format_next, "RM356::FormatNext");

            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    text = replace_once(text, dispatch_anchor, dispatch_new, "format dispatch")

    # Opcode 26 is EKA1 BaseClose but EKA2 FormatSubClose.
    close_old = """        case epoc::fs_msg_base_close:
            if (ctx->sys->get_symbian_version_use() < epocver::eka2) {
                generic_close(ctx);
            }

            break;
"""
    close_new = """        case epoc::fs_msg_base_close:
            if (ctx->sys->get_symbian_version_use() < epocver::eka2) {
                generic_close(ctx);
            } else {
                // NATIVEBOOT2-B10: on EKA2 opcode 26 is EFsFormatSubClose.
                rm356_format_close(ctx);
            }
            break;
"""
    text = replace_once(text, close_old, close_new, "format close dispatch")

    impl_anchor = """    void fs_server_client::file_lock(service::ipc_context *ctx) {
"""
    impl = r'''    void fs_server_client::rm356_format_open(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto drive_name = ctx->get_argument_value<std::u16string>(0);
        const auto format_mode = ctx->get_argument_value<std::uint32_t>(1);
        if (!drive_name || !format_mode) {
            LOG_ERROR(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_FORMAT_OPEN_BAD] drive={} mode={}",
                drive_name.has_value() ? 1 : 0, format_mode.value_or(0));
            ctx->complete(epoc::error_argument);
            return;
        }

        fs_server *serv = server<fs_server>();
        rm356_format_node *node = serv->make_new<rm356_format_node>();
        node->drive_name = *drive_name;
        node->format_mode = *format_mode;
        node->remaining_steps = 1;

        const epoc::handle format_handle = obj_table_.add(node);
        const std::int32_t handle_i = static_cast<std::int32_t>(format_handle);
        const std::int32_t count = 1;

        ctx->write_data_to_descriptor_argument<std::int32_t>(2, count);
        ctx->write_data_to_descriptor_argument<std::int32_t>(3, handle_i);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_FORMAT_OPEN] drive='{}' mode=0x{:08X} handle={} count={} action=NON_DESTRUCTIVE",
            common::ucs2_to_utf8(*drive_name), *format_mode, handle_i, count);
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_format_next(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto handle = ctx->get_argument_value<std::int32_t>(3);
        if (!handle) {
            ctx->complete(epoc::error_argument);
            return;
        }

        rm356_format_node *node = obj_table_.get<rm356_format_node>(*handle);
        if (!node) {
            LOG_ERROR(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_FORMAT_NEXT_BAD] handle={}", *handle);
            ctx->complete(epoc::error_bad_handle);
            return;
        }

        node->remaining_steps = 0;
        const std::int32_t count = 0;
        ctx->write_data_to_descriptor_argument<std::int32_t>(0, count);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_FORMAT_NEXT] drive='{}' handle={} count={} completion=KErrNone",
            common::ucs2_to_utf8(node->drive_name), *handle, count);
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_format_close(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto handle = ctx->get_argument_value<std::int32_t>(3);
        if (!handle) {
            ctx->complete(epoc::error_argument);
            return;
        }

        rm356_format_node *node = obj_table_.get<rm356_format_node>(*handle);
        if (!node) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_FORMAT_CLOSE_BAD] handle={}", *handle);
            ctx->complete(epoc::error_bad_handle);
            return;
        }

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_FORMAT_CLOSE] drive='{}' handle={} completion=KErrNone",
            common::ucs2_to_utf8(node->drive_name), *handle);
        obj_table_.remove(*handle);
        ctx->complete(epoc::error_none);
    }

'''
    text = replace_once(text, impl_anchor, impl + impl_anchor, "format implementation")
    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b10_fsformat1.py <upstream-root>")

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
            fail(f"missing B9 baseline file: {p}")

    if "[NBOOT2][RM356_FS_PROPERTIES]" not in fs_cpp.read_text(encoding="utf-8"):
        fail("B9 FSPROPS1 marker missing")
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
        "struct rm356_format_node",
        "[NBOOT2][RM356_FS_FORMAT_OPEN]",
        "[NBOOT2][RM356_FS_FORMAT_NEXT]",
        "[NBOOT2][RM356_FS_FORMAT_CLOSE]",
        "epoc::fs_msg_format_open",
        "epoc::fs_msg_format_next",
        "rm356_format_close(ctx)",
    ):
        if gate not in (h + c):
            fail(f"FS format gate missing: {gate}")

    for gate in (
        "[NBOOT2][RM356_FS_PROPERTIES]",
        "[NBOOT2][RM356_FS_MAPPING]",
        "[NBOOT2][RM356_FS_STARTUP_COMPLETE]",
        "[NBOOT2][RM356_FS_SYSTEM_DRIVE]",
    ):
        if gate not in c:
            fail(f"prior FileServer contract lost: {gate}")

    print("NATIVEBOOT2-B10 FSFORMAT1 applied")
    print("FileServer_52=RFormat_Open")
    print("FileServer_53=RFormat_Next")
    print("FileServer_26=RFormat_Close_on_EKA2")
    print("Format_action=NON_DESTRUCTIVE_virtual_board")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
