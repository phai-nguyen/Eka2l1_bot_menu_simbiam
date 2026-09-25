# NATIVEBOOT2 B68 STARTERWAKE1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; WAKE/SCHEDULER PASS; NEXT BLOCKER IDENTIFIED AT ALARM OPCODE 0x0C

## Inputs

Device logs:
- EKA2L1(20260925-042346).log
- EKA2L1_Persistent(20260925-042403).log
- EKA2L1_TakeThis(20260925-042404).log

Persistent and TakeThis contain the same useful boot sequence.

## Global startup state

Starter still publishes only:

- 0 -> 100
- 100 -> 101 StartingCriticalApps

No later global-state SET occurs. AknCapServer, Startup and Home later read 101.

B64 self-test remains healthy:

- SAServer opcode 0x67 response completes KErrNone;
- no FatalStartupError 117 regression.

## Final RID6 WaitForStart result

The final RM-356 StartingCriticalApps process,
profilesettingsmonitor.exe, completes normally.

At 11:10:54.642:

- STARTER_RENDEZVOUS complete:
  target_process=profilesettingsmonitor
  reason=0
- STARTER_WAKE before:
  request_status=0x0070032C
  request_count=-1
  thread_state=5
- STARTER_NOTIFY_WAKE result=0:
  request_count -1 -> 0
  thread_state 5 -> 3
- STARTER_WAKE after confirms the same transition.
- STARTER_SCHED switches from
  profilesettingsmonitor/ProfileSettingsMonitor
  to SYSSTART/StarterServer.
- StarterServer immediately executes guest SVC 0x35.

Therefore the final process rendezvous is not lost, notify_info signaling works,
the request semaphore becomes runnable, the scheduler selects StarterServer,
and guest code resumes.

This closes the B65/B68 wakeup ambiguity.

## Recurring KErrCancel is not the blocker

The known SYSSTART TRequestStatus 0x00700364 receives KErrCancel after the
successful WaitForStart, as on earlier successful critical-app cycles.

Starter consumes that queued signal and continues executing many subsequent
SVCs. The cancel is therefore not itself the terminal blocker.

Do not patch KErrCancel/request accounting based on B68.

## New exact blocker boundary

Immediately after the final RID6 continuation, Starter reaches the Alarm HLE
service.

At 11:10:54.643 the log reports:

Unimplemented opcode for Alarm server 0xC

Starter then enters SVC 0x800000 and WaitForAnyRequest:

- before: request_count=0
- after: request_count=-1, thread_state=5

About 610 ms later, another request at 0x007008D4 completes KErrNone:

- request_count -1 -> 0
- thread_state 5 -> 3
- scheduler selects SYSSTART/StarterServer
- Starter resumes at SVC 0x800000

Starter immediately calls WaitForAnyRequest again:

- before request_count=0
- after request_count=-1, thread_state=5

From that point there is no further Starter progress until user exit.

Thus B68 rules out:
- unresolved final process rendezvous;
- lost notify completion;
- request-semaphore wakeup failure;
- scheduler ready-queue failure;
- inability to resume guest SYSSTART code.

The durable post-RID6 boundary is now the Alarm-server request chain, with
opcode 0x0C the first concrete unimplemented request immediately preceding the
blocking wait.

## Upstream correlation

Current EKA2L1 upstream identifies Alarm opcode 12 / 0x0C as
EASShdOpCodeGetAlarmIdList.

Upstream commit:

127823a47b76c7edd50ef8e0b52ddb9b71a18782
"alarm: Answer all three alarm id list requests"
2026-08-20

adds:
- opcode 9: GetAlarmIdListForCategory
- opcode 12: GetAlarmIdList
- shared serialization/completion for 9, 11 and 12

The upstream commit specifically fixes synchronous Alarm-list requests that
otherwise receive no reply and therefore never return.

This matches the B68 device boundary strongly enough to select a narrow
upstream backport as B69.

## Teardown

B61 remains healthy:
- GSTORE_WIPEOUT_GUARD fires 27 times;
- shutdown_done reached;
- normal_restart_done has_device=1 reached.

No teardown regression.

## Next

B69 ALARMIDLIST1:
backport upstream EKA2L1 commit 127823a... for Alarm ID-list opcodes, preserving
all Starter/SAServer/P&S/scheduler behavior.

Primary device acceptance:
- [NBOOT2][ALARM_ID_LIST] opcode=0xC ... completion=KErrNone
- no old "Unimplemented opcode for Alarm server 0xC"
- observe whether Starter advances beyond the former wait
- inspect KPSGlobalSystemState for first value beyond 101
- if still blocked, use the first new post-0xC request as B70 evidence
