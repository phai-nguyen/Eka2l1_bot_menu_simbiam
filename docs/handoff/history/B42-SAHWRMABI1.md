# NATIVEBOOT2 B42 — SAHWRMABI1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: DIAGNOSTIC ONLY

## Starting point

B41 WSERVMESSAGEWINEXIT1 is the latest device-validated immutable functional
milestone. B40 Loader PDD and B41 MessageWin exit behavior are preserved.

B41 device logs exposed the next earlier startup boundary after healthy
`!EikAppUiServer` registration:

- HWRMServer loads Nokia `lightsadaptation.dll`;
- the plugin sends raw SAServer function `0x2000000A`;
- the historical EKA2L1 generic dispatcher reports it as unimplemented and
  leaves the request outstanding;
- about 30 seconds later SYSSTART starts HWRM failure recovery.

Later SAServer opcode `0x71` is
`StartupAdaptation::EExecuteShutdown = 113` and is downstream of startup
failure. The later `0x5` request is not yet proven and is not modified here.

Exa research did not locate a public Nokia/Symbian source that defines the
proprietary raw SA transport/response ABI for `0x2000000A`. Therefore B42 does
not synthesize a response.

## B42 scope

B42 registers exactly:

```text
0x2000000A -> NBOOT2::SaHwrmAbiProbe
```

Runtime marker:

```text
[NBOOT2][SA_HWRM_ABI]
```

The probe logs:

- raw function;
- low-16 logical function candidate;
- high transport bits;
- IPC flag;
- caller process name;
- caller thread name;
- session unique ID;
- all four raw IPC arguments;
- all four argument types;
- descriptor sizes and maximum sizes;
- descriptor presence;
- up to 32 bytes of each descriptor.

## Diagnostic-only semantic guard

The B42 block deliberately:

- does not write or resize descriptors;
- does not call `ctx.complete(...)`;
- does not complete the B15 pending SA event;
- returns with the request still outstanding.

This preserves the guest-visible historical unknown-IPC behavior while
replacing the generic warning with precise ABI evidence.

No blanket SAServer alias or unknown-IPC behavior change is included.

## Preserved behavior

B42 preserves:

- B19 SA language ABI diagnostics;
- B36 Wserv implicit handle carry;
- B37 Wserv batch signal deferral;
- B40 Loader PDD `EUART1` handling;
- B41 MessageWin wipeout exit guard;
- B34/B26 iOS exit choreography;
- firmware SYSSTART ownership;
- stock Nokia AvkonFep;
- Leave/TRAP and KErrCancel semantics;
- EPOC94 mappings;
- NOJAVA / MANIC3.

## Exa research result

A targeted Exa pass reviewed 12 candidate sources for
`lightsadaptation.dll / SAServer / 0x2000000A`. No reliable public source was
found that defines the exact response contract. Public Symbian material confirms
the general asynchronous client/server model but not this Nokia proprietary raw
transport value. This supports keeping B42 diagnostic-only.

## TDD

Canonical RED:

- test-file commit: `b7ac73c07cacb7ba70c17394f936a37c48af733d`
- RED manifest commit: `51eda041a207e9fb7216ffafe412921da545a700`
- run: `35798200345`
- job: `106982294325`
- B29-B41 apply/tests: PASS
- B20-B28 regressions before B42: PASS
- expected failure:
  `NATIVEBOOT2-B42-SAHWRMABI1-TEST: FAIL: missing in B42 runtime marker: [NBOOT2][SA_HWRM_ABI]`

Canonical GREEN:

- code HEAD: `c57838dbbe9f8b0d66fe5c5b79505eafa7b10da3`
- run: `35798478420`
- job: `106983166866`
- FASTBUILD1 manifest: VALID
- B29-B42 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- binary invariant `[NBOOT2][SA_HWRM_ABI]`: PASS
- IPA package/upload: PASS
- NOJAVA / MANIC3: PRESERVED

## Build audit

- bootstrap source: B28_CACHE
- bootstrap restore: 51 s
- patch/regression: 3 s
- CMake build: 48 s
- package: 3 s
- total: 134 s
- compile requests: 149
- executed: 149
- cache hits: 148
- cache misses: 1
- hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0
- Xcode: 16.4
- Apple clang: 17.0.0

## Artifacts

Unsigned IPA SHA-256:

`d75133e979e6bbea0ed28dbbb9c4b94f246f7ce8afbb991c2333d8349e7d74c7`

IPA artifact:

- ID: `10724414948`
- ZIP digest:
  `sha256:f111831f2719446addd6fc844f83362d2801b5faac5eecaf1059ba36f45da736`
- ZIP size: 19,889,727 bytes
- expires: 2026-10-06

Audit artifact:

- ID: `10724499913`
- digest:
  `sha256:1d165a183533dca7d95f361a8ba790e6f7282330ccdbe7484af79b2725f88366`
- expires: 2026-10-06

## Device-test acceptance

Sign/install B42 and boot the same Nokia 5800 RM-356 path.

B42 is not expected to fix HWRM or remove the approximately 30-second timeout.
The purpose of the device run is to capture the real request ABI.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

First checks:

1. `[NBOOT2][SA_HWRM_ABI]` appears for raw function `0x2000000A`.
2. Caller process/thread/session identify the actual HWRM/light-adaptation path.
3. All four slot types, sizes, maxima and descriptor previews are captured.
4. The old generic
   `Unimplemented IPC call: 0x2000000a for server: SAServer`
   is replaced by the B42 marker.
5. The request remains outstanding; no fabricated success response occurs.
6. B40 still completes `EUART1 result=0`.
7. B41 Exit Emulator remains healthy through
   `os_join_done -> shutdown_done -> normal_restart_done has_device=1`.

Do not promote B42 to an immutable functional milestone. Device evidence from
this diagnostic build is intended to determine whether B43 can safely implement
a narrow HWRM SA response.
