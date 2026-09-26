# NATIVEBOOT2 B44 DEVICE1 — ALFTFXSTARTDIAG1 device evidence

Updated: 2026-09-23
Branch: nativeboot2-current
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Previous device diagnostic: B43 TFXSERVERDIAG1

## Executive result

B44 identifies the first strong missing provider-startup boundary before the
public `TfxServer` endpoint.

The RM-356 run is using EKA2L1's HLE `!AknSkinServer`. That HLE successfully
initializes skin state and its shared chunk, but its implementation has no
native TFX/ECom/ALF startup path.

At the first transition-effects client attach, the expected TFX P&S property
`0x10207218 / 0x2` is not merely zero — it is **not defined at all**.

No tfxsrvplugin, ALF-streamer client session, Alfred process start, or
TfxServer registration is observed before akncapserver fails.

## Log integrity

- `EKA2L1(5).log`
  - size: 54,214 bytes
  - lines: 264
  - SHA-256: `f389ad365148cb69bc810db8daa6f363c560ea12a56ef44566a2b4a6820675af`
- `EKA2L1_Persistent(5).log`
  - size: 2,555,439 bytes
  - lines: 11,888
  - SHA-256: `6b777b8a06c7a16ceae10bb37356c80622e9c7620b59e60299154fd0a8d6adda`
- `EKA2L1_TakeThis(5).log`
  - size: 2,444,461 bytes
  - lines: 11,349
  - SHA-256: `cf5bae4037dcdd88b291741b4cd0c1ac424bbdf482e9b4676fd618b153f9477c`

## B44 marker counts

Persistent/TakeThis:

- `[TFX_PS]`: 3
- `[TFX_SESSION]`: 6
- `[TFX_LEAVE]`: 2
- `[SA_HWRM_ABI]`: 1
- `[LOADER_PDD]`: 2
- `[WSERV_MESSAGEWIN_EXIT]`: 2

Zero observed:
- `[ALF_PROC_CREATE]`
- `[TFX_ECOM_RSC]`
- `[TFX_ECOM_DLL]`
- `[TFX_MANIFEST]`
- `[ALF_SESSION]`
- `[ALF_SERVER_REGISTER]`
- `[TFX_SERVER_REGISTER]`
- `[TFX_RESOLVE]`

The zero counts above mean those instrumented runtime paths did not execute.
They are not, by themselves, proof that corresponding ROM files are absent.

## TFX P&S is initially undefined

At `11:38:05.396`:

```text
Attach to property with category: 0x10207218, key: 0x2
Property (0x10207218, 0x2) has not been defined before,
undefined behavior may rise
[NBOOT2][TFX_PS] op=attach ...
process=eiksrvs[10003a4a]0001
thread=EikAppUiServerThread
```

EKA2L1 `property_attach` behavior is material here:

1. `kern->get_prop(category,key)`
2. if no object exists, emit the warning;
3. create a placeholder `service::property`;
4. set its category/key;
5. create a property-reference handle.

It does **not** call `property::define()`.

Therefore this trace proves the TFX status property did not exist as a defined
P&S property before eiksrvs tried to attach.

Later:
- akncapserver #1 attaches the same placeholder at `11:38:06.009`;
- akncapserver #2 attaches it at `11:38:06.781`.

There is no matching definition/set marker for the TFX status property.

## Alfred registration exists

The firmware/AppArc path is not missing the registration file itself.

At `11:38:05.253`:

```text
Get entry of:
Z:\private\10003a3f\apps\alfredserver_reg.rsc

Opening file:
Z:\private\10003a3f\apps\alfredserver_reg.rsc

Handle opened
```

The same file is opened again at `11:38:06.748`.

The AppList scanner also reports:

```text
Found app: , uid: 0x10282845
```

at both initial and post-exit registry scans.

Thus the firmware's Alfred AppArc registration is visible to EKA2L1.

But no B44 `ALF_APPARC_GETINFO` marker occurs, so no runtime
`GetAppInfo(0x10282845)` request reaches the instrumented API during the TFX
failure window.

## HLE AknSkinServer is active

At `11:38:05.377`:

```text
Chunk created: AknsSrvSharedMemoryChunk
```

Upstream EKA2L1 source identifies that exact chunk as created by
`akn_skin_server::do_initialisation()` in
`src/emu/services/src/ui/skin/server.cpp`.

The HLE server is named:

```text
!AknSkinServer
```

and current EKA2L1 `services/src/init.cpp` creates
`akn_skin_server` unconditionally in the UI service set.

The HLE initializer performs skin settings, icon config, FBS hookup, chunk
creation, synchronization objects, chunk-maintainer setup, and active-skin
merge.

It has no code for:
- ECom TFX implementation creation;
- `tfxsrvplugin.dll`;
- TFX P&S status `0x10207218/0x2`;
- `RAlfTfxClient`;
- `alfstreamerserver` startup;
- Alfred AppArc startup;
- public `TfxServer` registration.

The device log shows no native `aknskinsrv` process launch.

## Provider-boundary conclusion

The strongest current chain is:

```text
S60 client requests !AknSkinServer
  -> EKA2L1 HLE AknSkinServer services skin data
  -> HLE initialisation creates AknsSrvSharedMemoryChunk
  X native TFX-provider startup side effects are absent
  -> TFX P&S 0x10207218/0x2 remains undefined
  -> no tfxsrvplugin.dll activity
  -> no ALF streamer client session
  -> no Alfred startup demand
  -> no TfxServer registration
  -> akncapserver CreateSession("TfxServer") = KErrNotFound
  -> same-thread Leave(-1)
```

This is substantially narrower than the B43 result.

It is still premature to claim that disabling HLE AknSkinServer outright is
safe: EKA2L1 marks this service family as HLE-required and the HLE currently
provides real skin/chunk behavior used by RM-356.

## Repeated B43 failure

eiksrvs:

- TfxServer miss: `11:38:05.397`
- ViewServerThread Leave(-1): `11:38:05.579`
- delta: ~182 ms

akncapserver #1:

- miss: `11:38:06.009`
- correlated same-thread Leave(-1): `11:38:06.122`
- delta: ~113 ms
- self-kill reason -1 follows.

akncapserver #2:

- miss: `11:38:06.781`
- correlated same-thread Leave(-1): `11:38:06.872`
- delta: ~91 ms
- self-kill reason -1 follows.

## Additional runtime evidence

- `akntransitionutils.dll` is loaded.
- `aknlistloadertfx.dll` is loaded immediately before the first
  akncapserver transition attempt.
- `aknskins.dll` appears in the deterministic Leave(-1) stack.
- no `tfxsrvplugin.dll` appears in the log.
- no `alfstreamerserver` client connection appears.
- no `TfxServer` registration appears.

ECom itself is running:
- `ecomserver.exe` spawns;
- `!ecomserver` registers;
- ROM ECom SPI files under `Z:\private\10009D8F\ecom-*-0.spi` open.

Therefore the absence of the TFX provider path is not explained simply by
EComServer failing to exist.

## B40/B41/B42 preservation

B42:
- `11:37:34.518 [SA_HWRM_ABI]`
- `11:38:04.514` SYSSTART HWRM kill failure
- ~29.996 s timeout preserved.

B40:
- `11:38:05.586 [LOADER_PDD] enter EUART1`
- same timestamp: completion result 0.
- `11:38:05.945 !EikAppUiServer` registers.

B41:
- `11:41:05.395` two MessageWin wipeout guards.
- `11:41:05.413 shutdown_done`.
- `11:41:05.532 normal_restart_done has_device=1`.

No KERN-EXEC or host access violation is observed in the B44 device-test
window.

## Next build candidate

Do not fake TfxServer and do not force-launch Alfred.

Preferred B45 should target the HLE/native skin-provider boundary:

**NATIVEBOOT2-B45-AKNSKINNTFX1** (working name)

Before committing to a functional shim, B45 should answer:
1. what native RM-356 AknSkinServer image/provider artifacts exist;
2. whether native client startup would normally invoke the missing TFX
   provider when HLE interception is absent;
3. whether a narrow HLE-side provider bridge can reproduce only the missing
   startup side effects without replacing the working skin/chunk
   implementation.

Preserve B41 functional baseline and all B42-B44 diagnostic invariants.
