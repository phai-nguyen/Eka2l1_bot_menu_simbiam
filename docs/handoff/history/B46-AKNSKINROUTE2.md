# NATIVEBOOT2 B46 — AKNSKINROUTE2

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: GUARDED NATIVE-ROUTE SELECTION FIX
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Device diagnostic baseline: B45 DEVICE1

## Purpose

Repair B45 route selection without changing TFX/ALF semantics.

B45 DEVICE1 proved the intended native route was blocked by two bad gates:
1. exact `epocver::epoc94` equality;
2. pre-mount Z-overlay existence checks.

B46 uses installed-device metadata already available before HLE service
creation.

## Route contract

```text
device *current = sys->get_device_manager()->get_current()
rm356 = firmware_code starts with "rm-356" or "RM-356"
route = cfg->native_phone_boot && rm356
```

If `route` is true:
- skip pre-creating HLE `akn_skin_server`;
- allow stock guest `CreateSession("!AknSkinServer")` to observe the real
  missing-server condition;
- allow the stock client to decide whether to run its normal StartServer path.

If false:
- create HLE AknSkinServer exactly as before.

The old epoc and Z probes are retained only for diagnostic comparison.

## Marker

`[NBOOT2][AKNSKIN_ROUTE2]`

Fields include:
- decision skip_hle / keep_hle;
- firmware_code;
- model;
- runtime epoc integer;
- epoc94 diagnostic bit;
- native_phone_boot;
- pre-mount sysbin/legacy existence bits;
- behavior.

## Preserved diagnostics

B45:
- AKNSKIN_ROUTE
- AKNSKIN_SESSION
- AKNSKIN_NATIVE_PROC
- AKNSKIN_NATIVE_REGISTER
- AKNSKIN_ROM

B44:
- TFX_PS
- TFX_ECOM_RSC
- TFX_ECOM_DLL
- ALF_SESSION
- ALF_APPARC_GETINFO
- TFX_MANIFEST

B43/B42/B41/B40 invariants remain intact.

## Semantic guard

B46 does not:
- change EKA2L1's global epoc version;
- fake/register TfxServer;
- force AknSkinSrv process creation from host code;
- force Alfred;
- synthesize ECom success;
- synthesize P&S values;
- synthesize IPC completion.

This remains emulator interoperability/startup debugging only.

## TDD

RED:
- test: `c2e6477a3bbf9424a3e7dc33d0191f7ba3506517`
- manifest: `79120778aa07de6a8e727d6ae39735ee717b88cc`
- run/job: `35840641091 / 107114600500`
- B29-B45 PASS
- B20-B28 regressions PASS
- expected B46 failure: missing AKNSKIN_ROUTE2.

Implementation:
- `e38c0b38211d0cf19b19eba3fdbfc739ccddcd10`
- manifest activation:
  `abb40f03b0a12bf64d51b91e139466d732fceafc`
- binary-invariant commit:
  `fc15de9e3c3e324142e33088990ca6ce25f27403`

## Canonical GREEN

- run: `35841200270`
- job: `107116409392`
- manifest VALID
- B29-B46 PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- AKNSKIN_ROUTE2 Mach-O invariant PASS
- IPA package/upload PASS
- compile requests/hits/misses: `149 / 149 / 0`
- actual compilations: `0`
- compilation failures: `0`

## Artifact

Unsigned IPA SHA-256:

`a536852b1c4f916e0b99e6a97aa36a315f434578e3830ce8c67824e9a0aaeab9`

IPA:
- artifact ID `10740833931`
- ZIP digest
  `sha256:af91c0905dcd8d0e6026e3347ed00453c11da118a2c39dfc47f9f4065125fef7`

Audit:
- artifact ID `10740769226`
- digest
  `sha256:31bf2b832b768291a8ebae26b3ccd53ff7cd8ffbbdcc6de976b7a3bd335edbe1`

Local IPA re-hash matches CI.

## Device acceptance

Primary expected sequence:

```text
AKNSKIN_ROUTE2 decision=skip_hle
AKNSKIN_SESSION request !AknSkinServer
AKNSKIN_SESSION lookup found=0
AKNSKIN_SESSION missing result=-1
AKNSKIN_NATIVE_PROC request aknskinsrv.exe
```

Then inspect:
- process creation result;
- native `!AknSkinServer` registration;
- first native session;
- TFX ECom/P&S;
- ALF;
- TfxServer.

If the sequence stops before registration, that exact stop point is the next
blocker.
