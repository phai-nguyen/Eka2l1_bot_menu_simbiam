# B32 DEVICE1 — EIKSRVFAULTDIAG1

Date: 2026-09-22
Status: DEVICE-OBSERVED; DIAGNOSTIC OBJECTIVE ACHIEVED
Device: iPhone 12 Pro Max, iOS 18.7
Firmware: Nokia 5800 RM-356

Build-tested B32 code commit:
`ca849738f8c1dd16949e687982904963c4bd8f6d`

B32 remained diagnostic-only. No B32 functional milestone branch is created.

## Preserved functional baseline

B30 rooted library resolution remains healthy:

`10:25:09.522 [NBOOT2][LDR_ROOT_RESOLVED] request=\sys\bin\EiksrvUi.dll candidate=Z:\sys\bin\EiksrvUi.dll success=1`

B31 scheduler protection remains healthy:

`10:25:39.383 [NBOOT2][SCHED_STALE_READY_DROP] thread=akncapserver owner_present=true mem_model_present=false`

The stale-ready marker appears exactly once.

No native host `thread_scheduler::switch_context()` crash is observed.

Safe B26 exit remains intact through the persistent log:

`10:27:11.906 [NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_done`
`10:27:11.906 [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_begin`
`10:27:12.064 [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done has_device=1`

## B32 marker counts

In both Persistent and TakeThis logs:
- `EIKFAULT_SVCMISS`: 11
- `EIKFAULT_LEAVE`: 16
- `EIKFAULT_LEAVE_FRAME`: 48
- `EIKFAULT_LEAVE_STACK`: 512
- `EIKFAULT_AV`: 16
- `KERN-EXEC`: 16
- `SCHED_STALE_READY_DROP`: 1
- `LDR_ROOT_RESOLVED`: 1

## Executive correlation result

B32 disproves SVCMISS 0xE3 as the immediate EikAppUiServerThread cause.

The observed 0xE3 owner is:

`10:25:39.305 [NBOOT2][EIKFAULT_SVCMISS] process=SYSSTART[100059c9]0001 thread=StarterServer svc=0xE3`

It is not issued by `eiksrvs` / `EikAppUiServerThread`.

One SVCMISS 0x2D is issued by eiksrvs:

`10:25:09.537 [NBOOT2][EIKFAULT_SVCMISS] process=eiksrvs[10003a4a]0001 thread=EikAppUiServerThread svc=0x2D`

but the first EikAppUiServerThread access violation does not occur until:

`10:25:41.640`

approximately 32.103 seconds later.

Additional 0x2D events belong to `sysap` or `akncapserver`, not the failing eiksrvs thread.

Therefore neither 0xE3 nor 0x2D has same-thread immediate temporal correlation with the repeated access-violation boundary.

Do not implement either executive on this evidence alone.

## Primary failure family — AknFep / trapped KErrCancel

All 16 B32 `EIKFAULT_LEAVE` records are identical in owner and leave state:

- process: `eiksrvs[10003a4a]0001`
- thread: `EikAppUiServerThread`
- leave: `-3` / KErrCancel
- trap: `0x007001FC`
- PC: `0x8029833C`
- LR: `0x802ABB29`

Resolved leave frames are identical for all 16 events:
- PC: `euser.dll +0x2EF4`
- LR: `euser.dll +0x166E0`
- trap address: unresolved guest data address

Most importantly, all 16 captured stacks have the same resolved code candidates:

1. `ws32.dll +0x370A`
2. `avkonfep.dll +0xF104`
3. `avkonfep.dll +0xF16E`
4. `avkonfep.dll +0x03D8`

This is a perfect 16/16 stack signature.

Immediately before the first Leave -3, the trace shows AknFep startup activity:
- `avkonfep.dll` loaded, UID3 0x100056DE;
- `AknFepUiAvkonPlugin.dll` loaded;
- `z:\resource\fep\aknfep.r01` opened;
- Central Repository 0x101F8780 / 0x101F877C / 0x10282DF0 opened;
- property category 0x101F876E key 0x4 attached.

First causal sequence:

`AknFep initialization`
-> `User::Leave(-3)`
-> B32 `EIKFAULT_LEAVE` / identical AknFep stack
-> `Leave trapped by trap handler`
-> same-timestamp `EIKFAULT_AV`
-> write address `0x10`
-> PC `0x802A01C4`
-> `euser.dll +0xAD7C`
-> `EikAppUiServerThread KERN-EXEC 3`.

The write-fault register state is stable:
- r0=0
- r1=0
- r2=1
- r3=1
- r6=0
- r7=0x007001FC

There are 11 occurrences of this write-fault family.

This is now the strongest causal boundary.

## Secondary failure family — CONE

Five later access violations are:
- process/thread: eiksrvs / EikAppUiServerThread
- operation: read
- address: 0x4
- PC: 0x806EA236
- LR: 0x806EC61B
- module: `cone.dll +0x13CE`

These occur around 10:27:08, about 85.2 seconds after the last captured AknFep Leave -3.

They do not have an immediately preceding B32 Leave -3 correlation.

Treat them as a secondary/later boundary, not the first causal target.

## External source correlation

Public S60 FEP documentation confirms that a FEP is loaded into CONE/CCoeEnv processes and interacts with Window Server/control-stack state.

The open Symbian inputmethods tree exposes the AknFep ECOM plugin path:
`CAknFepPlugin::NewFepL -> CAknFepManager::ConstructL`.

A historical open-source FEP proxy project records two relevant real-device observations:
- loading AKNFEP while a previous FEP instance is still loaded causes problems and was suspected to retain state in TLS;
- Contacts could terminate with KERN-EXEC 3 after AKNFEP reinstallation until processes were restarted/rebooted.

These are supporting pattern evidence only. They do not prove the emulator's exact root cause.

## Next direction

Preferred next build:

`B33 EIKCANCELORIGIN1`

Diagnostics only.

Goal:
identify which completion/notification path delivers `KErrCancel (-3)` to the failing eiksrvs/EikAppUiServerThread immediately before `avkonfep.dll` calls `User::Leave(-3)`.

Minimum B33 evidence:
- LLE/native `message_complete(..., -3)`: server/session, opcode, raw args, client process/thread, current server process/thread;
- HLE `ipc_context::complete(-3)`: same ownership/opcode context;
- generic `notify_info::complete(-3)`: requester process/thread and request-status address.

Do not alter completion values, signal counts, leave handling, FEP selection, or guest exception behavior.

Only after B33 identifies the origin of -3 should a functional compatibility patch be selected.

## Preserved invariants

Keep all B20-B31 functional behavior plus B32 diagnostics:
- firmware SYSSTART ownership;
- native fbserv;
- B25 shared FBS heap;
- B26 safe exit choreography;
- B28 LibraryType;
- B29 CenRep transactions;
- B30 rooted-no-drive library resolution;
- B31 stale-ready scheduler guard;
- NOJAVA;
- MANIC3.
