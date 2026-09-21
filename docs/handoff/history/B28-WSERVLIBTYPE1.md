# B28 WSERVLIBTYPE1 — Build Snapshot

Date: 2026-09-21
Branch: nativeboot2-b28-wservlibtype1
Build-tested code HEAD: 773752a4475dce019e8ae4342f2ab7d0b2abc060

## Purpose

B27 device evidence isolated this chain:

EKDATA.DLL load
-> EPOC94 SVCMISS 0x63
-> Symbian leave
-> EWsPanicFailedToInitialise
-> WSERV-INTERNAL 13
-> Domino 13 downstream

B28 is deliberately narrow: implement only the EPOC 9.4 LibraryType executive ABI at SVC 0x63.

## External source validation

Symbian source and documentation establish:
- RLibrary::Type() returns the DLL's TUidType.
- RLibrary::Type() constructs a TUidType and calls Exec::LibraryType(iHandle, u).
- Exec::LibraryType(TInt, TUidType&) dispatches EExecLibraryType.

Therefore the EKA2 ABI is:
LibraryType(library_handle, TUidType_output_reference)

The project EPOC94 table already contains ProcessType at 0x64 and lacked 0x63.

## TDD RED proof

Final focused RED run:
- run ID: 35605582017
- job ID: 106351726824
- expected failure:
  NATIVEBOOT2-B28-WSERVLIBTYPE1-TEST: FAIL: missing in svc.cpp:
  BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)

Earlier temporary RED/inspection runs were used only to correct CI/cache/table-layout assumptions and are not behavior evidence.

## Implementation

Files:
- apply_nativeboot2_b28_wservlibtype1.py
- test_nativeboot2_b28_wservlibtype1.py
- .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml

Implementation:
- adds EKA2 LibraryType bridge:
  BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)
- resolves kernel::library from the handle
- reads lib->get_codeseg()->get_uids()
- writes UID1 / UID2 / UID3 to the guest TUidType output
- registers EPOC94:
  BRIDGE_REGISTER(0x63, library_type)
- preserves:
  BRIDGE_REGISTER(0x64, process_type)
- runtime marker:
  [NBOOT2][WSERV_LIBRARY_TYPE]

No implementation was added for SVC 0x48, 0x4A, or 0x50.
No Wserv panic suppression was added.

## CI investigation note

B28 initially assumed the current project source followed the pinned upstream table layout. The B19 cached project baseline contains earlier NativeBoot patches and the real table ordering is:

- svc_register_funcs_v95_extras
- svc_register_funcs_v10
- svc_register_funcs_menuui10_epoc95_diff
- svc_register_funcs_v94
- svc_register_funcs_v93
- ...

A temporary inspection workflow proved the correct B28 EPOC94 boundary is v94 -> v93. Both apply and contract were corrected accordingly before the successful build.

## Successful build

Workflow run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35606704683

Run ID:
35606704683

Job ID:
106355431925

Conclusion:
SUCCESS

Regression evidence:
- B20 CENRESETALL1 PASS
- B21 FBSFONTALIAS1 PASS
- B22 FBSDEFAULTTYPEFACE1 PASS
- B23 FBSFONTSPECV2ABI1 PASS
- B24 FBSVTABLEABI1 PASS
- B25 FBSSHAREDHEAP1 PASS
- B26 IOSLIBRARYEXIT1 PASS
- B27 WSERVPANIC13TRACE1 PASS
- B28 WSERVLIBTYPE1 PASS
- iOS compilation/link PASS
- NOJAVA preserved
- MANIC3 preserved

## IPA

File:
EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-unsigned.ipa

Unsigned IPA SHA-256:
8fd1ef35863a8b8deb175650259052977d15c0e66dc578a415e95050ebfbc81b

IPA artifact:
- ID: 10642526382
- name: EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-IPA
- artifact ZIP SHA-256: 3d92f5b4ba6812ba44e4a3a6516750bbd08e35418197e6f988e2a808f4afd145
- expires: 2026-10-05

Audit artifact:
- ID: 10642476357
- name: EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-AUDIT
- artifact ZIP SHA-256: 7bb7db13282a9e1fb4a83c914079cbb7cfb6c276e81d633ebf7606ae7c32359f
- expires: 2026-10-05

## Device validation status

DEVICE-VALIDATED FOR THE B28 NARROW PURPOSE.

Device log supplied 2026-09-21 proves the B27 fatal Window Server chain is removed.

Observed Wserv ordering:
- SVCMISS 0x50 remains during early Wserv startup.
- !Windowserver registers successfully.
- B25 FBS shared-heap handoff/ready markers remain healthy.
- SVCMISS 0x48 remains.
- SVCMISS 0x4A remains.
- EKDATA.DLL loads with UID3 0x100039E0 and runtime code 0x807ABDF8.
- B28 marker:
  [NBOOT2][WSERV_LIBRARY_TYPE] handle=0x400F0007 valid=1 output_mapped=1 uid1=0x10000079 uid2=0x1000008D uid3=0x100039E0
- SVCMISS 0x63 is absent.
- A later Wserv Leave -5 is trapped and startup continues.
- WSERV-INTERNAL 13 is absent.
- Domino 13 is absent.
- StarterServer, tzserver, cntsrv and later UI/application services continue starting.

This validates both sides of the B28 hypothesis:
1. r0=0x400F0007 was the just-loaded EKDATA RLibrary handle.
2. LibraryType must return EKDATA's TUidType; UID3 0x100039E0 matches exactly.

Therefore B28 removes the B27 causal chain:
EKDATA.DLL -> missing LibraryType -> leave -> EWsPanicFailedToInitialise -> WSERV-INTERNAL 13 -> Domino 13.

B26 Exit Emulator behavior is also retained in this trace:
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1
- normal EKA2L1 library enumeration resumes.

Do not infer a complete Nokia UI boot from this validation alone. B28 proves Wserv gets past the former fatal initialization point; the next blocker is later in UIKON/AknCap/Eiksrv startup.

## New blocker exposed after B28

The strongest first-repeatable failure is now Central Repository/FEP initialization, not a Wserv executive call.

Repository:
0x10272618 = KUidFepFrameworkRepository

Authoritative Symbian source:
- SymbianSource/oss.FCL.sf.mw.classicui/lafagnosticuifoundation/cone/inc/coedefkeys.h
- SymbianSource/oss.FCL.sf.mw.classicui/commonuisupport/uikon/srvsrc/eiksrv.cpp
- SymbianSource/oss.FCL.sf.mw.inputmethods/fep/frontendprocessor/source/FEPBCONFIG.CPP
- SymbianSource/oss.FCL.sf.os.persistentdata/persistentstorage/centralrepository/common/inc/operations.h

Eiksrv's CEikServAppUiServer::ConstructL() is expected to:
1. open repository 0x10272618;
2. StartTransaction(EConcurrentReadWriteTransaction);
3. write default FEP state and key data;
4. Set ERepositoryKey_DefaultFepId;
5. CommitTransaction.

The first write after StartTransaction is the default OnState key:
0x1002 = ERepositoryKey_DefaultOnState.

Current EKA2L1 Central Repository behavior is incomplete:
- start_transaction() logs "TransactionStart stubbed" and completes KErrNone but does not activate a transaction;
- cancel_transaction() is also stubbed;
- get_entry(key, write-mode) creates a transaction-local entry only when is_active() is true;
- with the transaction never activated, Set on an absent key returns KErrNotFound;
- cen_rep_transaction_commit exists in the protocol enum but has no implemented handler in the current Central Repository service.

The B28 device trace correlates this directly:
- repo 0x10272618 opens;
- "TransactionStart stubbed";
- the immediately following EikAppUiServerThread path leaves with -1;
- stack contains centralrepository.dll and eiksrv.dll;
- TransactionCancel is then stubbed;
- eiksrvs later self-kills with reason -1.
The sequence repeats on restart.

AknCapServer also shows earlier/repeated Leave -1 paths through centralrepository.dll + cone.dll, consistent with the same FEP/CONE Central Repository state not being initialized.

Symbian's real Central Repository SetSettingL semantics create a setting when it is absent, while preserving type/meta/access-policy rules. A narrow B29 should therefore repair generic transaction/Set semantics rather than hardcode repository 0x10272618 or its keys.

## New SVC observation: 0x2D

A later SVCMISS appears:
svc=0x2D pc=0x80297DC4 lr=0x802A1E8B r0=0xFFFF8001 r1=0x000000FA r2=0x00000004 r3=0x008008D4

Symbian kernel execs.txt maps EPOC slow executive 0x2D to:
ThreadSetProcessPriority(thread_handle, TProcessPriority)

0xFA = 250 = EPriorityBackground.

This SVCMISS occurs after the first AknCap/eiksrvs Central Repository failures. It is therefore an observed compatibility gap, but it is not the first causal blocker in this trace and must not be chosen as B29 merely because it is newly visible.

The previously missing Wserv calls remain:
- 0x50 = WsRegisterThread
- 0x48 = CaptureEventHook
- 0x4A = RequestEvent

B28 proves they are not fatal to Wserv in this device trace. Keep them unpatched until a future trace ties one to a concrete failure.

## B29 decision rule

Preferred investigation target:
CENREP/FEP transaction compatibility.

A correct B29 should be generic and TDD-driven:
- activate transaction state and retain transaction mode;
- make Set-on-missing match Symbian semantics;
- implement CommitTransaction coherently so staged changes become repository state and are persisted/notified correctly;
- make CancelTransaction discard staged changes and clear transaction state;
- preserve B20 ResetAll and every B21-B28 invariant;
- add diagnostics around repo 0x10272618 / keys 0x1001, 0x1002, 0x1004 and 0x1008.

Do not hardcode FEP values, suppress leaves, or implement unrelated SVCs in the same milestone.

## Milestone result

B28: WSERVLIBTYPE1 — DEVICE-VALIDATED.

It fixes the B27 Window Server initialization blocker. The active blocker has moved later into Central Repository/FEP/UIKON initialization.
