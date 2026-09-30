#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B26 IOSLIBRARYEXIT1.

Device evidence from B25:
- Native Nokia boot reached the NOKIA splash after B25.
- FBS shared-heap handoff markers showed guest-owned native chunks renamed and HLE canonical chunks active.
- Exit crash is host-side iOS/UIKit, not a Symbian guest crash.
- Crash path: UICollectionView reloadData -> supplementary reuse -> EKAUnifiedLibraryViewController reloadWithSymbianApps -> RootViewController showAppsScreen -> exitEmulator.
- Emulator shutdown itself reached shutdown_done and normal_restart_begin.

B26 scope:
- preserve B25 guest/FBS behavior;
- make exitEmulator return to the library without immediately reloading the existing UICollectionView in the same main-loop turn;
- defer showAppsScreen until a fresh main-queue turn after normal-mode rebuild completes;
- suppress the immediate extra pollForAppsWithAttemptsLeft:20 from exitEmulator, because showAppsScreen already refreshes the library;
- add exact phase markers around the exit handoff so device logs can prove whether UIKit survives.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B26-IOSLIBRARYEXIT1-TEST"

def fail(msg:str)->None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text:str, needle:str, where:str)->None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main()->None:
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b26_ioslibraryexit1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    root=up/"src/emu/ios/app/RootViewController.mm"
    fbs=up/"src/emu/services/src/fbs/fbs.cpp"
    if not root.is_file() or not fbs.is_file():
        fail("baseline source missing")
    r=root.read_text(encoding="utf-8")
    f=fbs.read_text(encoding="utf-8")

    need(r,"NATIVEBOOT2 EMUHUB1","RootViewController.mm")
    need(f,"[NBOOT2][FBS_SHARED_HEAP_HANDOFF]","fbs.cpp")
    need(f,"[NBOOT2][FBS_SHARED_HEAP_READY]","fbs.cpp")

    start=r.find("- (void)exitEmulator")
    end=r.find("// ---- Install (device + game)",start)
    if start<0 or end<0:
        fail("cannot isolate exitEmulator")
    body=r[start:end]

    for needle in (
        "[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested",
        "[NBOOT2][IOS_EXIT_UI] phase=normal_mode_ready",
        "[NBOOT2][IOS_EXIT_UI] phase=library_show_deferred",
        "dispatch_async(dispatch_get_main_queue(), ^{",
        "[self showAppsScreen];",
    ):
        need(body,needle,"exitEmulator")

    if "[self pollForAppsWithAttemptsLeft:20];" in body:
        fail("exitEmulator must not queue a second immediate library refresh")

    normal=body.find("phase=normal_mode_ready")
    deferred=body.find("phase=library_show_deferred")
    show=body.find("[self showAppsScreen];")
    if not (0 <= normal < deferred < show):
        fail("exit phases must be normal_mode_ready -> library_show_deferred -> showAppsScreen")

    # Two main-queue hops are intentional: first resumes after lifecycle queue,
    # second lets UIKit finish dismissing/reuse bookkeeping before reloadData.
    if body.count("dispatch_async(dispatch_get_main_queue(), ^{") < 2:
        fail("exitEmulator must defer library show by a fresh main-queue turn")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
