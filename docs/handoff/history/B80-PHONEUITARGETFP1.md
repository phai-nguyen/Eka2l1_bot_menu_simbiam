# NATIVEBOOT2 B80 PHONEUITARGETFP1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Purpose

B79 resolved the real near-SP PhoneUIUtils chain but RM-612 control evidence
showed that Nokia production export surfaces can differ from the public
SymbianSource DEF.

B80 therefore identifies code, not guessed symbol names.

## New markers

[NBOOT2][PHONEUI_TARGET_FINGERPRINT]

For every validated in-module B79 target:
- phase
- source / index
- runtime target
- module-relative target offset
- ARM or Thumb state
- mapped flag
- 64-byte FNV-1a hash
- first 32 raw bytes as eight little-endian words

Expected DEVICE1 targets include:
- FileServer: +0x4274, +0x41AC
- CONE14: +0x4350, +0x3A28, +0x3B2E

[NBOOT2][PHONEUI_EXPORT_IDENTITY_CAUTION]

Reports:
- exact RM-356 production export count
- public SymbianSource DEF count 387
- RM-612 control E32-header export count 462
- ordinal_symbol_mapping=UNVERIFIED

[NBOOT2][PHONEUI_EXPORT_SURFACE]

Dumps raw runtime export entries for:
- ordinal 170..190
- ordinal 290..310

This will show exact duplicate/distinct export boundaries around the owner
ordinals used by B79 without importing names from a different build.

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
- PhoneUI export table/code

No set_export hook.
No AddResourceFile injection.
B76 host fix preserved.
B77/B78/B79 diagnostics preserved.
NOJAVA / MANIC3 preserved.

## Build history

Run #249 / 36159200379:
- B80 apply PASS
- B80 test produced a false positive because the test scanned from the B80
  marker to the end of fs.cpp/svc.cpp and encountered an unrelated historical
  ctx->complete().
- compile was not run.
- runtime patch was not implicated.

Test-only correction:
- commit 547807cfba57e7725852cf9e004bf7953c31c5e5
- scopes contract checks to B80-owned identifiers.
- no C++ runtime change.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36159350296
- run number: 250
- job ID: 108151750155
- functional runtime commit: 66c12f809fa41f565e33fa669d47da9984c329d7
- canonical build HEAD: 547807cfba57e7725852cf9e004bf7953c31c5e5
- apply: PASS
- B80 contract: PASS
- all regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 152
- cache hits: 150
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- bootstrap source: B28_CACHE
- bootstrap restore: 19 s
- patch/regression: 3 s
- CMake build: 40 s
- package: 2 s
- total: 83 s
- Xcode 16.4 / Build 16F6
- Apple clang 17
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:
55bb024694a85707909af9a2964b7c46e3547c2cb1e489e4f3f52af5a02b10d2

IPA artifact:
- ID: 10875137070
- ZIP digest:
  sha256:fb1a00c1c115c353ba0e9a64c95cf853636267c8a59ea3655706b7156a87ac7c
- expires: 2026-10-09

Audit artifact:
- ID: 10875072074
- ZIP digest:
  sha256:bde45c02638db2e667f07405a17fce9be0c2d7ee4f2367783247bf87fc12b356
- expires: 2026-10-09

Independent artifact verification:
- IPA SHA matches CI
- Mach-O: arm64
- UUID: CB0EC858-8549-30AF-927B-88DB7450656F
- PHONEUI_TARGET_FINGERPRINT present
- PHONEUI_EXPORT_IDENTITY_CAUTION present
- PHONEUI_EXPORT_SURFACE present

## DEVICE1

1. Install B80 over B79.
2. Start normal Emulator route.
3. Wait for current Phone start-up failed screen.
4. Leave stable 5-10 seconds.
5. Exit Emulator normally.
6. Send:
   - EKA2L1.log
   - EKA2L1_TakeThis.log
   - EKA2L1_Persistent.log
   - Persistent-prev if generated
   - .ips only if host crash occurs

No video is needed unless visible behavior changes.

## B81 decision

From B80 DEVICE1:
1. record exact RM-356 export_count;
2. inspect ordinal 170..190 and 290..310 duplicate boundaries;
3. decode/fingerprint +0x4350 / +0x41AC / +0x4274 as ARM code;
4. fingerprint Thumb +0x3A28 / +0x3B2E;
5. compare semantic instruction patterns against the RM-612 control binary.

Only if this identifies the real resource-registration/API boundary should B81
be a functional fix. Otherwise B81 stays diagnostic.
