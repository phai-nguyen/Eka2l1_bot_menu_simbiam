#!/usr/bin/env python3
"""NATIVEBOOT2-B6 RM356-BSP1.

Apply on top of B5 MEDIAHAL1.

This is the first consolidated RM-356 virtual-board adapter.  It keeps EKA2L1's
CPU/kernel/memory/VFS, while satisfying the EKA2 BSP contracts that the real
5800 EStart expects before it can create domainSrv/SysStart.

B6 scope:
- Kernel HAL StartupReason -> EStartupCold.
- FileServer startup contract:
    Add/Mount/Swap FSY/extension requests are acknowledged in native-phone mode
    because EKA2L1 has already mounted the host-backed device drives.
    SetLocalDriveMapping parses/stores the real 16-entry mapping descriptor.
    SetSystemDrive updates the HLE FileServer property/default path.
    StartupInitComplete completes the async request.
    FinaliseDrive is acknowledged for the virtual media.
    Startup configuration / composite / scan operations are traced + acked.
- Unknown native-boot FileServer opcodes get a dedicated trace before returning
  KErrNotSupported.

Preserves:
- B5 Media DriveInfo ABI/mask 0x00000E45
- B4 Custom.ldd
- B3 NokiaISC async completion
- B2 EPOC94 0x83/0x0A and 0xAA/0xAB/0xAC invariants
- EMUHUB1 / MENUUI36 / NOJAVA / MANIC3.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B6-RM356-BSP1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_hal(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_STARTUP_REASON]" in text:
        return

    method_anchor = """        int hardware_floating_point(int *a1, int *a2, const std::uint16_t device_num) {
"""
    method = """        int startup_reason(int *a1, int *, const std::uint16_t) {
            if (!a1) {
                return epoc::error_argument;
            }

            // TMachineStartupType::EStartupCold == 0.  EStart uses this to
            // decide whether cold-start filesystem actions are required.
            *a1 = 0;
            LOG_WARN(SYSTEM, "[NBOOT2][RM356_STARTUP_REASON] value=EStartupCold(0)");
            return epoc::error_none;
        }

"""
    text = replace_once(text, method_anchor, method + method_anchor, "kernel HAL StartupReason method")

    reg_anchor = """            REGISTER_HAL_FUNC(kernel_hal_memory_info, kern_hal, memory_info);
"""
    reg = reg_anchor + """            REGISTER_HAL_FUNC(kernel_hal_startup_reason, kern_hal, startup_reason);
"""
    text = replace_once(text, reg_anchor, reg, "kernel HAL StartupReason registration")
    path.write_text(text, encoding="utf-8")

def patch_fs_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "#include <array>" not in text:
        text = replace_once(text, "#include <atomic>\n", "#include <array>\n#include <atomic>\n", "fs header array include")

    if "rm356_startup_mount_ack" not in text:
        anchor = """        void filesystem_name(service::ipc_context *ctx);

"""
        methods = anchor + """        // NATIVEBOOT2-B6 RM356-BSP1 startup-only FileServer contract.
        void rm356_startup_mount_ack(service::ipc_context *ctx);
        void rm356_set_local_drive_mapping(service::ipc_context *ctx);
        void rm356_startup_init_complete(service::ipc_context *ctx);
        void rm356_finalise_drive(service::ipc_context *ctx);
        void rm356_set_system_drive(service::ipc_context *ctx);

"""
        text = replace_once(text, anchor, methods, "fs client RM356 declarations")

    if "rm356_local_drive_mapping_" not in text:
        anchor = """        service::property *system_drive_prop;
        std::u16string default_sys_path;
"""
        fields = anchor + """        // NATIVEBOOT2-B6: last mapping requested by native EStart.
        std::array<std::int32_t, 16> rm356_local_drive_mapping_{};
        std::int32_t rm356_local_drive_mapping_operation_{ -1 };
        bool rm356_startup_init_complete_{ false };
"""
        text = replace_once(text, anchor, fields, "fs server RM356 state")

    path.write_text(text, encoding="utf-8")

def patch_fs_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_FS_MAPPING]" in text:
        return

    if "#include <config/config.h>" not in text:
        text = replace_once(text, "#include <kernel/kernel.h>\n",
                            "#include <kernel/kernel.h>\n#include <config/config.h>\n",
                            "fs config include")

    dispatch_anchor = """            HANDLE_CLIENT_IPC(filesystem_name, epoc::fs_msg_filesystem_name, "Fs::IsFileOpen");
            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    dispatch = """            HANDLE_CLIENT_IPC(filesystem_name, epoc::fs_msg_filesystem_name, "Fs::IsFileOpen");

            // NATIVEBOOT2-B6 RM356-BSP1.  The VFS drives are mounted by the
            // emulator before EStart runs, so these startup FSY operations are
            // board-adapter acknowledgements rather than host filesystem mounts.
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_add_filesystem, "RM356::AddFileSystem");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_remove_filesystem, "RM356::RemoveFileSystem");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_mount_filesystem, "RM356::MountFileSystem");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_dismount_filesystem, "RM356::DismountFileSystem");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_scan_drive, "RM356::ScanDrive");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_add_ext, "RM356::AddExtension");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_mount_ext, "RM356::MountExtension");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_dismount_ext, "RM356::DismountExtension");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_remove_ext, "RM356::RemoveExtension");
            HANDLE_CLIENT_IPC(rm356_startup_init_complete, epoc::fs_msg_startup_init_complete, "RM356::StartupInitComplete");
            HANDLE_CLIENT_IPC(rm356_set_local_drive_mapping, epoc::fs_msg_set_local_drive_mapping, "RM356::SetLocalDriveMapping");
            HANDLE_CLIENT_IPC(rm356_finalise_drive, epoc::fs_msg_finalise_drive, "RM356::FinaliseDrive");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_swap_filesystem, "RM356::SwapFileSystem");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_mount_filesystem_scan, "RM356::MountFileSystemAndScan");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_set_startup_config, "RM356::SetStartupConfiguration");
            HANDLE_CLIENT_IPC(rm356_startup_mount_ack, epoc::fs_msg_add_composite_mount, "RM356::AddCompositeMount");
            HANDLE_CLIENT_IPC(rm356_set_system_drive, epoc::fs_msg_set_system_drive, "RM356::SetSystemDrive");

            HANDLE_CLIENT_IPC(notify_dismount, epoc::fs_msg_notify_dismount, "Fs::NotifyDismount");
"""
    text = replace_once(text, dispatch_anchor, dispatch, "RM356 FS dispatch")

    default_log_anchor = '            LOG_ERROR(SERVICE_EFSRV, "Unknown FSServer client opcode {}!", ctx->msg->function);\n'
    default_log_new = """            if (ctx->sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][RM356_FS_UNKNOWN] opcode={} a0=0x{:08X} a1=0x{:08X} a2=0x{:08X} a3=0x{:08X}",
                    ctx->msg->function, ctx->msg->args.args[0], ctx->msg->args.args[1],
                    ctx->msg->args.args[2], ctx->msg->args.args[3]);
            } else {
                LOG_ERROR(SERVICE_EFSRV, "Unknown FSServer client opcode {}!", ctx->msg->function);
            }
"""
    text = replace_once(text, default_log_anchor, default_log_new, "RM356 FS unknown trace")

    impl_anchor = """    void fs_server_client::file_lock(service::ipc_context *ctx) {
"""
    impl = r'''    namespace {
        struct rm356_local_drive_mapping_info {
            std::int32_t mapping[16];
            std::int32_t operation;
        };
        static_assert(sizeof(rm356_local_drive_mapping_info) == 68,
            "TLocalDriveMappingInfo ABI size mismatch");

        bool rm356_native_boot(service::ipc_context *ctx) {
            return ctx && ctx->sys && ctx->sys->get_config()->native_phone_boot;
        }
    }

    void fs_server_client::rm356_startup_mount_ack(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto name0 = ctx->get_argument_value<std::u16string>(0);
        const auto name1 = ctx->get_argument_value<std::u16string>(1);
        const auto arg0 = ctx->get_argument_value<std::int32_t>(0);
        const auto arg1 = ctx->get_argument_value<std::int32_t>(1);
        const auto arg2 = ctx->get_argument_value<std::int32_t>(2);
        const auto arg3 = ctx->get_argument_value<std::int32_t>(3);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_BOOT_ACK] opcode={} name0='{}' name1='{}' i0={} i1={} i2={} i3={}",
            ctx->msg->function,
            name0 ? common::ucs2_to_utf8(*name0) : std::string(""),
            name1 ? common::ucs2_to_utf8(*name1) : std::string(""),
            arg0.value_or(-2147483647), arg1.value_or(-2147483647),
            arg2.value_or(-2147483647), arg3.value_or(-2147483647));

        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_set_local_drive_mapping(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto mapping = ctx->get_argument_data_from_descriptor<rm356_local_drive_mapping_info>(0);
        if (!mapping) {
            LOG_ERROR(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_MAPPING_BAD] size={}", ctx->get_argument_data_size(0));
            ctx->complete(epoc::error_bad_descriptor);
            return;
        }

        fs_server *serv = server<fs_server>();
        for (std::size_t i = 0; i < serv->rm356_local_drive_mapping_.size(); ++i) {
            serv->rm356_local_drive_mapping_[i] = mapping->mapping[i];
        }
        serv->rm356_local_drive_mapping_operation_ = mapping->operation;

        std::string map_text;
        for (std::size_t i = 0; i < 16; ++i) {
            if (!map_text.empty()) {
                map_text += ",";
            }
            map_text += std::to_string(mapping->mapping[i]);
        }

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_MAPPING] operation={} mapping=[{}]",
            mapping->operation, map_text);
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_startup_init_complete(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        server<fs_server>()->rm356_startup_init_complete_ = true;
        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_STARTUP_COMPLETE] completing EStart StartupInitComplete KErrNone");
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_finalise_drive(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto drive = ctx->get_argument_value<std::int32_t>(0);
        const auto mode = ctx->get_argument_value<std::int32_t>(1);
        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_FINALISE] drive={} mode={} completion=KErrNone",
            drive.value_or(-1), mode.value_or(-1));
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::rm356_set_system_drive(service::ipc_context *ctx) {
        if (!rm356_native_boot(ctx)) {
            ctx->complete(epoc::error_not_supported);
            return;
        }

        const auto drive = ctx->get_argument_value<std::int32_t>(0);
        if (!drive || (*drive < static_cast<std::int32_t>(drive_a))
            || (*drive >= static_cast<std::int32_t>(drive_count))) {
            LOG_ERROR(SERVICE_EFSRV,
                "[NBOOT2][RM356_FS_SYSTEM_DRIVE_BAD] drive={}", drive.value_or(-1));
            ctx->complete(epoc::error_argument);
            return;
        }

        fs_server *serv = server<fs_server>();
        serv->system_drive_prop->set_int(*drive);
        std::u16string default_path = u"C:\\";
        default_path[0] = drive_to_char16(static_cast<drive_number>(*drive));
        serv->default_sys_path = default_path;

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][RM356_FS_SYSTEM_DRIVE] drive={} path={}",
            *drive, common::ucs2_to_utf8(default_path));
        ctx->complete(epoc::error_none);
    }

'''
    text = replace_once(text, impl_anchor, impl + impl_anchor, "RM356 FS implementations")
    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b6_rm356_bsp1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    hal_cpp = up / "src/emu/system/src/hal.cpp"
    hal_h = up / "src/emu/system/include/system/hal.h"
    fs_h = up / "src/emu/services/include/services/fs/fs.h"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    custom = up / "src/emu/ldd/src/custom/custom.cpp"
    nokiaisc = up / "src/emu/ldd/src/nokiaisc/nokiaisc.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (hal_cpp, hal_h, fs_h, fs_cpp, custom, nokiaisc, svc, state, root):
        if not p.is_file():
            fail(f"missing B5 baseline file: {p}")

    if "[NBOOT2][MEDIA_DRIVE_INFO]" not in hal_cpp.read_text(encoding="utf-8"):
        fail("B5 Media HAL marker missing")
    if "hal_category_media = 2" not in hal_h.read_text(encoding="utf-8"):
        fail("B5 Media HAL category missing")
    if "[NBOOT2][CUSTOM_CONTROL]" not in custom.read_text(encoding="utf-8"):
        fail("B4 Custom.ldd marker missing")
    if "[NBOOT2][NOKIAISC_INIT_COMPLETE]" not in nokiaisc.read_text(encoding="utf-8"):
        fail("B3 NokiaISC marker missing")
    if "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI" not in svc.read_text(encoding="utf-8"):
        fail("B2 EPOC94 ABI marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_hal(hal_cpp)
    patch_fs_header(fs_h)
    patch_fs_cpp(fs_cpp)

    hc = hal_cpp.read_text(encoding="utf-8")
    fh = fs_h.read_text(encoding="utf-8")
    fc = fs_cpp.read_text(encoding="utf-8")
    if 'std::u16string default_path = u"C:\\\\";' not in fc:
        fail("escaped C:\\\\ default_path literal missing")
    if 'std::u16string default_path = u"C:\\\";' in fc:
        fail("broken single-backslash C: default_path literal present")

    for gate in (
        "[NBOOT2][RM356_STARTUP_REASON]",
        "REGISTER_HAL_FUNC(kernel_hal_startup_reason, kern_hal, startup_reason)",
        "[NBOOT2][MEDIA_DRIVE_INFO]",
    ):
        if gate not in hc:
            fail(f"HAL gate missing: {gate}")

    for gate in (
        "rm356_local_drive_mapping_",
        "rm356_startup_mount_ack",
        "rm356_set_local_drive_mapping",
        "rm356_startup_init_complete",
    ):
        if gate not in fh:
            fail(f"FS header gate missing: {gate}")

    for gate in (
        "[NBOOT2][RM356_FS_BOOT_ACK]",
        "[NBOOT2][RM356_FS_MAPPING]",
        "[NBOOT2][RM356_FS_STARTUP_COMPLETE]",
        "[NBOOT2][RM356_FS_FINALISE]",
        "[NBOOT2][RM356_FS_SYSTEM_DRIVE]",
        "[NBOOT2][RM356_FS_UNKNOWN]",
        "static_assert(sizeof(rm356_local_drive_mapping_info) == 68",
        "epoc::fs_msg_set_local_drive_mapping",
        "epoc::fs_msg_startup_init_complete",
        "epoc::fs_msg_finalise_drive",
        "epoc::fs_msg_set_system_drive",
    ):
        if gate not in fc:
            fail(f"FS cpp gate missing: {gate}")

    # Preserve B5 media topology.
    if "RM356_REGISTERED_DRIVE_MASK = 0x00000E45" not in hc:
        fail("RM-356 drive mask lost")

    # Preserve RM-356 EPOC94 ABI invariants.
    svc_body = svc.read_text(encoding="utf-8")
    a = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = svc_body.find("\n    };", a)
    v94 = svc_body[a:b]
    if "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)" not in v94:
        fail("EPOC94 0x0A mapping lost")
    if "BRIDGE_REGISTER(0x83, logical_channel_create_v95)" not in v94:
        fail("EPOC94 0x83 mapping lost")
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)" not in v94:
        fail("EPOC94 0xAB invariant lost")
    if "BRIDGE_REGISTER(0xAC, message_kill)" not in v94:
        fail("EPOC94 0xAC invariant lost")

    print("NATIVEBOOT2-B6 RM356-BSP1 applied")
    print("StartupReason=EStartupCold")
    print("FileServer_startup_mounts=HOST_VFS_ACK")
    print("SetLocalDriveMapping=PARSE_STORE_68B")
    print("StartupInitComplete=ASYNC_COMPLETE_KErrNone")
    print("FinaliseDrive=VIRTUAL_MEDIA_ACK")
    print("SetSystemDrive=PROPERTY_AND_DEFAULT_PATH")
    print("UnknownNativeFS=TRACE_THEN_KErrNotSupported")
    print("MEDIAHAL1=CUSTOMLDD1=NOKIAISC2=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
