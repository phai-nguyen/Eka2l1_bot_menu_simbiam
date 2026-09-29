# NATIVEBOOT2 B72 PHONEUIRSCIO1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## B71 DEVICE1 selection

B71 reproduces Telephone CONE14 and captures the final panic stack, but no
0x4E738xxx PhoneUI resource ID survives in registers or the 128-word stack.

The matching RM-356 RPKG was parsed again:
- phoneui.r01 size: 28134
- index table offset: 27396
- resource count: 368 / 0x170
- signature base: 0x4E738000
- SHA-256:
  05c419086de5710d361f7d8c910ef5284006b5ee879cb0acb448b8090a7ce9a1

PhoneUIUtils.dll references:
- 0x4E738160
- 0x4E73800A
- 0x4E738019
- 0x4E738156
- 0x4E7380C9

All five records exist in phoneui.r01.

phoneui.exe references 0x4E7380E2 and resource 0xE2 also exists.

Therefore B72 moves the trace earlier to the actual FileServer resource I/O.

## B72 markers

[NBOOT2][PHONEUI_RSC_READ]

Telephone-only, exact path:
Z:\resource\apps\phoneui.r01

Before each read:
- file handle
- EFsrv function
- read position
- requested length
- previous cursor
- file size
- RSC geometry

After each read:
- read position
- clamped requested length
- actual bytes read
- next cursor
- whether the access overlaps the resource index table
- output descriptor address

[NBOOT2][PHONEUI_RSC_SEEK]

Logs:
- handle
- function
- cursor before
- seek mode
- seek offset
- resulting position

## Offline mapping

The exact RPKG index table is retained locally.

phoneui.r01 resource ranges are determined by the 369 16-bit offsets starting
at file offset 27396. Therefore any B72 read of a resource-data position can be
mapped back to a unique resource index; reads into the index table can likewise
be mapped to the queried index entry.

This can distinguish:
1. CONE/BAFL locates and reads an in-range resource, then fails later;
2. it asks for an out-of-range index;
3. it rejects/loses the PhoneUI resource file before any resource-data access.

## Behavior contract

B72 is diagnostic-only.

It does NOT:
- alter read position/length/data;
- alter file cursor semantics;
- alter seek results;
- inject a resource;
- suppress CONE14;
- force state 102;
- force ESimUsable;
- alter Starter/SAServer/P&S/scheduler/graphics/teardown.

B61/B64/B68/B69/B70/B71 remain preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36117855635
- run number: 227
- job ID: 108016063287
- build HEAD: dd76bf33827e56f1731f45810885410d1405d6d4
- manifest: VALID
- B72 apply: PASS
- B72 contract: PASS
- full regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile requests: 151
- cache hits: 150
- cache misses: 1
- cache hit rate: 99.34%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

ef4bb8c5c32c958a6e2a2531524a661eb3e222e12e23535682886094d625c03e

IPA artifact:
- ID: 10855129639
- ZIP digest:
  sha256:4af1b206ea2a9c49d1c120c814801f766afded15786e70266d3a979adc3bf948
- size: 19974004 bytes
- expires: 2026-10-09

Audit artifact:
- ID: 10856435156
- ZIP digest:
  sha256:283d68953becccb1d7c83e234f05399a7d4544f5f9bc81d0ee3f84b7e0398234

## DEVICE1 instructions

Install B72 over B71.

Run the same normal Emulator boot.

If the same Phone start-up failed screen appears, leave it stable 5-10 seconds
then exit through the game-menu/Emulator menu as before.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
- Persistent-prev if produced

Video is only needed if the visible behavior differs from B71.

Also report whether Exit Emulator:
- returns cleanly to EKA2L1 menu, or
- crashes the iOS host.

## B73 decision

Correlate the last PHONEUI_RSC_READ/SEEK operations before
[CONE14_PHONEUI].

Map file offsets against the exact phoneui.r01 index table.

If the last access maps to an in-range record, inspect CONE resource-file
registration/signature ownership around that resource.

If no resource-data read occurs after open/header/index handling, move the next
probe to the CONE resource-file registration/search path.

If an out-of-range resource index is proven, identify the binary/resource
version mismatch and only then implement a compatibility fix.

Do not bypass the Telephone failure or synthesize SIM success.
