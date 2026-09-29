#!/usr/bin/env python3
"""RED contract for NATIVEBOOT2 B47 AKNSKINTFXSTATE1.

Diagnostic-only boundary tracing after B46 proved native AknSkinSrv startup.
No CenRep value, Wserv result, ECom result, P&S value, or TfxServer behavior
may be synthesized.
"""
from pathlib import Path
import re
import sys

MARK="NATIVEBOOT2-B47-AKNSKINTFXSTATE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b47_aknskintfxstate1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()

    repo=up/"src/emu/services/src/centralrepo/repo.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    init=up/"src/emu/services/src/init.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    msg=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    for p in (repo,svc,init,loader,sa,msg):
        if not p.is_file():
            fail(f"missing source: {p}")

    rp=repo.read_text(encoding="utf-8")
    s=svc.read_text(encoding="utf-8")
    i=init.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    mw=msg.read_text(encoding="utf-8")

    # Canonical RED boundary.
    need(rp,"[NBOOT2][AKNSKIN_TFX_STATE]","B47 CenRep marker")
    need(s,"[NBOOT2][AKNSKIN_TFX_WSERV]","B47 Wserv marker")
    need(s,"[NBOOT2][AKNSKIN_TFX_ECOM]","B47 ECom marker")

    # Exact source-guided target.
    for needle in (
        "0x102818E8",
        "0x00000009",
        "cen_rep_get_int",
        "behavior=OBSERVE_ONLY",
    ):
        need(rp,needle,"B47 CenRep target")

    for needle in (
        'server_name == "!Windowserver"',
        "0x10207114",
        "behavior=OBSERVE_ONLY",
    ):
        need(s,needle,"B47 AknSkin Wserv probe")

    for needle in (
        'server_name == "!ecomserver"',
        "arg.args[0]",
        "arg.args[1]",
        "arg.args[2]",
        "arg.args[3]",
        "behavior=OBSERVE_ONLY",
    ):
        need(s,needle,"B47 ECom IPC probe")

    # Preserve route/provider milestones.
    for needle in (
        "[NBOOT2][AKNSKIN_ROUTE2]",
        "[NBOOT2][AKNSKIN_ROUTE]",
    ):
        need(i,needle,"B46 route preservation")
    for needle in (
        "[NBOOT2][TFX_SESSION]",
        "[NBOOT2][TFX_LEAVE]",
        "[NBOOT2][TFX_PS]",
        "[NBOOT2][ALF_SESSION]",
    ):
        need(s,needle,"B43/B44 preservation")
    need(l,"[NBOOT2][TFX_ECOM_DLL]","B44 TFX DLL preservation")
    need(l,"[NBOOT2][AKNSKIN_NATIVE_PROC]","B45 native process preservation")
    need(s,"[NBOOT2][AKNSKIN_NATIVE_REGISTER]","B45 native register preservation")
    need(sat,"[NBOOT2][SA_HWRM_ABI]","B42 preservation")
    need(l,"[NBOOT2][LOADER_PDD]","B40 preservation")
    need(mw,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 preservation")

    # CenRep semantics must remain real.
    need(rp,"ctx->complete(epoc::error_not_found);","CenRep KErrNotFound path")
    need(rp,"ctx->complete(epoc::error_argument);","CenRep argument/type path")
    need(rp,"ctx->complete(epoc::error_none);","CenRep success path")
    if "b47_force" in rp or "KThemesTransitionEffects = 0" in rp:
        fail("B47 appears to force a CenRep value")

    # Missing TfxServer must remain real KErrNotFound.
    ss=s.find("BRIDGE_FUNC(std::int32_t, session_create")
    se=s.find("BRIDGE_FUNC(std::int32_t, session_create_from_handle",ss)
    if ss<0 or se<0:
        fail("cannot isolate session_create")
    sb=s[ss:se]
    need(sb,"return epoc::error_not_found;","session_create real miss")
    if "create_and_add<service::server>" in sb:
        fail("B47 fabricates a server in session_create")

    # ECom send must still use original dispatch result.
    gs=s.find("static std::int32_t session_send_general")
    ge=s.find("BRIDGE_FUNC(std::int32_t, session_send_sync",gs)
    if gs<0 or ge<0:
        fail("cannot isolate session_send_general")
    gb=s[gs:ge]
    need(gb,"ss->send_receive_sync(ord, arg, status)","sync dispatch")
    need(gb,"ss->send_receive(ord, arg, status)","async dispatch")
    need(gb,"return result;","original dispatch result")
    marker_pos=gb.find("[NBOOT2][AKNSKIN_TFX_ECOM]")
    callback_pos=gb.find("kern->call_ipc_send_callbacks", marker_pos)
    if marker_pos < 0 or callback_pos < 0:
        fail("cannot isolate B47 ECom observe-only block")
    b47_block=gb[marker_pos:callback_pos]
    if re.search(r"\\bord\\s*=(?!=)", b47_block) or re.search(r"arg\\.args\\[[0-3]\\]\\s*=(?!=)", b47_block):
        fail("B47 appears to rewrite ECom request")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("cenrep_write=NONE")
    print("force_tfx_enabled=NONE")
    print("fake_ecom=NONE")
    print("fake_tfxserver=NONE")
    print("B40_B41_B42_B43_B44_B45_B46=PRESERVED")

if __name__=="__main__":
    main()
