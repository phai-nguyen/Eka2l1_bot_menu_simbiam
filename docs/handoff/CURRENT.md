# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-B88-2026-09-26.md](NEWCHAT-B88-2026-09-26.md)
Latest history: [B88-PHONEUICONE14CONTINUE1.md](history/B88-PHONEUICONE14CONTINUE1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Branch: `nativeboot2-current`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.
Acceptance goal: reach the Symbian Home/menu.

B87 FASTBUILD is GREEN and its IPA/audit were verified. The full RM-356 SYM.RPKG proves resource `0x1099B02D` is owned by `callhandlingui.r01/.r96`. Earlier device evidence shows Telephone UID3 `0x100058B3` panics CONE 14 and triggers the Phone startup failure before menu.

B88 FASTBUILD #270 (run `36229862894`) is GREEN. Regressions, iOS compile/link, B88 marker, IPA packaging, and audit all passed. IPA SHA-256: `3756273e80febcf43f48926877f9d810f734f5f49ee970d2fcbe94fa4783aa15`.

B88 changes only that exact Telephone panic into a clean termination (reason 0) so native startup can try to continue. This is a deliberate workaround; it does not fix resource registration. Device success requires the actual Symbian menu.
