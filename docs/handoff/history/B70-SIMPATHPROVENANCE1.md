# NATIVEBOOT2 B70 SIMPATHPROVENANCE1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Why B70

B69 DEVICE1 proves the Alarm ID-list backport works and moves SYSSTART past
the former Alarm 0x0C dead request.

The next exact boundary is guest request status 0x007008D4:
- requester: SYSSTART / StarterServer
- completes KErrNone while Starter waits
- wakes Starter correctly
- immediately after the wake Starter eventually requests
  StartupAdaptation::EGlobalStateChange(116 = ShuttingDown)
- P&S global state then changes 101 -> 117, also ShuttingDown

The intended normal SIM-present route is:

100 StartingUiServices
-> 101 StartingCriticalApps
-> 102 SelfTestOK
-> 103 SecurityCheck
-> SIM present/readable/security checks
-> KPSSimStatus=101 ESimUsable
-> 104 CriticalPhaseOK
-> GetSimChanged/GetSimOwned
-> 109 NormalRfOn

Current B69 exits at 101 before entering state 102 or the SIM security phase.

## B70 diagnostic markers

[NBOOT2][STARTER_IPC_ARM]

For every SYSSTART session SendReceive, logs:
- sync/async mode
- server
- function/opcode
- guest request-status address
- session id
- IPC argument types/raw arguments
- Starter thread

Primary target:
request_status=0x007008D4

If that address is armed through an IPC, this marker identifies the exact
server/function responsible.

[NBOOT2][STARTER_ASYNC_ARM]

Stable B28-compatible coverage:
- PROPERTY_SUBSCRIBE

Logs request status, property handle/category/key and Starter thread.

Timer-internal instrumentation was intentionally removed because the stable B28
bootstrap uses an older timer implementation than current upstream. Existing
B68 SVC + notify/wakeup traces remain available to correlate a non-IPC,
non-property completion without introducing version-fragile timer patches.

[NBOOT2][SIM_PS]

Observes authoritative SIM Startup P&S keys:
- 0x101F8766:0x31 KPSSimStatus
- 0x101F8766:0x32 KPSSimOwned
- 0x101F8766:0x33 KPSSimChanged

Coverage:
- direct category/key GET
- direct category/key SET
- handle-based SET

The older B28 property_get_int body is deliberately not patched solely to add
a redundant handle-based GET marker.

## Behavior contract

B70 is diagnostic-only.

It does NOT:
- force global state 102
- force KPSSimStatus=ESimUsable
- synthesize SIM ownership/change values
- alter IPC completion results
- alter property values
- alter request count/scheduler
- alter Starter rendezvous
- alter SAServer B64 self-test response
- alter B69 Alarm behavior
- alter graphics/teardown

B61/B64/B68/B69 remain preserved.
NOJAVA / MANIC3 preserved.

## Build iterations

Early B70 attempts failed safely before compile because diagnostic anchors were
too dependent on newer timer/property source shapes.

Final implementation intentionally keeps only stable B28-compatible probes.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36099148918
- run number: 219
- job ID: 107957715459
- build HEAD: 44e7cedeeae5e2d487b53a1032c51f634400b325
- B28 bootstrap cache: restored
- FASTBUILD manifest: VALID
- B70 apply: PASS
- B70 contract: PASS
- full regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile requests: 151
- cache hits: 150
- cache misses: 1
- cache hit rate: 99.34%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

6e04a5e37a77a6f255c3560faef846650daa20a85e8225c4540d4984e137ad3f

IPA artifact:
- ID: 10849100731
- ZIP digest:
  sha256:464dc6fafb7705aedb6e2061f5c3026a9e7d898e4e67fdf62553f3a62d198c86
- size: 19970221 bytes
- expires: 2026-10-09

Audit artifact:
- ID: 10848921007
- ZIP digest:
  sha256:ced0ec60bfd821e87c55ac1aab52daa2636e7efc6ce6dbbf3d8b55a9c34a07b4
- expires: 2026-10-09

## Device test

Install B70 over B69.

Boot the normal RM-356 Emulator path.

Allow the boot to reach/stabilize at the NOKIA screen and continue for roughly
the same former B69 shutdown window. Then exit normally.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Video is required only if visible behavior changes from B69.

## Acceptance / B71 decision

First search:

[NBOOT2][STARTER_IPC_ARM] ... request_status=0x007008D4

If present:
- exact server/function becomes the B71 target.

Otherwise search:

[NBOOT2][STARTER_ASYNC_ARM] ... request_status=0x007008D4

If property subscription:
- category/key becomes the B71 target.

Also inspect all:

[NBOOT2][SIM_PS]

Determine whether the firmware touches SIM status/owned/changed before shutdown.

Track whether any SAServer traffic reaches:
- 0x65 SecurityStateChange
- 0x68 GetSIMLanguages
- 0x6C GetSimChanged
- 0x6D GetSimOwned

If none occurs and global state remains 101 -> ShuttingDown, the failure remains
strictly before the SIM security phase.

Do not implement B71 by forcing ESimUsable or state 102. Use the provenance
captured by B70.


## DEVICE1 — 2026-09-25

B70 produced a decisive visible advance. The device no longer merely stalls at
the NOKIA plateau: after the logo it renders the native Startup failure UI:

`Phone start-up failed. Contact the retailer.`

The supplied ~122 s recording is sufficient. The failure screen remains stable
for more than a minute, so B70 does not need to be re-run.

### Exact causal chain

Global state:
- 14:07:12.434: 0 -> 100
- 14:07:45.305: 100 -> 101
- 14:07:49.086: 101 -> 116

SIM P&S initialization by SYSSTART:
- 0x101F8766:0x31 = 100
- 0x101F8766:0x32 = 100
- 0x101F8766:0x33 = 100

No evidence shows 0x31 reaching ESimUsable/101 before the failure.

The older diagnostic address 0x007008D4 does not occur in this B70 run.
The decisive request-status address is instead 0x00701684.

At 14:07:49.074 Telephone opens:
`Z:\\resource\\apps\\phoneui.r01`

At 14:07:49.075 Telephone UID3 0x100058B3 self-panics:
- category: CONE
- reason: 14
- PC: 0x80298584
- LR: 0x802A3A39

At 14:07:49.077 Starter receives:
- result=14
- request_status=0x00701684
- requester_thread=StarterServer

At 14:07:49.085 Starter arms SAServer function 0x64 and receives a valid
KErrNone adaptation response for input 0x75.

At 14:07:49.086 SYSSTART writes global state 101 -> 116.

Therefore the current first fatal chain is:

Telephone CONE14
-> Starter completion result 14
-> StartupAdaptation function 0x64 / shutdown selection
-> global state 116
-> native Phone start-up failed UI

### Meaning of CONE 14

The official Symbian crash-analysis table defines CONE 14 as:
the control environment cannot find the specified resource in any resource
file.

This moves the immediate blocker before the SIM security phase: Telephone
resource lookup is the first proven fatal condition. Do not force SIM status,
state 102, or ignore the critical-app failure.

### RM-356 PhoneUI resource evidence

Direct parsing of the matching SYM.RPKG confirms:
- Z:\\resource\\apps\\phoneui.r01 exists, size 28134
- Z:\\resource\\apps\\phoneui.r96 exists, size 32355
- both contain 368 resources
- resource signature offset/base: 0x4E738000
- expected user-resource index range: 0x001..0x170

phoneui.r01 SHA-256:
`05c419086de5710d361f7d8c910ef5284006b5ee879cb0acb448b8090a7ce9a1`

Thus B71 targets the exact missing resource ID/call chain rather than file
existence or SIM emulation.
