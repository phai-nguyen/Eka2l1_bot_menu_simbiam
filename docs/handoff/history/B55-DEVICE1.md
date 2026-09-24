# NATIVEBOOT2 B55 STARTUPREPLAY1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; CONTROLLED EXPERIMENT SUCCESS; WHITE STARTUP SURFACE REACHED

## Inputs

- Nokia 5800 RM-356 V60 runtime
- B55 STARTUPREPLAY1
- Logs:
  - EKA2L1(20260924-041059).log
  - EKA2L1_Persistent(20260924-041104).log
  - EKA2L1_TakeThis(20260924-041115).log
- Recording:
  - ScreenRecording_09-24-2026 10-35-43_1.mp4

## Device result

The visual result advances beyond B54.

B54 changed the retained Nokia splash to black at the natural Splash -> Startup
handoff. B55 changes that result again: the Nokia logo disappears and the
guest display becomes a stable white full-screen surface, visually resembling
a later phase of a Nokia startup sequence.

The transition aligns with the B55 one-shot replay event.

At 10:38:24.685 focus moves:

S60SplashScreenGroup id=3 -> Startup id=63 (UID 0x100058F4)

At 10:38:24.686:

- TRANSITION_CLEAR frame=173 fires
- STARTUP_REPLAY frame=173 fires
- flags_before=0x00000003
- flags_after=0x0000000B
- SERVER_REDRAW_PENDING is set for the one compositor pass

At 10:38:24.687:

- Startup canvas handle=0x00807AA8
- abs=[0,0,360,640]
- physically visible
- segments=1
- B55 drawable_segments=1
- background_region_empty=1
- clear_color_enable=1

Frame 173 then reports:

- server_redraw_pending=1
- color_clear=1
- total_physically_seen=1
- total_drawn=1

The host presents frames 171-174 immediately around the transition.

The recording changes from the white Nokia-logo splash to a blank white surface
at the same natural handoff and remains white afterward.

## Important interpretation correction

B55's field named drawable_segments counts stored segments whose type is not
gdi_store_command_segment_pending_redraw. It does NOT count pixel-writing GDI
commands inside the segment.

Therefore B55 proves:

1. the one-shot Startup server replay changes real guest output;
2. Startup owns one stored non-pending segment;
3. replaying the Startup store produces a white result instead of B54 black;
4. the next boundary is the command stream inside that one segment.

It does not yet prove which stored opcode creates the white surface or whether
the store contains the expected later Startup UI content.

## Next selected diagnostic

B56 STARTUPGDICMD1.

Trace, without changing behavior:

- stored segment type / region / command count
- every stored command opcode
- whether each opcode can write pixels
- bounded details for DRAW_RECT / DRAW_BITMAP / DRAW_TEXT /
  CLIP_SINGLE / UPDATE_TEXTURE

Do not force Home focus, add timers, or add another redraw before B56 device
evidence.
