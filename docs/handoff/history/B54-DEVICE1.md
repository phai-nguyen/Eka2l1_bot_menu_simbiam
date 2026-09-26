# B54 TRANSITIONCLEAR1 — DEVICE1

Date: 2026-09-24  
Status: DEVICE-OBSERVED; CONTROLLED EXPERIMENT SUCCESS — stale Nokia pixels are retained color-buffer content

## Device evidence

User-supplied files:

- `EKA2L1(20260924-020411).log`
  - size: 54,834 bytes
  - SHA-256:
    `6bd682e11d3f73a340923976bb5766aba6cdd8d278844f949c8ef9bb69af3b53`
- `EKA2L1_Persistent(20260924-020417).log`
  - size: 6,769,174 bytes
  - SHA-256:
    `6bb123f83e5595901c3a1b804f1c14aca172c540bbc58e17675a6411eef0d31c`
- `EKA2L1_TakeThis(20260924-020417).log`
  - size: 6,656,955 bytes
  - SHA-256:
    `9ee0e03885c8f7a3f6fadd31d4bcfc9621ea027fc313f5cdfbce841bff777ac1`
- `ScreenRecording_09-24-2026 08-33-15_1.mp4`
  - size: 25,440,520 bytes
  - SHA-256:
    `51a6c743a41ee9732d37ffb1959238d5f9fc8c38048d0fb0d764bd39e774bb3d`
  - duration: ~414.63 s
  - 510x1108, 30 fps

## Decisive visual result

The B54 recording remains on the normal white Nokia splash through video
t ~= 154.3 s.

At approximately t ~= 154.4 s the guest display becomes black.

Representative full-frame mean pixel values:

- t=154.0 s: ~205.92
- t=154.3 s: ~205.92
- t=154.4 s: ~2.51
- t=154.5 s: ~2.52
- t=155.0 s: ~2.54
- t=180 s: ~2.49
- t=250 s: ~2.48

The black state persists through the normal post-handoff interval.

The recording filename/time and runtime log align this black transition with the
natural Splash -> Startup handoff at ~08:35:49.576.

## B54 one-shot clear fires exactly once

At 08:35:49.576:

```
[NBOOT2][TRANSITION_CLEAR]
frame=173
screen=0
focus_id=61
focus_name=61 100058f4 Startup startup
flags=0x00000003
visible_recalc_before=1
server_redraw_pending=0
action=ADD_COLOR_BIT_TO_EXISTING_CLEAR
scope=ONE_STARTUP_FOCUS_EDGE
```

The same compositor frame then reports:

```
COMPOSITOR_FRAME phase=begin
frame=173
focus=Startup
flags=0x00000002
visible_recalc_before=1
visible_recalc_after=0
server_redraw_pending=0
client_redraw_pending=0
color_clear=1
```

Frames 174-176 return to:

`color_clear=0`.

Therefore B54's one-shot clear scope is working as designed.

## Natural focus transition is normal

The splash group demotes at 08:35:49.576:

```
requested_priority=-1000
old_priority=1001
new_priority=-1000
old_ordinal=0
new_ordinal=7
```

WindowServer focus changes:

```
S60SplashScreenGroup id=3
 -> Startup id=61
```

The splash WindowGroup is destroyed at 08:35:49.588 with:

`final_focus_id=61`.

## Startup canvas still exists after clear

B54 preserves B53's compositor evidence.

Frames 174-176 contain the full-screen Startup canvas:

```
group_id=61
group_name=61 100058f4 Startup startup
canvas_handle=0x00807AA8
abs=[0,0,360,640]
visible=1
visible_region_empty=0
physically_seen=1
draw_result=1
```

Home screen exists behind Startup but is not physically visible.

## Host presentation is alive after clear

The natural transition is followed by:

```
08:35:49.579 DIRECTSCREEN_PRESENT frame=171
08:35:49.587 DIRECTSCREEN_PRESENT frame=172
08:35:49.598 DIRECTSCREEN_PRESENT frame=173
08:35:49.611 DIRECTSCREEN_PRESENT frame=174
```

Therefore the black screen is not caused by losing the iOS present path.

## B54 conclusion

B54 confirms the previous Nokia image was retained color-buffer content in the
guest screen texture.

The clear removes it immediately.

The remaining problem is now much narrower:

```
old Nokia screen_texture pixels
 -> B54 one-shot clear
 -> pixels become black
 -> Startup is focus
 -> full-screen Startup canvas is physically visible
 -> draw() reports true
 -> no actual Startup pixels replace black
```

Inspection of the active B28 `redraw_msg_canvas::draw()` explains why
`draw_result=1` is not proof of pixel output:

```
if SERVER_REDRAW_PENDING:
    replay stored redraw segments

if CLIENT_REDRAW_PENDING:
    replay queued client commands

return true
```

At the B54 transition both pending bits are zero. Therefore the full-screen
Startup canvas can return true without emitting any pixel-writing command.

## Next milestone

B55 STARTUPREPLAY1 is selected as a controlled functional experiment.

At exactly the same one-shot Startup focus edge proven by B54, B55 sets:

`FLAG_SERVER_REDRAW_PENDING`

for that compositor pass.

This uses the existing WindowServer path to replay stored redraw segments for
the physically visible Startup canvas.

It does not force a new redraw or present and does not alter focus/z-order.

B55 also records the Startup canvas stored segment count and drawable segment
count.

Primary result:

- Startup/Home UI appears: retained stored redraw commands were the missing
  transition mechanism.
- screen changes but remains incomplete: continue from the first missing
  redraw/client-pending stage.
- still black with drawable segments > 0: inspect segment execution/output.
- still black with drawable_segments=0: Startup has no replayable pixels;
  move to client-redraw/invalidation path.
