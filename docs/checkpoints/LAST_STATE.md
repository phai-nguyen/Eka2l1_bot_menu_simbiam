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

- V9 starts `alfredserver.exe` after the six-service gate but remains at the Nokia splash; Home has not been observed or verified interactive, and TfxServer remains absent.
- The V9 log shows `alfappservercore.dll` faulting at offset `0xE84` after EikCore export #473 returns `0x80`; the caller then treats that value as an object pointer and attempts a write at `0x88`.
- FASTBUILD #355's observer fired at `alfappservercore.dll+0x31E`, but instruction decoding shows that is the following call, not EikCore #473's return point. It captured `r0=0`; the later fault still had `r0=0x80`.
- Correct the observation site to `alfappservercore.dll+0x318`, the instruction immediately after the #473 call, then rebuild. Keep the probe limited to ARM registers for Alfred UID3 `0x10282845`; do not read guest memory or change guest state/results.
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

Build and inspect the corrected EikCore #473 return-site diagnostic at `alfappservercore.dll+0x318`. Confirm the binary marker, verify the source SHA and Actions result, then use the next device log to compare the actual #473 return in `r0` against the later `0x80` fault. Keep B99 untouched; do not claim Home reached without screen and interaction evidence.
