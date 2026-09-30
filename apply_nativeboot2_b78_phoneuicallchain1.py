#!/usr/bin/env python3
"""NATIVEBOOT2 B78 PHONEUICALLCHAIN1.

B77 DEVICE1 proves:
- PhoneUIUtils EABI ordinal 182 resolves to RM-356 runtime +0x1BC8;
- no candidate in the 384-word FileServer or CONE14 scans lands inside
  ordinal-182's bounded +0x1BC8..+0x1BF6 range;
- +0x5094/+0x50B8 are descriptor/literal data, not executable callers.

The same B77 log contains nearby PhoneUIUtils candidates +0x1B74/+0x1B7C at
phoneui.r01 FileServer IPC and +0x1BC0/+0x3A38/+0x3B4C at CONE14. Offline
inspection of B71 CODE16 proves several are real Thumb BL return addresses.

B78 removes the remaining pointer heuristic:
- map key PhoneUI resolver exports 181/182/307/308 from the loaded RM-356 DLL;
- for every PhoneUIUtils stack/register candidate, accept it as a callsite only
  when the two halfwords immediately preceding a Thumb return address encode a
  real BL/BLX pair;
- decode Thumb BL targets;
- map both the return address and decoded target to the nearest runtime export
  range.

Diagnostic-only. No resource registration, panic, FileServer data/result,
SIM/state, scheduler, graphics, GameMenu or host lifecycle behavior changes.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B78-PHONEUICALLCHAIN1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b78_phoneuicallchain1.py <upstream-root>")

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
        ("[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",fs,"B77 fs"),
        ("[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]",fs,"B77 fs"),
        ("[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]",sv,"B77 svc"),
        ("[NBOOT2][PHONEUI_LITERAL_PTR]",sv,"B77 svc"),
        ("[NBOOT2][CONE14_PHONEUI]",sv,"B71"),
        ("[NBOOT2][GAMEMENU_SAFE_TITLE]",mn,"B76"),
    ):
        if gate not in body:
            fail(f"{name} gate missing: {gate}")

    if "[NBOOT2][PHONEUI_CALLSITE]" in fs:
        print(MARK+": already applied")
        return

    fs_anchor=r'''                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CALLER] path={} "
'''
    fs_helpers=r'''                // B78: runtime export ownership and validated Thumb
                // callsite helpers. A random pointer into PhoneUIUtils is no
                // longer treated as a caller merely because it falls in the
                // DLL address range.
                const std::vector<std::uint32_t> nboot2_b78_exports =
                    nboot2_b77_phone_seg
                        ? nboot2_b77_phone_seg->
                            get_export_table(nboot2_b73_pr)
                        : std::vector<std::uint32_t>();

                auto nboot2_b78_export_owner =
                    [&](const std::uint32_t addr,
                        std::uint32_t &ordinal,
                        std::uint32_t &begin,
                        std::uint32_t &end) {
                        ordinal=0;
                        begin=nboot2_b77_phone_base;
                        const std::uint64_t end64=
                            static_cast<std::uint64_t>(
                                nboot2_b77_phone_base)+
                            static_cast<std::uint64_t>(
                                nboot2_b77_text_size);
                        end=end64>0xFFFFFFFFULL
                            ? 0xFFFFFFFFU
                            : static_cast<std::uint32_t>(end64);

                        for (std::size_t i=0;
                             i<nboot2_b78_exports.size();++i) {
                            const std::uint32_t e=
                                nboot2_b78_exports[i]&~1U;
                            if ((e<nboot2_b77_phone_base) ||
                                (e>=end)) {
                                continue;
                            }
                            if ((e<=addr) && (e>=begin)) {
                                begin=e;
                                ordinal=
                                    static_cast<std::uint32_t>(i+1);
                            }
                        }
                        for (const std::uint32_t raw_e :
                             nboot2_b78_exports) {
                            const std::uint32_t e=raw_e&~1U;
                            if ((e>addr) && (e<end)) {
                                end=e;
                            }
                        }
                    };

                auto nboot2_b78_thumb_call =
                    [&](const std::uint32_t raw_return,
                        std::uint32_t &callsite,
                        std::uint32_t &target,
                        std::uint16_t &hi,
                        std::uint16_t &lo,
                        const char *&kind)->bool {
                        if ((raw_return&1U)==0U) {
                            return false;
                        }
                        const std::uint32_t ret=raw_return&~1U;
                        if (ret<4U) {
                            return false;
                        }
                        callsite=ret-4U;
                        const std::uint16_t *p_hi=
                            eka2l1::ptr<std::uint16_t>(callsite)
                                .get(nboot2_b73_pr);
                        const std::uint16_t *p_lo=
                            eka2l1::ptr<std::uint16_t>(callsite+2U)
                                .get(nboot2_b73_pr);
                        if (!p_hi || !p_lo) {
                            return false;
                        }
                        hi=*p_hi;
                        lo=*p_lo;
                        if ((hi&0xF800U)!=0xF000U) {
                            return false;
                        }
                        const bool is_bl=
                            (lo&0xF800U)==0xF800U;
                        const bool is_blx=
                            (lo&0xF800U)==0xE800U;
                        if (!is_bl && !is_blx) {
                            return false;
                        }
                        kind=is_bl ? "THUMB_BL" : "THUMB_BLX";
                        target=0;
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
                    };

                if (nboot2_b77_phone_seg) {
                    for (const std::uint32_t ord :
                         {181U,182U,307U,308U}) {
                        const std::uint32_t raw=
                            nboot2_b77_phone_seg->lookup(
                                nboot2_b73_pr,ord);
                        const std::uint32_t addr=raw&~1U;
                        std::uint32_t owner=0,begin=0,end=0;
                        nboot2_b78_export_owner(
                            addr,owner,begin,end);
                        const char *symbol=
                            ord==181U
                                ? "CPhoneMainResourceResolver::Instance"
                            : ord==182U
                                ? "CPhoneResourceResolverBase::BaseConstructL"
                            : ord==307U
                                ? "CPhoneResourceResolverBase::ResolveResourceID"
                                : "CPhoneResourceResolverBase::IsTelephonyFeatureSupported";
                        LOG_WARN(SERVICE_EFSRV,
                            "[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP] "
                            "phase=FILESERVER path_kind={} opcode=0x{:02X} "
                            "ordinal={} symbol={} raw=0x{:08X} "
                            "addr=0x{:08X} offset=0x{:08X} "
                            "range_end=0x{:08X} span=0x{:08X} "
                            "behavior=OBSERVE_ONLY",
                            nboot2_b74_phoneui
                                ? "PHONEUI" : "CALLHANDLINGUI",
                            nboot2_b74_opcode,ord,symbol,raw,addr,
                            addr>=nboot2_b77_phone_base
                                ? addr-nboot2_b77_phone_base : 0,
                            end,end>addr?end-addr:0);
                    }
                }

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_CALLER] path={} "
'''
    fs=rep1(fs,fs_anchor,fs_helpers,
            "B78 FileServer helpers/export map")

    fs_class_anchor=r'''                        if (module) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_FRAME] "
'''
    fs_class_insert=r'''                        if (nboot2_b77_phone_seg &&
                            (addr>=nboot2_b77_phone_base) &&
                            (addr<nboot2_b77_phone_base+
                                  nboot2_b77_text_size)) {
                            std::uint32_t callsite=0,target=0;
                            std::uint16_t hi=0,lo=0;
                            const char *call_kind="NONE";
                            if (nboot2_b78_thumb_call(
                                    raw,callsite,target,hi,lo,
                                    call_kind)) {
                                std::uint32_t ret_ord=0,ret_begin=0,
                                    ret_end=0;
                                nboot2_b78_export_owner(
                                    addr,ret_ord,ret_begin,ret_end);

                                std::uint32_t target_ord=0,
                                    target_begin=0,target_end=0;
                                if (target>=nboot2_b77_phone_base &&
                                    target<nboot2_b77_phone_base+
                                        nboot2_b77_text_size) {
                                    nboot2_b78_export_owner(
                                        target,target_ord,
                                        target_begin,target_end);
                                }

                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLSITE] "
                                    "phase=FILESERVER path_kind={} "
                                    "opcode=0x{:02X} source={} index={} "
                                    "raw_return=0x{:08X} "
                                    "return_offset=0x{:08X} "
                                    "callsite=0x{:08X} "
                                    "callsite_offset=0x{:08X} "
                                    "hi=0x{:04X} lo=0x{:04X} kind={} "
                                    "target=0x{:08X} target_offset=0x{:08X} "
                                    "return_owner_ordinal={} "
                                    "return_owner_start=0x{:08X} "
                                    "return_owner_end=0x{:08X} "
                                    "target_owner_ordinal={} "
                                    "target_owner_start=0x{:08X} "
                                    "target_owner_end=0x{:08X} "
                                    "validation=REAL_CALLSITE "
                                    "behavior=OBSERVE_ONLY",
                                    nboot2_b74_phoneui
                                        ? "PHONEUI" : "CALLHANDLINGUI",
                                    nboot2_b74_opcode,source,index,raw,
                                    addr-nboot2_b77_phone_base,
                                    callsite,
                                    callsite>=nboot2_b77_phone_base
                                        ? callsite-nboot2_b77_phone_base : 0,
                                    hi,lo,call_kind,target,
                                    target>=nboot2_b77_phone_base
                                        ? target-nboot2_b77_phone_base : 0,
                                    ret_ord,ret_begin,ret_end,
                                    target_ord,target_begin,target_end);
                            }
                        }

                        if (module) {
                            LOG_WARN(SERVICE_EFSRV,
                                "[NBOOT2][PHONEUI_RES_FRAME] "
'''
    fs=rep1(fs,fs_class_anchor,fs_class_insert,
            "B78 FileServer validated callsite")

    cone_anchor=r'''            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    cone_helpers=r'''            const std::vector<std::uint32_t>
                nboot2_b78_cone_exports =
                    nboot2_b77_cone_phone_seg
                        ? nboot2_b77_cone_phone_seg->
                            get_export_table(caller_pr)
                        : std::vector<std::uint32_t>();

            auto nboot2_b78_cone_owner =
                [&](const std::uint32_t addr,
                    std::uint32_t &ordinal,
                    std::uint32_t &begin,
                    std::uint32_t &end) {
                    ordinal=0;
                    begin=nboot2_b77_cone_base;
                    const std::uint64_t end64=
                        static_cast<std::uint64_t>(
                            nboot2_b77_cone_base)+
                        static_cast<std::uint64_t>(
                            nboot2_b77_cone_text_size);
                    end=end64>0xFFFFFFFFULL
                        ? 0xFFFFFFFFU
                        : static_cast<std::uint32_t>(end64);
                    for (std::size_t i=0;
                         i<nboot2_b78_cone_exports.size();++i) {
                        const std::uint32_t e=
                            nboot2_b78_cone_exports[i]&~1U;
                        if ((e<nboot2_b77_cone_base) ||
                            (e>=end)) {
                            continue;
                        }
                        if ((e<=addr) && (e>=begin)) {
                            begin=e;
                            ordinal=
                                static_cast<std::uint32_t>(i+1);
                        }
                    }
                    for (const std::uint32_t raw_e :
                         nboot2_b78_cone_exports) {
                        const std::uint32_t e=raw_e&~1U;
                        if ((e>addr) && (e<end)) {
                            end=e;
                        }
                    }
                };

            auto nboot2_b78_cone_thumb_call =
                [&](const std::uint32_t raw_return,
                    std::uint32_t &callsite,
                    std::uint32_t &target,
                    std::uint16_t &hi,
                    std::uint16_t &lo,
                    const char *&kind)->bool {
                    if ((raw_return&1U)==0U) {
                        return false;
                    }
                    const std::uint32_t ret=raw_return&~1U;
                    if (ret<4U) {
                        return false;
                    }
                    callsite=ret-4U;
                    const std::uint16_t *p_hi=
                        eka2l1::ptr<std::uint16_t>(callsite)
                            .get(caller_pr);
                    const std::uint16_t *p_lo=
                        eka2l1::ptr<std::uint16_t>(callsite+2U)
                            .get(caller_pr);
                    if (!p_hi || !p_lo) {
                        return false;
                    }
                    hi=*p_hi;
                    lo=*p_lo;
                    if ((hi&0xF800U)!=0xF000U) {
                        return false;
                    }
                    const bool is_bl=(lo&0xF800U)==0xF800U;
                    const bool is_blx=(lo&0xF800U)==0xE800U;
                    if (!is_bl && !is_blx) {
                        return false;
                    }
                    kind=is_bl ? "THUMB_BL" : "THUMB_BLX";
                    target=0;
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
                };

            if (nboot2_b77_cone_phone_seg) {
                for (const std::uint32_t ord :
                     {181U,182U,307U,308U}) {
                    const std::uint32_t raw=
                        nboot2_b77_cone_phone_seg->lookup(
                            caller_pr,ord);
                    const std::uint32_t addr=raw&~1U;
                    std::uint32_t owner=0,begin=0,end=0;
                    nboot2_b78_cone_owner(
                        addr,owner,begin,end);
                    const char *symbol=
                        ord==181U
                            ? "CPhoneMainResourceResolver::Instance"
                        : ord==182U
                            ? "CPhoneResourceResolverBase::BaseConstructL"
                        : ord==307U
                            ? "CPhoneResourceResolverBase::ResolveResourceID"
                            : "CPhoneResourceResolverBase::IsTelephonyFeatureSupported";
                    LOG_WARN(KERNEL,
                        "[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP] "
                        "phase=CONE14 ordinal={} symbol={} "
                        "raw=0x{:08X} addr=0x{:08X} "
                        "offset=0x{:08X} range_end=0x{:08X} "
                        "span=0x{:08X} behavior=OBSERVE_ONLY",
                        ord,symbol,raw,addr,
                        addr>=nboot2_b77_cone_base
                            ? addr-nboot2_b77_cone_base : 0,
                        end,end>addr?end-addr:0);
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    sv=rep1(sv,cone_anchor,cone_helpers,
            "B78 CONE14 helpers/export map")

    cone_frame_anchor=r'''                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_FRAME] kind={} stack_index={} "
'''
    cone_frame_insert=r'''                    if (nboot2_b77_cone_phone_seg &&
                        (seg==nboot2_b77_cone_phone_seg) &&
                        (addr>=nboot2_b77_cone_base) &&
                        (addr<nboot2_b77_cone_base+
                              nboot2_b77_cone_text_size)) {
                        std::uint32_t callsite=0,target=0;
                        std::uint16_t hi=0,lo=0;
                        const char *call_kind="NONE";
                        if (nboot2_b78_cone_thumb_call(
                                raw,callsite,target,hi,lo,
                                call_kind)) {
                            std::uint32_t ret_ord=0,
                                ret_begin=0,ret_end=0;
                            nboot2_b78_cone_owner(
                                addr,ret_ord,ret_begin,ret_end);

                            std::uint32_t target_ord=0,
                                target_begin=0,target_end=0;
                            if (target>=nboot2_b77_cone_base &&
                                target<nboot2_b77_cone_base+
                                    nboot2_b77_cone_text_size) {
                                nboot2_b78_cone_owner(
                                    target,target_ord,
                                    target_begin,target_end);
                            }

                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLSITE] "
                                "phase=CONE14 source={} index={} "
                                "raw_return=0x{:08X} "
                                "return_offset=0x{:08X} "
                                "callsite=0x{:08X} "
                                "callsite_offset=0x{:08X} "
                                "hi=0x{:04X} lo=0x{:04X} kind={} "
                                "target=0x{:08X} target_offset=0x{:08X} "
                                "return_owner_ordinal={} "
                                "return_owner_start=0x{:08X} "
                                "return_owner_end=0x{:08X} "
                                "target_owner_ordinal={} "
                                "target_owner_start=0x{:08X} "
                                "target_owner_end=0x{:08X} "
                                "validation=REAL_CALLSITE "
                                "behavior=OBSERVE_ONLY",
                                kind,stack_index,raw,
                                addr-nboot2_b77_cone_base,
                                callsite,
                                callsite>=nboot2_b77_cone_base
                                    ? callsite-nboot2_b77_cone_base : 0,
                                hi,lo,call_kind,target,
                                target>=nboot2_b77_cone_base
                                    ? target-nboot2_b77_cone_base : 0,
                                ret_ord,ret_begin,ret_end,
                                target_ord,target_begin,target_end);
                        }
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_FRAME] kind={} stack_index={} "
'''
    # Scope this anchor to B71 frame lambda because svc.cpp has many logs.
    ls=sv.find("            auto nboot2_b71_log_frame =")
    le=sv.find('            nboot2_b71_log_frame("pc",pc,0xFFFFFFFFU,pc);',ls)
    if ls<0 or le<0:
        fail("B71 frame lambda bounds missing")
    block=sv[ls:le]
    if block.count(cone_frame_anchor)!=1:
        fail("B78 CONE frame anchor count="+str(block.count(cone_frame_anchor)))
    block=block.replace(cone_frame_anchor,cone_frame_insert,1)
    sv=sv[:ls]+block+sv[le:]

    for x in (
        "[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]",
        "[NBOOT2][PHONEUI_CALLSITE]",
        "validation=REAL_CALLSITE",
        "CPhoneMainResourceResolver::Instance",
        "CPhoneResourceResolverBase::BaseConstructL",
        "CPhoneResourceResolverBase::ResolveResourceID",
        "181U,182U,307U,308U",
        "THUMB_BL",
    ):
        if x not in fs:
            fail("fs post-apply gate missing: "+x)
        if x not in sv:
            fail("svc post-apply gate missing: "+x)

    diagnostic=fs_helpers+fs_class_insert+cone_helpers+cone_frame_insert
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
    ):
        if forbidden in diagnostic:
            fail("behavior-changing token in B78 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    svc_cpp.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=PHONEUIUTILS_VALIDATED_CALL_CHAIN_DIAGNOSTIC")
    print("key_exports=181,182,307,308")
    print("callsite_validation=THUMB_BL_BLX_INSTRUCTION_PAIR")
    print("thumb_bl_target_decode=ENABLED")
    print("return_export_owner=ENABLED")
    print("target_export_owner=ENABLED")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_lifecycle=UNCHANGED")
    print("B76_HOST_FIX=PRESERVED")
    print("B77_EXPORT182=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
