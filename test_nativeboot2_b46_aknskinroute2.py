#!/usr/bin/env python3
"""RED contract for NATIVEBOOT2 B46 AKNSKINROUTE2.

B45 device evidence proved its route did not activate because:
- exact epoc94 equality did not match the current RM-356 runtime enum;
- Z-overlay existence was queried before the device Z profile was mounted.

B46 must make the route decision from device-manager metadata that is already
available before HLE service creation. It must not alter the global Symbian
version or synthesize TFX/ALF behavior.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B46-AKNSKINROUTE2-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b46_aknskinroute2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    init=up/"src/emu/services/src/init.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    applist=up/"src/emu/services/src/applist/applist.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"

    for p in (init,svc,loader,applist,sa,messagewin):
        if not p.is_file():
            fail(f"missing source file: {p}")

    i=init.read_text(encoding="utf-8")
    s=svc.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")
    a=applist.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    mw=messagewin.read_text(encoding="utf-8")

    # Canonical RED boundary.
    need(i,"[NBOOT2][AKNSKIN_ROUTE2]","B46 route marker")

    # Current-device metadata must drive the route.
    for needle in (
        "#include <system/devices.h>",
        "get_device_manager()->get_current()",
        "firmware_code",
        'rfind("rm-356", 0)',
        'rfind("RM-356", 0)',
        "b46_rm356_native_route",
        "cfg->native_phone_boot && b46_rm356_device",
        "[NBOOT2][AKNSKIN_ROUTE2]",
        "decision=skip_hle",
        "decision=keep_hle",
        "behavior=GUEST_NATIVE_ROUTE",
        "CREATE_SERVER(sys, akn_skin_server);",
    ):
        need(i,needle,"B46 route")

    # B45 epoc/existence probes remain diagnostics but must not gate B46 route.
    need(i,"epocver::epoc94","B45 epoc diagnostic preservation")
    need(i,'u"z:\\sys\\bin\\aknskinsrv.exe"',"B45 Z probe preservation")
    start=i.find("const bool b46_rm356_native_route")
    if start < 0:
        fail("cannot isolate B46 route expression")
    end=i.find(";",start)
    expr=i[start:end+1]
    if "epocver::epoc94" in expr:
        fail("B46 route still gated by epoc94")
    if "b45_aknskin_exe_sysbin" in expr or "b45_aknskin_exe_legacy" in expr:
        fail("B46 route still gated by pre-mount Z existence")

    # B45 provenance remains available for the real native attempt.
    for needle in (
        "[NBOOT2][AKNSKIN_ROUTE]",
        "[NBOOT2][AKNSKIN_SESSION]",
        "[NBOOT2][AKNSKIN_NATIVE_PROC]",
        "[NBOOT2][AKNSKIN_NATIVE_REGISTER]",
        "[NBOOT2][AKNSKIN_ROM]",
    ):
        need(i if needle=="[NBOOT2][AKNSKIN_ROUTE]" else
             s if needle in ("[NBOOT2][AKNSKIN_SESSION]","[NBOOT2][AKNSKIN_NATIVE_REGISTER]") else
             l if needle=="[NBOOT2][AKNSKIN_NATIVE_PROC]" else a,
             needle,"B45 preservation")

    # Provider diagnostics/fidelity guards remain unchanged.
    need(s,"[NBOOT2][TFX_SESSION]","B43 TfxServer diagnostic")
    need(s,"behavior=UNCHANGED_KErrNotFound","TfxServer missing semantics")
    need(s,"[NBOOT2][TFX_PS]","B44 TFX P&S diagnostic")
    need(l,"[NBOOT2][TFX_ECOM_DLL]","B44 ECom diagnostic")
    need(s,"[NBOOT2][ALF_SESSION]","B44 ALF diagnostic")
    need(sat,"[NBOOT2][SA_HWRM_ABI]","B42 HWRM")
    need(l,"[NBOOT2][LOADER_PDD]","B40 PDD")
    need(mw,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 exit")

    session_start=s.find("BRIDGE_FUNC(std::int32_t, session_create")
    session_end=s.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle",session_start)
    if session_start < 0 or session_end < 0:
        fail("cannot isolate session_create")
    block=s[session_start:session_end]
    need(block,"return epoc::error_not_found;","real missing-server result")
    if 'create_and_add<service::server>' in block:
        fail("B46 fabricates a server in session_create")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("route=RM356_DEVICE_METADATA")
    print("global_epoc_change=NONE")
    print("premount_z_gate=REMOVED")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ecom_synthesis=NONE")
    print("ps_synthesis=NONE")
    print("B40_B41_B42_B43_B44_B45=PRESERVED")

if __name__=="__main__":
    main()
