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
- Full unittest discovery: 63 tests pass, 1 upstream-dependent test skipped.
- `python3 ci/fastbuild1_manifest.py validate .`: PASS.
- `git diff --check`: PASS.
- FASTBUILD/iOS compile: pending; no IPA or GREEN status is claimed.

After FASTBUILD passes, device-test this IPA in explicit CompatBoot mode and
retain the usual logs/video. Interpret an absent TfxServer against the stock
disabled-TFX setting; do not force-enable TFX, fabricate the service, or bypass
the startup barrier. The primary question is which EStor operation is active
at the first Menu `Leave(-5)`.
