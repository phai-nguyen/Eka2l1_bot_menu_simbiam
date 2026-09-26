# B52 REDRAWSCHED1 — DEVICE1

Date: 2026-09-24  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — natural splash handoff reaches host present, Nokia pixels remain stale

## Device evidence

Files supplied by the user:

- `Log.zip`
  - SHA-256:
    `f41078b610cc7b19099afcc2a9a4b15bfdffa6d2a3435ce5a259ee0eae359850`
  - contains:
    - `EKA2L1.log` — 54,833 bytes
    - `EKA2L1_Persistent.log` — 6,729,123 bytes
    - `EKA2L1_TakeThis.log` — 6,616,908 bytes
- `ScreenRecording_09-24-2026 06-06-25_1.mp4`
  - size: 17,787,845 bytes
  - SHA-256:
    `eafd485e32fdb87c699fa0ea8304c31318f33c015e0bed26064387cc3b7011dd`
  - duration: ~356.37 s
  - 510x1108, 30 fps

TakeThis SHA-256:

`d40c648018cec5fe8db02a01c54e4b612cf4031dc550531a250061183da86c6b`

## Video authority

The recording begins around 06:06:25.

The emulator changes from black to the white Nokia splash at video t ~= 36.5 s.

The enlarged B52 host marker is clearly visible near the upper-left and much
easier to see than B51.

The natural splash handoff occurs in the log at 06:09:02.083, corresponding to
video t ~= 157.1 s.

The Nokia image remains visually unchanged through that transition and for the
rest of the normal test.

Central-emulator crop comparison against video t=40 s is essentially
pixel-identical:

- t=150 s: mean absolute difference 0.0000
- t=157 s: ~0.0013, max channel difference 3
- t=158 s: ~0.00006
- t=180 s: ~0.00010
- t=250 s: ~0.0013
- t=330 s: ~0.00010

Those differences are only video compression noise. The Startup/Home screen
never replaces the Nokia pixels.

## Initial splash redraw/present path

B52 records normal scheduler activity during the initial splash draw.

Example at 06:07:02:

```
REDRAW_SCHED schedule_enter
 -> scan_arm
 -> schedule_done
 -> idle_enter
 -> scan_enter
 -> scan_decision
 -> invoke_enter
 -> DIRECTSCREEN_REDRAW performed=1
 -> DIRECTSCREEN_PRESENT
 -> invoke_redraw_done
 -> invoke_done
```

The host marker advances with those present callbacks.

## Natural splash handoff is reached

At 06:09:02.083 the splash WindowGroup receives its normal order change:

```
process=splashscreen[100059de]0001
object_id=3
requested_priority=-1000
old_priority=1001
new_priority=-1000
old_ordinal=0
new_ordinal=7
result=0
```

Before the focus switch completes, B52 observes:

```
REDRAW_SCHED phase=schedule_enter
focus_id=3
schedule_before=0
callback_scheduled=0

REDRAW_SCHED phase=scan_arm
delay_us=500

REDRAW_SCHED phase=schedule_done
schedule_after=1
callback_scheduled=1
```

Focus then changes normally:

```
S60SplashScreenGroup id=3
 -> Startup id=61
```

The splash issues its second order adjustment and is destroyed at
06:09:02.095:

```
POSTLOGO_WG_DESTROY phase=begin
group_id=3
was_focus=0

POSTLOGO_WG_DESTROY phase=end
final_focus_id=61
redraw_region_pending=1
```

The splash thread exits normally with reason 0.

## Critical result: host presentation occurs at the natural handoff

The B52 iOS host callback presents four additional frames during the natural
transition:

```
06:09:02.085 DIRECTSCREEN_PRESENT frame=171 phase=3
06:09:02.093 DIRECTSCREEN_PRESENT frame=172 phase=0
06:09:02.104 DIRECTSCREEN_PRESENT frame=173 phase=1
06:09:02.117 DIRECTSCREEN_PRESENT frame=174 phase=2
```

Therefore the natural splash demotion does reach the existing iOS present path.

The final host marker is yellow/phase 2 and remains frozen afterward because no
further present occurs during the stationary state.

Most importantly, the central Nokia pixels remain unchanged across all four
handoff presents.

This closes the hypothesis that the natural splash transition simply fails to
reach host presentation.

## B52 instrumentation limitation

B52's scheduler/redraw filters inherited hard-coded WindowServer object IDs
from the B50 device run:

- splash 3
- Startup 63
- Home 75

WindowServer object IDs are not stable across runs. In B52, Startup is id=61.

Therefore after the focus changes to Startup 61, the B52 scheduler and
`DIRECTSCREEN_REDRAW` conditional logging stops matching even though the
iOS callback proves that redraw callbacks/presents do occur.

Do not interpret the missing post-focus scheduler markers as missing scheduler
execution.

This is an instrumentation-filter issue only.

## Exit remains healthy

The user keeps B52 running long enough to pass the natural transition.

Exit occurs much later:

```
06:12:20.544 exit_requested / shutdown_begin
06:12:20.590 os_join_done
06:12:20.726 normal_restart_done has_device=1
```

The OS join is about 46 ms.

## B52 conclusion

B52 is a diagnostic success.

The proven chain is:

```
natural splash SetOrdinalPositionPri
 -> redraw schedule request is created
 -> focus changes Splash -> Startup
 -> splash group is destroyed
 -> redraw_region_pending=1
 -> iOS host receives four new present callbacks
 -> host marker advances through four phases
 -> displayed Nokia pixels remain unchanged
```

Therefore the first unresolved boundary is no longer scheduler delivery or host
present.

The next investigation must inspect the guest WindowServer compositor output
itself:

- whether the color buffer is cleared at the transition;
- which WindowGroups/canvases remain in the tree;
- which canvases are physically visible after recalculation;
- which canvases return `draw() == true`;
- how many canvases actually contribute commands to `screen_texture`.

Important source observation for the next diagnostic:

`screen::redraw(builder, true)` clears the color buffer only when
`FLAG_SERVER_REDRAW_PENDING` is set.

The B52 handoff presents report `screen_flags=0x00000002`, which does not
contain `FLAG_SERVER_REDRAW_PENDING (0x8)`.

That means a redraw can traverse the new tree without clearing old color
pixels first.

This is a candidate explanation for stale Nokia pixels, but it must be proven
against the actual per-canvas draw results before introducing a functional
clear.

## Next milestone

Select B53 COMPOSITOR1 as diagnostic-only.

It should:

1. replace unstable hard-coded WindowGroup IDs with name/UID-based tracing;
2. log the primary-screen compositor frame flags and whether color clear is
   requested;
3. log top-level WindowGroup order at Startup/Home redraws;
4. log each relevant canvas:
   - group/name;
   - flags;
   - absolute rect;
   - visible-region empty/nonempty;
   - is_visible;
   - can_be_physically_seen;
   - `draw()` result;
5. log total canvases and total successful draws for each compositor frame.

Do not clear the color buffer or force Home focus in B53.
