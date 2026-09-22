#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B39 EIKPOSTLEAVEAV1 after B38.

B38 device evidence proved that:
- EWsClOpCreateWindow immediately before the failure succeeds;
- stock AvkonFep directly calls User::Leave(KErrCancel) because a nested
  state field is null;
- the Leave is caught successfully;
- the immediate fatal boundary is a later euser null write.

B39 is diagnostic-only. It adds read-only evidence at those two boundaries:
1) recover the saved caller r4/LR from the observed User::Leave frame and
   safely inspect the nested AvkonFep state chain r4 -> +0x10 -> +0x24;
2) resolve the later access-violation PC/LR to codeseg exports, dump bounded
   code windows, and dump a bounded stack window.

No guest state, exception result, FEP behavior, WindowServer behavior,
Leave/TRAP semantics, SVC mapping, scheduler, loader, or host-exit behavior
is changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B39-EIKPOSTLEAVEAV1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b39_eikpostleaveav1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (svc,kern,window,winuser,screenh):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    for needle,text,name in (
        ("[NBOOT2][EIKFAULT_LEAVE]",sv,"B32 leave"),
        ("[NBOOT2][EIKFAULT_AV]",ke,"B32 AV"),
        ("[NBOOT2][EIKCALLSITE]",sv,"B35 callsite"),
        ("[NBOOT2][EIKDIRECT_FRAME]",sv,"B38 direct frame"),
        ("[NBOOT2][EIKDIRECT_CODE16]",sv,"B38 direct code"),
        ("[NBOOT2][WSERV_HANDLE_CARRY]",ws,"B36 handle carry"),
        ("[NBOOT2][WSERV_BATCH_DEFER_BEGIN]",ws,"B37 deferral"),
        ("[NBOOT2][WSERV_BATCH_CMD]",ws,"B38 batch trace"),
        ("[NBOOT2][WSERV_BATCH_RESULT]",ws,"B38 batch result"),
        ("context.complete(epoc::error_none);",wu,"SetNonFading"),
        ("std::mutex focus_callback_mutex;",sh,"B34 focus mutex"),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][EIKFEP_STATE]",
        "[NBOOT2][EIKPOSTLEAVE_AV_FRAME]",
        "[NBOOT2][EIKPOSTLEAVE_AV_CODE16]",
        "[NBOOT2][EIKPOSTLEAVE_AV_STACK]",
    )
    combined=sv+"\n"+ke
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers):
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B39 state: "+", ".join(present))

    leave_anchor='''            nboot2_b38_log_direct_frame("pc", pc);
            nboot2_b38_log_direct_frame("lr", lr);

            for (std::uint32_t i=0; i<32; ++i) {
'''
    leave_new=r'''            nboot2_b38_log_direct_frame("pc", pc);
            nboot2_b38_log_direct_frame("lr", lr);

            // B39 EIKPOSTLEAVEAV1: read-only reconstruction of the direct
            // AvkonFep caller state proven by B38 device stack/code evidence.
            const std::uint32_t nboot2_b39_saved_caller_r4_addr =
                sp + 2 * sizeof(std::uint32_t);
            const std::uint32_t nboot2_b39_saved_caller_lr_addr =
                sp + 3 * sizeof(std::uint32_t);

            bool nboot2_b39_saved_r4_mapped = false;
            bool nboot2_b39_saved_lr_mapped = false;
            bool nboot2_b39_state_l1_mapped = false;
            bool nboot2_b39_state_l2_mapped = false;
            std::uint32_t nboot2_b39_caller_r4 = 0;
            std::uint32_t nboot2_b39_caller_lr = 0;
            std::uint32_t nboot2_b39_state_l1_slot = 0;
            std::uint32_t nboot2_b39_state_l1 = 0;
            std::uint32_t nboot2_b39_state_l2_slot = 0;
            std::uint32_t nboot2_b39_state_l2 = 0;

            if (nboot2_b39_saved_caller_r4_addr >= sp) {
                const std::uint32_t *saved_r4 =
                    eka2l1::ptr<std::uint32_t>(
                        nboot2_b39_saved_caller_r4_addr).get(nboot2_b32_pr);
                if (saved_r4) {
                    nboot2_b39_saved_r4_mapped = true;
                    nboot2_b39_caller_r4 = *saved_r4;
                }
            }

            if (nboot2_b39_saved_caller_lr_addr >= sp) {
                const std::uint32_t *saved_lr =
                    eka2l1::ptr<std::uint32_t>(
                        nboot2_b39_saved_caller_lr_addr).get(nboot2_b32_pr);
                if (saved_lr) {
                    nboot2_b39_saved_lr_mapped = true;
                    nboot2_b39_caller_lr = *saved_lr;
                }
            }

            if (nboot2_b39_saved_r4_mapped
                && (nboot2_b39_caller_r4 <= 0xFFFFFFEFU)) {
                nboot2_b39_state_l1_slot = nboot2_b39_caller_r4 + 0x10U;
                const std::uint32_t *state_l1 =
                    eka2l1::ptr<std::uint32_t>(
                        nboot2_b39_state_l1_slot).get(nboot2_b32_pr);
                if (state_l1) {
                    nboot2_b39_state_l1_mapped = true;
                    nboot2_b39_state_l1 = *state_l1;
                }
            }

            if (nboot2_b39_state_l1_mapped
                && (nboot2_b39_state_l1 != 0)
                && (nboot2_b39_state_l1 <= 0xFFFFFFDBU)) {
                nboot2_b39_state_l2_slot = nboot2_b39_state_l1 + 0x24U;
                const std::uint32_t *state_l2 =
                    eka2l1::ptr<std::uint32_t>(
                        nboot2_b39_state_l2_slot).get(nboot2_b32_pr);
                if (state_l2) {
                    nboot2_b39_state_l2_mapped = true;
                    nboot2_b39_state_l2 = *state_l2;
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][EIKFEP_STATE] sp=0x{:08X} saved_r4_slot=0x{:08X} saved_r4_mapped={} caller_r4=0x{:08X} saved_lr_slot=0x{:08X} saved_lr_mapped={} caller_lr=0x{:08X} state_l1_slot=0x{:08X} state_l1_mapped={} state_l1=0x{:08X} state_l2_slot=0x{:08X} state_l2_mapped={} state_l2=0x{:08X}",
                sp,
                nboot2_b39_saved_caller_r4_addr,
                nboot2_b39_saved_r4_mapped ? 1 : 0,
                nboot2_b39_caller_r4,
                nboot2_b39_saved_caller_lr_addr,
                nboot2_b39_saved_lr_mapped ? 1 : 0,
                nboot2_b39_caller_lr,
                nboot2_b39_state_l1_slot,
                nboot2_b39_state_l1_mapped ? 1 : 0,
                nboot2_b39_state_l1,
                nboot2_b39_state_l2_slot,
                nboot2_b39_state_l2_mapped ? 1 : 0,
                nboot2_b39_state_l2);

            for (std::uint32_t i=0; i<32; ++i) {
'''
    sv=replace_once(sv,leave_anchor,leave_new,"B39 AvkonFep state diagnostics")

    av_anchor='''            LOG_ERROR(KERNEL, "Access violation {} address 0x{:X} in thread {}", (exception_type == arm::exception_type_access_violation_read) ? "reading" : "writing", exception_data, crr_thread()->name());
'''
    av_diag=r'''            // B39 EIKPOSTLEAVEAV1: diagnostic-only symbol/code/stack
            // context for the access violation that follows a caught Leave.
            kernel::process *nboot2_b39_pr = crr_process();
            if (core && nboot2_b39_pr) {
                auto nboot2_b39_find_codeseg =
                    [&](const std::uint32_t candidate) -> codeseg_ptr {
                    for (const auto &seg_obj : get_codeseg_list()) {
                        codeseg_ptr seg =
                            reinterpret_cast<codeseg_ptr>(seg_obj.get());
                        if (!seg) {
                            continue;
                        }

                        const std::uint32_t base =
                            seg->get_code_run_addr(nboot2_b39_pr);
                        const std::uint64_t end =
                            static_cast<std::uint64_t>(base)
                            + static_cast<std::uint64_t>(seg->get_text_size());
                        if ((base <= candidate)
                            && (static_cast<std::uint64_t>(candidate) <= end)) {
                            return seg;
                        }
                    }

                    return nullptr;
                };

                auto nboot2_b39_log_av_frame =
                    [&](const char *kind, const std::uint32_t raw) {
                    const std::uint32_t candidate = raw & ~1U;
                    codeseg_ptr seg = nboot2_b39_find_codeseg(candidate);
                    if (!seg) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKPOSTLEAVE_AV_FRAME] kind={} raw=0x{:08X} module=<unresolved>",
                            kind, raw);
                        return;
                    }

                    const std::uint32_t base =
                        seg->get_code_run_addr(nboot2_b39_pr);
                    const auto exports =
                        seg->get_export_table(nboot2_b39_pr);
                    std::uint32_t nearest_export_ordinal = 0;
                    std::uint32_t nearest_export_address = 0;
                    std::uint32_t nearest_export_delta = 0xFFFFFFFFU;
                    const std::uint64_t code_end =
                        static_cast<std::uint64_t>(base)
                        + static_cast<std::uint64_t>(seg->get_code_size());

                    for (std::size_t export_index = 0;
                         export_index < exports.size(); ++export_index) {
                        const std::uint32_t export_raw =
                            exports[export_index];
                        const std::uint32_t export_address =
                            export_raw & ~1U;
                        if ((export_address < base)
                            || (static_cast<std::uint64_t>(export_address)
                                >= code_end)
                            || (export_address > candidate)) {
                            continue;
                        }

                        const std::uint32_t export_delta =
                            candidate - export_address;
                        if (export_delta < nearest_export_delta) {
                            nearest_export_delta = export_delta;
                            nearest_export_address = export_raw;
                            nearest_export_ordinal =
                                static_cast<std::uint32_t>(
                                    export_index + 1);
                        }
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][EIKPOSTLEAVE_AV_FRAME] kind={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X} thumb={} nearest_export_ordinal={} nearest_export=0x{:08X} nearest_export_delta=0x{:08X}",
                        kind, raw,
                        common::ucs2_to_utf8(seg->get_full_path()),
                        base, candidate - base,
                        (raw & 1U) ? 1 : 0,
                        nearest_export_ordinal,
                        nearest_export_address,
                        nearest_export_delta);

                    for (std::int32_t relative_halfword = -8;
                         relative_halfword <= 4; ++relative_halfword) {
                        const std::int64_t signed_code_address =
                            static_cast<std::int64_t>(candidate)
                            + static_cast<std::int64_t>(
                                relative_halfword) * 2;
                        if ((signed_code_address < 0)
                            || (signed_code_address > 0xFFFFFFFFLL)) {
                            continue;
                        }

                        const std::uint32_t code_address =
                            static_cast<std::uint32_t>(
                                signed_code_address);
                        const std::uint16_t *code16 =
                            eka2l1::ptr<std::uint16_t>(
                                code_address).get(nboot2_b39_pr);
                        if (!code16) {
                            LOG_WARN(KERNEL,
                                "[NBOOT2][EIKPOSTLEAVE_AV_CODE16] kind={} relative_halfword={} address=0x{:08X} mapped=0",
                                kind, relative_halfword, code_address);
                            continue;
                        }

                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKPOSTLEAVE_AV_CODE16] kind={} relative_halfword={} address=0x{:08X} code16=0x{:04X}",
                            kind, relative_halfword,
                            code_address, *code16);
                    }
                };

                nboot2_b39_log_av_frame("pc", core->get_pc());
                nboot2_b39_log_av_frame("lr", core->get_reg(14));

                const std::uint32_t nboot2_b39_sp = core->get_reg(13);
                for (std::uint32_t i = 0; i < 24; ++i) {
                    const std::uint32_t slot_addr =
                        nboot2_b39_sp + i * sizeof(std::uint32_t);
                    if (slot_addr < nboot2_b39_sp) {
                        break;
                    }

                    const std::uint32_t *slot =
                        eka2l1::ptr<std::uint32_t>(
                            slot_addr).get(nboot2_b39_pr);
                    if (!slot) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKPOSTLEAVE_AV_STACK] index={} slot=0x{:08X} mapped=0 stopping=1",
                            i, slot_addr);
                        break;
                    }

                    const std::uint32_t value = *slot;
                    const std::uint32_t candidate = value & ~1U;
                    codeseg_ptr seg = candidate >= 0x10000U
                        ? nboot2_b39_find_codeseg(candidate)
                        : nullptr;
                    if (seg) {
                        const std::uint32_t base =
                            seg->get_code_run_addr(nboot2_b39_pr);
                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKPOSTLEAVE_AV_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                            i, slot_addr, value,
                            common::ucs2_to_utf8(
                                seg->get_full_path()),
                            base, candidate - base);
                    } else {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][EIKPOSTLEAVE_AV_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                            i, slot_addr, value);
                    }
                }
            }

''' + av_anchor
    ke=replace_once(ke,av_anchor,av_diag,"B39 post-Leave AV diagnostics")

    for forbidden in (
        "0x802A01C4",
        "0x802A2DF5",
        "0x7680F104",
        "epoc::error_cancel = epoc::error_none",
        "context.complete(epoc::error_cancel);",
    ):
        if forbidden in sv or forbidden in ke or forbidden in wu:
            fail(f"out-of-scope target/behavior hardcode detected: {forbidden}")

    for needle in (
        "thr->increase_leave_depth();",
        "return current_local_data(kern)->trap_handler;",
        "thr->decrease_leave_depth();",
    ):
        if needle not in sv:
            fail(f"Leave/TRAP semantics lost: {needle}")

    if "cpu_exception_thread_handle(core);" not in ke:
        fail("fatal exception handling lost")
    if "context.complete(epoc::error_none);" not in wu:
        fail("SetNonFading KErrNone behavior lost")
    if "std::recursive_mutex" in sh:
        fail("B34 mutex regression")

    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    v94_end=sv.find("\n    };",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("EPOC94 map missing")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA unexpectedly mapped")
    for needle in (
        "BRIDGE_REGISTER(0xAB, message_construct)",
        "BRIDGE_REGISTER(0xAC, message_kill)",
        "BRIDGE_REGISTER(0xDF, leave_start)",
        "BRIDGE_REGISTER(0xE0, leave_end)",
    ):
        if needle not in v94:
            fail(f"EPOC94 invariant missing: {needle}")

    svc.write_text(sv,encoding="utf-8")
    kern.write_text(ke,encoding="utf-8")

    final=sv+"\n"+ke
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("stock_fep=PRESERVED")
    print("leave_trap_behavior=UNCHANGED")
    print("wserv_behavior=UNCHANGED")
    print("exception_behavior=UNCHANGED")
    print("B34_B35_B36_B37_B38=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
