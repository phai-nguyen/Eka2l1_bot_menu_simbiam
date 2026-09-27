# B94 — CompatBoot teardown diagnostic build

Date: 2026-09-27

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`

PR: [#6](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)

Build: [FASTBUILD #313](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36290239618)

Source commit: `c83d4b3749ba0436ecf467ee25ba087f02a04b09`.

## Change

Added read-only CompatBoot diagnostics around process kill entry, property
cancellation, `notify_info::complete()` request-status resolution, and the
matching guest-address translation in the requester's process address space.
The trace records process/requester identity, property reference, request
status address, resolved host pointer, and whether property cancellation checks
the requester thread at that point. If the cancel path does not make a liveness
check, the trace records `requester_alive=-1` rather than adding one.

The patch preserves the existing status write, IPC completion result,
subscription removal, and requester signal behavior. Diagnostics are gated by
the explicit CompatBoot profile and scoped status-address resolution. Native
Boot remains the default; firmware, target launch, and the six-service barrier
are unchanged.

## Verification

FASTBUILD #313 is **GREEN**. B28 baseline validation, patch application,
regressions, iOS compile, binary invariants, unsigned IPA packaging, and artifact
upload passed. Local unittest discovery passed 41 tests (one skipped), and the
B94 patch contract passed 7 tests.

The IPA is a diagnostic build, not evidence that the B94 crash is fixed. The
crash cause remains unconfirmed until the device log and `.ips` capture are
correlated with these new markers. No Menu visibility result is established.

## IPA artifact

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10921448412`; expires 2026-10-11 03:04 UTC
- ZIP size: 20,011,779 bytes
- IPA in ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- IPA SHA-256: `f9e2a019dd92941fc73694f9d36eee22eebce5738c2e07cba3115c894514aa72`

On iPhone, open the FASTBUILD #313 run page in Safari while signed in to GitHub,
download the IPA artifact, extract the ZIP in Files, then import the unsigned
IPA into ESign Match or the user's usual sideloading tool to sign and install.
Files cannot install the unsigned IPA directly.
