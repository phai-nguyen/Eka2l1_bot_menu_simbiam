#!/usr/bin/env python3
"""NATIVEBOOT2 B48 XNTHEMEPOST1.

Diagnostic-only tracing after B47 proved that stock RM-356 V60 suppresses TFX
at Themes CenRep key 0x102818E8:0x9 = KMaxTInt.

Observe the next native theme boundary without changing guest-visible behavior:
- requests sent to xnthemeserver and their exact completion values;
- xnthemeserver FileServer FileFlush (opcode 0x27 / decimal 39) result/path.

This deliberately preserves MENUUI13 FS-DIRUID1, all B47 TFX conclusions, and
all IPC/FileServer completion semantics.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B48-XNTHEMEPOST1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_between(text, begin, end, old, new, label):
    b = text.find(begin)
    e = text.find(end, b + 1)
    if b < 0 or e < 0:
        fail(f"{label}: bounds not found")
    region = text[b:e]
    n = region.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor in bounded region, found {n}")
    region = region.replace(old, new, 1)
    return text[:b] + region + text[e:]

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b48_xnthemepost1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc_path = up / "src/emu/kernel/src/svc.cpp"
    repo_path = up / "src/emu/services/src/centralrepo/repo.cpp"
    files_path = up / "src/emu/services/src/fs/files.cpp"
    dirs_path = up / "src/emu/services/src/fs/dirs.cpp"

    for p in (svc_path, repo_path, files_path, dirs_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    svc = svc_path.read_text(encoding="utf-8")
    repo = repo_path.read_text(encoding="utf-8")
    files = files_path.read_text(encoding="utf-8")
    dirs = dirs_path.read_text(encoding="utf-8")

    # Frozen authority from the validated predecessor chain. B47's Themes
    # state probe lives in centralrepo/repo.cpp; Wserv/ECom live in svc.cpp.
    if "[NBOOT2][AKNSKIN_TFX_STATE]" not in repo:
        fail("missing CenRep B47 baseline marker: [NBOOT2][AKNSKIN_TFX_STATE]")
    for marker in (
        "[NBOOT2][AKNSKIN_TFX_WSERV]",
        "[NBOOT2][AKNSKIN_TFX_ECOM]",
        "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE:",
    ):
        if marker not in svc:
            fail("missing svc baseline marker: " + marker)
    if "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:" not in dirs:
        fail("missing MENUUI13 FS-DIRUID1 baseline")

    ipc_marker = "[NBOOT2][XNTHEME_IPC]"
    flush_marker = "[NBOOT2][XNTHEME_FSFLUSH]"
    if ipc_marker in svc or flush_marker in files:
        if ipc_marker in svc and flush_marker in files:
            print(MARK + ": already applied")
            return
        fail("partial prior B48 patch detected")

    # ------------------------------------------------------------------
    # 1) Caller-side request trace for every native xnthemeserver IPC.
    # ------------------------------------------------------------------
    send_begin = "    static std::int32_t session_send_general("
    send_end = "    BRIDGE_FUNC(std::int32_t, session_send_sync,"
    send_anchor = '''        const std::string server_name = ss->get_server()->name();
'''
    send_block = '''        const std::string server_name = ss->get_server()->name();

        // NATIVEBOOT2 B48 XNTHEMEPOST1: observe-only native theme request.
        if (kern->get_config()->native_phone_boot && crr_pr && server_name == "xnthemeserver") {
            kernel::thread *b48_thr = kern->crr_thread();
            const std::uint32_t b48_uid3 =
                static_cast<std::uint32_t>(std::get<2>(crr_pr->get_uid_type()));
            LOG_WARN(KERNEL,
                "[NBOOT2][XNTHEME_IPC] phase=send process={} uid3=0x{:08X} thread={} server={} function={} function_hex=0x{:X} sync={} status=0x{:08X} flag=0x{:08X} raw=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] behavior=OBSERVE_ONLY",
                crr_pr->name(), b48_uid3,
                b48_thr ? b48_thr->name() : std::string("<null>"),
                server_name, ord, static_cast<std::uint32_t>(ord), sync ? 1 : 0,
                status.ptr_address(), static_cast<std::uint32_t>(arg.flag),
                static_cast<std::uint32_t>(arg.args[0]),
                static_cast<std::uint32_t>(arg.args[1]),
                static_cast<std::uint32_t>(arg.args[2]),
                static_cast<std::uint32_t>(arg.args[3]));
        }
'''
    svc = rep_between(svc, send_begin, send_end, send_anchor, send_block,
                      "B48 xntheme send")

    # ------------------------------------------------------------------
    # 2) Server-side exact completion trace. Unlike old MENUUI12, this is
    #    not limited to the Menu UID, so native Home screen is visible.
    # ------------------------------------------------------------------
    complete_begin = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {"
    complete_end = "\n    BRIDGE_FUNC("
    complete_anchor = '''        kern->call_ipc_complete_callbacks(msg, val);
'''
    complete_block = '''        // NATIVEBOOT2 B48 XNTHEMEPOST1: exact completion, no rewrite.
        if (kern->get_config()->native_phone_boot && msg && msg->own_thr) {
            kernel::process *b48_server_pr = kern->crr_process();
            kernel::process *b48_client_pr = msg->own_thr->owning_process();
            const std::uint32_t b48_server_uid3 = b48_server_pr
                ? static_cast<std::uint32_t>(std::get<2>(b48_server_pr->get_uid_type())) : 0;
            if (b48_server_pr && b48_client_pr && b48_server_uid3 == 0x10207254U) {
                const std::uint32_t b48_client_uid3 =
                    static_cast<std::uint32_t>(std::get<2>(b48_client_pr->get_uid_type()));
                LOG_WARN(KERNEL,
                    "[NBOOT2][XNTHEME_IPC] phase=complete server_process={} server_uid3=0x{:08X} client_process={} client_uid3=0x{:08X} client_thread={} function={} function_hex=0x{:X} result={} msg_id={} request_status=0x{:08X} session=0x{:08X} behavior=OBSERVE_ONLY",
                    b48_server_pr->name(), b48_server_uid3,
                    b48_client_pr->name(), b48_client_uid3,
                    msg->own_thr->name(), msg->function,
                    static_cast<std::uint32_t>(msg->function), val, msg->id,
                    msg->request_sts.ptr_address(),
                    static_cast<std::uint32_t>(msg->session_ptr_lle));
            }
        }

        kern->call_ipc_complete_callbacks(msg, val);
'''
    svc = rep_between(svc, complete_begin, complete_end, complete_anchor,
                      complete_block, "B48 xntheme completion")

    # ------------------------------------------------------------------
    # 3) Resolve the misleading historical "FS27" correlation by tracing
    #    the actual FileFlush handler result/path for xnthemeserver.
    #    Opcode 0x27 is decimal 39 == fs_msg_file_flush in EKA2L1 op.h.
    # ------------------------------------------------------------------
    flush_begin = "    void fs_server_client::file_flush(service::ipc_context *ctx) {"
    flush_end = "\n    void fs_server_client::file_rename(service::ipc_context *ctx) {"

    handle_anchor = '''        std::optional<std::int32_t> handle_res = ctx->get_argument_value<std::int32_t>(3);

        if (!handle_res) {
'''
    handle_block = '''        std::optional<std::int32_t> handle_res = ctx->get_argument_value<std::int32_t>(3);
        kernel::thread *b48_flush_thr = (ctx->msg ? ctx->msg->own_thr : nullptr);
        kernel::process *b48_flush_pr =
            b48_flush_thr ? b48_flush_thr->owning_process() : nullptr;
        const std::uint32_t b48_flush_uid3 = b48_flush_pr
            ? static_cast<std::uint32_t>(std::get<2>(b48_flush_pr->get_uid_type())) : 0;
        const bool b48_xntheme_flush = b48_flush_uid3 == 0x10207254U;

        if (!handle_res) {
'''
    files = rep_between(files, flush_begin, flush_end, handle_anchor,
                        handle_block, "B48 flush caller")

    bad_anchor = '''        if (node == nullptr || node->vfs_node->type != io_component_type::file) {
            ctx->complete(epoc::error_bad_handle);
            return;
        }

        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());

        // On Symbian, read-only file is fine with flushing. The VFS is changed to reflect this behaviour.
        if (!vfs_file->flush()) {
'''
    bad_block = '''        if (node == nullptr || node->vfs_node->type != io_component_type::file) {
            if (b48_xntheme_flush) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][XNTHEME_FSFLUSH] phase=result process={} uid3=0x{:08X} thread={} handle={} path=<bad-handle> flush_ok=0 completion={} behavior=OBSERVE_ONLY",
                    b48_flush_pr ? b48_flush_pr->name() : std::string("<null>"),
                    b48_flush_uid3,
                    b48_flush_thr ? b48_flush_thr->name() : std::string("<null>"),
                    handle_res.value_or(-1), epoc::error_bad_handle);
            }
            ctx->complete(epoc::error_bad_handle);
            return;
        }

        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());
        if (b48_xntheme_flush) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][XNTHEME_FSFLUSH] phase=enter process={} uid3=0x{:08X} thread={} handle={} path={} opcode=0x27 behavior=OBSERVE_ONLY",
                b48_flush_pr ? b48_flush_pr->name() : std::string("<null>"),
                b48_flush_uid3,
                b48_flush_thr ? b48_flush_thr->name() : std::string("<null>"),
                handle_res.value(),
                common::ucs2_to_utf8(vfs_file->file_name()));
        }

        // On Symbian, read-only file is fine with flushing. The VFS is changed to reflect this behaviour.
        const bool b48_flush_ok = vfs_file->flush();
        if (b48_xntheme_flush) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][XNTHEME_FSFLUSH] phase=result process={} uid3=0x{:08X} thread={} handle={} path={} flush_ok={} completion={} behavior=OBSERVE_ONLY",
                b48_flush_pr ? b48_flush_pr->name() : std::string("<null>"),
                b48_flush_uid3,
                b48_flush_thr ? b48_flush_thr->name() : std::string("<null>"),
                handle_res.value(),
                common::ucs2_to_utf8(vfs_file->file_name()),
                b48_flush_ok ? 1 : 0,
                b48_flush_ok ? epoc::error_none : epoc::error_general);
        }
        if (!b48_flush_ok) {
'''
    files = rep_between(files, flush_begin, flush_end, bad_anchor, bad_block,
                        "B48 FileFlush result")

    # Postconditions: diagnostics only; predecessor semantics survive.
    if svc.count(ipc_marker) != 2:
        fail(f"expected two XNTHEME_IPC source markers, got {svc.count(ipc_marker)}")
    if files.count(flush_marker) != 3:
        fail(f"expected three XNTHEME_FSFLUSH source markers, got {files.count(flush_marker)}")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE:" not in svc:
        fail("MENUUI12 xntheme diagnostic was lost")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:" not in dirs:
        fail("MENUUI13 FS-DIRUID1 was lost")

    svc_path.write_text(svc, encoding="utf-8")
    files_path.write_text(files, encoding="utf-8")

    print(MARK + ": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("xntheme_request_result_change=NONE")
    print("fileflush_result_change=NONE")
    print("FS_DIRUID1=PRESERVED")
    print("B47_STOCK_TFX_SUPPRESSION=PRESERVED")

if __name__ == "__main__":
    main()
