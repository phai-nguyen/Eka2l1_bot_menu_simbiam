#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B39 EIKPOSTLEAVEAV1.

B38 device evidence proves:
- the WindowServer CreateWindow immediately before Leave(-3) succeeds;
- stock AvkonFep directly calls User::Leave(KErrCancel) when a nested state field is null;
- the Leave is caught successfully;
- the fatal boundary is later, at a post-catch euser null write.

B39 is diagnostic-only. It must expose:
1) the saved AvkonFep caller state chain at the KErrCancel boundary;
2) exact code/export/stack context for the later access violation;
while preserving every functional behavior from B34-B38.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B39-EIKPOSTLEAVEAV1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b39_eikpostleaveav1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"
    for p in (svc,kern,window,winuser,screenh):
        if not p.is_file():
            fail(f"missing source file: {p}")

    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    # Preserve proven diagnostics and behavior.
    need(sv,"[NBOOT2][EIKFAULT_LEAVE]","B32 leave trace")
    need(ke,"[NBOOT2][EIKFAULT_AV]","B32 AV trace")
    need(sv,"[NBOOT2][EIKCALLSITE]","B35 callsite")
    need(sv,"[NBOOT2][EIKDIRECT_FRAME]","B38 direct frame")
    need(sv,"[NBOOT2][EIKDIRECT_CODE16]","B38 direct code")
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 deferral")
    need(ws,"[NBOOT2][WSERV_BATCH_CMD]","B38 batch command")
    need(ws,"[NBOOT2][WSERV_BATCH_RESULT]","B38 batch result")
    need(wu,"context.complete(epoc::error_none);","SetNonFading completion")
    need(sh,"std::mutex focus_callback_mutex;","B34 focus mutex")

    # B39 AvkonFep caller-state evidence. The B38 device trace proved that
    # User::Leave's current SP has saved caller r4 at +8 and saved LR at +12.
    need(sv,"[NBOOT2][EIKFEP_STATE]","AvkonFep state trace")
    need(sv,"nboot2_b39_saved_caller_r4_addr = sp + 2 * sizeof(std::uint32_t);",
         "saved caller r4 slot")
    need(sv,"nboot2_b39_saved_caller_lr_addr = sp + 3 * sizeof(std::uint32_t);",
         "saved caller LR slot")
    need(sv,"nboot2_b39_state_l1_slot = nboot2_b39_caller_r4 + 0x10U;",
         "AvkonFep state level 1")
    need(sv,"nboot2_b39_state_l2_slot = nboot2_b39_state_l1 + 0x24U;",
         "AvkonFep state level 2")
    need(sv,"nboot2_b39_saved_r4_mapped","safe caller-r4 mapping")
    need(sv,"nboot2_b39_state_l1_mapped","safe state-l1 mapping")
    need(sv,"nboot2_b39_state_l2_mapped","safe state-l2 mapping")

    # B39 post-catch access-violation evidence.
    need(ke,"[NBOOT2][EIKPOSTLEAVE_AV_FRAME]","post-Leave AV frame resolver")
    need(ke,"[NBOOT2][EIKPOSTLEAVE_AV_CODE16]","post-Leave AV code window")
    need(ke,"[NBOOT2][EIKPOSTLEAVE_AV_STACK]","post-Leave AV stack")
    need(ke,"nboot2_b39_log_av_frame","post-Leave AV resolver helper")
    need(ke,'nboot2_b39_log_av_frame("pc", core->get_pc());',"AV PC resolution")
    need(ke,'nboot2_b39_log_av_frame("lr", core->get_reg(14));',"AV LR resolution")
    need(ke,"nearest_export_ordinal","AV nearest export")
    need(ke,"relative_halfword","AV bounded code window")
    need(ke,"for (std::uint32_t i = 0; i < 24; ++i)","AV bounded stack window")

    # No target-address workaround or guest-behavior change belongs in B39.
    for forbidden in (
        "0x802A01C4",
        "0x802A2DF5",
        "0x7680F104",
        "epoc::error_cancel = epoc::error_none",
        "context.complete(epoc::error_cancel);",
    ):
        if forbidden in sv or forbidden in ke or forbidden in wu:
            fail(f"out-of-scope behavioral/target hardcode detected: {forbidden}")

    # Leave/trap semantics are untouched.
    need(sv,"thr->increase_leave_depth();","LeaveStart behavior")
    need(sv,"return current_local_data(kern)->trap_handler;","LeaveStart return")
    need(sv,"thr->decrease_leave_depth();","LeaveEnd behavior")

    # Access violations must still reach the existing fatal exception path.
    need(ke,"cpu_exception_thread_handle(core);","fatal AV handling")
    need(ke,"return false;","exception-handler return")

    # EPOC94 ABI invariant.
    start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    end=sv.find("\n    };",start)
    if start < 0 or end < 0:
        fail("EPOC94 map missing")
    v94=sv[start:end]
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA unexpectedly mapped")
    need(v94,"BRIDGE_REGISTER(0xAB, message_construct)","EPOC94 0xAB")
    need(v94,"BRIDGE_REGISTER(0xAC, message_kill)","EPOC94 0xAC")
    need(v94,"BRIDGE_REGISTER(0xDF, leave_start)","EPOC94 LeaveStart")
    need(v94,"BRIDGE_REGISTER(0xE0, leave_end)","EPOC94 LeaveEnd")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("stock_fep=PRESERVED")
    print("leave_trap_behavior=UNCHANGED")
    print("wserv_behavior=UNCHANGED")
    print("exception_behavior=UNCHANGED")
    print("B34_B35_B36_B37_B38=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
