# NATIVEBOOT2 B69 ALARMIDLIST1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; ALARM 0x0C FIX PASS; STARTER ADVANCES BEYOND B68 BLOCKER; NEXT PATH IS DIRECT SHUTDOWN FROM STATE 101

## Inputs

Device logs:
- EKA2L1(20260925-044959).log
- EKA2L1_Persistent(20260925-045010).log
- EKA2L1_TakeThis(20260925-045008).log

Video:
- ScreenRecording_09-25-2026 11-43-43_1.mp4
- duration approximately 327.8 seconds

Persistent and TakeThis contain the useful boot trace.

## Visual result

Video progression:
- initial black emulator surface
- at approximately 35 seconds: white Nokia splash with blue NOKIA wordmark
- the NOKIA splash remains static for the rest of the recording
- no hands animation
- no date/time query
- no visible S60 Home/Menu

This is visually different from the prior blank-white plateau, but the internal
state trace proves it is not yet a successful normal-state transition.

## B69 upstream Alarm backport: DEVICE PASS

The old B68 line:

Unimplemented opcode for Alarm server 0xC

is absent.

B69 marker proves both relevant list calls complete:

11:44:23.555
[NBOOT2][ALARM_ID_LIST]
opcode=0xB
alarm_count=0
transfer_bytes=4
completion=KErrNone

11:44:23.556
[NBOOT2][ALARM_ID_LIST]
opcode=0xC
alarm_count=0
transfer_bytes=4
completion=KErrNone

Therefore the upstream EKA2L1 127823a Alarm ID-list backport is valid on the
RM-356 device path and should remain in the chain.

## Starter advances beyond the B68 wait

After opcode 0x0C succeeds, Starter no longer remains permanently asleep at
the immediate post-Alarm WaitForAnyRequest boundary.

At 11:44:24.166 request status 0x007008D4 completes KErrNone:

- request_count -1 -> 0
- thread_state 5 -> 3
- scheduler selects SYSSTART/StarterServer
- Starter resumes guest execution

This proves B69 materially advances execution beyond the B68 blocker.

## New failure boundary

Immediately after the 0x007008D4 completion, Starter resumes and issues:

[NBOOT2][SA_RESPONSE]
func=0x64
input=0x00000074
payload=0
completion=KErrNone

0x74 decimal = 116.

There are TWO related but differently ordered state enums and they must not be
mixed:

StartupAdaptation::TGlobalState (used by EGlobalStateChange / SA opcode 0x64):
- 100 StartingUiServices
- 101 StartingCriticalApps
- 102 SelfTestOK
- 103 SecurityCheck
- 104 CriticalPhaseOK
- 105 EmergencyCallsOnly
- 106 Test
- 107 Charging
- 108 Alarm
- 109 NormalRfOn
- 110 NormalRfOff
- 111 NormalBTSap
- 112 AlarmToCharging
- 113 ChargingToAlarm
- 114 ChargingToNormal
- 115 AlarmToNormal
- 116 ShuttingDown
- 117 FatalStartupError

TPSGlobalSystemState (P&S key 0x101F8766:0x41):
- the same values through 115
- 116 FatalStartupError
- 117 ShuttingDown

Therefore the SA request at 11:44:24.167 is a request for
StartupAdaptation::ESWStateShuttingDown (116), NOT FatalStartupError.

In the same millisecond SYSSTART publishes the P&S form of the same semantic
state:

KPSGlobalSystemState:
before=101
requested=117
after=117

Thus the observed B69 path is:

101 StartingCriticalApps
  -> Alarm ID-list requests now succeed
  -> async request status 0x007008D4 completes KErrNone
  -> SYSSTART requests adaptation state 116 ShuttingDown
  -> SYSSTART publishes P&S state 117 ShuttingDown
  -> NOKIA splash remains on screen

Important correction:
B69 contains no proven FatalStartupError transition. The previous interpretation
mixed the two state enums.

## What B69 proves

B69 is a real diagnostic/functional advance:

- opcode 0x0C is no longer a dead synchronous Alarm request;
- Starter proceeds beyond the exact B68 durable wait;
- the next failure path becomes observable;
- the firmware itself now elects a direct shutdown path from state 101.

Do not revert B69.

However this is not a successful transition to 102. The system still never
publishes SelfTestOK=102.

## No obvious new unimplemented service opcode

Between successful Alarm 0x0C completion and the fatal adaptation request,
there is no new "Unimplemented opcode" or "Unknown opcode" line attributable
to Starter.

The critical unresolved event is request status:

0x007008D4

It completes KErrNone approximately 610 ms after the Alarm calls. The B68
generic notify probe proves completion/wakeup, but does not identify which
subsystem armed that request or what returned payload/status semantics caused
Starter to choose ShuttingDown.

This is the next exact evidence boundary.

## B64/B61 health

B64 self-test remains healthy:
- EExecuteSelftests 0x67 response KErrNone
- no regression to the old unsupported-selftest failure

B61 teardown remains healthy:
- GSTORE_WIPEOUT_GUARD fires during teardown
- shutdown_done reached
- normal_restart_done has_device=1 reached

## Recommended B70

B70 should be diagnostic-only.

Trace the provenance and ABI of the asynchronous SYSSTART request status
0x007008D4:

- where/which server or timer creates/arms it;
- IPC function/opcode;
- descriptor argument types/sizes/max lengths;
- completion result and any output payload written before completion;
- the exact guest branch after wakeup that selects
  StartupAdaptation::ESWStateShuttingDown=116 / P&S ShuttingDown=117.

Also trace EGlobalStateChange 0x64 input with a dedicated named marker around
adaptation state 116 so B70 can correlate the causative request to the direct
shutdown transition.

Do not force 102 and do not suppress the shutdown transition until the
0x007008D4 source and payload are identified.
