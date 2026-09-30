# B50 POSTLOGOCANVAS1 — BUILD SNAPSHOT

Date: 2026-09-23  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection evidence from B49 DEVICE1

B49 correlated the native WindowServer log with the full device recording.

The Nokia logo becomes visible at the same timestamp that
`splashscreen[100059de]` creates and focuses a WindowGroup which is later
named `S60SplashScreenGroup`.

Startup and Home screen both create their own focus-requesting WindowGroups
behind it. Home screen is discoverable by UID and therefore its group is not
missing.

At 23:22:07.655 the splash WindowGroup object receives window opcode `0x06`.
The WindowServer authority maps `0x06` to
`EWsWinOpSetOrdinalPositionPri`. Focus changes immediately from
`S60SplashScreenGroup` to Startup, and splashscreen exits normally 12 ms
later.

The B49 video nevertheless remains visually pixel-identical to the Nokia logo
after the splash focus handoff and process exit. Home screen receives focus
only during emulator teardown, after Exit Emulator has already been requested.

Therefore B50 does not force Home screen focus. It classifies the missing
post-logo presentation transition first.

## B50 diagnostic scope

B50 traces only the three actors established by B49 evidence:

- `0x100059DE` — splashscreen
- `0x100058F4` — Startup
- `0x102750F0` — Home screen

New markers:

### `[NBOOT2][POSTLOGO_ORDERPRI]`

Observes `EWsWinOpSetOrdinalPositionPri` and records:

- caller process / UID3 / thread;
- object and client handle;
- requested priority and position;
- old/new priority;
- old/new ordinal position;
- unchanged completion result.

### `[NBOOT2][POSTLOGO_RECEIVEFOCUS]`

Observes explicit WindowGroup ReceiveFocus requests:

- requested focusable state;
- old/new focusable state;
- resulting WindowServer focus group.

### `[NBOOT2][POSTLOGO_CANVAS_CREATE]`

Observes client window/canvas creation for the three actors:

- WindowServer object handle;
- Symbian client handle;
- canvas/window type;
- owning WindowGroup ID, handle and name.

### `[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]`

Observes native canvas activation from the authoritative implementation in
`classes/winuser.cpp`:

- flags before/after;
- owning group;
- visibility;
- `can_be_physically_seen()`;
- unchanged KErrNone completion.

### `[NBOOT2][POSTLOGO_CANVAS_VISIBLE]`

Observes SetVisible requests and resulting visibility/physical-visibility state.

### `[NBOOT2][POSTLOGO_WG_DESTROY]`

Observes group destruction around the splash/startup/home transition:

- priority / ordinal;
- focusable state;
- whether the group was current focus;
- resulting focus after destruction.

## Semantic guard

B50 is diagnostic-only. It does not:

- change WindowGroup priority or ordinal requests;
- force or suppress focus;
- rewrite `ReceiveFocus`;
- alter window creation results;
- force visibility;
- force activation;
- trigger an extra redraw;
- clear or replace the framebuffer;
- change B49 WindowGroup/focus behavior;
- reopen B47 TFX or B48 FileFlush hypotheses.

The device experiment is specifically intended to decide whether the stale
Nokia surface is caused before or after normal canvas visibility/activation.

## Build chronology

Initial implementation commit:

`f69aa6adecf159f02f0d23a3773f472612818e6e`

Runs 137-142 were development-contract failures caused by differences between
the project's B28 bootstrap source layout and the current upstream source
spelling. They failed during patch/test application and did not produce a
device build.

The patch/test anchors were successively narrowed to structural operations
rather than exact source spelling. No functional workaround was introduced.

Canonical GREEN:

- run: `35891253078`
- run number: 143
- job: `107283982581`
- build HEAD: `0445b52ba14d0c1b45ad79ed9d627c697d745be7`
- FASTBUILD1 manifest: VALID
- B29-B50 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 149
- cache hits: 145
- cache misses: 4
- hit rate: 97.32%
- actual compilations: 4
- compilation failures: 0
- NOJAVA: PRESERVED
- MANIC3: PRESERVED

FASTBUILD audit:

- bootstrap source: B28_CACHE
- bootstrap restore: 37 s
- patch/regression: 3 s
- CMake build: 82 s
- package: 2 s
- total: 151 s

## IPA

Unsigned IPA size:

`19,988,067` bytes

Unsigned IPA SHA-256:

`0d46c081142116b472bedf41dc0620e8eff3601714947bb03ff013e93e1cda4c`

GitHub IPA artifact:

- ID: `10765615710`
- artifact ZIP size: `19,927,662` bytes
- artifact ZIP digest:
  `sha256:fbe1ba7e2272104058df0675142f65218559075e9c054005e1e14dbb6248052c`
- expires: 2026-10-07

Audit artifact:

- ID: `10765496097`
- digest:
  `sha256:7fa44b668e1b6a04d5d692f808e3eb278992c2efbe762f5404fd9699f90042b1`

## Device-test acceptance

Use the exact same RM-356 V60 `SYM.ROM + SYM.RPKG` pair.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording from launch until the stationary state, including the
  splash -> post-splash interval

Primary classification:

1. If Startup/Home canvases are never created or never activated, follow that
   first missing WindowServer object boundary.
2. If canvases are created/activated but never visible or physically seen,
   follow the group ordering/focusability/visibility boundary.
3. If Startup/Home canvases are visible + active + physically seen while the
   video still shows stale Nokia pixels after splash destruction, move the next
   diagnostic into WindowServer redraw/compositor/framebuffer invalidation.
4. Do not force Home focus or clear the framebuffer until one of those states
   is proven.
