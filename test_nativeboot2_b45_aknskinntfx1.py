#!/usr/bin/env python3
"""RED contract for NATIVEBOOT2 B45 AKNSKINNTFX1.

B45 is a narrow native-route experiment for Nokia 5800 RM-356 / EPOC9.4.

Primary-source contract:
- RAknsSrvSession::Connect() calls CreateSession("!AknSkinServer").
- On KErrNotFound / KErrServerTerminated it calls StartServer().
- StartServer() launches AknSkinSrv.exe and waits on Rendezvous.
- Native CAknsSrv::PrepareMergedSkinContentUnprotectedL() calls
  StartTransitionSrvL().
- LoadTfxSrvPluginL() asks ECom for 0x10282DBD and 0x10282DBC.

B45 therefore skips only the pre-created HLE AknSkinServer for
native_phone_boot + EPOC9.4 so the guest client gets the real missing-server
condition and can launch the ROM server itself. All other modes/versions retain
the HLE service.

No TfxServer is fabricated and no ECom/P&S/IPC result is synthesized.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B45-AKNSKINNTFX1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b45_aknskinntfx1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    init=up/"src/emu/services/src/init.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    applist=up/"src/emu/services/src/applist/applist.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    window=up/"src/emu/services/src/window/window.cpp"

    for p in (init,svc,loader,applist,sa,messagewin,window):
        if not p.is_file():
            fail(f"missing source file: {p}")

    i=init.read_text(encoding="utf-8")
    s=svc.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")
    a=applist.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    mw=messagewin.read_text(encoding="utf-8")
    w=window.read_text(encoding="utf-8")

    # Canonical RED boundary.
    need(i,"[NBOOT2][AKNSKIN_ROUTE]","B45 init marker")

    # Route guard must be exact and HLE retained elsewhere.
    for needle in (
        "cfg->native_phone_boot",
        "epocver::epoc94",
        "[NBOOT2][AKNSKIN_ROUTE]",
        "phase=hle_skip",
        "phase=hle_keep",
        "CREATE_SERVER(sys, akn_skin_server);",
        "behavior=GUEST_NATIVE_ROUTE",
    ):
        need(i,needle,"B45 init route")

    # Session provenance for !AknSkinServer.
    for needle in (
        "[NBOOT2][AKNSKIN_SESSION]",
        '"!AknSkinServer"',
        "phase=request",
        "phase=missing",
        "phase=found",
        "server_hle={}",
        "behavior=OBSERVE_ONLY",
    ):
        need(s,needle,"B45 skin session diagnostics")

    # Native process launch provenance.
    for needle in (
        "[NBOOT2][AKNSKIN_NATIVE_PROC]",
        '"aknskinsrv.exe"',
        "phase=request",
        "phase=result",
        "uid3=0x{:08X}",
        "behavior=OBSERVE_ONLY",
    ):
        need(l,needle,"B45 native process diagnostics")

    # Native server registration provenance.
    need(s,"[NBOOT2][AKNSKIN_NATIVE_REGISTER]","B45 native register marker")

    # ROM inventory must include both EXE and implementation DLL.
    for needle in (
        "[NBOOT2][AKNSKIN_ROM]",
        'u"z:\\sys\\bin\\aknskinsrv.exe"',
        'u"z:\\sys\\bin\\aknskinsrv.dll"',
        "expected_exe_uid3=0x10207114",
        "expected_dll_uid3=0x10005A35",
    ):
        need(a,needle,"B45 ROM inventory")

    # B44 provider graph remains available in same IPA.
    for needle in (
        "[NBOOT2][ALF_SESSION]",
        "[NBOOT2][TFX_PS]",
        "[NBOOT2][TFX_ECOM_DLL]",
        "[NBOOT2][ALF_APPARC_GETINFO]",
        "[NBOOT2][TFX_ECOM_RSC]",
        "[NBOOT2][TFX_MANIFEST]",
    ):
        if needle in ("[NBOOT2][ALF_SESSION]","[NBOOT2][TFX_PS]"):
            need(s,needle,"B44 kernel preservation")
        elif needle=="[NBOOT2][TFX_ECOM_DLL]":
            need(l,needle,"B44 loader preservation")
        elif needle=="[NBOOT2][ALF_APPARC_GETINFO]":
            need(a,needle,"B44 AppArc preservation")

    # Older invariants.
    need(s,"[NBOOT2][TFX_SESSION]","B43 TfxServer diagnostics")
    need(s,"behavior=UNCHANGED_KErrNotFound","B43 missing semantics")
    need(sat,"[NBOOT2][SA_HWRM_ABI]","B42 HWRM diagnostic")
    need(l,"[NBOOT2][LOADER_PDD]","B40 Loader PDD")
    need(mw,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 exit guard")
    need(w,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(w,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral")

    # Do not fabricate TfxServer or complete it successfully.
    start=s.find("BRIDGE_FUNC(std::int32_t, session_create")
    end=s.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle",start)
    if start < 0 or end < 0:
        fail("cannot isolate session_create")
    block=s[start:end]
    need(block,"return epoc::error_not_found;","real missing-server result")
    if 'server_name == "TfxServer"' in block and 'return epoc::error_none;' in block:
        fail("B45 changes TfxServer missing semantics")
    if 'create_and_add<service::server>' in block:
        fail("B45 fabricates a server in session_create")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=EPOC94_NATIVE_AKNSKIN_ROUTE_EXPERIMENT")
    print("hle_scope=NATIVE_PHONE_BOOT_EPOC94_ONLY")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ecom_synthesis=NONE")
    print("ps_synthesis=NONE")
    print("B36_B37_B40_B41_B42_B43_B44=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
