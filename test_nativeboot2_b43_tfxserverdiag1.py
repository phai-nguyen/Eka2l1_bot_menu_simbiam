#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B43 TFXSERVERDIAG1.

B42 device evidence:
- TfxServer CreateSession misses in eiksrvs and twice in akncapserver;
- each miss is followed by Leave(-1);
- the second akncapserver failure is followed by SYSSTART shutdown handling.

B43 is diagnostic-only. It must identify the exact TfxServer CreateSession
caller/callsite, correlate the following Leave(-1) on the same guest thread,
and observe Tfx/Alfred process/library/server resolution without creating a
fake server or changing KErrNotFound semantics.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B43-TFXSERVERDIAG1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b43_tfxserverdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"

    for p in (svc,loader,sa,messagewin):
        if not p.is_file():
            fail(f"missing source file: {p}")

    s=svc.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    mwt=messagewin.read_text(encoding="utf-8")

    # Canonical RED: B42 must not already contain the B43 diagnostic marker.
    need(s,"[NBOOT2][TFX_SESSION]","B43 CreateSession runtime marker")

    for needle in (
        "[NBOOT2][TFX_SESSION_FRAME]",
        "[NBOOT2][TFX_SESSION_STACK]",
        "[NBOOT2][TFX_LEAVE]",
        "[NBOOT2][TFX_SERVER_REGISTER]",
        'server_name == "TfxServer"',
        "behavior=UNCHANGED_KErrNotFound",
        "correlated=1",
        "b43_tfx_miss.process == menuui6_pr",
        "b43_tfx_miss.thread == thr",
    ):
        need(s,needle,"B43 svc diagnostics")

    for needle in (
        "[NBOOT2][TFX_RESOLVE]",
        "kind=process phase=request",
        "kind=process phase=result",
        "kind=library phase=request",
        "kind=library phase=result",
        "behavior=OBSERVE_ONLY",
    ):
        need(l,needle,"B43 loader diagnostics")

    need(sat,"[NBOOT2][SA_HWRM_ABI]","B42 HWRM diagnostic")
    need(loader.read_text(encoding="utf-8"),"[NBOOT2][LOADER_PDD]","B40 Loader PDD")
    need(mwt,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 MessageWin exit guard")

    start=s.find("BRIDGE_FUNC(std::int32_t, session_create")
    end=s.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle",start)
    if start < 0 or end < 0:
        fail("cannot isolate session_create")
    block=s[start:end]

    # B43 may observe but must not fabricate TfxServer or success.
    for forbidden in (
        "create_and_add<service::server>",
        "ctx.complete(",
        "return epoc::error_none;",
    ):
        if forbidden in block:
            fail(f"B43 session_create changes guest semantics: {forbidden}")

    need(block,"return epoc::error_not_found;","original KErrNotFound behavior")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=TFXSERVER_CREATESESSION_AND_RESOLUTION_DIAGNOSTIC_ONLY")
    print("fake_server=NONE")
    print("missing_result=KErrNotFound_PRESERVED")
    print("B40_B41_B42=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
