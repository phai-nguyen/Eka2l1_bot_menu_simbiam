# B33 DEVICE1 — EIKCANCELORIGIN1 + EXIT WATCHDOG

Date: 2026-09-22
Status: DEVICE-OBSERVED; B33 CANCELLATION-ORIGIN PROBE ACHIEVED; NEW HOST EXIT DEADLOCK LOCALIZED
Device: iPhone 12 Pro Max, iOS 18.7
Firmware: Nokia 5800 RM-356

Build-tested B33 code commit:
`4db183b7a8f522f93057bfae22933f19c770156b`

B33 remains diagnostic-only. No immutable B33 functional milestone branch is created.

## Preserved functional baseline

B30 rooted EiksrvUi resolution remains present.

B31 stale-ready scheduler protection remains present and the old
`thread_scheduler::switch_context` native crash does not recur during normal
native-phone execution.

The repeated B32 guest boundary remains the same:
AknFep -> User::Leave(KErrCancel/-3) -> euser null write -> EikAppUiServerThread
KERN-EXEC 3.

## B33 cancellation-origin result

Main B33 log counts:
- `EIKCANCEL_LLE`: 2
- `EIKCANCEL_HLE`: 0
- `EIKCANCEL_NOTIFY`: 50
- exact `EIKFAULT_LEAVE`: 16
- `EIKFAULT_AV`: 12 in this captured session

The two LLE KErrCancel completions belong to AknIconSrv/CdlServer:
- client: `AknIconSrv[1020735b]0001 / AknIconPrecache2`
- server: `CdlServer`
- opcode: 3

They do not belong to the failing eiksrvs/EikAppUiServerThread path.

No `EIKCANCEL_HLE` marker appears.

There are 12 eiksrvs `EIKCANCEL_NOTIFY` markers, but their ordering is
post-fault cleanup rather than the origin of the preceding leave. First cycle:

`11:10:35.345 EIKFAULT_LEAVE leave=-3`
-> `11:10:35.346 EIKFAULT_AV write 0x10`
-> `11:10:35.348 EikAppUiServerThread KERN-EXEC 3`
-> `11:10:35.349 EIKCANCEL_NOTIFY result=-3 request_status=0x007039AC`.

The same ordering repeats.

Conclusion:
none of the three B33 completion probes identifies an immediate pre-Leave
KErrCancel delivery:
- HLE path: absent;
- LLE path: unrelated AknIcon/CdlServer traffic;
- notify path: eiksrvs cancellation occurs only after its KERN-EXEC 3
  termination.

Therefore do not modify these completion paths based on B33.

The origin of the AknFep `User::Leave(-3)` remains unresolved and should stay
separate from the host exit problem described below.

## Exit Emulator failure

The Exit Emulator button is accepted. The host enters the B26/B31 bridge
shutdown path, but stalls while joining the Symbian OS thread.

Main-log shutdown tail:

`11:11:59.743 [NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode`
`11:11:59.745 phase=exit_requested`
`11:11:59.745 phase=shutdown_begin`
`11:11:59.745 phase=shutdown_threads_begin`
`11:11:59.745 phase=flags_set`
`11:11:59.745 phase=request_exit`
`11:11:59.745 phase=core_wakeup`
`11:11:59.745 phase=os_join_begin`

There is no corresponding `os_join_done`, `shutdown_threads_done`,
`shutdown_done`, or `normal_restart_done` for this exit attempt.

The video matches the trace:
- Exit Emulator is selected;
- the menu closes;
- the NOKIA screen remains stuck;
- the user then manually swipes out to the iOS Home Screen.

Important correction:
the transition to the Home Screen was user-initiated. B33 did not spontaneously
crash or eject itself to the Home Screen.

## iOS watchdog report

Crash report timestamp:
`2026-09-22 11:12:22 +0700`

This is not a segmentation fault and it is not evidence that the Exit Emulator
action itself crashed to the Home Screen.

The report was produced after the user manually swiped the already-hung app to
the Home Screen. While transitioning the hung app to background, iOS observed
that its lifecycle work could not complete and later terminated the process.

Termination recorded in that secondary state:
- `EXC_CRASH`
- `SIGKILL`
- FRONTBOARD
- `0x8BADF00D`
- scene-update watchdog transgression
- 10-second wall-clock allowance exhausted

Main thread:
`std::mutex::lock`
-> `eka2l1::ios::bridge::pause()`
-> `UIApplication _applicationDidEnterBackground`.

Lifecycle queue:
`pthread_join`
-> `eka2l1::ios::shutdown_threads()+576`
-> `bridge::shutdown_locked()`
-> `bridge::stop_native_phone()`
-> Exit Emulator block.

Symbian OS thread:
`std::mutex::lock`
-> `screen::fire_focus_change_callbacks()+36`
-> `screen::update_focus()+532`
-> `window_group::~window_group()+104`
-> `window_server_client::~window_server_client()+148`
-> `window_server::disconnect()+252`
-> `service::server::process_accepted_msg()+840`
-> `service::session::destroy()+92`
-> `kernel_system::wipeout()+148`
-> `system_impl::~system_impl()+68`
-> `system::~system()+32`
-> `ios::os_thread()+292`.

This localizes the shutdown hang to window-server teardown attempting to lock
`screen::focus_callback_mutex` while the lifecycle worker waits to join the
OS thread.

The available crash report does not identify which execution path currently
owns that mutex. Do not convert this localization into a speculative mutex
behavior change yet.

## B33 did not directly modify exit/window code

The B32 -> B33 production instrumentation is limited to:
- kernel `svc.cpp`;
- services `context.cpp`;
- kernel `thread.cpp`.

B33 does not directly patch:
- iOS bridge shutdown;
- iOS thread joining;
- window server;
- screen focus callbacks;
- window-group teardown.

Therefore the device evidence supports the wording:
B33 exposed a timing-sensitive host shutdown deadlock/race.

It does not establish that the B33 diagnostics created the underlying locking
bug.

## Upstream correlation

Upstream EKA2L1 commit
`2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d`
previously fixed a related window-teardown deadlock by separating
focus/redraw/mode callback registries from `screen_mutex`.

The current source still holds `focus_callback_mutex` while executing focus
callbacks:

`screen::fire_focus_change_callbacks()`
locks `focus_callback_mutex` and invokes every registered callback before the
lock guard is released.

The current iOS device crash proves the OS thread blocks at acquisition of this
separate focus callback mutex during global teardown.

This is related evidence, not yet a proof of the exact owner/reentrancy
mechanism in the B33 run.

## Next direction

Preferred next build:

`B34 FOCUSLOCKDIAG1`

Diagnostics only.

Goal:
identify the last successful owner/dispatch sequence for
`focus_callback_mutex` before the Exit Emulator OS-thread stall.

Minimum instrumentation:
- focus callback fire: wait, acquired, each callback begin/end, released;
- focus callback add/remove: wait/acquired/released;
- window-group destructor/update-focus entry around the teardown path;
- generic host-thread identity/sequence number where feasible;
- preserve all existing callback behavior and locking.

B34 device success criterion is diagnostic, not behavioral:
when Exit Emulator stalls, the trace must reveal the unmatched focus-lock
acquire/callback sequence that owns or recursively requests the mutex.

Only after that evidence should a host exit locking fix be selected.

Do not combine this with the unresolved guest AknFep Leave(-3) investigation.

## Preserved invariants

Keep:
- B20-B31 functional behavior;
- B32/B33 diagnostics;
- B26 exit choreography;
- firmware SYSSTART ownership;
- native fbserv;
- NOJAVA;
- MANIC3.
