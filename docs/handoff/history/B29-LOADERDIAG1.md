# B29-LOADERDIAG1 — Rooted RLibrary Diagnostic Snapshot

Date: 2026-09-22
Development branch: nativeboot2-current
Functional baseline: B29 CENREPTX1 — DEVICE-VALIDATED
Immutable B29 branch: nativeboot2-b29-cenreptx1
Immutable B29 functional commit: 7bceb18a337b0977f0f2f68ea0232748dd848392
Diagnostic build-tested code commit: 9aa612714878541ec4b3f7481516bba00b6d52a4
Status: DEVICE-OBSERVED; ROOTED-NO-DRIVE PATH RESOLUTION CONFIRMED CAUSAL

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

## Device result

The supplied LOADERDIAG1 device logs resolve the decision matrix unambiguously.

Observed in EKA2L1_TakeThis:
- LDR_LIB_REQUEST: 5
- LDR_ROOT_BEGIN: 5
- LDR_ROOT_DIRECT: 5
- LDR_ROOT_MISS: 5
- LDR_LIB_RESULT failure: 5
- LDR_OPEN_FAIL: 0
- LDR_FORMAT: 0
- LDR_PARSE_FAIL: 0
- LDR_CODESEG_RESULT: 0
- LDR_DEP_FAIL: 0

All five repeated failing Eiksrv loads have the same sequence:

[NBOOT2][LDR_LIB_REQUEST]
process=eiksrvs[10003a4a]0001
request_path=\sys\bin\EiksrvUi.dll
rooted_no_drive=1

[NBOOT2][LDR_ROOT_BEGIN]
request=\sys\bin\EiksrvUi.dll
rooted=1
has_drive=0

[NBOOT2][LDR_ROOT_DIRECT]
request=\sys\bin\EiksrvUi.dll
path=\sys\bin\EiksrvUi.dll
has_drive=0
exists=0

[NBOOT2][LDR_ROOT_MISS]
reason=direct_vfs_miss

[NBOOT2][LDR_LIB_RESULT]
success=0
completion=-1

Immediately afterward:
EikAppUiServerThread leaves -1.

The earlier B29 CenRep fix remains healthy in the same trace:
- CEN_TX_COMMIT_RESULT for repo 0x10272618 occurs before every library load attempt.
- CEN_SET_FAIL count = 0.
- CEN_TX_COMMIT_FAIL count = 0.
- B28 WSERV_LIBRARY_TYPE remains present.
- WSERV-INTERNAL 13 and Domino 13 remain absent.

No parser or dependency stage is reached. Therefore parser/image-format handling and dependency resolution are not the current causal blocker.

## Root-cause confirmation against references

Current upstream EKA2L1 contains an explicit fix for this exact class of bug.

Upstream commit:
437b29006bd8a0186f4070c9445f43e98e5c7435

Its commit description states:
"A drive-less absolute path never resolved. Symbian writes an image's path without a drive letter (\sys\bin\foo.dll) and its loader searches the drive list for it. Both of the library manager's entry points opened such a path verbatim instead, so the image was simply not found."

Current upstream lib_manager::load() now detects:
- rooted path
- empty drive/root name

and tries mounted-drive candidates by prefixing each drive before calling the existing load path.

S60 5th Edition RLibrary documentation also defines drive-search behavior for DLL loading and confirms that the loader, not the caller, is responsible for resolving drive candidates in the supported path forms.

This matches the device trace exactly:
the historical B28 bootstrap opens \sys\bin\EiksrvUi.dll verbatim, while the real Symbian path is drive-relative and must be resolved to a mounted drive such as Z:.

## B30 decision

The next functional milestone is now evidence-backed:

B30 candidate:
ROOTEDLIBPATH1

Scope:
- backport only the rooted-no-drive drive-resolution behavior into lib_manager::load();
- reuse the existing load_depend_on_drive() path;
- preserve existing full-path and non-rooted search behavior;
- preserve B29/DIAG1/LOADERDIAG1 diagnostics for the first B30 device test;
- do not batch the newer upstream ROM/E32 classification fix, relocation fixes, dependency changes, or SVC 0x2D/0x48/0x4A/0x50.

The first B30 device test should prove:
1. LDR_ROOT_DIRECT/MISS no longer terminates the request.
2. A drive-qualified candidate is found and reaches LDR_FORMAT / parser / codeseg stages.
3. Ideally LDR_LIB_RESULT success=1 for EiksrvUi.dll.
4. If load then fails later, use the existing LOADERDIAG1 markers to identify the next exact boundary.

## Milestone rule

B29-LOADERDIAG1 remains diagnostic instrumentation only.
It is not an immutable functional milestone.

Its purpose is complete: it proved rooted-no-drive path resolution is the next causal bug.
