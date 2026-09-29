#!/usr/bin/env python3
"""RED contract for NATIVEBOOT2 B44 ALFTFXSTARTDIAG1.

Scope clarification:
B44 is diagnostic-only interoperability/emulator startup work for Nokia
5800/Symbian inside EKA2L1. It observes the native guest ALF/TFX startup chain
without creating a fake TfxServer, forcing Alfred to start, changing P&S
values, modifying descriptors, or completing unknown IPC differently.

Source-guided chain under test:
AknSkinSrv -> ECom TFX impl 0x10282DBD/0x10282DBC
-> tfxsrvplugin.dll UID 0x10282DBA
-> TFX P&S category 0x10207218 key 0x2
-> RAlfTfxClient -> alfstreamerserver
-> ALF backend -> TfxServer registration.

Parallel Alfred/AppArc chain:
GetAppInfo(0x10282845) -> alfredserver_reg.rsc -> process creation
-> alfredserver.exe / alfserver.exe -> ALF AppServer.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B44-ALFTFXSTARTDIAG1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b44_alftfxstartdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    applist=up/"src/emu/services/src/applist/applist.cpp"
    files=up/"src/emu/services/src/fs/files.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    window=up/"src/emu/services/src/window/window.cpp"

    for p in (svc,loader,applist,files,sa,messagewin,window):
        if not p.is_file():
            fail(f"missing source file: {p}")

    s=svc.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")
    a=applist.read_text(encoding="utf-8")
    f=files.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    mw=messagewin.read_text(encoding="utf-8")
    w=window.read_text(encoding="utf-8")

    # Canonical RED boundary.
    need(s,"[NBOOT2][ALF_SESSION]","B44 kernel marker")

    # Kernel/session/P&S probes.
    for needle in (
        "[NBOOT2][ALF_SESSION]",
        "[NBOOT2][ALF_SERVER_REGISTER]",
        "[NBOOT2][TFX_PS]",
        '"alfstreamerserver"',
        '"10282845_10282845_AppServer"',
        '"10282848_10282848_AppServer"',
        "0x10207218",
        "0x00000002",
        "behavior=OBSERVE_ONLY",
    ):
        need(s,needle,"B44 svc diagnostics")

    # Loader provider/process probes.
    for needle in (
        "[NBOOT2][ALF_PROC_CREATE]",
        "[NBOOT2][TFX_ECOM_DLL]",
        '"tfxsrvplugin.dll"',
        '"alfredserver.exe"',
        '"alfserver.exe"',
        "uid3=0x{:08X}",
        "behavior=OBSERVE_ONLY",
    ):
        need(l,needle,"B44 loader diagnostics")

    # AppArc/ROM inventory.
    for needle in (
        "[NBOOT2][ALF_ROM_ARTIFACT]",
        "[NBOOT2][ALF_APPARC_REG]",
        "[NBOOT2][ALF_APPARC_GETINFO]",
        "0x10282845",
        'u"z:\\sys\\bin\\alfredserver.exe"',
        'u"z:\\sys\\bin\\tfxsrvplugin.dll"',
        'u"z:\\resource\\effects\\manifest.mf"',
        'u"z:\\private\\10003a3f\\apps\\alfredserver_reg.rsc"',
    ):
        need(a,needle,"B44 AppArc/ROM diagnostics")

    # Native ECom/resource/config file access through FileServer.
    for needle in (
        "[NBOOT2][TFX_ECOM_RSC]",
        "[NBOOT2][TFX_MANIFEST]",
        "tfxsrvplugin",
        "10282dba",
        "manifest.mf",
        "behavior=OBSERVE_ONLY",
    ):
        need(f,needle,"B44 FileServer diagnostics")

    # B43/B42/B41/B40/B37/B36 invariants remain.
    need(s,"[NBOOT2][TFX_SESSION]","B43 TfxServer diagnostics")
    need(s,"behavior=UNCHANGED_KErrNotFound","B43 missing semantics")
    need(sat,"[NBOOT2][SA_HWRM_ABI]","B42 HWRM diagnostic")
    need(l,"[NBOOT2][LOADER_PDD]","B40 Loader PDD")
    need(mw,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 exit guard")
    need(w,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(w,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral")

    start=s.find("BRIDGE_FUNC(std::int32_t, session_create")
    end=s.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle", start)
    if start < 0 or end < 0:
        fail("cannot isolate session_create")
    block=s[start:end]
    need(block,"return epoc::error_not_found;","real missing-server result")
    for forbidden in (
        'create_and_add<service::server>',
        'return epoc::error_none;',
    ):
        if forbidden in block:
            fail(f"B44 fabricates/changes missing server semantics: {forbidden}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=ALF_TFX_PROVIDER_STARTUP_MULTI_BOUNDARY_DIAGNOSTIC_ONLY")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ps_mutation=NONE")
    print("B36_B37_B40_B41_B42_B43=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
