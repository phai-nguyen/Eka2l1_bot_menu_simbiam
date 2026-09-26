# New-chat handoff — COMPATBOOT1-MENUPROBE1

Updated: 2026-09-26

## Continue from here

- Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
- PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
- Branch: `codex/compatboot1-menuprobe1`
- Current PR commit: `840314d898e72bcbd3d17fef5a01d452202e39fc`
- Worktree used: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
- Base branch remains `nativeboot2-current` at the B89 baseline.

Do not restart earlier milestone research. The current objective is COMPATBOOT1-MENUPROBE1: retain Native Boot as the default, wait for the required UI services, then launch the real firmware `menu3.exe` and report the first missing dependency or visible target marker. No firmware replacement or readiness bypass is part of this change.

## Build status

FASTBUILD #280, run [36241579876](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241579876), is **GREEN** on commit `840314d898e72bcbd3d17fef5a01d452202e39fc`. B28 baseline validation, manifest regressions, CMake configuration, iOS compile, binary invariants, unsigned IPA packaging, and artifact upload all succeeded.

The two previous compile failures and fixes:

- FASTBUILD #278 exposed the injected `eka2l1::kernel::svc` helper namespace left open before the original `eka2l1::epoc` block. This nested the rest of `svc.cpp` and caused the `security_policy`, `ptr`, and `LOG_WARN` cascade. The helper now closes its namespace. Its version lookup uses `kernel_system::get_epoc_version()` instead of dereferencing the forward-declared `system` type.
- FASTBUILD #279 then exposed the target-visible marker's `config::state` lookup resolving under `epoc::config` and its `ctx.sys` dereference of incomplete `system`. It now uses `eka2l1::config::state` and the existing window-client path `client->get_ws().get_kernel_system()->get_config()`.
- The final local suite passed 44 Python tests; the COMPATBOOT contract module passed all 17 tests; `ci/fastbuild1_manifest.py validate .` and `git diff --check` passed.

## IPA artifact

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10906670626`
- IPA inside the ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Expiration: 2026-10-10 (14-day retention)
- Run page: [FASTBUILD #280](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241579876)

On iPhone, open the run page in Safari while signed in to GitHub, scroll to **Artifacts**, and tap the IPA artifact name. In Files, open **Downloads** and tap the downloaded ZIP once to extract it. Import the `.ipa` into ESign Match to sign/install it; this workflow deliberately produces an unsigned IPA, so tapping the IPA in Files alone will not install it.

## Device test still needed

After installing the signed IPA, open EKA2L1 and choose the explicit CompatBoot probe option from **Emulator**. Keep Native Boot as the default. Capture the first resulting log and screen recording, especially:

- `[COMPATBOOT][BARRIER_WAIT]` / `[COMPATBOOT][BARRIER_READY]`
- `[COMPATBOOT][TARGET_LAUNCH]`
- `[COMPATBOOT][FIRST_FAILURE]` and the exact missing server, if Menu3 stops
- `[COMPATBOOT][TARGET_VISIBLE]`, if a Menu3 window becomes visible

FASTBUILD proves the binary compiles and preserves its markers. It does not prove that the firmware menu is visible on the phone. PR #6 is unmerged, and device acceptance remains pending.
