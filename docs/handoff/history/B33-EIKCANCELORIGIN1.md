# B33 EIKCANCELORIGIN1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Active development branch: nativeboot2-current

## Why B33 exists

B32 device evidence achieved its diagnostic objective and localized the first
repeatable guest failure to this causal chain:

AknFep initialization
-> User::Leave(KErrCancel / -3)
-> trapped leave with a stable AknFep stack
-> euser.dll null write at 0x10
-> EikAppUiServerThread KERN-EXEC 3.

B32 also disproved SVCMISS 0xE3 as the immediate eiksrvs cause and showed that
the single eiksrvs SVCMISS 0x2D occurs about 32 seconds before the first access
violation. Neither executive is selected as a functional fix.

Full B32 device evidence:
`docs/handoff/history/B32-DEVICE1.md`

## B33 objective

B33 is diagnostic-only.

It identifies which completion path delivers KErrCancel (-3) before AknFep
calls User::Leave(-3), without changing completion values, signal counts,
message lifetime, leave semantics, FEP behavior, SVC mapping, or exception
behavior.

Markers:

- `[NBOOT2][EIKCANCEL_LLE]`
  - native/LLE message_complete path
  - server/session, opcode, raw args, request status
  - client process/thread
  - current process/thread

- `[NBOOT2][EIKCANCEL_HLE]`
  - HLE ipc_context::complete(-3)
  - same ownership/opcode/request-status context

- `[NBOOT2][EIKCANCEL_NOTIFY]`
  - generic notify_info::complete(-3)
  - requester process/thread
  - request-status address

## TDD RED

Contract:
`test_nativeboot2_b33_eikcancelorigin1.py`

RED run:
- run: `35683752870`
- expected conclusion: failure
- purpose: prove the B33 cancellation-origin markers are absent on the B32 baseline

The temporary RED workflow was removed after GREEN verification.

## Implementation

Apply script:
`apply_nativeboot2_b33_eikcancelorigin1.py`

Contract:
`test_nativeboot2_b33_eikcancelorigin1.py`

FASTBUILD1 manifest row:
`apply_nativeboot2_b33_eikcancelorigin1.py|test_nativeboot2_b33_eikcancelorigin1.py`

Final build-tested implementation commit:
`4db183b7a8f522f93057bfae22933f19c770156b`

A pre-GREEN correction changed only the HLE diagnostic anchor to the stable
`ipc_context::complete(int res)` function signature because the B28 bootstrap
legitimately contains older diagnostics inside that function body.

No B33 semantics were changed by this correction.

## Authoritative GREEN build

Run:
`35684075913`

Job:
`106607071205`

Result:
- workflow conclusion: success
- FASTBUILD1 manifest VALID
- B33 EIKCANCELORIGIN1 PASS
- full FASTBUILD1 regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- packaged Mach-O contains:
  - `[NBOOT2][EIKCANCEL_LLE]`
  - `[NBOOT2][EIKCANCEL_HLE]`
  - `[NBOOT2][EIKCANCEL_NOTIFY]`
- IPA package/upload PASS
- audit upload PASS

FASTBUILD1 audit:
- bootstrap_source=B28_CACHE
- bootstrap restore: 37 s
- patch + regression: 1 s
- CMake build: 51 s
- package: 3 s
- total: 119 s
- compile requests: 16
- cache hits: 13
- cache misses: 3
- hit rate: 81.25%
- actual compilations: 3
- compilation failures: 0
- NOJAVA preserved
- MANIC3 preserved

Unsigned IPA:
`EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`

IPA SHA-256:
`c8dd7468aa1d843bbe43cc0cd9f1965e82a15227faf98ca336a85e3d50ada2c8`

The downloaded artifact was independently extracted and reproduced the same
IPA SHA-256.

IPA artifact:
- ID: `10675733488`
- ZIP digest:
  `sha256:89dca7b9d1a1ef2935ef4c5dae5e81e8b4ceb5806b0c4ab71aec798c4ee0535a`
- expires: 2026-10-06

Audit artifact:
- ID: `10675908156`
- ZIP digest:
  `sha256:4b0597d5d250dee67b2369f2a4a3d6215b42fad46c0cf6de6224e3767ca46111`
- expires: 2026-10-06

## Scope exclusions

B33 does NOT:
- change any completion result;
- add/suppress request signals;
- change message reference lifetime;
- change leave/trap handling;
- change FEP selection/initialization;
- implement EPOC94 SVC 0x2D;
- implement/remap SVC 0xE3;
- backport GetModuleNameFromAddress;
- suppress KERN-EXEC 3;
- suppress guest access violations.

B30/B31/B32 behavior and diagnostics remain preserved.

## Device validation plan

Install/sign B33 and boot the Nokia 5800 firmware long enough to reproduce
multiple AknFep / EikAppUiServerThread failure cycles.

Then use the existing B26 safe Exit Emulator path and collect the standard logs.

For each B32 `EIKFAULT_LEAVE leave=-3`, locate the immediately preceding B33
cancellation marker from the same client/request context:

- EIKCANCEL_LLE
- EIKCANCEL_HLE
- EIKCANCEL_NOTIFY

The first consistently correlated origin of KErrCancel becomes the next causal
target. Do not select a functional patch before this device trace.

Do not create an immutable B33 milestone branch until device evidence is
analyzed.
