#!/usr/bin/env python3
"""NATIVEBOOT2 B82 PHONEUIVENEERDEST1.

B81 DEVICE1 corrected three PhoneUIUtils Thumb->ARM BLX targets to real
interworking veneers:
  +0x1B70 -> +0x46F4
  +0x1B78 -> +0x4694
  +0x3A34 -> +0x46C4

Each veneer begins with ARM E51FF004 (LDR pc,[pc,#-4]).  B82 follows exactly
one such veneer hop, resolves the literal target to the loaded production
codeseg, reports the exact export ownership around that destination, and emits
a 64-byte fingerprint.

Diagnostic-only.  No resource registration, FileServer result/data/cursor,
panic, SIM/state, scheduler, graphics, GameMenu, export patching, or host
lifecycle behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B82-PHONEUIVENEERDEST1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b82_phoneuiveneerdest1.py <upstream-root>")

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
        ("target_decode=BLX_IMM10L_BITS_10_1",fs,"B81 fs"),
        ("target_decode=BLX_IMM10L_BITS_10_1",sv,"B81 svc"),
        ("[NBOOT2][PHONEUI_TARGET_FINGERPRINT]",fs,"B80 fs"),
        ("[NBOOT2][PHONEUI_TARGET_FINGERPRINT]",sv,"B80 svc"),
        ("[NBOOT2][GAMEMENU_SAFE_TITLE]",mn,"B76"),
    ):
        if gate not in body:
            fail(f"{name} gate missing: {gate}")

    if "[NBOOT2][PHONEUI_VENEER_DEST]" in fs:
        print(MARK+": already applied")
        return

    fs_anchor=r'''                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    fs_insert=r'''                                // B82: follow exactly one ARM
                                // LDR pc,[pc,#-4] veneer produced by a
                                // validated B81 BLX target.
                                if (nboot2_b79_target_in_module &&
                                    nboot2_b77_kern) {
                                    const std::uint32_t *nboot2_b82_ins=
                                        eka2l1::ptr<std::uint32_t>(target)
                                            .get(nboot2_b73_pr);
                                    const std::uint32_t *nboot2_b82_lit=
                                        eka2l1::ptr<std::uint32_t>(target+4U)
                                            .get(nboot2_b73_pr);
                                    if (nboot2_b82_ins && nboot2_b82_lit &&
                                        (*nboot2_b82_ins==0xE51FF004U)) {
                                        const std::uint32_t
                                            nboot2_b82_dest_raw=*nboot2_b82_lit;
                                        const std::uint32_t nboot2_b82_dest=
                                            nboot2_b82_dest_raw&~1U;
                                        codeseg_ptr nboot2_b82_seg=nullptr;
                                        std::uint32_t nboot2_b82_base=0;
                                        std::uint32_t nboot2_b82_code_size=0;
                                        for (const auto &nboot2_b82_obj :
                                             nboot2_b77_kern->
                                                 get_codeseg_list()) {
                                            codeseg_ptr nboot2_b82_try=
                                                reinterpret_cast<codeseg_ptr>(
                                                    nboot2_b82_obj.get());
                                            if (!nboot2_b82_try) {
                                                continue;
                                            }
                                            const std::uint32_t
                                                nboot2_b82_try_base=
                                                    nboot2_b82_try->
                                                        get_code_run_addr(
                                                            nboot2_b73_pr);
                                            const std::uint32_t
                                                nboot2_b82_try_size=
                                                    nboot2_b82_try->
                                                        get_code_size();
                                            const std::uint64_t
                                                nboot2_b82_try_end=
                                                    static_cast<std::uint64_t>(
                                                        nboot2_b82_try_base)+
                                                    nboot2_b82_try_size;
                                            if (nboot2_b82_try_base &&
                                                nboot2_b82_dest>=
                                                    nboot2_b82_try_base &&
                                                static_cast<std::uint64_t>(
                                                    nboot2_b82_dest)<
                                                    nboot2_b82_try_end) {
                                                nboot2_b82_seg=
                                                    nboot2_b82_try;
                                                nboot2_b82_base=
                                                    nboot2_b82_try_base;
                                                nboot2_b82_code_size=
                                                    nboot2_b82_try_size;
                                                break;
                                            }
                                        }

                                        if (nboot2_b82_seg) {
                                            const std::vector<std::uint32_t>
                                                nboot2_b82_exports=
                                                    nboot2_b82_seg->
                                                        get_export_table(
                                                            nboot2_b73_pr);
                                            std::uint32_t nboot2_b82_ord=0;
                                            std::uint32_t
                                                nboot2_b82_owner_begin=
                                                    nboot2_b82_base;
                                            std::uint32_t
                                                nboot2_b82_owner_end=
                                                    nboot2_b82_base+
                                                    nboot2_b82_code_size;
                                            for (std::size_t nboot2_b82_i=0;
                                                 nboot2_b82_i<
                                                     nboot2_b82_exports.size();
                                                 ++nboot2_b82_i) {
                                                const std::uint32_t
                                                    nboot2_b82_e=
                                                        nboot2_b82_exports[
                                                            nboot2_b82_i]&~1U;
                                                if (nboot2_b82_e<=
                                                        nboot2_b82_dest &&
                                                    nboot2_b82_e>=
                                                        nboot2_b82_owner_begin) {
                                                    nboot2_b82_owner_begin=
                                                        nboot2_b82_e;
                                                    nboot2_b82_ord=
                                                        static_cast<
                                                            std::uint32_t>(
                                                            nboot2_b82_i+1U);
                                                }
                                                if (nboot2_b82_e>
                                                        nboot2_b82_dest &&
                                                    nboot2_b82_e<
                                                        nboot2_b82_owner_end) {
                                                    nboot2_b82_owner_end=
                                                        nboot2_b82_e;
                                                }
                                            }

                                            const auto nboot2_b82_uids=
                                                nboot2_b82_seg->get_uids();
                                            const std::string
                                                nboot2_b82_module=
                                                    common::ucs2_to_utf8(
                                                        nboot2_b82_seg->
                                                            get_full_path());

                                            LOG_WARN(SERVICE_EFSRV,
                                                "[NBOOT2][PHONEUI_VENEER_DEST] "
                                                "phase=FILESERVER "
                                                "path_kind={} opcode=0x{:02X} "
                                                "source={} index={} "
                                                "veneer=0x{:08X} "
                                                "veneer_offset=0x{:08X} "
                                                "ins=0x{:08X} "
                                                "literal=0x{:08X} "
                                                "dest=0x{:08X} thumb={} "
                                                "module={} uid3=0x{:08X} "
                                                "base=0x{:08X} "
                                                "code_size=0x{:08X} "
                                                "dest_offset=0x{:08X} "
                                                "export_count={} "
                                                "owner_ordinal={} "
                                                "owner_start=0x{:08X} "
                                                "owner_end=0x{:08X} "
                                                "exact_export={} "
                                                "behavior=OBSERVE_ONLY",
                                                nboot2_b74_phoneui
                                                    ? "PHONEUI"
                                                    : "CALLHANDLINGUI",
                                                nboot2_b74_opcode,source,index,
                                                target,
                                                target>=
                                                        nboot2_b77_phone_base
                                                    ? target-
                                                        nboot2_b77_phone_base
                                                    : 0,
                                                *nboot2_b82_ins,
                                                nboot2_b82_dest_raw,
                                                nboot2_b82_dest,
                                                nboot2_b82_dest_raw&1U?1:0,
                                                nboot2_b82_module,
                                                std::get<2>(
                                                    nboot2_b82_uids),
                                                nboot2_b82_base,
                                                nboot2_b82_code_size,
                                                nboot2_b82_dest-
                                                    nboot2_b82_base,
                                                nboot2_b82_exports.size(),
                                                nboot2_b82_ord,
                                                nboot2_b82_owner_begin,
                                                nboot2_b82_owner_end,
                                                nboot2_b82_owner_begin==
                                                        nboot2_b82_dest
                                                    ? 1 : 0);

                                            const std::uint32_t
                                                nboot2_b82_dest_off=
                                                    nboot2_b82_dest-
                                                    nboot2_b82_base;
                                            const bool nboot2_b82_room=
                                                nboot2_b82_dest_off<=
                                                    nboot2_b82_code_size &&
                                                (nboot2_b82_code_size-
                                                    nboot2_b82_dest_off)>=64U;
                                            if (nboot2_b82_room) {
                                                std::uint64_t
                                                    nboot2_b82_hash=
                                                        1469598103934665603ULL;
                                                std::uint32_t
                                                    nboot2_b82_words[8]={};
                                                bool nboot2_b82_mapped=true;
                                                for (std::uint32_t
                                                     nboot2_b82_i=0;
                                                     nboot2_b82_i<64U;
                                                     ++nboot2_b82_i) {
                                                    const std::uint8_t
                                                        *nboot2_b82_p=
                                                            eka2l1::ptr<
                                                                std::uint8_t>(
                                                                nboot2_b82_dest+
                                                                nboot2_b82_i)
                                                                .get(
                                                                    nboot2_b73_pr);
                                                    if (!nboot2_b82_p) {
                                                        nboot2_b82_mapped=false;
                                                        break;
                                                    }
                                                    const std::uint8_t
                                                        nboot2_b82_b=
                                                            *nboot2_b82_p;
                                                    nboot2_b82_hash^=
                                                        static_cast<
                                                            std::uint64_t>(
                                                            nboot2_b82_b);
                                                    nboot2_b82_hash*=
                                                        1099511628211ULL;
                                                    if (nboot2_b82_i<32U) {
                                                        nboot2_b82_words[
                                                            nboot2_b82_i/4U] |=
                                                            static_cast<
                                                                std::uint32_t>(
                                                                nboot2_b82_b)
                                                            << ((nboot2_b82_i%
                                                                4U)*8U);
                                                    }
                                                }
                                                LOG_WARN(SERVICE_EFSRV,
                                                    "[NBOOT2][PHONEUI_VENEER_DEST_FP] "
                                                    "phase=FILESERVER "
                                                    "module={} "
                                                    "dest_offset=0x{:08X} "
                                                    "thumb={} mapped={} "
                                                    "bytes=64 "
                                                    "fnv1a64=0x{:016X} "
                                                    "w0=0x{:08X} "
                                                    "w1=0x{:08X} "
                                                    "w2=0x{:08X} "
                                                    "w3=0x{:08X} "
                                                    "w4=0x{:08X} "
                                                    "w5=0x{:08X} "
                                                    "w6=0x{:08X} "
                                                    "w7=0x{:08X} "
                                                    "behavior=OBSERVE_ONLY",
                                                    nboot2_b82_module,
                                                    nboot2_b82_dest_off,
                                                    nboot2_b82_dest_raw&1U
                                                        ? 1 : 0,
                                                    nboot2_b82_mapped?1:0,
                                                    nboot2_b82_hash,
                                                    nboot2_b82_words[0],
                                                    nboot2_b82_words[1],
                                                    nboot2_b82_words[2],
                                                    nboot2_b82_words[3],
                                                    nboot2_b82_words[4],
                                                    nboot2_b82_words[5],
                                                    nboot2_b82_words[6],
                                                    nboot2_b82_words[7]);
                                            }
                                        } else {
                                            LOG_WARN(SERVICE_EFSRV,
                                                "[NBOOT2][PHONEUI_VENEER_DEST] "
                                                "phase=FILESERVER "
                                                "veneer=0x{:08X} "
                                                "literal=0x{:08X} "
                                                "module_found=0 "
                                                "behavior=OBSERVE_ONLY",
                                                target,nboot2_b82_dest_raw);
                                        }
                                    }
                                }

                                LOG_WARN(SERVICE_EFSRV,
                                    "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    fs=rep1(fs,fs_anchor,fs_insert,"B82 FileServer veneer follow")

    svc_anchor=r'''                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    svc_insert=r'''                            // B82: follow one validated B81
                            // ARM interworking veneer into the production
                            // destination module.
                            if (nboot2_b79_target_in_module) {
                                const std::uint32_t *nboot2_b82_ins=
                                    eka2l1::ptr<std::uint32_t>(target)
                                        .get(caller_pr);
                                const std::uint32_t *nboot2_b82_lit=
                                    eka2l1::ptr<std::uint32_t>(target+4U)
                                        .get(caller_pr);
                                if (nboot2_b82_ins && nboot2_b82_lit &&
                                    (*nboot2_b82_ins==0xE51FF004U)) {
                                    const std::uint32_t
                                        nboot2_b82_dest_raw=*nboot2_b82_lit;
                                    const std::uint32_t nboot2_b82_dest=
                                        nboot2_b82_dest_raw&~1U;
                                    codeseg_ptr nboot2_b82_seg=nullptr;
                                    std::uint32_t nboot2_b82_base=0;
                                    std::uint32_t nboot2_b82_code_size=0;
                                    for (const auto &nboot2_b82_obj :
                                         kern->get_codeseg_list()) {
                                        codeseg_ptr nboot2_b82_try=
                                            reinterpret_cast<codeseg_ptr>(
                                                nboot2_b82_obj.get());
                                        if (!nboot2_b82_try) {
                                            continue;
                                        }
                                        const std::uint32_t
                                            nboot2_b82_try_base=
                                                nboot2_b82_try->
                                                    get_code_run_addr(
                                                        caller_pr);
                                        const std::uint32_t
                                            nboot2_b82_try_size=
                                                nboot2_b82_try->
                                                    get_code_size();
                                        const std::uint64_t
                                            nboot2_b82_try_end=
                                                static_cast<std::uint64_t>(
                                                    nboot2_b82_try_base)+
                                                nboot2_b82_try_size;
                                        if (nboot2_b82_try_base &&
                                            nboot2_b82_dest>=
                                                nboot2_b82_try_base &&
                                            static_cast<std::uint64_t>(
                                                nboot2_b82_dest)<
                                                nboot2_b82_try_end) {
                                            nboot2_b82_seg=nboot2_b82_try;
                                            nboot2_b82_base=
                                                nboot2_b82_try_base;
                                            nboot2_b82_code_size=
                                                nboot2_b82_try_size;
                                            break;
                                        }
                                    }

                                    if (nboot2_b82_seg) {
                                        const std::vector<std::uint32_t>
                                            nboot2_b82_exports=
                                                nboot2_b82_seg->
                                                    get_export_table(
                                                        caller_pr);
                                        std::uint32_t nboot2_b82_ord=0;
                                        std::uint32_t nboot2_b82_owner_begin=
                                            nboot2_b82_base;
                                        std::uint32_t nboot2_b82_owner_end=
                                            nboot2_b82_base+
                                            nboot2_b82_code_size;
                                        for (std::size_t nboot2_b82_i=0;
                                             nboot2_b82_i<
                                                 nboot2_b82_exports.size();
                                             ++nboot2_b82_i) {
                                            const std::uint32_t nboot2_b82_e=
                                                nboot2_b82_exports[
                                                    nboot2_b82_i]&~1U;
                                            if (nboot2_b82_e<=
                                                    nboot2_b82_dest &&
                                                nboot2_b82_e>=
                                                    nboot2_b82_owner_begin) {
                                                nboot2_b82_owner_begin=
                                                    nboot2_b82_e;
                                                nboot2_b82_ord=
                                                    static_cast<
                                                        std::uint32_t>(
                                                        nboot2_b82_i+1U);
                                            }
                                            if (nboot2_b82_e>
                                                    nboot2_b82_dest &&
                                                nboot2_b82_e<
                                                    nboot2_b82_owner_end) {
                                                nboot2_b82_owner_end=
                                                    nboot2_b82_e;
                                            }
                                        }

                                        const auto nboot2_b82_uids=
                                            nboot2_b82_seg->get_uids();
                                        const std::string nboot2_b82_module=
                                            common::ucs2_to_utf8(
                                                nboot2_b82_seg->
                                                    get_full_path());

                                        LOG_WARN(KERNEL,
                                            "[NBOOT2][PHONEUI_VENEER_DEST] "
                                            "phase=CONE14 source={} index={} "
                                            "veneer=0x{:08X} "
                                            "veneer_offset=0x{:08X} "
                                            "ins=0x{:08X} "
                                            "literal=0x{:08X} "
                                            "dest=0x{:08X} thumb={} "
                                            "module={} uid3=0x{:08X} "
                                            "base=0x{:08X} "
                                            "code_size=0x{:08X} "
                                            "dest_offset=0x{:08X} "
                                            "export_count={} "
                                            "owner_ordinal={} "
                                            "owner_start=0x{:08X} "
                                            "owner_end=0x{:08X} "
                                            "exact_export={} "
                                            "behavior=OBSERVE_ONLY",
                                            kind,stack_index,target,
                                            target>=nboot2_b77_cone_base
                                                ? target-
                                                    nboot2_b77_cone_base : 0,
                                            *nboot2_b82_ins,
                                            nboot2_b82_dest_raw,
                                            nboot2_b82_dest,
                                            nboot2_b82_dest_raw&1U?1:0,
                                            nboot2_b82_module,
                                            std::get<2>(nboot2_b82_uids),
                                            nboot2_b82_base,
                                            nboot2_b82_code_size,
                                            nboot2_b82_dest-
                                                nboot2_b82_base,
                                            nboot2_b82_exports.size(),
                                            nboot2_b82_ord,
                                            nboot2_b82_owner_begin,
                                            nboot2_b82_owner_end,
                                            nboot2_b82_owner_begin==
                                                    nboot2_b82_dest
                                                ? 1 : 0);

                                        const std::uint32_t
                                            nboot2_b82_dest_off=
                                                nboot2_b82_dest-
                                                nboot2_b82_base;
                                        const bool nboot2_b82_room=
                                            nboot2_b82_dest_off<=
                                                nboot2_b82_code_size &&
                                            (nboot2_b82_code_size-
                                                nboot2_b82_dest_off)>=64U;
                                        if (nboot2_b82_room) {
                                            std::uint64_t nboot2_b82_hash=
                                                1469598103934665603ULL;
                                            std::uint32_t
                                                nboot2_b82_words[8]={};
                                            bool nboot2_b82_mapped=true;
                                            for (std::uint32_t nboot2_b82_i=0;
                                                 nboot2_b82_i<64U;
                                                 ++nboot2_b82_i) {
                                                const std::uint8_t
                                                    *nboot2_b82_p=
                                                        eka2l1::ptr<
                                                            std::uint8_t>(
                                                            nboot2_b82_dest+
                                                            nboot2_b82_i)
                                                            .get(caller_pr);
                                                if (!nboot2_b82_p) {
                                                    nboot2_b82_mapped=false;
                                                    break;
                                                }
                                                const std::uint8_t
                                                    nboot2_b82_b=
                                                        *nboot2_b82_p;
                                                nboot2_b82_hash^=
                                                    static_cast<
                                                        std::uint64_t>(
                                                        nboot2_b82_b);
                                                nboot2_b82_hash*=
                                                    1099511628211ULL;
                                                if (nboot2_b82_i<32U) {
                                                    nboot2_b82_words[
                                                        nboot2_b82_i/4U] |=
                                                        static_cast<
                                                            std::uint32_t>(
                                                            nboot2_b82_b)
                                                        << ((nboot2_b82_i%
                                                            4U)*8U);
                                                }
                                            }
                                            LOG_WARN(KERNEL,
                                                "[NBOOT2][PHONEUI_VENEER_DEST_FP] "
                                                "phase=CONE14 module={} "
                                                "dest_offset=0x{:08X} "
                                                "thumb={} mapped={} "
                                                "bytes=64 "
                                                "fnv1a64=0x{:016X} "
                                                "w0=0x{:08X} "
                                                "w1=0x{:08X} "
                                                "w2=0x{:08X} "
                                                "w3=0x{:08X} "
                                                "w4=0x{:08X} "
                                                "w5=0x{:08X} "
                                                "w6=0x{:08X} "
                                                "w7=0x{:08X} "
                                                "behavior=OBSERVE_ONLY",
                                                nboot2_b82_module,
                                                nboot2_b82_dest_off,
                                                nboot2_b82_dest_raw&1U?1:0,
                                                nboot2_b82_mapped?1:0,
                                                nboot2_b82_hash,
                                                nboot2_b82_words[0],
                                                nboot2_b82_words[1],
                                                nboot2_b82_words[2],
                                                nboot2_b82_words[3],
                                                nboot2_b82_words[4],
                                                nboot2_b82_words[5],
                                                nboot2_b82_words[6],
                                                nboot2_b82_words[7]);
                                        }
                                    } else {
                                        LOG_WARN(KERNEL,
                                            "[NBOOT2][PHONEUI_VENEER_DEST] "
                                            "phase=CONE14 "
                                            "veneer=0x{:08X} "
                                            "literal=0x{:08X} "
                                            "module_found=0 "
                                            "behavior=OBSERVE_ONLY",
                                            target,nboot2_b82_dest_raw);
                                    }
                                }
                            }

                            LOG_WARN(KERNEL,
                                "[NBOOT2][PHONEUI_CALLCHAIN_EDGE] "
'''
    sv=rep1(sv,svc_anchor,svc_insert,"B82 CONE14 veneer follow")

    for x in (
        "[NBOOT2][PHONEUI_VENEER_DEST]",
        "[NBOOT2][PHONEUI_VENEER_DEST_FP]",
        "0xE51FF004U",
        "owner_ordinal={}",
        "exact_export={}",
        "behavior=OBSERVE_ONLY",
    ):
        if x not in fs:
            fail("fs post-apply gate missing: "+x)
        if x not in sv:
            fail("svc post-apply gate missing: "+x)

    diagnostic=fs_insert+svc_insert
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
            fail("behavior-changing token in B82 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs,encoding="utf-8")
    svc_cpp.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=PHONEUI_ARM_VENEER_ONE_HOP_DESTINATION_IDENTITY")
    print("veneer_opcode=E51FF004")
    print("destination=MODULE_OFFSET_EXPORT_OWNER_FINGERPRINT")
    print("resource_registration=UNCHANGED")
    print("fileserver_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_lifecycle=UNCHANGED")
    print("B76_HOST_FIX=PRESERVED")
    print("B81_BLX_DECODE=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
