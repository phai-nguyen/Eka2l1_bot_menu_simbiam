# New-chat handoff — COMPATBOOT1-MENUPROBE1

Updated: 2026-09-26

## Continue from here

- Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
- PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
- Branch: `codex/compatboot1-menuprobe1`
- Latest build-validated source commit: `2ff5817ef0e347d59408632d944b6a89059d9ce5`
- Worktree used: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
- Base branch remains `nativeboot2-current` at the B89 baseline.

Do not restart earlier milestone research. The current objective is COMPATBOOT1-MENUPROBE1: retain Native Boot as the default, wait for the required UI services, then launch the real firmware `menu3.exe` and report the first missing dependency or visible target marker. No firmware replacement or readiness bypass is part of this change.

## Build status

FASTBUILD #281, run [36241917700](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241917700), is **GREEN** on commit `0bced6f0f897cfcce0e214ce77814177800c9887`. B28 baseline validation, manifest regressions, CMake configuration, iOS compile, binary invariants, unsigned IPA packaging, and artifact upload all succeeded.

The next patch added a CompatBoot-only `Leave(-5)` trace for Menu3: register values, trap/caller frame resolution, and at most 32 stack words. The trace leaves exception handling and guest behavior unchanged. FASTBUILD #284 initially stopped in patch application because the GitHub copy of the patcher had acquired a truncated-output banner. It was restored from the worktree in commit `2ff5817ef0e347d59408632d944b6a89059d9ce5`. FASTBUILD #285, run [36245715377](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36245715377), is **GREEN** on that commit. It passed B28 baseline validation, manifest regressions, iOS compile, binary marker invariants, unsigned IPA packaging, and artifact uploads.

The two previous compile failures and fixes:

- FASTBUILD #278 exposed the injected `eka2l1::kernel::svc` helper namespace left open before the original `eka2l1::epoc` block. This nested the rest of `svc.cpp` and caused the `security_policy`, `ptr`, and `LOG_WARN` cascade. The helper now closes its namespace. Its version lookup uses `kernel_system::get_epoc_version()` instead of dereferencing the forward-declared `system` type.
- FASTBUILD #279 then exposed the target-visible marker's `config::state` lookup resolving under `epoc::config` and its `ctx.sys` dereference of incomplete `system`. It now uses `eka2l1::config::state` and the existing window-client path `client->get_ws().get_kernel_system()->get_config()`.
- The final local suite passed 44 Python tests; the COMPATBOOT contract module passed all 17 tests; `ci/fastbuild1_manifest.py validate .` and `git diff --check` passed.

## IPA artifact

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10907232828` (FASTBUILD #285; latest artifact)
- IPA inside the ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Expiration: 2026-10-10 (14-day retention)
- Run page: [FASTBUILD #285](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36245715377)

On iPhone, open the run page in Safari while signed in to GitHub, scroll to **Artifacts**, and tap the IPA artifact name. In Files, open **Downloads** and tap the downloaded ZIP once to extract it. Import the `.ipa` into ESign Match to sign/install it; this workflow deliberately produces an unsigned IPA, so tapping the IPA in Files alone will not install it.

## B90 device result

B90 (`EKA2L1_TakeThis(20260926-125351).log`) confirms the barrier became ready and launched real `menu3.exe`. The visible marker did not fire. The first system-wide TfxServer miss is from `eiksrvs` at 19:49:16.979; Menu3 reports its own first failure at 19:49:21.932. Before those misses, AknSkinSrv reads Themes CenRep `0x102818E8` key `0x09` as `0x7FFFFFFF` (`enabled=0 suppressed=1`). Alfred starts and its AppServer registers successfully, but no TFX plugin DLL load or `TfxServer` registration is observed. See [B90 device evidence](history/B90-COMPATBOOT1-DEVICE1.md).

The observed value `0x7FFFFFFF` matches the extracted stock V60 ROM repository default for `0x102818E8:0x09`; generic `changes saved` lines do not establish a per-key write. Menu continues after the expected missing `TfxServer`. Its next notable event is FileServer `Fs::Entry` opcode 22 for `C:\\private\\101F4CD2\\appshell.ini`, returning `KErrNotFound`, followed by `Leave(-5)` in the same thread. This is correlated evidence, not proof the file is required or caused the leave. FASTBUILD #285 passed with the CompatBoot-only register/trap/32-word stack trace, preserving the leave path, so this IPA can be used for the next device capture. Do not force-enable TFX, create `appshell.ini`, fabricate a server, or change firmware.

- `[COMPATBOOT][BARRIER_WAIT]` / `[COMPATBOOT][BARRIER_READY]`
- `[COMPATBOOT][TARGET_LAUNCH]`
- `[COMPATBOOT][FIRST_FAILURE]` and the exact missing server, if Menu3 stops
- `[COMPATBOOT][TARGET_VISIBLE]`, if a Menu3 window becomes visible

FASTBUILD proves the binary compiles and preserves its markers. It does not prove that the firmware menu is visible on the phone. PR #6 is unmerged, and device acceptance remains pending.
