# NATIVEBOOT2 B65 STARTERRENDEZVOUS1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; STARTER DIRECT RENDEZVOUS MAP RESOLVED; STATE 101 STILL STALLED

## Inputs

- EKA2L1(20260924-230128).log
- EKA2L1_Persistent(20260924-230130).log
- EKA2L1_TakeThis(20260924-230130).log

No video was supplied because visual behavior did not change from B64.

## Direct SYSSTART rendezvous map

B65 identifies every process rendezvous request armed directly by
SYSSTART / StarterServer.

Completed with reason 0:

- ecomserver
- sysagt2svr
- fbserv
- ewsrv
- tzserver
- randsvr
- apsexe
- akncapserver
- profilesettingsmonitor

Timed out/cancelled:

- hwrmserver
  - armed at 05:56:03.905
  - cancelled at 05:56:33.906
  - exact ~30 s timeout

Still armed without a matching B65 completion/cancel in the trace:

- cntsrv
- dbrecovery

Those two occur before the transition to StartingUiServices=100 and Starter
continues beyond them, so they are not sufficient by themselves to explain the
later state-101 stall.

## State 101 boundary

Global startup state still follows:

- 0 -> 100 at 05:56:03.684
- 100 -> 101 at 05:56:36.410
- no SET after 101

B64 EExecuteSelftests response succeeds at 05:56:36.410.

After state 101, direct SYSSTART rendezvous tracing shows:

- profilesettingsmonitor armed at 05:56:36.447
- profilesettingsmonitor completes reason=0 at 05:56:40.445

No other direct SYSSTART process rendezvous is armed after state 101.

Thus the direct process wait for profilesettingsmonitor is healthy and is not
the remaining blocker.

## SysAp observation

sysap.exe is spawned at 05:56:36.413, immediately after state 101 and the
self-test response.

However B65 records no direct SYSSTART rendezvous arm for target sysap.

Public/reference critical-app command-list architecture uses a deferred
StartApplication for sysap followed by a MultipleWait barrier. Therefore the
remaining wait may be hidden behind an application-start helper / StartSafe
layer rather than a direct SYSSTART -> RProcess::Rendezvous relationship.

B65 cannot identify that indirect waiter because it filters on requester UID3
0x100059C9.

## Other useful evidence

- cfserver.exe is not observed in this RM-356 run.
- hwrmserver's 30 s timeout occurs before state 101 and Starter continues, so it
  is not the active post-selftest blocker.
- B64 self-test success remains active.
- Startup remains Wait=1.
- no StartAnimations=2.
- B61 teardown guard remains healthy.

## Decision

Selected next diagnostic: B66 CRITICALAPPWAIT1.

Trace target-side process wait/signal lifecycle for the critical-app path
regardless of requester identity:

- sysap
- ailaunch / Home screen app-launch path
- profilesettingsmonitor
- cfserver

Required evidence:

- who arms rendezvous/logon on each target;
- whether the target itself calls Rendezvous and with what reason;
- whether a target signals with zero queued waiters;
- pending wait counts at process finish.

Do not change process/rendezvous semantics and do not force state 102.
