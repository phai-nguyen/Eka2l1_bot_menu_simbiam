#!/usr/bin/env python3
"""NATIVEBOOT2 B73 PHONEUIFSFLOW1.

B72 DEVICE1 proves phoneui.r01 is opened repeatedly, including ~1 ms before
Telephone CONE14, but zero B72 file_read/file_seek markers fire. Therefore the
failure occurs before those RFile paths or through a different FileServer IPC.

B73 is diagnostic-only and moves one layer outward:
- identify which process opens phoneui.r01 and the returned handle;
- log every FileServer IPC issued by Telephone, before dispatch;
- resolve arg3 to a file node/path when it is a file handle;
- trace direct ReadFileSection calls for phoneui.r01.

No FileServer return value, file data/cursor, resource, panic, Starter/SIM/P&S,
scheduler, graphics or teardown behavior changes.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B73-PHONEUIFSFLOW1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b73_phoneuifsflow1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs_cpp=up/"src/emu/services/src/fs/fs.cpp"
    files_cpp=up/"src/emu/services/src/fs/files.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    session=up/"src/emu/kernel/src/session.cpp"

    for p in (fs_cpp,files_cpp,svc,session):
        if not p.is_file():
            fail(f"missing source: {p}")

    fs=fs_cpp.read_text(encoding="utf-8")
    files=files_cpp.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    se=session.read_text(encoding="utf-8")

    if "[NBOOT2][PHONEUI_FS_FLOW]" in fs:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("[NBOOT2][PHONEUI_RSC_READ]",files,"B72"),
        ("[NBOOT2][PHONEUI_RSC_SEEK]",files,"B72"),
        ("[NBOOT2][CONE14_PHONEUI]",sv,"B71"),
        ("[NBOOT2][STARTER_IPC_ARM]",se,"B70"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # 1) FileServer fetch: capture every Telephone request. Keep the raw opcode
    # before version translation and the translated opcode just before switch.
    sig="    void fs_server_client::fetch(service::ipc_context *ctx) {\n"
    if sig not in fs:
        fail("fs_server_client::fetch signature missing")
    fs=rep1(fs,sig,sig+'''        const std::uint32_t nboot2_b73_raw_function =
            ctx && ctx->msg
                ? static_cast<std::uint32_t>(ctx->msg->function) : 0;
''',"fetch raw opcode")

    switch_anchor="        switch (ctx->msg->function & 0xFF) {\n"
    inject='''        kernel::process *nboot2_b73_pr =
            (ctx && ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        if (nboot2_b73_pr &&
            (nboot2_b73_pr->get_uid() == 0x100058B3U)) {
            const std::uint32_t nboot2_b73_a0 =
                static_cast<std::uint32_t>(ctx->msg->args.args[0]);
            const std::uint32_t nboot2_b73_a1 =
                static_cast<std::uint32_t>(ctx->msg->args.args[1]);
            const std::uint32_t nboot2_b73_a2 =
                static_cast<std::uint32_t>(ctx->msg->args.args[2]);
            const std::uint32_t nboot2_b73_a3 =
                static_cast<std::uint32_t>(ctx->msg->args.args[3]);

            fs_node *nboot2_b73_node =
                get_file_node(static_cast<int>(nboot2_b73_a3));
            std::string nboot2_b73_path("<no-file-handle>");
            if (nboot2_b73_node &&
                nboot2_b73_node->vfs_node &&
                nboot2_b73_node->vfs_node->type == io_component_type::file) {
                file *nboot2_b73_file =
                    reinterpret_cast<file *>(nboot2_b73_node->vfs_node.get());
                nboot2_b73_path =
                    common::ucs2_to_utf8(nboot2_b73_file->file_name());
            }

            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_FS_FLOW] process={} uid3=0x{:08X} "
                "thread={} raw_function=0x{:08X} function=0x{:08X} "
                "low_opcode=0x{:02X} "
                "types=[{},{},{},{}] "
                "args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                "arg3_file={} behavior=OBSERVE_ONLY",
                nboot2_b73_pr->name(),
                nboot2_b73_pr->get_uid(),
                ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"),
                nboot2_b73_raw_function,
                static_cast<std::uint32_t>(ctx->msg->function),
                static_cast<std::uint32_t>(ctx->msg->function & 0xFF),
                static_cast<int>(ctx->msg->args.get_arg_type(0)),
                static_cast<int>(ctx->msg->args.get_arg_type(1)),
                static_cast<int>(ctx->msg->args.get_arg_type(2)),
                static_cast<int>(ctx->msg->args.get_arg_type(3)),
                nboot2_b73_a0,nboot2_b73_a1,nboot2_b73_a2,nboot2_b73_a3,
                nboot2_b73_path);
        }

        switch (ctx->msg->function & 0xFF) {
'''
    fs=rep1(fs,switch_anchor,inject,"Telephone FS flow")

    # 1b) Resource loaders can bypass RFile::Read for ROM-backed resources.
    # Record the exact IsFileInRom decision/address for Telephone + PhoneUI.
    rom_sig="    void fs_server_client::is_file_in_rom(service::ipc_context *ctx) {"
    rom_start=fs.find(rom_sig)
    rom_end=fs.find("\n    void fs_server_client::is_valid_name",rom_start)
    if rom_start<0 or rom_end<0:
        fail("is_file_in_rom bounds not found")
    rom_block=fs[rom_start:rom_end]

    rom_anchor='''        if (f) {
            addr = f->rom_address();
            f->close();
        }

        ctx->write_data_to_descriptor_argument<address>(1, addr);
'''
    rom_new='''        if (f) {
            addr = f->rom_address();
            f->close();
        }

        kernel::process *nboot2_b73_rom_pr =
            (ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        if (nboot2_b73_rom_pr &&
            (nboot2_b73_rom_pr->get_uid() == 0x100058B3U) &&
            (common::lowercase_ucs2_string(final_path) ==
                u"z:\\resource\\apps\\phoneui.r01")) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_IS_ROM] path={} rom_address=0x{:08X} "
                "process={} uid3=0x{:08X} thread={} "
                "behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(final_path),
                static_cast<std::uint32_t>(addr),
                nboot2_b73_rom_pr->name(),
                nboot2_b73_rom_pr->get_uid(),
                ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"));
        }

        ctx->write_data_to_descriptor_argument<address>(1, addr);
'''
    if rom_block.count(rom_anchor)!=1:
        fail(f"is_file_in_rom anchor count={rom_block.count(rom_anchor)}")
    rom_block=rom_block.replace(rom_anchor,rom_new,1)
    fs=fs[:rom_start]+rom_block+fs[rom_end:]

    # 2) Identify caller/handle for every exact phoneui.r01 open.
    open_sig="    void fs_server_client::new_file_subsession(service::ipc_context *ctx,"
    open_start=files.find(open_sig)
    open_end=files.find("\n    int fs_server_client::new_node(",open_start)
    if open_start<0 or open_end<0:
        fail("new_file_subsession bounds not found")
    open_block=files[open_start:open_end]

    open_anchor='''        LOG_TRACE(SERVICE_EFSRV, "Handle opened: {}", handle);

        ctx->write_data_to_descriptor_argument<int>(3, handle);
'''
    open_new='''        LOG_TRACE(SERVICE_EFSRV, "Handle opened: {}", handle);

        kernel::process *nboot2_b73_open_pr =
            (ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        const std::u16string nboot2_b73_open_lower =
            common::lowercase_ucs2_string(*name_res);
        if (nboot2_b73_open_lower ==
            u"z:\\resource\\apps\\phoneui.r01") {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_OPEN] path={} handle={} raw_mode={} "
                "process={} uid3=0x{:08X} thread={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(*name_res),handle,*open_mode_res,
                nboot2_b73_open_pr
                    ? nboot2_b73_open_pr->name() : std::string("<null>"),
                nboot2_b73_open_pr
                    ? nboot2_b73_open_pr->get_uid() : 0,
                ctx->msg && ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"));
        }

        ctx->write_data_to_descriptor_argument<int>(3, handle);
'''
    if open_block.count(open_anchor)!=1:
        fail(f"PhoneUI open provenance anchor count={open_block.count(open_anchor)}")
    open_block=open_block.replace(open_anchor,open_new,1)
    files=files[:open_start]+open_block+files[open_end:]

    # 3) Direct ReadFileSection path: trace exact phoneui.r01 before and after
    # host read. This catches BAFL paths that never use an RFile subsession read.
    sig="    void fs_server_client::read_file_section(service::ipc_context *ctx) {"
    start=files.find(sig)
    end=files.find("\n    void fs_server_client::new_file_subsession",start)
    if start<0 or end<0:
        fail("read_file_section bounds not found")
    block=files[start:end]

    path_anchor='''        target_file_path.value() = get_full_symbian_path(ss_path, target_file_path.value());

        if (!check_path_capabilities_pass'''
    path_new='''        target_file_path.value() = get_full_symbian_path(ss_path, target_file_path.value());

        kernel::process *nboot2_b73_section_pr =
            (ctx->msg && ctx->msg->own_thr)
                ? ctx->msg->own_thr->owning_process() : nullptr;
        const bool nboot2_b73_phoneui_section =
            nboot2_b73_section_pr &&
            (nboot2_b73_section_pr->get_uid() == 0x100058B3U) &&
            (common::lowercase_ucs2_string(target_file_path.value()) ==
                u"z:\\resource\\apps\\phoneui.r01");

        if (!check_path_capabilities_pass'''
    if block.count(path_anchor)!=1:
        fail(f"ReadFileSection path anchor count={block.count(path_anchor)}")
    block=block.replace(path_anchor,path_new,1)

    read_anchor='''        target_file->seek(position, eka2l1::file_seek_mode::beg);
        const std::size_t readed_size = target_file->read_file(buffer, buffer_length, 1);
        target_file->close();
'''
    read_new='''        if (nboot2_b73_phoneui_section) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_READ_SECTION] phase=before path={} "
                "function=0x{:08X} position={} buffer_length={} "
                "thread={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(target_file_path.value()),
                ctx->msg ? static_cast<std::uint32_t>(ctx->msg->function) : 0,
                position,buffer_length,
                ctx->msg && ctx->msg->own_thr
                    ? ctx->msg->own_thr->name() : std::string("<null>"));
        }

        target_file->seek(position, eka2l1::file_seek_mode::beg);
        const std::size_t readed_size = target_file->read_file(buffer, buffer_length, 1);

        if (nboot2_b73_phoneui_section) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_READ_SECTION] phase=after path={} "
                "position={} requested={} actual={} "
                "behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(target_file_path.value()),
                position,buffer_length,readed_size);
        }

        target_file->close();
'''
    if block.count(read_anchor)!=1:
        fail(f"ReadFileSection read anchor count={block.count(read_anchor)}")
    block=block.replace(read_anchor,read_new,1)
    files=files[:start]+block+files[end:]

    for need,text in (
        ("[NBOOT2][PHONEUI_FS_FLOW]",fs),
        ("nboot2_b73_raw_function",fs),
        ("[NBOOT2][PHONEUI_IS_ROM]",fs),\n        ("[NBOOT2][PHONEUI_RSC_OPEN]",files),
        ("[NBOOT2][PHONEUI_READ_SECTION]",files),
        ('u"z:\\resource\\apps\\phoneui.r01"',files),
        ("0x100058B3U",files),
        ("behavior=OBSERVE_ONLY",fs+files),
    ):
        if need not in text:
            fail("post-apply gate missing: "+need)

    # No FileServer behavior changes.
    diagnostic=inject+rom_new+open_new+path_new+read_new
    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "read_pos =",
        "buffer_length =",
        "requested=102",
        "ESimUsable",
        "reason = 0",
    ):
        if forbidden in diagnostic:
            fail("behavior-changing token in B73 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    files_cpp.write_text(files,encoding="utf-8")

    print(MARK+": applied")
    print("scope=TELEPHONE_FILESERVER_FLOW_PLUS_PHONEUI_OPEN_READSECTION")
    print("telephone_uid3=0x100058B3")
    print("target=Z:\\resource\\apps\\phoneui.r01")
    print("file_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("B61_B64_B68_B69_B70_B71_B72=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
