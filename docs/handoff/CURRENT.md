# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-21
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active branch: nativeboot2-b26-ioslibraryexit1
Device-tested code HEAD: e1e26c3b59c1b6bd4ec8649d0f83629e4fcd21d9

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, keeping firmware SYSSTART as boot owner while using narrowly scoped HLE compatibility fixes where required.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

B26 = NATIVEBOOT2-B26-IOSLIBRARYEXIT1

Branch:
nativeboot2-b26-ioslibraryexit1

Build workflow:
.github/workflows/build-ios-nativeboot2-b26-ioslibraryexit1-nojava-manic3.yml

Apply script:
apply_nativeboot2_b26_ioslibraryexit1.py

Contract:
test_nativeboot2_b26_ioslibraryexit1.py

Successful build run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35595573032

IPA artifact:
EKA2L1-NATIVEBOOT2-B26-IOSLIBRARYEXIT1-NOJAVA-MANIC3-IPA

IPA artifact ID:
10636601390

Unsigned IPA SHA-256:
9bf54e1d003db0ffa67cbc1983e309f162854f3700c7b9c058f7f5e243002dec

Audit artifact ID:
10636925762

## Device validation status

B25 and B26 are now device-validated.

### B25 validation

B25 FBSSHAREDHEAP1 successfully fixed the FBS canonical shared-heap mismatch.

Observed B25/B26 logs:
- [NBOOT2][FBS_SHARED_HEAP_HANDOFF] shared_found=true shared_guest_owned=true shared_renamed=true large_found=true large_guest_owned=true large_renamed=true
- [NBOOT2][FBS_SHARED_HEAP_READY] shared_created=true large_created=true canonical_owner=kernel native_shared_renamed=true native_large_renamed=true

The old B24 AknCapServer failure signature:
- PC = 0x000000F0
- r0 = 0x40201598
- KERN-EXEC 3

is no longer the active blocker.

The firmware now renders the NOKIA splash screen.

### B26 validation

B25 exposed a separate host-side iOS crash when choosing Exit Emulator.

B25 crash path was in UIKit:
UICollectionView reloadData -> supplementary-view reuse -> EKAUnifiedLibraryViewController reloadWithSymbianApps -> RootViewController showAppsScreen -> exitEmulator.

B26 changed only the iOS frontend exit choreography:
1. complete bridge::stop_native_phone();
2. return to main queue;
3. defer showAppsScreen by one additional main-queue turn;
4. remove the redundant immediate pollForAppsWithAttemptsLeft:20 from exitEmulator;
5. leave Nokia guest boot/FBS behavior untouched.

B26 markers:
- [NBOOT2][IOS_EXIT_UI] phase=shutdown_requested
- [NBOOT2][IOS_EXIT_UI] phase=normal_mode_ready
- [NBOOT2][IOS_EXIT_UI] phase=library_show_deferred
- [NBOOT2][IOS_EXIT_UI] phase=library_show_done

Device evidence from Log(10).zip:
- [NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_done
- [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_begin
- [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done has_device=1
- normal frontend app enumeration resumes afterward
- 54 visible ROM system apps were enumerated in the capture

Video evidence:
- firmware remains on NOKIA splash before exit;
- Exit Emulator returns successfully to the Symbian app-library screen;
- app remains running;
- no repeat of the B25 UIKit crash.

B26 IOSLIBRARYEXIT1 is therefore considered DEVICE-VALIDATED.

## Established B24 -> B25 root cause

Native firmware fbserv originally created:
- FbsSharedChunk @ 0x40200000
- FbsLargeChunk @ 0x44200000

HLE FBS later created:
- FbsSharedChunk @ 0x54200000

HLE returned an object offset such as:
- address_offset = 0x1598
- HLE object = 0x54201598

The client opened the native canonical global name and reconstructed:
0x40200000 + 0x1598 = 0x40201598

This exactly matched the old AknCapServer crash r0.

B25 resolves this by renaming guest-owned native chunks before HLE canonical chunk creation:
- FbsSharedChunk -> FbsSharedChunk.NativeBoot
- FbsLargeChunk -> FbsLargeChunk.NativeBoot

Native fbserv is preserved.
Native handles are preserved.
HLE still owns its own allocator/chunks.
No native RHeap adoption is performed.

## Current boot state

Current visible milestone:
NOKIA splash rendered successfully.

The boot has not yet progressed beyond the NOKIA splash during the latest test window.

The next work must return to guest-side startup analysis rather than frontend exit handling.

## B27 investigation target

Log(10) shows these notable early guest-side failures:

1. Main thread:
   - category: SosPmmHandler: N
   - exit code: -1

2. Window Server:
   - thread: Wserv
   - category: WSERV-INTERNAL
   - exit code: 13

3. Window Server companion:
   - thread: NearlyIdleKickBack
   - category: Domino
   - exit code: 13

The Wserv and NearlyIdleKickBack panics occur immediately after:
- native ewsrv startup;
- !Windowserver registration;
- successful B25 FBS shared-heap handoff;
- several property lookups/attachments;
- an SVCMISS near ewsrv startup.

These are CURRENT CANDIDATES, not yet proven root causes.

Do not implement B27 from the panic names alone.

### Required B27 procedure

1. Isolate the exact instruction/request immediately preceding Wserv panic 13.
2. Resolve the symbolic meaning/source location of WSERV-INTERNAL 13 and Domino 13 if possible.
3. Determine whether the preceding SVCMISS or missing P&S properties are causal.
4. Compare against upstream EKA2L1 Window Server behavior and relevant Symbian/S60 sources.
5. Add targeted runtime markers before changing behavior.
6. Establish a RED contract reproducing the specific missing behavior.
7. Only then implement B27.
8. Preserve B25 and B26 regression contracts.

## Important preserved invariants

Keep:
- firmware SYSSTART as startup owner
- native fbserv startup/rendezvous
- B25 FBS shared-heap handoff
- B24 CBitmapFont vtable diagnostics
- B23 TFontSpec v2 ABI handling
- B22 default typeface handling
- B21 font alias handling
- B20 Central Repository ResetAll
- B19 SA language ABI handling
- EMUHUB1 frontend
- B26 safe Exit Emulator path
- NOJAVA
- MANIC3

Do not reintroduce:
- host-driven SysStart/Menu launch
- native fbserv suppression
- native FBS heap adoption
- speculative font-vtable changes
- immediate library UICollectionView reload on Emulator exit

## Milestone history

Relevant chain:
- B19: SALANGABI1
- B20: CENRESETALL1
- B21: FBSFONTALIAS1
- B22: FBSDEFAULTTYPEFACE1
- B23: FBSFONTSPECV2ABI1
- B24: FBSVTABLEABI1
- B25: FBSSHAREDHEAP1 — device validated, NOKIA splash reached
- B26: IOSLIBRARYEXIT1 — device validated, Exit Emulator no longer crashes

Detailed snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md

## How to resume in a new ChatGPT conversation

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam and continue the Nokia 5800 NativeBoot project from the active branch. B25 and B26 are device-validated. Analyze the latest guest boot logs around Wserv WSERV-INTERNAL 13 / Domino 13 before implementing B27."

This file is the authoritative current project handoff unless newer committed device evidence supersedes it.
