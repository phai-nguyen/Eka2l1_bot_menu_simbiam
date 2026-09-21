#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B26 IOSLIBRARYEXIT1 on top of B25.

B25 device evidence proves boot/FBS improved enough to render NOKIA.
The remaining crash on "Exit Emulator" is in UIKit's UICollectionView reuse/reload path.
B26 changes only the iOS exit choreography: after bridge::stop_native_phone() returns,
showAppsScreen is deferred to a second main-queue turn and the redundant immediate
pollForAppsWithAttemptsLeft:20 is removed from exitEmulator.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B26-IOSLIBRARYEXIT1"

def fail(msg:str)->None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text:str, old:str, new:str, label:str)->str:
    c=text.count(old)
    if c!=1:
        fail(f"{label}: expected one anchor, found {c}")
    return text.replace(old,new,1)

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b26_ioslibraryexit1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    root=up/"src/emu/ios/app/RootViewController.mm"
    fbs=up/"src/emu/services/src/fbs/fbs.cpp"
    if not root.is_file() or not fbs.is_file():
        fail("baseline source missing")

    text=root.read_text(encoding="utf-8")
    f=fbs.read_text(encoding="utf-8")
    if "NATIVEBOOT2 EMUHUB1" not in text:
        fail("EMUHUB1 checkpoint missing")
    if "[NBOOT2][FBS_SHARED_HEAP_HANDOFF]" not in f or "[NBOOT2][FBS_SHARED_HEAP_READY]" not in f:
        fail("B25 checkpoint missing")

    if "[NBOOT2][IOS_EXIT_UI]" not in text:
        old='''    dispatch_async(EKANgageLifecycleQueue(), ^{
        eka2l1::ios::bridge::stop_native_phone();
        dispatch_async(dispatch_get_main_queue(), ^{
            self.emuView.userInteractionEnabled = YES;
            self.controlsView.userInteractionEnabled = YES;
            [self showAppsScreen];
            [self pollForAppsWithAttemptsLeft:20];
            NSLog(@"NATIVEBOOT2 EMUHUB1: restored normal EKA2L1 frontend mode");
        });
    });
}
'''
        new='''    NSLog(@"[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested");
    dispatch_async(EKANgageLifecycleQueue(), ^{
        eka2l1::ios::bridge::stop_native_phone();
        dispatch_async(dispatch_get_main_queue(), ^{
            self.emuView.userInteractionEnabled = YES;
            self.controlsView.userInteractionEnabled = YES;
            NSLog(@"[NBOOT2][IOS_EXIT_UI] phase=normal_mode_ready");

            // NATIVEBOOT2-B26 IOSLIBRARYEXIT1:
            // Do not reload the existing UICollectionView in the same main-loop
            // turn that restores the normal frontend. B25 device crash evidence
            // points at UICollectionView supplementary-view reuse during reloadData.
            // A second main-queue hop lets UIKit finish menu dismissal/view hierarchy
            // bookkeeping before showAppsScreen refreshes the library.
            dispatch_async(dispatch_get_main_queue(), ^{
                NSLog(@"[NBOOT2][IOS_EXIT_UI] phase=library_show_deferred");
                [self showAppsScreen];
                NSLog(@"[NBOOT2][IOS_EXIT_UI] phase=library_show_done");
            });
            NSLog(@"NATIVEBOOT2 EMUHUB1: restored normal EKA2L1 frontend mode");
        });
    });
}
'''
        text=replace_once(text,old,new,"defer iOS library reload after emulator exit")

    root.write_text(text,encoding="utf-8")
    check=root.read_text(encoding="utf-8")
    for n in ("phase=shutdown_requested","phase=normal_mode_ready","phase=library_show_deferred","phase=library_show_done"):
        if n not in check:
            fail(f"post-apply gate missing: {n}")
    start=check.find("- (void)exitEmulator")
    end=check.find("// ---- Install (device + game)",start)
    body=check[start:end]
    if "[self pollForAppsWithAttemptsLeft:20];" in body:
        fail("redundant exit poll still present")
    print("NATIVEBOOT2-B26 IOSLIBRARYEXIT1 applied")
    print("scope=iOS_frontend_exit_only")
    print("b25_fbssharedheap1=PRESERVED")
    print("guest_boot=UNCHANGED")
    print("exit_library_reload=DEFERRED_ONE_MAIN_LOOP")
    print("redundant_exit_poll=REMOVED")

if __name__=="__main__":
    main()
