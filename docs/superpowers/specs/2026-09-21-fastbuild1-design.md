# FASTBUILD1 Design — EKA2L1 Nokia 5800 NativeBoot CI

Date: 2026-09-21  
Status: Implemented and promoted on `nativeboot2-current` (2026-09-21)  
Baseline functional branch: `nativeboot2-b28-wservlibtype1`  
Design branch: `nativeboot2-fastbuild1-design`  
Active implementation branch: `nativeboot2-current`

## 1. Purpose

Reduce the turnaround time for iterative iOS IPA builds of the Nokia 5800 NativeBoot project without weakening functional regression checks or changing emulator behavior.

The current workflow is correct but inefficient for rapid B29/B30/... iteration because each milestone branch tends to rebuild from an older shared baseline and stores a very large whole-`upstream` cache.

FASTBUILD1 is CI/build-system work only. It must not modify guest boot semantics, FBS behavior, UIKit exit behavior, Symbian SVC behavior, or firmware ownership.

## 2. Current measured baseline

B28 successful run:

- Workflow run: `35606704683`
- Total job duration: about 3 minutes 17 seconds
- Restored cache size: about 1.739 GB
- Cache restore: about 45 seconds
- Recreate B27 from B19 + apply B28: about 1 second for patch/test scripts
- CMake build/link portion: about 83 seconds
- Whole-`upstream` cache save: about 41 seconds
- IPA packaging/upload: single-digit seconds

The most important observation is that cache transfer/compression alone consumes roughly 86 seconds of the run.

GitHub cache behavior also explains why milestone branches do not form a reliable parent/child cache chain: workflow runs can restore caches from the current branch and default branch, but sibling branch caches are isolated.

## 3. Success criteria

FASTBUILD1 is successful only if all of the following hold:

1. No emulator source behavior changes are required solely for FASTBUILD1.
2. B20–current regression contracts continue to run.
3. NOJAVA and MANIC3 invariants remain checked.
4. The generated IPA remains equivalent in build configuration to the milestone workflow.
5. Repeated development builds on the same long-lived branch are materially faster than the B28 baseline.
6. Retry builds after small C/C++ changes benefit from compiler cache hits.
7. Full milestone snapshot branches remain possible and reproducible.
8. CI failures remain diagnosable; speed must not come from skipping validation.

Initial performance target:

- Hot iterative build: aim for 30–90 seconds wall-clock when changes touch only a small number of translation units.
- This is a target, not a guarantee; the first implementation must benchmark actual runner behavior.

## 4. Chosen architecture

### 4.1 Long-lived development branch

Introduce a long-lived development branch:

`nativeboot2-current`

Future B29/B30/... development happens on this branch.

When a milestone is build-validated or device-validated, create an immutable snapshot branch from the exact commit, for example:

- `nativeboot2-b29-...`
- `nativeboot2-b30-...`

This preserves historical milestone branches while keeping the active CI cache in one branch scope.

### 4.2 Separate bootstrap state from compiler cache

Use two distinct cache layers.

#### Layer A — bootstrap/incremental build baseline

Keep one intentionally stable baseline containing the prepared upstream tree, build directory, tools, and already-built B28 state.

This cache is restored on `nativeboot2-current` but is not rewritten on every ordinary development build.

Why:

- preserving the configured build tree gives CMake incremental-build metadata immediately;
- avoiding a new 1.7 GB save on every run removes roughly 40 seconds from the current measured path;
- a stable baseline avoids cache-quota churn.

Checkpoint policy:

- refresh the large bootstrap cache only deliberately, such as every several milestones or after dependency/toolchain changes;
- do not create a new 1.7 GB cache per commit.

### 4.3 Add sccache for C/C++ compilation

Use Mozilla `sccache` with the GitHub Actions backend.

CMake integration:

```
-DCMAKE_C_COMPILER_LAUNCHER=sccache
-DCMAKE_CXX_COMPILER_LAUNCHER=sccache
```

Runtime environment:

```
SCCACHE_GHA_ENABLED=true
SCCACHE_IGNORE_SERVER_IO_ERROR=1
```

Also set `SCCACHE_BASEDIRS` to the workspace/upstream root so cache keys do not depend unnecessarily on absolute build paths.

Purpose:

- unchanged translation units can reuse compiled objects;
- retries after a failed link/package step should not recompile;
- a later build starting from an older bootstrap checkpoint can still recover compilation work from prior runs.

sccache must be treated as an optimization only. A cache miss must fall back to normal Clang compilation.

### 4.4 Keep source-level regression tests

Do not remove B20–current Python contracts.

They are inexpensive compared with cache transfer and C++ compilation, and they protect accumulated NativeBoot behavior.

FASTBUILD1 may reorganize them into one clearly named regression step, but it must not silently skip older contracts.

### 4.5 Build parallelism

Retain current parallelism initially:

`--parallel 4`

Do not raise this speculatively. The first FASTBUILD1 benchmark will measure whether the hosted macOS runner is CPU-bound before changing concurrency.

### 4.6 IPA packaging

Keep current unsigned IPA packaging semantics unchanged:

- copy app into `Payload/EKA2L1.app`
- remove `_CodeSignature`
- remove `embedded.mobileprovision`
- ZIP as unsigned IPA
- validate archive
- calculate SHA-256
- upload IPA and audit artifacts

## 5. Workflow layout

Create one development workflow, conceptually:

`.github/workflows/build-ios-nativeboot2-current-fast.yml`

High-level sequence:

1. Checkout repository.
2. Install/enable sccache.
3. Restore stable FASTBUILD bootstrap cache.
4. If bootstrap is unavailable, reconstruct from the pinned known-good fallback path.
5. Apply all milestone scripts after the bootstrap checkpoint up to current HEAD.
6. Run current contract plus full regression chain.
7. Reconfigure the existing CMake build directory to use sccache.
8. Build `eka2l1`.
9. Print sccache statistics.
10. Validate binary markers and NOJAVA/MANIC3 invariants.
11. Package unsigned IPA.
12. Upload IPA and audit artifacts.
13. Do not save the entire `upstream` tree on every normal run.

A separate manually triggered checkpoint workflow may refresh the large bootstrap cache when intentionally requested.

## 6. Benchmark design

FASTBUILD1 must be measured rather than assumed faster.

Record these timestamps/metrics in the audit artifact:

- bootstrap restore duration
- patch/regression duration
- CMake build duration
- sccache hit/miss counts
- IPA packaging duration
- total job duration

Run at least these cases:

### Case A — cold bootstrap

No FASTBUILD bootstrap cache available.

Expected outcome:
- slower than hot build;
- still functionally equivalent.

### Case B — hot no-op rebuild

Same source state, rerun workflow.

Expected outcome:
- very high compiler-cache/incremental reuse;
- establishes best-case floor.

### Case C — one-file C++ change

Change only a narrow file such as `svc.cpp`.

Expected outcome:
- compile affected translation unit(s), not broad project rebuild;
- unchanged units should be incremental/sccache hits.

The B28 run (~197 seconds) is the comparison baseline.

## 7. Safety and invalidation

The bootstrap cache must be invalidated when any of these materially change:

- runner OS/image family
- Xcode/toolchain
- CMake generator/configuration
- dependency/submodule revision
- architecture/deployment target
- bootstrap milestone
- build flags that affect object compatibility

sccache naturally hashes compiler inputs and flags, but explicit cache-buster metadata should be used if a toolchain transition is ambiguous.

Never cache secrets.

## 8. Branch and milestone policy

After FASTBUILD1 proves itself:

1. `nativeboot2-current` becomes the only active development branch.
2. New functional work lands there.
3. Successful/device-tested milestones are snapshotted to named Bxx branches.
4. `docs/handoff/CURRENT.md` points to the active development commit plus the latest immutable milestone snapshot.
5. A snapshot branch is historical evidence; it is not the primary location for future cache evolution.

This reverses the current pattern where every Bxx branch becomes the next development branch.

## 9. Alternatives considered

### Alternative A — keep milestone-per-branch and add more restore keys

Rejected as the primary design.

GitHub cache branch isolation prevents sibling milestone branches from reliably sharing each other's caches. Restore keys do not remove that scope boundary.

### Alternative B — save the entire upstream tree on every run

Rejected for normal iterative builds.

Measured B28 save time is about 41 seconds and the cache is about 1.739 GB. Repeating this on every small edit wastes time and repository cache quota.

### Alternative C — compiler cache only, no incremental bootstrap

Useful but incomplete.

sccache would reduce compilation, but a fresh source/configure/dependency setup on every run would still add avoidable latency. FASTBUILD1 therefore combines a stable bootstrap with compiler caching.

## 10. Rollback

FASTBUILD1 must be additive.

If the new workflow is slower or unreliable:

- milestone B28 workflow remains untouched and usable;
- delete/disable the FASTBUILD workflow;
- continue from `nativeboot2-b28-wservlibtype1`;
- no emulator code rollback is needed because FASTBUILD1 changes CI only.

## 11. Implementation boundary

FASTBUILD1 implementation may change:

- GitHub Actions workflow files
- CI helper scripts
- build/cache audit documentation
- branch strategy documentation

It must not change, unless separately approved for a functional milestone:

- `src/emu/**` runtime behavior
- Symbian SVC semantics
- FBS behavior
- NativeBoot startup ownership
- iOS frontend behavior

## 12. Verification gate

Before declaring FASTBUILD1 complete:

- one successful cold/bootstrap build;
- one successful hot/repeat build;
- B20–B28 contracts all PASS;
- iOS compile/link PASS;
- IPA packaging PASS;
- SHA-256 produced;
- sccache statistics recorded;
- measured timing comparison against B28 documented;
- confirm B28 milestone workflow still exists unchanged.

Only after these checks should `nativeboot2-current` be promoted as the normal development path.
