# FASTBUILD1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Create a long-lived "nativeboot2-current" GitHub Actions path that keeps B20-B28 regression coverage while replacing repeated 1.7 GB whole-tree cache churn with one stable B28 bootstrap and sccache-backed incremental C/C++ builds.

**Architecture:** Keep the existing B28 milestone workflow untouched. Add a small manifest helper for post-B28 work, a manual bootstrap seeder that creates one B28 "upstream" cache in the "nativeboot2-current" branch scope, and a fast development workflow that restores that cache, enables sccache, applies only post-bootstrap work, runs the full regression chain, builds, benchmarks, and packages the IPA. If the bootstrap is absent, the fast workflow falls back to the default-branch B19 cache and reconstructs B28, but it never saves the large "upstream" cache itself.

**Tech Stack:** GitHub Actions on macos-15, CMake 3.31.6, Clang, incremental CMake/Ninja build tree, Mozilla sccache, Python 3 standard library tests/helpers.

**Spec:** docs/superpowers/specs/2026-09-21-fastbuild1-design.md

## Global Constraints

- FASTBUILD1 is CI/build-system work only; do not change guest boot, FBS, UIKit exit, Symbian SVC semantics, firmware ownership, or committed runtime code under src/emu.
- Keep B20-current regression contracts, NOJAVA, MANIC3, build parallelism at --parallel 4, and the existing unsigned IPA packaging semantics.
- Normal fast builds must not save the whole upstream tree.
- Never cache secrets.
- Keep .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml byte-for-byte unchanged. Pinned Git blob: 44d1c8aaa7ff5f0ff97271396b8bf771ad125b54.
- Do not promote nativeboot2-current until the cold/bootstrap, hot/no-op, and one-file probe runs have all completed successfully and the hot path is materially faster than the B28 baseline of about 197 seconds.

## Review Focus

1. Missing or evicted bootstrap: the fast workflow must fall back to the default-branch B19 cache and reconstruct B28.
2. sccache backend I/O failure: SCCACHE_IGNORE_SERVER_IO_ERROR=1 must preserve normal compilation.
3. Stale/incompatible bootstrap: run the B28 contract before any post-bootstrap apply step; capture Xcode/Clang/CMake identities in audits, and bump the immutable bootstrap key version whenever runner image, Xcode/toolchain, generator/configuration, dependency revision, architecture/deployment target, bootstrap milestone, or build flags change.
4. Future manifest row references a missing file: manifest validation must fail before CMake.
5. Probe contamination: probe mode may change only the transient upstream svc.cpp and must publish no IPA.

## File Map

Create:
- ci/__init__.py
- ci/fastbuild1_manifest.py
- ci/fastbuild1_manifest.txt
- test_fastbuild1_manifest.py
- test_fastbuild1_workflows.py
- .github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml
- .github/workflows/build-ios-nativeboot2-current-fast.yml
- docs/handoff/history/FASTBUILD1.md

Modify only after benchmark success:
- docs/handoff/CURRENT.md

Do not modify:
- the B28 milestone workflow
- committed runtime source under src/emu

---

### Task 1: Add a manifest runner for post-bootstrap patches and regressions

**Files:**
- Create ci/__init__.py
- Create ci/fastbuild1_manifest.py
- Create ci/fastbuild1_manifest.txt
- Create test_fastbuild1_manifest.py

**Interfaces:**
- python3 ci/fastbuild1_manifest.py validate <repo-root>
- python3 ci/fastbuild1_manifest.py apply <repo-root> <upstream-root>
- python3 ci/fastbuild1_manifest.py regress <repo-root> <upstream-root>
- Section [post_bootstrap] contains apply_script|test_script rows.
- Section [regressions] contains one regression script per row.

- [ ] **Step 1: Write the failing tests**

Create test_fastbuild1_manifest.py with four tests:
- parse a manifest containing one apply/test pair and one regression;
- fail when a referenced script does not exist;
- verify apply order is patcher then its contract using unittest.mock on subprocess.run;
- verify the checked-in B28 manifest has no post-bootstrap pair and contains exactly B20 through B28 regression scripts.

Core test shape:

~~~python
import subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
import ci.fastbuild1_manifest as fb

class FastbuildManifestTests(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"m.txt"
            p.write_text("[post_bootstrap]\na.py|t.py\n[regressions]\nr.py\n")
            self.assertEqual(fb.parse_manifest(p), ([("a.py","t.py")],["r.py"]))

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); m=root/"m.txt"
            m.write_text("[post_bootstrap]\nmissing.py|test.py\n[regressions]\n")
            with self.assertRaisesRegex(SystemExit,"missing.py"):
                fb.validate_manifest(root,m)
~~~

Run:
~~~bash
python3 -m unittest -v test_fastbuild1_manifest.py
~~~
Expected: RED with ModuleNotFoundError for ci.fastbuild1_manifest.

- [ ] **Step 2: Add the initial B28 manifest**

ci/fastbuild1_manifest.txt:

~~~text
[post_bootstrap]
# B28 is the bootstrap checkpoint. Append B29+ apply|test pairs here.

[regressions]
test_nativeboot2_b20_cenresetall1.py
test_nativeboot2_b21_fbsfontalias1.py
test_nativeboot2_b22_fbsdefaulttypeface1.py
test_nativeboot2_b23_fbsfontspecv2abi1.py
test_nativeboot2_b24_fbsvtableabi1.py
test_nativeboot2_b25_fbssharedheap1.py
test_nativeboot2_b26_ioslibraryexit1.py
test_nativeboot2_b27_wservpanic13trace1.py
test_nativeboot2_b28_wservlibtype1.py
~~~

- [ ] **Step 3: Implement the helper**

Create empty ci/__init__.py. Implement ci/fastbuild1_manifest.py with:
- parse_manifest(path) -> (post_pairs, regression_list)
- validate_manifest(repo_root, manifest) that exits if any file is missing
- apply_post_bootstrap(repo_root, upstream, manifest) that runs each patcher then its test
- run_regressions(repo_root, upstream, manifest) that runs each test in order
- CLI commands validate, apply, regress.

Required execution primitive:

~~~python
def run_python(script: Path, upstream: Path) -> None:
    subprocess.run(["python3", str(script), str(upstream)], check=True)
~~~

Validation must happen before subprocess execution.

- [ ] **Step 4: GREEN**

Run:
~~~bash
python3 -m unittest -v test_fastbuild1_manifest.py
python3 ci/fastbuild1_manifest.py validate .
~~~
Expected: 4 tests pass and CLI prints FASTBUILD1-MANIFEST: VALID.

- [ ] **Step 5: Commit**

Commit message:
~~~text
ci: add FASTBUILD1 milestone manifest
~~~

---

### Task 2: Add the fast development workflow and static workflow contract

**Files:**
- Create test_fastbuild1_workflows.py
- Create .github/workflows/build-ios-nativeboot2-current-fast.yml

**Interfaces:**
- Consumes Task 1 CLI.
- Restores key eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1.
- Emits FASTBUILD1-BUILD-AUDIT.txt, FASTBUILD1-SCCACHE-STATS.txt, FASTBUILD1-IPA-SHA256.txt.
- Normal IPA name: EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa.
- Boolean workflow input probe_svc_change controls the one-file benchmark.

- [ ] **Step 1: Write RED static workflow tests**

test_fastbuild1_workflows.py must assert:
- git hash-object of the B28 workflow equals 44d1c8aaa7ff5f0ff97271396b8bf771ad125b54;
- fast workflow contains nativeboot2-current, the stable B28 bootstrap key, and B19 fallback key;
- fast workflow contains no actions/cache/save;
- sccache action is mozilla-actions/sccache-action@v0.0.11;
- SCCACHE_GHA_ENABLED is true and SCCACHE_IGNORE_SERVER_IO_ERROR is 1;
- CMAKE_C_COMPILER_LAUNCHER and CMAKE_CXX_COMPILER_LAUNCHER are sccache;
- B28 test appears before manifest apply;
- probe_svc_change, "#define NBOOT2_FASTBUILD1_PROBE 1", and "if: inputs.probe_svc_change != true" are present;
- timing labels bootstrap_restore_seconds, patch_regression_seconds, cmake_build_seconds, package_seconds, total_seconds are present;
- --parallel 4 and the current IPA packaging markers are present;
- seed workflow is manual-only and saves the exact B28 key.

Run:
~~~bash
python3 -m unittest -v test_fastbuild1_workflows.py
~~~
Expected: RED because the two FASTBUILD workflows do not exist.

- [ ] **Step 2: Create the fast workflow**

The workflow must implement this exact sequence:

1. workflow_dispatch with boolean probe_svc_change; push trigger only for nativeboot2-current.
2. macos-15 runner, contents: read.
3. Enable sccache:
~~~yaml
env:
  SCCACHE_GHA_ENABLED: "true"
  SCCACHE_IGNORE_SERVER_IO_ERROR: "1"
~~~
and:
~~~yaml
- uses: mozilla-actions/sccache-action@v0.0.11
~~~
4. Restore the stable B28 bootstrap key.
5. If the bootstrap misses, restore B19 key eka2l1-nativeboot2-b19-salangabi1-nojava-manic3-macos15-v1 and apply B20 through B28 scripts, then run the B28 contract.
6. Always run:
~~~bash
python3 ci/fastbuild1_manifest.py validate "$GITHUB_WORKSPACE"
python3 ci/fastbuild1_manifest.py apply "$GITHUB_WORKSPACE" "$UPSTREAM"
python3 ci/fastbuild1_manifest.py regress "$GITHUB_WORKSPACE" "$UPSTREAM"
~~~
7. Export SCCACHE_BASEDIRS="$UPSTREAM" and reconfigure the existing build directory:
~~~bash
"$CMAKE_BIN" -S "$UPSTREAM" -B "$UPSTREAM/build-ios-device" \
  -DCMAKE_C_COMPILER_LAUNCHER=sccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=sccache
sccache --zero-stats || true
~~~
8. If probe_svc_change is true, append only to the transient working tree:
~~~bash
printf '\n#define NBOOT2_FASTBUILD1_PROBE 1\n' >> "$UPSTREAM/src/emu/kernel/src/svc.cpp"
echo "FASTBUILD1_PROBE=1" >> "$GITHUB_ENV"
~~~
9. Build:
~~~bash
"$CMAKE_BIN" --build "$UPSTREAM/build-ios-device" --target eka2l1 --parallel 4
sccache --show-stats | tee "$GITHUB_WORKSPACE/FASTBUILD1-SCCACHE-STATS.txt"
~~~
10. Reuse B28 binary marker checks and NOJAVA/MANIC3 checks.
11. Package and upload IPA only when probe_svc_change is not true.
12. Never save upstream in the fast workflow.
13. Record start/end epochs and write:
~~~text
bootstrap_restore_seconds=
patch_regression_seconds=
cmake_build_seconds=
package_seconds=
total_seconds=
~~~
to FASTBUILD1-BUILD-AUDIT.txt.
14. Upload the audit with "if: always()".

- [ ] **Step 3: Task 2 GREEN**

Run all static contract tests except the seed-workflow test. Expected: all selected methods pass.

- [ ] **Step 4: Commit**

Commit message:
~~~text
ci: add FASTBUILD1 development workflow
~~~

---

### Task 3: Add the manual B28 bootstrap seeder

**Files:**
- Create .github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml

**Interfaces:**
- Manual-only workflow.
- Consumes B19 cache.
- Produces stable B28 key eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1.
- Produces FASTBUILD1-BOOTSTRAP-AUDIT.txt including xcodebuild -version, clang --version, and CMake --version.
- Does not package an IPA.
- The cache key is immutable. Refreshing the bootstrap requires intentionally bumping the terminal version component (for example v1 to v2) after one of the invalidation conditions in the spec changes.

- [ ] **Step 1: Confirm the remaining RED**

Run only the seed-workflow static test. Expected: FileNotFoundError.

- [ ] **Step 2: Implement the seed workflow**

Required header:

~~~yaml
name: Seed EKA2L1 FASTBUILD1 B28 Bootstrap
"on":
  workflow_dispatch:
permissions:
  contents: read
jobs:
  seed:
    runs-on: macos-15
    env:
      SCCACHE_GHA_ENABLED: "true"
      SCCACHE_IGNORE_SERVER_IO_ERROR: "1"
~~~

Then:
- checkout;
- fail unless GITHUB_REF_NAME is nativeboot2-current;
- enable mozilla-actions/sccache-action@v0.0.11;
- lookup the stable B28 key;
- on miss restore the B19 key;
- apply B20 through B28;
- run the Task 1 regression manifest;
- configure sccache launchers;
- build eka2l1 with --parallel 4;
- write sccache stats;
- run B28 contract, NOJAVA, and git diff --check;
- only after all verification passes, save:

~~~yaml
- uses: actions/cache/save@v4
  if: steps.bootstrap.outputs.cache-hit != 'true'
  with:
    path: upstream
    key: eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1
~~~

Upload bootstrap audit. Do not package or upload an IPA in this workflow.

- [ ] **Step 3: Full local GREEN**

Run:
~~~bash
python3 -m unittest -v test_fastbuild1_manifest.py test_fastbuild1_workflows.py
python3 ci/fastbuild1_manifest.py validate .
git diff --check
~~~
Expected: all exit 0; B28 blob pin remains unchanged.

- [ ] **Step 4: Commit**

Commit message:
~~~text
ci: add FASTBUILD1 B28 bootstrap seeder
~~~

---

### Task 4: Create nativeboot2-current and benchmark the three required paths

**Files:** no committed runtime files. Evidence comes from GitHub Actions runs and artifacts.

**Produces:** seed run ID, hot run ID, first probe run ID, identical probe-retry run ID, post-probe hot run ID, timing metrics, sccache stats, IPA SHA-256.

- [ ] **Step 1: Pre-branch verification**

Run the full Task 3 GREEN commands and:
~~~bash
git hash-object .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml
~~~
Expected exactly 44d1c8aaa7ff5f0ff97271396b8bf771ad125b54.

- [ ] **Step 2: Create the long-lived branch**

~~~bash
git branch nativeboot2-current HEAD
git push origin nativeboot2-current
~~~

- [ ] **Step 3: Cold/bootstrap seed**

~~~bash
gh workflow run seed-ios-nativeboot2-fastbuild1-bootstrap.yml --ref nativeboot2-current
gh run list --workflow seed-ios-nativeboot2-fastbuild1-bootstrap.yml \
  --branch nativeboot2-current --limit 1 --json databaseId,status,conclusion,url
gh run watch <SEED_RUN_ID> --exit-status
~~~

Expected: success; B20-B28 pass; compile/link pass; stable cache save succeeds; audit artifact exists.

- [ ] **Step 4: Hot/no-op build**

~~~bash
gh workflow run build-ios-nativeboot2-current-fast.yml --ref nativeboot2-current \
  -f probe_svc_change=false
gh run watch <HOT_RUN_ID> --exit-status
~~~

Download and inspect the FASTBUILD1 audit and sccache stats.

Expected:
- bootstrap source is B28_CACHE;
- B20-B28 pass;
- normal IPA and SHA exist;
- no whole-upstream save exists;
- hot total_seconds is lower than B28's ~197 seconds.
- Promotion threshold: total_seconds <= 150. The 30-90 second range is the optimization target, not a correctness requirement.

If total_seconds is over 150, do not promote. Identify the largest measured phase and optimize that phase without weakening validation.

- [ ] **Step 5: One-file C++ probe**

~~~bash
gh workflow run build-ios-nativeboot2-current-fast.yml --ref nativeboot2-current \
  -f probe_svc_change=true
gh run watch <PROBE_RUN_ID> --exit-status
~~~

Expected: success; audit says probe=1; sccache stats exist; IPA artifact is absent.

Immediately run the identical probe a second time with probe_svc_change=true. Expected: success again, no IPA, and sccache statistics show cache reuse for the repeated compile workload. Record both probe run IDs and both stats in the history snapshot.

- [ ] **Step 6: Post-probe normal build**

Run the hot workflow again with probe_svc_change=false.

Expected: success; normal IPA returns; the transient probe macro is absent because each run restores a clean bootstrap.

- [ ] **Step 7: Fix only evidence-backed failures**

Any workflow/helper failure must first be pinned by a failing Task 1 or Task 2 test, then fixed minimally, full local suite rerun, nativeboot2-current updated, and the affected benchmark rerun.

---

### Task 5: Record evidence and promote only if the gate passes

**Files:**
- Create docs/handoff/history/FASTBUILD1.md
- Modify docs/handoff/CURRENT.md only if promotion passes.

- [ ] **Step 1: Write the immutable history snapshot**

Record concrete values only:
- B28 baseline run 35606704683 and ~197 seconds;
- seed/hot/first-probe/probe-retry/post-probe run IDs and conclusions;
- bootstrap key and source;
- each timing field;
- sccache hits/misses;
- IPA SHA-256;
- B20-B28 results;
- NOJAVA/MANIC3 results;
- B28 workflow blob pin;
- promoted yes/no and measured reason.

Do not commit placeholders.

- [ ] **Step 2: Promotion rule**

Promote only if:
- seed, hot, first-probe, identical probe-retry, and post-probe runs all succeed;
- B20-B28 pass;
- B28 workflow pin is unchanged;
- probe publishes no IPA;
- normal build publishes an IPA;
- hot total_seconds <= 150.

On promotion, CURRENT.md must state:

~~~text
Active development branch: nativeboot2-current
Latest immutable functional milestone: nativeboot2-b28-wservlibtype1
FASTBUILD1 bootstrap: B28
FASTBUILD1 status: PROMOTED
~~~

And:

~~~text
Future B29/B30 work lands on nativeboot2-current first.
After build/device validation, snapshot the exact milestone commit into an immutable nativeboot2-bXX-* branch.
Do not use sibling milestone branches as the primary development/cache path.
~~~

If any gate fails, leave B28 active and record FASTBUILD1 as EXPERIMENTAL / NOT PROMOTED.

- [ ] **Step 3: Final verification**

~~~bash
python3 -m unittest -v test_fastbuild1_manifest.py test_fastbuild1_workflows.py
python3 ci/fastbuild1_manifest.py validate .
git diff --check
test "$(git hash-object .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml)" = \
  "44d1c8aaa7ff5f0ff97271396b8bf771ad125b54"
~~~

Expected: all commands exit 0.

- [ ] **Step 4: Commit documentation**

Commit message:
~~~text
docs: record FASTBUILD1 benchmark and rollout
~~~

- [ ] **Step 5: Final acceptance checklist**

~~~text
[ ] B28 milestone workflow unchanged
[ ] seed run success
[ ] B28 bootstrap cached in nativeboot2-current scope
[ ] hot run restores B28 bootstrap
[ ] normal fast run never saves whole upstream
[ ] sccache stats recorded
[ ] B20-B28 PASS
[ ] compile/link PASS
[ ] normal IPA + SHA produced
[ ] probe changes only transient svc.cpp
[ ] first probe publishes no IPA
[ ] identical probe retry publishes no IPA and demonstrates sccache reuse
[ ] post-probe normal IPA succeeds
[ ] hot total <=150 seconds for promotion
[ ] CURRENT.md status matches measured evidence
~~~

Only after every applicable box has concrete evidence may FASTBUILD1 be called complete.
