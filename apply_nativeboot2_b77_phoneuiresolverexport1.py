#!/usr/bin/env python3
"""NATIVEBOOT2 B77 PHONEUIRESOLVEREXPORT1.

B76 DEVICE1 closes the host GameMenu/Exit regressions. Guest startup still
fails at Telephone CONE14 for resource 0x1099B02D, owned by callhandlingui.r01.

B75/B76 also exposed an important diagnostic ambiguity: the repeated
PhoneUIUtils +0x5094 pointer is the UTF-16 "\\resource\\apps\\" descriptor
region, not proof of an executing function frame.

Authoritative Symbian PhoneUIUtils source and EABI exports identify
CPhoneResourceResolverBase::BaseConstructL() as export ordinal 182. B77
therefore resolves ordinal 182 from the *actual loaded RM-356 PhoneUIUtils.dll*
at runtime and uses the next higher text export as a conservative exported
function boundary. It then correlates PC/LR/register/stack candidates at
phoneui.r01 FileServer IPC and at CONE14.

Diagnostic-only. No resource registration, FileServer result/data, panic,
SIM/state, scheduler, graphics, or host lifecycle behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B77-PHONEUIRESOLVEREXPORT1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b77_phoneuiresolverexport1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs_cpp=up/"src/emu/services/src/fs/fs.cpp"
    svc_cpp=up/"src/emu/kernel/src/svc.cpp"
    for p in (fs_cpp,svc_cpp):
        if not p.is_file():
            fail(f"missing source: {p}")

    fs=fs_cpp.read_text(encoding="utf-8")
    sv=svc_cpp.read_text(encoding="utf-8")

    for gate,body,name in (
        ("[NBOOT2][PHONEUI_RES_MATCH2]",fs,"B75"),
        ("[NBOOT2][PHONEUI_RES_CALLER]",fs,"B74"),
        ("[NBOOT2][GAMEMENU_SAFE_TITLE]",
            (up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8"),
            "B76"),
        ("[NBOOT2][CONE14_PHONEUI]",sv,"B71"),
        ("[NBOOT2][CONE14_FRAME]",sv,"B71"),
    ):
        if gate not in body:
            fail(f"{name} gate missing: {gate}")

    if "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]" in fs:
        print(MARK+": already applied")
        return

    # fs.cpp needs the complete codeseg API for lookup()/export table metadata.
    inc="#include <kernel/thread.h>\n"
    if "#include <kernel/codeseg.h>" not in fs:
        fs=rep1(fs,inc,inc+"#include <kernel/codeseg.h>\n",
                "codeseg include")

    fs_anchor=r'''                const std::uint32_t nboot2_b74_sp=
                    nboot2_b74_ctx.get_sp();

                LOG_WARN(SERVICE_EFSRV,
'''
    fs_insert=r'''                const std::uint32_t nboot2_b74_sp=
                    nboot2_b74_ctx.get_sp();

                // B77: resolve the exact exported BaseConstructL() from the
                // loaded PhoneUIUtils codeseg instead of treating every pointer
                // inside the image as an executable caller.
                kernel_system *nboot2_b77_kern =
                    ctx->sys ? ctx->sys->get_kernel_system() : nullptr;
                codeseg_ptr nboot2_b77_phone_seg=nullptr;
                if (nboot2_b77_kern) {
                    for (const auto &nboot2_b77_seg_obj :
                         nboot2_b77_kern->get_codeseg_list()) {
                        codeseg_ptr nboot2_b77_seg =
                            reinterpret_cast<codeseg_ptr>(
                                nboot2_b77_seg_obj.get());
                        if (!nboot2_b77_seg) {
                            continue;
                        }
                        const std::u16string nboot2_b77_seg_path =
                            common::lowercase_ucs2_string(
                                nboot2_b77_seg->get_full_path());
                        if (nboot2_b77_seg_path ==
                            u"z:\\sys\\bin\\phoneuiutils.dll") {
                            nboot2_b77_phone_seg=nboot2_b77_seg;
                            break;
                        }
                    }
                }

                std::uint32_t nboot2_b77_phone_base=0;
                std::uint32_t nboot2_b77_text_size=0;
                std::uint32_t nboot2_b77_code_size=0;
                std::uint32_t nboot2_b77_baseconstruct_raw=0;
                std::uint32_t nboot2_b77_baseconstruct=0;
                std::uint32_t nboot2_b77_baseconstruct_limit=0;

                if (nboot2_b77_phone_seg) {
                    nboot2_b77_phone_base=
                        nboot2_b77_phone_seg->get_code_run_addr(
                            nboot2_b73_pr);
                    nboot2_b77_text_size=
                        nboot2_b77_phone_seg->get_text_size();
                    nboot2_b77_code_size=
                        nboot2_b77_phone_seg->get_code_size();

                    // EABI phoneuiutilsu.def:
                    // ordinal 182 =
                    // CPhoneResourceResolverBase::BaseConstructL().
                    nboot2_b77_baseconstruct_raw=
                        nboot2_b77_phone_seg->lookup(
                            nboot2_b73_pr,182U);
                    nboot2_b77_baseconstruct=
                        nboot2_b77_baseconstruct_raw & ~1U;

                    const std::uint64_t nboot2_b77_text_end64 =
                        static_cast<std::uint64_t>(
                            nboot2_b77_phone_base) +
                        static_cast<std::uint64_t>(
                            nboot2_b77_text_size);
                    nboot2_b77_baseconstruct_limit =
                        nboot2_b77_text_end64>0xFFFFFFFFULL
                            ? 0xFFFFFFFFU
                            : static_cast<std::uint32_t>(
                                nboot2_b77_text_end64);

                    const std::vector<std::uint32_t>
                        nboot2_b77_exports =
                            nboot2_b77_phone_seg->
                                get_export_table(nboot2_b73_pr);
                    for (const std::uint32_t nboot2_b77_export_raw :
                         nboot2_b77_exports) {
                        const std::uint32_t nboot2_b77_export =
                            nboot2_b77_export_raw & ~1U;
                        if ((nboot2_b77_export >
                             nboot2_b77_baseconstruct) &&
                            (nboot2_b77_export <
                             nboot2_b77_baseconstruct_limit)) {
                            nboot2_b77_baseconstruct_limit =
                                nboot2_b77_export;
                        }
                    }

                    LOG_WARN(SERVICE_EFSRV,
                        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT] "
                        "phase=FILESERVER path_kind={} opcode=0x{:02X} "
                        "ordinal=182 base=0x{:08X} text_size=0x{:08X} "
                        "code_size=0x{:08X} export_raw=0x{:08X} "
                        "export_addr=0x{:08X} export_offset=0x{:08X} "
                        "next_export=0x{:08X} span=0x{:08X} "
                        "behavior=OBSERVE_ONLY",
                        nboot2_b74_phoneui
                            ? "PHONEUI" : "CALLHANDLINGUI",
                        nboot2_b74_opcode,
                        nboot2_b77_phone_base,
                        nboot2_b77_text_size,
                        nboot2_b77_code_size,
                        nboot2_b77_baseconstruct_raw,
                        nboot2_b77_baseconstruct,
                        nboot2_b77_baseconstruct>=
                                nboot2_b77_phone_base
                            ? nboot2_b77_baseconstruct-
                                nboot2_b77_phone_base : 0,
                        nboot2_b77_baseconstruct_limit,
                        nboot2_b77_baseconstruct_limit>
                                nboot2_b77_baseconstruct
                            ? nboot2_b77_baseconstruct_limit-
                                nboot2_b77_baseconstruct : 0);
                } else {
                    LOG_WARN(SERVICE_EFSRV,
                        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT] "
                        "phase=FILESERVER path_kind={} opcode=0x{:02X} "
                        "ordinal=182 module_found=0 behavior=OBSERVE_ONLY",
                        nboot2_b74_phoneui
                            ? "PHONEUI" : "CALLHANDLINGUI",
                        nboot2_b74_opcode);
                }

                LOG_WARN(SERVICE_EFSRV,
'''
    fs=rep1(fs,fs_anchor,fs_insert,"B77 FileServer export resolver")

    classify_anchor=r'''                        if (module) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_FRAME] "
'''
    classify_insert=r'''                        // B77 correction: these exact RM-356 offsets were
                        // observed in B75/B76 as descriptor/literal data.
                        if (nboot2_b77_phone_seg &&
                            (addr>=nboot2_b77_phone_base)) {
                            const std::uint32_t nboot2_b77_off =
                                addr-nboot2_b77_phone_base;
                            if ((nboot2_b77_off==0x5094U) ||
                                (nboot2_b77_off==0x50B8U)) {
                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_LITERAL_PTR] "
                                    "phase=FILESERVER path_kind={} "
                                    "opcode=0x{:02X} source={} index={} "
                                    "raw=0x{:08X} offset=0x{:08X} "
                                    "classification=DESCRIPTOR_LITERAL "
                                    "behavior=OBSERVE_ONLY",
                                    nboot2_b74_phoneui
                                        ? "PHONEUI" : "CALLHANDLINGUI",
                                    nboot2_b74_opcode,source,index,raw,
                                    nboot2_b77_off);
                            }
                        }

                        if (nboot2_b77_baseconstruct &&
                            (addr>=nboot2_b77_baseconstruct) &&
                            (addr<nboot2_b77_baseconstruct_limit)) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME] "
                                "phase=FILESERVER path_kind={} "
                                "opcode=0x{:02X} source={} index={} "
                                "raw=0x{:08X} addr=0x{:08X} "
                                "export_addr=0x{:08X} delta=0x{:08X} "
                                "behavior=OBSERVE_ONLY",
                                nboot2_b74_phoneui
                                    ? "PHONEUI" : "CALLHANDLINGUI",
                                nboot2_b74_opcode,source,index,raw,addr,
                                nboot2_b77_baseconstruct,
                                addr-nboot2_b77_baseconstruct);
                        }

                        if (module) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_FRAME] "
'''
    fs=rep1(fs,classify_anchor,classify_insert,
            "B77 BaseConstruct classifier")

    deep_anchor=r'''                constexpr std::uint32_t nboot2_b74_words=96;
                for (std::uint32_t i=0;i<nboot2_b74_words;++i) {
'''
    if deep_anchor not in fs:
        fail("B74 96-word stack anchor missing")

    done_anchor=r'''                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CONTEXT_DONE] "
'''
    deep_scan=r'''                // B77 extends only the observation window. Keep the original
                // B74 96-word loop intact for historical regression gates.
                constexpr std::uint32_t nboot2_b77_words=384;
                for (std::uint32_t i=nboot2_b74_words;
                     i<nboot2_b77_words;++i) {
                    const std::uint32_t slot_addr=
                        nboot2_b74_sp+i*4U;
                    if (slot_addr<nboot2_b74_sp) {
                        break;
                    }
                    const std::uint32_t *slot=
                        eka2l1::ptr<std::uint32_t>(slot_addr)
                            .get(nboot2_b73_pr);
                    if (!slot) {
                        break;
                    }
                    nboot2_b74_classify("DEEP_STACK",i,*slot);
                }

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE] "
                    "phase=FILESERVER path_kind={} opcode=0x{:02X} "
                    "stack_words_max={} behavior=OBSERVE_ONLY",
                    nboot2_b74_phoneui
                        ? "PHONEUI" : "CALLHANDLINGUI",
                    nboot2_b74_opcode,nboot2_b77_words);

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CONTEXT_DONE] "
'''
    fs=rep1(fs,done_anchor,deep_scan,
            "B77 deep stack before context done")

    # CONE14: resolve the exact same export in the dying Telephone process.
    cone_anchor=r'''            const std::uint32_t cpsr=cpu->get_cpsr();

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    cone_insert=r'''            const std::uint32_t cpsr=cpu->get_cpsr();

            codeseg_ptr nboot2_b77_cone_phone_seg=nullptr;
            for (const auto &nboot2_b77_seg_obj :
                 kern->get_codeseg_list()) {
                codeseg_ptr nboot2_b77_seg =
                    reinterpret_cast<codeseg_ptr>(
                        nboot2_b77_seg_obj.get());
                if (!nboot2_b77_seg) {
                    continue;
                }
                const std::u16string nboot2_b77_seg_path =
                    common::lowercase_ucs2_string(
                        nboot2_b77_seg->get_full_path());
                if (nboot2_b77_seg_path ==
                    u"z:\\sys\\bin\\phoneuiutils.dll") {
                    nboot2_b77_cone_phone_seg=nboot2_b77_seg;
                    break;
                }
            }

            std::uint32_t nboot2_b77_cone_base=0;
            std::uint32_t nboot2_b77_cone_text_size=0;
            std::uint32_t nboot2_b77_cone_code_size=0;
            std::uint32_t nboot2_b77_cone_export_raw=0;
            std::uint32_t nboot2_b77_cone_export=0;
            std::uint32_t nboot2_b77_cone_limit=0;

            if (nboot2_b77_cone_phone_seg) {
                nboot2_b77_cone_base=
                    nboot2_b77_cone_phone_seg->
                        get_code_run_addr(caller_pr);
                nboot2_b77_cone_text_size=
                    nboot2_b77_cone_phone_seg->get_text_size();
                nboot2_b77_cone_code_size=
                    nboot2_b77_cone_phone_seg->get_code_size();
                nboot2_b77_cone_export_raw=
                    nboot2_b77_cone_phone_seg->lookup(
                        caller_pr,182U);
                nboot2_b77_cone_export=
                    nboot2_b77_cone_export_raw & ~1U;

                const std::uint64_t nboot2_b77_cone_end64 =
                    static_cast<std::uint64_t>(
                        nboot2_b77_cone_base) +
                    static_cast<std::uint64_t>(
                        nboot2_b77_cone_text_size);
                nboot2_b77_cone_limit =
                    nboot2_b77_cone_end64>0xFFFFFFFFULL
                        ? 0xFFFFFFFFU
                        : static_cast<std::uint32_t>(
                            nboot2_b77_cone_end64);

                const std::vector<std::uint32_t>
                    nboot2_b77_cone_exports =
                        nboot2_b77_cone_phone_seg->
                            get_export_table(caller_pr);
                for (const std::uint32_t nboot2_b77_export_raw :
                     nboot2_b77_cone_exports) {
                    const std::uint32_t nboot2_b77_export =
                        nboot2_b77_export_raw & ~1U;
                    if ((nboot2_b77_export>
                         nboot2_b77_cone_export) &&
                        (nboot2_b77_export<
                         nboot2_b77_cone_limit)) {
                        nboot2_b77_cone_limit=
                            nboot2_b77_export;
                    }
                }

                LOG_WARN(KERNEL,
                    "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT] "
                    "phase=CONE14 ordinal=182 base=0x{:08X} "
                    "text_size=0x{:08X} code_size=0x{:08X} "
                    "export_raw=0x{:08X} export_addr=0x{:08X} "
                    "export_offset=0x{:08X} next_export=0x{:08X} "
                    "span=0x{:08X} behavior=OBSERVE_ONLY",
                    nboot2_b77_cone_base,
                    nboot2_b77_cone_text_size,
                    nboot2_b77_cone_code_size,
                    nboot2_b77_cone_export_raw,
                    nboot2_b77_cone_export,
                    nboot2_b77_cone_export>=nboot2_b77_cone_base
                        ? nboot2_b77_cone_export-
                            nboot2_b77_cone_base : 0,
                    nboot2_b77_cone_limit,
                    nboot2_b77_cone_limit>
                            nboot2_b77_cone_export
                        ? nboot2_b77_cone_limit-
                            nboot2_b77_cone_export : 0);
            } else {
                LOG_WARN(KERNEL,
                    "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT] "
                    "phase=CONE14 ordinal=182 module_found=0 "
                    "behavior=OBSERVE_ONLY");
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    sv=rep1(sv,cone_anchor,cone_insert,
            "B77 CONE14 export resolver")

    cone_frame_anchor=r'''                    const std::uint32_t base=
                        seg->get_code_run_addr(caller_pr);
                    const std::string module=
                        common::ucs2_to_utf8(seg->get_full_path());
                    LOG_WARN(KERNEL,
'''
    cone_frame_insert=r'''                    const std::uint32_t base=
                        seg->get_code_run_addr(caller_pr);
                    const std::string module=
                        common::ucs2_to_utf8(seg->get_full_path());

                    if (nboot2_b77_cone_phone_seg &&
                        (seg==nboot2_b77_cone_phone_seg) &&
                        (addr>=nboot2_b77_cone_base)) {
                        const std::uint32_t nboot2_b77_off=
                            addr-nboot2_b77_cone_base;
                        if ((nboot2_b77_off==0x5094U) ||
                            (nboot2_b77_off==0x50B8U)) {
                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_LITERAL_PTR] "
                                "phase=CONE14 source={} index={} "
                                "raw=0x{:08X} offset=0x{:08X} "
                                "classification=DESCRIPTOR_LITERAL "
                                "behavior=OBSERVE_ONLY",
                                kind,stack_index,raw,nboot2_b77_off);
                        }
                    }

                    if (nboot2_b77_cone_export &&
                        (addr>=nboot2_b77_cone_export) &&
                        (addr<nboot2_b77_cone_limit)) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME] "
                            "phase=CONE14 source={} index={} "
                            "raw=0x{:08X} addr=0x{:08X} "
                            "export_addr=0x{:08X} delta=0x{:08X} "
                            "behavior=OBSERVE_ONLY",
                            kind,stack_index,raw,addr,
                            nboot2_b77_cone_export,
                            addr-nboot2_b77_cone_export);
                    }

                    LOG_WARN(KERNEL,
'''
    # The base/code/module sequence occurs elsewhere in svc.cpp too. Scope
    # this replacement strictly to B71's CONE14 frame-classifier lambda.
    nboot2_b77_lambda_start=sv.find("            auto nboot2_b71_log_frame =")
    nboot2_b77_lambda_end=sv.find(
        '            nboot2_b71_log_frame("pc",pc,0xFFFFFFFFU,pc);',
        nboot2_b77_lambda_start)
    if nboot2_b77_lambda_start<0 or nboot2_b77_lambda_end<0:
        fail("B71 CONE14 frame lambda bounds missing")
    nboot2_b77_lambda=sv[
        nboot2_b77_lambda_start:nboot2_b77_lambda_end]
    if nboot2_b77_lambda.count(cone_frame_anchor)!=1:
        fail("B77 CONE14 frame anchor inside lambda count="+
             str(nboot2_b77_lambda.count(cone_frame_anchor)))
    nboot2_b77_lambda=nboot2_b77_lambda.replace(
        cone_frame_anchor,cone_frame_insert,1)
    sv=(sv[:nboot2_b77_lambda_start]+nboot2_b77_lambda+
        sv[nboot2_b77_lambda_end:])

    fp_anchor=r'''            if ((fp>=0x40U)&&(fp<=0xFFFFFF7FU)) {
'''
    cone_deep=r'''            // B77: search beyond B71's original 128-word window for
            // frames that land specifically inside export-182's bounded region.
            constexpr std::uint32_t nboot2_b77_cone_words=384;
            if (nboot2_b77_cone_export &&
                nboot2_b77_cone_limit>
                    nboot2_b77_cone_export) {
                for (std::uint32_t i=nboot2_b71_stack_words;
                     i<nboot2_b77_cone_words;++i) {
                    const std::uint32_t slot_addr=
                        sp+i*sizeof(std::uint32_t);
                    if (slot_addr<sp) {
                        break;
                    }
                    const std::uint32_t *slot=
                        eka2l1::ptr<std::uint32_t>(
                            slot_addr).get(caller_pr);
                    if (!slot) {
                        break;
                    }
                    const std::uint32_t raw=*slot;
                    const std::uint32_t addr=raw & ~1U;
                    if ((addr>=nboot2_b77_cone_export) &&
                        (addr<nboot2_b77_cone_limit)) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME] "
                            "phase=CONE14 source=DEEP_STACK index={} "
                            "raw=0x{:08X} addr=0x{:08X} "
                            "export_addr=0x{:08X} delta=0x{:08X} "
                            "behavior=OBSERVE_ONLY",
                            i,raw,addr,nboot2_b77_cone_export,
                            addr-nboot2_b77_cone_export);
                    }
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE] "
                "phase=CONE14 stack_words_max={} behavior=OBSERVE_ONLY",
                nboot2_b77_cone_words);

            if ((fp>=0x40U)&&(fp<=0xFFFFFF7FU)) {
'''
    sv=rep1(sv,fp_anchor,cone_deep,
            "B77 CONE14 deep scan")

    required_fs=(
        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]",
        "[NBOOT2][PHONEUI_LITERAL_PTR]",
        "lookup(\n                            nboot2_b73_pr,182U)",
        "nboot2_b77_words=384",
        'u"z:\\\\sys\\\\bin\\\\phoneuiutils.dll"',
        "0x5094U",
        "0x50B8U",
    )
    for x in required_fs:
        if x not in fs:
            fail("fs post-apply gate missing: "+x)

    required_sv=(
        "[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]",
        "[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]",
        "[NBOOT2][PHONEUI_LITERAL_PTR]",
        "lookup(\n                        caller_pr,182U)",
        "nboot2_b77_cone_words=384",
        'u"z:\\\\sys\\\\bin\\\\phoneuiutils.dll"',
    )
    for x in required_sv:
        if x not in sv:
            fail("svc post-apply gate missing: "+x)

    diagnostic=fs_insert+classify_insert+deep_scan+cone_insert+cone_frame_insert+cone_deep
    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "set_int(",
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "thr->kill(",
        "write_file(",
        "WRITE_MODE",
    ):
        if forbidden in diagnostic:
            fail("behavior-changing token in B77 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    svc_cpp.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=PHONEUIUTILS_EXPORT182_RUNTIME_CORRELATION_DIAGNOSTIC")
    print("export_ordinal=182")
    print("symbol=CPhoneResourceResolverBase::BaseConstructL")
    print("file_server_stack_scan=384_WORDS")
    print("cone14_stack_scan=384_WORDS")
    print("offset_0x5094=DESCRIPTOR_LITERAL")
    print("offset_0x50B8=DESCRIPTOR_LITERAL")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_lifecycle=UNCHANGED")
    print("B76_HOST_FIX=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
