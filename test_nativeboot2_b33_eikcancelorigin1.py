#!/usr/bin/env python3
"""Source contract for B33 EIKCANCELORIGIN1.

B32 device evidence localizes the first repeated guest boundary to:
AknFep initialization -> EikAppUiServerThread Leave(-3/KErrCancel)
-> euser write AV at 0x10 -> KERN-EXEC 3.

B33 is diagnostic-only. It must identify which completion path delivers
KErrCancel before the AknFep leave without changing completion, signaling,
leave, SVC, or exception semantics.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B33-EIKCANCELORIGIN1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b33_eikcancelorigin1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    ctx=up/"src/emu/services/src/context.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"

    for p in (svc,ctx,thr,kern,sched,lib):
        if not p.is_file():
            fail(f"missing source file: {p}")

    sv=svc.read_text(encoding="utf-8")
    cx=ctx.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=sched.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")

    # Preserve the device-proven B30/B31 and B32 evidence instrumentation.
    need(lm,"[NBOOT2][LDR_ROOT_RESOLVED]","libmanager.cpp B30 preservation")
    need(sc,"[NBOOT2][SCHED_STALE_READY_DROP]","scheduler.cpp B31 preservation")
    need(lm,"[NBOOT2][EIKFAULT_SVCMISS]","libmanager.cpp B32 preservation")
    need(sv,"[NBOOT2][EIKFAULT_LEAVE]","svc.cpp B32 preservation")
    need(ke,"[NBOOT2][EIKFAULT_AV]","kernel.cpp B32 preservation")

    # B33 cancellation-origin markers.
    for needle in (
        "[NBOOT2][EIKCANCEL_LLE]",
        "msg->function",
        "msg->args.args[0]",
        "msg->own_thr",
        "msg->msg_session",
    ):
        need(sv,needle,"svc.cpp B33 LLE diagnostics")

    for needle in (
        "[NBOOT2][EIKCANCEL_HLE]",
        "msg->function",
        "msg->args.args[0]",
        "msg->own_thr",
        "msg->msg_session",
    ):
        need(cx,needle,"context.cpp B33 HLE diagnostics")

    for needle in (
        "[NBOOT2][EIKCANCEL_NOTIFY]",
        "requester->owning_process()",
        "requester->name()",
        "sts.ptr_address()",
    ):
        need(th,needle,"thread.cpp B33 notify diagnostics")

    # The traces must be keyed only by KErrCancel, not by target process/DLL.
    combined=(sv+"\n"+cx+"\n"+th).lower()
    for forbidden in (
        "eiksrvs",
        "10003a4a",
        "avkonfep.dll",
        "100056de",
    ):
        if forbidden in combined:
            fail(f"target hardcode detected: {forbidden}")

    # Original semantics must remain.
    need(sv,"status->set(val, kern->is_eka1());","svc.cpp message completion")
    need(sv,"msg->own_thr->signal_request();","svc.cpp request signal")
    need(sv,"kern->call_ipc_complete_callbacks(msg, val);","svc.cpp completion callbacks")
    need(sv,"msg->unref();","svc.cpp message release")

    need(cx,"(msg->request_sts.get(msg->own_thr->owning_process()))->set(res, kern->is_eka1());","context.cpp HLE completion")
    need(cx,"msg->own_thr->signal_request();","context.cpp HLE request signal")

    need(th,"sts_real->set(err_code, kern->is_eka1());","thread.cpp notify completion")
    need(th,"requester->signal_request();","thread.cpp notify signal")

    # B33 must not turn observed SVC gaps into fixes.
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94")
    v94_end=sv.find("const eka2l1::hle::func_map svc_register_funcs_v93",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("cannot isolate EPOC94 SVC table")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0x2D," in v94:
        fail("out-of-scope EPOC94 SVC 0x2D implementation detected")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope GetModuleNameFromAddress backport detected")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
