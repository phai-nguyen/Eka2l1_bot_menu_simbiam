# NATIVEBOOT2 B43 — TFXSERVERDIAG1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: DIAGNOSTIC ONLY
Functional baseline: B41 WSERVMESSAGEWINEXIT1 remains latest immutable functional milestone

## Scope clarification

This work is interoperability/emulator startup debugging for Nokia 5800/Symbian
firmware inside EKA2L1. It observes guest client/server startup provenance only.

It does **not**:
- attack networks or remote systems;
- bypass access controls;
- deploy malware;
- access external services or devices;
- fabricate authorization or privileges.

B43 preserves the guest-visible `KErrNotFound (-1)` result for a missing
`TfxServer`.

## Device evidence leading to B43

B42 proved that the HWRM/SAServer request is a real ~30-second startup delay but
not the final boot stopper. Startup continues into System GUI and registers
`!EikAppUiServer`.

A stronger later repeated family is:

```text
eiksrvs       -> CreateSession("TfxServer") -> KErrNotFound -> Leave(-1)
akncapserver1 -> CreateSession("TfxServer") -> KErrNotFound -> Leave(-1) -> self-kill
akncapserver2 -> CreateSession("TfxServer") -> KErrNotFound -> Leave(-1) -> self-kill
```

The second akncapserver failure is followed by SYSSTART shutdown handling.

Transition-related firmware components observed nearby include:
- `akntransitionutils.dll`
- `aknlistloadertfx.dll`
- `alfredserver_reg.rsc`

No `TfxServer` registration was observed in B42.

## B43 behavior

B43 is diagnostic-only and instruments exact provenance around the existing
missing-server behavior.

### Exact CreateSession trace

Only when native-phone-boot is active and:

```text
server_name == "TfxServer"
```

B43 emits:

```text
[NBOOT2][TFX_SESSION]
[NBOOT2][TFX_SESSION_FRAME]
[NBOOT2][TFX_SESSION_STACK]
```

The trace records:
- caller process and UID3;
- caller thread;
- message slots / session mode / security pointer;
- PC / LR / SP;
- module + offset for PC/LR where resolvable;
- candidate code addresses from the guest stack.

If the server is absent, B43 records:

```text
phase=missing
behavior=UNCHANGED_KErrNotFound
```

and preserves:

```cpp
return epoc::error_not_found;
```

No fake server or successful session is created.

### Leave correlation

B43 stores the missing-session provenance in thread-local host state. If the
same process and same guest thread subsequently calls `User::Leave(-1)`, it
emits:

```text
[NBOOT2][TFX_LEAVE] correlated=1
```

with the miss PC/LR/SP and current Leave PC/LR.

This correlation is observational only.

### Tfx/Alfred resolution trace

Loader process requests whose names contain Tfx/Alfred and library requests
whose names contain Tfx/Alfred/transition emit:

```text
[NBOOT2][TFX_RESOLVE]
```

with:
- process/library kind;
- request/result phase;
- path/name;
- success/failure;
- caller/spawned process or library handle where available;
- `behavior=OBSERVE_ONLY`.

Server creation also records:

```text
[NBOOT2][TFX_SERVER_REGISTER]
```

for an exact `TfxServer` name or Alfred/Tfx-related creating process.

## Semantic guard

B43 does not:
- create `TfxServer`;
- redirect the missing session to another server;
- return `KErrNone` from the missing-server path;
- change the HWRM B42 pending request;
- alter Wserv, Loader PDD, Leave/TRAP, FEP, SYSSTART, or iOS exit semantics.

## TDD

Canonical RED:

- test contract lineage: `e5945329de4d29c64dc8b5cf3ddc35ef18d9562b`
- interoperability-scope clarification: `f9a865225c6257e7dbdc70a53849f66c9dff5c21`
- RED run/job: `35809951781 / 107019069011`
- B29-B42 apply/tests: PASS
- B20-B28 regressions: PASS
- expected failure:
  `NATIVEBOOT2-B43-TFXSERVERDIAG1-TEST: FAIL: missing in B43 CreateSession runtime marker: [NBOOT2][TFX_SESSION]`

Implementation:

- initial instrumentation: `8b3e6eb2c5ee90e88f49cf20037f5b56e5bb61f1`
- manifest activation: `c019017dd0e19ad959ac9c5ae9831222d3417648`
- manifest-pair repair: `f7fa576943017111f3aa13190a0eefc9f64d4d2c`

The first compiled candidate exposed one build-only issue:
`loader.cpp` dereferenced `config::state` while only its forward declaration
was visible.

- failed compile run/job: `35810185857 / 107019798922`
- exact compiler failure: incomplete type `config::state`
- compilation failures: 1

Final narrow compile fix:

- final code HEAD: `00362ae8faedd6bda130b32ba39d3f051a02ef68`
- adds `#include <config/config.h>` to the reconstructed loader source before B43
  uses `native_phone_boot`.

## Canonical GREEN

- code HEAD: `00362ae8faedd6bda130b32ba39d3f051a02ef68`
- run: `35810358190`
- job: `107020337672`
- FASTBUILD1 manifest: VALID
- B29-B43 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- NOJAVA / MANIC3: PRESERVED

Compiler cache:

- compile requests: 149
- executed: 149
- cache hits: 148
- cache misses: 1
- hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0

## Artifacts

Unsigned IPA SHA-256:

`452346807417961e9c6fa85a7f5fc848b76ff65bb95cc861de1656c819be75c8`

IPA artifact:

- ID: `10729741855`
- ZIP size: 19,899,977 bytes
- ZIP digest:
  `sha256:5b8c50e8e38acae1eed2119d935bfa17f4c210c9c65a9a0ea3e8c3093e804010`
- expires: 2026-10-07

Audit artifact:

- ID: `10729547324`
- digest:
  `sha256:0cb2d06c40e735304f350f03e7be82c11829446d8973ebeb40792281d2975981`
- expires: 2026-10-07

The downloaded IPA was re-hashed locally and matches the CI SHA-256 exactly.

## Device-test acceptance

Install/sign B43 and boot the same Nokia 5800 RM-356 path.

B43 is not expected to make the phone boot farther by itself. It deliberately
keeps the missing `TfxServer` result as `KErrNotFound`.

Collect:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

Primary evidence to inspect:

1. `[NBOOT2][TFX_RESOLVE]` for Tfx/Alfred/transition process/library
   candidates.
2. Each `[NBOOT2][TFX_SESSION] phase=request` and `phase=missing` from
   eiksrvs / akncapserver.
3. `[NBOOT2][TFX_SESSION_FRAME]` and `[NBOOT2][TFX_SESSION_STACK]` module
   provenance.
4. `[NBOOT2][TFX_LEAVE] correlated=1` linking the same guest thread's missing
   TfxServer session to `Leave(-1)`.
5. Any `[NBOOT2][TFX_SERVER_REGISTER]` event, especially an actual
   `TfxServer` registration.
6. B42 `[NBOOT2][SA_HWRM_ABI]` remains present; the ~30-second HWRM delay may
   remain by design.
7. B40 `LOADER_PDD EUART1 result=0` and `!EikAppUiServer` remain healthy.
8. B41 Exit Emulator still completes through `normal_restart_done has_device=1`.

Use the B43 device evidence to decide the next narrow functional fix. Do not
fabricate a TfxServer before the provider/startup contract is identified.
