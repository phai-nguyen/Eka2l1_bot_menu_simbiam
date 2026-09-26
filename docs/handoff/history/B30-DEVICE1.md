# B30 DEVICE1 — ROOTEDLIBPATH1 device validation and scheduler crash localization

Date: 2026-09-22
Device: iPhone 12 Pro Max, iOS 18.7
Firmware: Nokia 5800 RM-356
Tested code commit: 58a6178a53f9ddd8f4edbb5b3788d25131b9d4f9
Immutable branch: nativeboot2-b30-rootedlibpath1
Tested IPA SHA-256: e93aeedfae3d9d7d033e7c1e15374bac74ba584ed5becd264a0a05dc3cd41e67
Status: B30 ROOTEDLIBPATH1 DEVICE-VALIDATED; NEW HOST SCHEDULER CRASH EXPOSED

## User-visible result

The Nokia splash is reached and remains visible for a period. The app then exits to the iOS Home Screen without the user selecting Exit Emulator.

The supplied screen recording confirms the NOKIA splash immediately before the crash and the iOS Home Screen immediately afterward.

## B30 target result

B30 succeeds at the exact B29-LOADERDIAG1 causal boundary.

Observed sequence:

- 08:47:17.772
  `[NBOOT2][LDR_LIB_REQUEST] process=eiksrvs[10003a4a]0001 request_path=\\sys\\bin\\EiksrvUi.dll rooted_no_drive=1 owner=1`
- 08:47:17.772
  `[NBOOT2][LDR_ROOT_BEGIN] request=\\sys\\bin\\EiksrvUi.dll rooted=1 has_drive=0`
- 08:47:17.772
  `[NBOOT2][LDR_ROOT_CANDIDATE] ... candidate=Z:\\sys\\bin\\EiksrvUi.dll exists=1`
- 08:47:17.773
  `[NBOOT2][LDR_FORMAT] path=Z:\\sys\\bin\\EiksrvUi.dll is_e32=0 is_rom=1 in_rom=1 format=ROM`
- 08:47:17.773
  `[NBOOT2][LDR_ROOT_RESOLVED] ... candidate=Z:\\sys\\bin\\EiksrvUi.dll success=1`
- 08:47:17.773
  `[NBOOT2][LDR_LIB_RESULT] ... success=1 handle=0x4019000E completion=0`

The old B29 causal sequence:

`LDR_ROOT_DIRECT exists=0 -> LDR_ROOT_MISS -> LDR_LIB_RESULT success=0`

does not occur for this request.

Conclusion: B30 removes the rooted-no-drive EiksrvUi load blocker.

## Progress after B30

After EiksrvUi loads, startup continues for roughly 30 seconds through substantially more UI/application work.

Notable late events:

- multiple AknIconSrv `Leave -5` events are trapped and do not immediately terminate the host;
- 08:47:47.542: thread `akncapserver` is forcefully killed with category `Domino`, exit code `-33`;
- 08:47:47.549: a new missing executive appears:
  `V5 SVCMISS: svc=0xE3 pc=0x8029835C lr=0x802A130B r0=0x00000001 r1=0x10208904 ...`;
- startup then summons `ailaunch.exe`, `startup.exe`, `sysap.exe`, `phoneui.exe`, `clknitzmdls.exe`, and `profilesettingsmonitor.exe`;
- logging stops abruptly at 08:47:47.646.

SVC 0x2D is also still observed earlier in this run, but is not selected as the current host-crash target.

## iOS crash report

Crash report timestamp:
2026-09-22 08:47:48 +0700

Exception:
- EXC_BAD_ACCESS
- SIGSEGV
- KERN_INVALID_ADDRESS at 0x0000000000000000
- Data Abort, byte-read translation fault

Faulting thread:
`Symbian OS thread`

Top frames:
1. `eka2l1::kernel::thread_scheduler::switch_context(kernel::thread*, kernel::thread*) + 232`
2. `eka2l1::kernel_system::reschedule() + 460`
3. `eka2l1::system_impl::loop() + 576`
4. `eka2l1::ios::os_thread(...) + 224`

This is not the B26 UIKit/Exit Emulator crash class.

## Upstream correlation

Upstream EKA2L1 commit:

`437b29006bd8a0186f4070c9445f43e98e5c7435`

contains an exact scheduler fix for this failure class. Its commit message states that:

- a ready thread can outlive its process memory model during teardown;
- the scheduler could pass such a stale thread to `switch_context`.

The pre-fix scheduler directly calls:

`switch_context(crr_thread, next_thread);`

The upstream fix inserts a narrow validation loop before that call:

- read `next_thread->owning_process()`;
- accept only a thread whose owner exists and `owner->get_mem_model()` is non-null;
- dequeue stale ready entries;
- retry `next_ready_thread()`;
- then call `switch_context`.

The B30 device crash matches this upstream failure signature:
- guest/process teardown immediately precedes the crash;
- fault is native, inside `switch_context`;
- null address is accessed;
- the current B28-derived scheduler lacks the upstream stale-ready-thread guard.

## New missing SVC 0xE3

The same upstream commit also identifies `Exec::GetModuleNameFromAddress` and maps it at 0xE3 for the relevant table. It returns the module containing a guest address and is used by callers including `TExtendedLocale::GetLocaleDllName`.

B30 observes SVCMISS 0xE3 after the AknCapServer Domino -33 event.

Important: do not batch this executive fix with the scheduler crash fix. The host crash is the first blocking failure for the next device run and has a direct native stack plus an exact upstream counterpart. Preserve 0xE3 as a separate observed compatibility gap for the trace after the host crash is removed.

## Preferred next direction

B31 candidate: `SCHEDREADYMM1`.

Scope:
- only `thread_scheduler::reschedule()`;
- backport only the stale-ready-thread / missing-process-memory-model filter from upstream 437b290;
- preserve all B20-B30 behavior and diagnostics;
- add a generic diagnostic marker when a stale ready entry is dropped;
- do not import the upstream object-lifetime batch, timer changes, IPC lifetime changes, SVC 0xE3, ROM/E32 classification, relocation, or other executive-table changes.

Device success criterion:
- the app must no longer terminate in `thread_scheduler::switch_context` after AknCapServer teardown;
- the next log should establish whether SVC 0xE3 or another later guest boundary is the next causal blocker.

