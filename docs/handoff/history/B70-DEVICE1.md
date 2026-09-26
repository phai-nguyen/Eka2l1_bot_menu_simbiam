# B70 DEVICE1 — SIMPATHPROVENANCE1

Date: 2026-09-25
Device path: Nokia 5800 RM-356 v60.0.003, normal boot + SIM-present target
Status: DEVICE EVIDENCE COMPLETE; B71 TARGET IDENTIFIED

## Visible result

B70 materially advances the visible boot.

Instead of remaining at the earlier NOKIA/white startup plateau, the guest UI
reaches the native fatal startup screen:

`Phone start-up failed. Contact the retailer.`

The user did not exit too early for diagnosis. The decisive guest failure is at
14:07:49.075. Host exit does not begin until 14:09:05.786, roughly 76 seconds
later.

## SIM P&S

Startup initializes the RM-356 SIM P&S keys:

- 0x101F8766:0x31 KPSSimStatus = 100
- 0x101F8766:0x32 KPSSimOwned = 100
- 0x101F8766:0x33 KPSSimChanged = 100

Later readers include VPbkSimServer and profilesettingsmonitor, but
KPSSimStatus remains 100. No ESimUsable transition is observed.

This does not justify synthesizing ESimUsable. The fatal boundary occurs before
the normal SIM security phase.

## Global state

Observed:

- 0 -> 100
- 100 -> 101
- 101 -> 116 at 14:07:49.086

No state 102 is reached.

The 101 -> 116 write is performed by SYSSTART / StarterServer immediately after
the critical Telephone process failure below.

## SAServer / SIM route

Observed SAServer traffic includes earlier startup adaptation requests,
GetSIMLanguages diagnostics, and the B64 self-test path.

Before the fatal transition there is no evidence of the later normal SIM
security sequence:

- 0x65 SecurityStateChange
- 0x6C GetSimChanged
- 0x6D GetSimOwned

Therefore the immediate blocker is still before the normal SIM security phase.

## B70 absolute request-address result

The former B68/B69 address 0x007008D4 does not occur in this run. Guest
allocation/layout changed between builds.

Do not use absolute guest TRequestStatus addresses as a cross-build identity.

The decisive B70 request completion is instead:

- 14:07:49.077
- result = 14
- request_status = 0x00701684
- requester = StarterServer

Track process/result/semantics, not the old absolute address.

## Decisive causal chain

Phone application startup:

- phoneui.exe is summoned at 14:07:45.313
- process phoneui is spawned at 14:07:45.346
- UID3 = 0x100058B3
- thread becomes Telephone
- MediatorServer and VPbkSimServer are subsequently started successfully
- VPbkSimServer reads KPSSimStatus = 100

Immediately before the fatal event:

- Telephone loads phoneuistates.dll (UID3 0x101F7C9F)
- EFsrv resolves and opens z:\resource\apps\phoneui.r01

Then:

14:07:49.075
`Telephone[100058B3] ... exit_type=2 reason=14 category=CONE`

followed by:

14:07:49.077
`[NBOOT2][STARTER_NOTIFY_WAKE] result=14 ... requester_thread=StarterServer`

then:

14:07:49.086
`[NBOOT2][STARTER_GLOBAL_STATE] before=101 requested=116 after=116`

This is the strongest current causal boundary:

Telephone / phoneui
-> CONE 14 panic
-> Starter critical-process result 14
-> SYSSTART selects state 116
-> native fatal startup UI

## Meaning of CONE 14

Authoritative Symbian Classic UI source:

`lafagnosticuifoundation/cone/src/coepanic.h`

defines:

`ECoePanicNoResourceFileForId = 14`

and `CCoeEnv::ResourceFileForId()` / `DoResourceFileForIdL()` panic with this
value when no loaded resource file owns the requested resource ID.

Therefore B71 must investigate the missing PhoneUI resource ID/resource-file
ownership path. It must not suppress the panic, force state 102, or synthesize
SIM status.

## Secondary observations

Telephone also encounters:

- TfxServer absence / theme compatibility traffic;
- several leaves;
- FBS LEAVE5 paths;
- EPOC94 SVCMISS 0x2D (ThreadSetProcessPriority) before the fatal event.

These are retained as secondary evidence. They are not selected as B71 merely
because they occur earlier; CONE 14 has direct result-code continuity into the
Starter fatal transition.

## B71 decision

Build diagnostic-only PHONECONERESOURCE1:

1. Capture Telephone CONE14 registers.
2. Resolve stack/code candidates to modules and offsets.
3. Dump bounded code windows around relevant cone/phone/euser frames.
4. Capture exact z:\resource\apps\phoneui.r01 bytes through a separate
   read-only VFS handle.
5. Preserve the real panic/result/state behavior.

No additional B70 device run is required.
