# B53 COMPOSITORTREE1 — BUILD SNAPSHOT

Date: 2026-09-24  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection from B52 DEVICE1

B52 device evidence is captured in:

`docs/handoff/history/B52-DEVICE1.md`

The natural splash transition is now proven to reach host presentation:

```
06:09:02.083 splash SetOrdinalPositionPri
 -> REDRAW_SCHED schedule_enter / scan_arm / schedule_done
 -> focus Splash -> Startup
 -> splash group destroy
 -> 06:09:02.085 DIRECTSCREEN_PRESENT frame=171
 -> 06:09:02.093 DIRECTSCREEN_PRESENT frame=172
 -> 06:09:02.104 DIRECTSCREEN_PRESENT frame=173
 -> 06:09:02.117 DIRECTSCREEN_PRESENT frame=174
```

The enlarged B52 marker advances across those host presents.

The device recording remains visually on the same Nokia splash pixels across
that transition and for the rest of the run.

Therefore the unresolved boundary is now inside guest WindowServer composition,
not scheduler delivery or iOS present.

## Important B52 instrumentation correction

B52 inherited run-specific WindowServer object IDs:

- splash 3
- Startup 63
- Home 75

Those IDs are not stable. In the B52 device run Startup is id=61.

Therefore B52's post-focus conditional scheduler/redraw logging stops matching
after the transition even though the host presents prove redraw callbacks
continue.

B53 removes that assumption and selects Startup/Home frames by WindowGroup
name/UID strings instead.

## Source candidate identified

The active B28 compositor clears the color buffer only when:

`FLAG_SERVER_REDRAW_PENDING`

is set.

At the B52 natural handoff the host present marker reports:

`screen_flags=0x00000002`

which does not include `FLAG_SERVER_REDRAW_PENDING (0x8)`.

Therefore the handoff redraw can traverse the new WindowServer tree without
first clearing the old splash color pixels.

This is a strong candidate for the stale Nokia surface, but B53 remains
diagnostic-only until the actual canvas draw results are observed.

## B53 instrumentation

New markers:

- `[NBOOT2][COMPOSITOR_FRAME]`
- `[NBOOT2][COMPOSITOR_GROUP]`
- `[NBOOT2][COMPOSITOR_CANVAS]`

### COMPOSITOR_FRAME

For primary-screen redraws where focus is Startup or Home screen by
name/UID, B53 records:

- focus group id/handle/name;
- flags;
- visible-region recalculation state;
- server/client redraw-pending bits;
- whether color clear is requested;
- total client canvases;
- total visible canvases;
- total physically-visible canvases;
- total canvases whose `draw()` returns true.

### COMPOSITOR_GROUP

B53 records the top-level WindowGroup chain for each traced frame:

- sibling index;
- group id / client handle;
- priority / ordinal;
- flags;
- focusability;
- whether it is current focus;
- name;
- whether it has child windows.

### COMPOSITOR_CANVAS

For every canvas that is visible, physically visible, or actually draws during
the traced frame, B53 records:

- owning group id/handle/name;
- group priority;
- canvas handle/priority;
- flags;
- window type;
- absolute rectangle;
- visible-region empty/nonempty;
- `is_visible()`;
- `can_be_physically_seen()`;
- exact `draw()` result.

The existing canvas `draw()` call still occurs exactly once.

## Semantic guard

B53 does not:

- change the conditional color-clear expression;
- add another clear;
- force `FLAG_SERVER_REDRAW_PENDING`;
- change WindowGroup order;
- force focus;
- force redraw;
- add a host present;
- change B52 scheduler behavior;
- change B51 host overlay behavior.

The active B28 tree traversal is preserved exactly:

`root->walk_tree(&adrawwalker, window_tree_walk_style::bonjour_children)`

No newer-upstream traversal semantics are imported in B53.

## Build chronology

Initial B53 commit:

`6a64c7de16a380a92e481b62eb5facb339216d9b`

Run 153 failed during patch application because the first B53 patch expected a
newer upstream `window_drawer_walker` containing streaming-window support and
`walk_tree_back_to_front`.

The active B28 bootstrap actually uses the older walker and:

`root->walk_tree(... bonjour_children)`.

An inspection workflow captured the exact B28 compositor source.

Corrections:

- `ae02feee71c3f4e44dd7e778a3f77b8e01a60a3d`
  — retarget B53 to the B28 walker/traversal;
- `332040435ef6318902e23732cf1c6ec4369a72f6`
  — update the B53 regression contract to preserve the same B28 traversal.

## Canonical GREEN

- workflow: `Build EKA2L1 NATIVEBOOT2 CURRENT FAST`
- run ID: `35933740025`
- run number: `155`
- job: `107425985727`
- HEAD: `332040435ef6318902e23732cf1c6ec4369a72f6`

Result:

- FASTBUILD manifest validation: PASS
- B29-B53 apply/tests: PASS
- B20-B28 regressions: PASS
- B53 contract: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- COMPOSITOR markers retained in Mach-O: PASS
- IPA package/upload: PASS
- NOJAVA: preserved
- MANIC3: preserved

FASTBUILD audit:

- bootstrap source: B28 cache
- bootstrap restore: 26 s
- patch/regression: 2 s
- CMake build: 49 s
- package: 2 s
- total: 100 s
- compile requests: 149
- cache hits: 148
- cache misses: 1
- hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0

## IPA

Unsigned IPA:

- size: `19,996,831` bytes
- SHA-256:
  `d4c126540b7a12bef9569fd60f0f8db1ce74f4d12a6d23a83e90d626ace707a5`

GitHub IPA artifact:

- ID: `10781634512`
- artifact ZIP digest:
  `sha256:5f86f7dd03c0e07dbe36db67ed320b82073f48997e88a3880d359106f2be848e`

Audit artifact:

- ID: `10781634527`
- digest:
  `sha256:03bb78c5b4b635106c224426be49eb58ba066bb70d9ee22dcaf44127f66ec5ed`

Library copy:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B53-COMPOSITORTREE1-unsigned.ipa`

## Device-test protocol

Use the same RM-356 V60 pair.

Keep the emulator running at least **150 seconds after the Nokia logo first
appears**, exactly as in the successful B52-duration test.

Send:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

The enlarged B52 marker remains active.

Primary decision matrix:

1. `color_clear=0` and Startup/Home frames have few/no
   `COMPOSITOR_CANVAS draw_result=1` entries:
   stale old splash color is the leading explanation; prepare a narrowly
   scoped color-clear experiment next.

2. `color_clear=0` but Startup/Home draw enough full-screen physically-visible
   canvases:
   inspect draw order/tree traversal and which group actually writes last.

3. `color_clear=1` and Nokia still remains:
   stale pixels are not explained by the conditional clear; inspect actual
   canvas textures/surfaces.

4. Startup/Home canvases are physically visible and draw successfully but the
   host still shows Nokia:
   move to screen-texture readback/signature probing.

Do not introduce a functional clear before B53 device evidence.
