# B29 CENREPTX1 — Build Snapshot

Date: 2026-09-21
Development branch: nativeboot2-current
Build-tested project HEAD: 7bceb18a337b0977f0f2f68ea0232748dd848392
Status: BUILD-VALIDATED, NOT YET DEVICE-VALIDATED

## Purpose

B28 device validation removed the old Window Server blocker:
EKDATA.DLL -> missing SVC 0x63 LibraryType -> Leave -> WSERV-INTERNAL 13 -> Domino 13.

The next repeatable device failure moved later into UIKON/Eiksrv Central Repository/FEP initialization:
- repository 0x10272618 opens;
- TransactionStart was stubbed;
- the first FEP Set path leaves -1;
- TransactionCancel was stubbed;
- cen_rep_transaction_commit existed in the protocol enum but was neither registered nor routed.

B29 is deliberately generic. It repairs the Central Repository transaction/Set path used by Eiksrv without hardcoding the FEP repository UID, FEP keys, or Nokia-specific values.

## Source validation

Authoritative Symbian sources used:
- SymbianSource/oss.FCL.sf.os.persistentdata/persistentstorage/centralrepository/cenrepcli/clirep.cpp
- SymbianSource/oss.FCL.sf.os.persistentdata/persistentstorage/centralrepository/cenrepsrv/srvsubsess.cpp
- SymbianSource/oss.FCL.sf.os.persistentdata/persistentstorage/centralrepository/common/inc/operations.h
- SymbianSource/oss.FCL.sf.mw.classicui/commonuisupport/uikon/srvsrc/eiksrv.cpp
- SymbianSource/oss.FCL.sf.mw.classicui/lafagnosticuifoundation/cone/inc/coedefkeys.h

Confirmed semantics:
- transaction mode is argument 0;
- CRepository transaction modes are 1=read, 2=concurrent read/write, 3=read/write;
- Start makes the transaction active;
- transaction writes are staged until Commit;
- Cancel discards staged writes;
- Commit writes a TUint32 result through descriptor argument 0;
- SetSettingL creates a missing setting and applies repository metadata/access-policy fallback semantics.

## TDD RED evidence

RED project HEAD:
14a558b2dba4ad0ae4adcbbb86b367e8d60e0db2

Run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35623202762

Run ID:
35623202762

Job ID:
106411071954

Expected failure:
NATIVEBOOT2-B29-CENREPTX1-TEST: FAIL: missing in centralrepo.cpp:
REGISTER_IPC(central_repo_server, redirect_msg_to_session, cen_rep_transaction_commit, "NBOOT2::CenRepTransactionCommit");

Before that expected failure, B20-B28 all passed.

## Implementation

Files:
- apply_nativeboot2_b29_cenreptx1.py
- test_nativeboot2_b29_cenreptx1.py
- ci/fastbuild1_manifest.txt

Implementation scope:
- register and route cen_rep_transaction_commit;
- add commit_transaction();
- fix transaction-mode decoding so the high active-bit half of flags cannot corrupt the low mode bits;
- StartTransaction:
  - validates mode;
  - clears stale staged changes;
  - records read/read-write mode;
  - marks the transaction active;
- get_entry():
  - active transaction reads staged values first;
  - active writes use copy-on-write for existing settings;
  - missing settings receive key + repository default metadata + type=none staging state;
- Set:
  - validates input before creating a missing setting;
  - preserves type mismatch as KErrArgument;
  - creates a missing int/real/string setting;
  - defers notification while transaction is active;
- Commit:
  - installs staged settings into the live repository;
  - clears persisted-deleted markers for recreated keys;
  - clears transaction state;
  - persists once;
  - sends notifications after commit;
  - writes changed_count to descriptor argument 0;
- Cancel:
  - discards staged settings;
  - clears active state.

Runtime markers:
- [NBOOT2][CEN_TX_START]
- [NBOOT2][CEN_SET_CREATE]
- [NBOOT2][CEN_TX_COMMIT]
- [NBOOT2][CEN_TX_CANCEL]

No hardcoded 0x10272618/FEP setting value is present in generic Central Repository code.

Deliberately deferred:
- full multi-client transaction conflict/version semantics;
- full failed-transaction state machine;
- transactional Create/Delete/Move coverage beyond the observed Eiksrv Set path;
- SVC 0x2D;
- SVC 0x48/0x4A/0x50.

## GREEN build evidence

Project HEAD:
7bceb18a337b0977f0f2f68ea0232748dd848392

Run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35623561823

Run ID:
35623561823

Job ID:
106412254328

Conclusion:
SUCCESS

Validation:
- B29 apply PASS
- B29 contract PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- unsigned IPA packaging PASS
- NOJAVA preserved
- MANIC3 preserved

Compile cache statistics:
- compile requests: 9
- compilations: 9
- compilation failures: 0

## IPA

File:
EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa

IPA SHA-256:
25c6846ced19f435523570c2e586fd18031f4c7f05e94e89a50e8f2bace63b70

IPA artifact:
- ID: 10650184716
- name: EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA
- artifact ZIP SHA-256: bb69c7477e763317d8f15507fb174bfa674ac46a79e36cda82c21baab2843a5f
- expires: 2026-10-05

Audit artifact:
- ID: 10650309612
- name: EKA2L1-NATIVEBOOT2-FASTBUILD1-AUDIT
- artifact ZIP SHA-256: 1fac54168a24440de04eeb367511778db157dafbc3e9790c64e213058e6e22ca
- expires: 2026-10-05

## Required device test

The next device log should establish whether B29 removes the first repeatable UIKON/Eiksrv failure.

Expected positive evidence:
- repo 0x10272618 still opens;
- [NBOOT2][CEN_TX_START] appears with mode=2;
- first missing FEP settings generate [NBOOT2][CEN_SET_CREATE], expected keys include the default FEP keyspace 0x1001/0x1002/0x1004/0x1008 as driven by firmware;
- [NBOOT2][CEN_TX_COMMIT] appears instead of TransactionCancel caused by Leave -1;
- eiksrvs no longer follows the same centralrepository.dll/eiksrv.dll Leave -1 path;
- AknCapServer progresses farther if its earlier cone/Central Repository failures shared the same cause;
- B28 [NBOOT2][WSERV_LIBRARY_TYPE] remains healthy;
- WSERV-INTERNAL 13 / Domino 13 remain absent;
- Exit Emulator remains safe.

If the failure moves, identify the first new divergence from this point. Do not automatically patch SVC 0x2D or the old Wserv gaps unless the B29 runtime ordering ties one to the new failure.

## Milestone rule

B29 is currently a development build on nativeboot2-current. Per FASTBUILD1 workflow policy, create the immutable nativeboot2-b29-* milestone branch only after device validation.
