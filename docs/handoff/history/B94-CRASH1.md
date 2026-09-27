# B94 device evidence — installed over, old logs cleared

Date: 2026-09-27 (user-provided device capture)

## Test conditions

The user confirms B94 was installed over the previous app installation, with old logs cleared before the run. The user also confirms the video shows EKA2L1 running and then crashing to the iOS Home screen; they did not swipe the app away. This is a separate result from B93, which was manually exited without a crash.

Evidence files:

- `Log b94.zip` — SHA-256 `5a039975e54990e3cd02f856dafd9f50b182bfabf517467de2b7e8f1efc9b4a5`
- `eka2l1-2026-09-27-092033.ips` — SHA-256 `9390defa11dbe2df9a14d935600f7233dcd8e43bcab98be4eb1dd76a89519026`
- `ScreenRecording_09-27-2026 09-19-39_1.mp4` — SHA-256 `878fcdd7d244270f66e07f6168f9ec146ed798d702e54c055e8db5ce48acc955`

## CompatBoot result

- `[COMPATBOOT][BARRIER_READY]` at 09:20:18.482; real `Z:\sys\bin\menu3.exe` launched at 09:20:18.510.
- `[COMPATBOOT][MENU3_FSFLUSH]` recorded two calls:
  - `z:\Private\10207254\themes\270486738\270513751\271067333\1.0\hasclassicgrid.o0001` — `flush_ok=1`, `completion=0`
  - `C:\private\101F4CD2\appshell.ini` — `flush_ok=1`, `completion=0`
- Menu3 still logged trapped `Leave(-5)` and the first missing `TfxServer`; its CenRep FindEqInt query against `0x102858F2` returned zero matches. No `[COMPATBOOT][TARGET_VISIBLE]` was recorded.
- These results do not establish that the leave, TfxServer miss, or CenRep query caused the host crash. Both FileFlush calls succeeded.

## iOS crash report

The report identifies process `eka2l1`, launched at 09:19:38.508 and captured at 09:20:32.6737 (+0700). It records `EXC_BAD_ACCESS`, `KERN_PROTECTION_FAILURE` at `0x105B49478`, and termination namespace `CODESIGNING` / indicator `Invalid Page`. The faulting PC resolves to `vtable for eka2l1::kernel::chunk + 16` (instruction abort / permission fault).

The relevant backtrace is:

`notify_info::complete(int)` → `property::cancel(...)` → `property_reference::~property_reference()` → kernel object-vector erase → `kernel_system::destroy()` → `kernel_obj::decrease_access_count()` → `object_ix::reset()` → `process::kill()` → `epoc::process_kill()` → guest SVC dispatch.

This confirms a host crash during kernel object/property-notification teardown while servicing a guest process-kill call. The vtable address used as an instruction target points toward an invalid virtual dispatch or object-lifetime problem; the report does not by itself prove which object was stale, nor identify which guest process initiated the kill. The CODESIGNING label accompanies the invalid executable page and is not evidence of a bad app signature.

The log ends at 09:20:32.660, with no normal emulator shutdown completion. The guest thread messages that end peacefully at that timestamp are not evidence that the iOS app was manually closed.

## Next investigation

Inspect the B28 source ordering and ownership rules across the stack above, identify the property/chunk object and the process being killed, then add narrowly scoped read-only diagnostics or a focused reproducer if the source review does not establish the lifetime error. Do not alter firmware, CenRep values, TFX behavior, guest files, or the readiness barrier based on this capture.