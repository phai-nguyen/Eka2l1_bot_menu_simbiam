# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-22
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active development branch: nativeboot2-current
Latest FASTBUILD1 CI implementation commit: 9381a02b131102ac6f1088ae077411d27f753132
Latest immutable functional milestone: B29 CENREPTX1
Latest immutable functional code HEAD: 7bceb18a337b0977f0f2f68ea0232748dd848392
Latest development build: B29 CENREPTX1 + DIAG1 + LOADERDIAG1 — BUILD-VALIDATED
Latest LOADERDIAG1 build-tested code commit: 9aa612714878541ec4b3f7481516bba00b6d52a4
Latest device-tested milestone: B29
FASTBUILD1 status: PROMOTED

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, preserving firmware SYSSTART ownership and adding narrowly scoped compatibility fixes only after device evidence.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

Latest device-validated functional milestone:
B29 = NATIVEBOOT2-B29-CENREPTX1

Immutable B29 branch:
nativeboot2-b29-cenreptx1

Immutable B29 functional commit:
7bceb18a337b0977f0f2f68ea0232748dd848392

Active diagnostic candidate:
B29-LOADERDIAG1

Status:
BUILD-VALIDATED, DEVICE LOG REQUIRED

Active development branch:
nativeboot2-current

FASTBUILD workflow:
.github/workflows/build-ios-nativeboot2-current-fast.yml

LOADERDIAG1 apply script:
apply_nativeboot2_b29_loaderdiag1.py

LOADERDIAG1 contract:
test_nativeboot2_b29_loaderdiag1.py

GREEN run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35662229010

Run ID:
35662229010

Job ID:
106539879024

Build-tested code commit:
9aa612714878541ec4b3f7481516bba00b6d52a4

Unsigned IPA to device-test:
EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa

IPA SHA-256:
b748c0e009721b37f24e89003fc1a2a0a8e64e158379a633ece78b0e94576d7c

IPA artifact:
- ID: 10668485125
- ZIP digest: sha256:850219186c73d92e0153c31f7d2b28110cf41eb7dc7e6d9c69f1081431142d1a
- expires: 2026-10-05

Audit artifact:
- ID: 10668055503
- ZIP digest: sha256:5cc3328e8728a5fc064eebbf95cef289eac4c9a8e56874fda9a01878e7ce6b8e
- expires: 2026-10-05

FASTBUILD1 for this build:
- bootstrap_source=B28_CACHE
- bootstrap restore: 29 s
- patch/regression: 2 s
- CMake build: 71 s
- package: 2 s
- total: 137 s
- sccache: 9/11 hits = 81.82%
- actual compilations: 2
- NOJAVA preserved
- MANIC3 preserved

Post-build verification:
- B29 CENREPTX1 PASS
- B29-DIAG1 PASS
- B29-LOADERDIAG1 PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- packaged Mach-O contains all ten LOADERDIAG1 markers

## FASTBUILD1 — promoted development build path

FASTBUILD1 is PROMOTED for B29 loader diagnostics and normal B30+ development.

Active development branch:
nativeboot2-current

Latest immutable functional milestone:
nativeboot2-b29-cenreptx1

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
- pre-final-review clean run 35617195868: 69 s with the earlier timer scope
- final corrected-scope hot run 35618944742: 63 s
- final permanent-equivalent probe 35619278590: 1 request / 1 hit / 0 miss / no IPA

Final FASTBUILD1 implementation verification:
- implementation commit: 9381a02b131102ac6f1088ae077411d27f753132
- build run: 35618944742
- bootstrap_source=B28_CACHE
- B20-B28 PASS
- compile requests: 0
- bootstrap restore: 36 s
- CMake build: 1 s
- package: 2 s
- corrected total_seconds: 63 s
- NOJAVA preserved
- MANIC3 preserved
- unsigned IPA SHA-256: b289101c866bfa2a86e8046605d08299833b4dcdd0ea98e69425d78a7f93ff8d
- IPA artifact: 10647737754
- audit artifact: 10647383101

Final static/TDD run:
- 35618944698
- manifest tests: 4/4 PASS
- workflow tests: 9/9 PASS
- manifest VALID

Final acceptance suite:
- run: 35619769274
- combined tests: 13/13 PASS
- manifest VALID
- git diff --check PASS
- B28 workflow blob pin PASS

Permanent probe behavior:
- appends a transient macro plus compile-time-only static_assert to restored svc.cpp
- probe runs do not package/upload IPA
- final verification run 35619278590 produced audit artifact 10647023252 and no IPA artifact

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

FASTBUILD1 does not change guest behavior. B29 CENREPTX1 is now the latest device-validated immutable milestone. The active diagnostic target is the later Eiksrv library-load failure exposed after B29's successful FEP transaction.

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

DEVICE-VALIDATED FOR THE LIBRARYTYPE/WSERV BLOCKER.

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

## B28 device result

The 2026-09-21 B28 device log validates the narrow fix.

Observed:
- EKDATA.DLL still loads, UID3=0x100039E0.
- [NBOOT2][WSERV_LIBRARY_TYPE] appears:
  handle=0x400F0007 valid=1 output_mapped=1 uid1=0x10000079 uid2=0x1000008D uid3=0x100039E0
- SVCMISS 0x63 is absent.
- WSERV-INTERNAL 13 is absent.
- Domino 13 is absent.
- a later Wserv Leave -5 is trapped rather than fatal.
- startup continues into StarterServer, tzserver, cntsrv and higher UI/application services.
- B26 Exit Emulator remains healthy: shutdown_done -> normal_restart_begin -> normal_restart_done has_device=1.

Conclusion:
B28 removed the B27 causal chain. Wserv is no longer the active boot blocker.

Do not claim full Nokia UI boot from this log alone; the next failure is later in UIKON/AknCap/Eiksrv startup.

## Active blocker after B28 — Central Repository / FEP

The strongest new causal chain is repository 0x10272618, the FEP framework Central Repository.

Symbian source identifies:
- KUidFepFrameworkRepository = 0x10272618
- default FEP keys under 0x1000:
  - 0x1001 DefaultFepId
  - 0x1002 DefaultOnState
  - 0x1004 DefaultOnKeyData
  - 0x1008 DefaultOffKeyData

Eiksrv CEikServAppUiServer::ConstructL() opens this repository, starts an EConcurrentReadWriteTransaction, writes the default FEP state/ID/key data, then commits.

The B28 baseline Central Repository implementation is incompatible with that path:
- TransactionStart is stubbed and does not call set_active(true).
- TransactionCancel is stubbed.
- Set write mode returns KErrNotFound for absent keys unless a transaction is actually active.
- cen_rep_transaction_commit exists in the opcode enum but is not handled/implemented.
- Symbian's actual SetSettingL creates a missing setting and applies fallback metadata/access policy.

The B28 log correlates this directly:
- repo 0x10272618 opens;
- TransactionStart stubbed;
- immediate eiksrvs Leave -1 with centralrepository.dll + eiksrv.dll on stack;
- TransactionCancel stubbed;
- eiksrvs later self-kills reason -1;
- the sequence repeats on restart.
AknCapServer also has Leave -1 paths through centralrepository.dll + cone.dll.

Therefore the preferred B29 direction is a generic Central Repository transaction/Set fix, not a repo/key hardcode.

## B29 — CENREPTX1

DEVICE-VALIDATED FOR THE CENTRAL REPOSITORY/FEP BLOCKER.

Functional commit:
7bceb18a337b0977f0f2f68ea0232748dd848392

Immutable branch:
nativeboot2-b29-cenreptx1

B29 implements the narrow generic Central Repository compatibility required by the B28 Eiksrv/FEP trace:
- registers/routes cen_rep_transaction_commit;
- makes StartTransaction activate state and map Symbian modes 1/2/3;
- stages transactional Set changes with copy-on-write;
- makes Set create a missing key with repository default metadata;
- Commit installs staged changes, persists once, then notifies;
- Cancel discards staged changes;
- fixes transaction-mode decoding so active bits do not contaminate the mode.

B29 does not hardcode repository 0x10272618 or FEP key values and does not modify SVC 0x2D/0x48/0x4A/0x50.

Device evidence from both B29 and B29-DIAG1:
- repo 0x10272618 starts transaction mode=2 successfully;
- all four FEP settings complete without CEN_SET_FAIL;
- commit reports changed=4, key_info=4, completion=0;
- no transaction cancel follows that successful transaction;
- keys created in the earlier B29 run are present in the later DIAG1 run, confirming persistence;
- B28 Wserv remains healthy: no SVCMISS 0x63, WSERV-INTERNAL 13, or Domino 13.

Conclusion:
the Central Repository/FEP blocker is removed.

### Failure exposed after B29

Both device logs then converge on:
1. FEP transaction commits successfully.
2. Fepswitch.exe returns KErrNotFound.
3. Symbian eiksrv.cpp treats Fepswitch KErrNotFound as optional and continues.
4. Eiksrv attempts RLibrary::Load for its UI-specific DLL.
5. EKA2L1 library loading returns KErrNotFound.
6. EikAppUiServerThread leaves -1 and eiksrvs later exits.

Symbian source confirms the load follows the FEP/Fepswitch sequence and propagates the RLibrary load error with User::LeaveIfError.

### B29-DIAG1 result

DEVICE-OBSERVED.

DIAG1 proved:
- no Set/type/descriptor failure occurs in the FEP transaction;
- Commit succeeds;
- the failure is later than CenRep.

Full snapshot:
docs/handoff/history/B29-DIAG1.md

## B29-LOADERDIAG1 — diagnostics only

BUILD-VALIDATED, DEVICE LOG REQUIRED.

Important source discovery:
the exact B28 FASTBUILD bootstrap differs from newer upstream EKA2L1. In the cached lib_manager::load(), drive iteration occurs only for non-rooted requests. A rooted path without a drive falls through to a direct io_->exist(lib_path) lookup; there is no A:..Z: fallback branch and no ROFS staging step in this loader path.

LOADERDIAG1 deliberately preserves this behavior and only instruments it.

Markers:
- [NBOOT2][LDR_LIB_REQUEST]
- [NBOOT2][LDR_LIB_RESULT]
- [NBOOT2][LDR_ROOT_BEGIN]
- [NBOOT2][LDR_ROOT_DIRECT]
- [NBOOT2][LDR_ROOT_MISS]
- [NBOOT2][LDR_OPEN_FAIL]
- [NBOOT2][LDR_FORMAT]
- [NBOOT2][LDR_PARSE_FAIL]
- [NBOOT2][LDR_CODESEG_RESULT]
- [NBOOT2][LDR_DEP_FAIL]

TDD RED:
- run 35661287453
- expected failure: LDR_LIB_REQUEST absent
- B20-B29/DIAG1 passed before the intended failure

Two patcher-only GREEN failures:
- 35661492473: stale exact load() entry anchor
- 35661698478: assumed newer upstream format/parse block
Neither reached compile.

Systematic one-time baseline inspection:
- run 35661849022
- restored exact B28 cache
- proved the actual rooted-path behavior
- temporary inspection workflow removed after use

Final GREEN:
- run 35662229010
- job 106539879024
- build-tested code commit 9aa612714878541ec4b3f7481516bba00b6d52a4
- B29 + DIAG1 + LOADERDIAG1 PASS
- B20-B28 PASS
- compile/link PASS
- binary invariants PASS
- IPA SHA-256 b748c0e009721b37f24e89003fc1a2a0a8e64e158379a633ece78b0e94576d7c

Device decision matrix:
- ROOT_DIRECT exists=0 + ROOT_MISS => rooted-no-drive direct VFS lookup is causal.
- exists=1 + PARSE_FAIL => image parser path is causal.
- exists=1 + CODESEG_RESULT success=0 + DEP_FAIL => dependency resolution is causal.
- LIB_RESULT success=1 => failure has moved beyond library loading.

Do not implement newer rooted-path search behavior or patch SVC 0x2D/0x48/0x4A/0x50 until this device trace establishes the causal branch.

Full snapshot:
docs/handoff/history/B29-LOADERDIAG1.md

## New missing executive observed after the UI failure

SVCMISS 0x2D appears later:
- r0=0xFFFF8001
- r1=0x000000FA

Symbian execs.txt maps 0x2D to:
ThreadSetProcessPriority(thread_handle, TProcessPriority)

0xFA = 250 = EPriorityBackground.

Because this occurs after the first Central Repository/AknCap/Eiksrv failures, it is not the first causal blocker. Keep it as an observed compatibility gap rather than patching it speculatively.

## Other Wserv gaps still under observation

B27 also saw:
- 0x50 during early Wserv startup, strongly consistent with WsRegisterThread.
- 0x48 and 0x4A during InitStaticsL, consistent with Window Server event-hook executive calls.

These remain candidates only.

Current decision rule:
B29 is device-validated. Device-test B29-LOADERDIAG1 and use the first LDR_* failure boundary to decide B30. Do not implement rooted-path fallback or batch SVC 0x2D/0x48/0x4A/0x50 without that causal evidence.

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
- B29 narrow generic CenRep transaction/Set compatibility
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
- B28: WSERVLIBTYPE1 — device validated; removes missing LibraryType -> WSERV-INTERNAL 13 / Domino 13 blocker
- B29: CENREPTX1 — device validated; immutable branch nativeboot2-b29-cenreptx1
- B29-DIAG1: device-observed; proves CenRep/FEP success and localizes the next failure to library loading
- B29-LOADERDIAG1: diagnostic-only build validated; use this IPA for the next device test

Snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md
- docs/handoff/history/B27-WSERVPANIC13TRACE1.md
- docs/handoff/history/B28-WSERVLIBTYPE1.md
- docs/handoff/history/B29-CENREPTX1.md
- docs/handoff/history/B29-DIAG1.md
- docs/handoff/history/B29-LOADERDIAG1.md

## How to resume

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam. Active development is nativeboot2-current with FASTBUILD1 promoted. B29 CENREPTX1 is the latest device-validated immutable milestone at commit 7bceb18a337b0977f0f2f68ea0232748dd848392 on branch nativeboot2-b29-cenreptx1. B29-LOADERDIAG1 is build-validated at code commit 9aa612714878541ec4b3f7481516bba00b6d52a4, run 35662229010, IPA SHA b748c0e009721b37f24e89003fc1a2a0a8e64e158379a633ece78b0e94576d7c. Device-test that IPA and analyze LDR_LIB_REQUEST/RESULT, LDR_ROOT_BEGIN/DIRECT/MISS, LDR_OPEN_FAIL, LDR_FORMAT/PARSE_FAIL, LDR_CODESEG_RESULT and LDR_DEP_FAIL around the first eiksrvs UI-library load before deciding B30. Do not patch rooted-path fallback or SVC 0x2D/0x48/0x4A/0x50 without the new causal ordering."

This file is authoritative unless newer committed device evidence supersedes it.
