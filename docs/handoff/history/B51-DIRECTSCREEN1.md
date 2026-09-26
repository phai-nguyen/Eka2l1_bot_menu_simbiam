# NATIVEBOOT2 B51 DIRECTSCREEN1

Date: 2026-09-24  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection from B50 DEVICE1

B50 device evidence closes the simple "Startup/Home windows never exist or
activate" hypothesis.

Observed sequence:

- Nokia splash WindowGroup/canvas renders.
- Startup group 63 and multiple Startup canvases exist.
- Home screen group 75 and many Home canvases exist.
- visible Startup/Home canvases activate successfully.
- splash group demotes from priority 1001 to -1000.
- focus moves from splash group 3 to Startup group 63.
- splash group is destroyed.
- WindowServer reports visible-region recomputation pending.
- the full device recording nevertheless remains on the same Nokia startup
  pixels.

Full evidence:

- `docs/handoff/history/B50-DEVICE1.md`

The next unresolved boundary is therefore:

```
WindowServer screen::redraw()
 -> screen_texture updated or not
 -> iOS redraw callback
 -> launcher_->draw(screen_texture)
 -> host present
```

## B51 implementation

B51 is diagnostic-only.

New runtime markers:

- `[NBOOT2][DIRECTSCREEN_REDRAW]`
- `[NBOOT2][DIRECTSCREEN_PRESENT]`

### WindowServer side

`screen::redraw(drivers::graphics_driver*)` now reports, for primary-screen
focus groups 3 / 63 / 75:

- phase enter/result;
- screen texture handle;
- flags before/after;
- visible-region recalculation state before/after;
- current focus group id/handle/name;
- whether the compositor returned `performed=1`.

No redraw is forced.

### iOS host-present side

The actual B28/current iOS present path is in
`src/emu/ios/src/state.cpp`:

```
screen::redraw()
 -> fire_screen_redraw_callbacks()
 -> emulator::register_draw_callback callback
 -> launcher_->draw(builder, scr, ...)
 -> builder.present()
```

B51 draws a 15x15 four-phase colored marker directly on host bitmap 0 after
`launcher_->draw()` and before the already-existing `present()`.

The marker:

- runs only while `native_phone_mode` is active;
- advances only when the existing redraw callback fires;
- does not write `scr->screen_texture`;
- does not add a timer;
- does not call `screen::redraw()`;
- does not add an extra `present()`;
- does not change focus, z-order, visibility, activation, TFX, xntheme, FBS,
  CenRep, or firmware state.

## Build lineage correction

The first B51 implementation incorrectly targeted the newer upstream
`src/emu/ios/Bridge/IosEmulator.mm` layout. The active FASTBUILD B28 bootstrap
uses the older/current project iOS layout:

- `src/emu/ios/src/state.cpp`
- `src/emu/ios/src/launcher.cpp`

An inspection workflow confirmed the real presentation path before the
corrected B51 was applied.

Corrected B51 implementation commit:

`f5a5e5b2a37a0cd94a31cb0ad73cc134a19bdfc7`

## Canonical GREEN

Workflow:

- `Build EKA2L1 NATIVEBOOT2 CURRENT FAST`

Run:

- run ID: `35902306523`
- run number: `150`
- HEAD: `f5a5e5b2a37a0cd94a31cb0ad73cc134a19bdfc7`

Result:

- FASTBUILD manifest validation: PASS
- B29-B51 apply/tests: PASS
- B20-B28 regressions: PASS
- B51 contract: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- `DIRECTSCREEN_PRESENT` present in Mach-O: YES
- `DIRECTSCREEN_REDRAW` present in Mach-O: YES
- `git diff --check`: PASS
- IPA package/upload: PASS
- NOJAVA: preserved
- MANIC3: preserved

FASTBUILD audit:

- bootstrap source: B28 cache
- bootstrap restore: 55 s
- patch/regression: 3 s
- CMake build: 56 s
- package: 3 s
- total: 147 s
- compile requests: 149
- cache hits: 147
- cache misses: 2
- hit rate: 98.66%
- actual compilations: 2
- compilation failures: 0

Unsigned IPA:

- size: `19,989,478` bytes
- SHA-256:
  `c9113a51d3a8d7ad90e3d2270dcd0c350fa82ec812bf629045b81dfac2b6f4f9`

GitHub IPA artifact:

- ID: `10770061156`
- artifact ZIP digest:
  `sha256:59d65eb64c9aaa3046b69691180d7a8eb1cf071007a39f6cfa8c4aff66019195`
- expires: 2026-10-07

Audit artifact:

- ID: `10769866656`
- digest:
  `sha256:48251a2b1746f319ffe926387dbdb5f7383b563aae8a43ce02ba2eaef87b8a88`

Library copy:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B51-DIRECTSCREEN1-unsigned.ipa`

## Device-test protocol

Use the exact same RM-356 V60 runtime pair used for B47-B50.

Record the whole test and send:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

Let the boot continue beyond the Nokia logo and preferably beyond splash
demotion/destruction before exiting normally.

Watch the tiny colored marker near the upper-left of the host emulator surface.

Decision matrix:

1. **Marker continues changing/moving after splash teardown while Nokia pixels
   remain unchanged**
   - iOS host present is alive.
   - Next investigation moves inside guest `screen_texture` / WindowServer
     composition output.

2. **Marker stops when the Nokia splash becomes stale and no later
   `DIRECTSCREEN_PRESENT` appears**
   - redraw callback / present scheduling is the first missing stage.

3. **`DIRECTSCREEN_REDRAW` continues with `performed=0`**
   - WindowServer redraw is invoked but emits no drawable guest content.

4. **`DIRECTSCREEN_REDRAW performed=1` continues and marker moves, but Nokia
   pixels remain stale**
   - compositor commands are running and host presentation is live;
   - next diagnostic should inspect what is actually written into
     `screen_texture` and the tree/clear behavior.

Do not force Home focus or clear the framebuffer before B51 device evidence.
