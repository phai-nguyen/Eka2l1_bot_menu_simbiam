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

- `python3 -m unittest discover -v`: 64 passed, 2 skipped because no FASTBUILD upstream checkout was supplied.
- `python3 ci/fastbuild1_manifest.py validate .`: passed.
- `git diff --check`: passed.
- FASTBUILD #321, run `36310459634`, commit `1611e3533306a604435c9b12d59f7606ecfeb879`: GREEN.
  - B28 baseline and all manifest regressions passed, including updated B27 panic/SYSSTART assertions.
  - iOS compile, binary invariants, unsigned IPA packaging, and artifact upload passed.
  - Binary check confirmed B88 and B89 bypass markers are absent.
  - IPA artifact: [download from GitHub Actions](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36310459634/artifacts/10929206594), 20,009,182-byte ZIP, available until 2026-10-11.
  - IPA SHA-256: `acb839f04d3aa4e51ee6999877586f0fcd7033bf353f7a52936baedd3f6de021`.
  - Audit artifact ID: `10928393854`.
- Device installation and runtime validation: pending; this workflow produced an unsigned IPA.

## Guardrails

- NativeBoot remains the default.
- No firmware substitution, PhoneUI failure bypass, or check suppression.
- Do not merge before FASTBUILD and device review.
- Keep PR #6 (`codex/compatboot1-menuprobe1`) as the independent B89/Menu3 investigation track.
