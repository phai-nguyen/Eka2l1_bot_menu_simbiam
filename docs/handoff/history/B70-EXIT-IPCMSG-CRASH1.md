# B70 EXIT-EMULATOR HOST CRASH TRACK

Date: 2026-09-25
Status: CONFIRMED ON B70; REPRO CHECK PLANNED ON B71; DO NOT MERGE WITH PHONEUI CONE14

## User symptom

After the B70 Phone start-up failed screen, choosing the Emulator exit/menu
causes the whole iOS app to crash back to the iPhone Home screen.

## iOS crash report

File:
eka2l1-2026-09-25-140906.ips

Crash time:
2026-09-25 14:09:05 +0700

Exception:
- EXC_BAD_ACCESS
- SIGSEGV
- KERN_INVALID_ADDRESS
- fault address: 0x0000000100000041

Faulting thread:
- thread name: Symbian OS thread
- PC symbol: eka2l1::ipc_msg::~ipc_msg() + 104

Native host stack:
1. eka2l1::ipc_msg::~ipc_msg()
2. eka2l1::kernel_system::wipeout()
3. eka2l1::system_impl::~system_impl()
4. eka2l1::system::~system()
5. eka2l1::ios::os_thread(...)
6. eka2l1::ios::large_stack_trampoline(...)

At the same time the iOS lifecycle queue is in:
- eka2l1::ios::shutdown_threads(...)
- shutdown_locked()
- stop_native_phone()
- RootViewController exitEmulator

This proves the exit failure is a host teardown crash, not the guest Telephone
CONE14 startup failure.

## Log correlation

Immediately before the host crash:
- B61 GSTORE_WIPEOUT_GUARD fires repeatedly;
- WSERV_MESSAGEWIN_EXIT wipeout guards fire;
- multiple WindowServer groups are destroyed.

The process does not reach the previously expected clean shutdown completion
because it crashes in ipc_msg destruction during kernel wipeout.

Therefore B61 continues protecting the old graphics/FBS wipeout class, but it
does not cover this newer IPC-message teardown lifetime bug.

## Upstream correlation

Current EKA2L1 upstream contains an explicit IPC/teardown lifetime fix in:

437b29006bd8a0186f4070c9445f43e98e5c7435
"kernel: object lifetimes, timers, image loading and the executive tables"
2026-08-21

Its teardown section specifically documents:
- IPC messages being destroyed after sessions/servers are gone;
- leaked nonzero message references running unref side effects against freed
  sessions/owners;
- teardown/completion crashes from stale objects.

Current upstream kernel_system::wipeout() neutralizes each remaining message
before reset:
- own_thr = nullptr
- msg_session = nullptr
- ref_count = 0
- then msgs_[i].reset()

Current upstream ipc_msg::unref() also includes lifetime guards and stale queue
cleanup.

This is a strong candidate source for a narrow B72 backport if B71 reproduces
the exit crash.

## Plan

Do NOT alter B71. B71 remains dedicated to PhoneUI CONE14 diagnostics.

During B71 DEVICE1:
1. run until Phone start-up failed or later visible progress;
2. wait 5-10 seconds;
3. use the same Emulator exit/menu path;
4. report whether the iOS app returns cleanly to the EKA2L1 menu or crashes to
   the iPhone Home screen.

If B71 reproduces the host crash, B72 should address the IPC teardown lifetime
path using the proven .ips stack and upstream 437b2900 evidence, while
preserving B71 PhoneUI diagnostics.

If B71 exits cleanly, keep this as a B70-only teardown observation and do not
introduce an unnecessary B72 teardown patch.
