# COMPATBOOT1-NOBYPASS1 handoff — 2026-09-27

## Goal

Validate the CompatBoot Menu3 probe with the NativeBoot PhoneUI/SYSSTART checks left intact. This is the second branch of the B97 follow-up; the separate Menu3-probing branch keeps the B89 behavior unchanged.

## Change in this branch

- Removed B88 Telephone CONE 14 reclassification and B89 SYSSTART `116 -> 109` override from the current FASTBUILD manifest.
- Kept B71 PhoneUI/CONE14 diagnostics and the original thread panic dispatch.
- Kept the original SYSSTART property write (`prop->set_int(value)`).
- Kept CompatBoot opt-in, its six-service readiness barrier, and the one-shot `menu3.exe` probe.
- Changed binary invariants to fail if either B88/B89 runtime marker is present.
- Tightened the B27 regression to require native PhoneUI panic and SYSSTART behavior.

The historical B88/B89 patchers and their standalone contract tests remain in the repository as archived milestones; they are no longer applied by the current manifest.

## Validation

- FASTBUILD #324, run `36318399524`, commit `a82d31a2626f8bd77e8e4c83ba57069b79ff252f`: **GREEN**.
  - B28 baseline and every manifest regression passed; B99 manifest-style test invocation passed.
  - iOS compile and binary checks passed. The binary contains `[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1`; the explicit binary gate confirmed both B88/B89 bypass markers are absent.
  - Unsigned IPA packaging and upload passed. Artifact [10931945136](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36318399524/artifacts/10931945136), ZIP size 20,011,253 bytes; retained until 2026-10-11 12:18 UTC.
  - IPA SHA-256: `1fe03ed0b2716066932a9a21c75e283f87196211453f1e40914f5338b5a78f70`.
  - Audit artifact ID: `10931770389`.
- Local regressions: 69 passed, 2 skipped because no upstream checkout is present locally. Manifest validation and `git diff --check` passed. The FASTBUILD run exercised the cached upstream B27 contract.
- Physical iPhone installation and runtime validation are pending. A successful build does not establish PhoneUI success or reaching the Symbian Home Screen.

## B99 iPhone test

- Download the IPA artifact from the link above on the iPhone (sign in to GitHub if prompted), save the ZIP in Files, and tap it once to extract it.
- Install the extracted IPA using the same signing/sideloading method used for the previous test builds.
- Keep the B98 logs. Install B99 over the current app, then start a new emulator session and collect fresh logs. A valid B99 log must contain the full B99 build marker above.
- Record whether `Phone start-up failed` appears, whether the app closes by itself or is exited manually, and whether the six-service barrier and real `menu3.exe` launch markers appear. Do not count the PhoneUI error screen as Home Screen success.
- Send the fresh log and, if available, a screen recording. This branch has not yet been validated on-device.

## Guardrails

- NativeBoot remains the default.
- No firmware substitution, PhoneUI failure bypass, or check suppression.
- Do not merge before FASTBUILD and device review.
- Keep PR #6 (`codex/compatboot1-menuprobe1`) as the independent B89/Menu3 investigation track.
