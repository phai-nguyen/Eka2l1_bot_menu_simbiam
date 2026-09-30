#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B27 WSERVPANIC13TRACE1.

B27 is diagnostic-only. It must:
- preserve B25 FBSSHAREDHEAP1 and B26 IOSLIBRARYEXIT1;
- add focused deep tracing for ewsrv/Wserv self-kill/panic paths;
- record PC/LR/SP/CPSR/registers and stack candidates when category is
  WSERV-INTERNAL or Domino, especially reason 13;
- preserve panic behavior except for the single, later-authorized B88 Telephone CONE 14 startup-continuation exception.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B27-WSERVPANIC13TRACE1-TEST"

def fail(m:str)->None:
    raise SystemExit(f"{MARK}: FAIL: {m}")

def need(t:str,n:str,w:str)->None:
    if n not in t:
        fail(f"missing in {w}: {n}")

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b27_wservpanic13trace1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    fbs=up/"src/emu/services/src/fbs/fbs.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"
    for p in (svc,fbs,root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")
    s=svc.read_text(encoding="utf-8")
    f=fbs.read_text(encoding="utf-8")
    r=root.read_text(encoding="utf-8")

    need(f,"[NBOOT2][FBS_SHARED_HEAP_HANDOFF]","fbs.cpp")
    need(f,"[NBOOT2][FBS_SHARED_HEAP_READY]","fbs.cpp")
    need(r,"[NBOOT2][IOS_EXIT_UI] phase=library_show_done","RootViewController.mm")

    for n in (
        "[NBOOT2][WSERV_TRACE]",
        "[NBOOT2][WSERV_FRAME]",
        "[NBOOT2][WSERV_STACK]",
        "[NBOOT2][WSERV_PANIC_CONTEXT]",
        "WSERV-INTERNAL",
        "Domino",
    ):
        need(s,n,"svc.cpp")

    # Preserve ordinary panic semantics. B88 is the only authorized exception:
    # Telephone UID3 0x100058B3 / CONE / reason 14 exits cleanly for startup.
    need(s,"thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);","svc.cpp")
    for n in (
        "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]",
        "const bool nboot2_b71_phoneui_cone14",
        "nboot2_b71_target_uid3 == 0x100058B3U",
        "reason == 14",
        'exit_category == \"CONE\"',
    ):
        need(s,n,"svc.cpp")
    # The thread_kill source has other kill dispatches; verify B88 by its own
    # marker and guarded predicate rather than a file-global call ordering.
    for n in (
        "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]",
        "etype = kernel::entity_exit_type::terminate;",
        'exit_category = "None";',
        "reason = 0;",
    ):
        need(s,n,"B88 exception")

    gate_start=s.index("const bool nboot2_b71_phoneui_cone14")
    gate_end=s.index(";",gate_start)+1
    gate=s[gate_start:gate_end]
    for n in (
        "nboot2_b71_target_uid3 == 0x100058B3U",
        "reason == 14",
        'exit_category == "CONE"',
    ):
        need(gate,n,"B71 exact PhoneUI panic predicate")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
