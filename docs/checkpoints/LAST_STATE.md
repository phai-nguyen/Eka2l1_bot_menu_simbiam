# LAST_STATE — EKA2L1 DirectHome

**Checkpoint date:** 2026-09-28  
**Repository:** `phai-nguyen/Eka2l1_bot_menu_simbiam`  
**Active branch:** `codex/compatboot1-directhome`  
**Comparison branch — DO NOT MODIFY/MERGE:** `codex/compatboot1-menuprobe2-nobypass`  
**PR:** #9 — CompatBoot DirectHome FASTBUILD test — draft  
**Base:** `nativeboot2-current`

## Last verified remote source state

- Source HEAD before adding recovery-checkpoint infrastructure: `d134425946c62da677553d9ff21c9626a6c97f82`
- Commit message: `test: report observed TFX dispatch shape`
- Previous relevant commit: `218166c97658839093cb8bc5941d29fec398e9b3` — trace DirectHome TFX callsite and sessions.
- Runtime objective: bypass normal firmware startup far enough to reach the real Nokia 5800 Home Screen using DirectHome while preserving B99 as comparison baseline.

## Current observed problem

- FASTBUILD #356 was device-tested from source SHA `1be807528c9ec556adf5e2e5dd55541652828487`. The video reaches and remains on the PhoneUI text `Phone start-up failed. Contact the retailer.`; Home is not shown or confirmed interactive.
- At `05:39:20.545`, the `ailaunch` thread was renamed `Home screen`. Its first observed `TfxServer` session request failed with `KErrNotFound` at `05:39:20.598`.
- At `05:39:20.605`, EikCore #473 returned `r0=0` at `alfappservercore.dll+0x318`. In the same timestamp, ALF faulted at `+0xE84`, with `r0=0x80` and an attempted write to `0x88`, then terminated with KERN-EXEC 3 at `05:39:20.608`.
- The code window identifies `+0xE82` as `ADD r0, #0x80` immediately before the failing store at `+0xE84`. The existing fault record therefore shows the derived `r0=0x80`, but not the base value before that add.
- `Telephone` panicked with `CONE 14` (`NoResourceFileForId`) at `05:39:24.796`; the resource probe saw `0x1099B02D` but could not verify its owner. The host stayed alive until the user exited the emulator at the end of the recording.
- Remote DirectHome HEAD is `a09662528e5e1058d96fde23a36b863a058653de`; Actions #357 for that docs-only commit succeeded. B99 remains at `b14804a4ccd594d837496e2f106c4b5e8a2cdb10`.
- A diagnostic-only observer at ALF UID3 `0x10282845`, PC `alfappservercore.dll+0xE82`, now records registers before the add. It does not read guest memory or alter registers/results. Source tests and DirectHome preflight pass; this change has not yet been built or device-tested.
- The earlier B28 dispatch question is already covered by functional patches newer than the checkpoint's original `d1344259…` source state; do not reconstruct it.

## Safety / branch constraints

- Build work must target `codex/compatboot1-directhome`.
- Verify remote HEAD before each FASTBUILD.
- Keep B99 `codex/compatboot1-menuprobe2-nobypass` unchanged for A/B comparison.
- Do not merge PR #9 merely to checkpoint/recover state.
- A recovery/documentation commit is not evidence that the emulator behavior changed.

## Recovery procedure

1. Read this file.
2. Read `docs/checkpoints/AUTO_LAST_COMMIT.md` if present.
3. Fetch the current HEAD of `codex/compatboot1-directhome`.
4. Compare commits newer than the source HEAD recorded above.
5. Check the latest Actions run/artifact before claiming a build exists.
6. Use the newest device logs/video as runtime truth.
7. Recreate any explicitly recorded unpushed patch only after checking it is absent from current remote source.

## NEXT ACTION

Build the tested `+0xE82` observer on the DirectHome branch, verify the exact SHA, Actions result and IPA checksum, then test that diagnostic FASTBUILD on device. Correlate pre-add `r0` with the existing `+0xE84` fault and `TfxServer` failure. This is a diagnostic build, not a release or a claim of a fix. Keep B99 untouched; do not claim Home reached without screen and interaction evidence.
