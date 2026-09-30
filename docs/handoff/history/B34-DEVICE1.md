# B34 DEVICE1 — FOCUSMUTEXSPLIT1

Date: 2026-09-22
Status: DEVICE-VALIDATED
Immutable branch: nativeboot2-b34-focusmutexsplit1
Exact IPA-producing/device-tested commit: 24001e3306070fab2145bc1a4dd326a9fa83587d
Authoritative GREEN run: 35691395487
Job: 106628955424
IPA SHA-256: 486ed148c18689b9582988df1e30616ab4bb40c18070a7e554078161d20c4c5c

## Device inputs

The user supplied three B34 logs:
- EKA2L1(20260922-071141).log
- EKA2L1_Persistent(20260922-071148).log
- EKA2L1_TakeThis(20260922-071147).log

The user explicitly did NOT swipe the app to the iOS Home Screen before
evaluating Exit Emulator.

## B34 exit result

B34 fixes the B33 Exit Emulator deadlock on device.

The user-triggered exit at 12:54:31 follows:

12:54:31.866
[NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode

12:54:31.867
phase=exit_requested
phase=shutdown_begin

12:54:31.868
phase=shutdown_threads_begin
phase=flags_set
phase=request_exit
phase=core_wakeup
phase=os_join_begin

12:54:31.891
phase=os_join_done

12:54:31.892
phase=graphics_abort
phase=graphics_join_begin
phase=graphics_join_done
phase=shutdown_threads_done
phase=state_reset_begin
phase=state_reset_done
phase=shutdown_done
phase=normal_restart_begin

12:54:32.055
phase=normal_restart_done has_device=1

The critical B33 boundary changed from:
- B33: os_join_begin -> hang

to:
- B34: os_join_begin -> os_join_done in approximately 23 ms.

The complete B26 frontend restoration also returns.

This is direct device evidence that the dedicated focus_callback_mutex split
removes the same-thread screen_mutex self-deadlock during Wserv teardown.

## Preserved earlier milestones

The B34 logs preserve:
- [NBOOT2][LDR_ROOT_RESOLVED] — B30
- [NBOOT2][SCHED_STALE_READY_DROP] exactly once — B31
- B32 EIKFAULT diagnostics
- B33 EIKCANCEL diagnostics
- B26 shutdown/restart choreography

No host scheduler crash reappears.

## Guest AknFep failure remains independent

B34 intentionally changes only host/window-server focus callback locking. The
guest Eiksrv/AknFep failure remains.

In EKA2L1_TakeThis:
- exact [NBOOT2][EIKFAULT_LEAVE]: 16
- all 16 are process eiksrvs[10003a4a]0001 / EikAppUiServerThread
- all leave=-3
- all trap=0x007001FC
- all PC=0x8029833C
- all LR=0x802ABB29
- all share the same register signature.

Access violations:
- total [NBOOT2][EIKFAULT_AV]: 16
- 13 are write address=0x00000010 at PC=0x802A01C4 / LR=0x802A2DF5
- 3 later are read address=0x00000004 at PC=0x806EA236 / LR=0x806EC61B
- all 16 corresponding EikAppUiServerThread terminations are KERN-EXEC 3.

B33 completion-origin result remains unchanged:
- EIKCANCEL_HLE: 0
- EIKCANCEL_LLE: 2, both unrelated AknIconSrv/CdlServer opcode=3 cancellations
- EIKCANCEL_NOTIFY: 72 total
- eiksrvs EikAppUiServerThread notify cancellations follow the KERN-EXEC events
  and remain cleanup, not the pre-Leave(-3) source.

Three additional eiksrvs notify cancellations at 12:54:31 belong to normal
B34 shutdown (UikonWatchers / EikAppUiServerThread) and must not be mixed with
the earlier guest-fault chronology.

## Conclusion

B34 FOCUSMUTEXSPLIT1 is DEVICE-VALIDATED for its intended functional boundary.

Promote:
- immutable branch: nativeboot2-b34-focusmutexsplit1
- exact validated code: 24001e3306070fab2145bc1a4dd326a9fa83587d

The host Exit Emulator blocker is closed.

The next active blocker is again the independent guest UI path:
AknFep -> User::Leave(KErrCancel/-3) -> null write 0x10 -> KERN-EXEC 3,
with later secondary read-0x4 faults.

Do not undo B34 while investigating the guest failure.
