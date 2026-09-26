#!/usr/bin/env python3
"""NATIVEBOOT2 B80 PHONEUITARGETFP1.

B79 DEVICE1 proved a compact near-SP PhoneUIUtils call chain at CONE14:
  +0x1BBC -> +0x3B2E -> +0x3A28 -> BLX ARM +0x4350
while FileServer deep-stack context reaches ARM targets +0x4274/+0x41AC.

The RM-612 control firmware also showed that production Nokia PhoneUIUtils
export surfaces can differ from the public SymbianSource EABI DEF.  B80 is
therefore diagnostic-only and captures:
1. exact 64-byte runtime fingerprints for every validated B79 in-module target;
2. the real RM-356 PhoneUIUtils export count;
3. raw runtime export entries for ordinals 170..190 and 290..310;
4. an explicit warning that public DEF symbol labels are hints, not proof.

No guest behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B80-PHONEUITARGETFP1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b80_phoneuitargetfp1.py <upstream-root>")

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
        ("[NBOOT2][PHONEUI_CALLCHAIN_EDGE]",fs,"B79 fs"),
        ("[NBOOT2][PHONEUI_BLX_TARGET]",fs,"B79 fs"),
        ("[NBOOT2][PHONEUI_CALLCHAIN_EDGE]",sv,"B79 svc"),
        ("[NBOOT2][PHONEUI_BLX_TARGET]",sv,"B79 svc"),
        ("[NBOOT2][GAMEMENU_SAFE_TITLE]",mn,"B76"),
    ):
        if gate not in body:
            fail(f"{name} gate missing: {gate}")

    if "[NBOOT2][PHONEUI_TARGET_FINGERPRINT]" in fs:
        print(MARK+": already applied")
        return

    fs_anchor=r'''                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    fs_insert=r'''                                if (nboot2_b79_target_in_module) {
                                    const std::uint32_t nboot2_b80_off=
                                        target-nboot2_b77_phone_base;
                                    const bool nboot2_b80_room=
                                        nboot2_b80_off<=nboot2_b77_text_size &&
                                        (nboot2_b77_text_size-nboot2_b80_off)>=64U;
                                    if (nboot2_b80_room) {
                                        std::uint64_t nboot2_b80_hash=
                                            1469598103934665603ULL;
                                        std::uint32_t nboot2_b80_words[8]={};
                                        bool nboot2_b80_mapped=true;
                                        for (std::uint32_t nboot2_b80_i=0;
                                             nboot2_b80_i<64U;
                                             ++nboot2_b80_i) {
                                            const std::uint8_t *nboot2_b80_p=
                                                eka2l1::ptr<std::uint8_t>(
                                                    target+nboot2_b80_i)
                                                    .get(nboot2_b73_pr);
                                            if (!nboot2_b80_p) {
                                                nboot2_b80_mapped=false;
                                                break;
                                            }
                                            const std::uint8_t nboot2_b80_b=
                                                *nboot2_b80_p;
                                            nboot2_b80_hash^=
                                                static_cast<std::uint64_t>(
                                                    nboot2_b80_b);
                                            nboot2_b80_hash*=
                                                1099511628211ULL;
                                            if (nboot2_b80_i<32U) {
                                                nboot2_b80_words[
                                                    nboot2_b80_i/4U] |=
                                                    static_cast<std::uint32_t>(
                                                        nboot2_b80_b)
                                                    << ((nboot2_b80_i%4U)*8U);
                                            }
                                        }
                                        LOG_WARN(SERVICE_EFSRV,
                                            "[NBOOT2][PHONEUI_TARGET_FINGERPRINT] "
                                            "phase=FILESERVER path_kind={} "
                                            "opcode=0x{:02X} source={} index={} "
                                            "target=0x{:08X} "
                                            "target_offset=0x{:08X} state={} "
                                            "mapped={} bytes=64 "
                                            "fnv1a64=0x{:016X} "
                                            "w0=0x{:08X} w1=0x{:08X} "
                                            "w2=0x{:08X} w3=0x{:08X} "
                                            "w4=0x{:08X} w5=0x{:08X} "
                                            "w6=0x{:08X} w7=0x{:08X} "
                                            "behavior=OBSERVE_ONLY",
                                            nboot2_b74_phoneui
                                                ? "PHONEUI" : "CALLHANDLINGUI",
                                            nboot2_b74_opcode,source,index,
                                            target,nboot2_b80_off,
                                            nboot2_b79_target_state,
                                            nboot2_b80_mapped?1:0,
                                            nboot2_b80_hash,
                                            nboot2_b80_words[0],
                                            nboot2_b80_words[1],
                                            nboot2_b80_words[2],
                                            nboot2_b80_words[3],
                                            nboot2_b80_words[4],
                                            nboot2_b80_words[5],
                                            nboot2_b80_words[6],
                                            nboot2_b80_words[7]);
                                    }
                                }

                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    fs=rep1(fs,fs_anchor,fs_insert,"B80 FileServer target fingerprint")

    svc_anchor=r'''                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    svc_insert=r'''                            if (nboot2_b79_target_in_module) {
                                const std::uint32_t nboot2_b80_off=
                                    target-nboot2_b77_cone_base;
                                const bool nboot2_b80_room=
                                    nboot2_b80_off<=
                                        nboot2_b77_cone_text_size &&
                                    (nboot2_b77_cone_text_size-
                                        nboot2_b80_off)>=64U;
                                if (nboot2_b80_room) {
                                    std::uint64_t nboot2_b80_hash=
                                        1469598103934665603ULL;
                                    std::uint32_t nboot2_b80_words[8]={};
                                    bool nboot2_b80_mapped=true;
                                    for (std::uint32_t nboot2_b80_i=0;
                                         nboot2_b80_i<64U;
                                         ++nboot2_b80_i) {
                                        const std::uint8_t *nboot2_b80_p=
                                            eka2l1::ptr<std::uint8_t>(
                                                target+nboot2_b80_i)
                                                .get(caller_pr);
                                        if (!nboot2_b80_p) {
                                            nboot2_b80_mapped=false;
                                            break;
                                        }
                                        const std::uint8_t nboot2_b80_b=
                                            *nboot2_b80_p;
                                        nboot2_b80_hash^=
                                            static_cast<std::uint64_t>(
                                                nboot2_b80_b);
                                        nboot2_b80_hash*=
                                            1099511628211ULL;
                                        if (nboot2_b80_i<32U) {
                                            nboot2_b80_words[
                                                nboot2_b80_i/4U] |=
                                                static_cast<std::uint32_t>(
                                                    nboot2_b80_b)
                                                << ((nboot2_b80_i%4U)*8U);
                                        }
                                    }
                                    LOG_WARN(KERNEL,
                                        "[NBOOT2][PHONEUI_TARGET_FINGERPRINT] "
                                        "phase=CONE14 source={} index={} "
                                        "target=0x{:08X} "
                                        "target_offset=0x{:08X} state={} "
                                        "mapped={} bytes=64 "
                                        "fnv1a64=0x{:016X} "
                                        "w0=0x{:08X} w1=0x{:08X} "
                                        "w2=0x{:08X} w3=0x{:08X} "
                                        "w4=0x{:08X} w5=0x{:08X} "
                                        "w6=0x{:08X} w7=0x{:08X} "
                                        "behavior=OBSERVE_ONLY",
                                        kind,stack_index,target,
                                        nboot2_b80_off,
                                        nboot2_b79_target_state,
                                        nboot2_b80_mapped?1:0,
                                        nboot2_b80_hash,
                                        nboot2_b80_words[0],
                                        nboot2_b80_words[1],
                                        nboot2_b80_words[2],
                                        nboot2_b80_words[3],
                                        nboot2_b80_words[4],
                                        nboot2_b80_words[5],
                                        nboot2_b80_words[6],
                                        nboot2_b80_words[7]);
                                }
                            }

                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    sv=rep1(sv,svc_anchor,svc_insert,"B80 CONE14 target fingerprint")

    export_anchor=r'''            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    export_insert=r'''            if (nboot2_b77_cone_phone_seg) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][PHONEUI_EXPORT_IDENTITY_CAUTION] "
                    "phase=CONE14 production_export_count={} "
                    "public_symbiansource_def_count=387 "
                    "ordinal_symbol_mapping=UNVERIFIED "
                    "rm612_control_export_count=462 "
                    "behavior=OBSERVE_ONLY",
                    nboot2_b78_cone_exports.size());

                auto nboot2_b80_export_surface =
                    [&](const std::uint32_t ord) {
                        if ((ord==0U) ||
                            (ord>nboot2_b78_cone_exports.size())) {
                            return;
                        }
                        const std::uint32_t raw=
                            nboot2_b78_cone_exports[ord-1U];
                        const std::uint32_t addr=raw&~1U;
                        LOG_WARN(KERNEL,
                            "[NBOOT2][PHONEUI_EXPORT_SURFACE] "
                            "phase=CONE14 ordinal={} raw=0x{:08X} "
                            "addr=0x{:08X} offset=0x{:08X} "
                            "thumb={} behavior=OBSERVE_ONLY",
                            ord,raw,addr,
                            addr>=nboot2_b77_cone_base
                                ? addr-nboot2_b77_cone_base : 0,
                            raw&1U?1:0);
                    };

                for (std::uint32_t ord=170U;ord<=190U;++ord) {
                    nboot2_b80_export_surface(ord);
                }
                for (std::uint32_t ord=290U;ord<=310U;++ord) {
                    nboot2_b80_export_surface(ord);
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
'''
    sv=rep1(sv,export_anchor,export_insert,"B80 production export surface")

    for x in (
        "[NBOOT2][PHONEUI_TARGET_FINGERPRINT]",
        "fnv1a64=0x{:016X}",
        "bytes=64",
    ):
        if x not in fs:
            fail("fs post-apply gate missing: "+x)
        if x not in sv:
            fail("svc post-apply gate missing: "+x)

    for x in (
        "[NBOOT2][PHONEUI_EXPORT_IDENTITY_CAUTION]",
        "[NBOOT2][PHONEUI_EXPORT_SURFACE]",
        "public_symbiansource_def_count=387",
        "rm612_control_export_count=462",
        "ordinal_symbol_mapping=UNVERIFIED",
        "ord=170U;ord<=190U",
        "ord=290U;ord<=310U",
    ):
        if x not in sv:
            fail("svc export gate missing: "+x)

    diagnostic=fs_insert+svc_insert+export_insert
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
            fail("behavior-changing token in B80 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    svc_cpp.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=PHONEUI_RUNTIME_TARGET_FINGERPRINT_AND_EXPORT_SURFACE")
    print("target_fingerprint=64_BYTES_FNV1A_PLUS_8_WORDS")
    print("export_ranges=170_190_AND_290_310")
    print("public_def_symbol_mapping=UNVERIFIED")
    print("rm612_control_export_count=462")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_lifecycle=UNCHANGED")
    print("B76_HOST_FIX=PRESERVED")
    print("B77_B78_B79_DIAGNOSTICS=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
