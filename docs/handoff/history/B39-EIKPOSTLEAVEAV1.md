# NATIVEBOOT2 B39 — EIKPOSTLEAVEAV1

Updated: 2026-09-22
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED.

## Purpose

B38 device evidence proved:
- the WindowServer CreateWindow immediately before all repeated Leave(-3) events succeeds;
- stock AvkonFep directly calls User::Leave(KErrCancel) when a nested state field is null;
- the Leave is caught successfully;
- the immediate fatal boundary is a later euser null write at address 0x10.

B39 is therefore diagnostic-only. It does not attempt a guest-behavior fix.

## TDD

Canonical RED:
- commit: f382cd9cdd3f39d9f41ec46a714c830897e0739f
- run: 35747370629
- job: 106812318986
- expected failure:
  NATIVEBOOT2-B39-EIKPOSTLEAVEAV1-TEST: FAIL: missing in AvkonFep state trace: [NBOOT2][EIKFEP_STATE]

Note: commit 5ef3535db7a0679e148d5691afa21fb4c6f772ac created the first test file, but its run is not canonical RED proof because the manifest did not yet execute the B39 regression.

Intermediate GREEN attempts:
- 3c4f9c47133bf26c6ae6a68d980ab123f4a025a8: implementation added; contract caught a source-format mismatch.
- b36063e9aad85391b812c5ee6739f3e7a0bb0529: contract/regressions passed; compiler caught switch-case scope lifetime issue in kernel.cpp.
- 7f845581ba32dd59fc5229ee24fa5979ef7cc81e: wrapped AV diagnostics in an inner scope without changing diagnostic semantics.

Canonical GREEN:
- code HEAD: 7f845581ba32dd59fc5229ee24fa5979ef7cc81e
- run: 35748481719
- job: 106816104243
- workflow conclusion: success
- B29-B39 apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compilation failures: 0
- NOJAVA / MANIC3: PRESERVED

FASTBUILD audit:
- bootstrap source: B28_CACHE
- bootstrap restore: 35 s
- patch/regression: 2 s
- CMake build: 74 s
- package: 3 s
- total: 139 s
- sccache hit rate: 99.33%

## New diagnostics

### AvkonFep Leave-boundary state

Marker:
- [NBOOT2][EIKFEP_STATE]

B39 uses the B38-proven User::Leave stack layout on this firmware:
- saved caller r4: current SP + 8
- saved caller LR: current SP + 12

It then performs mapping-checked, read-only inspection:
- caller_r4
- [caller_r4 + 0x10]
- [[caller_r4 + 0x10] + 0x24]

The log records each slot address, mapping flag, and value. It does not write guest memory.

### Post-caught-Leave access violation

Markers:
- [NBOOT2][EIKPOSTLEAVE_AV_FRAME]
- [NBOOT2][EIKPOSTLEAVE_AV_CODE16]
- [NBOOT2][EIKPOSTLEAVE_AV_STACK]

At the existing fatal access-violation path, B39:
- resolves PC and LR against the process's loaded codesegs;
- reports nearest preceding export ordinal/address/delta;
- dumps a bounded halfword code window around PC/LR;
- dumps up to 24 stack words and resolves code candidates.

The existing fatal exception path remains unchanged.

## Scope preserved

B39 does not:
- suppress KErrCancel;
- alter User::Leave / TRAP behavior;
- alter SVC 0xDF / 0xE0;
- patch or replace stock avkonfep.dll;
- hardcode the observed device PC/LR/AvkonFep addresses;
- alter WindowServer dispatch/completion;
- alter B36 handle carry;
- alter B37 signal deferral;
- alter scheduler/loader;
- alter B34 Exit Emulator choreography.

EPOC94 remains:
- 0xAA unmapped
- 0xAB = message_construct
- 0xAC = message_kill
- 0xDF = leave_start
- 0xE0 = leave_end

## Exa/source research

Public searches did not yield an exact Nokia 5800 / S60 5th Edition euser symbol map sufficient to identify euser +0xAD7C and +0xD9AD reliably. Available Symbian documentation supports the Leave/TRAP and cleanup-stack model but is not precise enough to name these two firmware offsets. Runtime export/code resolution is therefore required rather than guessing from offsets.

## Artifact

IPA artifact:
- ID: 10703293386
- artifact ZIP digest: sha256:d87cccf761bb2fcf9f6faebf25f5c852cbb060fd10abbb659aa1421e4b02ab46
- expires: 2026-10-06

Unsigned IPA:
- size: 19,950,168 bytes
- SHA-256: 94322fffc3f90e367e32081c2e52cdbdcfec32f47a8fff797447b4e897a85509

Audit artifact:
- ID: 10704033038
- digest: sha256:d29e9ab583ced3fcb620a94b242e1bf360fadb2c1a06bff39e24fd8b2f7240fa

## Device-test target

Install/sign B39 and reproduce the same Nokia 5800 startup path.

Collect:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Primary analysis:
1. compare all [NBOOT2][EIKFEP_STATE] cycles and determine exactly which nested AvkonFep state level is null;
2. resolve the fatal PC/LR from [NBOOT2][EIKPOSTLEAVE_AV_FRAME] to euser export ordinals;
3. decode [NBOOT2][EIKPOSTLEAVE_AV_CODE16] and correlate [NBOOT2][EIKPOSTLEAVE_AV_STACK] call candidates;
4. determine whether the post-catch AV is cleanup/destruction fallout from the same missing AvkonFep state or an independent emulator incompatibility;
5. confirm B34 Exit Emulator remains healthy.

Do not implement a behavioral B40 until B39 device evidence names the failing state/function.
