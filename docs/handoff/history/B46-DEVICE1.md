# NATIVEBOOT2 B46 DEVICE1 — AKNSKINROUTE2

Updated: 2026-09-23
Branch: nativeboot2-current
Status: DEVICE-OBSERVED; ROUTE SUCCESS
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Previous diagnostic: B45 DEVICE1

## Executive result

B46 successfully removes HLE !AknSkinServer from RM-356 native boot and restores
the stock Symbian startup choreography.

The guest receives KErrNotFound, launches AknSkinSrv.exe itself, native
!AknSkinServer registers, and subsequent clients bind with server_hle=0.

The native server remains alive through the test.

TFX still does not start. No tfxsrvplugin, ALF, or TfxServer registration is
observed.

## Log integrity

- EKA2L1(7).log
  - 54,837 bytes
  - 266 lines
  - SHA-256:
    `15c5bff3997ee62c0332dc8ed0c0514c59ab6227cec06b6eb3009103ba10c902`
- EKA2L1_Persistent(7).log
  - 6,059,213 bytes
  - 26,391 lines
  - SHA-256:
    `802f308e0b562baa96319802bf62e25970962b1a31aac26c95a9a8fa4af4e132`
- EKA2L1_TakeThis(7).log
  - 5,946,991 bytes
  - 25,848 lines
  - SHA-256:
    `3be362dba20e5c07b96fb03f359aea149c5b9a8c845f4d359fe62428693dcb20`

## B46 acceptance chain

At 16:24:00.897:

```text
AKNSKIN_ROUTE2 decision=skip_hle
firmware_code=RM-356
model=5800 XpressMusic
epoc=10
native_phone_boot=1
```

At 16:24:32.583:

```text
eiksrvs CreateSession(!AknSkinServer)
lookup found=0 server_hle=-1
missing result=-1
Trying to summon: AknSkinSrv.exe
AKNSKIN_NATIVE_PROC phase=request
```

At 16:24:32.590-32.592:

```text
Spawned process: AknSkinSrv
aknskinsrv.exe UID3=0x10207114
AKNSKIN_NATIVE_PROC success=1
AKNSKIN_NATIVE_REGISTER !AknSkinServer process_hle=0
AknsSrvSharedMemoryChunk created
```

At 16:24:32.995:

```text
eiksrvs -> !AknSkinServer
found=1 server_hle=0
```

Later native bindings include akncapserver, Home screen, aknnfysrv and
AknIconSrv.

## TFX after native route

Persistent marker counts:
- AKNSKIN_ROUTE2: 3
- AKNSKIN_SESSION: 30
- AKNSKIN_NATIVE_PROC: 2
- AKNSKIN_NATIVE_REGISTER: 1
- TFX_PS: 8
- TFX_SESSION: 29
- TFX_LEAVE: 3

Zero:
- TFX_ECOM_RSC
- TFX_ECOM_DLL
- ALF_SESSION
- ALF_SERVER_REGISTER
- TFX_SERVER_REGISTER

At 16:24:33.010 eiksrvs:
- TFX P&S attaches;
- TfxServer CreateSession still returns KErrNotFound.

At 16:24:33.711 akncapserver does the same; correlated Leave(-1) follows at
16:24:34.017.

Telephone and Home screen later show the same TfxServer family.

## Native AknSkin CenRep leave

At 16:24:35.088:

```text
Try to open repo 0x1028583D
Repository not found with UID 0x1028583D
MENUUI6 LEAVE_NEG1:
  process=AknSkinSrv[10207114]0001
  thread=!AknSkinServer
  leave_code=-1
```

The stack contains centralrepository.dll frames.

This leave is trapped. After it:
- Home screen binds !AknSkinServer server_hle=0 at 16:24:35.295;
- aknnfysrv binds server_hle=0 at 16:24:35.540;
- AknSkinSrv still owns live async requests at teardown.

EKA2L1 HLE calls this UID ICON_CAPTION_UID and explicitly tolerates a missing
repo. Therefore it is not promoted to root cause.

## Source-guided TFX gate

SymbianSource classicui:
`classicui_plat/themes_settings_api/inc/PslnInternalCRKeys.h`

```text
KCRUidThemes             = 0x102818E8
KThemesTransitionEffects = 0x00000009
```

The key semantics:
- zero = all transition effects supported;
- KMaxTInt = all transition effects suppressed.

SymbianSource uiresources:
`skins/AknSkins/srvsrc/AknsSrvSettings.cpp`

`TransitionFxState()` reads key 0x9. Any CenRep Get error is converted to
KMaxTInt.

`CAknsSrv::StartTransitionSrvL()` only calls `LoadTfxSrvPluginL()` if
`TransitionFxState() != KMaxTInt`.

The RM-356 firmware extraction logs prove:
`Z:\private\10202BE9\102818E8.txt` exists.

B46 also opens repo 0x102818E8 successfully at 16:24:32.596 and later saves it.
The unresolved question is exact key 0x9 Get result/value.

## Old milestone health

B42:
- SA_HWRM_ABI 16:24:01.803.
- HWRM kill failure 16:24:31.801.
- delay ~29.998 s.

B40:
- EUART1 PDD result=0 at 16:24:33.303.
- !EikAppUiServer registers 16:24:33.677.

B41:
- MessageWin wipeout guards remain active.
- shutdown_done 16:27:02.198.
- normal_restart_done has_device=1 16:27:02.297.

No KERN-EXEC / EXC_BAD_ACCESS / host access violation appears.

## Next milestone candidate

`NATIVEBOOT2-B47-AKNSKINTFXSTATE1`

Diagnostic-only target:
1. CenRep UID 0x102818E8 key 0x9 Get result/value for native AknSkinSrv.
2. AknSkinSrv Wserv connection just before transition provider startup.
3. ECom CreateImplementation requests for 0x10282DBD and 0x10282DBC.
4. Existing B44 provider markers remain.

Do not modify key 0x9 or fabricate TFX behavior until this evidence is
captured.
