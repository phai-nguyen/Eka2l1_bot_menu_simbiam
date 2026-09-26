# NATIVEBOOT2 B88 PHONEUICONE14CONTINUE1

Date: 2026-09-26
Base: B87 CALLHANDLINGUICAPTURE1 FASTBUILD GREEN
Branch: `nativeboot2-current`

## Goal change

The user has explicitly changed the acceptance criterion: prioritize getting the RM-356 firmware to the Symbian menu, allowing targeted boot-path workarounds. The earlier diagnostic-only constraint is superseded for this task.

## Evidence

B70/B71 device evidence established that Telephone UID3 `0x100058B3` panics with category `CONE`, reason 14, after requesting resource ID `0x1099B02D`. The failure drives startup to state 116 (“Phone start-up failed”). B87 confirms from the complete RM-356 SYM.RPKG that the owner is `callhandlingui.r01/.r96`, but it did not change guest behavior.

## B88 change

At the existing EKA2L1 `thread_kill` boundary, reclassify only the already-proven failure when all three conditions match:
- target process UID3 is Telephone `0x100058B3`;
- category is `CONE`;
- reason is 14.

For this case only, mark the process exit as `terminate`, category `None`, reason 0, so native Starter can continue rather than switching to the fatal startup screen. Keep every other panic and exit unchanged. This is an explicit startup compatibility bypass; it does not repair resource registration, and the Phone/Telephone process will be unavailable if startup proceeds.

## Gates

- Local B88 patch-contract tests: PASS (2 tests).
- FASTBUILD must pass B28 bootstrap validation, all manifest regressions, iOS compile/link, binary marker check for B88, IPA packaging, and audit.
- Device success means the RM-356 Symbian Home/menu is visibly reached; the B88 marker or state progression alone is not success.
- If B88 proceeds past the Phone failure but does not display the menu, the next step is to bypass the blocking startup dependency and launch the firmware shell path directly.

