# NATIVEBOOT2 B45 DEVICE1 — AKNSKINNTFX1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: DEVICE-OBSERVED; ROUTE NOT ACTIVATED
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Previous device diagnostic: B44 DEVICE1

## Result

B45 did not reach the native AknSkinServer experiment.

The B45 route guard evaluated false in native RM-356 mode because:
1. runtime `get_symbian_version_use()` logs integer `10`, while B45 required
   exact `epocver::epoc94`;
2. the extracted Z-profile is mounted one initialization step after HLE service
   creation, so both B45 `io_system::exist()` checks returned zero too early.

The HLE skin server therefore remained registered and all clients continued to
bind to `server_hle=1`.

## Log integrity

- `EKA2L1(6).log`
  - size 54,500
  - lines 265
  - SHA-256 `bf0c6b1c37fd932454f87ba527448018094547c38d7ed92b9fe5cda3fca1bbd4`
- `EKA2L1_Persistent(6).log`
  - size 2,559,778
  - lines 11,903
  - SHA-256 `178854edd9bd874fd3aa19d92e7a417af3d0b1f784afe469e2cb3e0cc108283b`
- `EKA2L1_TakeThis(6).log`
  - size 2,448,230
  - lines 11,362
  - SHA-256 `d3b45ea360bc86afa853c3fb3195123b584c83e6c20f4dac70072aa91230ddb7`

## B45 marker counts

Persistent:
- AKNSKIN_ROUTE: 3
- AKNSKIN_SESSION: 12
- AKNSKIN_NATIVE_PROC: 0
- AKNSKIN_NATIVE_REGISTER: 0
- TFX_PS: 3
- TFX_SESSION: 6
- TFX_LEAVE: 2
- SA_HWRM_ABI: 1
- LOADER_PDD: 2
- WSERV_MESSAGEWIN_EXIT: 2

No B44 TFX ECom/ALF provider markers fire.

## Exact native-mode route result

```text
15:05:08.368
[NBOOT2][AKNSKIN_ROUTE]
phase=hle_keep
epoc=10
native_phone_boot=1
exe_sysbin=0
exe_legacy=0
behavior=UNCHANGED_HLE
```

The active device is then announced as:

```text
5800 XpressMusic (RM-356)
```

and the Z-profile mount is announced at `15:05:08.369`, after the route
decision.

## Firmware artifact is known to exist

Earlier firmware extraction logs in the project record:

```text
Extracting: Z:\sys\bin\aknskinsrv.exe
Extracting: Z:\sys\bin\aknskinsrv.dll
```

Therefore the B45 zero-existence result is an initialization-order artifact,
not evidence that RM-356 lacks AknSkinSrv.

## HLE binding proof

At `15:05:40.170` eiksrvs:

```text
AKNSKIN_SESSION request
AKNSKIN_SESSION lookup found=1 server_hle=1
AKNSKIN_SESSION found server_hle=1
AknsSrvSharedMemoryChunk created
```

Both akncapserver attempts and AknIconSrv also report `server_hle=1`.

No session sees `phase=missing`, so the guest client never calls its native
StartServer path.

## TFX chain unchanged

At the first TFX client:

```text
Property (0x10207218, 0x2) has not been defined before
TFX_PS attach
CreateSession("TfxServer")
KErrNotFound
```

akncapserver attempt 1:
- TfxServer miss 15:05:40.800
- correlated Leave(-1) 15:05:40.906
- delta ~106 ms.

attempt 2:
- TfxServer miss 15:05:41.565
- correlated Leave(-1) 15:05:41.664
- delta ~99 ms.

## Old milestone health

B42 timeout:
- SA_HWRM_ABI 15:05:09.310
- SYSSTART HWRM kill failure 15:05:39.306
- delta ~29.996 s.

B40:
- EUART1 PDD completes result 0 at 15:05:40.380.
- !EikAppUiServer registers at 15:05:40.755.

B41:
- MessageWin guard twice at 15:08:04.206.
- shutdown_done at 15:08:04.213.
- normal_restart_done has_device=1 at 15:08:04.332.

No KERN-EXEC or host access-violation family is observed.

## Next build candidate

`NATIVEBOOT2-B46-AKNSKINROUTE2`

B46 must only repair route-selection timing/discrimination.

Do not:
- fake TfxServer;
- synthesize TFX P&S;
- force Alfred;
- synthesize ECom success;
- alter B42 HWRM behavior.

The first B46 device acceptance condition is not "boot farther". It is:

```text
native RM-356
-> HLE !AknSkinServer absent
-> first stock CreateSession returns KErrNotFound
-> guest requests AknSkinSrv.exe
-> native !AknSkinServer either registers or produces a new precise blocker
```
