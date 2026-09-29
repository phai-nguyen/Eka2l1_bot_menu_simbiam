# B47 AKNSKINTFXSTATE1 — DEVICE1

Date: 2026-09-23  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — stock V60 suppresses TFX at Themes CenRep gate

## Device evidence

Files supplied by the user:

- `EKA2L1(8).log`
  - SHA-256 `9b459d6b66d269b454ecaf02f2552b6117c402fc24ced4267254bacde5c7e2cd`
- `EKA2L1_Persistent(8).log`
  - SHA-256 `9bb8cb9e5b8a691f87edfe6514190e1b14371da88d98597806497577fddfa3cc`
- `EKA2L1_TakeThis(8).log`
  - SHA-256 `7f375b01f7ec5d944cf6961e94f93de82d78ed0213b69c8644ec629ed610c430`

Authoritative current-session analysis is based primarily on
`EKA2L1_TakeThis(8).log`, beginning at 21:34:53.091.

Firmware profile reported by the runtime:

`rm-356__v-60.0.003__5f9fd6d77ac214ec`

Device:

`5800 XpressMusic (RM-356)`

## B46 route remains healthy

At 21:34:53.113:

```
[NBOOT2][AKNSKIN_ROUTE2]
decision=skip_hle
firmware_code=RM-356
model=5800 XpressMusic
native_phone_boot=1
behavior=GUEST_NATIVE_ROUTE
```

At 21:35:24.914, eiksrvs receives the intended real missing native server:

```
AKNSKIN_SESSION phase=lookup found=0 server_hle=-1
AKNSKIN_SESSION phase=missing result=-1
```

At 21:35:24.914-21:35:24.915 the guest launches the stock server:

```
AKNSKIN_NATIVE_PROC phase=request
path=Z:\System\Programs\AknSkinSrv.exe

AKNSKIN_NATIVE_PROC phase=result
success=1
spawned=AknSkinSrv[10207114]0001
uid3=0x10207114
```

At 21:35:24.916:

```
AKNSKIN_NATIVE_REGISTER
server=!AknSkinServer
process_hle=0
```

At 21:35:25.338 eiksrvs retries and binds the native server with
`server_hle=0`. Later akncapserver, SysAp, Telephone, Startup, Home screen,
aknnfysrv and AknIconSrv also bind to the same native server.

## B47 WindowServer observation

At 21:35:25.322:

```
AKNSKIN_TFX_WSERV phase=request
process=AknSkinSrv[10207114]0001
server=!Windowserver

AKNSKIN_TFX_WSERV phase=lookup
found=1
server_hle=1
```

Therefore native AknSkinSrv can reach the current HLE WindowServer. This is not
the missing stage.

## B47 decisive Themes CenRep result

At the same timestamp, native AknSkinSrv performs the exact read targeted by
B47:

```
AKNSKIN_TFX_STATE phase=request
repo=0x102818E8
key=0x00000009
function=5
```

Result:

```
AKNSKIN_TFX_STATE phase=result
repo=0x102818E8
key=0x00000009
result=0
value_valid=1
value=0x7FFFFFFF
enabled=0
suppressed=1
behavior=OBSERVE_ONLY
```

This exactly matches the independently extracted stock RM-356 V60 firmware
value in `private\10202BE9\102818E8.txt`:

`0x9 int 0x7fffffff`

Therefore EKA2L1 CenRep is returning the stock firmware value correctly to the
native AknSkinSrv.

## ECom interpretation

B47 logged 22 AknSkinSrv IPC sends to `!ecomserver` during startup.

However every marker has:

```
literal_controller=0
literal_server=0
```

No observed AknSkinSrv ECom IPC contains the target TFX interface UIDs:

- `0x10282DBD` controller interface
- `0x10282DBC` server interface

The paired V60 firmware itself is already proven to contain both ECom
registrations and the TFX binaries. Therefore their absence from the runtime
TFX creation path is not a firmware-content omission.

The pre-CenRep ECom traffic is generic AknSkinSrv/ECom activity and must not be
misclassified as a TFX provider creation request.

## TFX runtime state is consistent with stock suppression

No runtime markers appear for:

- `TFX_ECOM_RSC`
- `TFX_ECOM_DLL`
- `ALF_SESSION`
- `ALF_SERVER_REGISTER`
- `TFX_SERVER_REGISTER`

The TFX status P&S `0x10207218 / 0x2` remains undefined/missing.

Clients later request `TfxServer` and receive the unchanged real
`KErrNotFound (-1)`:

- eiksrvs at 21:35:25.360
- akncapserver at 21:35:26.075
- Telephone at 21:35:27.349
- Home screen at 21:35:27.434
- Startup at 21:37:24.295

This now has a firmware-consistent explanation: the stock Themes repository
suppresses transition-provider startup.

Do not fake `TfxServer`, do not force key 0x9, and do not synthesize
`0x10282DBD/0x10282DBC`.

## Other preserved milestones

B42 remains visible:

```
21:34:54.052 SA_HWRM_ABI raw_func=0x2000000A
```

The known ~30 second HWRM/SYSSTART delay remains; the native AknSkin boundary
is reached ~31.8 s after the initial route marker.

B40 remains healthy:

```
21:35:25.654 LOADER_PDD phase=enter name=EUART1
21:35:25.654 LOADER_PDD phase=complete name=EUART1 result=0
21:35:26.036 SERVER_REGISTER server=!EikAppUiServer
```

No `KERN-EXEC 3`, `EIKFAULT_AV`, host access violation, or
`EXC_BAD_ACCESS` family appears in the current TakeThis log.

## Exit Emulator remains healthy

At 21:38:15.687:

`BRIDGE_EXIT_PHASE phase=os_join_begin`

At 21:38:15.733:

`BRIDGE_EXIT_PHASE phase=os_join_done`

Join time is about 46 ms.

Shutdown then reaches:

```
graphics_join_done
shutdown_threads_done
state_reset_done
shutdown_done
normal_restart_begin
```

`EKA2L1(8).log` records:

```
21:38:15.873 BRIDGE_EXIT_PHASE phase=normal_restart_done has_device=1
```

B41 remains healthy.

## Post-B47 observation: xnthemeserver

The log progresses beyond B47 into native Home screen theme infrastructure.

At 21:35:29.072 Home screen requests missing `xnthemeserver`, which the guest
then launches. At 21:35:29.080:

```
SERVER_REGISTER
process=xnthemeserver[10207254]0001
server=xnthemeserver
```

The process remains alive until emulator teardown.

There are repeated trapped `Leave(-5)` events in xnthemeserver after
FileServer opcode `0x27` observations while accessing theme cache files such
as:

- `C:\Private\10207254\themes\sources\hdrcache.dat`
- `C:\Private\10207254\themes\sources\cleanupfiles.dat`

This is noteworthy for the next investigation, but it is not yet proven to be
the visual/boot blocker: the leaves are trapped, the xnthemeserver registers,
and it remains live. Do not patch FileServer behavior solely from this
correlation.

## B47 conclusion

B47 is a diagnostic success.

The decisive runtime chain is:

```
native AknSkinSrv
 -> !Windowserver reachable
 -> CenRep 0x102818E8 / key 0x9
 -> result=0, value=0x7FFFFFFF
 -> enabled=0, suppressed=1
 -> no target TFX ECom UID request
 -> no ALF/TfxServer startup
```

This exactly matches stock RM-356 V60 firmware authority.

Therefore the missing TFX provider is not a bug to fix. B47 closes the
AknSkin/TFX hypothesis without changing runtime semantics.

No B48 functional behavior should enable/fake TFX. The next milestone should
move to the first device-proven blocker after this stock-suppressed path.
