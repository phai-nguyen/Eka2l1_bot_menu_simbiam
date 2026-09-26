# NATIVEBOOT2 B79 PHONEUICALLCHAIN2 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; BLX TARGETS RESOLVED; NEAR-SP CHAIN PROVEN
Selected route: NORMAL BOOT + SIM PRESENT

## Device files

- EKA2L1(20260925-160601).log
- EKA2L1_Persistent(20260925-160603).log
- EKA2L1_Persistent-prev(10).log
- EKA2L1_TakeThis(20260925-160609).log

Visible blocker remains:
Phone start-up failed.
Contact the retailer.

## Marker counts

TakeThis:
- PHONEUI_BLX_TARGET: 11
- PHONEUI_CALLCHAIN_EDGE: 13
- PHONEUI_CALLSITE: 13
- PHONEUI_RESOLVER_EXPORT_MAP: 168
- PHONEUI_BASECONSTRUCT_EXPORT: 42
- PHONEUI_BASECONSTRUCT_FRAME: 0
- PHONEUI_RES_MATCH2: 41
- CONE14_PHONEUI: 1
- callhandlingui.r01 string/open marker: 0

## FileServer context

Validated deep-stack edges:

1. source DEEP_STACK index 137
   - sp_delta 0x224 (548 bytes)
   - return +0x1B74
   - callsite +0x1B70
   - THUMB_BLX
   - target ARM +0x4274
   - return owner ordinal 178
   - target owner ordinal 298

2. source DEEP_STACK index 137/175
   - sp_delta 0x224 / 0x2BC (548 / 700 bytes)
   - return +0x1B7C
   - callsite +0x1B78
   - THUMB_BLX
   - target ARM +0x41AC
   - return owner ordinal 178
   - target owner ordinal 298

These are real instruction callsites but are deep saved context, so they are not
treated as the strongest live failure frames.

## CONE14 near-SP chain

Telephone remains:
- UID3 0x100058B3
- reason 14
- category CONE
- r6 0x1099B02D

Three validated PhoneUIUtils edges are all within 188 bytes of SP:

1. stack index 23
   - sp_delta 0x5C (92 bytes)
   - callsite +0x3A34
   - return +0x3A38
   - THUMB_BLX
   - target ARM +0x4350
   - nearest owner 298

2. stack index 35
   - sp_delta 0x8C (140 bytes)
   - callsite +0x3B48
   - return +0x3B4C
   - THUMB_BL
   - target Thumb +0x3A28
   - nearest owner 298

3. stack index 47
   - sp_delta 0xBC (188 bytes)
   - callsite +0x1BBC
   - return +0x1BC0
   - THUMB_BL
   - target Thumb +0x3B2E
   - return owner 178
   - target owner 298

Control-flow shape:

owner-178 routine
    -> Thumb +0x3B2E
        -> Thumb +0x3A28
            -> ARM +0x4350

This near-SP chain is now the primary PhoneUI provenance evidence.

## Code-window confirmation

Existing CONE14_CODE16 windows confirm:
- +0x3A28 begins with Thumb prologue B5F3 B085.
- +0x3A34 instruction pair is F000 EE46 (BLX).
- +0x3B2E begins with Thumb prologue B571 B087.
- +0x3B48 pair is F7FF FF6E (BL).
- +0x1BBC pair is F001 FFB7 (BL).

The code at +0x1BC8 begins a different Thumb routine (B510...), so the
+0x1BBC -> +0x3B2E edge belongs to the preceding routine.

## RM-612 control correlation

RM-612 control firmware proves:
- phoneui.exe UID3 0x100058B3 is shared;
- callhandlingui resource namespace 0x1099B000 is shared;
- resource 0x1099B02D exists at index 0x2D;
- the production C6 PhoneUIUtils export count reported by its E32 header is
  462, while the public SymbianSource DEF has 387 entries.

Therefore nearest-export ordinal labels remain useful as runtime boundaries,
but public ordinal->symbol names must not be treated as proven across Nokia
production builds.

## Host lifecycle

Normal exit is healthy:
shutdown -> normal restart completes with has_device=1.

No new host crash evidence was supplied.

## Decision

Do not make B80 a functional resource-registration hook.

Selected B80:
PHONEUITARGETFP1

B80 must:
- fingerprint exact runtime target code for validated B79 edges;
- expose the RM-356 production PhoneUIUtils export count;
- dump raw export offsets around 170..190 and 290..310;
- explicitly mark public DEF symbol mapping UNVERIFIED;
- preserve all guest behavior.

Only after B80 DEVICE1 should a functional resource-registration fix be
considered.
