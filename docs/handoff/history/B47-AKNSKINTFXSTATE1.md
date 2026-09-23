# NATIVEBOOT2 B47 — AKNSKINTFXSTATE1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Type: DIAGNOSTIC-ONLY
Functional baseline: B41 WSERVMESSAGEWINEXIT1
Device diagnostic baseline: B46 DEVICE1

## Goal

Observe the first source-guided TFX startup gate inside native AknSkinSrv
without changing any guest-visible behavior.

Targets:
- CenRep UID 0x102818E8 / key 0x00000009;
- AknSkinSrv -> !Windowserver session creation;
- AknSkinSrv -> !ecomserver IPC.

## New markers

`[NBOOT2][AKNSKIN_TFX_STATE]`
`[NBOOT2][AKNSKIN_TFX_WSERV]`
`[NBOOT2][AKNSKIN_TFX_ECOM]`

All are OBSERVE_ONLY.

## Semantic guard

No CenRep writes, no TFX enable override, no Wserv result change, no ECom
function/argument/result rewrite, no fake TfxServer, no P&S synthesis, no
Alfred force-start.

## Canonical RED

- test contract: `4dff83fde398150a534e4f9bb4f641ac3a6635c0`
- pair wiring: `7eb4787e075a72215aa4ce55f217b761f9b8249d`
- run/job: `35847386001 / 107136721921`
- B29-B46 PASS
- expected B47 failure: missing AKNSKIN_TFX_STATE marker.

## Implementation

Primary implementation:
`08ff6f5c86ecdcd518663686cdf902aae27579d1`

Follow-up fixes:
- ECom anchor: `39e624f97944dd071a89c02c8fb9d52964f4a6d3`
- UID annotation: `f53298c978c5808aa66c70a84c5d2aca788c0d34`
- test observe-only boundary: `5cbfba2b7330bb34e7afadafde534df4351543e8`
- test assignment regex: `db1b7258b7808a2b3e04bddd22d9252d5eac6adc`
- process-type include: `ab4415d0f94b002d01e6ea2035600a2dddc99c1d`
- binary invariants: `cc7d53ebb99f0ea754ffc432f9221586bef13fcc`

## Canonical GREEN

Run/job:
`35854365057 / 107159241200`

PASS:
- FASTBUILD1 manifest
- B29-B47 apply/tests
- B20-B28 regressions
- iOS compile/link
- all three B47 Mach-O markers
- IPA package/upload
- audit upload

sccache:
- requests 149
- hits 149
- misses 0
- hit rate 100%
- failures 0

## Artifact

Unsigned IPA SHA-256:

`ae3a0b0e467c19d30277274355c3eb537fdcd75becd55f2f2e463dbca1b27885`

IPA artifact:
- ID `10746604288`
- ZIP digest
  `sha256:cd5f8842f473c4244281de3430ff72ced4eec2f4490a27a912fa4e2598557adc`

Audit artifact:
- ID `10746932579`
- digest
  `sha256:7747fcb0e01ea2088f6181ff6420bffeab24eb37234724c67a340ccdcf6ac06e`

Local re-hash matches CI.

## Device-test decision tree

1. Read AKNSKIN_TFX_STATE.
2. If key 0x9 is missing/error or value is KMaxTInt, TFX is intentionally
   suppressed at the Themes CenRep gate.
3. If key 0x9 permits TFX, inspect AKNSKIN_TFX_WSERV.
4. If Wserv succeeds, inspect AKNSKIN_TFX_ECOM.
5. Then classify ECom resource/DLL/ALF/TfxServer markers.

Do not implement B48 behavior before this device evidence.
