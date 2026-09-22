# B32 EIKSRVFAULTDIAG1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Active development branch: nativeboot2-current

## Why B32 exists

B31 SCHEDREADYMM1 is device-validated for the B30 native host scheduler crash.

The B31 device trace proves:
- B30 rooted EiksrvUi.dll loading remains healthy;
- `[NBOOT2][SCHED_STALE_READY_DROP]` fires exactly once for `akncapserver`;
- the old native `thread_scheduler::switch_context()` EXC_BAD_ACCESS does not recur;
- the session survives for more than 100 seconds after the marker;
- user exit later follows the existing B26 clean shutdown path.

Once that host crash is removed, the strongest repeated guest boundary is:
- 16 `eiksrvs` process spawns after the B31 marker;
- 16 `EikAppUiServerThread` access violations;
- 16 matching `KERN-EXEC 3` terminations.

Observed device fault families from B31:
1. 11 writes to address `0x10`, PC `0x802A01C4`, euser.dll + `0xAD7C`.
2. 5 reads from address `0x4`, PC `0x806EA236`, cone.dll + `0x13CE`.

The first euser fault occurs immediately after a trapped `Leave -3` sequence.

SVCMISS `0xE3` and `0x2D` are also observed, but the B31 log does not prove that either one is the direct cause of the repeated EikAppUiServerThread access violations.

Therefore B32 is diagnostic-only.

## Diagnostic contract

Test:

`test_nativeboot2_b32_eiksrvfaultdiag1.py`

B32 must add generic correlation at three boundaries without changing guest behavior.

### 1. Missing executive call

Marker:

`[NBOOT2][EIKFAULT_SVCMISS]`

Recorded fields:
- process;
- thread;
- SVC number;
- PC/LR/SP/CPSR;
- r0-r3.

The existing unimplemented-SVC path remains unchanged and still returns false.

### 2. KErrCancel leave/trap path

Markers:

`[NBOOT2][EIKFAULT_LEAVE]`
`[NBOOT2][EIKFAULT_LEAVE_FRAME]`
`[NBOOT2][EIKFAULT_LEAVE_STACK]`

Only `epoc::error_cancel` (-3) is deeply traced.

Recorded fields include:
- process/thread;
- trap-handler address;
- PC/LR/SP/CPSR;
- r0-r12;
- resolved module/base/offset for PC, LR and trap address where possible;
- 32 stack words with code-segment resolution where possible.

The original:
- `thr->increase_leave_depth()`;
- trap-handler return;
- leave completion behavior

remain unchanged.

### 3. Guest access violation

Marker:

`[NBOOT2][EIKFAULT_AV]`

Recorded fields:
- process/thread;
- read/write;
- fault address;
- PC/LR/SP/CPSR;
- r0-r12.

The original guest exception path remains unchanged:
`cpu_exception_thread_handle(core)` then the existing return behavior.

## Explicit exclusions

B32 does NOT:
- implement EPOC94 SVC 0x2D;
- implement or remap SVC 0xE3;
- backport `GetModuleNameFromAddress`;
- suppress KERN-EXEC 3;
- suppress access violations;
- change leave/trap semantics;
- change EikAppUi behavior;
- change IPC completion semantics;
- import timer, IPC lifetime, teardown-order, ROM/E32, relocation or unrelated executive-table changes.

B30 ROOTEDLIBPATH1 and B31 SCHEDREADYMM1 remain preserved.

NOJAVA and MANIC3 remain preserved.

## TDD RED

Temporary RED workflow:

`.github/workflows/test-nativeboot2-b32-eiksrvfaultdiag1-red.yml`

RED run:
- run: `35681056539`
- job: `106597890491`
- B29/B30/B31 reconstruction: PASS
- B31 contract: PASS
- expected B32 failure:

`NATIVEBOOT2-B32-EIKSRVFAULTDIAG1-TEST: FAIL: missing in libmanager.cpp B32 SVC diagnostics: [NBOOT2][EIKFAULT_SVCMISS]`

The temporary RED workflow was removed after the proof.

## Implementation

Apply script:

`apply_nativeboot2_b32_eiksrvfaultdiag1.py`

Contract:

`test_nativeboot2_b32_eiksrvfaultdiag1.py`

FASTBUILD1 manifest row:

`apply_nativeboot2_b32_eiksrvfaultdiag1.py|test_nativeboot2_b32_eiksrvfaultdiag1.py`

Production source touched by the apply script:
- `src/emu/kernel/src/libmanager.cpp`
- `src/emu/kernel/src/svc.cpp`
- `src/emu/kernel/src/kernel.cpp`

## Compile correction during GREEN

First full build:
- run: `35681214706`
- job: `106598360914`

Source contract and regressions passed, but C++ compilation correctly failed in `kernel.cpp` because B32 initially declared diagnostic local variables directly under a switch-case label.

Compiler error:
`cannot jump from switch statement to this case label`

with:
`jump bypasses variable initialization`.

Root cause:
C++ case-scope rules only; not an EKA2L1 semantic failure.

Correction:
wrap the access-violation diagnostic local variables in a lexical `{ ... }` scope inside the existing case.

No test, marker, guest behavior, or B32 diagnostic scope changed.

Corrected implementation commit:

`ca849738f8c1dd16949e687982904963c4bd8f6d`

## Authoritative GREEN build

Run:

`35681361472`

Job:

`106598810379`

Build-tested code commit:

`ca849738f8c1dd16949e687982904963c4bd8f6d`

Result:
- FASTBUILD1 manifest VALID;
- B29 CENREPTX1 PASS;
- B29-DIAG1 PASS;
- B29-LOADERDIAG1 PASS;
- B30 ROOTEDLIBPATH1 PASS;
- B31 SCHEDREADYMM1 PASS;
- B32 EIKSRVFAULTDIAG1 PASS;
- B20-B28 regression chain PASS;
- iOS compile/link PASS;
- packaged Mach-O contains `[NBOOT2][EIKFAULT_SVCMISS]`;
- packaged Mach-O contains `[NBOOT2][EIKFAULT_LEAVE]`;
- packaged Mach-O contains `[NBOOT2][EIKFAULT_AV]`;
- package/upload PASS.

FASTBUILD1 audit:
- bootstrap_source=B28_CACHE
- bootstrap restore: 40 s
- patch + regression: 1 s
- CMake build: 35 s
- package: 2 s
- total: 107 s
- compile requests: 14
- cache hits: 13
- cache misses: 1
- hit rate: 92.86%
- actual compilations: 1
- compilation failures: 0
- NOJAVA preserved
- MANIC3 preserved

Unsigned IPA:

`EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`

IPA SHA-256:

`9ef6e0f9b421cb20ed08c1ad03b1ebbe1c9274ba73b11a7977e78131a796e593`

The downloaded artifact was extracted locally after CI and the IPA SHA-256 was independently reproduced exactly.

IPA artifact:
- ID: `10675243561`
- size: 19,878,553 bytes
- ZIP digest: `sha256:e9f66f94d4f2d4258c4b4d9c0c748a43df5d199b050cb9f7871f58e55916e8e1`
- expires: 2026-10-06

Audit artifact:
- ID: `10674879017`
- ZIP digest: `sha256:da4633ec8c258d32d51cb678c7913b19af194062a25340de4948159a27f3a999`
- expires: 2026-10-06

## Device validation plan

B32 is not intended to visually change the boot result. It is an evidence build.

Device-test B32 until multiple `eiksrvs` / `EikAppUiServerThread` fault cycles have occurred, then use the existing safe Exit Emulator path and collect the standard logs.

The trace should be analyzed in this order:

1. Confirm B30 still reports `LDR_ROOT_RESOLVED` for EiksrvUi.dll.
2. Confirm B31 still reports the one stale-ready drop and no native host crash.
3. For each `[NBOOT2][EIKFAULT_AV]` whose process/thread belongs to eiksrvs/EikAppUiServerThread:
   - locate the immediately preceding `[NBOOT2][EIKFAULT_LEAVE]`;
   - inspect its resolved frame and stack markers;
   - locate nearby `[NBOOT2][EIKFAULT_SVCMISS]` entries and check their process/thread ownership.
4. Determine whether SVC 0x2D, SVC 0xE3, the trapped Leave -3 path, or another code path consistently precedes the fault in the same process/thread.
5. Only then select a functional compatibility fix.

Do not create an immutable B32 milestone branch until its device trace is analyzed.
