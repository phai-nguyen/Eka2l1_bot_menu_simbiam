# B83 PHONEUICENREPDIAG1 — Native descriptor/status probe

Date: 2026-09-26
Branch: `nativeboot2-b82-callhandlingui-register`
Status: **PATCH IMPLEMENTED; LOCAL CONTRACTS PASS; BUILD/DEVICE TEST PENDING**

## Scope

B83 is diagnostic-only. It adds three native software-breakpoint callbacks
for the exact RM-356 `centralrepository.dll` path. The callbacks read registers
and log; they do not modify guest registers, register resources, change the
CONE lookup, or add global fallback behavior.

The callbacks are compiled through the native-patches path used by iOS
(`ENABLE_SCRIPTING_LUA` is not defined there); no LuaJIT hook is required.
Each software breakpoint briefly pauses the emulated core while its callback
runs, then the original guest instruction is restored and execution resumes.

## Verified addresses and captured fields

RM-356 CentralRepository UID3 is `0x101FBC70`; runtime E32 code base is
`0x80391CF8`. Thumb function addresses set bit zero:

| Boundary | Thumb pointer | Captured data |
|---|---:|---|
| `+0x43C` entry | `0x80392135` | incoming object `r0`, descriptor pointer `r1`, `lr` |
| `+0x448` after `+0xF60` | `0x80392141` | returned status `r0`, saved object `r5`, descriptor pointer `r6` |
| `+0x4CA` caller continuation | `0x803921C3` | returned status `r0`, object `r4` |

The descriptor is logged by pointer only; its guest memory is not decoded.
The last marker proves normal return to the wrapper. A missing marker alone
does not prove a Leave; it must be correlated with Leave/panic and surrounding
PhoneUI/CONE records.

## Files and verification

- `apply_nativeboot2_b83_phoneuicenrepdiag1.py`
- `test_nativeboot2_b83_phoneuicenrepdiag1.py`
- `ci/fastbuild1_manifest.txt`
- `.github/workflows/build-ios-nativeboot2-current-fast.yml`
- `docs/handoff/CURRENT.md`

Local checks run:

- B83 contract test: PASS
- B83 patch re-application: idempotent
- FASTBUILD1 manifest validation: PASS
- `test_fastbuild1_manifest.py` and `test_fastbuild1_workflows.py`: PASS
- `git diff --check`: PASS

The workspace has no iOS compiler/FASTBUILD runner, so B83 has not yet been
compiled, packaged, or device-tested. Do not treat the patch as build-GREEN.
After an authorized build and RM-356 device run, correlate the B83 markers with
EFSrv `callhandlingui.r01` activity and PhoneUI's CONE lookup. B79 and earlier
are out of scope for this continuation.
