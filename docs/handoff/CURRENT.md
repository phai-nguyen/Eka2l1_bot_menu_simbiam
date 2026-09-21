# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-21
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active development branch: nativeboot2-current
Latest FASTBUILD1 clean build-tested branch HEAD: 8dc0423c9cdcf8fa353e16eae9ec8359b1587f66
Latest immutable functional milestone: B28 WSERVLIBTYPE1
Latest immutable functional code HEAD: 773752a4475dce019e8ae4342f2ab7d0b2abc060
Latest device-tested milestone: B27
FASTBUILD1 status: PROMOTED

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, preserving firmware SYSSTART ownership and adding narrowly scoped compatibility fixes only after device evidence.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

B28 = NATIVEBOOT2-B28-WSERVLIBTYPE1

Immutable milestone branch:
nativeboot2-b28-wservlibtype1

Active development branch:
nativeboot2-current

Build workflow:
.github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml

Apply script:
apply_nativeboot2_b28_wservlibtype1.py

Contract:
test_nativeboot2_b28_wservlibtype1.py

Successful build run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35606704683

Run ID:
35606704683

Build code HEAD:
773752a4475dce019e8ae4342f2ab7d0b2abc060

Unsigned IPA:
EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-unsigned.ipa

IPA SHA-256:
8fd1ef35863a8b8deb175650259052977d15c0e66dc578a415e95050ebfbc81b

IPA artifact:
- ID: 10642526382
- ZIP digest: sha256:3d92f5b4ba6812ba44e4a3a6516750bbd08e35418197e6f988e2a808f4afd145
- expires: 2026-10-05

Audit artifact:
- ID: 10642476357
- ZIP digest: sha256:7bb7db13282a9e1fb4a83c914079cbb7cfb6c276e81d633ebf7606ae7c32359f
- expires: 2026-10-05

## FASTBUILD1 — promoted development build path

FASTBUILD1 is PROMOTED for normal B29/B30 development.

Active development branch:
nativeboot2-current

Latest immutable functional milestone:
nativeboot2-b28-wservlibtype1

Stable bootstrap:
- milestone: B28 WSERVLIBTYPE1
- key: eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1
- seed run: 35612902115
- fallback: B19 cache -> apply B20-B28
- normal fast workflow does not save the whole upstream tree

Fast workflow:
.github/workflows/build-ios-nativeboot2-current-fast.yml

Manual bootstrap workflow:
.github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml

sccache:
- mozilla-actions/sccache-action@v0.0.11
- SCCACHE_GHA_ENABLED=true
- SCCACHE_IGNORE_SERVER_IO_ERROR=1
- SCCACHE_BASEDIRS=<upstream>
- C/C++ compiler launchers = sccache

Measured evidence:
- B28 historical baseline: ~197 s
- cold B19 fallback run 35612768609: 614 s
- hot B28-cache run 35614076698: 71 s
- strong one-file probe run 35616222173: 1 request / 1 miss / 1 real compile
- identical probe retry 35616567861: 1 request / 1 hit / 0 miss
- post-probe clean run 35616906674: 56 s
- final clean verification run 35617195868: 69 s

Final clean verification run:
- code HEAD: 8dc0423c9cdcf8fa353e16eae9ec8359b1587f66
- bootstrap_source=B28_CACHE
- B20-B28 PASS
- compile requests: 0
- NOJAVA preserved
- MANIC3 preserved
- unsigned IPA SHA-256: be170c9e03f9fe901c775a323d00e16411752beb68950e4bbd7e46097fabaf1f
- IPA artifact: 10647395134
- audit artifact: 10646479731

Static/TDD clean-head run:
- 35617195978
- manifest tests: 4/4 PASS
- workflow tests: 8/8 PASS
- manifest VALID

B28 workflow remains byte-for-byte unchanged:
44d1c8aaa7ff5f0ff97271396b8bf771ad125b54

Full benchmark/probe evidence:
docs/handoff/history/FASTBUILD1.md

Development rule from now on:
1. B29/B30 functional work lands on nativeboot2-current.
2. Add the new apply_script|test_script row to ci/fastbuild1_manifest.txt.
3. Build/test/device-test on nativeboot2-current.
4. Snapshot the exact validated commit to an immutable nativeboot2-bXX-* branch.
5. Do not return to sibling milestone branches as the primary development/cache path.

FASTBUILD1 does not change the current guest-side blocker. B28 is still the functional baseline awaiting device validation.

## Validated milestones

### B25 — FBSSHAREDHEAP1

DEVICE-VALIDATED.

B25 fixed the native/HLE FBS canonical global chunk-name collision.

Healthy runtime markers:
- [NBOOT2][FBS_SHARED_HEAP_HANDOFF]
- shared_guest_owned=true
- shared_renamed=true
- large_guest_owned=true
- large_renamed=true
- [NBOOT2][FBS_SHARED_HEAP_READY]

The old AknCapServer failure:
- PC = 0x000000F0
- r0 = 0x40201598
- KERN-EXEC 3

is no longer the active blocker.

Firmware reaches the NOKIA splash.

### B26 — IOSLIBRARYEXIT1

DEVICE-VALIDATED.

The host-side UIKit UICollectionView crash when choosing Exit Emulator is fixed.

Validated exit sequence:
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

Preserve the B26 exit choreography.

### B27 — WSERVPANIC13TRACE1

DEVICE-TESTED diagnostic milestone.

B27 localized the current Nokia boot blocker.

Observed ordering:
1. !Windowserver registration succeeds.
2. B25 FBS shared-heap handoff succeeds.
3. SVCMISS 0x48.
4. SVCMISS 0x4A.
5. EKDATA.DLL loads:
   - UID3 = 0x100039E0
   - runtime code = 0x807ABDF8
6. SVCMISS 0x63:
   - pc = 0x80297F64
   - lr = 0x802A1CFD
   - r0 = 0x400F0007
7. Symbian leave begins/traps immediately afterward.
8. Wserv reports EWsPanicFailedToInitialise.
9. Wserv self-panics:
   - category = WSERV-INTERNAL
   - reason = 13
10. NearlyIdleKickBack then panics Domino 13 downstream.

B27 Wserv panic:
- PC = 0x80298584
- LR = 0x802A3A39
- SP = 0x00503C70

## Source meaning of WSERV-INTERNAL 13

Public Symbian Window Server source defines:
EWsPanicFailedToInitialise = 13

WSTOP.CPP traps CWsTop::RunServerL(); if it leaves/errors, E32Main panics with EWsPanicFailedToInitialise.

Thus B27 proves Wserv is leaving during RunServerL / InitStaticsL rather than failing in the old FBS crash path.

Reference:
- SymbianSource/oss.FCL.sf.os.graphics
- commit ff133bc50e6158bfb08cc093b0f0055321dcde99
- windowing/windowserver/nonnga/SERVER/WSTOP.CPP
- windowing/windowserver/SERVER/openwfc/panics.h

## B28 — WSERVLIBTYPE1

BUILD-VALIDATED, NOT YET DEVICE-VALIDATED.

B28 implements only EPOC 9.4 SVC 0x63 as the EKA2 LibraryType executive.

External Symbian source confirms:
- RLibrary::Type() creates a TUidType and calls Exec::LibraryType(iHandle, u).
- Exec::LibraryType(TInt, TUidType&) dispatches EExecLibraryType.

B28 implementation:
- ABI:
  LibraryType(handle, TUidType&)
- resolves kernel::library from the guest handle
- reads lib->get_codeseg()->get_uids()
- writes UID1 / UID2 / UID3 into the guest output
- adds runtime marker:
  [NBOOT2][WSERV_LIBRARY_TYPE]
- registers:
  BRIDGE_REGISTER(0x63, library_type)
- preserves:
  BRIDGE_REGISTER(0x64, process_type)

B28 deliberately does NOT implement:
- SVC 0x48
- SVC 0x4A
- SVC 0x50

and does not suppress Wserv panic behavior.

### TDD evidence

Focused RED run:
35605582017

Expected failure:
NATIVEBOOT2-B28-WSERVLIBTYPE1-TEST: FAIL: missing in svc.cpp:
BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)

GREEN/build run:
35606704683

PASS:
- B20
- B21
- B22
- B23
- B24
- B25
- B26
- B27
- B28
- iOS compile/link
- NOJAVA
- MANIC3

## Required B28 device test

On the next device log, check in this order:

1. EKDATA.DLL still loads.
2. SVCMISS 0x63 is absent.
3. Marker appears:
   [NBOOT2][WSERV_LIBRARY_TYPE]
4. Record:
   - handle
   - valid
   - output_mapped
   - uid1
   - uid2
   - uid3
5. For the observed EKDATA call, UID3 should correspond to 0x100039E0 if r0=0x400F0007 is indeed that just-loaded RLibrary handle.
6. Check whether:
   - EWsPanicFailedToInitialise disappears;
   - WSERV-INTERNAL 13 disappears;
   - Domino 13 disappears downstream;
   - boot advances beyond the NOKIA splash.
7. If Wserv still fails, identify the first newly exposed call after LibraryType. Do not immediately fix 0x48/0x4A/0x50 without fresh ordering evidence.
8. Test Thoát Emulator once to preserve B26 validation.

## Other Wserv gaps still under observation

B27 also saw:
- 0x50 during early Wserv startup, strongly consistent with WsRegisterThread.
- 0x48 and 0x4A during InitStaticsL, consistent with Window Server event-hook executive calls.

These remain candidates only.

Current decision rule:
B28 first. Let the device log establish the next causal blocker.

## Preserved invariants

Keep:
- firmware SYSSTART as startup owner
- native fbserv startup/rendezvous
- B25 FBS shared-heap handoff
- B24 CBitmapFont/vtable diagnostics
- B23 TFontSpec v2 ABI
- B22 default typeface
- B21 font aliases
- B20 Central Repository ResetAll
- B19 SA language ABI
- EMUHUB1
- B26 safe Exit Emulator path
- B27 Wserv panic diagnostics
- B28 narrow LibraryType implementation
- NOJAVA
- MANIC3

Do not reintroduce:
- host-driven SysStart/Menu launch ownership
- native fbserv suppression
- native FBS heap adoption
- Wserv panic suppression
- speculative multi-SVC batches

## Milestone history

- B19: SALANGABI1
- B20: CENRESETALL1
- B21: FBSFONTALIAS1
- B22: FBSDEFAULTTYPEFACE1
- B23: FBSFONTSPECV2ABI1
- B24: FBSVTABLEABI1
- B25: FBSSHAREDHEAP1 — device validated
- B26: IOSLIBRARYEXIT1 — device validated
- B27: WSERVPANIC13TRACE1 — device trace isolated SVC 0x63 -> leave -> WSERV-INTERNAL 13
- B28: WSERVLIBTYPE1 — build validated, awaiting device test

Snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md
- docs/handoff/history/B27-WSERVPANIC13TRACE1.md
- docs/handoff/history/B28-WSERVLIBTYPE1.md

## How to resume

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam. Active development is nativeboot2-current with FASTBUILD1 promoted; B28 WSERVLIBTYPE1 remains the latest immutable functional milestone and is not device-validated. Analyze the first B28 device log around [NBOOT2][WSERV_LIBRARY_TYPE], SVCMISS 0x63, and Wserv WSERV-INTERNAL 13 before deciding B29. Any B29 work should land on nativeboot2-current first, then be snapshotted after validation."

This file is authoritative unless newer committed device evidence supersedes it.
