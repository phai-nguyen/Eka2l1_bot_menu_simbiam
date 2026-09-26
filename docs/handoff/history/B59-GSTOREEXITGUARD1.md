# NATIVEBOOT2 B59 GSTOREEXITGUARD1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B58 DEVICE1 crashes on "Thoát Emulator" with Apple EXC_BAD_ACCESS at address
0x18 inside gdi_store_command_segment::~gdi_store_command_segment during
kernel_system::wipeout.

B59 is intentionally limited to redraw-store segment teardown.

Stored FBS font/bitmap refs continue to deref normally while they are safely
owned. The destructor skips only null/exhausted refs or the unsafe final deref
case where:

- ref_count == 1
- owner == nullptr

This avoids entering ref_count_object::deref()'s owner->remove(this) path for an
ownerless final reference.

Marker:

[NBOOT2][GSTORE_EXIT_GUARD]

Fields identify font/bitmap, index, object presence, ref count, owner presence
and action SKIP_UNSAFE_FINAL_DEREF.

No Startup state, rendering, redraw scheduling, focus, compositor, TFX or guest
boot behavior is changed. B58 STARTUP_STATE_PS remains enabled.

## Canonical GREEN

- run ID: 35995597677
- run number: 169
- job: 107619640241
- HEAD: 656303d83d23efaf2a877a3ce2e69eb60ad9b652
- apply PASS
- B59 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0

Unsigned IPA SHA-256:

e77367744136b20ece0e0d93eca34ca0540b29b496f09d2fd5f6af26a76c191f

IPA artifact:

- ID: 10806605340
- ZIP digest: sha256:2ea72b00fd411765771e581054284c2993267cd2e175a94d5ce831290a5b240b
- expires: 2026-10-08

Audit artifact:

- ID: 10806047606
- ZIP digest: sha256:fbb3b44dadcf7fc4901d6c4eae2feaabdcf6651fc12788886d7e412c5bc86591
- expires: 2026-10-08

## Device acceptance

Run the same SIM-present normal boot path.

Primary B59 acceptance is exit stability:

1. Allow Nokia splash -> Startup white as before.
2. Open Emulator menu.
3. Select "Thoát Emulator".
4. The app should return to the emulator UI without iOS process crash.
5. Send the three EKA2L1 logs.
6. If iOS still creates a new .ips crash report, send it too.

Expected diagnostic if B59 hits the exact crash boundary:

[NBOOT2][GSTORE_EXIT_GUARD] ... owner_present=0 ... action=SKIP_UNSAFE_FINAL_DEREF

Boot progression is not expected to improve in B59; this build isolates and
repairs teardown before the next Startup synchronization probe.
