# NATIVEBOOT2 B87 CALLHANDLINGUICAPTURE1

Date: 2026-09-26
Base: B86 FASTBUILD GREEN, branch `nativeboot2-current`

## Firmware result

The complete user-supplied RM-356 `SYM.RPKG` has 8,030 entries and is 134,540,934 bytes (SHA-256 `bc41496abc8d4c87de976b65cadfb922b4dfd9583a0dbcf35b7e4bff23eb008f`). It contains `Z:\\resource\\apps\\callhandlingui.r01` (1,968 bytes) and `callhandlingui.r96` (2,101 bytes).

Both files have UID1 `0x101F4A6B`, UID3 `0x0001099B`, and resource #1 signature bytes `04 00 00 00 01 B0 99 10`. EKA2L1's RSC reader masks the signature offset to `0x1099B000`. Both files contain 46 resources; resource ID `0x1099B02D` maps to entry 45 and exists in both locale files. Entry 45 is 82 bytes and has the same SHA-256 in both: `b68066cbcc54e33815bf24862532172b694d3715cf778af252920a5229ad4e55`.

This confirms callhandlingui as the exact ROM owner of the resource ID. The resource is present; B85's VPbk candidate was a false lead.

## Timeline clarification

The supplied crash/log capture is the B85 run at 14:05–14:07 +0700. B86 was committed and its FASTBUILD completed afterward at 14:18 +0700 (run 36226370083). Therefore the B85 exit crash does not establish whether B86 reproduces the user's exit crash condition.

B85 logs show VPbk resource opens shortly before Telephone CONE14 but no callhandlingui open in the recorded flow. This leaves the actual registration/open path as the remaining guest-side question.

## B87 scope

- Retarget the bounded, separate read-only resource capture from VPbk to both exact RM-356 ROM locale paths for callhandlingui.
- Rename the runtime marker to `[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B87]`; require the marker in the FASTBUILD binary.
- Keep resource registration, guest behavior, panic semantics, startup chain, and iOS exit/teardown unchanged.
- Use the B87 runtime log to establish whether PhoneUI opens either owning RSC before the missing-resource panic. If no open occurs, trace resource registration/call path before making a functional change.

Local contract and B85→B86→B87 patch-chain tests passed. FASTBUILD result pending.
