# NATIVEBOOT2 B41 DEVICE1 — device validation

Updated: 2026-09-23
Branch: nativeboot2-current
Promoted immutable branch: nativeboot2-b41-wservmessagewinexit1
Status: DEVICE-VALIDATED

## Summary

The user confirms B41 fixes the native iOS crash triggered by **Thoát Emulator**.
The three device logs independently support the report and also validate the
B40 Loader PDD root-cause fix.

## B40 boot evidence

At 05:59:23.443:

```
[NBOOT2][LOADER_PDD] phase=enter name=EUART1
[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0
```

The canonical eiksrvs instance continues through initialization and at
05:59:23.820 registers the real System GUI server:

```
[NBOOT2][SERVER_REGISTER] process=eiksrvs[10003a4a]0001 server=!EikAppUiServer handle=1079115815 mode=0
```

The previous B39 fatal family is absent:

- EIKFEP_STATE: 0
- EIKFAULT_AV: 0
- EIKPOSTLEAVE_AV_FRAME: 0
- EikAppUiServerThread KERN-EXEC 3: 0
- Loader opcode-4 unimplemented warning: 0

Therefore B40 is DEVICE-VALIDATED and the B39 NULL-session root-cause chain is
closed.

## B41 exit evidence

Relevant exit starts at 06:00:26.675-06:00:26.676.

At 06:00:26.683 B41 emits the exact causal guard twice:

```
[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout
[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout
```

The OS-thread join that crashed in B40 now completes:

```
06:00:26.676 phase=os_join_begin
06:00:26.700 phase=os_join_done
```

The rest of B34 shutdown choreography also completes:

```
06:00:26.701 phase=graphics_join_done
06:00:26.701 phase=shutdown_threads_done
06:00:26.701 phase=state_reset_done
06:00:26.701 phase=shutdown_done
06:00:26.854 phase=normal_restart_done has_device=1
```

No host-crash boundary interrupts the sequence. This is the expected behavior
for the B41 MessageWin wipeout guard.

## Promotion

B41 is promoted as the latest immutable functional milestone.

Immutable branch:
`nativeboot2-b41-wservmessagewinexit1`

Validated code HEAD:
`b43e59696d313da97c8845a1a20e78d9b6c762d7`

Build:
- GREEN run: 35794136142
- job: 106969339936
- apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- compilation failures: 0

## Log integrity

- EKA2L1(2).log
  SHA-256 `6ad6b13f5f8b15f77454aa11012a8f7738a590e0fd28d5bf15175f2017188a1a`
- EKA2L1_Persistent(2).log
  SHA-256 `d43817c9b10340c5d46328ac335348f88b927a8027d05cfc21595ff34c8beae2`
- EKA2L1_TakeThis(2).log
  SHA-256 `a09e9b668ae2f50e286d8c4389a7525d2dea4d7f00c2170c0a227b7f408c76e5`

## Preserve

Do not regress:
- B40 Loader::LoadPhysicalDevice / EUART1 completion;
- B41 MessageWin wipeout guard;
- B34 exit choreography;
- B36 implicit Wserv handle carry;
- B37 batch completion deferral;
- stock avkonfep.dll and firmware SYSSTART ownership;
- Leave/TRAP/KErrCancel semantics;
- EPOC94 0xAA unmapped, 0xAB message_construct, 0xAC message_kill,
  0xDF leave_start, 0xE0 leave_end;
- NOJAVA / MANIC3.
