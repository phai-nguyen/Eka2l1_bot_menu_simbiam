# B96 — Menu3 EStor Leave stack export probe

Date: 2026-09-27

## Evidence motivating B96

B95 shows stock firmware TFX is intentionally suppressed by Themes CenRep
`0x102818E8:0x09 = 0x7FFFFFFF`. TFX components exist in ROM, but no plugin load
or public `TfxServer` registration is observed. The first Menu `Leave(-5)` is
logged 38 ms before Menu's own TfxServer miss, so that missing server is not
yet a demonstrated cause.

The B95 Leave stack has return-address candidates inside `estor.dll` and
`XnRequestClient.dll`. The current stack logger records module and offset but
not nearby export ordinals or instructions. B96 adds those details to the
existing scoped trace so the next device capture can resolve these frames.

## Change

New patcher: `apply_nativeboot2_b96_estorleaveexports1.py`.

For each guest code candidate found in the existing Menu3 `Leave(-5)` stack,
the patcher adds:

- `[COMPATBOOT][MENU3_LEAVE5_EXPORT]`: nearest preceding code export ordinal,
  address, delta, module, offset, and ARM/Thumb bit.
- `[COMPATBOOT][MENU3_LEAVE5_CODE16]`: a bounded halfword window from 8
  halfwords before through 4 after the candidate return address.

The output is read-only and remains inside the existing CompatBoot mode and
target UID3 `Leave(-5)` gates. It does not alter the guest code, memory,
`Leave`/trap behavior, firmware, TFX/CenRep, server registration, Native Boot
default, or service barrier. B96 is added after B94 in the FASTBUILD manifest;
the workflow now checks both marker strings in the compiled binary.

## Verification status

- B96 unit contract: 3 tests pass.
- Full unittest discovery: 62 tests pass, 2 upstream-dependent tests skipped
  (64 total).
- `python3 ci/fastbuild1_manifest.py validate .`: PASS.
- `git diff --check`: PASS.
- FASTBUILD #315 exposed a test assertion that started its source slice at the
  log marker, after the export lookup. The test now starts at
  `const auto compat_leave_exports`.
- FASTBUILD #316, run `36295344432`, is **GREEN** on commit
  `9268e8bfbf546afef801a3bd24c090a0bdb7affe`. Baseline, patch application,
  regressions, iOS compile, binary markers, unsigned IPA packaging, and upload
  passed. Audit: 121 seconds total, 43 seconds compiling, 3 seconds packaging.
- IPA artifact `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`, ID
  `10923757448`, expires 2026-10-11 04:49 UTC. IPA SHA-256:
  `cf9e2ce80f9748d23d04362ab7efe156c796ad935e8496da42dba3c722719cb2`.

On iPhone, open [FASTBUILD #316](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36295344432)
in Safari while signed into GitHub, download the IPA artifact ZIP, tap it in
Files to extract, and import the unsigned IPA into ESign Match or the usual
sideloading tool to sign and install. Then device-test in explicit CompatBoot
mode and retain logs/video. Interpret an absent TfxServer against the stock
disabled-TFX setting; do not force-enable TFX, fabricate the service, or bypass
the startup barrier. The primary question is which EStor operation is active
at the first Menu `Leave(-5)`.
