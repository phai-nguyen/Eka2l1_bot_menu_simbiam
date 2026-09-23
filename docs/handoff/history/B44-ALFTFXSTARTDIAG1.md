# NATIVEBOOT2 B44 — ALFTFXSTARTDIAG1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: DIAGNOSTIC ONLY
Functional baseline: B41 WSERVMESSAGEWINEXIT1 remains latest immutable functional milestone
Device diagnostic baseline: B43 TFXSERVERDIAG1

## Purpose

B43 proved two deterministic same-thread akncapserver chains:

```text
CreateSession("TfxServer") -> KErrNotFound(-1)
-> User::Leave(-1) -> self-kill(-1)
```

Deep Research against primary Symbian/Nokia source shows that the fastest next
step is not to force Alfred or fake TfxServer. B44 instruments the complete
provider-startup graph in a single IPA.

## Source-guided provider graph

Primary target:

```text
AknSkinSrv
-> REComSession::CreateImplementationL(0x10282DBD / 0x10282DBC)
-> tfxsrvplugin.rsc / tfxsrvplugin.dll
-> DLL UID 0x10282DBA
-> TFX P&S category 0x10207218 key 0x2
-> RAlfTfxClient
-> alfstreamerserver
-> ALF backend
-> TfxServer
```

Parallel AppArc/Alfred branch:

```text
GetAppInfo(0x10282845)
-> alfredserver_reg.rsc
-> alfredserver.exe / alfserver.exe process creation
-> 10282845_10282845_AppServer
```

Additional observed ALF AppServer candidate:
`10282848_10282848_AppServer`.

## Instrumentation

### Kernel

`session_create` observes:
- `alfstreamerserver`
- `10282845_10282845_AppServer`
- `10282848_10282848_AppServer`

Markers:
- `[NBOOT2][ALF_SESSION]`
- `[NBOOT2][ALF_SERVER_REGISTER]`

P&S exact filter:
- category `0x10207218`
- key `0x00000002`

Marker:
- `[NBOOT2][TFX_PS]`

Stable category/key Get/Set and handle-based Set paths are observed. Values are
never changed by B44.

### Loader

Exact process candidates:
- `alfredserver.exe`
- `alfserver.exe`

Marker:
- `[NBOOT2][ALF_PROC_CREATE]`

Exact TFX provider DLL:
- `tfxsrvplugin.dll`
- expected UID3 `0x10282DBA`

Marker:
- `[NBOOT2][TFX_ECOM_DLL]`

B43 `[TFX_RESOLVE]` remains preserved.

### AppList/AppArc

One-shot ROM inventory:
- `z:\sys\bin\alfredserver.exe`
- `z:\sys\bin\alfserver.exe`
- `z:\sys\bin\tfxsrvplugin.dll`
- `z:\resource\effects\manifest.mf`
- `z:\private\10003a3f\apps\alfredserver_reg.rsc`
- likely plugin-resource candidates

Markers:
- `[NBOOT2][ALF_ROM_ARTIFACT]`
- `[NBOOT2][ALF_APPARC_REG]`
- `[NBOOT2][ALF_APPARC_GETINFO]`

The B28 bootstrap predates the newer upstream `commit_registry()` helper, so
B44 deliberately does not port that behavior. Registry existence is observed
through the UID `0x10282845` lookup path only.

### FileServer

Normalized file-open requests are filtered for:
- `tfxsrvplugin`
- `10282dba`
- `manifest.mf`

Markers:
- `[NBOOT2][TFX_ECOM_RSC]`
- `[NBOOT2][TFX_MANIFEST]`

Each request records an immediate host-side `exists=0/1` snapshot without
modifying the file operation.

## Semantic guard

B44 does not:
- create or redirect TfxServer;
- turn KErrNotFound into KErrNone;
- force Alfred/ALF process startup;
- force ECom UID-to-DLL resolution;
- set or define the TFX running property on behalf of the guest;
- edit descriptors;
- complete unknown IPC;
- alter HWRM B42 behavior.

B36/B37/B40/B41/B42/B43, stock AvkonFep, firmware SYSSTART ownership,
EPOC94 mappings, native fbserv, NOJAVA and MANIC3 are preserved.

## TDD

RED:
- `ff910c5e8072b27b737b07e376564cce8c5b9db2`
- manifest RED: `e177e561a166e6d902c93841f3be98daa2186e5d`
- run/job: `35816770777 / 107039852137`
- previous milestones/regressions PASS
- expected fail: missing `[NBOOT2][ALF_SESSION]`

Final implementation:
- `d9f8e8fabecb3f5af4b28f10413166e6fa07d4f6`

Binary-invariant commit:
- `b7810836cbb252dcf4232377345e84dfb4037797`

Canonical GREEN:
- run/job: `35818238348 / 107044317789`
- B29-B44: PASS
- B20-B28 regressions: PASS
- compile/link: PASS
- B44 binary markers: PASS
- package/upload: PASS
- compile requests/hits/misses: `149 / 149 / 0`
- real compilations: `0`
- compilation failures: `0`

## Artifact

Unsigned IPA SHA-256:

`5797d71f39bb790ebbae605459f03ce9d248fd713e8a3def0fa450a51eba2870`

IPA artifact:
- `10732596370`
- ZIP digest:
  `sha256:41bbc1cfffac4def2e248ddaf0c4c9702cbc6ad4ff888fae52a0ec9a4619a5cf`

Audit artifact:
- `10732566416`
- digest:
  `sha256:37c73a442c9fb28287b9efcd6a735a652cc21860230f51547103d5d7aa930d28`

## Device acceptance

A successful diagnostic run should identify the earliest missing stage among:

1. ROM artifacts.
2. TFX ECom resource request.
3. tfxsrvplugin.dll load.
4. TFX P&S status activity.
5. alfstreamerserver session/registration.
6. Alfred AppArc registration/GetAppInfo/process creation.
7. final TfxServer registration.
8. akncapserver CreateSession outcome.

The run may still fail exactly like B43; that is acceptable if it identifies
the missing provider boundary.

Preserve the B42 ~30-second HWRM delay for clean chronology comparison.
