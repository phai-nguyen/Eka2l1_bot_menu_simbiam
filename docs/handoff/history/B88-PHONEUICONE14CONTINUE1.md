# NATIVEBOOT2 B88 PHONEUICONE14CONTINUE1

Date: 2026-09-26
Base: B87 CALLHANDLINGUICAPTURE1 FASTBUILD GREEN
Branch: `nativeboot2-current`

## Goal change

The user has explicitly changed the acceptance criterion: prioritize getting the RM-356 firmware to the Symbian menu, allowing targeted boot-path workarounds. The earlier diagnostic-only constraint is superseded for this task.

## Evidence

B70/B71 device evidence established that Telephone UID3 `0x100058B3` panics with category `CONE`, reason 14, after requesting resource ID `0x1099B02D`. The failure drives startup to state 116 (“Phone start-up failed”). B87 confirms from the complete RM-356 SYM.RPKG that the owner is `callhandlingui.r01/.r96`, but it did not change guest behavior.

## B88 change

At EKA2L1's `thread_kill` boundary, reclassify only the already-proven failure when all three conditions match:
- target process UID3 is Telephone `0x100058B3`;
- category is `CONE`;
- reason is 14.

For this case only, mark the process exit as `terminate`, category `None`, reason 0, so native Starter can continue rather than switching to the fatal startup screen. Every other panic and exit remains unchanged. This is an explicit startup compatibility bypass; it does not repair resource registration, and the Telephone process will be unavailable if startup proceeds.

## Verification

- Local B88 patch-contract tests: PASS (2 tests), including FASTBUILD's upstream-directory invocation.
- The earlier B27 regression prohibited any panic-result change. It was narrowed to permit only the B88 exception while still requiring the exact B71 UID/category/reason predicate.
- FASTBUILD #270: **GREEN** — run ID `36229862894`, head `fa20db9b687d8b6c2c27d7ead45fcb51e850d5b5`.
- B28 bootstrap validation and all manifest regressions: PASS.
- iOS compile/link: PASS; binary includes `[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]`.
- IPA packaging/upload and audit: PASS.
- IPA SHA-256: `3756273e80febcf43f48926877f9d810f734f5f49ee970d2fcbe94fa4783aa15`.

Device success means the RM-356 Symbian Home/menu is visibly reached; the B88 marker or state progression alone is not success. If B88 continues past the Phone failure but does not display the menu, next move to a direct firmware shell-launch fallback.
