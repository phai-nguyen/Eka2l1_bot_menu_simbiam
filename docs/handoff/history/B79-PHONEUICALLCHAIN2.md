# NATIVEBOOT2 B79 PHONEUICALLCHAIN2

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Purpose

B78 proved real Thumb BL/BLX callsites but did not decode BLX targets.

B79 adds architecture-correct T32 BLX-immediate target decoding and stack
locality classification.

## Exact BLX test vectors

B79 contract validates the exact B78 DEVICE1 halfwords before compilation:

1. callsite 0x80EDA918 / F002 EDC0
   -> target 0x80EDD01C
   -> PhoneUIUtils +0x4274

2. callsite 0x80EDA920 / F002 ED8C
   -> target 0x80EDCF54
   -> PhoneUIUtils +0x41AC

3. callsite 0x80EDC7DC / F000 EE46
   -> target 0x80EDD0F8
   -> PhoneUIUtils +0x4350

BLX PC base follows aligned T32 semantics:
(callsite & ~2) + 4
and target is ARM-state / word aligned.

## Markers

[NBOOT2][PHONEUI_BLX_TARGET]
- explicit BLX decoded target
- target state ARM
- SP delta
- stack locality

[NBOOT2][PHONEUI_CALLCHAIN_EDGE]
- BL or BLX
- target state
- return offset
- target offset
- nearest return export owner
- nearest target export owner
- target scope
- validation=BL_OR_BLX_DECODED

Stack locality:
- NEAR_0_255B
- MID_256_511B
- DEEP_512B_PLUS
- NON_STACK

## Behavior contract

Diagnostic-only.

No changes to:
- resource registration
- FileServer result/data/cursor
- CONE14/panic
- SIM/state
- Starter/SAServer/P&S
- scheduler/graphics
- GameMenu
- host lifecycle
- PhoneUI export table

B76 host fix preserved.
B77/B78 diagnostics preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36151562614
- run number: 248
- job ID: 108125827530
- functional HEAD: ab66e3d33fc39b2a0f2fe326971056e72cdf0f0d
- B79 apply: PASS
- B79 contract: PASS
- all manifest/regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
  - PHONEUI_BLX_TARGET
  - PHONEUI_CALLCHAIN_EDGE
- package/upload: PASS
- compile requests: 152
- cache hits: 150
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- bootstrap source: B28_CACHE
- bootstrap restore: 50 s
- patch/regression: 5 s
- CMake build: 108 s
- package: 3 s
- total audit: 204 s
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:
eb62a6e7a49438ee8cce42dfba04bc494efece657de34667c5bf48c06c0f8f90

IPA artifact:
- ID: 10871089877
- ZIP digest:
  sha256:5c9440efda2d2e8e0a5e88d788181301c8b58d336b4dc87599d0fab2594cffcc
- expires: 2026-10-09

Audit artifact:
- ID: 10871269583
- ZIP digest:
  sha256:669d1f7dc3004a09522d561ffc168c535e90b8c168b217e08368de7b33254a79
- expires: 2026-10-09

Packaged Mach-O UUID:
462E23A0-2CCC-3C5A-B7BA-0D19D1BF0AD6

Independent artifact verification:
- IPA SHA-256 matches CI
- Mach-O is arm64
- PHONEUI_BLX_TARGET marker present
- PHONEUI_CALLCHAIN_EDGE marker present

## DEVICE1

1. Install B79 over B78.
2. Boot normal Emulator path.
3. Wait until Phone start-up failed.
4. Leave stable for 5-10 seconds.
5. Exit Emulator normally.
6. Send:
   - EKA2L1.log
   - EKA2L1_TakeThis.log
   - EKA2L1_Persistent.log
   - Persistent-prev if generated
   - .ips only on host crash

No video is required unless visible behavior changes.

## B80 decision

The decisive B79 evidence is:
- BLX targets +0x4274/+0x41AC/+0x4350;
- their runtime nearest target export owners;
- near-stack CONE14 chain versus deep FileServer context;
- whether the near-stack chain converges on an exact resolver/resource-loading
  routine.

Only then choose either:
1. another narrow internal-function provenance probe, or
2. a functional callhandlingui registration fix at a proven boundary.
