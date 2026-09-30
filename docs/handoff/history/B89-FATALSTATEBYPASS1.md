# NATIVEBOOT2 B89 FATALSTATEBYPASS1

Date: 2026-09-26
Base: B88 device evidence, branch `nativeboot2-current`

## B88 device evidence

- B88 handles only the proven Telephone UID3 `0x100058B3`, category `CONE`,
  reason `14` panic as a clean process termination.
- The B88 device log confirms Telephone terminated peacefully, but SYSSTART
  then publishes `KPSGlobalSystemState 0x101F8766:0x41` from `101` to `116`.
- In the published P&S enum, `116` is `FatalStartupError`; the video remains at
  `Phone start-up failed. Contact the retailer.` and never shows the menu.
- Emulator exit completes normally; this B88 run did not reproduce the iOS
  crash-to-Home issue.

## B89 behavior

Arm a one-shot host flag only when the existing B88 exact Telephone/CONE/14
predicate is handled. When SYSSTART UID3 `0x100059C9` then writes the exact
global-state P&S key with `before=101` and `requested=116`, publish `109`
(`NormalRfOn`) instead. This aims to release the normal non-critical startup
list and Menu3 while bypassing the failed critical PhoneUI path and SIM
security sequence. All other P&S writes and thread exits remain unchanged.

Marker:

`[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]`

## Verification and acceptance

- B89 contract test must prove exact one-shot gating and refuse missing B88/B62
  predecessors.
- FASTBUILD must run the full manifest regression chain, iOS compile/link,
  binary marker check, IPA packaging and audit.
- Device success requires the visible Symbian Home/menu; seeing state 109 in a
  log is not sufficient. Report any subsequent failure as the next boot gate.

Build status: pending.
