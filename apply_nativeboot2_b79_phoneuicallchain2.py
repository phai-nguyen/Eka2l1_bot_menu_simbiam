#!/usr/bin/env python3
"""NATIVEBOOT2 B79 PHONEUICALLCHAIN2.

B78 DEVICE1 proves the instruction validator is useful, but Thumb BLX
immediates were only recognized, not decoded.  The unresolved BLX edges are
exactly the most interesting FileServer and CONE14 candidates:

- FileServer +0x1B74 / +0x1B7C
- CONE14   +0x3A38

B79 is diagnostic-only and:
1. decodes Thumb BLX immediate targets using the T32 architectural encoding;
2. emits explicit BLX target markers;
3. records stack locality / SP delta so near-stack CONE14 frames can be
   separated from deep stale/context pointers;
4. emits a compact CALLCHAIN_EDGE record with return/target export ownership.

No resource registration, FileServer result/data/cursor, panic, SIM/state,
scheduler, graphics, GameMenu, or host lifecycle behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B79-PHONEUICALLCHAIN2"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b79_phoneuicallchain2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs_cpp=up/"src/emu/services/src/fs/fs.cpp"
    svc_cpp=up/"src/emu/kernel/src/svc.cpp"
    menu=up/"src/emu/ios/app/GameMenuView.mm"
    for p in (fs_cpp,svc_cpp,menu):
        if not p.is_file():
            fail(f"missing source: {p}")

    fs=fs_cpp.read_text(encoding="utf-8")
    sv=svc_cpp.read_text(encoding="utf-8")
    mn=menu.read_text(encoding="utf-8")

    for gate,body,name in (
        ("[NBOOT2][PHONEUI_CALLSITE]",fs,"B78 fs"),
        ("[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]",fs,"B78 fs"),
        ("[NBOOT2][PHONEUI_CALLSITE]",sv,"B78 svc"),
        ("[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]",sv,"B78 svc"),
        ("[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",sv,"B77"),
        ("[NBOOT2][GAMEMENU_SAFE_TITLE]",mn,"B76"),
    ):
        if gate not in body:
            fail(f"{name} gate missing: {gate}")

    if "[NBOOT2][PHONEUI_BLX_TARGET]" in fs:
        print(MARK+": already applied")
        return

    fs_decode_old=r'''                        target=0;
                        if (is_bl) {
                            const std::uint32_t s=(hi>>10U)&1U;
                            const std::uint32_t j1=(lo>>13U)&1U;
                            const std::uint32_t j2=(lo>>11U)&1U;
                            const std::uint32_t i1=(~(j1^s))&1U;
                            const std::uint32_t i2=(~(j2^s))&1U;
                            const std::uint32_t imm10=hi&0x03FFU;
                            const std::uint32_t imm11=lo&0x07FFU;
                            std::uint32_t imm25=
                                (s<<24U)|(i1<<23U)|(i2<<22U)|
                                (imm10<<12U)|(imm11<<1U);
                            const std::int32_t signed_off=
                                (imm25&0x01000000U)
                                    ? static_cast<std::int32_t>(
                                        imm25|0xFE000000U)
                                    : static_cast<std::int32_t>(imm25);
                            const std::int64_t target64=
                                static_cast<std::int64_t>(callsite)+4+
                                static_cast<std::int64_t>(signed_off);
                            target=static_cast<std::uint32_t>(
                                target64&0xFFFFFFFFLL);
                        }
                        return true;
'''
    fs_decode_new=r'''                        target=0;
                        const std::uint32_t s=(hi>>10U)&1U;
                        const std::uint32_t j1=(lo>>13U)&1U;
                        const std::uint32_t j2=(lo>>11U)&1U;
                        const std::uint32_t i1=(~(j1^s))&1U;
                        const std::uint32_t i2=(~(j2^s))&1U;
                        const std::uint32_t imm10h=hi&0x03FFU;
                        const std::uint32_t imm_low=
                            is_bl ? (lo&0x07FFU) : (lo&0x03FFU);
                        const std::uint32_t imm25=
                            is_bl
                                ? ((s<<24U)|(i1<<23U)|(i2<<22U)|
                                   (imm10h<<12U)|(imm_low<<1U))
                                : ((s<<24U)|(i1<<23U)|(i2<<22U)|
                                   (imm10h<<12U)|(imm_low<<2U));
                        const std::int32_t signed_off=
                            (imm25&0x01000000U)
                                ? static_cast<std::int32_t>(
                                    imm25|0xFE000000U)
                                : static_cast<std::int32_t>(imm25);
                        const std::uint32_t pc_base=
                            is_bl
                                ? callsite+4U
                                : ((callsite&~2U)+4U);
                        const std::int64_t target64=
                            static_cast<std::int64_t>(pc_base)+
                            static_cast<std::int64_t>(signed_off);
                        target=static_cast<std::uint32_t>(
                            target64&0xFFFFFFFFLL);
                        if (is_blx) {
                            target &= ~3U;
                        }
                        return true;
'''
    fs=rep1(fs,fs_decode_old,fs_decode_new,"B79 FileServer BLX decoder")

    svc_decode_old=r'''                    target=0;
                    if (is_bl) {
                        const std::uint32_t s=(hi>>10U)&1U;
                        const std::uint32_t j1=(lo>>13U)&1U;
                        const std::uint32_t j2=(lo>>11U)&1U;
                        const std::uint32_t i1=(~(j1^s))&1U;
                        const std::uint32_t i2=(~(j2^s))&1U;
                        const std::uint32_t imm10=hi&0x03FFU;
                        const std::uint32_t imm11=lo&0x07FFU;
                        std::uint32_t imm25=
                            (s<<24U)|(i1<<23U)|(i2<<22U)|
                            (imm10<<12U)|(imm11<<1U);
                        const std::int32_t signed_off=
                            (imm25&0x01000000U)
                                ? static_cast<std::int32_t>(
                                    imm25|0xFE000000U)
                                : static_cast<std::int32_t>(imm25);
                        const std::int64_t target64=
                            static_cast<std::int64_t>(callsite)+4+
                            static_cast<std::int64_t>(signed_off);
                        target=static_cast<std::uint32_t>(
                            target64&0xFFFFFFFFLL);
                    }
                    return true;
'''
    svc_decode_new=r'''                    target=0;
                    const std::uint32_t s=(hi>>10U)&1U;
                    const std::uint32_t j1=(lo>>13U)&1U;
                    const std::uint32_t j2=(lo>>11U)&1U;
                    const std::uint32_t i1=(~(j1^s))&1U;
                    const std::uint32_t i2=(~(j2^s))&1U;
                    const std::uint32_t imm10h=hi&0x03FFU;
                    const std::uint32_t imm_low=
                        is_bl ? (lo&0x07FFU) : (lo&0x03FFU);
                    const std::uint32_t imm25=
                        is_bl
                            ? ((s<<24U)|(i1<<23U)|(i2<<22U)|
                               (imm10h<<12U)|(imm_low<<1U))
                            : ((s<<24U)|(i1<<23U)|(i2<<22U)|
                               (imm10h<<12U)|(imm_low<<2U));
                    const std::int32_t signed_off=
                        (imm25&0x01000000U)
                            ? static_cast<std::int32_t>(
                                imm25|0xFE000000U)
                            : static_cast<std::int32_t>(imm25);
                    const std::uint32_t pc_base=
                        is_bl
                            ? callsite+4U
                            : ((callsite&~2U)+4U);
                    const std::int64_t target64=
                        static_cast<std::int64_t>(pc_base)+
                        static_cast<std::int64_t>(signed_off);
                    target=static_cast<std::uint32_t>(
                        target64&0xFFFFFFFFLL);
                    if (is_blx) {
                        target &= ~3U;
                    }
                    return true;
'''
    sv=rep1(sv,svc_decode_old,svc_decode_new,"B79 CONE14 BLX decoder")

    fs_tail_old=r'''                                    ret_ord,ret_begin,ret_end,
                                    target_ord,target_begin,target_end);
                            }
                        }

                        if (module) {
'''
    fs_tail_new=r'''                                    ret_ord,ret_begin,ret_end,
                                    target_ord,target_begin,target_end);

                                const bool nboot2_b79_stack_source=
                                    (source[0]=='S') || (source[0]=='D');
                                const std::uint32_t nboot2_b79_sp_delta=
                                    nboot2_b79_stack_source
                                        ? index*4U : 0xFFFFFFFFU;
                                const char *nboot2_b79_locality=
                                    !nboot2_b79_stack_source
                                        ? "NON_STACK"
                                    : index<64U
                                        ? "NEAR_0_255B"
                                    : index<128U
                                        ? "MID_256_511B"
                                        : "DEEP_512B_PLUS";
                                const bool nboot2_b79_target_in_module=
                                    target>=nboot2_b77_phone_base &&
                                    target<nboot2_b77_phone_base+
                                        nboot2_b77_text_size;
                                const char *nboot2_b79_target_state=
                                    ((lo&0xF800U)==0xE800U)
                                        ? "ARM" : "THUMB";

                                if ((lo&0xF800U)==0xE800U) {
                                    LOG_WARN(SERVICE_EFSRV,
                                        "[NBOOT2][PHONEUI_BLX_TARGET] "
                                        "phase=FILESERVER path_kind={} "
                                        "opcode=0x{:02X} source={} index={} "
                                        "callsite=0x{:08X} "
                                        "callsite_offset=0x{:08X} "
                                        "target=0x{:08X} "
                                        "target_offset=0x{:08X} "
                                        "target_state=ARM "
                                        "sp_delta=0x{:08X} "
                                        "stack_locality={} "
                                        "behavior=OBSERVE_ONLY",
                                        nboot2_b74_phoneui
                                            ? "PHONEUI" : "CALLHANDLINGUI",
                                        nboot2_b74_opcode,source,index,
                                        callsite,
                                        callsite>=nboot2_b77_phone_base
                                            ? callsite-
                                                nboot2_b77_phone_base : 0,
                                        target,
                                        nboot2_b79_target_in_module
                                            ? target-
                                                nboot2_b77_phone_base : 0,
                                        nboot2_b79_sp_delta,
                                        nboot2_b79_locality);
                                }

                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
                                    "phase=FILESERVER path_kind={} "
                                    "opcode=0x{:02X} source={} index={} "
                                    "sp_delta=0x{:08X} stack_locality={} "
                                    "call_kind={} target_state={} "
                                    "return_offset=0x{:08X} "
                                    "target_offset=0x{:08X} "
                                    "return_owner_ordinal={} "
                                    "target_owner_ordinal={} "
                                    "target_scope={} "
                                    "validation=BL_OR_BLX_DECODED "
                                    "behavior=OBSERVE_ONLY",
                                    nboot2_b74_phoneui
                                        ? "PHONEUI" : "CALLHANDLINGUI",
                                    nboot2_b74_opcode,source,index,
                                    nboot2_b79_sp_delta,
                                    nboot2_b79_locality,
                                    call_kind,nboot2_b79_target_state,
                                    addr-nboot2_b77_phone_base,
                                    nboot2_b79_target_in_module
                                        ? target-nboot2_b77_phone_base : 0,
                                    ret_ord,target_ord,
                                    nboot2_b79_target_in_module
                                        ? "PHONEUIUTILS" : "EXTERNAL");
                            }
                        }

                        if (module) {
'''
    fs=rep1(fs,fs_tail_old,fs_tail_new,"B79 FileServer edge marker")

    svc_tail_old=r'''                                ret_ord,ret_begin,ret_end,
                                target_ord,target_begin,target_end);
                        }
                    }

                    LOG_WARN(KERNEL,
'''
    svc_tail_new=r'''                                ret_ord,ret_begin,ret_end,
                                target_ord,target_begin,target_end);

                            const bool nboot2_b79_stack_source=
                                kind[0]=='s';
                            const std::uint32_t nboot2_b79_sp_delta=
                                nboot2_b79_stack_source
                                    ? stack_index*4U : 0xFFFFFFFFU;
                            const char *nboot2_b79_locality=
                                !nboot2_b79_stack_source
                                    ? "NON_STACK"
                                : stack_index<64U
                                    ? "NEAR_0_255B"
                                : stack_index<128U
                                    ? "MID_256_511B"
                                    : "DEEP_512B_PLUS";
                            const bool nboot2_b79_target_in_module=
                                target>=nboot2_b77_cone_base &&
                                target<nboot2_b77_cone_base+
                                    nboot2_b77_cone_text_size;
                            const char *nboot2_b79_target_state=
                                ((lo&0xF800U)==0xE800U)
                                    ? "ARM" : "THUMB";

                            if ((lo&0xF800U)==0xE800U) {
                                LOG_WARN(KERNEL,
                                    "[NBOOT2][PHONEUI_BLX_TARGET] "
                                    "phase=CONE14 source={} index={} "
                                    "callsite=0x{:08X} "
                                    "callsite_offset=0x{:08X} "
                                    "target=0x{:08X} "
                                    "target_offset=0x{:08X} "
                                    "target_state=ARM "
                                    "sp_delta=0x{:08X} "
                                    "stack_locality={} "
                                    "behavior=OBSERVE_ONLY",
                                    kind,stack_index,callsite,
                                    callsite>=nboot2_b77_cone_base
                                        ? callsite-
                                            nboot2_b77_cone_base : 0,
                                    target,
                                    nboot2_b79_target_in_module
                                        ? target-
                                            nboot2_b77_cone_base : 0,
                                    nboot2_b79_sp_delta,
                                    nboot2_b79_locality);
                            }

                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
                                "phase=CONE14 source={} index={} "
                                "sp_delta=0x{:08X} stack_locality={} "
                                "call_kind={} target_state={} "
                                "return_offset=0x{:08X} "
                                "target_offset=0x{:08X} "
                                "return_owner_ordinal={} "
                                "target_owner_ordinal={} "
                                "target_scope={} "
                                "validation=BL_OR_BLX_DECODED "
                                "behavior=OBSERVE_ONLY",
                                kind,stack_index,nboot2_b79_sp_delta,
                                nboot2_b79_locality,
                                call_kind,nboot2_b79_target_state,
                                addr-nboot2_b77_cone_base,
                                nboot2_b79_target_in_module
                                    ? target-nboot2_b77_cone_base : 0,
                                ret_ord,target_ord,
                                nboot2_b79_target_in_module
                                    ? "PHONEUIUTILS" : "EXTERNAL");
                        }
                    }

                    LOG_WARN(KERNEL,
'''
    sv=rep1(sv,svc_tail_old,svc_tail_new,"B79 CONE14 edge marker")

    for x in (
        "[NBOOT2][PHONEUI_BLX_TARGET]",
        "[NBOOT2][PHONEUI_CALLCHAIN_EDGE]",
        "BL_OR_BLX_DECODED",
        "NEAR_0_255B",
        "DEEP_512B_PLUS",
        "target_state=ARM",
        "imm_low",
        "callsite&~2U",
    ):
        if x not in fs:
            fail("fs post-apply gate missing: "+x)
        if x not in sv:
            fail("svc post-apply gate missing: "+x)

    diagnostic=fs_decode_new+svc_decode_new+fs_tail_new+svc_tail_new
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
        "set_export(",
        "AddResourceFile",
    ):
        if forbidden in diagnostic:
            fail("behavior-changing token in B79 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    svc_cpp.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=PHONEUIUTILS_CALLCHAIN_BLX_DECODE_AND_STACK_LOCALITY")
    print("thumb_bl_target_decode=PRESERVED")
    print("thumb_blx_target_decode=ENABLED")
    print("blx_pc_base=ALIGN_PC_4")
    print("stack_locality=NEAR_MID_DEEP")
    print("callchain_edge=ENABLED")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_lifecycle=UNCHANGED")
    print("B76_HOST_FIX=PRESERVED")
    print("B77_B78_DIAGNOSTICS=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
