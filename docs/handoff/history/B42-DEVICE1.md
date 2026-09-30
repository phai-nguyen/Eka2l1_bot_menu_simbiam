# NATIVEBOOT2 B42 DEVICE1 — SAHWRMABI1 device evidence

Updated: 2026-09-23
Branch: nativeboot2-current
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS
Functional baseline: B41 WSERVMESSAGEWINEXIT1 remains latest immutable functional milestone

## Summary

B42 successfully captures the real RM-356 HWRM -> SAServer request ABI without
changing guest completion semantics.

The raw SAServer request is confirmed to come from the real Nokia HWRM server:

```text
[NBOOT2][SA_HWRM_ABI]
raw_func=0x2000000A
logical_func=0xA
transport_bits=0x20000000
ipc_flag=0x924
process=!HWRMServer
thread=!HWRMServer
session=808
```

All four IPC arguments are descriptors:

```text
types=[4,4,4,4]
sizes=[12,4,12,4]
max=[12,4,12,4]
```

Captured contents:

```text
slot0 = [0x00010008, 0x2000000A, 0x00000000]
slot1 = [0x000000F3]
slot2 = [0x00010008, 0x2000000B, 0x00000000]
slot3 = [0x00700390]
```

The old generic warning for raw `0x2000000A` is absent and is replaced by the
B42 marker.

## Transport interpretation

The B42 evidence matches the already proven SAClient request/response-template
shape from B14/B19:

- slot 0 contains the request envelope;
- slot 2 contains a prebuilt response envelope;
- request code `0x2000000A` pairs with response-template code
  `0x2000000B`;
- slot 3 is exactly four bytes wide, matching the common TInt-style response
  payload used by the HWRM light plug-in interface.

However B42 does not yet prove the semantic meaning of slot1 `0xF3` or the
initial slot3 value `0x00700390`. No response is synthesized in this build.

## HWRM timeout is proven but not fatal

B42 marker time:

- `07:48:39.975`

SYSSTART later attempts to kill HWRM:

- `07:49:09.972`

Delta:

- approximately `29.997 s`

The kill attempt fails on capability grounds:

```text
Process kill failed, process SYSSTART[100059c9]0001 doesn't have enough
capability to kill process !HWRMServer[101f7a02]0002
```

Despite that timeout, startup continues into later services, including:

- `!AccServer`
- `!AknIconServer`
- `!AppListServer`
- `!ViewServer`
- `KeySoundServer`
- `!EikAppUiServer`
- `!Notifier`

Therefore the HWRM timeout is a real 30-second startup delay/recovery event, but
it is not the immediate final boot stopper in this run.

## B40 remains device-healthy

At `07:49:10.977`:

```text
[NBOOT2][LOADER_PDD] phase=enter name=EUART1
[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0
```

At `07:49:11.356`:

```text
[NBOOT2][SERVER_REGISTER] process=eiksrvs[10003a4a]0001 server=!EikAppUiServer ...
```

So the B40 Loader PDD and System GUI startup fix remain intact.

## B41 remains device-healthy

During user Exit Emulator at approximately `07:52:05`:

```text
[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout
[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout
```

Shutdown reaches:

```text
phase=os_join_done
phase=graphics_join_done
phase=shutdown_threads_done
phase=state_reset_done
phase=shutdown_done
phase=normal_restart_done has_device=1
```

No regression of the B41 host-exit fix is observed.

## Later fatal startup family

After the HWRM timeout, a stronger repeated causal family appears around
`TfxServer`.

First relevant eiksrvs instance:

```text
07:49:10.788 MISSING_SERVER process=eiksrvs ... server=TfxServer
07:49:10.971 ViewServerThread Leave(-1)
```

AknCapServer attempt 1:

```text
07:49:11.396 MISSING_SERVER process=akncapserver...0002 server=TfxServer
07:49:11.499 akncapserver Leave(-1)
07:49:11.536 akncapserver self-kill reason=-1
```

AknCapServer attempt 2:

```text
07:49:12.183 MISSING_SERVER process=akncapserver...0003 server=TfxServer
07:49:12.276 akncapserver Leave(-1)
07:49:12.308 akncapserver self-kill reason=-1
```

The TfxServer-missing -> Leave(-1) spacing is approximately:

- eiksrvs: 183 ms
- akncapserver attempt 1: 103 ms
- akncapserver attempt 2: 93 ms

The second akncapserver death is followed by SYSSTART error handling and then:

```text
07:49:12.813 Unimplemented IPC call: 0x71 for server: SAServer
```

Public StartupAdaptation source identifies `0x71` as
`EExecuteShutdown = 113`, so this is downstream shutdown handling rather than
the first failure.

Firmware/runtime evidence also shows transition-related components loaded or
registered nearby:

- `akntransitionutils.dll`
- `aknlistloadertfx.dll`
- `alfredserver_reg.rsc`

No TfxServer registration appears in the captured run.

## Next-candidate decision

Do not immediately turn B42 into a broad HWRM success shim.

The HWRM transport now has enough structure for a future narrow response build,
but the device run proves it is not the immediate final boot stopper.

The evidence-first next candidate should localize the repeated
`TfxServer -> Leave(-1)` path before changing behavior.

Preferred next candidate:

**B43 TFXSERVERDIAG1**

Suggested scope:

- identify whether `TfxServer` is expected to be provided by a process such as
  Alfred/transition-effects infrastructure in this RM-356 firmware;
- trace server-name -> executable/plugin resolution;
- capture the exact CreateSession return/error for eiksrvs and akncapserver;
- resolve the subsequent Leave(-1) callsite in both ViewServerThread and
  akncapserver;
- do not fabricate a TfxServer session yet;
- preserve B42 HWRM pending behavior, B40, B41, Wserv semantics, stock AvkonFep,
  SYSSTART ownership, NOJAVA and MANIC3.

## Log integrity

- `EKA2L1(3).log`
  SHA-256 `c4ebf57a86d7b7d38cda2813f7dad998c3abb3b687019ae420925f1a33ba025c`
- `EKA2L1_Persistent(3).log`
  SHA-256 `853b5d5a0dfe4aeeb7ed311f209c5c4ea5ec15ac326ad8212c8645a012bdc722`
- `EKA2L1_TakeThis(3).log`
  SHA-256 `676da5f052dc5d3440bdc6822398d55465308f5319b01df56e933271ded23982`
