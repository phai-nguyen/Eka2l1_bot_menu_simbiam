# SDD ledger — plan: docs/superpowers/plans/2026-09-21-fastbuild1-implementation.md

Execution mode: Native / executing-plans
Isolated workspace adaptation: GitHub branch nativeboot2-fastbuild1-design (not main).

Pre-flight interfaces:
- Task 1 -> Task 2: manifest CLI validate/apply/regress; interface consistent.
- Task 2 -> Task 3: shared bootstrap key and workflow contract; interface consistent.
- Task 2/3 -> Task 4: fast + seed workflows consumed for benchmark; interface consistent.
- Task 4 -> Task 5: measured run IDs/timings/artifacts consumed by docs; interface consistent.

Task 0: Ruling: use mozilla-actions/sccache-action@v0.0.11 instead of plan's v0.0.10 — current official Mozilla-Actions documentation/examples show v0.0.11; spec does not pin a version — cost if wrong: workflow action compatibility regression, caught by CI before promotion.

Task 1: complete — RED run 35611701170 failed on missing ci package as expected; GREEN run 35611811639 passed 4 manifest tests + manifest validation. Implementation commits e15d64c4..1d8a70ce.

Task 2: complete — RED run 35611963896 failed only because the fast workflow was absent; GREEN run 35612160731 passed the six Task-2 workflow contracts plus Task-1 suite and manifest validation. Fast workflow commit a0dae974. Ruling carried: sccache-action v0.0.11.

Task 3: complete — RED run 35612260312 failed only because the manual seed workflow was absent; GREEN run 35612350063 passed 4 manifest tests + 7 workflow contracts + manifest validation. Seed workflow commit 6e9c0c94.

Task 4: Ruling: the available GitHub connector has no workflow_dispatch mutation, so the cold seed will be executed once through a temporary push-triggered bootstrap workflow on nativeboot2-current, using the same verified seed logic/cache key, then that temporary workflow will be deleted. Final seed workflow remains manual-only. Cost if wrong: a wrongly scoped bootstrap cache; mitigated by branch check, exact key, B20-B28 contracts, build verification, and deleting the temporary trigger afterward.

Task 4: Finding before benchmark: seed workflow uses lookup-only=true, which would not materialize upstream on an existing-cache rerun while the audit still dereferences upstream. Must pin with RED and fix before seed.

Task 4 pre-benchmark fix: RED run 35612595589 proved seed lookup-only would not materialize upstream. RED run 35612699293 additionally proved malformed GitHub expressions existed in both workflows. Root cause: workflow-generation placeholder replacement normalized only one occurrence. Fix commits 74034811 + 981daa4d correct all expressions and make the seed restore materialize the cache. GREEN run 35612785024 passed the full FASTBUILD1 static suite.

Task 4 benchmark evidence: cold fallback run 35612768609 PASS (B19_FALLBACK, total 614s); seed run 35612902115 PASS; hot run 35614076698 PASS (B28_CACHE, total 71s); initial probe 35615089931 PASS (1 request/1 hit/0 miss, total 128s, no IPA); identical retry 35615429046 PASS (1 request/1 hit/0 miss, total 127s, no IPA); post-probe hot 35615810558 PASS (B28_CACHE, total 60s, IPA restored, SHA d077a550ae1120275d5a80f84200e15cff891ebc82f5f9229a52054111019182).

Task 4: Ruling: strengthen the one-file probe before promotion — official mozilla/sccache source hashes preprocessed C/C++ source, so an unused trailing #define can legitimately hit an existing baseline object and does not prove new-content write→reuse. Add a transient static_assert consuming the probe macro, run it once and rerun identically; require first run to issue exactly one request and establish a distinct cache entry, second run to hit it. Cost if wrong: ~2 extra CI runs; no committed runtime change because the probe touches only restored upstream.


Task 4 strong-probe evidence: run 35616222173 PASS with 1 request / 0 hit / 1 miss / 1 real compile / 0 write errors; identical retry 35616567861 PASS with 1 request / 1 hit / 0 miss / 0 compiles; post-probe normal run 35616906674 PASS with IPA restored.

Task 5: initial history/CURRENT promotion snapshot committed after the benchmark gate passed.

Final review: self-review (no subagent tool).

Final: fixed weak permanent one-file probe — test_probe_is_transient_and_never_uploads_ipa RED in run 35617848036, then GREEN in run 35618944698 after permanent workflow gained the compile-time static_assert; final permanent-equivalent probe run 35619278590 PASS with 1/1 cache hit and no IPA.

Final: fixed incomplete total timing scope — test_total_timing_covers_checkout_and_ipa_upload RED in run 35617848036, then GREEN in run 35618944698; corrected normal build run 35618944742 PASS with total_seconds=63 measured from before checkout through completed IPA upload.

Task 5 verification evidence: run 35618944698 passed 4/4 manifest tests + 9/9 workflow contract tests + manifest validation; run 35618944742 passed B20-B28, compile/link, NOJAVA/MANIC3, IPA packaging/upload, and produced SHA b289101c866bfa2a86e8046605d08299833b4dcdd0ea98e69425d78a7f93ff8d.
