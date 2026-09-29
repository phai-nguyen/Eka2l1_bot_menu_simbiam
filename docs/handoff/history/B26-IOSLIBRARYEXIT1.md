# B26 IOSLIBRARYEXIT1 — Device-Validated Snapshot

Date: 2026-09-21
Branch: nativeboot2-b26-ioslibraryexit1
Device-tested code HEAD: e1e26c3b59c1b6bd4ec8649d0f83629e4fcd21d9

## Build

Workflow run: 35595573032
Status: SUCCESS

IPA artifact:
- name: EKA2L1-NATIVEBOOT2-B26-IOSLIBRARYEXIT1-NOJAVA-MANIC3-IPA
- artifact ID: 10636601390
- artifact ZIP digest: sha256:648b5fee7772cdb5b9e57bced3ae2db32ed0b75249148946a7fd7c7728e9c872

Unsigned IPA:
- file: EKA2L1-NATIVEBOOT2-B26-IOSLIBRARYEXIT1-NOJAVA-MANIC3-unsigned.ipa
- SHA-256: 9bf54e1d003db0ffa67cbc1983e309f162854f3700c7b9c058f7f5e243002dec

Audit artifact:
- artifact ID: 10636925762
- artifact ZIP digest: sha256:2a95dbd67cfa084df1935c202d499dc7e4cf5e9ed25f2f5b97367e29dc99884e

Build validation:
- B26 IOSLIBRARYEXIT1 contract PASS
- B25 FBSSHAREDHEAP1 regression PASS
- B24/B23/B22/B21/B20 regression suite PASS
- iOS compile PASS
- unsigned IPA packaging PASS

## Device evidence

User device test supplied:
- Log(10).zip
- ScreenRecording_09-21-2026 19-07-25_1(1).mp4

Observed video result:
- native Nokia boot reaches the NOKIA splash;
- selecting the emulator exit action returns to the normal Symbian app-library screen;
- application remains alive after the return;
- subsequent movement to the iOS Home/App Switcher is user-initiated, not an app crash.

Observed logs:
- B25 FBS handoff remains active:
  - shared_found=true
  - shared_guest_owned=true
  - shared_renamed=true
  - large_found=true
  - large_guest_owned=true
  - large_renamed=true
- HLE canonical FBS chunks are created successfully.
- Exit sequence reaches:
  - [NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_done
  - [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_begin
  - [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done has_device=1
- normal frontend app enumeration resumes after restart (54 visible ROM system apps in this capture).

Conclusion:
B26 fixes the B25 host-side iOS/UIKit crash that occurred when returning from Emulator to the collection-view library.

## B26 change

The exit path no longer reloads the existing library UICollectionView immediately in the same main-loop turn after native-mode teardown.

It:
1. completes bridge::stop_native_phone();
2. returns to the main queue;
3. defers showAppsScreen by one additional main-queue turn;
4. removes the redundant immediate pollForAppsWithAttemptsLeft:20 call from exitEmulator;
5. preserves all Nokia guest/FBS behavior from B25.

Runtime markers introduced:
- [NBOOT2][IOS_EXIT_UI] phase=shutdown_requested
- [NBOOT2][IOS_EXIT_UI] phase=normal_mode_ready
- [NBOOT2][IOS_EXIT_UI] phase=library_show_deferred
- [NBOOT2][IOS_EXIT_UI] phase=library_show_done

## Next boot blocker candidate

The firmware remains at the NOKIA splash during the test window.

The earliest notable post-FBS guest-side failures in Log(10) are:
- Wserv panic: category WSERV-INTERNAL, exit code 13
- NearlyIdleKickBack panic: category Domino, exit code 13

These are candidates for B27 investigation only; they are not yet established as the root cause.

Also present earlier:
- Main panic: SosPmmHandler: N, exit code -1

Do not patch these speculatively. First isolate the earliest causal divergence around ewsrv/Window Server startup and determine whether the SVCMISS/property warnings immediately before the Wserv panic are causal.

## Milestone status

B25: device-validated FBS shared-heap fix; NOKIA splash reached.
B26: device-validated iOS exit/library crash fix.

The next work should focus again on advancing firmware boot beyond the NOKIA splash.
