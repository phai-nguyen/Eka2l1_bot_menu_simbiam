# NATIVEBOOT2 B66 STARTERSCRIPTDUMP1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Recommended install mode: INSTALL OVER B65

## Selection

B65 shows that the only StarterServer process rendezvous newly armed after
global state 101 is profilesettingsmonitor, and it completes reason=0.
Therefore there is no demonstrated post-101 process-rendezvous blocker.

Rather than infer the remaining Starter command order from generic Symbian SSM
resources, B66 reads the actual RM-356 classic Starter files used by this
firmware.

Targets:

- Z:\private\100059C9\ScriptInit.txt
- Z:\private\100059C9\script0.txt
- Z:\private\100059C9\script1.txt
- C:\private\100059C9\plg_script*.txt

## B66 behavior

New marker:

[NBOOT2][STARTER_SCRIPT_DUMP]

When EFsrv opens an exact target path, B66 opens a separate VFS handle with:

READ_MODE | BIN_MODE

and captures up to 65536 raw bytes. Bytes are escaped and emitted in bounded
log chunks.

The guest's own EFsrv file subsession and cursor are untouched.

B66 does NOT:

- write or resize any guest file;
- alter open modes/results;
- set KPSGlobalSystemState;
- set KPSStartupAppState;
- alter process/rendezvous behavior;
- alter the B64 self-test response;
- alter graphics or teardown behavior.

B61/B62/B64/B65 diagnostics remain in the chain.

## Build history

Runs 186-190 failed before C++ compile because B66's own contract checks used
brittle source-boundary detection / an over-broad string-resize predicate.
Those failures did not exercise runtime C++.

The final correction makes the contract anchor-independent and distinguishes
the harmless std::string buffer resize from guest file mutation.

## Canonical GREEN

- run ID: 36071875735
- run number: 191
- job: 107874453544
- build HEAD: c28fe41d9646ee1e6d3144a91efb0c98d9a2ce64
- B66 apply PASS
- B66 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 150/149/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

91146a96cd7a37a94021971b89f8a6c7458a77647b9e73be30d50dbb97053ef3

IPA artifact:

- ID: 10838543339
- ZIP digest: sha256:f9210f059c0053f7df942c35fe967fd170a2bfcdf123f16c04fd3fe87df5199d
- expires: 2026-10-08

Audit artifact:

- ID: 10838548231
- ZIP digest: sha256:00bfc197f6300ed96fe61d22931bb869706713e9368e41cdf779e764ed749630
- expires: 2026-10-08

## Device test

Install B66 over B65 for the cleanest comparison.

Run normal RM-356 boot through NOKIA -> blank-white Startup and leave it for
2-3 minutes, then exit normally.

Video is not needed unless the visible behavior changes.

Send all generated logs.

Primary B66 evidence:

[NBOOT2][STARTER_SCRIPT_DUMP]

The goal is to reconstruct the real RM-356 startup script/policy around the
StartingCriticalApps=101 phase and identify the exact command/dependency that
must complete before the transition to SelfTestOK=102.
