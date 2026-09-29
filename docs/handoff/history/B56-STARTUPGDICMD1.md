# NATIVEBOOT2 B56 STARTUPGDICMD1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B55 DEVICE1 advances the natural Splash -> Startup transition from B54 black to
a stable white guest surface.

B55 reports one non-pending stored segment for the physically-visible Startup
0x100058F4 canvas, but its drawable_segments counter classifies segment state,
not the GDI commands inside it.

B56 is diagnostic-only and inspects the exact stored command stream that B55
replays.

## New markers

- [NBOOT2][STARTUP_GDI_SEGMENT]
- [NBOOT2][STARTUP_GDI_CMD]
- [NBOOT2][STARTUP_GDI_DETAIL]

The trace records:

- segment type
- stored region rect count
- commands per segment
- command opcode
- local pixel-writing classification for DRAW_RECT, DRAW_LINE, DRAW_POLYGON,
  DRAW_BITMAP, DRAW_TEXT and UPDATE_TEXTURE
- DRAW_RECT geometry + RGBA
- DRAW_BITMAP source/destination geometry, flags and cached handles
- DRAW_TEXT box/color/alignment
- CLIP_SINGLE rectangle
- UPDATE_TEXTURE dimensions/size/handles

No redraw, present, focus, z-order, visibility, activation, clear or timer
behavior is changed. B55 STARTUPREPLAY1 remains intact.

## Build history

Early probe runs intentionally exposed two instrumentation defects and were
corrected without changing guest behavior:

- run 158: apply guard looked for STARTUP_REPLAY in winuser.cpp; marker belongs
  to screen.cpp
- run 159: baseline B28 does not contain newer helper
  gdi_store_command_draws_pixels(); replaced with a local opcode switch
- run 161: Python contract contained a literal backslash-n; corrected

Canonical GREEN:

- run ID: 35955643932
- run number: 162
- job: 107493277047
- HEAD: 1c0d14f9ab5a890f409a407d9075ea08ec14ac89
- FASTBUILD manifest APPLY PASS
- regressions PASS
- iOS compile/link PASS
- compilation failures: 0
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

Unsigned IPA SHA-256:

8f935d4a06ccb019ac97f0df3607c3ab90993ab352d0c8bcbf25944d16ef414a

IPA artifact:

- ID: 10790611306
- ZIP digest: sha256:ded6e01a286d1f4b0ee7ab74a8698de3364626525a82407e2bcec51678af3341
- expires: 2026-10-08

Audit artifact:

- ID: 10790198741
- ZIP digest: sha256:7d5232095d11e2a6b96583dfc9acc86511aa04227699074f346a95f887f905fb
- expires: 2026-10-08

## Device-test decision

Use the same RM-356 V60 pair and allow the natural Splash -> Startup handoff.

Primary question:

Startup white surface
 -> stored segment
 -> exact GDI opcodes
 -> actual pixel-writing commands
 -> geometry/color/bitmap/text payload

If the segment is only state/clip commands, the white result is background
behavior and the missing guest drawing path remains upstream of the store.

If it contains a full-screen white DRAW_RECT, identify who recorded that rect
and why later UI content never replaces it.

If it contains bitmap/text/update commands, trace those exact payloads through
gdi_command_builder and texture/font/bitmap resolution next.
