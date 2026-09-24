# NATIVEBOOT2 B65 STARTERRENDEZVOUS1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; RENDEZVOUS TARGETS RESOLVED; NO POST-101 PROCESS-WAIT BLOCKER FOUND
Visual result: unchanged from B64; no video required for this diagnostic run.

## Inputs

- EKA2L1(20260924-230128).log
- EKA2L1_Persistent(20260924-230130).log
- EKA2L1_TakeThis(20260924-230130).log

## Global-state result

B65 preserves the B64 path:

- 0 -> 100 StartingUiServices
- 100 -> 101 StartingCriticalApps
- later readers continue to see 101
- no 102 SelfTestOK
- no 117 FatalStartupError

B64 EExecuteSelftests success remains healthy:
template=true, header_ok=true, payload_ok=true, payload=0, completion=KErrNone.

Startup private state remains Wait=1.

## Starter rendezvous inventory

B65 records 34 [STARTER_RENDEZVOUS] events.

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

Important cases:

### HWRMServer

- armed/queued at 05:56:03.905
- cancelled by StarterServer at 05:56:33.906 with completion=-3
- this occurs before state 101 is published at 05:56:36.410

Starter continues beyond this timeout and enters StartingCriticalApps=101.
Therefore the HWRM rendezvous timeout is not the active post-101 blocker.

### profilesettingsmonitor

- armed/queued at 05:56:36.447, after state 101
- completes with reason 0 at 05:56:40.445

This is the only new SYSSTART process-rendezvous arm observed after the
101 transition. It completes successfully.

### cntsrv / dbrecovery

Both were armed/queued earlier and no B65 complete/cancel marker is observed for
them in this session. However Starter continues through many later startup
steps and eventually publishes state 101. They are therefore old outstanding
requests, not sufficient evidence of the current state-101 barrier.

## Decision

B65 does not identify an unresolved process rendezvous after state 101.

Do not patch profilesettingsmonitor, HWRMServer, cntsrv or dbrecovery based on
this run.

The next diagnostic must move to the real RM-356 Starter policy/configuration.
The installed firmware contains:

- Z:\private\100059C9\ScriptInit.txt
- Z:\private\100059C9\script0.txt
- Z:\private\100059C9\script1.txt

and runtime uses generated C:\private\100059C9\plg_script*.txt files.

Selected next build: B66 STARTERSCRIPTDUMP1.

B66 will dump these files through a separate read-only VFS handle when the
guest opens them, without moving the guest's file cursor or changing startup
semantics.
