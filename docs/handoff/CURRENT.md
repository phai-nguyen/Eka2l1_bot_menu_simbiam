# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B89-FATALSTATEBYPASS1.md](history/B89-FATALSTATEBYPASS1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Active commit: `840314d898e72bcbd3d17fef5a01d452202e39fc`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test an explicitly selected CompatBoot path that waits for the UI services before launching firmware `menu3.exe`.

FASTBUILD #280 (run `36241579876`) is GREEN. It passed the B28 baseline check, manifest regressions, iOS compile, binary marker checks, unsigned IPA packaging, and upload. The IPA artifact is available for 14 days. Device validation is still needed to establish that the Menu3 surface becomes visible; no device result is recorded yet.

PR #6 is still open and unmerged. No firmware image or startup checks were changed to get this build through CI.
