# B92 — CompatBoot CenRep FindEqInt trace

Date: 2026-09-26

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`

PR: [#6](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)

Build-validated commit: `a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`

## Change

B92 adds `[COMPATBOOT][CENREP_FIND_EQ_INT]` around
`central_repo_client_subsession::find()` in `repo.cpp`. The request record is
emitted only when `compat_menu_probe_mode` is active and the opcode is
`cen_rep_find_eq_int`, after the filter and result-array descriptors pass the
existing validation. It records the attached repository UID, filter
`partial_key` and `id_mask`, signed comparison value, and whether that value is
available. The result record logs the existing result count and status for the
not-found and success paths. Existing completion calls and guest behavior are
unchanged. No repository values, firmware settings, startup checks, or Native
Boot defaults are changed.

This targets the unresolved B91 log entry: Menu3 CenRep opcode 12 returned
`-1`; upstream maps it to `FindEqInt`, with Menu3 UID3 `0x101F4CD2` as the
comparison value. The B91 log did not contain the repository UID or filter, so
it did not establish that the no-match was a fatal dependency.

## Verification

- FASTBUILD #293 applied B92 and B91 successfully, then stopped before
  compilation because the B92 test harness passed the upstream directory into
  `unittest` as a test-name selector. No compile or IPA result came from #293.
- The test harness now consumes the upstream path and checks the B28 source
  after patch application.
- FASTBUILD #294, run
  [36256303111](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36256303111),
  completed **GREEN** on `a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`.
  B28 baseline, manifest apply/regressions, iOS compile, binary marker checks,
  IPA package, and artifact upload all passed.
- Local Python test discovery passed 52 tests (one test skips without a
  FASTBUILD upstream path). Manifest validation and `git diff --check` passed.

## IPA

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10910382274`
- IPA file: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- SHA-256: `ba28cf8781426e5e698f6ccc8e700dc5600e118c3ffe5878069b9b484f384dc5`
- Expires: 2026-10-10 16:43 UTC

The artifact ZIP can be downloaded from the FASTBUILD #294 run page in Safari
while signed in to GitHub, then extracted in Files. The IPA is unsigned and
must be signed through ESign Match or the user's normal sideloading workflow.

## Device state and next step

The latest device capture still has no `[COMPATBOOT][TARGET_VISIBLE]` marker.
It did not return to iOS Home on exit. The install method was not recorded, so
this is not a clean-install validation result. At the next CompatBoot run,
retain the full log and inspect the new FindEqInt request/result records for
repository and filter values, then check whether Menu3 becomes visible. Do not
change the stock firmware value, force-enable TFX, create `appshell.ini`,
fabricate a server, or bypass service readiness.

PR #6 remains open and unmerged.
