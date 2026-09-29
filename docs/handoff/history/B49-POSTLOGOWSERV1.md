# B49 POSTLOGOWSERV1 — BUILD SNAPSHOT

Date: 2026-09-23  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection evidence

B48 device video shows:

- emulator enters a black screen after launch;
- the white Nokia boot surface appears at about 35.2 seconds;
- the blue Nokia logo remains visually unchanged for the rest of the roughly
  228-second recording;
- the user exits normally.

The video aligns the Nokia-logo appearance with the same boot interval where
WindowServer activity is already live. The B48 logs then show native Home
screen starting at 22:39:01.746 and continuing through xnthemeserver/theme
setup while the video never transitions away from the boot logo.

B48 already proved xnthemeserver FileFlush is healthy, so B49 moves the
diagnostic boundary to WindowServer window groups and focus.

## Scope

B49 is diagnostic-only.

New markers:

- `[NBOOT2][POSTLOGO_WG_FIND]`
  - caller process/UID3/thread;
  - previous group ID, offset, wildcard pattern;
  - exact match result, matched group ID/client handle/name.
- `[NBOOT2][POSTLOGO_WG_CREATE]`
  - caller process/UID3/thread;
  - new WindowGroup ID/client handle;
  - focus-request flag, parent ID, screen, current focus.
- `[NBOOT2][POSTLOGO_WG_ORDINAL]`
  - target group/name;
  - requested ordinal position;
  - old/new ordinal position.
- `[NBOOT2][POSTLOGO_FOCUS]`
  - old and newly selected WindowGroup IDs/client handles/names;
  - final focus selection per screen.

B49 deliberately does not alter WindowServer return values, z-order requests,
focus policy, theme state, TFX, FileServer, or rendering.

The earlier activation probe was removed before the canonical green build
because the predecessor-patched source body did not provide a stable patch
anchor. B49 therefore narrows the first device experiment to group/focus
classification; activation can be instrumented later only if group/focus
results are healthy.

## Build chronology

Initial B49 commit:

`10849166880fc4a29e2af422e7124fbbb1604fb1`

Run 133 failed during patch application because the first activation-body
anchor did not match the predecessor-patched source.

Run 134, after moving the activation hook toward the function entry, still
failed the same patch-anchor contract.

Commit `9d08f1b870c83fa47a61f7f65aa7a41a120e8ff6` removed activation tracing
from B49 and narrowed scope to WindowGroup/focus diagnostics.

Run 135:
- apply/test PASS;
- compilation failed in `screen.cpp` because the diagnostic guard attempted
  member access through an incomplete `config::state` type.

Commit `58cb44733ad6b8cd5bd0543687532a70852cf326` removed that diagnostic-only
config-state dependency from the focus logger. It does not change WindowServer
semantics.

## Canonical GREEN

- run: `35886788765`
- job: `107268855673`
- build HEAD: `58cb44733ad6b8cd5bd0543687532a70852cf326`
- FASTBUILD1 manifest: VALID
- B29-B49 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 149
- cache hits: 148
- cache misses: 1
- hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0
- NOJAVA/MANIC3 preserved

## IPA

Unsigned IPA SHA-256:

`ab22067d9be0f28a802cfc2ff0356790e43c04ca8fb34847bdccaef7271dd17b`

Extracted IPA size:

`19,981,928` bytes

GitHub IPA artifact:

- ID: `10763560496`
- ZIP size: `19,919,958` bytes
- ZIP digest:
  `sha256:df69213c6a9310b323124c46d9b0572a871c9c96c37c9e9381b5361318241f9c`
- expires: 2026-10-07

Audit artifact:

- ID: `10763945205`
- digest:
  `sha256:ff2d434721ad690a2215f0be958b144a8175361de627045d6030fff201160286`

## Device test

Use the exact same RM-356 V60 `SYM.ROM + SYM.RPKG` pair.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- a full screen recording from launch through the stationary visual state

Primary questions:

1. Which process creates the WindowGroup that owns the Nokia boot surface?
2. Does Home screen create its own WindowGroup?
3. Does that Home screen group ever become selected/final focus?
4. Are `0x2B` lookup misses from Home screen, Startup, or another process,
   and what wildcard group name is being searched?
5. Does Home screen request an ordinal change that should move its group ahead
   of the startup group?

Do not patch `ws_cl_op_find_window_group_identifier` or force focus until the
device log answers these questions.
