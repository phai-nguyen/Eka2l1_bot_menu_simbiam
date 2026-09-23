# B49 POSTLOGOWSERV1 — DEVICE1

Date: 2026-09-23  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — splash/focus boundary identified

## Device evidence

Files supplied by the user:

- `EKA2L1(20260923-162439).log`
  - size 54,835 bytes
  - SHA-256 `3100fe5a59210fd962d0a4cd9c9784c6f120be9559109df4a466becac59d4e16`
- `EKA2L1_Persistent(20260923-162449).log`
  - size 5,939,949 bytes
  - SHA-256 `2cf1e785c2ed8b37b54763a89f4360cd8c052d69e0feb4a770781bfd769487b0`
- `EKA2L1_TakeThis(10).log`
  - size 5,827,729 bytes
  - SHA-256 `c6cc1503295bbbfee4318a332becba3c2793b7a581841a4a7530a71d114406df`
- `ScreenRecording_09-23-2026 23-19-31_1.mp4`
  - size 34,078,689 bytes
  - SHA-256 `734cb6f32cd081c78ea963125c3c56b2939cc0b0380b2d3f45e507a3665f7adc`
  - duration ~212.63 s
  - 510x1108, 30 fps

Current-session TakeThis begins at 23:19:36.499 with native_phone_boot=1.

## Video/log synchronization

The recording begins at approximately 23:19:31.

Automated frame sampling shows the emulator content changes from black to the
white Nokia startup surface at video t ~= 36.5 s, corresponding to
approximately 23:20:07.5.

That timestamp matches B49 exactly:

```
23:20:07.499 POSTLOGO_WG_CREATE
process=splashscreen[100059de]0001
id=196611          # 0x00030003 WindowServer object handle
client_handle=0x007000F0
focus_request=1

23:20:07.499 POSTLOGO_FOCUS
old_id=0
new_id=3
new_handle=0x007000F0
```

The group is subsequently named:

`S60SplashScreenGroup`.

Therefore the visible white Nokia logo is directly correlated with the native
splashscreen WindowGroup, not merely inferred from timing.

## Startup and Home screen groups both exist behind the splash

Startup creates a focus-requesting WindowGroup at 23:20:10.070:

```
process=startup[100058f4]0001
id=131074
client_handle=0x008000C0
focus_request=1
current_focus_id=3
```

Home screen / ailaunch creates another focus-requesting WindowGroup at
23:20:10.136:

```
process=ailaunch[102750f0]0001
id=131074
client_handle=0x007007E8
focus_request=1
current_focus_id=3
```

The Home screen group becomes discoverable by UID at 23:20:10.738:

```
pattern=* 102750f0 * *
result=75
matched=1
group_client_handle=0x007007E8
group_name=00 102750f0 Home screen
```

So the Home screen WindowGroup exists successfully only ~3.2 s after the Nokia
logo appears. It is not missing.

## Splash group remains focus for about two minutes

All B49 focus selections continue to choose group 3
`S60SplashScreenGroup` through 23:20:11.510.

No normal boot focus transition occurs again until 23:22:07.655.

At that exact time the WindowServer batch targets:

```
op=0x6
obj_handle=0x00030003
```

The object handle is exactly the handle returned when splashscreen created its
WindowGroup.

In the WindowServer opcode table, window opcode 0x06 is
`EWsWinOpSetOrdinalPositionPri`.

The command immediately changes focus:

```
old_id=3
old_name=S60SplashScreenGroup
new_id=61
new_handle=0x008000C0
new_name=61 100058f4 Startup startup
closing_id=0
```

This is a live reordering/focus transition, not destruction fallback.

Twelve milliseconds later, at 23:22:07.667, splashscreen kills its own Main
thread normally with reason 0.

## Decisive video result after splash loses focus

The recording is still visually pixel-identical to the Nokia logo across this
transition.

Representative central-screen frame comparison against video t=40 s:

- t=150 s: mean absolute pixel difference ~= 0.012
- t=156.7 s (the splash -> Startup focus transition): ~= 0.008
- t=165 s: ~= 0.012
- t=205 s: ~= 0.010

Differences are only video-encoding noise. The Nokia surface does not visibly
change after splash loses focus or exits.

The white Nokia surface persists until approximately t=209.5 s, when the user
opens/exits the emulator UI.

This proves that a successful focus handoff by itself is not enough to replace
the displayed splash pixels.

## Home screen never receives normal-run focus

After splash demotion, B49 focus is:

`group 61 / Startup / client_handle 0x008000C0`.

It remains the final focus throughout the normal running interval.

Home screen group 75 receives focus only during emulator teardown:

```
23:23:01.964
old_id=61  Startup
new_id=75  Home screen
closing_id=61
```

Exit was already requested at 23:23:01.935, so this cannot be interpreted as a
successful boot transition.

A few milliseconds later teardown destroys Home screen and then aknnfysrv,
moving focus again.

## Previous milestones remain intact

B47 stock V60 TFX authority remains:

```
repo=0x102818E8
key=0x00000009
result=0
value=0x7FFFFFFF
enabled=0
suppressed=1
```

B48 remains healthy: all 40 observed xnthemeserver FileFlush calls have
`flush_ok=1 completion=0`.

No current-session `KERN-EXEC`, `EIKFAULT_AV`, `EXC_BAD_ACCESS` or host
access violation is present.

Exit Emulator remains healthy:

```
23:23:01.935 exit_requested / shutdown_begin
23:23:01.980 os_join_done
23:23:02.124 normal_restart_done has_device=1
```

## B49 conclusion

B49 is a diagnostic success.

The proven visual/runtime chain is:

```
S60SplashScreenGroup created + focused
 -> Nokia logo becomes visible at the same timestamp
 -> Startup group exists, focus_request=1
 -> Home screen group exists, focus_request=1 and is discoverable
 -> splash remains focus for ~120 s
 -> splash group receives window opcode 0x06 (SetOrdinalPositionPri)
 -> focus switches to Startup
 -> splash process exits normally
 -> rendered Nokia pixels remain unchanged
 -> Startup remains focus
 -> Home screen gets focus only during emulator teardown
```

Do not force Home screen focus yet.

The next diagnostic must distinguish:

1. whether splash/Startup/Home group priority and ReceiveFocus state are
   correct after opcode 0x06;
2. whether Home/Startup canvases are actually created, made visible and
   activated;
3. if those are healthy, whether WindowServer redraw/compositor scheduling is
   leaving the already-destroyed/demoted splash framebuffer stale.

B50 POSTLOGOCANVAS1 is selected for this classification.
