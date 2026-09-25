#!/usr/bin/env python3
"""NATIVEBOOT2 B74 PHONEUIRESCALLER1.

B73 DEVICE1 proves Telephone parses phoneui.r01 successfully, but never opens
callhandlingui.r01 before requesting resource 0x1099B02D and panicking CONE14.

B74 is diagnostic-only. It captures the saved guest CPU context at every
Telephone FileServer operation targeting phoneui.r01 or callhandlingui.r01,
including a bounded stack scan for PhoneUIUtils/cone return addresses and the
exact 0x1099B02D resource ID.

No resource registration, file I/O, panic, Starter, SIM, scheduler, graphics
or teardown behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B74-PHONEUIRESCALLER1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b74_phoneuirescaller1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs_cpp=up/"src/emu/services/src/fs/fs.cpp"
    files_cpp=up/"src/emu/services/src/fs/files.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for p in (fs_cpp,files_cpp,svc):
        if not p.is_file():
            fail(f"missing source: {p}")

    fs=fs_cpp.read_text(encoding="utf-8")
    files=files_cpp.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    if "[NBOOT2][PHONEUI_RES_CALLER]" in fs:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("[NBOOT2][PHONEUI_FS_FLOW]",fs,"B73"),
        ("[NBOOT2][PHONEUI_RSC_OPEN]",files,"B73"),
        ("[NBOOT2][CONE14_PHONEUI]",sv,"B71"),
        ("0x1099B02D",sv,"B71 resource-id evidence"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # Need the complete kernel::thread type for get_thread_context().
    inc="#include <kernel/kernel.h>\n"
    if "#include <kernel/thread.h>" not in fs:
        fs=rep1(fs,inc,inc+"#include <kernel/thread.h>\n","thread include")

    anchor='''                nboot2_b73_a0,nboot2_b73_a1,nboot2_b73_a2,nboot2_b73_a3,
                nboot2_b73_path);
        }

        switch (ctx->msg->function & 0xFF) {
'''

    inject=r'''                nboot2_b73_a0,nboot2_b73_a1,nboot2_b73_a2,nboot2_b73_a3,
                nboot2_b73_path);

            // B74: capture the saved Telephone guest context around the exact
            // PhoneUI resource-registration I/O. This is observation-only.
            std::u16string nboot2_b74_path;
            const std::uint32_t nboot2_b74_opcode =
                static_cast<std::uint32_t>(ctx->msg->function & 0xFF);

            if ((nboot2_b74_opcode == 0x16U) ||
                (nboot2_b74_opcode == 0x1EU)) {
                std::optional<std::u16string> nboot2_b74_name =
                    ctx->get_argument_value<std::u16string>(0);
                if (nboot2_b74_name) {
                    nboot2_b74_path =
                        get_full_symbian_path(ss_path,*nboot2_b74_name);
                }
            } else if (nboot2_b73_node &&
                       nboot2_b73_node->vfs_node &&
                       nboot2_b73_node->vfs_node->type ==
                           io_component_type::file) {
                file *nboot2_b74_file =
                    reinterpret_cast<file *>(
                        nboot2_b73_node->vfs_node.get());
                nboot2_b74_path=nboot2_b74_file->file_name();
            }

            const std::u16string nboot2_b74_lower =
                common::lowercase_ucs2_string(nboot2_b74_path);
            const bool nboot2_b74_phoneui =
                nboot2_b74_lower ==
                    u"z:\resource\apps\phoneui.r01";
            const bool nboot2_b74_callhandling =
                nboot2_b74_lower ==
                    u"z:\resource\apps\callhandlingui.r01";

            if ((nboot2_b74_phoneui || nboot2_b74_callhandling) &&
                ctx->msg->own_thr) {
                kernel::thread *nboot2_b74_thr=ctx->msg->own_thr;
                arm::core::thread_context &nboot2_b74_ctx =
                    nboot2_b74_thr->get_thread_context();

                auto nboot2_b74_reg =
                    [&](const std::size_t idx)->std::uint32_t {
                        return nboot2_b74_ctx.cpu_registers.size()>idx
                            ? nboot2_b74_ctx.cpu_registers[idx] : 0;
                    };

                const std::uint32_t nboot2_b74_pc=
                    nboot2_b74_ctx.get_pc();
                const std::uint32_t nboot2_b74_lr=
                    nboot2_b74_ctx.get_lr();
                const std::uint32_t nboot2_b74_sp=
                    nboot2_b74_ctx.get_sp();

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CALLER] path={} "
                    "kind={} opcode=0x{:02X} "
                    "pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} "
                    "cpsr=0x{:08X} "
                    "r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} "
                    "r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} "
                    "r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} "
                    "r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} "
                    "r12=0x{:08X} behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(nboot2_b74_path),
                    nboot2_b74_phoneui ? "PHONEUI" : "CALLHANDLINGUI",
                    nboot2_b74_opcode,
                    nboot2_b74_pc,nboot2_b74_lr,nboot2_b74_sp,
                    nboot2_b74_ctx.cpsr,
                    nboot2_b74_reg(0),nboot2_b74_reg(1),
                    nboot2_b74_reg(2),nboot2_b74_reg(3),
                    nboot2_b74_reg(4),nboot2_b74_reg(5),
                    nboot2_b74_reg(6),nboot2_b74_reg(7),
                    nboot2_b74_reg(8),nboot2_b74_reg(9),
                    nboot2_b74_reg(10),nboot2_b74_reg(11),
                    nboot2_b74_reg(12));

                auto nboot2_b74_classify =
                    [&](const char *source,
                        const std::uint32_t index,
                        const std::uint32_t raw) {
                        const std::uint32_t addr=raw & ~1U;
                        const char *module=nullptr;
                        std::uint32_t base=0;

                        if ((addr>=0x80ED8DA8U) &&
                            (addr<0x80EDF040U)) {
                            module="PhoneUIUtils.dll";
                            base=0x80ED8DA8U;
                        } else if ((addr>=0x806E8E68U) &&
                                   (addr<0x806F4378U)) {
                            module="cone.dll";
                            base=0x806E8E68U;
                        }

                        if (module) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_FRAME] "
                                "path_kind={} opcode=0x{:02X} "
                                "source={} index={} raw=0x{:08X} "
                                "module={} offset=0x{:08X} "
                                "behavior=OBSERVE_ONLY",
                                nboot2_b74_phoneui
                                    ? "PHONEUI" : "CALLHANDLINGUI",
                                nboot2_b74_opcode,source,index,raw,
                                module,addr-base);
                        }

                        if (raw==0x1099B02DU) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_ID] "
                                "path_kind={} opcode=0x{:02X} "
                                "source={} index={} "
                                "resource_id=0x1099B02D "
                                "owner=callhandlingui.r01 "
                                "behavior=OBSERVE_ONLY",
                                nboot2_b74_phoneui
                                    ? "PHONEUI" : "CALLHANDLINGUI",
                                nboot2_b74_opcode,source,index);
                        }
                    };

                nboot2_b74_classify("PC",0,nboot2_b74_pc);
                nboot2_b74_classify("LR",0,nboot2_b74_lr);
                for (std::uint32_t r=0;r<13;++r) {
                    nboot2_b74_classify(
                        "REG",r,nboot2_b74_reg(r));
                }

                constexpr std::uint32_t nboot2_b74_words=96;
                for (std::uint32_t i=0;i<nboot2_b74_words;++i) {
                    const std::uint32_t slot_addr=
                        nboot2_b74_sp+i*4U;
                    if (slot_addr<nboot2_b74_sp) {
                        break;
                    }

                    const std::uint32_t *slot=
                        eka2l1::ptr<std::uint32_t>(slot_addr)
                            .get(nboot2_b73_pr);
                    if (!slot) {
                        LOG_WARN(SERVICE_EFSRV,
                            "[NBOOT2][PHONEUI_RES_STACK_END] "
                            "path_kind={} opcode=0x{:02X} "
                            "index={} slot=0x{:08X} mapped=0 "
                            "behavior=OBSERVE_ONLY",
                            nboot2_b74_phoneui
                                ? "PHONEUI" : "CALLHANDLINGUI",
                            nboot2_b74_opcode,i,slot_addr);
                        break;
                    }

                    nboot2_b74_classify("STACK",i,*slot);
                }

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CONTEXT_DONE] "
                    "path_kind={} opcode=0x{:02X} "
                    "stack_words_max={} behavior=OBSERVE_ONLY",
                    nboot2_b74_phoneui
                        ? "PHONEUI" : "CALLHANDLINGUI",
                    nboot2_b74_opcode,nboot2_b74_words);
            }
        }

        switch (ctx->msg->function & 0xFF) {
'''

    fs=rep1(fs,anchor,inject,"B74 Telephone resource context")

    for need in (
        "[NBOOT2][PHONEUI_RES_CALLER]",
        "[NBOOT2][PHONEUI_RES_FRAME]",
        "[NBOOT2][PHONEUI_RES_ID]",
        "[NBOOT2][PHONEUI_RES_CONTEXT_DONE]",
        'u"z:\\resource\\apps\\phoneui.r01"',
        'u"z:\\resource\\apps\\callhandlingui.r01"',
        "0x1099B02DU",
        "0x80ED8DA8U",
        "0x806E8E68U",
        "nboot2_b74_words=96",
    ):
        if need not in fs:
            fail("post-apply gate missing: "+need)

    diagnostic=inject
    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "set_int(",
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "kill(",
    ):
        if forbidden in diagnostic:
            fail("behavior-changing token in B74 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")

    print(MARK+": applied")
    print("scope=TELEPHONE_RESOURCE_CALLER_CONTEXT_DIAGNOSTIC")
    print("targets=PHONEUI_R01_AND_CALLHANDLINGUI_R01")
    print("resource_id=0x1099B02D_OBSERVE_ONLY")
    print("phoneuiutils_range=0x80ED8DA8_0x80EDF040")
    print("cone_range=0x806E8E68_0x806F4378")
    print("stack_words=96")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("B61_B64_B68_B69_B70_B71_B72_B73=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
