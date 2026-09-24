# B53 COMPOSITORTREE1 — DEVICE1

Date: 2026-09-24  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — Startup redraws are presented with color_clear=0 while stale Nokia pixels remain

## Device evidence

User-supplied files:

- `EKA2L1(20260924-003917).log`
  - size: 54,837 bytes
  - SHA-256:
    `0492522e8fcea1c57e57f27330378315f659c274bb1af4f1b0fc088452c890fd`
- `EKA2L1_Persistent(20260924-003923).log`
  - size: 6,776,273 bytes
  - SHA-256:
    `e6f7e8fda62f3eeb4ae0862cea6e8a2119cfe603570472c600e75cb893fd0efd`
- `EKA2L1_TakeThis(20260924-003923).log`
  - size: 6,664,051 bytes
  - SHA-256:
    `b48fd36ce3f194042701ecb403c84403f7fff4f56146af23628e6633fa6348f6`
- `ScreenRecording_09-24-2026 07-34-06_1.mp4`
  - size: 38,700,642 bytes
  - SHA-256:
    `e95d2b6c9b6ebc4abae371c4d79d144b45cdae763e496254b025b1b2b3a9bdbf`
  - duration: ~250.90 s
  - video: 510x1108, 30 fps

## Duration / transition authority

The recording begins around 07:34:06.

First B52/B53 host-present frame appears at:

```
07:34:42.199
DIRECTSCREEN_PRESENT frame=0
```

The natural Splash -> Startup transition occurs at:

```
07:36:42.166
```

roughly 156.2 s into the recording, i.e. about 120 s after the first Nokia
present.

The user keeps the emulator running until:

```
07:38:14.139 exit_requested
```

roughly 248.1 s into the recording.

Therefore B53 fully captures the natural handoff and a long post-handoff
stationary period.

## Video result

The Nokia surface is unchanged through the natural transition.

Central-emulator crop comparison against video t=40 s gives approximately:

- t=150 s: mean absolute difference 0.0110, max 5
- t=157 s: mean absolute difference 0.0052, max 3
- t=158 s: mean absolute difference 0.0078, max 3
- t=160 s: mean absolute difference 0.0115, max 3
- t=180 s: mean absolute difference 0.0116, max 4

These are encoding-level differences only. The guest image remains the Nokia
splash.

## Natural handoff

At 07:36:42.166:

```
POSTLOGO_ORDERPRI
process=splashscreen[100059de]0001
requested_priority=-1000
old_priority=1001
new_priority=-1000
old_ordinal=0
new_ordinal=7
result=0
```

Focus changes to the Startup WindowGroup:

```
POSTLOGO_FOCUS phase=final
focus_id=63
focus_handle=0x008000C0
focus_name=61\0 100058f4 \0 Startup \0 startup
```

Unlike B52's hard-coded diagnostic filter, B53 tracks this by group name/UID,
so the post-focus compositor frames are captured correctly.

## Four Startup compositor frames are observed

B53 captures frames 173-176 immediately after the natural focus switch.

All four have the same essential state:

```
focus = Startup 0x100058F4
flags = 0x00000002
visible_recalc_before = 1
visible_recalc_after = 0
server_redraw_pending = 0
client_redraw_pending = 0
color_clear = 0
need_bind = 1
```

Frame 173:

```
07:36:42.167 COMPOSITOR_FRAME phase=begin
07:36:42.168 COMPOSITOR_FRAME phase=end
total_clients=93
total_visible=11
total_physically_seen=1
total_drawn=1
```

Frames 174-176:

```
total_clients=92
total_visible=10
total_physically_seen=1
total_drawn=1
```

## Exactly one canvas is physically visible and reports draw_result=1

For every Startup compositor frame, the only physically-visible and drawn
canvas is:

```
group_id=63
group_name=61\0 100058f4 \0 Startup \0 startup
canvas_handle=0x00807AA8
canvas_priority=0
flags=0x0000200E
win_type=0
abs=[0,0,360,640]
visible=1
visible_region_empty=0
physically_seen=1
draw_result=1
```

This is a full-screen 360x640 Startup canvas.

Home screen exists behind Startup:

```
group_id=75
name=41\0 102750f0 \0 Home screen
priority=0
ordinal=4
```

but its full-screen canvas:

```
canvas_handle=0x008DCC08
abs=[0,0,360,640]
visible=1
visible_region_empty=1
physically_seen=0
draw_result=0
```

does not contribute to these frames.

## Group order

For frames 173-176 the top-level group order starts:

```
index 0: WindowGroup708730 priority=999
index 1: WindowGroup70312C priority=750
index 2: Startup        priority=0 ordinal=2  < focus
index 3: EiksrvBackdrop priority=0 ordinal=3
index 4: Home screen     priority=0 ordinal=4
index 5: SysAp           priority=0 ordinal=5
...
```

The splash WindowGroup is no longer in the traced post-focus group chain.

Therefore the stale Nokia image is not caused by the splash WindowGroup still
being composited on top after the transition.

## Host presentation remains alive

The Startup compositor frames are followed by host presents, including:

```
07:36:42.168 DIRECTSCREEN_PRESENT
07:36:42.175 DIRECTSCREEN_PRESENT
07:36:42.186 DIRECTSCREEN_PRESENT frame=173
07:36:42.197 DIRECTSCREEN_PRESENT frame=174
```

The host marker advances, but the Nokia guest pixels remain unchanged.

Thus the proven chain is:

```
natural splash demotion
 -> focus Startup
 -> visible-region recalculation
 -> Startup compositor frame
 -> exactly one full-screen Startup canvas is physically visible
 -> canvas draw() reports true
 -> no color-buffer clear
 -> host presents
 -> Nokia pixels remain
```

## Critical interpretation

`draw_result=1` proves that the canvas draw function returned true, but does
not yet prove that the canvas emitted pixel-writing GPU commands covering the
whole screen.

The active compositor performs color clear only when
`FLAG_SERVER_REDRAW_PENDING` is set. In all four Startup handoff frames that
bit is absent.

The old Nokia pixels therefore remain in `screen_texture` unless the Startup
canvas actually overwrites them.

B53 narrows the first plausible stale-pixel mechanism to:

```
screen_texture contains Nokia splash
 -> Splash group removed
 -> Startup becomes physically visible
 -> server redraw pending = 0
 -> no color clear
 -> Startup draw path may emit no effective full-screen pixel overwrite
 -> old Nokia pixels survive
 -> iOS presents stale screen_texture
```

Before making a permanent fix, inspect the exact active B28
`redraw_msg_canvas::draw()` semantics and then run a one-shot controlled clear
experiment.

## Next milestone candidate

B54 TRANSITIONCLEAR1:

- only at the first primary-screen transition into Startup 0x100058F4;
- only if `FLAG_SERVER_REDRAW_PENDING` is absent;
- add the color-buffer bit to the existing clear call for that one frame;
- do not force redraw, present, focus, visibility, or z-order;
- preserve B51-B53 diagnostics;
- emit `[NBOOT2][TRANSITION_CLEAR]`.

Expected diagnostic result:

- Nokia disappears / screen changes:
  stale color-buffer retention is confirmed.
- Nokia remains even after the explicit one-frame screen-texture clear:
  old pixels originate from another render path/surface and the hypothesis is
  rejected.

Do not promote the one-shot clear to a permanent behavior until device evidence.
