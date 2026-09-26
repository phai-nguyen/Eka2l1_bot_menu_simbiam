# NATIVEBOOT2 B57 STARTUPGDIORIGIN1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS

## Inputs

B57 logs supplied from the Nokia 5800 RM-356 V60 device run:

- EKA2L1_Persistent(20260924-070220).log
- EKA2L1(20260924-070218).log
- EKA2L1_Persistent-prev.log
- EKA2L1_TakeThis(20260924-070217).log

The full useful boot history is in Persistent-prev / TakeThis.

## Exact Startup GDI origin

B57 records exactly six STARTUP_GDI_ORIGIN events for the visible Startup
0x100058F4 canvas 0x00807AA8. All occur at 13:57:39.894, roughly 116 seconds
before the natural Splash -> Startup handoff.

Exact sequence:

1. SET_BRUSH_STYLE
   - process Startup[100058f4]0003
   - gc_op 0x0D
   - fill_mode 1

2. GDI_BLT
   - gc_op 0x34
   - version 3
   - ws_bitmap 0
   - source_handle 0x0000008A
   - source [0,0,360,640]
   - destination [0,0,0,0] (auto-size)
   - flags 0x08

3. CLEAR_RECT
   - gc_op 0x42
   - rect [0,0,360,640]
   - brush 0xFFFFFFFF

4. SET_BRUSH_STYLE
   - gc_op 0x0D
   - fill_mode 1

5. SET_BRUSH_COLOR
   - gc_op 0x0C
   - brush 0xFFFFFFFF

6. CLEAR
   - gc_op 0x43
   - rect [0,0,360,640]
   - brush 0xFFFFFFFF

This maps directly onto B56's stored sequence:

CLIP -> BLIT -> CLIP -> white RECT -> white RECT.

Therefore the full-screen bitmap and both opaque white rectangles are
guest-requested by Startup.exe through WindowServer graphics-context APIs.
They are not synthesized by the host renderer.

No later STARTUP_GDI_ORIGIN event targets this visible canvas before the
natural handoff at ~13:59:35.680. The white frame is therefore a genuine
Startup waiting frame which was prepared early and later exposed when the
splash group drops away.

## Other post-handoff observations

Immediately after the handoff Startup requests TfxServer and receives the
existing KErrNotFound path. There is no immediate Startup leave after the
missing TfxServer, so this remains secondary evidence rather than a selected
cause.

The same interval contains one unimplemented redraw-canvas opcode 0x90.
EKA2L1's opcode enum maps 0x90 to ClearRedrawStore, but the observed request is
for another Startup canvas/object, not the white target 0x00807AA8. Do not
treat this as the white-screen cause without further evidence.

Home screen also emits many trapped Leave(-5) events but continues creating
windows and loading components afterward; they are not selected as the current
causal boundary.

## Startup synchronization property

The device trace shows Startup defines integer P&S:

- category 0x100058F4
- key 0x00000001

and then attaches to it.

Official Startup source defines this as KPSStartupAppState with states:

- 1 = EStartupAppStateWait
- 2 = EStartupAppStateStartAnimations
- 3 = EStartupAppStateFinished

Startup ConstructL() sets the property to 1 and subscribes to changes. When it
observes state 2, it calls SetWaitingStartupAnimationStartL().

The current B28-derived project baseline was subsequently proven at B58 build
time to already use property::set_int() for the category/key integer setter.
Therefore the older upstream binary-template-set bug is NOT present in the
current project baseline.

Next diagnostic: B58 STARTUPSTATEPS1 readback of category 0x100058F4 key 1.
