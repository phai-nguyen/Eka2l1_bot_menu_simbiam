# NATIVEBOOT2 B41 — WSERVMESSAGEWINEXIT1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Device evidence from B40

B40 successfully passed the Loader PDD startup boundary:

- `[NBOOT2][LOADER_PDD] phase=enter name=EUART1`
- `[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0`

When the user selected **Thoát Emulator**, the host iOS application then
crashed instead of completing the existing B34 shutdown choreography.

The iOS crash report identifies a native host crash, not a guest Symbian panic:

- exception: `EXC_BAD_ACCESS / SIGSEGV`
- invalid address: `0x168`
- faulting thread: `Symbian OS thread`
- exit log stopped at:
  `[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin`

Fault stack:

```
screen::need_update_visible_regions(bool)
 <- canvas_base::set_visible(bool)
 <- messagewin_anim_executor::~messagewin_anim_executor()
 <- anim_dll::~anim_dll()
 <- window_server_client::~window_server_client()
 <- window_server::disconnect(...)
 <- service::session::destroy()
 <- kernel_system::wipeout()
 <- system_impl::~system_impl()
 <- system::~system()
 <- ios::os_thread(...)
```

At the fault, the screen method receives a null `this`, consistent with
`messagewin_anim_executor` dereferencing its borrowed `canvas_` during
WindowServer object teardown after that canvas has become invalid/in teardown.

## Root cause

At the pinned upstream baseline, MessageWin stores a raw `canvas_base *` in
`anim_executor`. Its destructor unconditionally executes:

```cpp
canvas_->set_visible(true);
```

During `kernel_system::wipeout()`, WindowServer destroys its client object
table. MessageWin destruction can therefore occur after the borrowed canvas
has entered teardown. Restoring its visibility is unnecessary during full
emulator shutdown and can dereference invalid canvas/screen state.

Current upstream research did not identify a dedicated MessageWin destructor
fix. Upstream commit
`2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d` contains broader WindowServer
lifetime/locking work, but importing that batch would change many unrelated
behaviors and is deliberately outside B41 scope.

## B41 functional change

B41 modifies only:

- `src/emu/services/include/services/window/classes/plugins/anim/clock/messagewin.h`
- `src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp`

The executor captures a stable `kernel_system *kern_` while its canvas is
known live. In the destructor it checks that stable kernel pointer before
touching the borrowed canvas:

```cpp
if (kern_ && kern_->wipeout_in_progress()) {
    LOG_WARN(SERVICE_WINDOW,
        "[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout");
    return;
}

canvas_->set_visible(true);
```

Normal MessageWin destruction outside kernel wipeout preserves the original
visibility restore.

## Preserved scope

B41 does not change:

- generic `canvas_base::set_visible()`;
- WindowServer command dispatch/completion;
- animation behavior during normal guest operation;
- B40 Loader PDD behavior;
- FEP / Leave / TRAP semantics;
- scheduler semantics;
- rooted library resolution;
- EPOC94 SVC mappings;
- B34 iOS shutdown choreography;
- NOJAVA / MANIC3.

## TDD

Canonical RED:

- commit: `92dc4230524d52bb1ca6c42fa0c5077e460870c6`
- run: `35793893027`
- job: `106968553796`
- expected failure:
  `NATIVEBOOT2-B41-WSERVMESSAGEWINEXIT1-TEST: FAIL: missing in B41 runtime marker: [NBOOT2][WSERV_MESSAGEWIN_EXIT]`
- B29-B40 apply/tests before B41: PASS
- B20-B28 regressions: PASS

GREEN implementation:

- implementation commit: `cfe2fd70f8630f718aab7780062000980273f5b5`
- final validated HEAD: `b43e59696d313da97c8845a1a20e78d9b6c762d7`
- run: `35794136142`
- job: `106969339936`
- manifest validation: PASS
- B29-B41 apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compilation failures: 0
- NOJAVA / MANIC3: PRESERVED

A manifest-edit typo was detected and corrected before the final GREEN run;
only run `35794136142` is the canonical B41 GREEN.

## Build audit

- compile requests: 149
- cache hits: 147
- cache misses: 2
- cache hit rate: 98.66%
- actual compilations: 2
- compilation failures: 0

## Artifacts

Unsigned IPA SHA-256:

`0f6e4694af7cee6897fe0ebbe6b5e98c3374fa1cdb4f8118305b5b93cc7d172d`

IPA artifact:

- ID: `10723611386`
- ZIP digest:
  `sha256:d4069d008d0e8d615c8353c1b3236d2ea8aaa815f9d1db1836cafd103a1d2d15`
- ZIP size: 19,891,120 bytes
- expires: 2026-10-06

Audit artifact:

- ID: `10723341826`
- digest:
  `sha256:072c190faef76104c0469f08ab5df80a692e818506e4303dbc1a060e5c0f069b`
- expires: 2026-10-06

## Device-test acceptance

Install/sign B41 and reproduce the same Nokia 5800 startup/exit path.

When selecting **Thoát Emulator**, acceptance requires:

1. `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout` appears if
   MessageWin is still alive during wipeout.
2. `[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_done` is reached.
3. shutdown proceeds through graphics join, shutdown_threads_done and
   state_reset_done.
4. no iOS `EXC_BAD_ACCESS` crash report is produced.
5. B40 `LOADER_PDD EUART1 result=0` remains intact on startup.

Do not promote B41 to a device-validated milestone until this exit path is
confirmed on the device.
