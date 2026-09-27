#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B27 WSERVPANIC13TRACE1.

B27 is diagnostic-only. It must:
- preserve B25 FBSSHAREDHEAP1 and B26 IOSLIBRARYEXIT1;
- add focused deep tracing for ewsrv/Wserv self-kill/panic paths;
- record PC/LR/SP/CPSR/registers and stack candidates when category is
  WSERV-INTERNAL or Domino, especially reason 13;
- preserve native panic and SYSSTART state behavior; PhoneUI failures remain diagnostic-only.
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

    # PhoneUI CONE 14 remains observable, but must keep native panic semantics.
    need(s,"thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);","svc.cpp")
    for n in (
        "const bool nboot2_b71_phoneui_cone14",
        "nboot2_b71_target_uid3 == 0x100058B3U",
        "reason == 14",
        'exit_category == \"CONE\"',
    ):
        need(s,n,"svc.cpp")
    for n in (
        "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]",
        "[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]",
        "nboot2_b89_effective",
        "nboot2_b89_phoneui_bypass_seen",
    ):
        if n in s:
            fail(f"forbidden startup bypass remains in svc.cpp: {n}")

    gate_start=s.index("const bool nboot2_b71_phoneui_cone14")
    gate_end=s.index(";",gate_start)+1
    gate=s[gate_start:gate_end]
    for n in (
        "nboot2_b71_target_uid3 == 0x100058B3U",
        "reason == 14",
        'exit_category == "CONE"',
    ):
        need(gate,n,"B71 exact PhoneUI panic predicate")

    setter_start=s.index("BRIDGE_FUNC(std::int32_t, property_find_set_int")
    setter_end=s.index("\n    }",setter_start)
    setter=s[setter_start:setter_end]
    need(setter,"prop->set_int(value)","native property setter")
    for n in ("prop->set_int(nboot2_b89_effective)","[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]"):
        if n in setter:
            fail(f"forbidden SYSSTART state override remains: {n}")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
