# LAST_STATE — EKA2L1 DirectHome

**Checkpoint date:** 2026-09-29
**Repository:** `phai-nguyen/Eka2l1_bot_menu_simbiam`  
**Active branch:** `codex/compatboot1-directhome`  
**Comparison branch — DO NOT MODIFY/MERGE:** `codex/compatboot1-menuprobe2-nobypass`  
**PR:** #9 — CompatBoot DirectHome FASTBUILD test — draft  
**Base:** `nativeboot2-current`

## Last verified remote source state

- Latest source-changing commit on DirectHome: `50b293f4852112c6fce7afadc48bcbff184b7b6d`; the checkpoint recorder subsequently wrote `8d1e9df99f52b494ba3208f2a79080498d9f0fd6`.
- FASTBUILD #359 source branch SHA: `50b293f4852112c6fce7afadc48bcbff184b7b6d`; PR merge candidate: `14ff88bfa99be8e4f36af8269bed888483ac0e9c`.
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

## FASTBUILD #359 result

- Actions run `36498797082` completed successfully for branch SHA `50b293f4852112c6fce7afadc48bcbff184b7b6d`; preflight, regressions, and binary invariants passed.
- The diagnostic candidate IPA SHA-256 is `b4a6fd651c59ba0e66f8befdebb1ae3e4dc746b041db74b970d9afbe2f532ff2`.
- This is build evidence only. It does not establish that the host crash is gone, ALF continues, TfxServer appears, or Home is reachable.

## NEXT ACTION

Device evidence from the FASTBUILD #359 candidate has now been received. Check the new HAL destination guard in the next Actions build, confirm its exact source SHA and IPA checksum, then test that IPA on the device with fresh logs and an iOS `.ips` if it exits. Inspect the one-time `[NBOOT2][HAL_PAGE_SIZE_INVALID_DEST]` marker for guest process/thread/raw destination/PC; continue tracing the earlier `EikCore#473` null return, ALF death, missing `TfxServer`, and the `ailaunch.exe` restart loop. Keep Native Boot as default and B99 untouched; do not claim Home reached without a visible, interactive Home.

## FASTBUILD #359 device result (2026-09-29 07:16–07:19 +0700)

- Video duration 184.23 s includes the iOS Home after the crash. The iOS `.ips` records launch `07:16:28.9003` and host crash `07:19:10.0985`, about 161.20 s. The guest displayed `Phone start-up failed. Contact the retailer.` throughout the later video; interactive Home was not observed.
- `EKA2L1_Persistent.log` (2,225,965,145 bytes) begins with the 57,379-byte `EKA2L1_TakeThis.log` and then the 2,225,907,766-byte `EKA2L1.log`. The main log has 10,401,277 lines. Do not mistake these two concatenated copies for two independent device sessions.
- At `07:17:06.746`, `EikCore#473` in `alfappservercore.dll` again returned `r0=0`, the object observer recorded `pre_add_r0=0`, and guest ALF faulted. `TfxServer` requests returned `KErrNotFound`, including Home screen. From `07:17:20.902`, guest `ailaunch.exe` repeatedly ended with `KERN-EXEC 3` and `SYSSTART` reloaded it. The main log contains 40,052 `KERN-EXEC` lines; this restart loop explains its size and may contribute to load.
- The prior host SIGBUS in `codeseg::free_attached_data` did not recur during this run. The new host exception is `EXC_BAD_ACCESS/SIGSEGV` at null address on the Symbian OS thread, frame `epoc::kern_hal::page_size(int*, int*, unsigned short)+28`, called via `hal::do_hal` and `hal_function`. The source writes `*a1` without checking whether guest pointer translation returned null. This proves a new crash site; it does not prove every `codeseg` failure is eliminated or that startup has advanced to Home.
- FASTBUILD #359 Actions run `36498797082` passed at `50b293f4852112c6fce7afadc48bcbff184b7b6d`; docs-only #360 run `36499177222` also passed at `995d33b49c781598cc3c80592f40b6e46f6cba2a` with the same source-changing code. Device binary identity was not independently extracted from the supplied IPA, so interpret this as the candidate device evidence rather than a cryptographic match to #359.
