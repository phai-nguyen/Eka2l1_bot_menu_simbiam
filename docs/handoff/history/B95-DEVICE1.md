# B95 — installed-over test with previous logs retained

Date: 2026-09-27 (user-provided device capture)

## Test result

The user installed over the previous app and retained the old logs. The new
CompatBoot run is isolated in both `EKA2L1_TakeThis(20260927-042309).log` and
the later portion of `EKA2L1_Persistent-prev(20260927-042233).log`:

- Run starts at 11:16:11.657.
- The six-service barrier is ready at 11:16:43.362; real `menu3.exe` launches
  at 11:16:43.382.
- Menu's first `Leave(-5)` is logged at 11:16:48.479.
- Menu's first CompatBoot `TfxServer` miss is logged at 11:16:48.517.
- The recording is 247.467 seconds. It shows “Phone start-up failed” persisting
  until the user opens **Thoát Emulator** near the end.
- At 11:20:08.228 the log records `exit_requested`, followed by
  `shutdown_done` and `normal_restart_begin`. This is an orderly manual exit,
  not an automatic crash to iOS Home.

The log contains a guest `SosPmmHandler` thread panic at startup; that is a
Symbian guest event and does not indicate an iOS host-app crash.

## TfxServer diagnosis

At 11:16:43.889 AknSkinSrv reads Themes CenRep repository `0x102818E8`, key
`0x09`, as `0x7FFFFFFF`, with `enabled=0 suppressed=1`. The extracted stock
RM-356 ROM defines the same value at
`private/10202be9/102818e8.txt:17`. ROM files `tfxserver.dll`,
`tfxsrvplugin.dll`, `aknlistloadertfx.dll`, `transitionserver.dll`, and
`aknskinsrv.exe` are present, but the run has no `[NBOOT2][TFX_ECOM_DLL]` or
`[NBOOT2][TFX_SERVER_REGISTER]` event.

The stock setting explains why no public `TfxServer` provider is registered.
However, the first Menu `Leave(-5)` occurs 38 ms before Menu's own TfxServer
miss. Other clients also request TfxServer while startup continues. The capture
therefore does not establish the absent TfxServer as the cause of the Menu
leave or the visible phone startup failure.

The first Leave stack has five EStor code candidates, including offsets
`0x38AA`, `0x777C`, `0x358E`, `0x35A4`, and `0xA76C`, plus an
`XnRequestClient.dll` candidate. The matching Menu `FileFlush` of the theme
object succeeds (`flush_ok=1`, `completion=0`), so that call is not evidence of
a failed flush. See B96 for the read-only export/instruction probe added to
resolve those stack locations.

## Evidence integrity

- `ScreenRecording_09-27-2026 11-16-05_1.mp4` SHA-256:
  `a5d34d59926642d7bdded5a672d74616182948d38d5e3adf3d93ab8f20b42226`
- `EKA2L1_TakeThis(20260927-042309).log` SHA-256:
  `2947d89a634fcf83f4c7732543402d03318d571c08dfe20edf825d85a84a32e0`
- `EKA2L1_Persistent-prev(20260927-042233).log` SHA-256:
  `cd1df7d38f67f7b67c6d2913b760f9c872cdea51159c8dba2d9436304c79e4fd`
- `EKA2L1(20260927-042206).log` and
  `EKA2L1_Persistent(20260927-042207).log` are byte-identical; SHA-256:
  `5e6a13111c02339e6f89312bff3359faa5f3526a4856b60fcacfc3784080bbee`

No firmware, CenRep value, server behavior, or readiness condition was changed
as a result of this test.
