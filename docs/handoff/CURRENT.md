# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-21
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active development branch: nativeboot2-current
Latest FASTBUILD1 CI implementation commit: 9381a02b131102ac6f1088ae077411d27f753132
Latest immutable functional milestone: B28 WSERVLIBTYPE1
Latest immutable functional code HEAD: 773752a4475dce019e8ae4342f2ab7d0b2abc060
Latest development build: B29 CENREPTX1 + DIAG1 — BUILD-VALIDATED
Latest B29-DIAG1 build-tested project HEAD: f2916297aad315c656c5800f88a7c62d1ce4816a
Latest device-tested milestone: B28
FASTBUILD1 status: PROMOTED

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, preserving firmware SYSSTART ownership and adding narrowly scoped compatibility fixes only after device evidence.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

Active development candidate:
B29 = NATIVEBOOT2-B29-CENREPTX1

Status:
BUILD-VALIDATED, NOT YET DEVICE-VALIDATED

Active development branch:
nativeboot2-current

Stable immutable fallback milestone:
B28 WSERVLIBTYPE1 on nativeboot2-b28-wservlibtype1

FASTBUILD workflow:
.github/workflows/build-ios-nativeboot2-current-fast.yml

B29 apply script:
apply_nativeboot2_b29_cenreptx1.py

B29 contract:
test_nativeboot2_b29_cenreptx1.py

B29 GREEN build run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35623561823

Run ID:
35623561823

Job ID:
106412254328

Functional B29 build-tested project HEAD:
7bceb18a337b0977f0f2f68ea0232748dd848392

Latest diagnostic build-tested project HEAD:
f2916297aad315c656c5800f88a7c62d1ce4816a

Unsigned IPA to device-test:
EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa

IPA SHA-256:
b61edcd7721de3298818bd483debd8f186f6eb796aac57e4956e458f6f5996dc

IPA artifact:
- ID: 10652337447
- ZIP digest: sha256:6f0cac8dfd94d4c3079b10bebe7d192dde6651f17d3491ed6017d6122344153a
- expires: 2026-10-05

Audit artifact:
- ID: 10652602353
- ZIP digest: sha256:90505db5ff05ae1444ad5e7e3edbc72aa17e7284d22e3a108d730edac3cc3b85
- expires: 2026-10-05

B29 RED evidence:
- project HEAD: 14a558b2dba4ad0ae4adcbbb86b367e8d60e0db2
- run: 35623202762
- expected failure: missing cen_rep_transaction_commit registration
- B20-B28 passed before the intended B29 failure

B29 GREEN evidence:
- B29 apply PASS
- B29 contract PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA packaging/upload PASS
- NOJAVA preserved
- MANIC3 preserved

## FASTBUILD1 — promoted development build path

FASTBUILD1 is PROMOTED for B29 device validation and normal B30+ development.

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

FASTBUILD1 does not change guest behavior. B28 remains the latest device-validated immutable milestone. B29 CENREPTX1 is now build-validated on nativeboot2-current and targets the Central Repository/FEP/UIKON blocker; device evidence is still required before promotion to an immutable B29 milestone.

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

BUILD-VALIDATED, NOT YET DEVICE-VALIDATED.

B29 implements the narrow generic Central Repository compatibility required by the B28 Eiksrv/FEP trace:
- registers/routes cen_rep_transaction_commit;
- makes StartTransaction activate state and map Symbian modes 1/2/3;
- stages transactional Set changes with copy-on-write;
- makes Set create a missing key with repository default metadata;
- Commit installs staged changes, persists once, then notifies;
- Cancel discards staged changes;
- fixes transaction-mode decoding so active bits do not contaminate the mode;
- adds [NBOOT2][CEN_TX_START], [NBOOT2][CEN_SET_CREATE], [NBOOT2][CEN_TX_COMMIT], [NBOOT2][CEN_TX_CANCEL].

B29 does not hardcode repository 0x10272618 or FEP key values and does not modify SVC 0x2D/0x48/0x4A/0x50.

TDD RED:
- run 35623202762
- expected B29 contract failure
- B20-B28 PASS first

GREEN:
- run 35623561823
- job 106412254328
- B29 PASS
- B20-B28 PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA SHA-256 25c6846ced19f435523570c2e586fd18031f4c7f05e94e89a50e8f2bace63b70

Required device decision:
Use the B29-DIAG1 IPA above. Confirm repo 0x10272618 now shows the detailed transaction path and determine the first divergence before promoting B29 or choosing B30.

### B29-DIAG1 — diagnostics only

BUILD-VALIDATED.

DIAG1 does not alter B29 semantics. It adds:
- [NBOOT2][CEN_SET_BEGIN]
- [NBOOT2][CEN_SET_RESULT]
- [NBOOT2][CEN_SET_FAIL]
- [NBOOT2][CEN_TX_COMMIT_BEGIN]
- [NBOOT2][CEN_TX_COMMIT_KEY]
- [NBOOT2][CEN_TX_COMMIT_RESULT]
- [NBOOT2][CEN_TX_COMMIT_FAIL]

Existing CEN_TX_START / CEN_SET_CREATE / CEN_TX_COMMIT / CEN_TX_CANCEL markers remain.

RED:
- run 35626098291
- expected failure: CEN_SET_BEGIN absent

First GREEN attempt:
- run 35626322869
- patcher stopped before compile because a common Set anchor occurred in int/real/string cases
- root cause fixed by scoping replacements to each Set case

Final GREEN:
- run 35626484148
- job 106421997929
- project HEAD f2916297aad315c656c5800f88a7c62d1ce4816a
- B29 + DIAG1 PASS
- B20-B28 PASS
- compile/link PASS
- binary contains all DIAG1 marker strings
- sccache 8/9 hits (88.89%)
- total_seconds=142
- IPA SHA-256 b61edcd7721de3298818bd483debd8f186f6eb796aac57e4956e458f6f5996dc

For repo 0x10272618, inspect:
CEN_TX_START -> CEN_SET_BEGIN -> CEN_SET_RESULT/CEN_SET_FAIL -> CEN_SET_CREATE when applicable -> CEN_TX_COMMIT_BEGIN -> CEN_TX_COMMIT_KEY -> CEN_TX_COMMIT_RESULT/CEN_TX_COMMIT_FAIL -> CEN_TX_CANCEL if rollback occurs.

Important diagnostic question:
record existing=0/1 and existing_type/requested_type for the FEP keys. SymbianSource operations.h explicitly permits internal SetSettingL to create a missing setting; higher-level SDK prose also distinguishes public Create(). Do not change B29 semantics again until the device trace shows which path this firmware actually exercises.

Full snapshot:
docs/handoff/history/B29-DIAG1.md

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
B29 is build-validated. Device-test B29 first and use the first new divergence after CEN_TX_START/CEN_SET_CREATE/CEN_TX_COMMIT to choose B30. Do not batch 0x2D, 0x48, 0x4A, or 0x50 without new causal evidence.

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
- B29: CENREPTX1 — build validated on nativeboot2-current; awaiting device validation
- B29-DIAG1: diagnostic-only logging build validated; use this IPA for the next device test

Snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md
- docs/handoff/history/B27-WSERVPANIC13TRACE1.md
- docs/handoff/history/B28-WSERVLIBTYPE1.md
- docs/handoff/history/B29-CENREPTX1.md
- docs/handoff/history/B29-DIAG1.md

## How to resume

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam. Active development is nativeboot2-current with FASTBUILD1 promoted. B28 is the latest device-validated immutable milestone. B29 CENREPTX1 plus B29-DIAG1 is build-validated at project HEAD f2916297aad315c656c5800f88a7c62d1ce4816a, run 35626484148. Device-test IPA SHA b61edcd7721de3298818bd483debd8f186f6eb796aac57e4956e458f6f5996dc and analyze repo 0x10272618 using CEN_TX_START, CEN_SET_BEGIN/RESULT/FAIL, CEN_SET_CREATE, CEN_TX_COMMIT_BEGIN/KEY/RESULT/FAIL, CEN_TX_CANCEL, eiksrvs Leave -1, AknCapServer progress, and preserved B28 Wserv markers before deciding B30."

This file is authoritative unless newer committed device evidence supersedes it.
