#!/usr/bin/env python3
r"""NATIVEBOOT2 B71 PHONEUICONE14RES1.

B70 DEVICE1 proves the immediate RM-356 fatal boundary:
Telephone/phoneui UID3 0x100058B3 -> CONE 14 -> Starter result 14 ->
KPSGlobalSystemState 101 -> 116 -> native "Phone start-up failed" UI.

Authoritative Symbian Classic UI source defines CONE 14 as
ECoePanicNoResourceFileForId: no loaded CCoeEnv resource file owns the
requested resource ID.

B71 is diagnostic-only:
- capture the exact Telephone CONE14 registers and a deep guest stack;
- resolve code candidates to modules/offsets and emit bounded code windows;
- capture the exact z:\resource\apps\phoneui.r01 bytes through a separate
  read-only VFS handle for offline RSC decoding.

No resource-ID range is hard-coded. No panic/result/state/SIM/resource behavior
is modified.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B71-PHONEUICONE14RES1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b71_phoneuicone14res1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    fs=up/"src/emu/services/src/fs/files.cpp"
    sess=up/"src/emu/kernel/src/session.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    alarm=up/"src/emu/services/src/alarm/alarm.cpp"
    for p in (svc,fs,sess,sa,alarm):
        if not p.is_file():
            fail(f"missing source: {p}")

    sv=svc.read_text(encoding="utf-8")
    ff=fs.read_text(encoding="utf-8")
    se=sess.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    al=alarm.read_text(encoding="utf-8")

    markers=(
        "[NBOOT2][CONE14_PHONEUI]",
        "[NBOOT2][CONE14_FRAME]",
        "[NBOOT2][CONE14_STACK]",
        "[NBOOT2][CONE14_CODE16]",
        "[NBOOT2][PHONEUI_RSC_DUMP]",
    )
    present=[m for m in markers if m in (sv+"\n"+ff)]
    if present:
        if len(present)==len(markers):
            print(MARK+": already applied")
            return
        fail("partial B71 markers present: "+", ".join(present))

    for needle,text,name in (
        ("SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",sv,"MENUUI4"),
        ("static codeseg_ptr get_codeseg_from_addr(",sv,"codeseg helper"),
        ("[NBOOT2][STARTER_GLOBAL_STATE]",sv,"B62"),
        ("[NBOOT2][STARTER_WAIT_ANY]",sv,"B68"),
        ("[NBOOT2][STARTER_IPC_ARM]",se,"B70"),
        ("[NBOOT2][SIM_PS]",sv,"B70 SIM P&S"),
        ("[NBOOT2][STARTER_SSC_DUMP]",ff,"B67 read-only dump"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sat,"B64"),
        ("[NBOOT2][ALARM_ID_LIST]",al,"B69"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    sig="    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h, kernel::entity_exit_type etype, std::int32_t reason, eka2l1::ptr<desc8> reason_des) {"
    start=sv.find(sig)
    end=sv.find("\n    BRIDGE_FUNC(",start+len(sig))
    if start<0 or end<0:
        fail("thread_kill block not found")
    body=sv[start:end]
    anchor="        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"
    if body.count(anchor)!=1:
        fail(f"thread_kill dispatch anchor count={body.count(anchor)}")

    for need in (
        "kernel::thread *caller_thr = kern->crr_thread();",
        "kernel::process *caller_pr = kern->crr_process();",
        "kernel::process *target_pr = thr->owning_process();",
        "auto *cpu = kern->get_cpu();",
    ):
        if need not in body:
            fail("MENUUI4 variable missing: "+need)

    inject=r'''        // B71 PHONEUICONE14RES1: diagnostic-only capture of the
        // proven Telephone self-panic. The original thr->kill call remains
        // immediately below this block unchanged.
        const std::uint32_t nboot2_b71_target_uid3 = target_pr
            ? static_cast<std::uint32_t>(
                std::get<2>(target_pr->get_uid_type())) : 0;
        const bool nboot2_b71_phoneui_cone14 =
            cpu && caller_thr && caller_pr && target_pr
            && (nboot2_b71_target_uid3 == 0x100058B3U)
            && (reason == 14)
            && (exit_category == "CONE");

        if (nboot2_b71_phoneui_cone14) {
            const std::uint32_t pc=cpu->get_pc();
            const std::uint32_t lr=cpu->get_reg(14);
            const std::uint32_t sp=cpu->get_reg(13);
            const std::uint32_t fp=cpu->get_reg(11);
            const std::uint32_t cpsr=cpu->get_cpsr();

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_PHONEUI] process={} uid3=0x{:08X} "
                "thread={} reason={} category={} pc=0x{:08X} lr=0x{:08X} "
                "sp=0x{:08X} fp=0x{:08X} cpsr=0x{:08X} "
                "r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} "
                "r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} "
                "r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} "
                "r12=0x{:08X} behavior=OBSERVE_ONLY",
                target_pr->name(),nboot2_b71_target_uid3,thr->name(),
                reason,exit_category,pc,lr,sp,fp,cpsr,
                cpu->get_reg(0),cpu->get_reg(1),cpu->get_reg(2),
                cpu->get_reg(3),cpu->get_reg(4),cpu->get_reg(5),
                cpu->get_reg(6),cpu->get_reg(7),cpu->get_reg(8),
                cpu->get_reg(9),cpu->get_reg(10),cpu->get_reg(11),
                cpu->get_reg(12));

            auto nboot2_b71_log_frame =
                [&](const char *kind,const std::uint32_t raw,
                    const std::uint32_t stack_index,
                    const std::uint32_t slot_addr) {
                    const std::uint32_t addr=raw & ~1U;
                    codeseg_ptr seg=addr>=0x10000U
                        ? get_codeseg_from_addr(
                            kern,caller_pr,addr,false)
                        : nullptr;
                    if (!seg) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][CONE14_FRAME] kind={} stack_index={} "
                            "slot=0x{:08X} raw=0x{:08X} addr=0x{:08X} "
                            "module=<unresolved> behavior=OBSERVE_ONLY",
                            kind,stack_index,slot_addr,raw,addr);
                        return;
                    }

                    const std::uint32_t base=
                        seg->get_code_run_addr(caller_pr);
                    const std::string module=
                        common::ucs2_to_utf8(seg->get_full_path());
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_FRAME] kind={} stack_index={} "
                        "slot=0x{:08X} raw=0x{:08X} addr=0x{:08X} "
                        "module={} base=0x{:08X} offset=0x{:08X} thumb={} "
                        "behavior=OBSERVE_ONLY",
                        kind,stack_index,slot_addr,raw,addr,module,base,
                        addr-base,(raw&1U)?1:0);

                    const bool relevant=
                        (module.find("cone")!=std::string::npos) ||
                        (module.find("CONE")!=std::string::npos) ||
                        (module.find("phone")!=std::string::npos) ||
                        (module.find("Phone")!=std::string::npos) ||
                        (module.find("euser")!=std::string::npos) ||
                        (module.find("EUSER")!=std::string::npos);
                    if (!relevant) {
                        return;
                    }

                    for (std::int32_t rel=-24;rel<=12;++rel) {
                        const std::int64_t signed_addr=
                            static_cast<std::int64_t>(addr)
                            +static_cast<std::int64_t>(rel)*2;
                        if ((signed_addr<0) ||
                            (signed_addr>0xFFFFFFFFLL)) {
                            continue;
                        }
                        const std::uint32_t code_addr=
                            static_cast<std::uint32_t>(signed_addr);
                        const std::uint16_t *code16=
                            eka2l1::ptr<std::uint16_t>(
                                code_addr).get(caller_pr);
                        if (!code16) {
                            LOG_WARN(KERNEL,
                                "[NBOOT2][CONE14_CODE16] kind={} "
                                "stack_index={} module={} rel={} "
                                "address=0x{:08X} mapped=0 "
                                "behavior=OBSERVE_ONLY",
                                kind,stack_index,module,rel,code_addr);
                        } else {
                            LOG_WARN(KERNEL,
                                "[NBOOT2][CONE14_CODE16] kind={} "
                                "stack_index={} module={} rel={} "
                                "address=0x{:08X} code16=0x{:04X} "
                                "behavior=OBSERVE_ONLY",
                                kind,stack_index,module,rel,
                                code_addr,*code16);
                        }
                    }
                };

            nboot2_b71_log_frame("pc",pc,0xFFFFFFFFU,pc);
            nboot2_b71_log_frame("lr",lr,0xFFFFFFFFU,lr);

            constexpr std::uint32_t nboot2_b71_stack_words=128;
            for (std::uint32_t i=0;i<nboot2_b71_stack_words;++i) {
                const std::uint32_t slot_addr=
                    sp+i*sizeof(std::uint32_t);
                if (slot_addr<sp) {
                    break;
                }
                const std::uint32_t *slot=
                    eka2l1::ptr<std::uint32_t>(
                        slot_addr).get(caller_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "mapped=0 stopping=1 behavior=OBSERVE_ONLY",
                        i,slot_addr);
                    break;
                }

                const std::uint32_t value=*slot;
                const std::uint32_t candidate=value&~1U;
                codeseg_ptr seg=candidate>=0x10000U
                    ? get_codeseg_from_addr(
                        kern,caller_pr,candidate,false)
                    : nullptr;
                if (seg) {
                    const std::uint32_t base=
                        seg->get_code_run_addr(caller_pr);
                    const std::string module=
                        common::ucs2_to_utf8(seg->get_full_path());
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "value=0x{:08X} code_candidate=1 module={} "
                        "base=0x{:08X} offset=0x{:08X} "
                        "behavior=OBSERVE_ONLY",
                        i,slot_addr,value,module,base,candidate-base);
                    nboot2_b71_log_frame(
                        "stack",value,i,slot_addr);
                } else {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_STACK] index={} slot=0x{:08X} "
                        "value=0x{:08X} code_candidate=0 "
                        "behavior=OBSERVE_ONLY",
                        i,slot_addr,value);
                }
            }

            if ((fp>=0x40U)&&(fp<=0xFFFFFF7FU)) {
                const std::uint32_t begin=fp-0x40U;
                for (std::uint32_t i=0;i<48;++i) {
                    const std::uint32_t addr=
                        begin+i*sizeof(std::uint32_t);
                    const std::uint32_t *word=
                        eka2l1::ptr<std::uint32_t>(
                            addr).get(caller_pr);
                    if (!word) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][CONE14_FP] index={} address=0x{:08X} "
                            "mapped=0 stopping=1 behavior=OBSERVE_ONLY",
                            i,addr);
                        break;
                    }
                    LOG_WARN(KERNEL,
                        "[NBOOT2][CONE14_FP] index={} address=0x{:08X} "
                        "value=0x{:08X} fp_delta={} behavior=OBSERVE_ONLY",
                        i,addr,*word,
                        static_cast<std::int32_t>(addr-fp));
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_SUMMARY] meaning=NoResourceFileForId "
                "stack_words={} fp_words=48 "
                "resource_range_assumption=NONE "
                "panic_behavior=UNCHANGED behavior=OBSERVE_ONLY",
                nboot2_b71_stack_words);
        }

'''
    body=body.replace(anchor,inject+anchor,1)
    sv=sv[:start]+body+sv[end:]

    helper_anchor="    // NATIVEBOOT2-B67 STARTERSSCDUMP1:\n"
    helper=r'''    // NATIVEBOOT2-B71 PHONEUICONE14RES1:
    // Capture the exact localized resource opened immediately before CONE14.
    // Separate READ_MODE|BIN_MODE handle keeps the guest EFsrv cursor intact.
    static void nboot2_b71_dump_phoneui_rsc(io_system *io,
        const std::u16string &path) {
        if (!io) {
            return;
        }
        const std::u16string lower=
            common::lowercase_ucs2_string(path);
        if (lower!=u"z:\resource\apps\phoneui.r01") {
            return;
        }

        symfile probe=io->open_file(path,READ_MODE|BIN_MODE);
        if (!probe || !probe->valid()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_DUMP] phase=open_fail path={} "
                "behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
            return;
        }

        const std::uint64_t raw_size=probe->size();
        constexpr std::size_t max_capture=262144;
        const std::size_t capture_size=
            static_cast<std::size_t>(
                raw_size>max_capture?max_capture:raw_size);
        std::string raw;
        raw.resize(capture_size);
        std::size_t bytes_read=0;
        if (capture_size>0) {
            bytes_read=probe->read_file(
                raw.data(),1,
                static_cast<std::uint32_t>(capture_size));
            if (bytes_read>capture_size) {
                bytes_read=capture_size;
            }
            raw.resize(bytes_read);
        }

        static constexpr char digits[]="0123456789ABCDEF";
        constexpr std::size_t chunk_bytes=512;
        const std::size_t chunks=raw.empty()?1:
            ((raw.size()+chunk_bytes-1)/chunk_bytes);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][PHONEUI_RSC_DUMP] phase=begin path={} "
            "raw_size={} captured={} truncated={} chunks={} "
            "encoding=HEX behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path),raw_size,bytes_read,
            raw_size>max_capture,chunks);

        if (raw.empty()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RSC_DUMP] phase=data path={} "
                "chunk=1/1 offset=0 bytes=0 hex=<EMPTY> "
                "behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
        } else {
            for (std::size_t off=0,index=0;
                 off<raw.size();off+=chunk_bytes,++index) {
                const std::size_t count=
                    std::min(chunk_bytes,raw.size()-off);
                std::string hex;
                hex.resize(count*2);
                for (std::size_t i=0;i<count;++i) {
                    const unsigned char ch=
                        static_cast<unsigned char>(raw[off+i]);
                    hex[i*2]=digits[(ch>>4)&0xF];
                    hex[i*2+1]=digits[ch&0xF];
                }
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RSC_DUMP] phase=data path={} "
                    "chunk={}/{} offset={} bytes={} hex={} "
                    "behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(path),index+1,chunks,
                    off,count,hex);
            }
        }

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][PHONEUI_RSC_DUMP] phase=end path={} "
            "behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path));
    }

'''
    ff=rep1(ff,helper_anchor,helper+helper_anchor,
            "B71 PhoneUI RSC helper")

    hook_anchor='''        nboot2_b66_dump_starter_script(io, *name_res);
        nboot2_b67_dump_starter_ssc(io, *name_res);
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    hook_new='''        nboot2_b66_dump_starter_script(io, *name_res);
        nboot2_b67_dump_starter_ssc(io, *name_res);
        nboot2_b71_dump_phoneui_rsc(io, *name_res);
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    ff=rep1(ff,hook_anchor,hook_new,"B71 PhoneUI RSC open hook")

    final=sv+"\n"+ff
    for need in markers+(
        "[NBOOT2][CONE14_FP]",
        "[NBOOT2][CONE14_SUMMARY]",
        "0x100058B3U",
        '(reason == 14)',
        '(exit_category == "CONE")',
        'u"z:\\resource\\apps\\phoneui.r01"',
        "io->open_file(path,READ_MODE|BIN_MODE)",
        "constexpr std::size_t max_capture=262144",
        "nboot2_b71_dump_phoneui_rsc(io, *name_res);",
        "resource_range_assumption=NONE",
        "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
    ):
        if need not in final:
            fail("post-apply gate missing: "+need)

    # Explicitly reject the previous unverified resource-range guess.
    for forbidden in ("0x4E738000","0x170U","phoneui_resource_count"):
        if forbidden in inject:
            fail("unverified PhoneUI resource range survived: "+forbidden)

    b71=inject+"\n"+helper
    for forbidden in (
        "reason = 0","reason=0","requested=102","ESimUsable",
        "set_int(","set_property","WRITE_MODE","write_file(",
        "ctx.complete(","signal_request("
    ):
        if forbidden in b71:
            fail("behavior-changing token in B71 block: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    svc.write_text(sv,encoding="utf-8")
    fs.write_text(ff,encoding="utf-8")

    print(MARK+": applied")
    print("scope=TELEPHONE_CONE14_DIAGNOSTIC_ONLY")
    print("telephone_uid3=0x100058B3")
    print("cone14=ECoePanicNoResourceFileForId")
    print("resource_range_assumption=NONE")
    print("stack_scan=128_WORDS")
    print("frame_pointer_scan=48_WORDS")
    print("phoneui_r01=READ_ONLY_HEX_CAPTURE")
    print("phoneui_r01_capture_limit=262144")
    print("panic_behavior=UNCHANGED")
    print("starter_state=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("B61_B64_B67_B68_B69_B70=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
