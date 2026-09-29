# NATIVEBOOT2 B64 SASELFTESTRESPONSE1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; SELFTEST RESPONSE PASS; FATAL PATH REMOVED; STARTER STILL STUCK AT 101
Install mode: CLEAN INSTALL / fresh logs

## Inputs

- ScreenRecording_09-25-2026 05-29-27_1.mp4
- EKA2L1_Persistent-prev(3).log
- EKA2L1_TakeThis(20260924-223735).log
- EKA2L1_Persistent(20260924-223725).log
- EKA2L1(20260924-223726).log

## B64 self-test response

At 05:30:01.761:

- Starter has just published global state 101 StartingCriticalApps.
- SYSSTART / StarterServer sends SAServer opcode 0x67 EExecuteSelftests.
- B64 response marker reports:
  - template=true
  - header=[0x00010004,0x01000067,0x00000009]
  - slot2_size=12
  - slot2_max=12
  - slot3_max=16
  - header_ok=true
  - header_err=0
  - payload_ok=true
  - payload=0
  - completion=KErrNone

Thus the RM-356 self-test response transport is accepted at the EKA2L1 IPC
layer exactly as designed.

## Starter global state result

Full observed KPSGlobalSystemState trace contains only:

- 0 -> 100 by SYSSTART / StarterServer
- 100 -> 101 by SYSSTART / StarterServer
- later reads of 101 by AknCapServer, Startup (twice), and Home screen

There is no SET to 102, 103, 104 or 117.

Therefore B64 removes B63's 101 -> 117 FatalStartupError path, but successful
EExecuteSelftests is not sufficient to finish StartingCriticalApps.

The active blocker has moved to work that Starter performs while state 101 is
active, most likely launch/wait synchronization for critical apps or another
critical dependency.

## Post-selftest launch activity

Immediately after the successful self-test response, multiple system/UI
processes are launched, including:

- ailaunch.exe
- startup.exe
- sysap.exe
- phoneui.exe
- clknitzmdls.exe
- profilesettingsmonitor.exe
- AlarmServer
- aknnfysrv.exe
- PhoneServer.exe

The legacy process trace does not expose which target process each
StarterServer rendezvous request belongs to.

Only one generic "Rendezvous to: StarterServer" occurs after the self-test
boundary, at 05:30:06.002, immediately after profilesettingsmonitor registers
its server. This is not enough to identify the pending target(s).

Other failures near this later boundary include:
- ETel cannot open CUSTOMAPI at 05:30:06.000
- Alarm server opcode 0xC unimplemented at 05:30:06.003

These are candidates only; B64 does not establish that either blocks Starter.

## Startup / compositor / video

Startup private state remains Wait=1. There is no handle-based writer and no
StartAnimations=2.

Video duration is ~354.0 s.

Observed:
- emulator launch / black
- NOKIA logo on white through roughly 150 s
- transition to blank-white Startup around 154 s
- blank white remains through the rest of the boot observation
- no Nokia hands/welcome animation
- no RTC/date-time UI
- no visible S60 Home/Menu before exit

At 05:31:59.458 Splash gives focus to Startup group 63.
Startup's full-size 360x640 canvas is physically_seen=1 / draw_result=1.
Home screen exists in the compositor tree but remains non-physical while
Startup owns focus.

Home receives focus only during final teardown when Startup is destroyed; that
is not boot progress.

Final host marker phase is phase 1/cyan. It remains a host-only debug overlay.

## Exit stability

B61 wipeout protection still fires, including retained FBS segments with
font_refs=1 bitmap_refs=4.

Shutdown reaches shutdown_done / normal_restart_begin with no iOS crash.

## Decision

B64 self-test response track: PASS.

B64 normal startup advancement: still blocked at global state 101.

Selected next diagnostic: B65 STARTERRENDEZVOUS1.

Instrument process rendezvous/logon requests owned by SYSSTART UID3 0x100059C9
to reveal:
- target process Starter arms
- queued/immediate wait state
- completion target and reason
- cancellation

Do not force state 102 and do not change child-process behavior.
