#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B28 WSERVLIBTYPE1 on top of B27.

B27 device evidence:
EKDATA.DLL load -> EPOC94 SVCMISS 0x63 -> leave ->
EWsPanicFailedToInitialise / WSERV-INTERNAL 13.

B28 adds only the EPOC 9.4 Exec::LibraryType ABI at SVC 0x63.
No Wserv panic suppression and no batch implementation of 0x48/0x4A/0x50.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B28-WSERVLIBTYPE1"

def fail(msg:str)->None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text:str, old:str, new:str, label:str)->str:
    count=text.count(old)
    if count!=1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b28_wservlibtype1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    fbs=up/"src/emu/services/src/fbs/fbs.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"
    for p in (svc,fbs,root):
        if not p.is_file():
            fail(f"missing B27 baseline file: {p}")

    s=svc.read_text(encoding="utf-8")
    f=fbs.read_text(encoding="utf-8")
    r=root.read_text(encoding="utf-8")

    if "[NBOOT2][FBS_SHARED_HEAP_READY]" not in f:
        fail("B25 checkpoint missing")
    if "[NBOOT2][IOS_EXIT_UI] phase=library_show_done" not in r:
        fail("B26 checkpoint missing")
    if "[NBOOT2][WSERV_PANIC_CONTEXT]" not in s:
        fail("B27 checkpoint missing")

    if "[NBOOT2][WSERV_LIBRARY_TYPE]" in s:
        print("NATIVEBOOT2-B28 WSERVLIBTYPE1 already present")
        return

    eka1_func='''    BRIDGE_FUNC(void, library_type_eka1, epoc::uid_type *type, kernel::handle h) {
        kernel::library *lib = kern->get<kernel::library>(h);

        if (!lib) {
            return;
        }

        const auto types_of_codeseg = lib->get_codeseg()->get_uids();

        type->uid1 = std::get<0>(types_of_codeseg);
        type->uid2 = std::get<1>(types_of_codeseg);
        type->uid3 = std::get<2>(types_of_codeseg);
    }
'''

    eka2_func=eka1_func+'''
    // NATIVEBOOT2-B28 WSERVLIBTYPE1:
    // Symbian EKA2 Exec::LibraryType ABI is (handle, TUidType&).
    // B27 Nokia 5800 evidence shows ewsrv loading EKDATA.DLL and then issuing
    // EPOC94 SVC 0x63 immediately before the startup leave.
    BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr) {
        kernel::library *lib = kern->get<kernel::library>(h);

        if (!lib) {
            LOG_WARN(KERNEL,
                "[NBOOT2][WSERV_LIBRARY_TYPE] handle=0x{:X} valid=0",
                h);
            return;
        }

        kernel::process *crr_pr = kern->crr_process();
        epoc::uid_type *type = type_ptr.get(crr_pr);
        if (!type) {
            LOG_WARN(KERNEL,
                "[NBOOT2][WSERV_LIBRARY_TYPE] handle=0x{:X} valid=1 output_mapped=0",
                h);
            return;
        }

        const auto types_of_codeseg = lib->get_codeseg()->get_uids();

        type->uid1 = std::get<0>(types_of_codeseg);
        type->uid2 = std::get<1>(types_of_codeseg);
        type->uid3 = std::get<2>(types_of_codeseg);

        LOG_WARN(KERNEL,
            "[NBOOT2][WSERV_LIBRARY_TYPE] handle=0x{:X} valid=1 output_mapped=1 uid1=0x{:08X} uid2=0x{:08X} uid3=0x{:08X}",
            h, type->uid1, type->uid2, type->uid3);
    }
'''
    s=replace_once(s,eka1_func,eka2_func,"add EKA2 LibraryType bridge")

    old_reg='''        BRIDGE_REGISTER(0x5F, process_get_memory_info),
        BRIDGE_REGISTER(0x64, process_type),
'''
    new_reg='''        BRIDGE_REGISTER(0x5F, process_get_memory_info),
        BRIDGE_REGISTER(0x63, library_type),
        BRIDGE_REGISTER(0x64, process_type),
'''
    # Restrict replacement to the EPOC94 table. The exact anchor is unique in
    # the current B27 source; fail rather than silently touching another ABI.
    s=replace_once(s,old_reg,new_reg,"register EPOC94 SVC 0x63 LibraryType")

    svc.write_text(s,encoding="utf-8")

    check=svc.read_text(encoding="utf-8")
    for needle in (
        "BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)",
        "[NBOOT2][WSERV_LIBRARY_TYPE]",
        "BRIDGE_REGISTER(0x63, library_type),",
        "BRIDGE_REGISTER(0x64, process_type),",
    ):
        if needle not in check:
            fail(f"post-apply gate missing: {needle}")

    print("NATIVEBOOT2-B28 WSERVLIBTYPE1 applied")
    print("epoc94_svc_0x63=LibraryType")
    print("abi=handle_then_TUidType_ref")
    print("other_wserv_svc_gaps=UNCHANGED")
    print("wserv_panic_behavior=UNCHANGED")
    print("B25_FBSSHAREDHEAP1=PRESERVED")
    print("B26_IOSLIBRARYEXIT1=PRESERVED")
    print("B27_WSERVPANIC13TRACE1=PRESERVED")

if __name__=="__main__":
    main()
