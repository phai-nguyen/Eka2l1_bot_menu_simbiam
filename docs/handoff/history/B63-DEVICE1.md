# NATIVEBOOT2 B63 SASELFTESTABI1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; ABI PROVEN; SELFTEST FAILURE DRIVES FATAL STARTUP STATE; HOME SURFACE LATER BECOMES PHYSICALLY VISIBLE

## Inputs

- EKA2L1(20260924-214449).log
- EKA2L1_Persistent(20260924-214518).log
- EKA2L1_TakeThis(20260924-214531).log

## Self-test ABI result

At 22:56:46.782 StarterServer sends exact SAServer opcode 0x67.

B63 proves:

- command: StartupAdaptation::EExecuteSelftests
- command id: 103 / 0x67
- caller process: SYSSTART
- caller thread: StarterServer
- session: 429
- arg types: [4,6,4,4]
- sizes: [12,0,12,0]
- max: [12,0,12,16]

Request / response-envelope previews:

slot 0:
  [0x00010004, 0x00000067, 0x00000009]

slot 2:
  [0x00010004, 0x01000067, 0x00000009]

slot 3:
  len=0 max=16

This matches the established RM-356 SA transport shape:
- slot 2 carries a 12-byte response envelope;
- slot 3 is the writable command response payload;
- public response for EExecuteSelftests is TResponsePckg = TInt.

## Failure consequence

B63 explicitly completes the self-test IPC with KErrNotSupported (-5).

Immediately after:
- V10 IPCERR records opcode 0x67 result=-5.
- Starter later issues EGlobalStateChange with value 117.
- KPSGlobalSystemState transitions 101 -> 117.

117 is ESwStateFatalStartupError.

Therefore the self-test boundary is causally significant. A failed self-test
request sends Starter into fatal-startup handling rather than the normal
101 -> 102 SelfTestOK path.

Compared with B62, B63 is not behavior-neutral on-device: exact registration
plus explicit completion makes the failure path observable and leads to state
117. Treat B63 as a diagnostic probe, not a valid normal-boot candidate.

## Startup / UI consequences

Startup still writes its private state Wait=1 and does not receive
StartAnimations=2.

Startup's WindowGroup is destroyed at 22:56:53.894 while Splash remains focus.

At 22:58:44.458, about 118 seconds later, S60SplashScreenGroup lowers priority
and focus moves to Home screen group 76.

The compositor then records the Home screen full-size canvas:

- abs=[0,0,360,640]
- visible=1
- visible_region_empty=0
- physically_seen=1
- draw_result=1

Thus B63 eventually makes the Home surface physically visible, but this occurs
after Starter has entered FatalStartupError=117. It is not the correct Nokia
startup sequence and must not be treated as a successful normal boot.

This behavior is useful evidence that the Home surface itself is renderable
once Splash/Startup stop covering it.

## Exit stability

B61 GSTORE_WIPEOUT_GUARD remains active and final shutdown reaches
shutdown_done / normal_restart_begin without an iOS crash.

## Decision

B64 SASELFTESTRESPONSE1 is selected.

Implement only the documented EExecuteSelftests success transport:
- echo slot 2 12-byte response template;
- write TInt(KErrNone) to slot 3;
- complete RMessage with KErrNone.

Do NOT write KPSGlobalSystemState directly.

Primary B64 acceptance:
- SA_SELFTEST_RESPONSE header_ok=1 payload_ok=1
- Starter advances 101 -> 102 (SelfTestOK)
- no 101 -> 117 FatalStartupError
- identify the next real dependency after SelfTestOK.
