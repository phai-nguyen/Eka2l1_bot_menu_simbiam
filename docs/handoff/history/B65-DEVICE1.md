# NATIVEBOOT2 B65 STARTERRENDEZVOUS1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; PROCESS-RENDEZVOUS BOUNDARY CLEARED; STARTER STILL STUCK AT 101
Visual result: unchanged from B64; no new video required.

## Inputs

- EKA2L1(20260924-230128).log
- EKA2L1_Persistent(20260924-230130).log
- EKA2L1_TakeThis(20260924-230130).log

## Global-state baseline preserved

B65 reproduces B64:

- 0 -> 100 StartingUiServices
- 100 -> 101 StartingCriticalApps
- no SET to 102 SelfTestOK
- no SET to 117 FatalStartupError

B64 EExecuteSelftests response remains successful:

- template=true
- header_ok=true
- payload_ok=true
- payload=0 / KErrNone
- completion=KErrNone

Startup still publishes private Wait=1 and no StartAnimations=2 writer appears.

## SYSSTART rendezvous trace

B65 emits 34 STARTER_RENDEZVOUS records.

Successful reason=0 rendezvous targets include:

- ecomserver / 0x10009D8F
- sysagt2svr / 0x10204FC5
- fbserv / 0x10003A16
- ewsrv / 0x10003B20
- tzserver / 0x1020383E
- randsvr / 0x100066DC
- apsexe / 0x10003A3F
- akncapserver / 0x10207218
- profilesettingsmonitor / 0x10207B7D

hwrmserver / 0x101F7A02 is armed at 05:56:03.905, remains pending for about
30 seconds, and is cancelled by Starter at 05:56:33.906. Starter then continues
booting and eventually publishes 100 then 101, so this timeout is an early boot
delay but is not the current post-101 blocker.

cntsrv / 0x10003A73 and dbrecovery / 0x10005A17 are armed/queued without a
matching B65 completion record, but Starter nevertheless proceeds through the
later startup phases. They therefore cannot by themselves explain the stable
post-101 stop.

## Critical observation after state 101

At 05:56:36.410:

- Starter publishes 100 -> 101.
- EExecuteSelftests 0x67 is answered successfully by B64.

At 05:56:36.447:

- Starter arms profilesettingsmonitor.

At 05:56:40.445:

- profilesettingsmonitor registers its server;
- its rendezvous completes reason=0.

After this completion there is no further SYSSTART process-rendezvous arm,
pending wait, cancellation, or failed completion in the run.

Yet KPSGlobalSystemState remains 101.

Therefore the current StartingCriticalApps blocker is not a normal
process::rendezvous wait owned by StarterServer.

## Public SSM reference comparison

The public Symbian criticalappscmdlist.rss for StartingCriticalApps contains a
deferred self-test custom command, cfserver start, SysAp start,
profilesettingsmonitor start, then a MultipleWait barrier.

This public reference is architecture guidance, not proof of the exact RM-356
merged resource.

The RM-356 B65 log shows:

- self-test request is issued and B64 answers success;
- sysap.exe is launched;
- profilesettingsmonitor is launched and its process rendezvous completes;
- no cfserver launch string is observed;
- no SYSSTART process-rendezvous arm is created for SysAp.

That makes a non-process asynchronous boundary (custom command / StartApp /
application-architecture IPC / multiple-wait completion) the stronger next
target.

## Teardown

B61 GSTORE_WIPEOUT_GUARD still fires on retained FBS references and shutdown
reaches shutdown_done normally.

## Decision

B65 process-rendezvous diagnostic: PASS.

Selected next build: B66 STARTERIPC1.

B66 traces every HLE IPC dispatched by SYSSTART UID3 0x100059C9 and every
matching ipc_context completion:

- server
- function/opcode
- session
- requester thread
- request-status presence
- completion result

A dispatch with no matching completion should identify the remaining
StartingCriticalApps asynchronous boundary.

B66 must not alter IPC results, state values, child-process behavior, graphics,
or teardown semantics.
