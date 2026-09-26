# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B93 device evidence](history/B93-DEVICE1.md); [B92 device evidence](history/B92-DEVICE1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Latest build-validated commit: `a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test explicitly selected CompatBoot, which waits for the UI services before launching the real firmware `menu3.exe`.

The B92 method-2 run and B93 method-3 run both reached the readiness barrier and launched real `menu3.exe`, but neither produced `[COMPATBOOT][TARGET_VISIBLE]`. Both show five identical no-match `FindEqInt` queries against `0x102858F2`. Menu's own query occurs after the first trapped `Leave(-5)` and its first `TfxServer` miss. B93's video shows the Nokia logo, not the Symbian Menu; its logs record clean shutdown and normal restart, while the video ends on iOS Home without a crash report to identify how the app was closed. See [B93 device evidence](history/B93-DEVICE1.md).

B92 adds a read-only `[COMPATBOOT][CENREP_FIND_EQ_INT]` trace around the real CenRep FindEqInt request/result. It records repository UID, validated filter, comparison value, result count, and status only when CompatBoot is active. It preserves the existing IPC completion values, Native Boot default, stock firmware state, and readiness checks.

FASTBUILD #294 (run `36256303111`) is **GREEN** on commit `a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`. B28 baseline, all patch application/regressions, iOS compile, binary marker checks, unsigned IPA packaging, and artifact upload passed. FASTBUILD #293 stopped in the new test harness before compilation because `unittest` interpreted the upstream path as a test name; B92 now accepts the path and checks the patched B28 source. PR #6 remains open and unmerged.

Latest IPA artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA` (ID `10910382274`), from [FASTBUILD #294](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36256303111). It expires 2026-10-10 16:43 UTC. ZIP size: 20,003,715 bytes. SHA-256: `ba28cf8781426e5e698f6ccc8e700dc5600e118c3ffe5878069b9b484f384dc5`.

On iPhone, sign in to GitHub in Safari, open the FASTBUILD #294 run page, then download the IPA artifact under **Artifacts**. In Files, tap the ZIP once to extract it. The included IPA is unsigned; import it into ESign Match (or sign it with the user's normal sideloading tool) to sign and install. Tapping an unsigned IPA in Files will not install it.

Next: symbolize the first Menu `Leave(-5)` stack and decode FileServer opcode `0x27` using the RM-356 firmware and available symbols. B92 and B93 reproduce the same order; neither proves that the missing `TfxServer` caused the leave or that it prevents the menu surface. Do not change firmware, CenRep results, force TFX, create guest files, fabricate services, or bypass the barrier.
