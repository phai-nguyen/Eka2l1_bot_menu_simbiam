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

- FASTBUILD #355's device run stays at the Nokia splash for the full recording; Home is not visible or confirmed interactive, and TfxServer remains missing.
- The new marker at `alfappservercore.dll+0x31E` captured `r0=0`, but decoding showed that PC is the following call, not the return from EikCore #473. Immediately afterward ALF faults at `+0xE84` with `r0=0x80` and terminates with KERN-EXEC 3.
- The video/log show no spontaneous host shutdown during the roughly six-minute run; teardown begins at the end when the emulator menu is opened. The guest is still not at Home.
- FASTBUILD #356 moves the observer to the corrected return site `alfappservercore.dll+0x318`. Actions #356 passed for source SHA `1be807528c9ec556adf5e2e5dd55541652828487`, and the binary contains the corrected marker/offset. This build has not yet been device-tested.
- Probe remains register-only for Alfred UID3 `0x10282845`; it does not read guest memory or change guest state/results.
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

Run the FASTBUILD #356 IPA on device, then compare `[NBOOT2][DIRECTHOME_EIKCORE473_RETURN]` at `+0x318` against the later ALF fault. Record whether the host remains alive and whether TfxServer is still missing. Keep B99 untouched; do not claim Home reached without screen and interaction evidence.
