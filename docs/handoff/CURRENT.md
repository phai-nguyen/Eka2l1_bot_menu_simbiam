# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-27

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B93 device evidence](history/B93-DEVICE1.md); [B92 device evidence](history/B92-DEVICE1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Latest build-validated commit: `c0a1056069cb709895c72ef9093e7dbb1d8ebcca`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test explicitly selected CompatBoot, which waits for the UI services before launching the real firmware `menu3.exe`.

The B92 method-2 run and B93 method-3 run both reached the readiness barrier and launched real `menu3.exe`, but neither produced `[COMPATBOOT][TARGET_VISIBLE]`. Both show five identical no-match `FindEqInt` queries against `0x102858F2`. Menu's own query occurs after the first trapped `Leave(-5)` and its first `TfxServer` miss. B93's video shows the Nokia logo, not the Symbian Menu; its logs record clean shutdown and normal restart, and the user confirms the app was exited manually without a crash. See [B93 device evidence](history/B93-DEVICE1.md).

B92 adds a read-only `[COMPATBOOT][CENREP_FIND_EQ_INT]` trace around the real CenRep FindEqInt request/result. It records repository UID, validated filter, comparison value, result count, and status only when CompatBoot is active. It preserves the existing IPC completion values, Native Boot default, stock firmware state, and readiness checks.

The latest change adds a read-only `[COMPATBOOT][MENU3_FSFLUSH]` trace for Menu3's FileServer `FileFlush` request. It records the caller, handle, path, flush result, and completion result only for the selected CompatBoot target UID3. The B48 flush implementation and its existing xnthemeserver trace remain intact; the change reuses `b48_flush_ok` and makes no second flush call.

FASTBUILD #302 (run `36279806117`) is **GREEN** on commit `c0a1056069cb709895c72ef9093e7dbb1d8ebcca`. B28 baseline, milestone application and regressions, iOS compile, binary invariant checks, unsigned IPA packaging, and upload all passed. Earlier retries were diagnostic: #299/#300 stopped applying the patch because the B28 source uses B48's `b48_flush_ok`; #301 exposed the missing complete config definition in `files.cpp`, fixed by including `<config/config.h>`. PR #6 remains open and unmerged.

Latest IPA artifact: [`EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36279806117/artifacts/10918187160) (ID `10918187160`), from [FASTBUILD #302](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36279806117). It expires 2026-10-10 23:36 UTC. Artifact ZIP size: 20,006,864 bytes. IPA SHA-256: `2c46be975611125673b19ae89b4e2220b20f10e390ab42d23afd30037e139331`.

On iPhone, open the [FASTBUILD #302 run page](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36279806117) in Safari while signed in to GitHub. Under **Artifacts**, download `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`. In Files, tap its ZIP once to extract it. The IPA is unsigned; import it into ESign Match (or the usual sideloading tool) to sign and install. Tapping the unsigned IPA in Files will not install it.

Next device test: install the FASTBUILD #302 IPA and select **CompatBoot Menu Probe**. Capture the fresh logs around the first `[COMPATBOOT][MENU3_FSFLUSH]`, including `path`, `flush_ok`, and `completion`, plus any subsequent `[COMPATBOOT][MENU3_LEAVE5]` and `[COMPATBOOT][TARGET_VISIBLE]`. Native Boot remains the default. This build only observes FileFlush; it does not infer the cause of `Leave(-5)`, change firmware/CenRep, force TFX, create guest files, fabricate services, or bypass the readiness barrier. PR #6 remains unmerged pending review and device validation.
