# NATIVEBOOT2 B45 — AKNSKINNTFX1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: GUARDED NATIVE-ROUTE EXPERIMENT
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Device diagnostic baseline: B44 ALFTFXSTARTDIAG1

## Purpose

B44 proved:
- EKA2L1 HLE `!AknSkinServer` is active on RM-356;
- TFX P&S `0x10207218/0x2` is undefined before client attach;
- no tfxsrvplugin/ALF/TfxServer provider path executes.

B45 tests the source-confirmed native route without fabricating any TFX state.

## Primary Symbian source contract

### Native executable

`skins/AknSkins/group/AknSkinSrvMain.mmp`:

```text
TARGET          AknSkinSrv.exe
TARGETTYPE      EXE
TARGETPATH      /system/programs
UID             0x1000008d 0x10207114
```

### Native DLL

`skins/AknSkins/group/AknSkinSrv.mmp`:

```text
TARGET          AKNSKINSRV.dll
TARGETTYPE      DLL
UID             0x1000008D 0x10005A35
LIBRARY         ws32.lib
LIBRARY         ecom.lib
```

### Client startup

`RAknsSrvSession::Connect()`:

```text
CreateSession(!AknSkinServer)
if KErrNotFound / KErrServerTerminated:
    StartServer()
retry CreateSession
```

`StartServer()` launches `KAknSkinSrvExe` via `RProcess::Create`, performs
Rendezvous/Resume, and waits for startup completion.

### TFX provider startup

Native `CAknsSrv::PrepareMergedSkinContentUnprotectedL()` ends with:

```text
StartTransitionSrvL(tfxServerRunning)
```

`LoadTfxSrvPluginL()` calls ECom:

- `KTfxSrvCtrlEcomImpl = 0x10282DBD`
- `KTfxSrvEcomImpl = 0x10282DBC`

This source contract directly explains why HLE interception can suppress the
provider side effects observed missing in B44.

## B45 route

The HLE is skipped only when all are true:

```text
cfg->native_phone_boot
&& epoc == epoc94
&& native AknSkinSrv.exe exists in ROM
```

Checked paths:

- `z:\sys\bin\aknskinsrv.exe`
- `z:\system\programs\aknskinsrv.exe`

Otherwise EKA2L1 still executes:

```cpp
CREATE_SERVER(sys, akn_skin_server);
```

B45 does not directly invoke RProcess::Create. It lets the stock guest client
decide whether/when to start its native server.

## Markers

- `[NBOOT2][AKNSKIN_ROUTE]`
- `[NBOOT2][AKNSKIN_SESSION]`
- `[NBOOT2][AKNSKIN_NATIVE_PROC]`
- `[NBOOT2][AKNSKIN_NATIVE_REGISTER]`
- `[NBOOT2][AKNSKIN_ROM]`

B43/B44 markers remain intact.

## Safety/fidelity guard

This is emulator interoperability work only.

No network attack, access-control bypass, malware behavior, or external-system
access is involved.

Guest fidelity constraints:
- no fake TfxServer;
- no forced Alfred;
- no ECom success synthesis;
- no P&S definition/value synthesis;
- no unknown-IPC completion synthesis;
- no service-route change outside native_phone_boot EPOC9.4;
- no HLE removal when native AknSkinSrv image is absent.

## TDD

Canonical RED:

- contract: `2c19fac5446e8e3fddf37a991094a927e184e23d`
- manifest: `760df37fe003a3899b778c456c253a7aad67ce4c`
- run/job: `35820882559 / 107052262345`
- B29-B44 PASS
- old regressions PASS
- expected failure:
  `missing in B45 init marker: [NBOOT2][AKNSKIN_ROUTE]`

Implementation lineage:

- `b6873465a60f3d6eb1fe17e6e60efb99219274bc`
- `6cdd56945ae6a0910c24ab6c253a2c8f2a8d1962`
- final implementation:
  `512f30981971f340dd45d2828754856782076122`
- binary invariants:
  `956b3f4df2354af31c5ca017fd3b004f58b13b5e`

## Canonical GREEN

- run: `35821489397`
- job: `107054091391`
- manifest valid
- B29-B45 PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- B45 binary invariants PASS
- IPA package/upload PASS
- compile requests/hits/misses: `149 / 149 / 0`
- actual compilations: `0`
- compilation failures: `0`

## Artifact

Unsigned IPA SHA-256:

`0a4f794ab29943d97cf5613ade8558852a482c07ca3931a07513adc5e7d361e6`

IPA:
- artifact ID `10733511496`
- ZIP digest
  `sha256:f4d9da039f28db8038ba9e9f71f7442279c0096090beac77fa561f5b8c7e120b`

Audit:
- artifact ID `10733377076`
- digest
  `sha256:6586fdedc31ef93aab938353fbb5e2ec4c4dd8d0afacc64c5a8b4ad8a0e44917`

## Device acceptance

Test normal RM-356 boot.

Primary sequence to look for:

```text
AKNSKIN_ROM
AKNSKIN_ROUTE hle_skip
AKNSKIN_SESSION missing
AKNSKIN_NATIVE_PROC request
AKNSKIN_NATIVE_PROC success
AKNSKIN_NATIVE_REGISTER
AKNSKIN_SESSION found server_hle=0
TFX_ECOM_RSC / TFX_ECOM_DLL
TFX_PS define/set
ALF_SESSION
TfxServer registration
```

If the sequence stops earlier, that stop point becomes the next narrow blocker.

B41 exit behavior should still be tested if the UI remains responsive enough to
use Thoát Emulator.
