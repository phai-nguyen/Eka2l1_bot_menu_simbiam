# NATIVEBOOT2 B37 — WSERVBATCHCOMPLETE1

Updated: 2026-09-22

Status: DEVICE-OBSERVED; signal deferral works, causal failure remains.

## Baseline

B34 FOCUSMUTEXSPLIT1 remains the latest device-validated immutable functional milestone.

B36 WSERVHANDLECARRY1 is device-observed and proved that the WindowServer implicit destination-handle correction is active on device.

B36 device log summary:
- `[NBOOT2][WSERV_HANDLE_CARRY]`: 17
- `[NBOOT2][WSERV_NONFADING_ENTER]`: 17
- `[NBOOT2][WSERV_NONFADING_COMPLETE]`: 17
- `[NBOOT2][EIKFAULT_LEAVE]` for EikAppUiServerThread Leave(-3): 16
- SetNonFading calls use implicit handles successfully, primarily effective handle `0x00060006`.
- Every failing-path SetNonFading entry reports `signaled_before=1`.
- SetNonFading itself still completes `KErrNone` and reports `signaled_after=1`.

This shows the guest request had already been signaled before the later WindowServer command in the same command buffer was processed.

## B37 rationale

Symbian WindowServer processes the command buffer, keeps a reply value during command execution, and completes/signals the client message once after the complete command buffer returns.

The EKA2L1 baseline allows each command handler to call `ipc_context::complete()`, which writes request status and immediately signals the guest thread. During a multi-command WindowServer batch this can wake the guest while the host is still executing later commands in the same batch.

B37 changes only the request-signal timing for WindowServer command buffers:
- add opt-in `defer_request_signal` and `completion_written` state to `ipc_context`;
- `complete()` still writes the same completion value immediately;
- when deferral is active, `complete()` does not signal yet;
- WindowServer enables deferral before `execute_commands()`;
- WindowServer disables deferral and calls `flush_deferred_completion()` after the whole batch;
- the guest request is signaled once at batch end;
- if no command wrote a completion, batch flush supplies the WindowServer default `KErrNone`.

No FEP, Leave/trap, SVC, scheduler, loader, host exit, or B36 handle-carry behavior is changed.

New markers:
- `[NBOOT2][WSERV_BATCH_DEFER_BEGIN]`
- `[NBOOT2][WSERV_BATCH_SIGNAL]`

## TDD

RED:
- run: 35735338725
- job: 106771025304
- expected failure: `missing in ipc_context: bool defer_request_signal = false;`

GREEN:
- run: 35735710861
- job: 106772280995
- code HEAD: `dabed3de3d543d1700eca8b3394fead2a40ef94a`
- workflow: Build EKA2L1 NATIVEBOOT2 CURRENT FAST
- conclusion: SUCCESS
- manifest validate/apply/regression: PASS
- B37 contract: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA packaging/upload: PASS
- NOJAVA: PRESERVED
- MANIC3: PRESERVED

FASTBUILD audit:
- bootstrap source: B28_CACHE
- bootstrap restore: 49 s
- patch + regression: 2 s
- CMake build: 164 s
- package: 2 s
- total: 245 s
- compile requests: 149
- cache hits: 10
- cache misses: 139
- compilation failures: 0

Artifact:
- artifact ID: 10697426907
- IPA SHA-256: `80db395f1f6083c19b25a5b763fd04f43e9276001f3299a31bc3e54c19a5bf3d`

## Device-test acceptance

Install/sign B37 and boot the same Nokia 5800 path as B36.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Primary checks:
1. `WSERV_BATCH_DEFER_BEGIN` appears before WindowServer batch execution.
2. SetNonFading inside the batch should show `signaled_before=0` while deferral is active.
3. `WSERV_BATCH_SIGNAL` appears once after batch execution with `signaled_after=1`.
4. Compare the number/timing of EikAppUiServerThread Leave(-3) failures with B36.
5. B34 Exit Emulator choreography must remain healthy.

Do not promote B37 to an immutable device-validated branch until device evidence confirms the intended behavior.


## Cross-device corroboration

A second B36 device run on iPhone 8 Plus / iOS 15.6.1 via TrollStore reproduces the iPhone 12 Pro Max / iOS 18.7 signature almost exactly:
- 17 WSERV_HANDLE_CARRY
- 17 WSERV_NONFADING_ENTER
- 17 WSERV_NONFADING_COMPLETE
- signaled_before=1 for all 17 entries
- 16 EikAppUiServerThread Leave(-3)
- 16 access violations / KERN-EXEC terminations
- 58 invalid WindowServer handles, split 29 x 0x14000000 and 29 x 0

The same guest PC/LR and ws32 ordinal-206 path recur. This materially reduces the likelihood of an iOS-version/device-specific cause and strengthens B37's generic WindowServer batch-signal timing hypothesis.

Snapshot:
- docs/handoff/history/B36-DEVICE2-IP8PLUS-IOS15.md


## Device result — B37

B37 works exactly as designed at the IPC signaling boundary:
- WSERV_BATCH_DEFER_BEGIN = 604
- WSERV_BATCH_SIGNAL = 604
- SetNonFading signaled_before=0 on 17/17 calls
- SetNonFading signaled_after=0 on 17/17 calls
- the batch then signals once with signaled_after=1

However the causal failure is unchanged:
- EikAppUiServerThread Leave(-3) = 16
- EIKFAULT_AV = 16
- KERN-EXEC 3 = 16
- invalid WindowServer handle reports = 58

The first Leave occurs before the later batch that actually dispatches opcode 0x5D SetNonFading. Symbian source also shows SetNonFading only writes opcode/data into the WindowServer client buffer. Therefore the ws32 SetNonFading frame is a localization clue, not the immediate server-side KErrCancel origin.

B37 is not promoted as a causal/device-validated functional milestone.

Preferred B38: diagnostic-only trace of the command/result immediately preceding Leave(-3), plus exact euser PC/LR export/code resolution.

Snapshot:
- docs/handoff/history/B37-DEVICE1.md
