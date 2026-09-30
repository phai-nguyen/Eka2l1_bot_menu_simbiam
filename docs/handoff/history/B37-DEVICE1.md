# B37 DEVICE1 — WSERVBATCHCOMPLETE1

Updated: 2026-09-22
Status: DEVICE-OBSERVED; signaling timing fix works as designed, but the EikAppUiServerThread Leave(-3) failure remains.

## Device log result

Primary B37 marker counts:
- WSERV_BATCH_DEFER_BEGIN: 604
- WSERV_BATCH_SIGNAL: 604
- WSERV_HANDLE_CARRY: 17
- WSERV_NONFADING_ENTER: 17
- WSERV_NONFADING_COMPLETE: 17
- EikAppUiServerThread EIKFAULT_LEAVE(-3): 16
- EIKFAULT_AV: 16
- EIKCALLSITE: 64
- KERN-EXEC 3: 16
- Object handle is invalid: 58

SetNonFading state changed exactly as intended by B37:
- signaled_before=0 on 17/17 entries
- signaled_after=0 on 17/17 SetNonFading completions
- WSERV_BATCH_SIGNAL then reports signaled_after=1 / completion_written_after=1

Therefore the request is no longer signaled from an individual command handler while a WindowServer batch is still running.

## Failure result

Despite the corrected signal timing, the repeated failure is unchanged:
- 16 User::Leave(-3) events
- pc=0x8029833C in euser.dll, offset 0x2EF4
- lr=0x802ABB29 in euser.dll, offset 0x166E0
- stack still contains ws32.dll + 0x370A and avkonfep.dll frames
- each Leave is followed by write access violation at address 0x10 and KERN-EXEC 3

For the first cycle:
- 21:16:45.688: a WindowServer batch of 1 command completes/signals
- 21:16:45.688: EikAppUiServerThread Leave(-3)
- 21:16:45.689: opcode 0x5D SetNonFading is parsed in a later 6-command batch
- 21:16:45.689: SetNonFading enters with signaled_before=0
- 21:16:45.689: SetNonFading completes KErrNone with signaled_after=0
- 21:16:45.689: batch signals once
- 21:16:45.689: guest access violation at 0x10 follows

Across the 16 cycles, Leave -> next SetNonFading entry is typically 0-1 ms, with a few longer intervals. This ordering shows SetNonFading is not the immediate server-side origin of KErrCancel.

## Source interpretation

Symbian WindowServer client source implements:
RWindowTreeNode::SetNonFading(TBool)
  -> WriteInt(aNonFading, EWsWinOpSetNonFading)

MWsClientClass::WriteInt() then writes into RWsBuffer. The WindowServer client-side architecture buffers non-synchronous commands and flushes them later as a batch.

Therefore the ws32 SetNonFading frame is a strong localization clue inside the AvkonFep path, but is not proof that the SetNonFading server handler generated Leave(-3).

## Exit Emulator

B34 exit remains healthy:
- os_join_begin 21:19:02.994
- os_join_done 21:19:03.016
- approximately 22 ms
- graphics_join_done and shutdown_done follow
- normal_restart_begin is reached

## Decision

B37 is not a causal fix for the EikAppUiServerThread failure. Do not promote it as a device-validated functional milestone.

Preferred B38 direction is diagnostic-only:
1. trace the exact WindowServer command opcode/object/completion for eiksrvs/EikAppUiServerThread around the batch immediately preceding Leave(-3);
2. resolve euser.dll PC 0x8029833C and LR 0x802ABB29 to nearest export ordinals and emit local code windows;
3. preserve B36 handle carry and B37 signal deferral unchanged;
4. do not alter FEP, completion values, Leave/trap behavior, SVCs, scheduler, loader, or exit choreography.

The purpose of B38 is to identify the actual guest/client-side KErrCancel origin before any further behavioral patch.
