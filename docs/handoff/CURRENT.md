# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B90-COMPATBOOT1-DEVICE1.md](history/B90-COMPATBOOT1-DEVICE1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Latest build-validated source commit: `0bced6f0f897cfcce0e214ce77814177800c9887`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test an explicitly selected CompatBoot path that waits for the UI services before launching firmware `menu3.exe`.

FASTBUILD #281 (run `36241917700`) is GREEN on `0bced6f0f897cfcce0e214ce77814177800c9887`. B90 confirms real Menu3 launch but no visible surface. Stock V60 suppresses TFX at Themes CenRep `0x102818E8:0x09 = 0x7FFFFFFF`, so the first missing server `TfxServer` is consistent with firmware settings. The next diagnostic traces Menu3's later `Leave(-5)` caller/stack without changing leave behavior. Its source change and binary marker audit are awaiting FASTBUILD; device acceptance is pending.

PR #6 is still open and unmerged. No firmware image or startup checks were changed to get this build through CI.
