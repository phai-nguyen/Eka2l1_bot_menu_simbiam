# B90 COMPATBOOT1 DEVICE1 — Menu3 first dependency

Updated: 2026-09-26
Branch: `codex/compatboot1-menuprobe1`
PR: #6 (open; not merged)
Build tested: FASTBUILD #281, run `36241917700`, commit `0bced6f0f897cfcce0e214ce77814177800c9887`

## Result

The explicit CompatBoot barrier reached ready state and launched the real RM-356
`Z:\sys\bin\menu3.exe` process. The Menu3 visible-surface marker did not
fire. The first Menu3-owned missing-server failure is `TfxServer`.

More importantly, the B90 log shows an earlier guest configuration gate:

```text
19:49:16.952 [NBOOT2][AKNSKIN_TFX_STATE]
repo=0x102818E8 key=0x00000009 result=0 value=0x7FFFFFFF
 enabled=0 suppressed=1 behavior=OBSERVE_ONLY
```

This is the existing B47 interpretation of the RM-356 Themes CenRep TFX gate:
`KMaxTInt` suppresses TFX. The first system-wide `CreateSession("TfxServer")`
miss follows at 19:49:16.979 from `eiksrvs`; Menu3 later hits the same absent
server at 19:49:21.932 and emits `[COMPATBOOT][FIRST_FAILURE]`.

The value matches the extracted stock RM-356 V60 ROM repository file
`Z:\\private\\10202BE9\\102818E8.txt`, whose key `0x9` is
`int 0x7fffffff` (documented in B47 and the firmware extraction report).
B90 also logs generic `Repo 0x102818E8: changes saved` events, but those lines
do not identify any changed key or value; they do not prove that key `0x9`
was written or altered.

## Startup evidence

- `19:49:16.415`: CompatBoot barrier ready with FileServer, FBS, WindowServer,
  CenRep, AppArc and AknCapServer.
- `19:49:16.433`: real `menu3.exe` launched; process `menu3[101f4cd2]0001`.
- `19:49:16.542`: native guest `AknSkinSrv.exe` starts and registers
  `!AknSkinServer`.
- `19:49:16.546`: Themes CenRep repository `0x102818E8` is opened; key `0x09`
  is read as suppressed before the first TfxServer request.
- `19:49:18.956–19:49:20.155`: Menu starts `alfredserver.exe`; it registers
  `10282845_10282845_AppServer`, and Menu connects successfully. Alfred is
  therefore running; its AppServer is not the missing endpoint.
- `[COMPATBOOT][TARGET_VISIBLE]`: 0 occurrences.
- `[NBOOT2][TFX_ECOM_DLL]` and `[NBOOT2][TFX_SERVER_REGISTER]`: 0 occurrences.
  AknSkinSrv does send generic ECom IPC requests; the log does not show a TFX
  plugin DLL load or TfxServer registration.

## Conclusion and next step

B90 reached the intended real Menu3 probe. The first failure exposed to Menu3 is
`TfxServer`, while the earliest relevant gate in the trace is the firmware
Themes CenRep setting that suppresses TFX. The observed value matches the
extracted ROM default. B90 alone cannot tell whether the emulator's runtime
repository was later modified: its generic save lines do not contain per-key
write details. No evidence currently justifies changing key `0x9`.

Next, keep the stock gate and missing-server semantics intact while diagnosing
the first Menu3 failure in context. If a future question specifically requires
proving whether key `0x9` changes at runtime, add item-level write tracing;
generic repository save messages are insufficient. Do not change the firmware,
force-enable TFX, fabricate `TfxServer`, or treat Alfred startup as a
substitute for the TFX provider.

## Log integrity

- `EKA2L1_TakeThis(20260926-125351).log` SHA-256:
  `1376980bafea7205c178c73613d51135dcada20e1ab13672e2d796f020343568`
- `EKA2L1_Persistent-prev(20260926-125331).log` SHA-256:
  `dada1a55c35a8502d7e2fea8a144b64e79e0d3c169f22669bd26fbe70e338fb4`
- `EKA2L1(20260926-125307).log` and `EKA2L1_Persistent(20260926-125306).log`
  are byte-identical; SHA-256:
  `3ce5c3b55078645537bac8c985103c84abadb32df4744357e39c4f51af6a0842`
