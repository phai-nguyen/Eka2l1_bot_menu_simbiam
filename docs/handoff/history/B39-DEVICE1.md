# B39 EIKPOSTLEAVEAV1 — DEVICE1

Updated: 2026-09-22
Branch: nativeboot2-current
Build: B39 EIKPOSTLEAVEAV1
B39 GREEN HEAD: `7f845581ba32dd59fc5229ee24fa5979ef7cc81e`
B39 GREEN run/job: `35748481719 / 106816104243`
Status: DEVICE-OBSERVED; ROOT CAUSE IDENTIFIED; NO B40 BEHAVIORAL PATCH APPLIED IN THIS SNAPSHOT

## Device evidence supplied

Analyzed:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

The B39 diagnostic markers fired successfully:
- 16 x `[NBOOT2][EIKFEP_STATE]`
- 16 repeated EikAppUiServerThread Leave(-3) cycles
- post-Leave AV symbol/code/stack evidence captured
- B36/B37/B38 diagnostics remained active
- B34/B26 Exit Emulator path remained healthy

## B39 FEP state result

All 16 `EIKFEP_STATE` records are stable:

```
caller_r4   = 0x00703A88
[r4+0x10]   = 0x00700078
[[r4+0x10]+0x24] = 0x00000000
caller_lr   = 0x7680F105
```

All intermediate addresses are mapped. The nested state field is therefore consistently NULL, not an unmapped/random/timing value.

This remains useful evidence, but B39 now proves it is downstream of an earlier incomplete Eik server initialization.

## Exact post-Leave AV resolution

The first repeated fatal family is:

- write address: `0x00000010`
- PC: `0x802A01C4 = euser.dll + 0xAD7C`
- LR: `0x802A2DF5 = euser.dll + 0xD9AC`
- r0 = 0
- nearest PC export: ordinal 1290
- nearest LR export: ordinal 2176

SymbianSource EABI export map:
- euser ordinal 1290 = `CServer2::DoConnect(RMessage2 const&)`
- euser ordinal 2176 = `UserSvr::DllTls(int,int)`

The B39 Thumb window around the fault contains:

```
... 
BLX  r3
STR  r0,[sp,#8]
STR  r4,[r0,#0x10]
...
```

At the fault r0=0, so the write at address 0x10 is a NULL session object dereference.

SymbianSource `kernel/eka/euser/cbase/ub_svr.cpp` matches this exactly:

```cpp
aSession = NewSessionL(v, aMessage);
if (!aSession->iServer)
    aSession->iServer = this;
```

Therefore a CServer2-derived `NewSessionL()` returned NULL without leaving.

## EikAppUiServer NULL source

SymbianSource classicui:
`commonuisupport/uikon/srvsrc/eiksrv.cpp`

`CEikServAppUiServer::NewSessionL(...)` does:

```cpp
const CEikServEnv* env = static_cast<CEikServEnv*>(CEikonEnv::Static());
MEikServAppUiSessionFactory* factory = env->EikServAppUiSessionFactory();
return (factory ? factory->CreateSessionL() : NULL);
```

So the NULL session has one direct meaning here:
`EikServAppUiSessionFactory()` was not installed.

The System GUI installs that factory only near the end of:
`uifw/EikStd/srvuisrc/EIKSRVUI.CPP`
`CEikServAppUi::ConstructL()`:

```cpp
STATIC_CAST(CEikServEnv*,CEikonEnv::Static())
    ->SetEikServAppUiSessionFactory(this);
```

## Earlier causal boundary found in the first native eiksrvs instance

The first canonical eiksrvs instance starts normally:

1. eiksrvs is spawned at ~23:06:07.088.
2. Main becomes `EikAppUiServerThread`.
3. B30 rooted `EiksrvUi.dll` load succeeds.
4. ViewServer thread is created.
5. `!ViewServer` is registered.
6. parent continues, proving the ViewServer Rendezvous completed.
7. `c32root.dll` loads at ~23:06:07.384.
8. immediately afterward:
   `Unimplemented IPC call: 0x4 for server: !Loader`
9. the first canonical eiksrvs instance never reaches the point where it exposes a healthy `!EikAppUiServer` / installs the AppUi session factory.

Later clients repeatedly summon eiksrvs because the expected EikAppUi server is absent. Those partial/duplicate startup paths eventually reach a CServer2 connect with the factory still NULL, producing the B39 NULL session and the euser write AV.

## Symbian source proves Loader opcode 4 is on the exact initialization path

In `CEikServAppUiBase::InitializeL()`, after ViewServer setup:

```cpp
TInt err = StartC32();
if (err != KErrNone && err != KErrAlreadyExists)
    User::Leave(err);

err = User::LoadPhysicalDevice(COMMS_PDD_NAME);
if (err != KErrNone && err != KErrAlreadyExists && err != KErrNotFound)
    User::Leave(err);

err = User::LoadLogicalDevice(COMMS_LDD_NAME);
if (err != KErrNone && err != KErrAlreadyExists && err != KErrNotFound)
    User::Leave(err);
```

For target builds:
- PDD = `EUART1`
- LDD = `ECOMM`

Symbian comms source/docs confirm `StartC32()` starts/configures the communications root server and blocks until the required startup state is reached.

EKA2L1 loader opcode map:
- 3 = `ELoadLogicalDevice`
- 4 = `ELoadPhysicalDevice`

Thus the runtime opcode 0x4 is the exact `User::LoadPhysicalDevice("EUART1")` call expected at this point.

## Why B39 hangs rather than Leave(-5)

B39 is built from the older B28 cache lineage. Its runtime log prints the unknown IPC line at warning level.

Upstream EKA2L1 commit:
`9f28c76fe0f54f43a39319da5f4042c853505807`
(`services: Complete a request nothing implements, do not drop it`)

documents the old behavior precisely: unknown server IPC was logged and then dropped without completing the message. That wedges a synchronous `SendReceive` forever.

Therefore B39's `User::LoadPhysicalDevice()` does not return an error; it remains blocked. This also explains why there is no immediate Leave(-5) following the Loader warning.

## Exact upstream functional reference

Upstream EKA2L1 commit:
`0987745cc0bde96511fce2a4bfefcfd8fbced3dc`
(`loader: Answer Loader::LoadPhysicalDevice`)

adds only the missing physical-device loader path:
- declaration `loader_server::load_physical_device`
- parse PDD name
- complete bad descriptor with `KErrArgument`
- otherwise complete `ELoadPhysicalDevice` with `KErrNone`
- register opcode `ELoadPhysicalDevice`

The upstream commit message identifies the same failure class: Loader::LoadLogicalDevice already had an answer, opcode 4 did not, so a client that loads a PDD waits forever on the synchronous request.

This is a stronger and narrower reference than globally completing every unknown IPC with KErrNotSupported.

## Root-cause conclusion

Primary root cause for the B39 chain:

```
CEikServAppUiBase::InitializeL
 -> StartC32 completes
 -> User::LoadPhysicalDevice("EUART1")
 -> !Loader opcode 0x4 / ELoadPhysicalDevice
 -> B39 HLE Loader has no opcode-4 handler
 -> old generic dispatcher logs and drops synchronous IPC
 -> first canonical eiksrvs blocks before ConstructL finishes
 -> SetEikServAppUiSessionFactory(this) is never reached
 -> healthy !EikAppUiServer is not established
 -> later/repeated eiksrvs startup sees factory == NULL
 -> CEikServAppUiServer::NewSessionL returns NULL
 -> CServer2::DoConnectL dereferences NULL session
 -> STR [r0,#0x10] with r0=0
 -> KERN-EXEC 3
```

The AvkonFep Leave(-3)/nested NULL state is therefore not selected as the first behavioral target. It is observed in a guest whose System GUI initialization has already been broken upstream.

## Eliminated hypotheses

Not selected:
- SetNonFading completion: occurs downstream; B37/B38 already ruled it out.
- WindowServer CreateWindow: succeeds and returns a positive handle.
- SVC 0xDF LeaveStart remapping: Leave is trapped normally.
- request-semaphore lost wakeup: EKA2L1 request semaphore is counting.
- ViewServer thread Rendezvous: parent proceeds to load c32root.dll after `!ViewServer`.
- iOS/UIKit host crash: no matching host crash evidence in this B39 run; Exit Emulator remains healthy.

## iOS/host result

No B39 evidence requires an iOS-specific fix.

Exit Emulator still reaches:
- `os_join_begin`
- `os_join_done`
- `shutdown_done`
- `normal_restart_done has_device=1`

The active blocker is guest Symbian startup compatibility in the HLE Loader path.

## Selected next candidate

Preferred B40:
**NATIVEBOOT2-B40-LOADERPDD1** (name may be normalized before implementation).

Scope:
- port only the upstream `Loader::LoadPhysicalDevice` behavior from `0987745cc0bde96511fce2a4bfefcfd8fbced3dc`;
- register `ELoadPhysicalDevice` / opcode 4;
- validate the PDD descriptor;
- return `KErrNone` for the HLE-backed physical device;
- add one narrow B40 runtime marker to prove `EUART1` reaches/completes the handler.

Do NOT:
- globally alter unknown-IPC completion semantics as part of B40;
- suppress KErrCancel or FEP Leaves;
- change CServer2/EikAppUiServer to tolerate NULL sessions;
- force-set the Eik session factory;
- modify WindowServer, scheduler, SVC mappings, loader library resolution, or iOS shutdown behavior.

## B40 acceptance evidence

On device, require ordering showing:

1. `Loader::LoadPhysicalDevice` receives `EUART1`.
2. opcode 4 completes KErrNone.
3. initialization progresses beyond the former 23:06:07.384 boundary.
4. first canonical eiksrvs reaches a healthy `!EikAppUiServer` / no repeated missing-server summon loop.
5. the 16 repeated CServer2 NULL-session AV family disappears or moves to a new later boundary.
6. B34 Exit Emulator remains healthy.

Only after that should B40 be considered for promotion.
