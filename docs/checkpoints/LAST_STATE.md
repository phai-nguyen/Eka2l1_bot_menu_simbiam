# LAST_STATE — EKA2L1 DirectHome

**Checkpoint date:** 2026-09-29
**Repository:** `phai-nguyen/Eka2l1_bot_menu_simbiam`  
**Active branch:** `codex/compatboot1-directhome`  
**Comparison branch — DO NOT MODIFY/MERGE:** `codex/compatboot1-menuprobe2-nobypass`  
**PR:** #9 — CompatBoot DirectHome FASTBUILD test — draft  
**Base:** `nativeboot2-current`

## Last verified remote source state

- Verified DirectHome branch HEAD: `eff46f2b821a0ed767d16ea36d0061095425eadf` (`docs: auto-record DirectHome recovery checkpoint`).
- FASTBUILD #358 source commit: `1517daae41c81c521ac58b428e639fd2a8717e00`; PR merge candidate: `dbe5860594b92057cae8d0f1337ccfe4c14ca9ab`.
- Verified B99 reference HEAD remains `b14804a4ccd594d837496e2f106c4b5e8a2cdb10`.
- Runtime objective: bypass normal firmware startup far enough to reach the real Nokia 5800 Home Screen using DirectHome while preserving B99 as comparison baseline.

## Current observed problem

- FASTBUILD #358 source branch SHA is `1517daae41c81c521ac58b428e639fd2a8717e00`; PR build candidate source SHA is `dbe5860594b92057cae8d0f1337ccfe4c14ca9ab`; Actions run `36495436746` completed successfully. The IPA SHA-256 is `8e99817fd9df84cd5fac92553b8cb293a77b90e486cc70b6587e199a41f98a05`.
- Device evidence from FASTBUILD #358 confirms `EikCore#473` at `alfappservercore.dll+0x318` returns `r0=0`. The observer at `+0xE82` records `pre_add_r0=0`; the next instructions derive `r0=0x80` and attempt the failing write at `0x88`. ALF terminates with KERN-EXEC 3.
- `TfxServer` still returns `KErrNotFound`; the video shows `Phone start-up failed. Contact the retailer.` Home was not observed or confirmed interactive.
- The iOS `.ips` records a separate host crash: `SIGBUS` / `KERN_PROTECTION_FAILURE` at `0x1500000134` in `codeseg::free_attached_data`, reached through `codedump_collector::add`, `codeseg::detach`, and `thread::cleanup_detachs`. The `Symbian OS thread` crashes while draining collected code segments after the guest ALF failure.
- The property-cancel guard was active in this build. At `06:11:55.663`, it logged `decision=skip` for requests owned by an exiting requester; the host crash occurred later at `06:12:02`. This guard does not explain or prevent the separate code-segment crash.
- Upstream EKA2L1 commit `437b29006bd8a0186f4070c9445f43e98e5c7435` fixes an attached-info collector lifetime issue by removing `info` from the codedump collector before erasing it from `attaches`. The B28 baseline is known to predate other fixes from that upstream batch; backport only this unlink invariant, not the rest of the upstream batch.
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

Apply and test the narrow collector unlink in `codeseg::free_attached_data()` before the attach-info links and owning entry are erased. Run the full suite and DirectHome preflight, then push a fast-forward commit to `codex/compatboot1-directhome` and verify the exact Actions SHA/result. If the build succeeds, provide the IPA and checksum as a diagnostic candidate for device testing. Keep Native Boot as default and B99 untouched; do not label a V9 or claim the crash/Home issue fixed without device evidence.
