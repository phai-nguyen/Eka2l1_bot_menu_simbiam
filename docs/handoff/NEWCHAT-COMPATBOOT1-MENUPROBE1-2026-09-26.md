# New-chat handoff — COMPATBOOT1-MENUPROBE1

Updated: 2026-09-26

## Continue from here

- Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
- PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
- Branch: `codex/compatboot1-menuprobe1`
- Current PR commit: `0bced6f0f897cfcce0e214ce77814177800c9887`
- Worktree used: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
- Base branch remains `nativeboot2-current` at the B89 baseline.

Do not restart earlier milestone research. The current objective is COMPATBOOT1-MENUPROBE1: retain Native Boot as the default, wait for the required UI services, then launch the real firmware `menu3.exe` and report the first missing dependency or visible target marker. No firmware replacement or readiness bypass is part of this change.

## Build status

FASTBUILD #281, run [36241917700](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241917700), is **GREEN** on commit `0bced6f0f897cfcce0e214ce77814177800c9887`. B28 baseline validation, manifest regressions, CMake configuration, iOS compile, binary invariants, unsigned IPA packaging, and artifact upload all succeeded.

The two previous compile failures and fixes:

- FASTBUILD #278 exposed the injected `eka2l1::kernel::svc` helper namespace left open before the original `eka2l1::epoc` block. This nested the rest of `svc.cpp` and caused the `security_policy`, `ptr`, and `LOG_WARN` cascade. The helper now closes its namespace. Its version lookup uses `kernel_system::get_epoc_version()` instead of dereferencing the forward-declared `system` type.
- FASTBUILD #279 then exposed the target-visible marker's `config::state` lookup resolving under `epoc::config` and its `ctx.sys` dereference of incomplete `system`. It now uses `eka2l1::config::state` and the existing window-client path `client->get_ws().get_kernel_system()->get_config()`.
- The final local suite passed 44 Python tests; the COMPATBOOT contract module passed all 17 tests; `ci/fastbuild1_manifest.py validate .` and `git diff --check` passed.

## IPA artifact

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10906140997`
- IPA inside the ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Expiration: 2026-10-10 (14-day retention)
- Run page: [FASTBUILD #281](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241917700)

On iPhone, open the run page in Safari while signed in to GitHub, scroll to **Artifacts**, and tap the IPA artifact name. In Files, open **Downloads** and tap the downloaded ZIP once to extract it. Import the `.ipa` into ESign Match to sign/install it; this workflow deliberately produces an unsigned IPA, so tapping the IPA in Files alone will not install it.

## B90 device result

B90 (`EKA2L1_TakeThis(20260926-125351).log`) confirms the barrier became ready and launched real `menu3.exe`. The visible marker did not fire. The first system-wide TfxServer miss is from `eiksrvs` at 19:49:16.979; Menu3 reports its own first failure at 19:49:21.932. Before those misses, AknSkinSrv reads Themes CenRep `0x102818E8` key `0x09` as `0x7FFFFFFF` (`enabled=0 suppressed=1`). Alfred starts and its AppServer registers successfully, but no TFX plugin DLL load or `TfxServer` registration is observed. See [B90 device evidence](history/B90-COMPATBOOT1-DEVICE1.md).

The observed value `0x7FFFFFFF` matches the extracted stock V60 ROM repository default for `0x102818E8:0x09`. B90's generic `changes saved` lines do not establish that this key was written at runtime. Continue diagnosing Menu3 with this stock gate and the original `TfxServer -> KErrNotFound` behavior preserved; add key-level write tracing only if runtime mutation itself becomes a necessary question. Do not force-enable TFX or fabricate a server. A device-visible Menu3 surface remains unconfirmed. Capture the next diagnostic log and screen recording, especially:

- `[COMPATBOOT][BARRIER_WAIT]` / `[COMPATBOOT][BARRIER_READY]`
- `[COMPATBOOT][TARGET_LAUNCH]`
- `[COMPATBOOT][FIRST_FAILURE]` and the exact missing server, if Menu3 stops
- `[COMPATBOOT][TARGET_VISIBLE]`, if a Menu3 window becomes visible

FASTBUILD proves the binary compiles and preserves its markers. It does not prove that the firmware menu is visible on the phone. PR #6 is unmerged, and device acceptance remains pending.
