# B81 PHONEUIBLXDECODE1 — Build snapshot

Date: 2026-09-25
Branch: `nativeboot2-current`
Status: **BUILD-VALIDATED; DEVICE TEST REQUIRED**
Build commit: `42ca0136983714b01fd259120921188066c71af4`

## Why B81 exists

B80 DEVICE1 plus direct inspection of the exact RM-356 `SYM.ROM` callsite
bytes showed that the B79/B80 diagnostic decoder extracted Thumb-2 BLX
`imm10L` from the wrong bit positions. B81 corrects only that diagnostic
decode in the FileServer and CONE14 paths. No guest behavior, resource
registration, panic behavior, or host behavior changes.

## Binary evidence

RM-356 `PhoneUIUtils.dll`:
- code base: `0x80ED8DA8`
- code size: `0x6298`
- UID3: `0x101F4D0F`
- export count: `410`

Correctly decoded callsite targets:
| Callsite | Bytes | Correct target | Target bytes |
|---|---|---|---|
| `+0x1B70` | `02 F0 C0 ED` | `+0x46F4` | `04 F0 1F E5` |
| `+0x1B78` | `02 F0 8C ED` | `+0x4694` | `04 F0 1F E5` |
| `+0x3A34` | `00 F0 46 EE` | `+0x46C4` | `04 F0 1F E5` |

Each target is the start of an ARM `LDR pc, [pc, #-4]` veneer. The prior
B79/B80 outputs `+0x4274 / +0x41AC / +0x4350` were caused by reading the
second-halfword low immediate without shifting away bit 0. Correct extraction
is `((lo >> 1) & 0x03FF) << 2`, with PC base aligned as required by BLX.

Runtime expected addresses used by B81 contract:
- `0x80EDA918 -> 0x80EDD49C`
- `0x80EDA920 -> 0x80EDD43C`
- `0x80EDC7DC -> 0x80EDD46C`

## B81 changes and scope

Apply script: `apply_nativeboot2_b81_phoneuiblxdecode1.py`
Contract: `test_nativeboot2_b81_phoneuiblxdecode1.py`
Manifest: `ci/fastbuild1_manifest.txt`
Workflow binary gate: checks `target_decode=BLX_IMM10L_BITS_10_1`.

Both `fs.cpp` and `svc.cpp` use the corrected `imm10L` bits and expose a
decoder label in `[NBOOT2][PHONEUI_BLX_TARGET]`.

Preserved:
- diagnostic-only / `behavior=OBSERVE_ONLY`;
- PhoneUI resource registration unchanged;
- CONE panic behavior unchanged;
- B76 safe GameMenu unchanged;
- NOJAVA and MANIC3.

## Canonical GREEN

- Actions run: `36168367449` / #251
- Job: `108181574451`
- Commit: `42ca0136983714b01fd259120921188066c71af4`
- B28 bootstrap restore PASS; B19 fallback skipped
- B20-B81 apply and regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA packaging and artifact upload PASS
- IPA SHA-256: `f733443c48e5c6acde57e3e66d5dc706050a12e37afe0f7eb0f97cde427e5b16`
- IPA artifact: `10879995790`; ZIP digest `sha256:f6bdf5f9bdee61b01d66dfbb72633014c2ed72de9abcecf2c1cd5dd89d5ab881`
- Audit artifact: `10880155635`; ZIP digest `sha256:36db87e20f1d99e75f1c7d2460d2ac984c0e212c22d10b5b7b48a66848aa6757`
- Both artifacts expire 2026-10-09
- Compile requests/hits/misses: `152/150/2`
- Cache hit rate: `98.68%`; compilation failures: `0`
- Bootstrap restore: `41 s`; patch/regression: `5 s`; CMake build: `78 s`; package: `2 s`; total: `158 s`
- Xcode 16.4; Apple clang 17.0.0.13.5
- NOJAVA / MANIC3 preserved

## Device test

Install B81 over B80 on the same iPhone and use the same Nokia 5800 boot path.
Reproduce the existing Telephone startup failure, wait 5-10 seconds, then
exit through the Emulator normally. Send:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- `EKA2L1_Persistent-prev.log` if generated

The key check is that the three decoded calls now report targets
`+0x46F4 / +0x4694 / +0x46C4`, with corresponding 64-byte fingerprints.
Confirm the existing clean Exit Emulator path remains healthy. Do not send
video unless visible behavior changed.

## Decision gate after DEVICE1

Use the corrected B81 target locations and their fingerprints to compare
against exact RM-356 PhoneUIUtils code and export entries. Keep production
ordinal symbol labels unverified where the raw production export surface does
not establish them. Do not register `callhandlingui.r01` or otherwise change
guest behavior until the exact resource-init boundary is proven.
