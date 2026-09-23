# B50 POSTLOGOCANVAS1 — DEVICE1

Date: 2026-09-24  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — stale splash persists beyond canvas/focus setup

## Device evidence

Files supplied by the user:

- `EKA2L1(20260923-172523).log`
  - size: 54,836 bytes
  - SHA-256:
    `ddc6a29dbbf83337380be4299676f2125ce987fb19932e7e13c79c2d573ca4f0`
- `EKA2L1_Persistent(20260923-172524).log`
  - size: 5,983,124 bytes
  - SHA-256:
    `d997f1f2ccf9bdedcd7aa37afaa600d2fcea48b744ae01847a0141b463a814a3`
- `EKA2L1_TakeThis(20260923-172531).log`
  - size: 5,870,905 bytes
  - SHA-256:
    `515fd00e8ea65e08ab85ab90887a2825f40c72b0a1b6b0f1b98f8f7a12ae7ded`
- `ScreenRecording_09-24-2026 00-20-22_1.mp4`
  - size: 39,510,397 bytes
  - SHA-256:
    `535d87ab491c5e08dc67236e3d76908437bfe45305286043e051b2bbc2a8ae4f`
  - duration: ~259.23 s
  - 510x1108, 30 fps

Current-session TakeThis starts at 00:20:24.616 with
`native_phone_boot=1` and RM-356 V60.0.003.

## Video/log correlation

The recording starts around 00:20:22.

Automated frame sampling finds the black -> white Nokia surface transition at
video t ~= 33.0 s, corresponding to ~00:20:55.

The log at 00:20:55.667 creates/focuses
`S60SplashScreenGroup`, and at 00:20:55.682 creates its canvas.

The Nokia surface remains effectively pixel-identical for the remainder of the
normal boot interval.

Using the central emulator image at video t=40 s as reference, mean absolute
pixel difference remains approximately:

- t=120 s: 0.009
- t=150 s: 0.010
- t=153.8 s, around splash demotion/destruction: 0.011
- t=160 s: 0.011
- t=180 s: 0.013
- t=220 s: 0.009
- t=250 s: 0.012

Maximum per-channel differences in these samples are only 2-4 levels, consistent
with video encoding noise. No visible Startup/Home frame replaces the Nokia
surface.

## Splash

Splash creates one canvas:

```
00:20:55.682
POSTLOGO_CANVAS_CREATE
uid3=0x100059DE
group_id=3
client_handle=0x00700740
win_type=0
group_name=S60SplashScreenGroup
```

It activates successfully:

```
00:20:55.829
POSTLOGO_CANVAS_ACTIVATE
visible=1
physically_seen=0
result=0
```

The activation occurs before later visible-region recomputation; the fact that
the Nokia logo subsequently becomes visible proves that an instantaneous
`physically_seen=0` at activation time is not by itself a rendering failure.

Splash raises its group priority to 1001.

At 00:22:55.833 it explicitly demotes itself:

```
priority 1001 -> -1000
ordinal 0 -> 7
```

and focus changes from splash group 3 to Startup group 63.

It then issues another order change and the splash group is destroyed at
00:22:55.839:

```
POSTLOGO_WG_DESTROY phase=begin
group_id=3
was_focus=0

POSTLOGO_WG_DESTROY phase=end
final_focus_id=63
redraw_region_pending=1
```

Despite this, the video still shows the same Nokia pixels.

## Startup

Startup group 63 exists and becomes the normal focus after splash demotion.

Across Startup processes B50 observes:

- 13 canvas creations;
- 12 canvas activations;
- 10 explicit SetVisible operations.

The final Startup presentation canvas at 00:21:00.152 is:

```
client_handle=0x008E38D4
group_id=63
group_name=61 100058f4 Startup startup
visible=1
physically_seen=0
result=0
```

Two Startup activation events have `visible=1`; all 12 activation-time
`physically_seen` values are 0. The 10 explicit SetVisible events in this
trace all request hidden state on the particular auxiliary canvases observed.

At splash destruction, Startup is the selected focus and remains so through
normal runtime.

## Home screen

Home screen group 75 is healthy and hosts substantial native window content.

Across ailaunch/Home screen B50 observes:

- 23 canvas creations;
- 18 canvas activations;
- 33 explicit SetVisible operations.

Of those 33 SetVisible operations:

- 9 request/show visible state;
- 24 request hidden state.

All 33 instantaneous `physically_seen_after` observations are 0 while splash
is still in front.

Home has several visible/active canvases. Examples:

At 00:21:01.801:

```
client_handle=0x008DCC08
requested=1
visible_after=1
physically_seen_after=0
result=0
```

At 00:21:01.819:

```
POSTLOGO_CANVAS_ACTIVATE
process=Home screen[102750f0]0003
client_handle=0x008F3E8C
group_id=75
visible=1
physically_seen=0
result=0
```

Thus Home screen is not failing to create or activate windows.

No B50 `POSTLOGO_RECEIVEFOCUS` event is emitted for the three target actors;
their focusability in this boot comes from the existing creation/state path
rather than a later explicit ReceiveFocus IPC.

## Teardown-only Home focus remains unchanged

Exit is requested at 00:24:40.101.

Only during teardown, at 00:24:40.134, Startup group 63 is destroyed and
WindowServer switches focus to Home group 75.

Therefore this focus transition remains teardown evidence and must not be
classified as a successful boot transition.

Exit Emulator remains healthy:

```
00:24:40.101 exit_requested
00:24:40.149 os_join_done
```

about 48 ms.

## B50 conclusion

B50 closes the hypothesis that Startup/Home fail simply because their
WindowServer canvases are absent or never activated.

The proven chain is:

```
Nokia splash canvas renders
 -> Startup group/canvases exist
 -> Home group + many canvases exist
 -> visible Home/Startup canvases activate successfully
 -> splash group is demoted
 -> focus changes to Startup
 -> splash group is destroyed
 -> visible-region recomputation is requested
 -> displayed pixels nevertheless remain the Nokia splash
```

The next boundary is therefore between WindowServer recomposition and iOS host
presentation, not firmware content, TFX, xnthemeserver, FileFlush, group
existence, or simple canvas activation.

## B51 selection

B51 DIRECTSCREEN1 is selected.

It must not force Home focus or mutate the guest screen texture.

B51 should:

1. log every actual WindowServer `screen::redraw(driver)` result around the
   splash teardown;
2. draw a tiny animated marker directly on the iOS host swapchain after the
   guest `screen_texture`;
3. advance that marker only when the existing present path already submits a
   frame — no periodic present timer and no forced guest redraw.

Decision matrix:

- marker moves after splash teardown while Nokia pixels stay stale:
  host present is healthy; guest `screen_texture`/recomposition is stale.
- no host present marker/log after splash teardown:
  redraw-to-present scheduling is the first missing stage.
- WindowServer redraw continues with `performed=0`:
  compositor is running but emits no drawable guest content.
- redraw reports `performed=1` and host marker advances while Nokia remains:
  inspect compositor clearing/tree traversal and stale splash texture content
  next.
