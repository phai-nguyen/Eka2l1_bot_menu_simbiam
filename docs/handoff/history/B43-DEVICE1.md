# NATIVEBOOT2 B43 DEVICE1 — TFXSERVERDIAG1 device evidence

Updated: 2026-09-23
Branch: nativeboot2-current
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS
Type: DIAGNOSTIC ONLY
Functional baseline: B41 WSERVMESSAGEWINEXIT1 remains latest immutable functional milestone

## Scope clarification

This work is interoperability/emulator startup debugging for Nokia 5800/Symbian
firmware inside EKA2L1. It observes guest client/server startup provenance only.
It does not attack networks, bypass access controls, deploy malware, or access
external systems.

## Summary

B43 proves a direct same-thread causal chain for the two failing
`akncapserver` startup attempts:

```text
CreateSession("TfxServer")
    -> KErrNotFound (-1)
    -> User::Leave(-1) on the same guest thread
    -> akncapserver self-kill reason=-1
```

The correlation repeats twice with the same guest call pattern and the same
Avkon/AknSkins leave-stack module/offset signature.

The earlier `eiksrvs` TfxServer miss is different: the missing session occurs
on `EikAppUiServerThread`, while the later Leave(-1) occurs on
`ViewServerThread`. B43 therefore does **not** prove a same-thread causal link
for the eiksrvs event.

B43's provider-resolution probes are negative:

- `[NBOOT2][TFX_RESOLVE]`: 0
- `[NBOOT2][TFX_SERVER_REGISTER]`: 0

No `TfxServer` registration occurs in the captured run.

## Marker counts

In the canonical TakeThis/Persistent device trace:

- `[NBOOT2][TFX_RESOLVE]`: 0
- `[NBOOT2][TFX_SESSION]`: 6
  - three request events
  - three missing events
- `[NBOOT2][TFX_SESSION_FRAME]`: 6
- `[NBOOT2][TFX_SESSION_STACK]`: 4
- `[NBOOT2][TFX_LEAVE]`: 2
- `[NBOOT2][TFX_SERVER_REGISTER]`: 0
- `[NBOOT2][SA_HWRM_ABI]`: 1
- `[NBOOT2][LOADER_PDD]`: 2
- `[NBOOT2][WSERV_MESSAGEWIN_EXIT]`: 2

## First TfxServer miss — eiksrvs

At `09:55:44.806`:

```text
[NBOOT2][TFX_SESSION] phase=request
process=eiksrvs[10003a4a]0001
uid=0x10003A4A
thread=EikAppUiServerThread
server=TfxServer
msg_slots=16
mode=0
pc=0x80298044
lr=0x802A5287
sp=0x00404698
```

Resolved frames:

- PC: `euser.dll + 0x00002BFC`
- LR: `euser.dll + 0x0000FE3E`
- stack index 11: `euser.dll + 0x0001C718`
- stack index 13: `bafl.dll + 0x000059AA`

The call returns the unchanged historical result:

```text
[NBOOT2][TFX_SESSION] phase=missing ... result=-1
behavior=UNCHANGED_KErrNotFound
```

At `09:55:44.990`, approximately 184 ms later, `eiksrvs` emits
`Leave(-1)`, but on `ViewServerThread`, not `EikAppUiServerThread`.

Therefore the B43 thread-local correlator correctly does not emit
`[TFX_LEAVE] correlated=1` for this event.

## AknCapServer attempt 1 — direct correlation proven

At `09:55:45.436-09:55:45.437`:

```text
[NBOOT2][TFX_SESSION] phase=request
process=akncapserver[10207218]0002
thread=akncapserver
server=TfxServer
pc=0x80298044
lr=0x802A5287
sp=0x00507338

[NBOOT2][TFX_SESSION] phase=missing
result=-1
behavior=UNCHANGED_KErrNotFound
```

At `09:55:45.545`, about 108 ms later, on the **same process and same guest
thread**:

```text
[NBOOT2][TFX_LEAVE] correlated=1
process=akncapserver[10207218]0002
thread=akncapserver
leave_code=-1
miss_pc=0x80298044
miss_lr=0x802A5287
now_pc=0x8029833C
now_lr=0x802ABB29
behavior=DIAGNOSTIC_ONLY
```

At `09:55:45.575`, the same process self-kills with reason `-1`.

## AknCapServer attempt 2 — deterministic repeat

At `09:55:46.202`:

```text
[NBOOT2][TFX_SESSION] phase=request
process=akncapserver[10207218]0003
thread=akncapserver
server=TfxServer
pc=0x80298044
lr=0x802A5287
sp=0x00507338

[NBOOT2][TFX_SESSION] phase=missing
result=-1
behavior=UNCHANGED_KErrNotFound
```

At `09:55:46.296`, about 94 ms later:

```text
[NBOOT2][TFX_LEAVE] correlated=1
process=akncapserver[10207218]0003
thread=akncapserver
leave_code=-1
miss_pc=0x80298044
miss_lr=0x802A5287
now_pc=0x8029833C
now_lr=0x802ABB29
```

At `09:55:46.327`, the process self-kills with reason `-1`.

The second failure is then followed by SYSSTART error/shutdown handling and:

```text
09:55:46.838 Unimplemented IPC call: 0x71 for server: SAServer
```

As established earlier from public StartupAdaptation source, `0x71` is the
downstream shutdown request, not the initiating failure.

## Deterministic Avkon/AknSkins Leave stack

Both akncapserver attempts have the same code-candidate module/offset pattern at
the Leave(-1) point:

- `avkon.dll + 0x000A73DC`
- `euser.dll + 0x000095B0`
- `AKNSKINS.DLL + 0x00000164`
- `avkon.dll + 0x000A742C`
- `avkon.dll + 0x000A742C`
- `AKNSKINS.DLL + 0x00000384`
- `avkon.dll + 0x000A73DC`
- `euser.dll + 0x0001C83C`
- `avkon.dll + 0x000A742C`
- `avkon.dll + 0x000A741C`

The surrounding non-code stack data differs slightly between attempts, but the
resolved code module/offset sequence is the same. This points the repeatable
failure into the Avkon/AknSkins transition-effects startup path rather than a
generic euser-only failure.

## Transition-effects runtime evidence

The device trace also shows:

- `akntransitionutils.dll` loaded before the TfxServer calls;
- `aknlistloadertfx.dll` loaded immediately before akncapserver's TfxServer
  session attempt;
- AppArc reads `alfredserver_reg.rsc`;
- no runtime `alfredserver.exe` process is observed;
- UID `0x10282845` is not observed in this run;
- no `TfxServer` server registration is observed.

Because `[TFX_RESOLVE]` is zero, B43 does not show a Tfx/Alfred-named process
or library being resolved through the instrumented Loader entry points.

## Public Symbian source cross-check

Public Symbian/Nokia source materially narrows the architecture:

### Avkon / AknCapServer

`oss.FCL.sf.mw.classicui/uifw/AvKon/src/transitionmanager.cpp` defines:

```cpp
_LIT(KTfxServerName,"TfxServer");
```

and polls for that server with `TFindServer`.

`AknCapServer.mmp` explicitly enables `TFX_USE_WCHANGE_EVENT` when the
TfxServer CRP supports the window-group event and links transition components
including `gfxtrans.lib`, `akntransitionutils.lib`, and optionally
`aknlistloadertfx.lib`.

### Alfred / UI Accelerator

In `oss.FCL.sf.mw.uiaccelerator`:

- `alfredserver.exe` has UID3 `0x10282845`;
- `alfredserver_reg.rss` registers it as a hidden background application;
- `RAlfClientBase::StartServerL()` launches Alfred through AppArc on ALF-client
  demand if its app server is not already present;
- Alfred's `CAlfAppUi::ConstructL()` creates the transition-effect object and
  invokes `CreateTfxServerPlugin()`;
- `tfxsrvplugin.dll` is an ECom plugin (DLL UID `0x10282DBA`);
- the TFX definitions use public name `TfxServer` and server UID
  `0x10281F7D`;
- the transition-server controller source describes the TFX component as loaded
  into Wserv through a CAnimDll Wserv plugin;
- Alfred's internal `RAlfTfxClient::Open()` connects to the ALF
  streamer/bridge server rather than directly creating a server named
  `TfxServer`.

Therefore it is too strong to equate `alfredserver.exe` itself with
`TfxServer`. Alfred is part of the provider infrastructure, while the public
`TfxServer` endpoint is supplied through the transition-effects/ALF/Wserv
plugin architecture.

## B40/B41/B42 preservation

B42 HWRM diagnostic remains unchanged at `09:55:13.920`.

B40 remains healthy:

```text
09:55:44.998 [NBOOT2][LOADER_PDD] phase=enter name=EUART1
09:55:44.998 [NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0
09:55:45.361 [NBOOT2][SERVER_REGISTER] ... server=!EikAppUiServer ...
```

B41 exit remains healthy:

- two `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout`;
- `phase=os_join_done`;
- `phase=shutdown_done`;
- persistent log reaches `phase=normal_restart_done has_device=1`.

No B40/B41 regression is observed.

## Next candidate

Do **not** fabricate a TfxServer and do **not** simply force-launch
`alfredserver.exe` yet.

Preferred next diagnostic:

**B44 ALFTFXSTARTDIAG1**

Scope:

1. Trace AppArc lookup/start of Alfred UID `0x10282845` and
   `alfredserver.exe`:
   - GetAppInfo result;
   - resolved executable path;
   - StartApp request/completion.
2. Trace ALF app-server and ALF streamer/bridge CreateSession/registration
   names around the transition-effects startup.
3. Trace ECom resolution/load for TFX plugin DLL UID `0x10282DBA` and relevant
   implementation/interface UIDs when observed.
4. Trace TFX status/property path around UID/key `0x10281F7D` if a narrow
   non-invasive hook is available.
5. Preserve the real `TfxServer -> KErrNotFound` behavior while gathering this
   provider-startup evidence.
6. Preserve B42 HWRM pending behavior, B40 Loader PDD, B41 exit guard, Wserv
   semantics, stock AvkonFep, firmware SYSSTART ownership, NOJAVA and MANIC3.

B44 should answer one question before any functional shim is considered:
**what exact startup/provider step that should create the public TfxServer
endpoint is missing in this RM-356/EKA2L1 run?**

## Log integrity

- `EKA2L1(4).log`
  SHA-256 `5dc54248522d1af8c113a6442a388547b364ca9ed76f712e600e74b62897c8d3`
- `EKA2L1_Persistent(4).log`
  SHA-256 `d8d39a8ad0ff3b94e30012beb7b24fca9d751213396e7cadd279cb20ea1ce474`
- `EKA2L1_TakeThis(4).log`
  SHA-256 `235ee896b98f4e5f5c1d0c4265a920d822829a8e2ae475cf9a6cdc6d7415cf5c`
