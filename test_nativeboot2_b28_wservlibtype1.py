#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B28 WSERVLIBTYPE1.

B27 device evidence isolated:
EKDATA.DLL load -> EPOC94 SVCMISS 0x63 -> leave ->
EWsPanicFailedToInitialise / WSERV-INTERNAL 13.

B28 must implement only the EPOC 9.4 LibraryType executive ABI at 0x63.
It must preserve B25/B26/B27 behavior and must not opportunistically add
the other observed Wserv SVC gaps (0x48/0x4A/0x50).
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B28-WSERVLIBTYPE1-TEST"

def fail(msg:str)->None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text:str, needle:str, where:str)->None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b28_wservlibtype1.py <upstream-root>")
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

    # Preserve already device-validated / diagnostic milestones.
    need(f,"[NBOOT2][FBS_SHARED_HEAP_READY]","fbs.cpp")
    need(r,"[NBOOT2][IOS_EXIT_UI] phase=library_show_done","RootViewController.mm")
    need(s,"[NBOOT2][WSERV_PANIC_CONTEXT]","svc.cpp")

    # EPOC9 ABI is handle first, TUidType output pointer second.
    need(
        s,
        "BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)",
        "svc.cpp",
    )
    need(s,"kernel::library *lib = kern->get<kernel::library>(h);","library_type")
    need(s,"lib->get_codeseg()->get_uids()","library_type")
    need(s,"type->uid1 = std::get<0>(types_of_codeseg);","library_type")
    need(s,"type->uid2 = std::get<1>(types_of_codeseg);","library_type")
    need(s,"type->uid3 = std::get<2>(types_of_codeseg);","library_type")
    need(s,"[NBOOT2][WSERV_LIBRARY_TYPE]","svc.cpp")

    v94_start=s.find("const eka2l1::hle::func_map svc_register_funcs_v94")
    v94_end=s.find("const eka2l1::hle::func_map svc_register_funcs_v91_diff",v94_start)
    if v94_start<0 or v94_end<0:
        fail("cannot isolate EPOC94 SVC table")
    v94=s[v94_start:v94_end]

    need(v94,"BRIDGE_REGISTER(0x63, library_type),","EPOC94 SVC table")
    need(v94,"BRIDGE_REGISTER(0x64, process_type),","EPOC94 SVC table")

    # B28 is deliberately single-variable: do not batch-fix the other B27 misses.
    for svcnum in ("0x48","0x4A","0x50"):
        if f"BRIDGE_REGISTER({svcnum}," in v94:
            fail(f"B28 must not add unrelated EPOC94 SVC {svcnum}")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
