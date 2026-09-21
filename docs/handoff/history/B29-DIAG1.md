# B29-DIAG1 — CenRep Transaction Diagnostic Snapshot

Date: 2026-09-21
Development branch: nativeboot2-current
Functional baseline: B29 CENREPTX1
Diagnostic build-tested project HEAD: f2916297aad315c656c5800f88a7c62d1ce4816a
Status: DEVICE-OBSERVED; B29 FUNCTIONAL HYPOTHESIS VALIDATED

## Purpose

B29-DIAG1 adds diagnostic observability only. It does not change B29 transaction state, Set behavior, persistence, notifications, or any Symbian SVC.

Goal: make the next device log sufficient to identify the first Central Repository divergence without needing another diagnostic rebuild.

## Source grounding

Authoritative Symbian sources and SDK documentation establish the useful transaction boundaries:
- StartTransaction mode/state
- Set key/type/result
- CommitTransaction aKeyInfo / changed-count or failure key
- CancelTransaction rollback path

SymbianSource persistentdata common/inc/operations.h explicitly documents SetSettingL as:
"Set a setting to a new value, create the setting if it does not exist yet".

Some higher-level SDK prose describes Create() as the public API for creating a new key. For B29-DIAG1 this discrepancy is intentionally not resolved by changing semantics; the runtime diagnostics expose whether the FEP path is updating existing keys or exercising missing-key behavior on this firmware.

## TDD RED

RED project HEAD:
18cee3af352bf4df17b3e224f579ecc35e23dede

Run:
35626098291

Expected failure:
NATIVEBOOT2-B29-DIAG1-TEST: FAIL: missing in repo.cpp DIAG1 markers: [NBOOT2][CEN_SET_BEGIN]

This proved the new contract was not already satisfied by B29.

## First GREEN attempt — patcher bug

Run:
35626322869

Failure:
NATIVEBOOT2-B29-DIAG1: integer missing-data diagnostics: expected one anchor, found 3

Root cause:
the initial patcher used a whole-file replace_once() for the common
if (!data.has_value()) block, which legitimately appears once in each
int/real/string Set case.

Fix:
scope each diagnostic replacement to its individual Set case region.
No runtime semantics were changed.

## Final implementation

Files:
- apply_nativeboot2_b29_diag1.py
- test_nativeboot2_b29_diag1.py
- ci/fastbuild1_manifest.txt

Added runtime markers:
- [NBOOT2][CEN_SET_BEGIN]
- [NBOOT2][CEN_SET_RESULT]
- [NBOOT2][CEN_SET_FAIL]
- [NBOOT2][CEN_TX_COMMIT_BEGIN]
- [NBOOT2][CEN_TX_COMMIT_KEY]
- [NBOOT2][CEN_TX_COMMIT_RESULT]
- [NBOOT2][CEN_TX_COMMIT_FAIL]

Existing B29 markers remain:
- [NBOOT2][CEN_TX_START]
- [NBOOT2][CEN_SET_CREATE]
- [NBOOT2][CEN_TX_COMMIT]
- [NBOOT2][CEN_TX_CANCEL]

Diagnostic fields include:
- repository UID
- key
- IPC Set function
- transaction active/mode
- existing yes/no
- existing_type
- requested_type
- created/staged
- failure reason
- completion code
- commit staged count
- per-key type and metadata
- Commit key_info / changed count

No repository UID or FEP key is hardcoded.

## GREEN build evidence

Run:
35626484148

Job:
106421997929

Project HEAD:
f2916297aad315c656c5800f88a7c62d1ce4816a

Conclusion:
SUCCESS

Validation:
- B29 CENREPTX1 contract PASS
- B29-DIAG1 apply PASS
- B29-DIAG1 contract PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA packaging/upload PASS
- NOJAVA preserved
- MANIC3 preserved

FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap_restore_seconds=56
- patch_regression_seconds=0
- cmake_build_seconds=48
- package_seconds=2
- total_seconds=142

sccache:
- compile requests: 9
- cache hits: 8
- cache misses: 1
- hit rate: 88.89%
- compilations: 1
- compilation failures: 0
- cache errors: 0

## IPA

File:
EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa

SHA-256:
b61edcd7721de3298818bd483debd8f186f6eb796aac57e4956e458f6f5996dc

IPA artifact:
- ID: 10652337447
- artifact ZIP SHA-256: 6f0cac8dfd94d4c3079b10bebe7d192dde6651f17d3491ed6017d6122344153a
- expires: 2026-10-05

Audit artifact:
- ID: 10652602353
- artifact ZIP SHA-256: 90505db5ff05ae1444ad5e7e3edbc72aa17e7284d22e3a108d730edac3cc3b85
- expires: 2026-10-05

Post-build binary verification:
the packaged eka2l1 Mach-O contains all B29-DIAG1 marker strings, including SET_BEGIN/RESULT/FAIL and COMMIT_BEGIN/KEY/RESULT/FAIL.

## Device result

The supplied B29 and B29-DIAG1 device logs validate the diagnostic hypothesis.

For repository 0x10272618:
- CEN_TX_START succeeds with mode=2.
- Four FEP settings complete without CEN_SET_FAIL.
- CEN_TX_COMMIT_RESULT reports changed=4, key_info=4, completion=0.
- No CEN_TX_COMMIT_FAIL is observed.
- No CEN_TX_CANCEL follows the successful FEP transaction.
- Settings created during the earlier B29 run are seen as existing during the later DIAG1 run, demonstrating persistence across runs.

The first repeated failure moved after the CenRep transaction:
- optional Fepswitch.exe is not found;
- Eiksrv then attempts to load its UI-specific library;
- EKA2L1 returns KErrNotFound from library loading;
- EikAppUiServerThread leaves -1.

Therefore DIAG1 completed its purpose and B29 CENREPTX1 is device-validated for the CenRep/FEP blocker.

The next diagnostic build is B29-LOADERDIAG1; see:
docs/handoff/history/B29-LOADERDIAG1.md

## Required device log interpretation

For repository 0x10272618, inspect the first sequence around:

[NBOOT2][CEN_TX_START]
[NBOOT2][CEN_SET_BEGIN]
[NBOOT2][CEN_SET_RESULT] or [NBOOT2][CEN_SET_FAIL]
[NBOOT2][CEN_SET_CREATE] when applicable
[NBOOT2][CEN_TX_COMMIT_BEGIN]
[NBOOT2][CEN_TX_COMMIT_KEY]
[NBOOT2][CEN_TX_COMMIT_RESULT] or [NBOOT2][CEN_TX_COMMIT_FAIL]
[NBOOT2][CEN_TX_CANCEL]

Key questions:
- mode should normally be 2 for EConcurrentReadWriteTransaction;
- are FEP keys already present or missing (existing=1/0)?
- does requested_type match existing_type?
- does any Set fail before commit?
- how many staged keys reach Commit?
- does Commit return success with key_info equal to changed count?
- does the old eiksrvs Leave -1 / Cancel path disappear?
- does AknCapServer progress farther?
- do B28 Wserv markers remain healthy?

Do not use this diagnostic build as evidence to patch SVC 0x2D/0x48/0x4A/0x50 unless the device ordering makes one causal.

## Milestone rule

B29-DIAG1 is diagnostic instrumentation on the B29 development candidate.
It is not B30 and does not become an immutable milestone by itself.
Device-test B29+DIAG1 first; only then decide whether B29 is validated or what B30 should change.
