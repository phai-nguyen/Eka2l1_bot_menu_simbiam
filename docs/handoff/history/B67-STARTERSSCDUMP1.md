# NATIVEBOOT2 B67 STARTERSSCDUMP1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Recommended install mode: INSTALL OVER B66

## Selection

B66 DEVICE1 captured the requested private/100059C9 text scripts, but those
files contain MD/CD/CP file-system initialisation commands and do not encode the
remaining Starter critical-state order.

The same device log proves SYSSTART opens:

Z:\resource\starter_arm.RSC

at 06:50:10.709, before Starter publishes global state 100.

B67 therefore targets the exact RM-356 Starter ROM resource instead of guessing
the remaining 101 -> 102 dependency from generic startup order.

## B67 behavior

New marker:

[NBOOT2][STARTER_SSC_DUMP]

When EFsrv opens exact path Z:\resource\starter_arm.RSC (case-insensitive),
B67 opens a separate VFS handle with:

READ_MODE | BIN_MODE

and captures up to 262144 raw bytes.

Output is uppercase hexadecimal in bounded 512-byte chunks. Hex is used so the
binary RSC can be reconstructed byte-for-byte without the escape-boundary
ambiguity of B66's text-oriented logger.

B67 does NOT:

- write, resize or remove any guest file;
- alter the guest EFsrv file subsession or cursor;
- set KPSGlobalSystemState;
- set KPSStartupAppState;
- alter SAServer IPC responses;
- alter process/rendezvous behavior;
- alter graphics or teardown behavior.

B61/B62/B64/B65/B66 behavior remains in the chain.

## Canonical GREEN

- run ID: 36076676081
- run number: 196
- job: 107889315577
- build HEAD: 7515a78766a72c03b308c67fee9f03b51d5ef692
- FASTBUILD1 manifest VALID
- B67 apply PASS
- B67 contract PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- bootstrap source: B28_CACHE
- bootstrap restore: 34 s
- patch/regression: 4 s
- CMake build: 65 s
- package: 3 s
- compile requests/hits/misses: 150/149/1
- cache hit rate: 99.33%
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

13c83e3cd126178c91e461ba672a4365a4ff3ca4981dbe87a1e57318cd80caec

IPA artifact:

- ID: 10840189166
- ZIP digest: sha256:6fc1bb01924cdaae903a9ea4c313a6189df4077d99140e1edab992370bc338c4
- expires: 2026-10-09

Audit artifact:

- ID: 10840243716
- ZIP digest: sha256:153ed497d5e7afa7223d3d69672edf67bb6ce1c18b34fe64e23dcb0dfc598498
- expires: 2026-10-09

## Device test

Install B67 over B66.

Run the normal RM-356 boot through NOKIA -> blank-white Startup. The target RSC
is opened very early in the Starter path, so no visual change is expected and
video is unnecessary unless behavior changes.

Exit normally and send:

- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Primary acceptance:

[NBOOT2][STARTER_SSC_DUMP]

must contain a complete begin/data/end sequence with:

- captured == raw_size
- truncated=false
- encoding=HEX

Once captured, concatenate data chunks by offset, decode the hex to exact
starter_arm.RSC bytes, then parse/decompile the SSC resource. The next
functional milestone must be chosen from the real RM-356 command/dependency
around StartingCriticalApps=101; do not directly force state 102.
