# NATIVEBOOT2 B62 STARTERGLOBALSTATE1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Install mode: INSTALL OVER B61

## Selection

B60/B61 close the Startup private-state writer ambiguity:

- 0x100058F4:1 reaches Wait=1;
- no category/key write publishes StartAnimations=2;
- no handle-based write targets that property.

Source review of Nokia/Symbian Startup shows another gating property:

- category 0x101F8766 (KPSUidStartup)
- key 0x00000041 (KPSGlobalSystemState)

Startup subscribes this property and does not mark Starter's critical phase as
ended until the value reaches an accepted post-critical state.

Relevant enum values from startupdomainpskeys.h:

- 100 StartingUiServices
- 101 StartingCriticalApps
- 102 SelfTestOK
- 103 SecurityCheck
- 104 CriticalPhaseOK
- 105 EmergencyCallsOnly
- 109 NormalRfOn
- 110 NormalRfOff
- 111 NormalBTSap

B61 logs already prove Startup attaches 0x101F8766:0x41, but previous builds do
not record its actual read/write values.

## B62 marker

[NBOOT2][STARTER_GLOBAL_STATE]

Coverage:

1. category/key Get
   - current value
   - reader process / UID3 / thread

2. category/key Set
   - before / requested / after / result
   - writer process / UID3 / thread

3. handle-based integer Set
   - before / requested / after / result
   - writer process / UID3 / thread / handle

No property is mutated by B62 beyond the guest's own request.

B58 private Startup marker, B60 handle writer marker and B61 wipeout guard all
remain active.

## Why this boundary matters

If SYSSTART/StarterServer never advances global state to >=104 / a terminal
accepted state, Startup's own source says its critical block remains active.
That would explain why the real Startup waiting frame stays white.

If global state reaches 104/109/110/111 but StartAnimations=2 is still absent,
the next boundary is Starter's UI-service/startup-animation handoff rather than
the critical-state machine itself.

## Canonical GREEN

- run ID: 36016936055
- run number: 181
- job: 107691773271
- HEAD: bc8da2307427095d20bfd5d21c7b5b67fe958b8c
- B62 apply PASS
- B62 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

d4800eec71e1d353ecfcb28fec2a73823f8bd06af706cada10cd3ddd3e36fb11

IPA artifact:

- ID: 10814674270
- ZIP digest: sha256:15979a83fc623b0e684dba26d913c99f51ccb06e6208b44e2ce01c85b9fd3263
- expires: 2026-10-08

Audit artifact:

- ID: 10814927913
- ZIP digest: sha256:7ae9bc5fc1102b9681848e2b5d32a4082ad4d70321cedb4fe3de68aea0e80dbe
- expires: 2026-10-08

## Device test

Install B62 over the confirmed-clean B61 installation.

Use the same normal SIM-present RM-356 V60 path.

Let the boot run through NOKIA -> white and leave it running long enough to pass
the natural handoff. Then exit normally.

Send the three logs and video if the visual behavior changes.

Primary question:

What exact 0x101F8766:0x41 sequence is observed, and which process writes the
last value?

Decision:

- stops below 104:
  trace the exact Starter state transition / dependency immediately after the
  last published global state.

- reaches 104/109/110/111 but no private state 2:
  trace the Starter UI-service handoff that should publish StartAnimations=2.

- reaches accepted global state and private state 2:
  trace Startup subscriber completion -> welcome animation controller.
