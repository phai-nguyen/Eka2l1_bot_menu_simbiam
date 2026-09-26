# NATIVEBOOT2 B65 STARTERRENDEZVOUS1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; POST-SELFTEST PROCESS RENDEZVOUS COMPLETES; STARTER STILL STUCK AT 101

## Inputs

- EKA2L1(20260924-230128).log
- EKA2L1_Persistent(20260924-230130).log
- EKA2L1_TakeThis(20260924-230130).log
- no video (user reports no visual change from B64)

## Global startup state

B65 preserves the B64 state behavior:

- 0 -> 100 by SYSSTART / StarterServer
- 100 -> 101 by SYSSTART / StarterServer
- no SET to 102
- no SET to 117
- later AknCapServer, Startup and Home screen all read 101

B64 self-test response remains successful:

[NBOOT2][SA_SELFTEST_RESPONSE]
template=true
header_ok=true
payload_ok=true
payload=0
completion=KErrNone

Startup private state remains Wait=1 and there is still no
[STARTUP_STATE_HANDLE] writer / StartAnimations=2.

## B65 rendezvous findings

B65 emits 34 [STARTER_RENDEZVOUS] events.

Early pre-101 startup targets that arm and complete successfully:

- ecomserver 0x10009D8F -> complete reason 0
- sysagt2svr 0x10204FC5 -> complete reason 0
- fbserv 0x10003A16 -> complete reason 0
- ewsrv 0x10003B20 -> complete reason 0
- tzserver 0x1020383E -> complete reason 0
- randsvr 0x100066DC -> complete reason 0
- apsexe 0x10003A3F -> complete reason 0
- akncapserver 0x10207218 -> complete reason 0

Early pending/problematic targets before state 101:

- cntsrv 0x10003A73 is armed/queued but no B65 complete/cancel is observed.
- dbrecovery 0x10005A17 is armed/queued, then fails to connect to CNTSRV,
  leaves -1 and kills its own thread; no B65 complete/cancel is observed.
- hwrmserver 0x101F7A02 is armed/queued, remains pending ~30 s, then
  StarterServer cancels it with completion -3. SYSSTART is also denied when
  attempting to kill !HWRMServer for capability reasons.

These occur before 100 -> 101 and therefore are not the final post-selftest
critical-app blocker, although cntsrv/dbrecovery remain architectural debt.

## Exact post-selftest / state-101 rendezvous result

At 05:56:36.410:

- Starter publishes 100 -> 101.
- EExecuteSelftests returns the successful B64 response.

Immediately after, Starter launches multiple components including:

- ailaunch.exe
- startup.exe
- sysap.exe
- phoneui.exe
- clknitzmdls.exe
- profilesettingsmonitor.exe

The only B65 SYSSTART process-rendezvous request armed after entering state 101
is:

profilesettingsmonitor 0x10207B7D

Timeline:

- 05:56:36.447 arm
- 05:56:36.447 queued
- 05:56:40.445 complete reason=0

Therefore profilesettingsmonitor is NOT the blocker.

After that successful completion, the log shows no further B65
STARTER_RENDEZVOUS arm/queue events and no 101 -> 102 transition.

This is the key B65 conclusion:

**The remaining StartingCriticalApps blocker is not an unresolved process
rendezvous captured by process::logon().**

StarterServer becomes effectively silent after the profilesettingsmonitor
completion except for request cancellation bookkeeping, while global state
remains 101.

## Other observations around the post-selftest phase

Potential dependencies/errors observed after state 101 include:

- sysap SVC miss 0x2D
- ETel unimplemented phone opcodes 24011 / 22022 / 22008
- AlarmServer LEAVE -1 activity
- Phone Server initially missing and later spawned
- !MediatorServer and VPbkSimServer are missing then launched
- Telephone eventually panics CONE/14
- CentralRepository IPC 0x21 unimplemented
- ETel CUSTOMAPI open fails
- Alarm server opcode 0xC unimplemented

These are candidates only. B65 does not prove any one of them is what prevents
Starter from transitioning to SelfTestOK=102.

## Likely next diagnostic boundary

The public generic SSM critical-app command list contains deferred
wait-for-signal commands plus a multiple-wait barrier. B65 shows the
post-selftest process rendezvous visible through process::logon() completes
successfully, yet Starter does not advance.

Therefore B66 should trace StarterServer's remaining async wait / command-list
completion path rather than patching another child process blindly.

Recommended B66 scope:

- trace StarterServer request-status waits/completions after state 101;
- identify which request remains pending after profilesettingsmonitor completes;
- correlate request status addresses with child-process / custom-command /
  multiple-wait ownership;
- preserve all B64/B65 behavior;
- do not force global state 102.

Useful observed Starter request-status events:
- request_status=0x00700364 is cancelled immediately after
  profilesettingsmonitor rendezvous completion at 05:56:40.445;
- additional Starter request statuses are only cancelled during final shutdown.

## Exit stability

B61 GSTORE_WIPEOUT_GUARD still fires 27 times, including retained-FBS
segments, and shutdown reaches shutdown_done normally.

## Decision

B65 diagnostic success:

- no visual change from B64;
- self-test remains fixed;
- fatal 117 remains absent;
- post-selftest profilesettingsmonitor rendezvous completes successfully;
- no unresolved post-selftest process rendezvous explains state 101.

Next: B66 async-wait / command-list completion trace.
