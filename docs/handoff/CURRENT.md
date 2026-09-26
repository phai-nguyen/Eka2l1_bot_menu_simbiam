# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-B89-2026-09-26.md](NEWCHAT-B89-2026-09-26.md)
Latest history: [B89-FATALSTATEBYPASS1.md](history/B89-FATALSTATEBYPASS1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Branch: `nativeboot2-current`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.
Acceptance goal: reach the Symbian Home/menu.

B88 device evidence: the exact Telephone CONE 14 was cleanly bypassed, and exiting the emulator completed the normal iOS shutdown path without returning to Home unexpectedly. The video still shows “Phone start-up failed”; the log proves SYSSTART then publishes P&S global state `101 -> 116` (FatalStartupError). The Symbian menu was not reached.

B89 is the next step: after and only after the exact B88 Telephone exit, rewrite SYSSTART's exact `KPSGlobalSystemState` transition `101 -> 116` to `109` (NormalRfOn). This aims to release the normal post-critical firmware startup list, including Menu3. Every other property transition stays unchanged. Build and device result are pending.

B88 FASTBUILD #270 (run `36229862894`) is GREEN. B88 changes only that exact Telephone panic into clean termination (reason 0). The full RM-356 SYM.RPKG proves resource `0x1099B02D` is owned by `callhandlingui.r01/.r96`; resource registration is still not fixed. Device acceptance remains an actual visible Symbian Home/menu.
