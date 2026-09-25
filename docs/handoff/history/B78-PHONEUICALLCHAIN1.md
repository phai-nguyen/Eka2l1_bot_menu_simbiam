# NATIVEBOOT2 B78 PHONEUICALLCHAIN1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Purpose

B77 resolves BaseConstructL correctly at PhoneUIUtils +0x1BC8 but captures no
BaseConstructL frame in 384-word FileServer/CONE14 scans.

B77 nevertheless exposes several nearby PhoneUIUtils pointers. B71 CODE16
inspection proves that some are real Thumb BL return addresses while others
are data/stale pointers.

B78 therefore replaces image-range pointer heuristics with instruction-
validated call-chain evidence.

## Runtime validation

For each PhoneUIUtils candidate B78:
1. requires Thumb return bit;
2. reads the two halfwords immediately before the return address;
3. accepts the candidate only if those halfwords encode Thumb BL/BLX;
4. decodes Thumb BL targets;
5. maps the return address to the nearest PhoneUIUtils export range;
6. maps decoded in-module targets to the nearest PhoneUIUtils export range.

Key resolver exports mapped explicitly:
- 181 CPhoneMainResourceResolver::Instance
- 182 CPhoneResourceResolverBase::BaseConstructL
- 307 CPhoneResourceResolverBase::ResolveResourceID
- 308 CPhoneResourceResolverBase::IsTelephonyFeatureSupported

## Markers

[NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]
- runtime addresses/ranges for the four key resolver exports

[NBOOT2][PHONEUI_CALLSITE]
- phase FILESERVER or CONE14
- source/index
- raw return and module offset
- validated callsite address/offset
- BL/BLX halfwords and kind
- decoded target/offset where available
- return-owner ordinal/range
- target-owner ordinal/range
- validation=REAL_CALLSITE

B77 markers remain active.

## Behavior contract

Diagnostic-only.

No changes to:
- resource registration
- FileServer result/data/cursor
- CONE14
- SIM/state
- Starter/SAServer/P&S
- scheduler/graphics
- GameMenu
- host exit/teardown
- PhoneUI export table / guest code

No set_export hooking is used.

B76 host fix preserved.
B77 export-182 diagnostics preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36148877670
- run number: 247
- job ID: 108116800815
- functional HEAD: d652d10cd68661274900734af79c1ef62ce8fbe4
- B78 apply: PASS
- B78 contract: PASS
- manifest/regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
  - PHONEUI_RESOLVER_EXPORT_MAP
  - PHONEUI_CALLSITE
- package/upload: PASS
- compile requests: 152
- cache hits: 150
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- bootstrap source: B28_CACHE
- bootstrap restore: 29 s
- patch/regression: 6 s
- CMake build: 57 s
- package: 3 s
- total audit: 126 s
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:
42b454f7c2cdfb28e0fb646b2c16f1c451c13a9d62bef3bc2ed50ba11b1a6002

IPA artifact:
- ID: 10870706328
- ZIP digest:
  sha256:3a9c91d6532f95280ff482d478f3fc850b518d1cfefbf725069380a6cc07ba5b
- expires: 2026-10-09

Audit artifact:
- ID: 10870628680
- ZIP digest:
  sha256:463463f1b27873aee77bd95d75f892ef70c6c7c98d65322f4e9b59473ba95cb6
- expires: 2026-10-09

Packaged Mach-O UUID:
ABB63FE7-BA91-3DB6-9A61-C1595754B938

Independent artifact verification:
- IPA SHA-256 matches CI
- packaged Mach-O contains PHONEUI_RESOLVER_EXPORT_MAP
- packaged Mach-O contains PHONEUI_CALLSITE

## DEVICE1

1. Install B78 over B77.
2. Boot normal Emulator path.
3. Wait for the current Phone start-up failed screen.
4. Leave it stable for 5-10 seconds.
5. Exit Emulator normally.
6. Send:
   - EKA2L1.log
   - EKA2L1_TakeThis.log
   - EKA2L1_Persistent.log
   - Persistent-prev if produced
   - .ips only if a host crash appears

Video is unnecessary unless visible behavior changes.

## B79 decision

Primary B78 evidence:
- PHONEUI_CALLSITE entries at FILESERVER and CONE14;
- return_owner_ordinal and target_owner_ordinal;
- decoded target offsets for the +0x1BC0/+0x3A38/+0x3B4C chain;
- whether any validated edge reaches resolver exports 181/182/307/308 or a
  stable neighboring internal routine.

Only after this call chain is identified should the next build restore the
missing callhandlingui registration or intercept an exact proven missing
resolver step.
