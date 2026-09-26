# NATIVEBOOT2 B56 STARTUPGDICMD1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS

## Inputs

- Nokia 5800 RM-356 V60 runtime
- B56 STARTUPGDICMD1
- Logs:
  - EKA2L1(20260924-044558).log
  - EKA2L1_Persistent(20260924-044602).log
  - EKA2L1_TakeThis(20260924-044600).log
- Recording:
  - ScreenRecording_09-24-2026 11-39-21_1.mp4

## Visual result

The B55 visual result is reproduced.

Around the natural Splash -> Startup transition, approximately 160-161 seconds
into the recording, the NOKIA logo disappears and the display becomes a stable
blank white surface.

The transition aligns with the B56/B55 replay markers at 11:42:01.492-493.

## Exact stored Startup command stream

For the physically-visible Startup 0x100058F4 canvas:

- canvas handle: 0x00807AA8
- abs: [0,0,360,640]
- one stored segment
- segment type: 2 (redraw)
- region_rects: 1
- commands: 5
- commands classified as pixel-writing: 3

Exact order:

1. opcode 6 — CLIP_SINGLE
   - rect [0,0,360,640]

2. opcode 4 — DRAW_BITMAP
   - dest [0,0,0,0]
   - source [0,0,360,640]
   - flags 0x00000008 (BLIT)
   - main_drv 0
   - mask_drv 0

3. opcode 6 — CLIP_SINGLE
   - rect [0,0,360,640]

4. opcode 1 — DRAW_RECT
   - rect [0,0,360,640]
   - RGBA [255,255,255,255]

5. opcode 1 — DRAW_RECT
   - rect [0,0,360,640]
   - RGBA [255,255,255,255]

This directly explains the white result: the stored command stream explicitly
contains two opaque full-screen white rectangles after the full-screen bitmap
BLIT.

## Timing

The target Startup canvas 0x00807AA8 is created at:

11:40:05.217

and activated at:

11:40:05.219

The natural Splash -> Startup replay occurs at:

11:42:01.492

So the stored content exists roughly 116.3 seconds before it becomes visible.

Around target-canvas creation the firmware also opens:

z:\resource\apps\startup.mbm

This is a strong correlation with the stored full-screen bitmap, but B56 does
not prove that the replayed bitmap originates from that file.

## Decision

The next boundary is no longer compositor, focus, clear, or segment replay.

The next question is the origin of the five stored commands:

- which guest graphics-context opcode creates the BLIT;
- whether the two white rectangles are CLEAR, CLEAR_RECT, or DRAW_RECT;
- which process/thread records them;
- what brush state produces white;
- whether later Startup drawing ever replaces them before the natural handoff.

Selected next diagnostic:

B57 STARTUPGDIORIGIN1.
