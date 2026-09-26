# B52 REDRAWSCHED1 — BUILD SNAPSHOT

Date: 2026-09-24  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection from B51 DEVICE1

B51 device evidence is captured in:

`docs/handoff/history/B51-DEVICE1.md`

Key result:

- B51 recorded 170 WindowServer redraws;
- all 170 returned `performed=1`;
- B51 recorded exactly 170 host presents;
- the host-only marker moved during that same interval;
- redraw/present activity stopped at 05:05:10.422;
- the B51 device test exited about 80 s after the first Nokia splash frame;
- B49/B50 had shown the natural splash demotion only around 120 s after the
  Nokia surface became active.

Therefore the B51 run ended too early to classify the critical natural
splash -> Startup redraw scheduling handoff.

The B51 marker was also visually too small. In the 1125x2436 host surface the
15x15 marker becomes only about 7x7 pixels in the 510x1108 screen recording.

## B52 objective

B52 keeps the B51 direct-screen diagnostic and observes the WindowServer
animation scheduler without changing its behavior.

New marker:

`[NBOOT2][REDRAW_SCHED]`

Observed phases:

- `schedule_enter`
- `schedule_done`
- `scan_arm`
- `scan_reuse`
- `idle_enter`
- `scan_enter`
- `scan_decision`
- `invoke_enter`
- `invoke_redraw_done`
- `invoke_done`

This lets the device test classify the exact natural handoff chain:

```
splash SetOrdinalPositionPri / group order change
 -> need_update_visible_regions(true)
 -> animation_scheduler::schedule
 -> schedule_scans
 -> idle_callback
 -> scan_for_redraw
 -> invoke_due_animation
 -> screen::redraw
 -> iOS redraw callback
 -> host present
```

## Enlarged visual marker

The existing B51 host marker is enlarged from:

`15x15`

to:

`72x72`

host pixels.

It is also moved down from y=6 to y=128 to make it easier to distinguish from
small UI/status content.

The four phases remain color/position coded.

This is still host-overlay-only:

- no guest `screen_texture` write;
- no forced redraw;
- no extra `present()`;
- no timer;
- no focus change;
- no z-order change;
- no visibility/activation change;
- no framebuffer clear.

## Source inspection before B52

The project B28 bootstrap scheduler was inspected directly.

Important scheduler authority:

- `animation_scheduler::schedule()` writes/coalesces a per-screen schedule and
  calls `schedule_scans(driver)`;
- `schedule_scans()` arms a 500-us callback only if one is not already armed;
- `idle_callback()` scans screens;
- `scan_for_redraw()` either invokes immediately or arms `anim_due_evt_`;
- `invoke_due_animation()` takes the kernel lock + screen mutex and calls
  `scr->redraw(driver)`;
- the screen state returns to `inactive` afterward.

B52 only logs these existing decisions.

## Build chronology

Initial B52 commit:

`7ba09917e35fab1320da7134d9a758b9fa73fb67`

Run 151 failed at compile time because `scheduler.cpp` only had a forward
declaration of `window_group`, while the new diagnostic helper reads
`scr->focus->id`.

This was a compile-only instrumentation issue; no IPA was produced.

Fix:

`2461ee8a5747a07f1aacbc58790a7021de134b4e`

adds the existing WindowGroup header needed by the diagnostic helper.

## Canonical GREEN

- workflow: `Build EKA2L1 NATIVEBOOT2 CURRENT FAST`
- run ID: `35928441761`
- run number: `152`
- job: `107409037256`
- HEAD: `2461ee8a5747a07f1aacbc58790a7021de134b4e`

Result:

- FASTBUILD manifest validation: PASS
- B29-B52 apply/tests: PASS
- B20-B28 regressions: PASS
- B52 contract: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- `REDRAW_SCHED` retained in Mach-O: PASS
- IPA package/upload: PASS
- NOJAVA: preserved
- MANIC3: preserved

FASTBUILD:

- bootstrap source: B28 cache
- bootstrap restore: 57 s
- patch/regression: 4 s
- CMake build: 104 s
- package: 2 s
- total: 196 s
- compile requests: 149
- cache hits: 147
- cache misses: 2
- hit rate: 98.66%
- actual compilations: 2
- compilation failures: 0

## IPA

Unsigned IPA:

- size: `19,991,158` bytes
- SHA-256:
  `f391d2114b4142bb7282d224d2d8d07a30a239045d46e9984234b316955ed40a`

GitHub IPA artifact:

- ID: `10779274613`
- artifact ZIP digest:
  `sha256:52c68a143be6205b9cf4c1ca8fd293a2f52b7e45c97edd5aec9918ce2a20f528`
- expires: 2026-10-07

Audit artifact:

- ID: `10779573844`
- digest:
  `sha256:4e4e1007160b2599672c391363352da643f1acf8984796cbf29a5e19b34abc85`

Library copy:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B52-REDRAWSCHED1-unsigned.ipa`

## Device-test protocol

Use the same RM-356 V60 pair.

Important: do **not** exit around 80-100 s after the Nokia logo appears.

After the Nokia logo first appears, keep the emulator running for at least
**150 seconds** before pressing Exit Emulator. This provides margin beyond the
~120 s natural splash demotion observed in B49/B50.

Record the whole run and send:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

Watch the enlarged colored marker.

Primary classification:

1. `REDRAW_SCHED schedule_enter` appears at natural splash demotion, but no
   `idle_enter`:
   callback scheduling/ntimer delivery is the first missing stage.
2. `idle_enter` appears, but no `scan_decision` / `invoke_enter`:
   scheduler state/coalescing is the first missing stage.
3. `invoke_enter` appears and calls redraw, but no
   `DIRECTSCREEN_PRESENT`:
   redraw callback -> iOS present path is the first missing stage.
4. redraw + present continue and the enlarged marker moves while Nokia remains:
   host presentation is alive; inspect the guest `screen_texture` contents /
   compositor tree traversal next.
5. if the guest screen finally replaces Nokia, preserve the exact scheduler
   trace that enabled the transition and do not add a synthetic workaround.

Do not implement a scheduler fix before this device evidence.
