# FASTBUILD1 — Promoted CI/Build-System Snapshot

Date: 2026-09-21
Status: PROMOTED
Active development branch: nativeboot2-current
Latest immutable functional milestone: nativeboot2-b28-wservlibtype1
FASTBUILD1 bootstrap milestone: B28 WSERVLIBTYPE1

## Scope

FASTBUILD1 changes CI/build strategy only. It does not change committed runtime behavior under src/emu, Symbian SVC semantics, FBS behavior, iOS frontend behavior, or firmware/SYSSTART ownership.

Permanent files:
- ci/__init__.py
- ci/fastbuild1_manifest.py
- ci/fastbuild1_manifest.txt
- test_fastbuild1_manifest.py
- test_fastbuild1_workflows.py
- .github/workflows/build-ios-nativeboot2-current-fast.yml
- .github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml

The B28 milestone workflow remains byte-for-byte unchanged:
- .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml
- Git blob: 44d1c8aaa7ff5f0ff97271396b8bf771ad125b54

## Architecture

Normal development builds on nativeboot2-current:
1. restore stable B28 bootstrap cache;
2. validate B28 before applying any post-bootstrap work;
3. apply manifest-listed B29+ patch/test pairs, if any;
4. run B20-B28 regression contracts;
5. reconfigure the existing CMake build tree with sccache launchers;
6. build eka2l1 with --parallel 4;
7. validate B28/B27/B25/B26/EMUHUB markers plus NOJAVA/MANIC3;
8. package the unsigned IPA;
9. upload IPA + audit;
10. never save the large upstream tree during a normal fast run.

Stable bootstrap cache key:
eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1

Fallback cache key:
eka2l1-nativeboot2-b19-salangabi1-nojava-manic3-macos15-v1

sccache configuration:
- mozilla-actions/sccache-action@v0.0.11
- SCCACHE_GHA_ENABLED=true
- SCCACHE_IGNORE_SERVER_IO_ERROR=1
- SCCACHE_BASEDIRS=<absolute upstream root>
- CMAKE_C_COMPILER_LAUNCHER=sccache
- CMAKE_CXX_COMPILER_LAUNCHER=sccache

Toolchain captured by bootstrap:
- macos-15
- Xcode 16.4 / build 16F6
- Apple clang 17.0.0 (clang-1700.0.13.5)
- CMake 3.31.6
- sccache 0.18.0

## Baseline

Original B28 milestone build:
- run: 35606704683
- wall-clock baseline: about 197 seconds
- whole-upstream cache: about 1.739 GB
- milestone workflow remains available as rollback/repro path

## Bootstrap seed

Seed run:
- run: 35612902115
- conclusion: SUCCESS
- branch: nativeboot2-current
- bootstrap key: eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1
- audit artifact: 10645835312
- audit ZIP digest: sha256:820d6e03121899bb0602c2d0624f95ac284c4f51e2fa4d4eb6e99815748a956a

Seed sccache stats:
- compile requests: 953
- hits: 551
- misses: 402
- hit rate: 57.82%
- cache write errors: 337
- compilation failures: 0

The seed's broad write-error count did not fail the build because sccache is an optimization and compiler fallback is preserved. The exact cause of those write errors was not established. Subsequent one-file probe writes completed with zero write errors and were reusable on the next run.

The available GitHub connector did not expose workflow_dispatch, so the first seed was executed once through a temporary push-triggered clone of the verified manual seeder. That temporary workflow was deleted immediately after the successful seed. The permanent seeder remains manual-only.

## Cold fallback proof

Run:
- 35612768609
- conclusion: SUCCESS
- bootstrap source: B19_FALLBACK
- B20-B28: PASS
- bootstrap_restore_seconds: 43
- patch_regression_seconds: 1
- cmake_build_seconds: 534
- package_seconds: 3
- total_seconds: 614

Cold sccache:
- requests: 953
- hits: 4
- misses: 949

Cold IPA:
- SHA-256: d8340315fe9ed5e54d03e81f019002331cc4d6fb221b0ad6d45ab79d3caa998b
- artifact: 10645810490
- artifact ZIP digest: sha256:2913d3ee1ae6e01c45226fd3b4281196be525593621ed48d297f1568f28b5ce1
- audit artifact: 10645580674
- audit ZIP digest: sha256:596fcb7bfe78c076d160e22d8cb367064787411063ade393cdb848d5026e927f

Conclusion: missing/evicted B28 bootstrap is slow but still functional and reconstructs from B19 without weakening validation.

## Hot no-op proof

Run:
- 35614076698
- conclusion: SUCCESS
- bootstrap source: B28_CACHE
- B20-B28: PASS
- bootstrap_restore_seconds: 45
- patch_regression_seconds: 0
- cmake_build_seconds: 1
- package_seconds: 2
- total_seconds: 71
- compile requests: 0

IPA:
- SHA-256: 06e12037d1ec584d9b2439639264949b7c1e29d3c0fad6a9e32191942f75249f
- artifact: 10645149495
- audit artifact: 10645164448

This run established the hot incremental behavior. Its original `total_seconds=71` was measured with the pre-final-review timer scope (start after checkout; audit before IPA upload), so it is retained as historical evidence but is not the final promotion timing metric.

## One-file compiler-cache proof

The original plan probe appended only:
#define NBOOT2_FASTBUILD1_PROBE 1

Runs 35615089931 and 35615429046 each produced one compile request and one cache hit. That satisfied the written contract but was weaker evidence than desired because sccache hashes C/C++ preprocessed source; an unused trailing macro can map to an existing preprocessed cache entry.

A stronger transient probe was therefore used:
- append the same probe macro to restored upstream/src/emu/kernel/src/svc.cpp;
- append a compile-time-only static_assert consuming the macro;
- do not commit any runtime source;
- do not package or upload an IPA.

Strong probe first run:
- run: 35616222173
- conclusion: SUCCESS
- B20-B28: PASS
- total_seconds: 125
- compile requests: 1
- cache hits: 0
- cache misses: 1
- compilations: 1
- cache write errors: 0
- average compiler: 13.654 s
- audit artifact: 10645784068
- no IPA artifact

Identical strong-probe retry:
- run: 35616567861
- conclusion: SUCCESS
- B20-B28: PASS
- total_seconds: 107
- compile requests: 1
- cache hits: 1
- cache misses: 0
- compilations: 0
- cache read errors: 0
- average cache read hit: 0.096 s
- audit artifact: 10645974229
- no IPA artifact

Conclusion: a new one-file C++ input causes exactly one miss/compile/write, and the identical retry reuses that new cache entry with a 100% hit rate.

## Post-probe clean-state proof

After removing the temporary strong-probe workflow, a normal fast build restored the untouched B28 bootstrap rather than carrying transient svc.cpp state.

Run:
- 35616906674
- conclusion: SUCCESS
- bootstrap source: B28_CACHE
- probe: 0
- B20-B28: PASS
- compile requests: 0
- total_seconds: 56
- IPA SHA-256: 93309733268b7319d26c133d0d35a407a027f6f2b2c5e5830eac0eb21a24e106
- IPA artifact: 10646224390
- audit artifact: 10646662018

Final clean verification run after removing benchmark trigger comments:
- run: 35617195868
- conclusion: SUCCESS
- code HEAD: 8dc0423c9cdcf8fa353e16eae9ec8359b1587f66
- bootstrap source: B28_CACHE
- B20-B28: PASS
- compile requests: 0
- bootstrap_restore_seconds: 31
- patch_regression_seconds: 0
- cmake_build_seconds: 1
- package_seconds: 3
- total_seconds: 69
- IPA SHA-256: be170c9e03f9fe901c775a323d00e16411752beb68950e4bbd7e46097fabaf1f
- IPA artifact: 10647395134
- IPA artifact ZIP digest: sha256:85d2c5d421702a5694f0e8043eff7b3a06268fee482a7ebe63f4b1a0aa2a984e
- audit artifact: 10646479731
- audit ZIP digest: sha256:5dc95adcd3f97e0672495184180d5c38b69fee693d91d30a82f0236f8ab2d095

Static/TDD verification on the same clean HEAD:
- run: 35617195978
- conclusion: SUCCESS
- manifest unit tests: 4/4 PASS
- workflow contract tests: 8/8 PASS
- FASTBUILD1 manifest: VALID
- B28 workflow blob pin: PASS

## Final review corrections

A whole-branch self-review found two Important CI-evidence issues after the first promotion snapshot:

1. The permanent `probe_svc_change` path still appended only an unused `#define`. Because sccache keys C/C++ work from preprocessed source, that can legitimately resolve to the baseline object's cache key and is weaker than a real changed-preprocessor-output probe.
2. `total_seconds` started after checkout and was written before IPA artifact upload, so it did not cover the full primary deliverable path.

TDD RED:
- run: 35617848036
- code HEAD: 9aec70c2dbe8d0be6c5d31da204dced49cfb558e
- expected failures: exactly 2
  - permanent workflow missing `static_assert(NBOOT2_FASTBUILD1_PROBE == 1, "FASTBUILD1_PROBE_V2");`
  - `Mark FASTBUILD start` ordered after checkout / audit ordered before IPA upload

Minimal fix:
- implementation commit: 9381a02b131102ac6f1088ae077411d27f753132
- permanent probe now appends the macro plus compile-time-only `static_assert`
- FASTBUILD start timestamp is captured before checkout
- `Write FASTBUILD audit` runs after `Upload IPA`; with `if: always()`, probe runs still create audit after the intentionally skipped IPA step

GREEN static/TDD:
- run: 35618944698
- conclusion: SUCCESS
- manifest tests: 4/4 PASS
- workflow contract tests: 9/9 PASS
- manifest: VALID

Corrected-scope normal hot build:
- run: 35618944742
- conclusion: SUCCESS
- code HEAD: 9381a02b131102ac6f1088ae077411d27f753132
- bootstrap source: B28_CACHE
- B20-B28: PASS
- compile requests: 0
- cache errors: 0
- bootstrap_restore_seconds: 36
- patch_regression_seconds: 0
- cmake_build_seconds: 1
- package_seconds: 2
- total_seconds: 63
- NOJAVA: PRESERVED
- MANIC3: PRESERVED
- IPA SHA-256: b289101c866bfa2a86e8046605d08299833b4dcdd0ea98e69425d78a7f93ff8d
- IPA artifact: 10647737754
- IPA artifact ZIP digest: sha256:572666f0e0fbbf8f824aa3febd211188da67859316431d015b494b1121653809
- audit artifact: 10647383101
- audit ZIP digest: sha256:933d3407fbb27c8009559bbb9d7a191c3ac48f2eb8aecb573e6b2eafca345a02

Final permanent-equivalent probe verification:
- run: 35619278590
- conclusion: SUCCESS
- B20-B28: PASS
- probe: 1
- strong `static_assert` probe present
- compile requests: 1
- cache hits: 1
- cache misses: 0
- hit rate: 100%
- IPA artifact: ABSENT
- audit artifact: 10647023252
- audit ZIP digest: sha256:f841bab9236770ce4aa3af311aaa11e27dda5d408b106cd97e185dcb6402558d

The connector still does not expose workflow_dispatch, so that final probe used a temporary push-triggered clone of the corrected permanent workflow with the probe forced on. The temporary workflow was deleted after success.

The final promotion timing is therefore `total_seconds=63` from run 35618944742, measured from before checkout through completion of the IPA upload step.

## Promotion decision

Promotion gate: PASS.

Evidence:
- cold fallback succeeds;
- B28 bootstrap seed succeeds;
- hot no-op succeeds;
- strong one-file probe produces one real miss/compile/write;
- identical retry produces one hit and zero misses;
- probes publish no IPA;
- normal post-probe build publishes IPA;
- B20-B28 pass throughout;
- NOJAVA and MANIC3 are preserved;
- B28 milestone workflow blob remains 44d1c8aaa7ff5f0ff97271396b8bf771ad125b54;
- final corrected-scope hot total is 63 s, below the 150-second promotion threshold.

FASTBUILD1 status:
PROMOTED

## Development policy from here

Future B29/B30 work lands on nativeboot2-current first.

After build/device validation, snapshot the exact milestone commit into an immutable nativeboot2-bXX-* branch.

Do not use sibling milestone branches as the primary development/cache path.

When adding a new milestone after B28:
1. add its apply_script|test_script pair under [post_bootstrap] in ci/fastbuild1_manifest.txt;
2. retain B20-current regression coverage;
3. build/test on nativeboot2-current;
4. device-test as required;
5. snapshot the validated commit to the immutable Bxx branch.

Refresh the large bootstrap intentionally only when a documented invalidation condition changes, including runner image, Xcode/toolchain, CMake generator/configuration, dependency revision, architecture/deployment target, bootstrap milestone, or build flags affecting object compatibility.
