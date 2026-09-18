#!/usr/bin/env python3
"""MENUUI26 FSRESERVE1: implement RFs reserved-space IPCs used by UniEditor.

MENUUI25 device evidence:
- Messaging New message reaches AppList opcode 46/48 successfully.
- UniEditor UID 0x102072D8 launches and renames thread to "Msg. editor".
- After loading z:\\resource\\msgeditorappui.r01, !FileServer receives opcode 100.
- EKA2L1 logs "Unknown FSServer client opcode 100!" and the synchronous request
  never completes; the editor never presents its window.

Symbian mapping:
100 = EFsReserveDriveSpace
101 = EFsGetReserveAccess
102 = EFsReleaseReserveAccess

The original server keeps reserved-space/access state per RFs session. EKA2L1's
VFS does not model physical free-space reservation, so this compatibility layer
preserves the observable session semantics and limits while leaving VFS capacity
unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI26 FSRESERVE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n = text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui26_fsreserve1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fs_h = up / "src/emu/services/include/services/fs/fs.h"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    fs_op = up / "src/emu/services/include/services/fs/op.h"
    applist = up / "src/emu/services/src/applist/applist.cpp"
    oom = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (fs_h, fs_cpp, fs_op, applist, oom, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    fs_text = fs_cpp.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE:" in fs_text:
        print("MENUUI26 FSRESERVE1 already present")
        return

    # Proven lineage gates.
    if "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI25 APPSERVICE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER:" not in oom.read_text(encoding="utf-8"):
        fail("MENUUI24 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI23 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:" not in kernel.read_text(encoding="utf-8"):
        fail("SCHEDRUN1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:" not in svc.read_text(encoding="utf-8"):
        fail("sync diagnostics missing")
    if "MANIC_MODALFIX1" not in root.read_text(encoding="utf-8"):
        fail("MANIC3 baseline missing")

    op = fs_op.read_text(encoding="utf-8")
    for name in ("fs_msg_reserve_drive_space", "fs_msg_get_reserve_access", "fs_msg_release_reserve_access"):
        if name not in op:
            fail(f"missing FS opcode enum: {name}")

    # fs.h: per-session reserved-space/access state and handlers.
    h = fs_h.read_text(encoding="utf-8")
    h = replace_once(
        h,
        "#include <atomic>\n",
        "#include <array>\n#include <atomic>\n",
        "array include",
    )
    old = """    struct fs_server_client : public service::typical_session {
        std::u16string ss_path;

        fs_node *get_file_node(const int handle) {
"""
    new = """    struct fs_server_client : public service::typical_session {
        std::u16string ss_path;

        // Symbian RFs reserve-space bookkeeping is session scoped.
        std::array<std::int32_t, drive_z + 1> reserved_space_{};
        std::array<bool, drive_z + 1> reserve_access_{};

        fs_node *get_file_node(const int handle) {
"""
    h = replace_once(h, old, new, "session reserve state")

    old = """        void volume(service::ipc_context *ctx);
        void is_file_opened(service::ipc_context *ctx);
        void filesystem_name(service::ipc_context *ctx);
"""
    new = """        void volume(service::ipc_context *ctx);
        void reserve_drive_space(service::ipc_context *ctx);
        void get_reserve_access(service::ipc_context *ctx);
        void release_reserve_access(service::ipc_context *ctx);
        void is_file_opened(service::ipc_context *ctx);
        void filesystem_name(service::ipc_context *ctx);
"""
    h = replace_once(h, old, new, "reserve handler declarations")
    fs_h.write_text(h, encoding="utf-8")

    # fs.cpp: mapping assertions, dispatch and implementation.
    text = fs_text
    text = replace_once(
        text,
        "namespace eka2l1 {\n",
        """namespace eka2l1 {
    static_assert(epoc::fs_msg_reserve_drive_space == 100,
        "MENUUI26 EFsReserveDriveSpace opcode mismatch");
    static_assert(epoc::fs_msg_get_reserve_access == 101,
        "MENUUI26 EFsGetReserveAccess opcode mismatch");
    static_assert(epoc::fs_msg_release_reserve_access == 102,
        "MENUUI26 EFsReleaseReserveAccess opcode mismatch");

""",
        "FS opcode assertions",
    )

    old = """            HANDLE_CLIENT_IPC(volume, epoc::fs_msg_volume, "Fs::Volume");
            HANDLE_CLIENT_IPC(query_drive_info_ext, epoc::fs_msg_query_volume_info_ext, "Fs::QueryVolumeInfoExt");
"""
    new = """            HANDLE_CLIENT_IPC(volume, epoc::fs_msg_volume, "Fs::Volume");
            HANDLE_CLIENT_IPC(reserve_drive_space, epoc::fs_msg_reserve_drive_space, "Fs::ReserveDriveSpace");
            HANDLE_CLIENT_IPC(get_reserve_access, epoc::fs_msg_get_reserve_access, "Fs::GetReserveAccess");
            HANDLE_CLIENT_IPC(release_reserve_access, epoc::fs_msg_release_reserve_access, "Fs::ReleaseReserveAccess");
            HANDLE_CLIENT_IPC(query_drive_info_ext, epoc::fs_msg_query_volume_info_ext, "Fs::QueryVolumeInfoExt");
"""
    text = replace_once(text, old, new, "FS reserve dispatch")

    anchor = """    void fs_server_client::replace(service::ipc_context *ctx) {
"""
    impl = r'''    static bool valid_reserve_drive(const std::int32_t drive) {
        return drive >= static_cast<std::int32_t>(drive_a)
            && drive <= static_cast<std::int32_t>(drive_z);
    }

    void fs_server_client::reserve_drive_space(service::ipc_context *ctx) {
        static constexpr std::int32_t KMaxSessionDriveReserved = 0x10000;

        const auto drive = ctx->get_argument_value<std::int32_t>(0);
        const auto space = ctx->get_argument_value<std::int32_t>(1);

        if (!drive.has_value() || !space.has_value()
            || !valid_reserve_drive(drive.value())
            || space.value() < 0 || space.value() > KMaxSessionDriveReserved) {
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=argument opcode=100 drive={} space={}",
                drive.value_or(-1), space.value_or(-1));
            ctx->complete(epoc::error_argument);
            return;
        }

        const std::size_t idx = static_cast<std::size_t>(drive.value());
        if (reserve_access_[idx]) {
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=in_use opcode=100 drive={} space={}",
                drive.value(), space.value());
            ctx->complete(epoc::error_in_use);
            return;
        }

        // EKA2L1's VFS does not expose a physical free-space reservation primitive.
        // Preserve RFs per-session semantics; the existing volume model reports ample
        // free space, so a valid <=64 KiB reservation succeeds.
        reserved_space_[idx] = space.value();

        LOG_WARN(SERVICE_EFSRV,
            "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=complete opcode=100 drive={} space={}",
            drive.value(), space.value());
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::get_reserve_access(service::ipc_context *ctx) {
        const auto drive = ctx->get_argument_value<std::int32_t>(0);
        if (!drive.has_value() || !valid_reserve_drive(drive.value())) {
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=argument opcode=101 drive={}",
                drive.value_or(-1));
            ctx->complete(epoc::error_argument);
            return;
        }

        const std::size_t idx = static_cast<std::size_t>(drive.value());
        if (reserved_space_[idx] <= 0) {
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=permission_denied opcode=101 drive={}",
                drive.value());
            ctx->complete(epoc::error_permission_denied);
            return;
        }

        reserve_access_[idx] = true;
        LOG_WARN(SERVICE_EFSRV,
            "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=complete opcode=101 drive={} reserved={}",
            drive.value(), reserved_space_[idx]);
        ctx->complete(epoc::error_none);
    }

    void fs_server_client::release_reserve_access(service::ipc_context *ctx) {
        const auto drive = ctx->get_argument_value<std::int32_t>(0);
        if (!drive.has_value() || !valid_reserve_drive(drive.value())) {
            LOG_WARN(SERVICE_EFSRV,
                "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=argument opcode=102 drive={}",
                drive.value_or(-1));
            ctx->complete(epoc::error_argument);
            return;
        }

        const std::size_t idx = static_cast<std::size_t>(drive.value());
        reserve_access_[idx] = false;

        LOG_WARN(SERVICE_EFSRV,
            "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE: result=complete opcode=102 drive={} reserved={}",
            drive.value(), reserved_space_[idx]);
        ctx->complete(epoc::error_none);
    }

''' + anchor
    text = replace_once(text, anchor, impl, "FS reserve implementations")

    for gate in (
        "static_assert(epoc::fs_msg_reserve_drive_space == 100",
        "HANDLE_CLIENT_IPC(reserve_drive_space, epoc::fs_msg_reserve_drive_space",
        "HANDLE_CLIENT_IPC(get_reserve_access, epoc::fs_msg_get_reserve_access",
        "HANDLE_CLIENT_IPC(release_reserve_access, epoc::fs_msg_release_reserve_access",
        "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE:",
    ):
        if gate not in text:
            fail(f"implementation gate missing: {gate}")

    fs_cpp.write_text(text, encoding="utf-8")

    print("MENUUI26 FSRESERVE1 applied")
    print("opcode100=ReserveDriveSpace_IMPLEMENTED")
    print("opcode101=GetReserveAccess_IMPLEMENTED")
    print("opcode102=ReleaseReserveAccess_IMPLEMENTED")
    print("session_reserve_state=IMPLEMENTED")
    print("VFS_capacity_model=UNCHANGED")
    print("MENUUI25/MENUUI24/MENUUI23/SCHEDRUN1/MANIC3/NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
