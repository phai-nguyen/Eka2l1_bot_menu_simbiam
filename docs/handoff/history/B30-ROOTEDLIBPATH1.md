# B30 ROOTEDLIBPATH1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Active development branch: nativeboot2-current

## Purpose

B29-LOADERDIAG1 device evidence proved that Eiksrv repeatedly requests:

`\\sys\\bin\\EiksrvUi.dll`

with a rooted path but no drive. The historical B28/B29 loader tested that string
as a direct VFS path, observed `exists=0`, emitted `LDR_ROOT_MISS`, and returned
`KErrNotFound` before file open, image parsing, codeseg creation, or dependency
resolution.

B30 fixes only that causal boundary.

## Reference evidence

Upstream EKA2L1 commit:

`437b29006bd8a0186f4070c9445f43e98e5c7435`

describes the same defect:

"A drive-less absolute path never resolved."

Its `lib_manager::load()` fix recognizes a rooted path whose drive/root name is
empty, prefixes drive candidates, checks existence, and calls the existing
drive-qualified load path.

S60 5th Edition RLibrary documentation confirms that DLL loading uses drive-aware
search semantics and that executable DLLs reside under `\\sys\\bin\\`.

B30 intentionally backports only the `lib_manager::load()` rooted-no-drive
resolution. It does not import the same upstream batch's ROM/E32 classification,
relocation, lifetime, executive-table, dependency, or trampoline changes.

## Implementation

Apply script:

`apply_nativeboot2_b30_rootedlibpath1.py`

Contract:

`test_nativeboot2_b30_rootedlibpath1.py`

FASTBUILD manifest row:

`apply_nativeboot2_b30_rootedlibpath1.py|test_nativeboot2_b30_rootedlibpath1.py`

Behavior:
- reuse the existing `nativeboot2_root_diag` predicate from LOADERDIAG1;
- for rooted-no-drive paths, iterate drive A: through Z: as in the upstream fix;
- construct `<drive>:<rooted path>`;
- probe candidate existence once;
- call existing `load_depend_on_drive(candidate, is_driver_lib)`;
- on success set the codeseg full path to the drive-qualified candidate and return;
- if an existing candidate is not loadable, continue searching;
- if all drives fail, return null;
- ordinary rooted paths with an explicit drive and non-rooted search behavior remain unchanged.

New generic device markers:
- `[NBOOT2][LDR_ROOT_CANDIDATE]`
- `[NBOOT2][LDR_ROOT_RESOLVED]`
- `[NBOOT2][LDR_ROOT_EXHAUSTED]`

B29 LOADERDIAG1 markers remain compiled for the first B30 device test.

## TDD evidence

Focused RED run:

`35665850841`

Job:

`106551322423`

Expected failure after applying the complete B29 stack and before B30 implementation:

`NATIVEBOOT2-B30-ROOTEDLIBPATH1-TEST: FAIL: missing in libmanager.cpp B30 rooted-no-drive resolution: std::u16string candidate(1, drive_to_char16(drv));`

This establishes that the B30 contract did not already pass on the B29 baseline.

An intermediate build run `35666010666` reached the B30 apply successfully but
the source contract required the literal form `if (io_->exist(candidate))`.
The implementation deliberately probes existence once into
`candidate_exists` for both logging and branching. The contract was corrected
to test that equivalent single-probe behavior instead of a particular spelling.
No guest implementation change was required for that failure.

The temporary RED workflow was removed after the RED proof.

## Final GREEN build

Run:

`35666140887`

Job:

`106552222745`

Build-tested code commit:

`58a6178a53f9ddd8f4edbb5b3788d25131b9d4f9`

Result:
- B29 CENREPTX1 PASS
- B29-DIAG1 PASS
- B29-LOADERDIAG1 PASS
- B30 ROOTEDLIBPATH1 PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariant step PASS, including B30 resolved/exhausted markers
- package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

sccache:
- compile requests: 11
- cache hits: 10
- cache misses: 1
- hit rate: 90.91%
- actual compilations: 1

Unsigned IPA:

`EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`

IPA SHA-256:

`e93aeedfae3d9d7d033e7c1e15374bac74ba584ed5becd264a0a05dc3cd41e67`

IPA artifact:
- ID: 10669182381
- size: 19,874,899 bytes
- ZIP digest: `sha256:98e4dae0e680af2538c1d0215ff11e3972fd6b1aacfc2445d11ee8f29474a413`
- expires: 2026-10-05

Audit artifact:
- ID: 10669247230
- ZIP digest: `sha256:dd975141c66820a11fb3b8daf6532d591d4981c8fbfb9b09fbc9c8e2818ed8f3`
- expires: 2026-10-05

## Preserved scope

B30 does not change:
- firmware SYSSTART startup ownership;
- native fbserv startup/rendezvous;
- B25 FBS shared-heap handoff;
- B26 safe iOS Exit Emulator path;
- B27 Wserv panic diagnostics;
- B28 LibraryType;
- B29 CenRep transaction/Set compatibility;
- B29-DIAG1 / LOADERDIAG1 diagnostics;
- ROM/E32 image classification;
- dependency resolver behavior;
- relocation behavior;
- SVC 0x2D/0x48/0x4A/0x50;
- NOJAVA / MANIC3.

No EiksrvUi DLL name or UID is hardcoded in the loader fix.

## Device validation

For the first B30 device log, inspect the first rooted Eiksrv library request.

Expected progress:
1. `LDR_LIB_REQUEST request_path=\\sys\\bin\\EiksrvUi.dll rooted_no_drive=1`.
2. `LDR_ROOT_BEGIN`.
3. One or more `LDR_ROOT_CANDIDATE` lines for an existing drive-qualified path.
4. Preferably `LDR_ROOT_RESOLVED ... success=1`.
5. `LDR_LIB_RESULT ... success=1 completion=0`.

The old causal sequence:

`LDR_ROOT_DIRECT exists=0 -> LDR_ROOT_MISS -> LDR_LIB_RESULT success=0 -> EikAppUiServerThread Leave -1`

must no longer terminate the rooted-no-drive request.

If B30 reaches `LDR_FORMAT`, `LDR_PARSE_FAIL`, `LDR_CODESEG_RESULT`, or
`LDR_DEP_FAIL`, use the first new boundary as the next causal target. Do not
preemptively import the upstream ROM/E32 classification change or patch the
observed SVC gaps.
