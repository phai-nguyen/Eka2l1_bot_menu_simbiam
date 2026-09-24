# NATIVEBOOT2 B60 STARTUPSTATEWRITER1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS; NO NEW VISUAL BOOT CHECKPOINT; EXIT CRASH REPRODUCED

## Inputs

- ScreenRecording_09-24-2026 19-57-55_1.mp4
- EKA2L1(20260924-132415).log
- EKA2L1_Persistent(20260924-132413).log
- EKA2L1_TakeThis(20260924-132412).log
- eka2l1-2026-09-24-200303.ips

## Visual result

The ~319.1 s recording follows the same boot path as B58/B59:

loading -> black -> NOKIA on white -> stable blank-white Startup surface.

The Nokia splash remains until the natural handoff at ~20:00:53.845.
After the handoff, no Nokia hands/welcome animation, RTC UI or S60 Idle appears.

At ~20:03:02 the user opens the Emulator menu and selects "Thoát Emulator".
At ~20:03:03 the app exits to the iOS Home screen because of a host crash.

Thus B60 does not add a new visible Nokia boot checkpoint.

## Startup state writer result

B58 category/key marker remains:

0x100058F4:1
before=0 requested=1 after=1 set_result=1

B60 adds handle-based integer writer coverage for the same property.

Result: zero [NBOOT2][STARTUP_STATE_HANDLE] events for 0x100058F4:1.

Therefore the current evidence closes the ambiguity left by B58/B59:

- category/key integer path writes Wait=1;
- handle-based integer path never writes the target property;
- no observed integer P&S writer publishes StartAnimations=2.

This is meaningful diagnostic progress even though the screen does not progress.
The next boot investigation should move upstream to SSM/Starter / command-list
execution responsible for publishing EStartupAppStateStartAnimations rather than
adding more graphics probes.

## Handoff/replay remains unchanged

At 20:00:53.845 Startup becomes focus and B55 replay runs on frame 172.
The compositor already contains Home screen and SysAp groups, but Startup remains
focus and its full-screen white redraw-store is physically visible.

Startup then requests TfxServer at 20:00:53.875-876 and receives KErrNotFound,
matching B58/B59.

## Exit crash

The final shutdown begins at 20:03:03.130 and reaches:

shutdown_begin
-> shutdown_threads_begin
-> flags_set
-> request_exit
-> core_wakeup
-> os_join_begin

It never reaches os_join_done.

During kernel wipeout, Startup WindowGroup destruction moves focus temporarily
to Home screen. This is teardown behavior, not boot progress.

The Apple .ips is definitive:

- EXC_BAD_ACCESS / SIGSEGV
- KERN_INVALID_ADDRESS at 0x18
- faulting thread: Symbian OS thread

Fault stack:

gdi_store_command_segment::~gdi_store_command_segment()
 -> redraw_msg_canvas::~redraw_msg_canvas()
 -> window_server_client::~window_server_client()
 -> window_server::disconnect()
 -> service::session::destroy()
 -> kernel_system::wipeout()
 -> system_impl::~system_impl()
 -> ios::os_thread()

This is the same teardown boundary as B58.

## B59 guard interpretation

No [NBOOT2][GSTORE_EXIT_GUARD] marker fires in B60.

B59 guarded only a narrow retained-FBS case:
- null/exhausted ref, or
- final ref with owner == nullptr.

B60 proves that this is not a complete teardown fix. The redraw-store still has
a lifetime hazard that can crash outside that narrow condition (for example a
stale retained FBS pointer or stale/non-null owner/container state). The exact
member access cannot be proven from the symbolized .ips alone.

B59's one clean device exit should now be treated as a timing-dependent pass,
not a fully resolved crash.

## Decision

Separate the next work into two boundaries:

1. Boot:
   trace the SSM/Starter command-list path which should publish
   KPSStartupAppState StartAnimations=2.

2. Exit stability:
   strengthen redraw-store/FBS lifetime handling specifically during
   kernel_system::wipeout; do not change normal redraw-store refcount behavior.

Do not interpret the temporary Home-screen focus during wipeout as Nokia boot
progress.
