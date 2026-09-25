# NATIVEBOOT2 B78 PHONEUICALLCHAIN1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; REAL CALLSITES PROVEN; BLX TARGETS UNRESOLVED
Selected route: NORMAL BOOT + SIM PRESENT

## Device inputs

- EKA2L1(20260925-145718).log
- EKA2L1_Persistent(20260925-145718).log
- EKA2L1_Persistent-prev(9).log
- EKA2L1_TakeThis(20260925-145734).log

Visible result remains:
Phone start-up failed.
Contact the retailer.

Host exit remains clean:
BRIDGE_EXIT_PHASE normal_restart_done has_device=1.

## Marker counts

TakeThis:
- PHONEUI_CALLSITE: 13
- PHONEUI_RESOLVER_EXPORT_MAP: 168
- PHONEUI_BASECONSTRUCT_EXPORT: 42
- PHONEUI_BASECONSTRUCT_FRAME: 0
- CONE14_PHONEUI: 1
- callhandlingui.r01: 0

## Proven FileServer callsites

At phoneui.r01 FileServer IPC:

1. return +0x1B74
   - source DEEP_STACK index 137
   - callsite +0x1B70
   - halfwords F002 EDC0
   - THUMB_BLX
   - B78 target unresolved
   - nearest return export owner 178

2. return +0x1B7C
   - source DEEP_STACK index 137 or 175
   - callsite +0x1B78
   - halfwords F002 ED8C
   - THUMB_BLX
   - B78 target unresolved
   - nearest return export owner 178

These are 548+ and 700+ bytes above saved SP and therefore are deep stack
context, not automatically live frames.

## Proven CONE14 callsites

At Telephone CONE14:

1. stack index 23
   - return +0x3A38
   - callsite +0x3A34
   - halfwords F000 EE46
   - THUMB_BLX
   - B78 target unresolved
   - nearest return export owner 298

2. stack index 35
   - return +0x3B4C
   - callsite +0x3B48
   - THUMB_BL
   - decoded target +0x3A28
   - return/target nearest export owner 298

3. stack index 47
   - return +0x1BC0
   - callsite +0x1BBC
   - THUMB_BL
   - decoded target +0x3B2E
   - return nearest export owner 178
   - target nearest export owner 298

All three are within 188 bytes of CONE14 SP and therefore are near-stack
candidates. This makes them materially stronger than the FileServer
DEEP_STACK entries.

## Guest blocker

Telephone still self-panics CONE 14 with r6=0x1099B02D.
callhandlingui.r01 is still never opened/registered before panic.

B78 remains diagnostic-only.

## B79 decision

B79 must:
- decode Thumb BLX immediate targets;
- validate exact B78 vectors before compile;
- report SP delta / stack locality;
- emit compact call-chain edges;
- keep all guest behavior unchanged.

Architecture-correct BLX expected targets for the three B78 vectors:
- +0x1B70 F002 EDC0 -> +0x4274
- +0x1B78 F002 ED8C -> +0x41AC
- +0x3A34 F000 EE46 -> +0x4350

These are expected runtime diagnostics to verify on DEVICE1.
