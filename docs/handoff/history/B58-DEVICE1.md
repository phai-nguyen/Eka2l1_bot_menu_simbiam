# NATIVEBOOT2 B58 STARTUPSTATEPS1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; STATE READBACK SUCCESS; EXIT CRASH OBSERVED

## Inputs

- EKA2L1(20260924-114347).log
- EKA2L1_Persistent(20260924-114349).log
- EKA2L1_TakeThis(20260924-114343).log
- ScreenRecording_09-24-2026 18-36-26_1.mp4
- eka2l1-2026-09-24-184038.ips

B57 was removed and B58 installed fresh before this run.

## Visual result

The ~256.6 s recording reproduces the same normal NATIVEBOOT2 path:

- Nokia splash remains visible for the early boot interval.
- Around the natural Splash -> Startup handoff the Nokia logo disappears.
- Startup becomes a stable blank white full-screen surface.
- No Nokia hands / welcome animation appears.
- User opens Emulator exit menu near the end and selects "Thoát Emulator".
- The app then exits unexpectedly to the iOS Home screen.

Thus B58 does not advance beyond real-device visual checkpoint B.

## Startup state readback

Exactly one B58 Startup-state marker is present:

[NBOOT2][STARTUP_STATE_PS]
category=0x100058F4
key=0x00000001
before=0
requested=1
after=1
set_result=1
path=CATEGORY_KEY_INT
behavior=PRESERVE_EXISTING_SET_INT

This proves the current baseline correctly writes:

KPSStartupAppState: 0 -> EStartupAppStateWait (1)

No B58 category/key marker requests value 2 during the run.

Therefore the observed blank-white state remains consistent with Startup waiting
for the next synchronization stage. The next writer diagnostic must also cover
the handle-based RProperty integer setter before concluding no component ever
writes StartAnimations=2.

## Related boot evidence

SYSSTART UID 0x100059C9 starts StarterServer.

Early SYSSTART/Starter activity also launches DosServer. DosServer reaches ETel
and fails to open subsession PACKET_NAME, producing a trapped Leave(-1) in the
DosServer SAEThread. Treat this as a possible upstream normal-boot dependency,
not yet as the selected cause.

## Host crash on exit

The supplied Apple crash report is definitive:

- exception: EXC_BAD_ACCESS
- signal: SIGSEGV
- invalid address: 0x18
- faulting thread: "Symbian OS thread"

Fault stack:

gdi_store_command_segment::~gdi_store_command_segment()
 -> redraw_msg_canvas::~redraw_msg_canvas()
 -> window_server_client::~window_server_client()
 -> window_server::disconnect()
 -> service::server::process_accepted_msg()
 -> service::session::destroy()
 -> kernel_system::wipeout()
 -> system_impl::~system_impl()
 -> ios::os_thread()

The emulator logs immediately before the crash show wipeout teardown and
WSERV_MESSAGEWIN_EXIT guards firing. This is a host redraw-store/FBS reference
lifetime problem during global teardown, not a guest Nokia panic.

B58's added state probe is in svc.cpp and does not touch gstore/window teardown,
so the stack does not support attributing this crash to the B58 state marker.

## Decision

B59 GSTOREEXITGUARD1 is selected to fix only the teardown crash while preserving
all B58 boot/state diagnostics unchanged.

After B59 is device-validated for clean exit, continue the boot blocker with a
separate state-writer diagnostic covering both category/key and handle-based
integer P&S writes to 0x100058F4:1.
