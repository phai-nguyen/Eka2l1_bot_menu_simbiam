#!/usr/bin/env python3
"""NATIVEBOOT2 B72 PHONEUIRSCIO1.

B71 DEVICE1 confirms Telephone[0x100058B3] still self-panics CONE 14 after
opening Z:\\resource\\apps\\phoneui.r01. At panic time no 0x4E738xxx
resource ID remains in registers or the 128-word stack, so the requested ID has
already been consumed.

B72 moves the observation point earlier: trace only Telephone file reads/seeks
against the exact RM-356 phoneui.r01 resource file. The matching RPKG gives:
- size 28134
- index table offset 27396
- resource signature base 0x4E738000
- resource count 368 (0x170)

After DEVICE1, read_pos/read_len can be mapped offline against the exact RPKG
index table to identify the last resource/index access before CONE14.

Diagnostic only: no file cursor, bytes, completion result, resource, panic,
Starter, SIM, scheduler, graphics or teardown behavior changes.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B72-PHONEUIRSCIO1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b72_phoneuirscio1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    files=up/"src/emu/services/src/fs/files.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    alarm=up/"src/emu/services/src/alarm/alarm.cpp"
    session=up/"src/emu/kernel/src/session.cpp"
    for p in (files,svc,sa,alarm,session):
        if not p.is_file():
            fail(f"missing source: {p}")

    fs=files.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    al=alarm.read_text(encoding="utf-8")
    se=session.read_text(encoding="utf-8")

    if "[NBOOT2][PHONEUI_RSC_READ]" in fs:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("[NBOOT2][CONE14_PHONEUI]",sv,"B71"),
        ("[NBOOT2][STARTER_GLOBAL_STATE]",sv,"B62"),
        ("[NBOOT2][STARTER_WAIT_ANY]",sv,"B68"),
        ("[NBOOT2][STARTER_IPC_ARM]",se,"B70"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sat,"B64"),
        ("[NBOOT2][ALARM_ID_LIST]",al,"B69"),
        ("[NBOOT2][STARTER_SSC_DUMP]",fs,"B67"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # Patch inside file_read using stable semantic statements.
    sig="    void fs_server_client::file_read(service::ipc_context *ctx) {"
    start=fs.find(sig)
    end=fs.find("\n    void fs_server_client::file_close",start)
    if start<0 or end<0:
        fail("file_read bounds not found")
    block=fs[start:end]

    anchor='''        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());

        int read_len = *ctx->get_argument_value<std::int32_t>(1);
'''
    inject='''        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());

        kernel::process *nboot2_b72_pr =
            (ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        const std::u16string nboot2_b72_lower =
            common::lowercase_ucs2_string(vfs_file->file_name());
        const bool nboot2_b72_phoneui =
            nboot2_b72_pr &&
            (nboot2_b72_pr->get_uid() == 0x100058B3U) &&
            (nboot2_b72_lower == u"z:\\resource\\apps\\phoneui.r01");

        int read_len = *ctx->get_argument_value<std::int32_t>(1);
'''
    if block.count(anchor)!=1:
        fail(f"file_read setup anchor count={block.count(anchor)}")
    block=block.replace(anchor,inject,1)

    anchor='''        vfs_file->seek(read_pos, file_seek_mode::beg);

        uint64_t size = vfs_file->size();
'''
    inject='''        if (nboot2_b72_phoneui) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_READ] phase=before "
                "path={} handle={} function=0x{:08X} "
                "read_pos={} read_len_requested={} last_pos={} "
                "file_size={} index_table_offset=27396 resource_count=368 "
                "resource_base=0x4E738000 thread={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(vfs_file->file_name()),
                *handle_res,
                ctx->msg ? static_cast<std::uint32_t>(ctx->msg->function) : 0,
                read_pos,read_len,last_pos,vfs_file->size(),
                ctx->msg && ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"));
        }

        vfs_file->seek(read_pos, file_seek_mode::beg);

        uint64_t size = vfs_file->size();
'''
    if block.count(anchor)!=1:
        fail(f"file_read pre-read anchor count={block.count(anchor)}")
    block=block.replace(anchor,inject,1)

    anchor='''        size_t read_finish_len = vfs_file->read_file(read_data.data(), 1, read_len);
        ctx->write_data_to_descriptor_argument(0, reinterpret_cast<uint8_t *>(read_data.data()), static_cast<std::uint32_t>(read_finish_len));

        //LOG_TRACE(SERVICE_EFSRV, "Readed {} from {} to address 0x{:x}", read_finish_len, read_pos, ctx->msg->args.args[0]);
'''
    inject='''        size_t read_finish_len = vfs_file->read_file(read_data.data(), 1, read_len);
        ctx->write_data_to_descriptor_argument(0, reinterpret_cast<uint8_t *>(read_data.data()), static_cast<std::uint32_t>(read_finish_len));

        if (nboot2_b72_phoneui) {
            const bool nboot2_b72_index_overlap =
                (read_pos < 28134ULL) &&
                ((read_pos + read_finish_len) > 27396ULL);
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_READ] phase=after "
                "path={} handle={} read_pos={} requested_after_clamp={} "
                "actual={} next_pos={} index_overlap={} "
                "descriptor0=0x{:08X} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(vfs_file->file_name()),
                *handle_res,read_pos,read_len,read_finish_len,
                vfs_file->tell(),nboot2_b72_index_overlap?1:0,
                ctx->msg
                    ? static_cast<std::uint32_t>(ctx->msg->args.args[0]) : 0);
        }

        //LOG_TRACE(SERVICE_EFSRV, "Readed {} from {} to address 0x{:x}", read_finish_len, read_pos, ctx->msg->args.args[0]);
'''
    if block.count(anchor)!=1:
        fail(f"file_read post-read anchor count={block.count(anchor)}")
    block=block.replace(anchor,inject,1)
    fs=fs[:start]+block+fs[end:]

    # Patch file_seek: exact path + Telephone only.
    sig="    void fs_server_client::file_seek(service::ipc_context *ctx) {"
    start=fs.find(sig)
    end=fs.find("\n    void fs_server_client::file_flush",start)
    if start<0 or end<0:
        fail("file_seek bounds not found")
    block=fs[start:end]

    anchor='''        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());

        std::optional<std::int32_t> seek_mode = ctx->get_argument_value<std::int32_t>(1);
'''
    inject='''        file *vfs_file = reinterpret_cast<file *>(node->vfs_node.get());

        kernel::process *nboot2_b72_seek_pr =
            (ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        const std::u16string nboot2_b72_seek_lower =
            common::lowercase_ucs2_string(vfs_file->file_name());
        const bool nboot2_b72_phoneui_seek =
            nboot2_b72_seek_pr &&
            (nboot2_b72_seek_pr->get_uid() == 0x100058B3U) &&
            (nboot2_b72_seek_lower == u"z:\\resource\\apps\\phoneui.r01");

        std::optional<std::int32_t> seek_mode = ctx->get_argument_value<std::int32_t>(1);
'''
    if block.count(anchor)!=1:
        fail(f"file_seek setup anchor count={block.count(anchor)}")
    block=block.replace(anchor,inject,1)

    anchor='''        std::uint64_t seek_res = vfs_file->seek(*seek_off, vfs_seek_mode);

        if (seek_res == 0xFFFFFFFFFFFFFFFF) {
'''
    inject='''        const std::uint64_t nboot2_b72_seek_before =
            vfs_file->tell();
        std::uint64_t seek_res = vfs_file->seek(*seek_off, vfs_seek_mode);

        if (nboot2_b72_phoneui_seek) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_SEEK] path={} handle={} "
                "function=0x{:08X} before={} seek_mode={} seek_off={} "
                "result={} thread={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(vfs_file->file_name()),
                *handle_res,
                ctx->msg ? static_cast<std::uint32_t>(ctx->msg->function) : 0,
                nboot2_b72_seek_before,
                seek_mode ? *seek_mode : -9999,
                seek_off ? *seek_off : -9999,
                seek_res,
                ctx->msg && ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"));
        }

        if (seek_res == 0xFFFFFFFFFFFFFFFF) {
'''
    if block.count(anchor)!=1:
        fail(f"file_seek operation anchor count={block.count(anchor)}")
    block=block.replace(anchor,inject,1)
    fs=fs[:start]+block+fs[end:]

    for need in (
        "[NBOOT2][PHONEUI_RSC_READ]",
        "[NBOOT2][PHONEUI_RSC_SEEK]",
        'u"z:\\resource\\apps\\phoneui.r01"',
        "0x100058B3U",
        "index_table_offset=27396",
        "resource_count=368",
        "resource_base=0x4E738000",
        "behavior=OBSERVE_ONLY",
    ):
        if need not in fs:
            fail("post-apply gate missing: "+need)

    # B72 must not alter I/O semantics.
    for forbidden in (
        "read_pos = 27396",
        "read_len = 4",
        "seek_res = 0",
        "ctx->complete(epoc::error_none); // B72",
        "requested=102",
        "ESimUsable",
    ):
        if forbidden in fs[start:end]:
            fail("B72 behavior change detected: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    files.write_text(fs,encoding="utf-8")
    print(MARK+": applied")
    print("scope=TELEPHONE_PHONEUI_R01_IO_DIAGNOSTIC")
    print("target_uid3=0x100058B3")
    print("target=Z:\\resource\\apps\\phoneui.r01")
    print("rsc_size=28134")
    print("index_table_offset=27396")
    print("resource_count=368")
    print("resource_base=0x4E738000")
    print("file_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("B61_B64_B68_B69_B70_B71=PRESERVED")

if __name__=="__main__":
    main()
