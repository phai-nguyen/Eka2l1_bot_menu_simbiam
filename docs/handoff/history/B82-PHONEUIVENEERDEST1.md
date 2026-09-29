# NATIVEBOOT2 B82 PHONEUIVENEERDEST1

Date: 2026-09-26
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Why B82

B81 DEVICE1 corrected the PhoneUIUtils Thumb-2 BLX targets and proved that the
three interesting destinations are ARM interworking veneers:

- PhoneUIUtils +0x46F4 -> literal 0x8038AD15 -> BAFL +0x346C Thumb
- PhoneUIUtils +0x4694 -> CONE-linked veneer region
- PhoneUIUtils +0x46C4 -> literal 0x806ECA17 -> CONE +0x3BAE Thumb

The guest still panics:
Telephone UID3 0x100058B3 -> CONE 14 -> r6=0x1099B02D.

No callhandlingui.r01 open/registration is observed.

Public symbol files are not trusted as production ordinal maps:
- RM-356 PhoneUIUtils production export count: 410
- RM-612 PhoneUIUtils production export count: 462
- public SymbianSource PhoneUIUtils DEF: 387
- public BAFL DEF: 475
- public CONE DEF: 740

B82 therefore follows code identity, not guessed export names.

## B82 behavior

B82 is diagnostic-only.

For each validated B81 ARM target whose first instruction is:

0xE51FF004 = ARM LDR pc,[pc,#-4]

B82:
1. reads the veneer literal at +4;
2. resolves the literal destination against the loaded production codeseg list;
3. records module path, UID3, runtime code base, code size and destination
   module-relative offset;
4. records the production export count;
5. computes the nearest export ownership interval:
   owner ordinal / owner start / owner end / exact-export flag;
6. records the Thumb bit of the destination literal;
7. fingerprints 64 destination bytes with FNV-1a and eight raw 32-bit words.

New markers:

[NBOOT2][PHONEUI_VENEER_DEST]
[NBOOT2][PHONEUI_VENEER_DEST_FP]

B81 corrected BLX decoder markers remain preserved.

## Expected DEVICE1 identity

At minimum B82 should resolve:

- BAFL destination around +0x346C
- CONE destination around +0x3A0C from the +0x4694 veneer family
- CONE destination +0x3BAE from +0x46C4

Exact production export ownership is intentionally left for DEVICE1.

## Behavior contract

No changes to:
- resource registration;
- FileServer result/data/cursor;
- CONE panic;
- SIM/state;
- Starter/SAServer/P&S;
- scheduler/graphics;
- GameMenu;
- PhoneUI export table;
- host lifecycle.

No set_export.
No AddResourceFile.
No forced startup state.
No panic suppression.

B76 host fix preserved.
B81 corrected BLX decode preserved.
NOJAVA / MANIC3 preserved.

## Build history

### Run #252

- run ID: 36202921207
- functional commit: 99c8bd668b8690c607846b60d22d6f3788106935
- B82 apply stopped before compile because the source gate expected the
  contiguous marker PHONEUI_VENEER_DEST_FP while the C++ source constructed it
  from two adjacent string literals.
- no compile/runtime binary was produced.
- this was a diagnostic source-gate false negative, not a guest regression.

Marker-only source-gate correction:
- commit 5d5040db3a21c178afdb1212ed0ab0ba5cfe171d
- no runtime diagnostic logic change.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36202997551
- run number: 253
- job ID: 108293431493
- functional B82 commit: 99c8bd668b8690c607846b60d22d6f3788106935
- canonical build HEAD: 5d5040db3a21c178afdb1212ed0ab0ba5cfe171d
- B82 apply: PASS
- B82 contract: PASS
- all regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- bootstrap source: B28_CACHE
- compile requests/hits/misses: 152/150/2
- cache hit rate: 98.68%
- compilation failures: 0
- bootstrap restore: 31 s
- patch/regression: 5 s
- CMake build: 76 s
- package: 3 s
- total: 144 s
- Xcode 16.4 / Build 16F6
- Apple clang 17.0.0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

1a4248d325da2005e00a0bb4871626f97fb92e0e8a7d09e03e6116cd80de00e2

IPA artifact:
- ID: 10892513677
- artifact ZIP digest:
  sha256:50e4cda7ec192748b5db4541fd6b9e30fa9d903fa2981056d80cd738ba818f2c
- expires: 2026-10-10

Audit artifact:
- ID: 10892319421
- artifact ZIP digest:
  sha256:83e0c672498aac7f4c6af1f6f71a4e0492cc562d252569f64fa8a98f5593c3e2
- expires: 2026-10-10

Independent artifact verification:
- IPA SHA matches CI
- Mach-O: arm64
- UUID: C5E41D9A-FC54-39ED-8FBF-30EA8213C4FC
- PHONEUI_VENEER_DEST present in Mach-O strings
- PHONEUI_VENEER_DEST_FP present in Mach-O strings

## DEVICE1

Install B82 over B81.

1. Open Emulator through the normal RM-356 boot route.
2. Let it reach the current Nokia splash / Phone startup failure condition.
3. Leave it stable for 5-10 seconds.
4. Exit Emulator normally.
5. Send:
   - EKA2L1.log
   - EKA2L1_TakeThis.log
   - EKA2L1_Persistent.log
   - EKA2L1_Persistent-prev.log if generated
   - .ips only if the host app crashes

No video is needed unless visible behavior changes.

## B83 decision gate

Analyze B82 DEVICE1 first.

Required evidence:
- PHONEUI_VENEER_DEST count and all distinct destinations;
- module/UID/base/destination offset;
- exact production export counts for BAFL/CONE;
- owner ordinal/start/end/exact_export;
- destination fingerprints;
- continued CONE14/resource ID behavior;
- clean host exit.

Use public BAFL/CONE sources only as semantic comparison after exact production
boundaries are known.

Do not implement a callhandlingui registration fix until B82 proves the exact
production resource-init/read boundary.
