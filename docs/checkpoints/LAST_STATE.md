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

- TFX-off/DirectHome testing still does **not** reach the Home Screen.
- Current investigation is centered on the real RM-356 TfxServer / transition-effects call path and its interaction with DirectHome.
- Latest diagnostic state reports the observed TFX dispatch shape.
- A compatibility fix for the FASTBUILD B28 dispatch case was being investigated for a shape with **2 `GOTO_NEXT_INST` and 0 fused branches**. Treat this as **not present on remote unless a later commit proves otherwise**.

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

Resume from the TfxServer/DirectHome investigation. First compare current remote HEAD against `d134425946c62da677553d9ff21c9626a6c97f82`; if no newer functional patch exists, reconstruct/validate the pending FASTBUILD B28 dispatch compatibility fix, then build/test on `codex/compatboot1-directhome`. Keep B99 untouched.
