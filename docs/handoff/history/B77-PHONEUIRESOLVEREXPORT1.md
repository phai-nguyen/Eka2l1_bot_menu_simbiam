# NATIVEBOOT2 B77 PHONEUIRESOLVEREXPORT1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Purpose

B76 DEVICE1 closes the host GameMenu and exit regressions.

Guest startup still fails at Telephone CONE14 for resource 0x1099B02D, owned
by callhandlingui.r01.

B75/B76 showed that the repeated PhoneUIUtils +0x5094 value is descriptor/
literal data rather than a proven executing frame.

B77 therefore resolves the exact loaded RM-356 PhoneUIUtils.dll export for:
CPhoneResourceResolverBase::BaseConstructL()

Export ordinal:
182

The resolver uses the actual loaded codeseg and computes:
- runtime PhoneUIUtils code base
- text size
- code size
- ordinal-182 runtime address
- next-higher text export as a conservative function boundary

## Markers

[NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]
- emitted at FileServer phoneui.r01/callhandlingui.r01 contexts
- emitted again at Telephone CONE14
- records base/text/code sizes, export address/offset, next-export boundary

[NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]
- emitted only if PC/LR/register/stack candidate falls inside the bounded
  ordinal-182 function range

[NBOOT2][PHONEUI_LITERAL_PTR]
- explicitly reclassifies +0x5094/+0x50B8 as DESCRIPTOR_LITERAL

[NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]
- confirms bounded deep scans complete

Stack observation is extended to 384 words while preserving the B74 96-word
loop for regression compatibility.

## Behavior contract

Diagnostic-only.

No changes to:
- resource registration
- FileServer data/result/cursor
- CONE14 panic
- Starter/SAServer/P&S
- SIM/state
- scheduler/graphics
- host GameMenu
- host exit/teardown

B76 GAMEMENU_SAFE_TITLE is preserved.
NOJAVA / MANIC3 preserved.

## Build history

Run #245 failed during patch application because the first implementation used
a non-unique svc.cpp anchor.

Run #246 scopes the CONE14 classifier patch specifically to the B71 lambda and
is canonical GREEN.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36143687408
- run number: 246
- job ID: 108099418515
- functional HEAD: 930a94e2fe366d39894a1a81d2ce69608ca933b5
- B77 apply: PASS
- B77 contract: PASS
- manifest/regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
  - PHONEUI_BASECONSTRUCT_EXPORT
  - PHONEUI_BASECONSTRUCT_FRAME
- package/upload: PASS
- compile requests: 152
- cache hits: 150
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- bootstrap source: B28_CACHE
- bootstrap restore: 37 s
- patch/regression: 5 s
- CMake build: 98 s
- package: 2 s
- total audit: 168 s
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:
b6301ef32c19744064b2843fea2ee3d036b0ee921b0c9d056db11140d1567ffc

IPA artifact:
- ID: 10868711638
- ZIP digest:
  sha256:49ff2d58352fa78120e18071562bde4ff3e2ed65a8be8939f32d3bde3461227a
- expires: 2026-10-09

Audit artifact:
- ID: 10868996503
- ZIP digest:
  sha256:d04a5e9742fdd60ad127c427fa0ac8a832b09e2067f9d59bb3c6768199b5b381
- expires: 2026-10-09

Packaged Mach-O UUID:
6348A9D9-F972-31D5-8782-E5E54339224D

## DEVICE1 instructions

1. Install B77 over B76.
2. Boot the normal Emulator path.
3. Wait until the same Phone start-up failed screen appears.
4. Leave stable for 5-10 seconds.
5. Open the three-dot menu once to confirm B76 host fix remains intact.
6. Exit Emulator normally.
7. Send:
   - EKA2L1.log
   - EKA2L1_Persistent.log or Persistent-prev if produced
   - EKA2L1_TakeThis.log
   - .ips only if a crash occurs

Video is not required unless visible startup behavior changes.

## Acceptance / B78 decision

Primary evidence:
- PHONEUI_BASECONSTRUCT_EXPORT must resolve module_found=1 with a nonzero
  ordinal-182 address in both FileServer and CONE14 contexts.
- Check whether PHONEUI_BASECONSTRUCT_FRAME appears before/during phoneui.r01
  I/O and/or in the CONE14 stack.

If ordinal 182 correlates directly with the failing sequence, B78 may restore
the missing callhandlingui registration at that proven PhoneUI resolver
boundary.

If ordinal 182 does not correlate, use the B77 export metadata to identify the
actual neighboring resolver function rather than blindly injecting resources.
