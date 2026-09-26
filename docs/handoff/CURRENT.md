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

FASTBUILD #281 (run `36241917700`) is GREEN on `0bced6f0f897cfcce0e214ce77814177800c9887`. B90 device logs confirm barrier readiness and launch of the real `menu3.exe`; the visible-surface marker did not fire. The earliest relevant gate is Themes CenRep `0x102818E8` key `0x09`, whose observed value `0x7FFFFFFF` matches the extracted stock V60 ROM setting and suppresses TFX. Menu3 then reports the first missing server as `TfxServer`. Generic repository save messages do not establish per-key writes. The current IPA artifact is available for 14 days.

PR #6 is still open and unmerged. No firmware image or startup checks were changed to get this build through CI.
