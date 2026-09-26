# COMPATBOOT1-MENUPROBE1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in RM-356 compatibility boot mode that waits for UI services and launches the firmware's real Menu3 application to identify its first runtime dependency.

**Architecture:** Preserve the existing NATIVEBOOT2 EStart flow and default. Add a separate CompatBoot choice in the existing Emulator action, pass that transient mode through the iOS bridge, wait for the six UI substrate services, then launch `Z:\sys\bin\menu3.exe` once through EKA2L1's guest process loader. Reuse existing detailed NATIVEBOOT2 diagnostics where sufficient and add profile-scoped `[COMPATBOOT]` markers only for missing evidence.

**Tech Stack:** Existing EKA2L1 C++/Objective-C++ iOS frontend and kernel; Python 3 patcher/`unittest` contracts; GitHub Actions FASTBUILD on macOS 15; unsigned iOS IPA packaging.

**Spec:** `docs/superpowers/specs/2026-09-26-compatboot1-menuprobe1-design.md`

## Global Constraints

- NATIVEBOOT2 remains the default and fidelity/reference path.
- COMPATBOOT is selected explicitly for a run and must not silently alter Native Boot.
- Use real RM-356 firmware executables and resources; the target is `Z:\sys\bin\menu3.exe`.
- Wait for FileServer, FBS, WindowServer, CenRep, AppArc, and AknCapServer before launching Menu3.
- Do not preemptively fake broad P&S, CenRep, server, or UI state.
- Launch Menu3 at most once per COMPATBOOT run; report barrier timeout or first decisive dependency failure.
- Do not declare Menu success from state `109`, process spawn, or process liveness alone; P2 requires a visible real Menu surface.
- Preserve NOJAVA, MANIC3, and the FASTBUILD full regression chain.

## Review Focus

- Missing firmware image or no installed device: both Native and CompatBoot choices must fail safely without corrupting the normal app session; test the bridge guard and rollback.
- One required service absent or late: Menu3 must not launch early; test all six services individually and timeout reporting.
- Repeated readiness notifications: Menu3 must still launch once; test one-shot behavior.
- Menu3 loader failure or target panic: retain the first actionable failure and leave emulator exit usable; test error-marker paths and device exit.
- Native Boot selected/default: no host Menu3 launch or CompatBoot state may leak into the existing path; test native-mode isolation.

---

### Task 1: Add explicit CompatBoot mode selection

**Files:**
- Create: `apply_nativeboot2_compatboot1_menuprobe1.py`
- Create: `test_nativeboot2_compatboot1_menuprobe1.py`
- Modify upstream through the patcher: `src/emu/config/include/config/config.h`
- Modify upstream through the patcher: `src/emu/ios/include/ios/state.h`
- Modify upstream through the patcher: `src/emu/ios/src/state.cpp`
- Modify upstream through the patcher: `src/emu/ios/include/ios/emu_bridge.h`
- Modify upstream through the patcher: `src/emu/ios/src/emu_bridge.mm`
- Modify upstream through the patcher: `src/emu/ios/app/RootViewController.mm`
- Modify upstream through the patcher: `src/emu/ios/app/EKALocalization.mm`
- Modify: `ci/fastbuild1_manifest.txt`

**Interfaces:**
- Consumes: Existing `bridge::start_native_phone()`, `bridge::stop_native_phone()`, and the transient `native_phone_mode` rebuild path.
- Produces: `bridge::start_compat_menu_probe() -> bool`; a transient emulator/profile flag that survives the in-process rebuild but is not serialized. Existing running-state and stop/exit behavior is shared with the firmware Emulator session.

- [ ] **Step 1: Add failing contract tests** named `test_compat_mode_is_opt_in_and_does_not_change_native_default`, `test_emulator_choice_routes_to_native_or_compat_bridge`, and `test_compat_start_failure_restores_normal_frontend`. Assert the Native choice still calls the existing bridge API, CompatBoot calls only the new API, and both reject a missing device.
- [ ] **Step 2: Run the contract tests and verify they fail** because the B90 patcher and CompatBoot routing are absent.
- [ ] **Step 3: Implement the idempotent patcher and bridge/UI mode routing.** Make the current Emulator toolbar action present two choices: Native Boot and CompatBoot Menu Probe. Add localized labels. Keep `native_phone_boot` true for the firmware-driven profile; carry the CompatBoot selector as separate transient state and reuse the current emulator exit/rollback path.
- [ ] **Step 4: Add the patcher/test pair to `[post_bootstrap]` in `ci/fastbuild1_manifest.txt`; run the tests and `python3 ci/fastbuild1_manifest.py validate .` to confirm the pair is registered.**
- [ ] **Step 5: Commit** as `feat: add opt-in compatboot menu probe mode`.

### Task 2: Implement the UI barrier and one-shot Menu3 launch

**Files:**
- Modify: `apply_nativeboot2_compatboot1_menuprobe1.py`
- Modify: `test_nativeboot2_compatboot1_menuprobe1.py`
- Modify upstream through the patcher: `src/emu/ios/src/state.cpp`
- Modify upstream through the patcher: `src/emu/services/src/init.cpp`
- Modify upstream through the patcher: `src/emu/kernel/src/svc.cpp`
- Reuse upstream guest loader from `src/emu/kernel/src/process.cpp` / existing `kernel::system::spawn_new_process` call path; patch only the smallest confirmed integration point.

**Interfaces:**
- Consumes: `compat_menu_probe_mode` from Task 1 and the serialized emulator/guest startup execution context.
- Produces: a CompatBoot barrier state with required logical services `{FileServer, FBS, WindowServer, CenRep, AppArc, AknCapServer}`, a bounded wait (60 seconds maximum), and a one-shot launch result for `Z:\sys\bin\menu3.exe` through `kernel::system::spawn_new_process(path, args)` followed by the guest process `run()` call.

- [ ] **Step 1: Add failing tests** named `test_each_required_service_blocks_launch_until_ready`, `test_live_process_without_ready_server_does_not_release_barrier`, `test_barrier_timeout_reports_exact_missing_services`, and `test_menu3_launches_once_after_all_services_ready`. For each of the six services, assert that its absence blocks launch; assert process existence alone is insufficient when a server-ready signal is required; assert timeout never launches; assert duplicate readiness events still produce one launch and the exact firmware path.
- [ ] **Step 2: Run the tests and verify they fail** against the unimplemented barrier/launcher contract.
- [ ] **Step 3: Implement readiness checks using observable server registration/ready state and the EKA2L1 serialized execution path.** Map each logical service to its actual registered firmware/HLE identity from B28 runtime naming; do not use guessed aliases or treat process existence alone as readiness. Start the 60-second deadline after EStart runs, report every still-missing service at timeout, and stop polling on launch, exit, or timeout. If a required service has no reliable ready signal, fail closed and report that gap instead of launching Menu3.
- [ ] **Step 4: Launch the real firmware Menu3 once** after all six services are ready. On create/run failure, report the path and result and do not retry automatically. Keep this branch gated by `compat_menu_probe_mode`; prove Native Boot never enters it.
- [ ] **Step 5: Run the contract tests and commit** as `feat: launch firmware menu after compatboot barrier`.

### Task 3: Add first-blocker CompatTrace and build audit

**Files:**
- Modify: `apply_nativeboot2_compatboot1_menuprobe1.py`
- Modify: `test_nativeboot2_compatboot1_menuprobe1.py`
- Modify upstream through the patcher: `src/emu/config/include/config/config.h`, `src/emu/kernel/src/svc.cpp`, and `src/emu/services/src/window/classes/winuser.cpp`.
- Modify: `.github/workflows/build-ios-nativeboot2-current-fast.yml`

**Interfaces:**
- Consumes: CompatBoot mode, barrier result, and target process identity from Tasks 1–2; existing NATIVEBOOT2 loader, resource, CenRep/P&S, session, panic, and visibility diagnostics.
- Produces: profile-gated markers `[COMPATBOOT][MODE]`, `[COMPATBOOT][BARRIER_WAIT]`, `[COMPATBOOT][BARRIER_READY]`, `[COMPATBOOT][BARRIER_TIMEOUT]`, `[COMPATBOOT][TARGET_LAUNCH]`, `[COMPATBOOT][MISSING_SERVER]`, `[COMPATBOOT][FIRST_FAILURE]`, and `[COMPATBOOT][TARGET_VISIBLE]`.
- Reuse existing `[NBOOT2]` loader, resource, CenRep/P&S, IPC, and panic diagnostics for detailed failure data. The CompatBoot first-failure marker correlates those existing records to the selected profile and Menu3 UID3 rather than duplicating every diagnostic format.

- [ ] **Step 1: Add failing tests** named `test_compat_markers_are_profile_gated`, `test_first_target_failure_is_logged_without_semantic_override`, and `test_visible_marker_requires_menu3_window_surface`. Assert existing guest error/result semantics are unchanged and marker context contains target process/UID3 plus the relevant dependency and result.
- [ ] **Step 2: Run the tests and verify they fail** because CompatTrace markers are not yet emitted.
- [ ] **Step 3: Reuse existing NATIVEBOOT2 diagnostics where they already expose the failure.** Add CompatBoot-scoped marker forwarding only at missing diagnostic boundaries; do not change leave, IPC, loader, P&S, CenRep, or panic results. Emit `TARGET_VISIBLE` only after Menu3's own visible WindowGroup/canvas is confirmed.
- [ ] **Step 4: Extend FASTBUILD binary marker checks** for the required marker set and confirm the manifest regression executes the new contract test. Keep the existing B20–B89 regression chain and NOJAVA/MANIC3 checks intact.
- [ ] **Step 5: Run** `python3 -m unittest -v test_nativeboot2_compatboot1_menuprobe1.py`, `python3 ci/fastbuild1_manifest.py validate .`, and `git diff --check`; commit as `feat: trace compatboot menu dependencies`.

### Task 4: Build, verify, and record B90

**Files:**
- Modify: `docs/handoff/CURRENT.md`
- Create: `docs/handoff/history/B90-COMPATBOOT1-MENUPROBE1.md`
- Modify: `docs/handoff/NEWCHAT-B89-2026-09-26.md` to point to the B90 handoff.

- [ ] **Step 1: Run the full FASTBUILD workflow** on `nativeboot2-current`; require all manifest regressions, iOS compile/link, binary marker audit, unsigned IPA packaging, and IPA audit to pass.
- [ ] **Step 2: Check the artifact** exists, contains `Payload/EKA2L1.app/eka2l1`, passes `unzip -t`, and record the SHA-256 and workflow run ID.
- [ ] **Step 3: Record the B90 build and test protocol** in the handoff. Request a device run of CompatBoot Menu Probe and capture the log/video needed to classify P0–P5; do not call the Menu reached unless P2 is evidenced.
- [ ] **Step 4: Commit** the handoff update as `docs: record COMPATBOOT1 menu probe build`.

---

## Plan self-review

- **Spec coverage:** Separate opt-in profile and Native default are Task 1; six-service barrier and real one-shot Menu3 launch are Task 2; first-blocker diagnostics and P2 visibility are Task 3; build/device ladder and handoff are Task 4.
- **Ruling:** Detailed NATIVEBOOT2 traces already cover loader/DLL/ordinal, firmware resource, CenRep/P&S, IPC, and panic failure context when Native Phone mode is active. CompatBoot adds a profile-scoped first-failure envelope and Menu3-visible marker, avoiding duplicate diagnostic paths that could drift or alter error handling.
- **Step scan:** Each task has an explicit failing contract, implementation boundary, verification command, and commit; the timeout and one-shot inputs are tested.
- **Type consistency:** The bridge start API returns `bool`; existing running-state and stop/exit methods are reused. The guest launch uses the existing `spawn_new_process(path, args)` plus `run()` pattern. The launcher remains gated by the transient CompatBoot selector.
- **Review focus:** Missing device/firmware, delayed/missing service, duplicate readiness, target failure/panic, and Native Boot isolation each have a named test above.
- **Proportion:** Four tasks separate mode selection, boot/launch, diagnostics, and the final build/handoff; no speculative shim subsystem is included.
