# B54 TRANSITIONCLEAR1 — BUILD SNAPSHOT

Date: 2026-09-24  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection from B53 DEVICE1

Full device snapshot:

`docs/handoff/history/B53-DEVICE1.md`

B53 captures the natural Nokia splash -> Startup transition and proves:

- Startup becomes focus;
- visible regions are recalculated;
- the splash WindowGroup is no longer present in the traced post-focus group chain;
- exactly one Startup canvas is physically visible;
- that canvas covers the full 360x640 screen;
- `draw_result=1`;
- `server_redraw_pending=0`;
- `client_redraw_pending=0`;
- `color_clear=0`;
- iOS host presents the resulting frames;
- the Nokia pixels remain unchanged.

The full-screen Startup canvas is:

```
group UID: 0x100058F4
canvas_handle=0x00807AA8
abs=[0,0,360,640]
visible=1
visible_region_empty=0
physically_seen=1
draw_result=1
```

Frames 173-176 all show the same pattern.

## Active B28 draw semantics inspected

An inspection workflow read the exact B28 bootstrap source used by FASTBUILD.

`redraw_msg_canvas::draw()`:

1. returns false only when the canvas is not physically visible or has zero size;
2. replays stored segments only under
   `FLAG_SERVER_REDRAW_PENDING`;
3. consumes pending client drawing only under
   `FLAG_CLIENT_REDRAW_PENDING`;
4. then returns `true`.

Therefore `draw_result=1` in B53 does **not** prove that any pixel-writing
command was emitted.

For B53's four Startup frames, both pending flags are zero. The canvas can
therefore return true while doing no effective pixel overwrite.

This explains why old Nokia pixels can survive despite
`total_physically_seen=1` and `total_drawn=1`.

## B54 experiment

B54 performs one deliberately narrow functional experiment.

On the first primary-screen redraw whose focus changes into Startup
`0x100058F4`, and only when normal
`FLAG_SERVER_REDRAW_PENDING` is absent, B54 adds
`draw_buffer_bit_color_buffer` to the **existing** compositor clear call.

Runtime marker:

`[NBOOT2][TRANSITION_CLEAR]`

The clear trigger is an edge detector, not a permanent Startup-state clear:

```
primary screen
AND focus name contains 100058f4 / Startup
AND previous primary-screen redraw was not Startup
AND FLAG_SERVER_REDRAW_PENDING == 0
```

A normal Splash redraw resets the edge state, so a later Emulator session can
trigger the experiment again.

## What B54 does not change

B54 does not:

- add another `builder.clear()`;
- set/forge `FLAG_SERVER_REDRAW_PENDING`;
- force a WindowServer redraw;
- force a host present;
- change focus;
- change WindowGroup order;
- change window visibility or activation;
- change scheduler timing;
- change the B28 tree traversal;
- remove B51/B52/B53 diagnostics.

The compositor still contains exactly one clear command.

## Canonical GREEN

Workflow:

`Build EKA2L1 NATIVEBOOT2 CURRENT FAST`

- run ID: `35940100239`
- run number: `156`
- job: `107445895276`
- HEAD: `4f8629aa182b1de8d1c952733bfa49a6e1fc1040`

Result:

- B29-B54 apply/tests: PASS
- B20-B28 regressions: PASS
- B54 contract: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- `TRANSITION_CLEAR` retained in Mach-O: PASS
- IPA package/upload: PASS
- NOJAVA: preserved
- MANIC3: preserved

FASTBUILD:

- bootstrap source: B28 cache
- bootstrap restore: 38 s
- patch/regression: 3 s
- CMake build: 124 s
- package: 2 s
- total: 195 s
- compile requests: 149
- cache hits: 148
- cache misses: 1
- hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0

## IPA

Unsigned IPA:

- size: `19,996,203` bytes
- SHA-256:
  `e22acd144bac8fc9f455df176fc650d708aa38ce27ba4fde8caaf4aa4c5f27b7`

GitHub IPA artifact:

- ID: `10784681598`
- artifact ZIP digest:
  `sha256:9551eba348e70835e65668e71825cceb4e937a3ccd84f0012c5aa847647dd1e6`

Audit artifact:

- ID: `10784513042`
- digest:
  `sha256:23ecb2bc881a436e3a419f724bb0aeb01eb24e53268e2faddfec5b9b567d86b9`

Library copy:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B54-TRANSITIONCLEAR1-unsigned.ipa`

## Device-test protocol

Use the same RM-356 runtime pair.

B54 needs to reach the natural splash handoff, so leave the emulator running
for at least **150 seconds after the Nokia logo appears**.

Record the full run and send:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

Critical observation is what happens exactly when
`[NBOOT2][TRANSITION_CLEAR]` appears.

Decision:

1. Nokia pixels disappear/change immediately after TRANSITION_CLEAR:
   stale color-buffer retention is confirmed.
2. A black/blank screen replaces Nokia:
   the clear is effective, but Startup still supplies no usable pixel content;
   next work moves to missing Startup redraw content/replay.
3. A real Startup/Home UI appears:
   the stale retained splash was the blocking presentation artifact.
4. Nokia remains unchanged despite TRANSITION_CLEAR + host present:
   stale pixels originate from another surface/render path; reject the
   screen_texture-retention hypothesis.

Do not promote B54's clear to permanent behavior until device result.
