#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B40 LOADERPDD1.

B39 device evidence identified the first causal startup break:
CEikServAppUiBase::InitializeL -> User::LoadPhysicalDevice("EUART1")
-> !Loader opcode 4 -> unimplemented synchronous IPC -> canonical eiksrvs stalls.

B40 is intentionally narrow: implement only Loader::LoadPhysicalDevice using
upstream EKA2L1 commit 0987745cc0bde96511fce2a4bfefcfd8fbced3dc,
return KErrNone for a valid HLE-backed PDD request, and expose runtime evidence
of entry/completion. Generic unknown-IPC behavior and all B34-B39 behavior
remain unchanged.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B40-LOADERPDD1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b40_loaderpdd1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/loader/loader.h"
    src=up/"src/emu/services/src/loader/loader.cpp"
    op=up/"src/emu/services/include/services/loader/op.h"
    context=up/"src/emu/services/src/context.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    screenh=up/"src/emu/services/include/services/window/screen.h"

    for p in (hdr,src,op,context,svc,kern,window,screenh):
        if not p.is_file():
            fail(f"missing source file: {p}")

    h=hdr.read_text(encoding="utf-8")
    s=src.read_text(encoding="utf-8")
    o=op.read_text(encoding="utf-8")
    ct=context.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    sh=screenh.read_text(encoding="utf-8")

    need(s,"[NBOOT2][LOADER_PDD]","B40 Loader PDD runtime marker")

    # Exact narrow upstream behavior.
    need(o,"ELoadPhysicalDevice = 4","Loader opcode 4")
    need(h,"void load_physical_device(service::ipc_context &context);",
         "loader declaration")
    need(s,"void loader_server::load_physical_device(service::ipc_context &context)",
         "Loader::LoadPhysicalDevice handler")
    need(s,"context.get_argument_value<utf16_str>(1)","PDD descriptor read")
    need(s,"context.complete(epoc::error_argument);","bad PDD descriptor completion")
    need(s,'REGISTER_IPC(loader_server, load_physical_device, ELoadPhysicalDevice, "Loader::LoadPhysicalDevice");',
         "opcode-4 registration")
    need(s,"context.complete(epoc::error_none);","HLE-backed PDD success")
    need(s,"phase=enter","B40 entry evidence")
    need(s,"phase=complete","B40 completion evidence")

    # Do not absorb upstream 9f28c76f generic unknown-IPC completion into B40.
    unknown_old='LOG_WARN(SERVICE_TRACK, "Unimplemented IPC call: 0x{:x} for server: {}", func, obj_name);'
    need(ct, unknown_old, "legacy unknown-IPC dispatcher")
    if 'LOG_ERROR(SERVICE_TRACK, "Unimplemented IPC call: 0x{:x} for server: {}", func, obj_name);' in ct:
        fail("generic unknown-IPC dispatcher changed in B40")
    pos=ct.find(unknown_old)
    if pos < 0 or "context.complete(epoc::error_not_supported);" in ct[pos:pos+800]:
        fail("generic unknown-IPC completion bundled into B40")

    # Preserve previous validated/diagnostic milestones.
    need(s,"[NBOOT2][LDR_LIB_REQUEST]","B29 loader diagnostics")
    need(sv,"[NBOOT2][EIKFEP_STATE]","B39 FEP diagnostics")
    need(ke,"[NBOOT2][EIKPOSTLEAVE_AV_FRAME]","B39 AV diagnostics")
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 signal deferral")
    need(ws,"[NBOOT2][WSERV_BATCH_CMD]","B38 batch diagnostics")
    need(sh,"std::mutex focus_callback_mutex;","B34 focus mutex")

    # Leave/TRAP ABI remains untouched.
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
    print("scope=LOADER_PDD_OPCODE4_ONLY")
    print("upstream_reference=0987745cc0bde96511fce2a4bfefcfd8fbced3dc")
    print("ELoadPhysicalDevice=4")
    print("valid_pdd_completion=KErrNone")
    print("generic_unknown_ipc=UNCHANGED")
    print("B34_B35_B36_B37_B38_B39=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
