# B31 SCHEDREADYMM1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Active development branch: nativeboot2-current

## Purpose

B30 ROOTEDLIBPATH1 is device-validated for its intended loader blocker. The
Nokia 5800 firmware successfully resolves and loads:

`Z:\\sys\\bin\\EiksrvUi.dll`

and startup continues for roughly 30 seconds.

The next failure is a native iOS host crash:
- EXC_BAD_ACCESS / SIGSEGV
- KERN_INVALID_ADDRESS at 0x0
- faulting thread: Symbian OS thread
- top frame: `thread_scheduler::switch_context()+232`
- caller: `kernel_system::reschedule()+460`

Immediately before that crash, `akncapserver` is forcefully killed with
category `Domino`, reason `-33`.

Upstream EKA2L1 commit:

`437b29006bd8a0186f4070c9445f43e98e5c7435`

documents the matching failure class: a ready thread can outlive the memory
model of its owning process during teardown and then be passed to
`switch_context`.

B31 backports only that scheduler guard.

## TDD RED

Contract:

`test_nativeboot2_b31_schedreadymm1.py`

Temporary RED workflow:

`.github/workflows/test-nativeboot2-b31-schedreadymm1-red.yml`

RED run:
- run: 35679256321
- job: 106592402999
- B28 cache restore: PASS
- B29/B30 reconstruction: PASS
- B30 contract: PASS
- expected B31 failure:
  `NATIVEBOOT2-B31-SCHEDREADYMM1-TEST: FAIL: missing in scheduler.cpp B31 stale-ready guard: while (next_thread) {`

The temporary RED workflow was removed after the proof.

## Implementation

Apply script:

`apply_nativeboot2_b31_schedreadymm1.py`

Contract:

`test_nativeboot2_b31_schedreadymm1.py`

FASTBUILD manifest row:

`apply_nativeboot2_b31_schedreadymm1.py|test_nativeboot2_b31_schedreadymm1.py`

Only `thread_scheduler::reschedule()` is changed.

Before `switch_context(crr_thread, next_thread)`, B31:
1. examines `next_thread->owning_process()`;
2. accepts the ready thread only when the owner exists and
   `owner->get_mem_model()` is non-null;
3. otherwise emits:
   `[NBOOT2][SCHED_STALE_READY_DROP]`;
4. dequeues the stale ready entry;
5. retries `next_ready_thread()`;
6. only then enters `switch_context`.

This matches the narrow scheduler portion of upstream 437b290.

## Scope exclusions

B31 does NOT import:
- SVC 0xE3 / `Exec::GetModuleNameFromAddress`;
- SVC 0x2D / 0x48 / 0x4A / 0x50;
- timer callback lifetime fixes;
- HLE sleep changes;
- IPC/message lifetime changes;
- kernel teardown-order changes;
- object-container lifetime changes;
- ROM/E32 classification;
- relocation changes;
- other executive-table changes.

B30 ROOTEDLIBPATH1 remains intact.

NOJAVA and MANIC3 remain preserved.

## GREEN build

Authoritative GREEN run:

`35679378076`

Job:

`106592773474`

Build-tested code commit:

`6ccdd5c1b9101124981315322af5002dac057edc`

Result:
- FASTBUILD1 manifest VALID
- B29 CENREPTX1 PASS
- B29-DIAG1 PASS
- B29-LOADERDIAG1 PASS
- B30 ROOTEDLIBPATH1 PASS
- B31 SCHEDREADYMM1 PASS
- B20-B28 regression chain PASS
- iOS compile/link PASS
- binary invariant PASS
- packaged Mach-O contains `[NBOOT2][SCHED_STALE_READY_DROP]`
- IPA package/upload PASS

FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap restore: 31 s
- patch + regression: 1 s
- CMake build: 47 s
- package: 3 s
- total: 108 s
- compile requests: 12
- cache hits: 11
- cache misses: 1
- hit rate: 91.67%
- actual compilations: 1
- compilation failures: 0

Unsigned IPA:

`EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`

IPA SHA-256:

`adff1b39cf24ebf05abd2a3a01d01f14e68fc60106a79deab2e960574b4f5063`

IPA artifact:
- ID: 10674108825
- ZIP digest: `sha256:153f55848d52db74d5ac3f0c97b1a89be883ea1e0631b32d22d4abe57d2e4a05`
- expires: 2026-10-06

Audit artifact:
- ID: 10674800586
- ZIP digest: `sha256:a075f3d9905df94e7b4f55f662aa92f7c6c6ecb547c0073b212ce6b2be6fa79c`
- expires: 2026-10-06

Local post-download verification also reproduced the IPA SHA-256 exactly.

## Device validation

First B31 device run should reproduce the same Nokia 5800 boot sequence as B30
through the EiksrvUi load.

Inspect the late startup window around AknCapServer teardown.

Primary success condition:
- the app must NOT terminate with the B30 native stack
  `thread_scheduler::switch_context -> kernel_system::reschedule`.

Strong confirming marker:
- `[NBOOT2][SCHED_STALE_READY_DROP]`

If that marker appears and the host survives, the B30 scheduler-crash hypothesis is
confirmed.

If the host survives, use the next guest-side causal boundary. SVCMISS 0xE3 was
already observed in B30 and upstream maps it to `Exec::GetModuleNameFromAddress`,
but do not select it automatically unless the B31 device trace shows it is now the
first blocker.

If the same switch_context crash occurs without the marker, the B31 hypothesis is
not sufficient and the scheduler data flow must be instrumented further rather than
batching unrelated upstream lifetime fixes.
