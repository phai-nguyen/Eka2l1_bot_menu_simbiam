# B29-LOADERDIAG1 — Rooted RLibrary Diagnostic Snapshot

Date: 2026-09-22
Development branch: nativeboot2-current
Functional baseline: B29 CENREPTX1 — DEVICE-VALIDATED
Immutable B29 branch: nativeboot2-b29-cenreptx1
Immutable B29 functional commit: 7bceb18a337b0977f0f2f68ea0232748dd848392
Diagnostic build-tested code commit: 9aa612714878541ec4b3f7481516bba00b6d52a4
Status: BUILD-VALIDATED, DEVICE LOG REQUIRED

## Purpose

The two B29 device logs prove Central Repository/FEP initialization now succeeds and expose the next repeatable failure:

CEN_TX_COMMIT success
-> optional Fepswitch.exe not found
-> RLibrary::Load for the UI-specific server DLL
-> EKA2L1 library load returns KErrNotFound
-> EikAppUiServerThread Leave -1
-> eiksrvs exits

Symbian classicui source confirms Fepswitch KErrNotFound is intentionally ignored, while the following RLibrary::Load error is propagated with User::LeaveIfError.

LOADERDIAG1 is diagnostic-only. It does not change loader search behavior, parser behavior, dependency resolution, codeseg creation, completion codes, or any Symbian SVC.

## Important baseline discovery

The exact B28 FASTBUILD bootstrap source differs from newer upstream EKA2L1.

The cached lib_manager::load() has:
- a codeseg fast path;
- search-path/drive iteration only for paths that are NOT rooted;
- for a rooted path it falls through to a direct:
  if (!io_->exist(lib_path)) return nullptr;
- it does NOT contain the newer upstream rooted-no-drive A:..Z: resolution branch.

This distinction is important because the Symbian UIKON source passes a rooted path without an explicit drive for the UI server DLL.

LOADERDIAG1 intentionally does not add the newer search behavior. It only records the existing B28 behavior so the device trace can prove which condition is hit.

## Source grounding

Authoritative references:
- SymbianSource/oss.FCL.sf.mw.classicui/commonuisupport/uikon/srvsrc/eiksrv.cpp
- SymbianSource/oss.FCL.sf.mw.classicui/uifw/EikStd/srvuisrc/EIKSRVUI.MMP
- EKA2L1/EKA2L1 src/emu/services/src/loader/loader.cpp
- EKA2L1/EKA2L1 src/emu/kernel/src/libmanager.cpp

Symbian sequence:
1. Commit FEP Central Repository transaction.
2. Try Fepswitch.exe; ignore KErrNotFound because it is optional.
3. Build the UI DLL path from the Eiksrvs drive plus a rooted sys/bin name.
4. RLibrary::Load it with the expected TUidType.
5. Leave on any library-load error.

## TDD RED

Contract:
test_nativeboot2_b29_loaderdiag1.py

RED project commit:
7bc90e789e53a1add30e69a1e92789308865fe0e

Run:
35661287453

Job:
106536866299

Expected failure after B20-B29/DIAG1 passed:
NATIVEBOOT2-B29-LOADERDIAG1-TEST: FAIL: missing in loader.cpp: [NBOOT2][LDR_LIB_REQUEST]

## Baseline-inspection iterations

First GREEN attempt:
- run 35661492473
- patcher stopped before compile
- reason: exact lib_manager::load() entry anchor did not match the historical B28 cache

Second GREEN attempt:
- run 35661698478
- patcher stopped before compile
- reason: format/parse block assumed newer upstream loader logic that is absent from B28 cache

Systematic inspection:
- one-time run 35661849022
- job 106538675951
- restored the exact B28 bootstrap cache and printed the relevant libmanager.cpp / loader.cpp regions
- inspection workflow was deleted immediately after use

The inspection invalidated two initial test assumptions:
- there is no rooted-no-drive candidate loop in this baseline;
- there is no ROFS staging step in this baseline load path.

The diagnostic contract was therefore corrected to test the actual B28 behavior rather than inventing stages that do not exist.

## Final implementation

Files:
- apply_nativeboot2_b29_loaderdiag1.py
- test_nativeboot2_b29_loaderdiag1.py
- ci/fastbuild1_manifest.txt

Generic runtime markers:
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

Diagnostic fields include:
- requesting process
- requested path
- rooted-no-drive state
- direct VFS exists=0/1
- ROM/E32 branch classification
- ROM-backed state
- parser failure
- codeseg result
- dependency name
- parent codeseg path
- final loader completion code

No target DLL filename or UID is hardcoded.

## GREEN build evidence

Run:
35662229010

Job:
106539879024

Build-tested code commit:
9aa612714878541ec4b3f7481516bba00b6d52a4

Conclusion:
SUCCESS

Validation:
- B29 CENREPTX1 contract PASS
- B29-DIAG1 contract PASS
- B29-LOADERDIAG1 apply PASS
- B29-LOADERDIAG1 contract PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA packaging/upload PASS
- NOJAVA preserved
- MANIC3 preserved

FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap_restore_seconds=29
- patch_regression_seconds=2
- cmake_build_seconds=71
- package_seconds=2
- total_seconds=137

sccache:
- compile requests: 11
- cache hits: 9
- cache misses: 2
- hit rate: 81.82%
- compilations: 2

## IPA

File:
EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa

SHA-256:
b748c0e009721b37f24e89003fc1a2a0a8e64e158379a633ece78b0e94576d7c

IPA artifact:
- ID: 10668485125
- artifact ZIP SHA-256: 850219186c73d92e0153c31f7d2b28110cf41eb7dc7e6d9c69f1081431142d1a
- expires: 2026-10-05

Audit artifact:
- ID: 10668055503
- artifact ZIP SHA-256: 5cc3328e8728a5fc064eebbf95cef289eac4c9a8e56874fda9a01878e7ce6b8e
- expires: 2026-10-05

Post-build verification:
the packaged EKA2L1 Mach-O contains all ten LOADERDIAG1 marker strings.

## Required device interpretation

For the first failing Eiksrv library load, capture the complete sequence around:
- LDR_LIB_REQUEST / LDR_LIB_RESULT
- LDR_ROOT_BEGIN
- LDR_ROOT_DIRECT
- LDR_ROOT_MISS
- LDR_OPEN_FAIL
- LDR_FORMAT
- LDR_PARSE_FAIL
- LDR_CODESEG_RESULT
- LDR_DEP_FAIL

Decision matrix:
- ROOT_DIRECT exists=0 + ROOT_MISS:
  the current rooted-no-drive VFS lookup is the blocker.
- exists=1 + PARSE_FAIL:
  parser/image-format path is the blocker.
- exists=1 + CODESEG_RESULT success=0 + DEP_FAIL:
  dependency resolution is the blocker.
- exists=1 + CODESEG_RESULT success=0 without DEP_FAIL:
  inspect codeseg/image construction next.
- LIB_RESULT success=1:
  the failure moved beyond library loading; follow the first later divergence.

Do not implement the newer upstream rooted-path search, dependency workarounds, or SVC 0x2D/0x48/0x4A/0x50 until the device log establishes which branch is causal.

## Milestone rule

B29-LOADERDIAG1 is diagnostic instrumentation only.
It is not B30 and is not an immutable functional milestone.
