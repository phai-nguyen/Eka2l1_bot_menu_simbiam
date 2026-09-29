# B51 DIRECTSCREEN1 — DEVICE1

Date: 2026-09-24  
Status: DEVICE-OBSERVED; VISUAL DIAGNOSTIC SUCCESS — redraw/present activity captured, but test ended before the known ~120 s splash handoff

## Device evidence

User-supplied files:

- `EKA2L1(20260923-221311).log`
  - size: 54,837 bytes
  - SHA-256:
    `8ebc32c6f7aaa8f19f6c5505fa3c3a5fe3f688ec6b6ecce0ac563074a3b9f173`
- `EKA2L1_Persistent(20260923-221327).log`
  - size: 6,097,232 bytes
  - SHA-256:
    `d558d121377a202e0986d4af354e2a9dd140ae325a2783e07209f4b632d76329`
- `EKA2L1_TakeThis(20260923-221329).log`
  - size: 5,985,009 bytes
  - SHA-256:
    `541ceae02acc8a4bc29bf947062f9dfabe9543227da1a66aa9fa1b1911689c28`
- `ScreenRecording_09-24-2026 05-04-28_1.mp4`
  - size: 17,181,011 bytes
  - SHA-256:
    `25d009f32e825359ef93e9a6cadbe797cb8cc2f22af55d6009aca92d88b33379`
  - duration: ~116.9 s
  - 510x1108, 30 fps

## B51 host marker is real and visible

The video shows the four-phase host-only square in the upper-left host surface.

Because B51 draws a 15x15 marker in the 1125x2436 renderbuffer, it becomes only
about 7x7 pixels in the 510x1108 screen recording. The user explicitly reported
that it is too small and difficult to see.

Frame inspection confirms the marker changes position/color during the active
present interval and then freezes.

Representative video samples:

- t=35.5 s: cyan marker
- t=36.0 s: magenta marker
- t=36.5 s: green marker
- t=37.5 s: cyan marker
- t=39.0 s: green marker
- t=40.0 s: magenta marker
- t=42.0 s onward: same cyan position/color remains frozen

Therefore the B51 visual marker behaves exactly like the runtime present
counter.

## Exact redraw/present interval

TakeThis contains:

- 170 `DIRECTSCREEN_PRESENT` events;
- 170 `DIRECTSCREEN_REDRAW phase=enter`;
- 170 `DIRECTSCREEN_REDRAW phase=result`.

All 170 redraw results report:

`performed=1`.

First WindowServer redraw:

```
05:05:04.095
DIRECTSCREEN_REDRAW phase=enter
focus_id=3
focus_name=S60SplashScreenGroup

05:05:04.095
DIRECTSCREEN_REDRAW phase=result
performed=1
callback_next=1
```

First host present:

```
05:05:04.096
DIRECTSCREEN_PRESENT
frame=0
phase=0
screen_texture=0x00000002
marker=[6,6,15,15]
```

Last WindowServer redraw:

```
05:05:10.422
DIRECTSCREEN_REDRAW phase=result
performed=1
focus_id=3
focus_name=S60SplashScreenGroup
callback_next=1
```

Last host present:

```
05:05:10.422
DIRECTSCREEN_PRESENT
frame=169
phase=1
screen_texture=0x00000002
marker=[25,6,15,15]
```

No `DIRECTSCREEN_REDRAW` and no `DIRECTSCREEN_PRESENT` occur after
05:05:10.422 in this test.

This is why the visual square freezes in the recording.

## Important test-duration qualification

This B51 recording exits earlier than the natural splash transition observed in
B49/B50.

B51:

- first B51 splash redraw/present: ~05:05:04;
- user requests Exit Emulator: 05:06:24.425;
- elapsed after first splash frame: ~80.3 s.

The WindowGroup destruction seen at 05:06:24.428 is therefore teardown caused
by Exit Emulator:

```
05:06:24.425 BRIDGE_EXIT_PHASE phase=exit_requested

05:06:24.428
POSTLOGO_WG_DESTROY
process=splashscreen
group_id=3
was_focus=1

05:06:24.428
POSTLOGO_WG_DESTROY phase=end
final_focus_id=63
redraw_region_pending=1
```

B50's normal device run showed the splash demotion only around 120 s after the
Nokia surface became active. Therefore B51 did **not** run long enough to test
the critical natural splash -> Startup redraw/present boundary.

Do not misclassify the absence of presents from 05:05:10 to 05:06:24 as a
confirmed scheduler fault: while the splash is static, no further redraw may be
required.

## What B51 does prove

B51 proves all of the following:

1. WindowServer composition works during splash startup.
2. Every B51-observed redraw emitted content (`performed=1`).
3. The iOS callback/present path works during that same interval.
4. Host marker movement is coupled one-for-one with existing WindowServer
   redraw callbacks.
5. When WindowServer redraw callbacks stop, the host marker freezes exactly as
   designed.
6. This particular run does not reach the natural ~120 s splash demotion, so it
   cannot yet classify whether the scheduler wakes correctly at that handoff.

## Next diagnostic — B52 REDRAWSCHED1

B52 should keep B51's direct-screen probe but:

- enlarge the visual marker substantially;
- trace animation_scheduler::schedule / schedule_scans / idle_callback /
  scan_for_redraw / invoke_due_animation around splash, Startup and Home focus;
- preserve every existing scheduling decision and timing;
- not force a redraw or present.

Device test must continue for at least **150 seconds after the Nokia logo first
appears** before Exit Emulator, so the normal ~120 s splash handoff is captured.

Primary question:

```
natural splash demotion
 -> WindowServer move/order marks screen dirty
 -> animation_scheduler::schedule ?
 -> scan callback ?
 -> invoke_due_animation ?
 -> screen::redraw ?
 -> iOS present ?
```

If the chain stops, the first missing phase becomes the B53 functional
candidate. Do not patch scheduler behavior before B52 device evidence.
