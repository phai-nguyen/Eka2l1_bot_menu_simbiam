# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B91-POSTFIX-DEVICE1.md](history/B91-POSTFIX-DEVICE1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Latest build-validated source commit: `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test an explicitly selected CompatBoot path that waits for the UI services before launching firmware `menu3.exe`.

One post-B91 device attempt has now completed without the reported return-to-Home crash. The user reports normal exit, and the persistent log reaches `BRIDGE_EXIT_PHASE shutdown_done`. The install method was not stated, so this is one successful shutdown observation, not a clean-install validation series.

The same run reached the barrier and launched the real firmware `menu3.exe`, but emitted no `TARGET_VISIBLE` marker. Its first Menu3 failure marker is the stock-suppressed `TfxServer`; Menu3 continues past it. The first `Leave(-5)` is trapped after a successful FileServer `FileFlush`. The upstream CenRep enum/handler maps opcode 12 to `FindEqInt`; its value argument is Menu3 UID3 `0x101F4CD2`, and `-1` means no match. The query filter and repository UID are not logged, and the exact B28 handler still needs validation, so this is not yet a proven missing dependency. Menu3 later self-terminates with exit code 0. The missing `appshell.ini` entry is followed by a successful open. See [B91 post-fix device evidence](history/B91-POSTFIX-DEVICE1.md).

FASTBUILD #289 (run `36251856831`) is GREEN on `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`. B28 validation, all patch regressions, iOS build, binary invariants, unsigned IPA packaging, and upload passed. This build result is separate from the single device shutdown observation; device evidence still does not confirm a visible Menu3 surface.

Latest IPA artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA` (ID `10909561923`), from [FASTBUILD #289](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36251856831); expires 2026-10-10.

Next diagnostic: capture the CenRep repository UID and filter values for Menu3's `FindEqInt` request, then decide whether a no-match is expected. Keep NativeBoot default, firmware state, TFX suppression, and startup checks unchanged. PR #6 is still open and unmerged. No firmware image or startup checks were changed to get this build through CI.
