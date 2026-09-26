#!/usr/bin/env python3
"""Add an explicit, transient COMPATBOOT Menu Probe entry beside Native Boot."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-COMPATBOOT1-MENUPROBE1"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_state_header(source):
    marker = "bool compat_menu_probe_mode = false;"
    if marker in source:
        return source
    anchor = "        bool native_phone_mode = false;\n"
    return replace_once(
        source,
        anchor,
        anchor + "        // COMPATBOOT is opt-in and transient; Native Boot stays the default.\n"
        "        bool compat_menu_probe_mode = false;\n",
        "transient CompatBoot state",
    )


def patch_emulator_choice(source):
    if "CompatBoot Menu Probe" in source and "start_compat_menu_probe()" in source:
        return source
    start = "- (void)onEmulator {"
    end = "- (void)onShowApps { [self showAppsScreen]; }"
    begin = source.find(start)
    stop = source.find(end, begin)
    if begin < 0 or stop < 0 or source.find(start, begin + len(start)) >= 0:
        fail("could not find the single EMUHUB1 Emulator action")
    replacement = r'''- (void)onEmulator {
    if (!eka2l1::ios::bridge::has_device()) {
        [self showAlert:EKAL(@"Emulator unavailable")
                 message:EKAL(@"Install a Symbian device before starting Emulator.")];
        return;
    }
    if (self.phoneRunning) { return; }
    UIAlertController *choice = [UIAlertController
        alertControllerWithTitle:EKAL(@"Emulator")
        message:EKAL(@"Choose startup mode")
        preferredStyle:UIAlertControllerStyleActionSheet];
    [choice addAction:[UIAlertAction actionWithTitle:EKAL(@"Native Boot")
        style:UIAlertActionStyleDefault handler:^(UIAlertAction *) {
            [self startEmulatorWithCompatProbe:NO];
        }]];
    [choice addAction:[UIAlertAction actionWithTitle:EKAL(@"CompatBoot Menu Probe")
        style:UIAlertActionStyleDefault handler:^(UIAlertAction *) {
            [self startEmulatorWithCompatProbe:YES];
        }]];
    [choice addAction:[UIAlertAction actionWithTitle:EKAL(@"Cancel")
        style:UIAlertActionStyleCancel handler:nil]];
    if (choice.popoverPresentationController) {
        choice.popoverPresentationController.sourceView = self.view;
        choice.popoverPresentationController.sourceRect =
            CGRectMake(CGRectGetMidX(self.view.bounds), CGRectGetMidY(self.view.bounds), 1, 1);
    }
    [self presentViewController:choice animated:YES completion:nil];
}

- (void)startEmulatorWithCompatProbe:(BOOL)compatProbe {
    if (!eka2l1::ios::bridge::has_device()) { return; }
    [self beginProgress:EKAL(@"Starting Emulator…")];
    [self climbProgressToward:0.92f];
    self.emuView.userInteractionEnabled = NO;
    self.controlsView.userInteractionEnabled = NO;
    self.inputManager.enabled = NO;
    dispatch_async(EKANgageLifecycleQueue(), ^{
        const bool ok = compatProbe
            ? eka2l1::ios::bridge::start_compat_menu_probe()
            : eka2l1::ios::bridge::start_native_phone();
        dispatch_async(dispatch_get_main_queue(), ^{
            [self endProgress];
            self.emuView.userInteractionEnabled = YES;
            self.controlsView.userInteractionEnabled = YES;
            if (!ok) {
                self.phoneRunning = NO;
                [self showAppsScreen];
                [self showAlert:EKAL(@"Emulator failed")
                    message:EKAL(@"CompatBoot start failed; normal EKA2L1 mode was restored.")];
                return;
            }
            self.phoneRunning = YES;
            self.gameRunning = YES;
            self.currentGameUid = 0;
            self.currentGameHideIsland = NO;
            self.currentGameShowStatus = NO;
            self.currentGameAutoScaleP = NO;
            self.currentGameAutoScaleL = NO;
            self.keyLayout = 0;
            self.controlsView.layout = 0;
            self.controlsView.hidden = YES;
            self.statusLabel.hidden = YES;
            [self updateChrome];
        });
    });
}

'''
    return source[:begin] + replacement + source[stop:]


def patch_bridge_header(source):
    if "start_compat_menu_probe" in source:
        return source
    anchor = "    bool start_native_phone();\n"
    return replace_once(
        source, anchor,
        anchor + "    bool start_compat_menu_probe();\n",
        "CompatBoot bridge declaration",
    )


def patch_bridge_cpp(source):
    if "[COMPATBOOT][MODE]" in source:
        return source
    source = replace_once(
        source,
        "        bool g_native_phone_mode = false;\n",
        "        bool g_native_phone_mode = false;\n"
        "        bool g_compat_menu_probe_mode = false;\n",
        "CompatBoot bridge selector",
    )
    source = replace_once(
        source,
        "            g_state->native_phone_mode = g_native_phone_mode;\n",
        "            g_state->native_phone_mode = g_native_phone_mode;\n"
        "            g_state->compat_menu_probe_mode = g_compat_menu_probe_mode;\n",
        "pass CompatBoot selector into emulator state",
    )
    source = replace_once(
        source,
        "        g_native_phone_mode = true;\n",
        "        g_native_phone_mode = true;\n"
        "        g_compat_menu_probe_mode = false;\n",
        "Native Boot remains separate",
    )
    stop = "    void stop_native_phone() {\n"
    compat_api = r'''    bool start_compat_menu_probe() {
        std::lock_guard<std::mutex> guard(g_mutex);
        if (!g_running || !g_state || !g_has_device) {
            LOG_ERROR(FRONTEND_CMDLINE,
                "[COMPATBOOT][BRIDGE_ENTER_FAIL] reason=no_active_device");
            return false;
        }
        LOG_WARN(FRONTEND_CMDLINE, "[COMPATBOOT][MODE] explicit=1");
        g_native_phone_mode = true;
        g_compat_menu_probe_mode = true;
        shutdown_locked();
        const bool has_device = start_locked();
        const bool handoff_ok = has_device && g_state && g_state->native_boot_handoff_ok;
        if (!handoff_ok) {
            LOG_ERROR(FRONTEND_CMDLINE,
                "[COMPATBOOT][ROLLBACK] EStart handoff failed; restoring normal mode");
            g_native_phone_mode = false;
            g_compat_menu_probe_mode = false;
            shutdown_locked();
            start_locked();
            return false;
        }
        return true;
    }

'''
    source = replace_once(source, stop, compat_api + stop,
                          "CompatBoot start API")
    lines = source.splitlines(keepends=True)
    cleared = []
    for index, line in enumerate(lines):
        cleared.append(line)
        if line == "        g_native_phone_mode = false;\n":
            following = lines[index + 1] if index + 1 < len(lines) else ""
            if "g_compat_menu_probe_mode = false;" not in following:
                cleared.append("        g_compat_menu_probe_mode = false;\n")
    return "".join(cleared)


def patch_localization(source):
    marker = '@"CompatBoot Menu Probe" : @"CompatBoot Menu Probe"'
    if marker in source:
        return source
    anchor = '            @"Add Mode" : @"Thêm chế độ",\n'
    localized = anchor + '''            @"CompatBoot Menu Probe" : @"CompatBoot Menu Probe",
            @"Native Boot" : @"Native Boot",
            @"Choose startup mode" : @"Chọn chế độ khởi động",
            @"CompatBoot start failed; normal EKA2L1 mode was restored." : @"CompatBoot không khởi động được; EKA2L1 đã trở về chế độ bình thường.",
'''
    return replace_once(source, anchor, localized, "CompatBoot localization")


def patch_config_header(source):
    if "compat_menu_probe_deadline_ms" in source:
        return source
    anchor = "        bool native_phone_boot{ false };\n"
    fields = anchor + '''        // COMPATBOOT1 state is transient and is not part of serialized user config.
        bool compat_menu_probe_mode{ false };
        std::atomic<bool> compat_menu_probe_launched{ false };
        std::atomic<bool> compat_menu_probe_timed_out{ false };
        std::atomic<bool> compat_menu_probe_finished{ false };
        std::uint64_t compat_menu_probe_deadline_ms{ 0 };
        std::uint32_t compat_target_uid3{ 0 };
        int compat_menu_probe_timeout_event{ -1 };
        std::atomic<bool> compat_timeout_event_registered{ false };
        std::atomic<bool> compat_seen_file_server{ false };
        std::atomic<bool> compat_seen_fbs{ false };
        std::atomic<bool> compat_seen_window_server{ false };
        std::atomic<bool> compat_seen_cenrep{ false };
        std::atomic<bool> compat_seen_apparc{ false };
        std::atomic<bool> compat_seen_akncap{ false };
'''
    return replace_once(source, anchor, fields, "COMPATBOOT transient fields")


def patch_state_cpp(source):
    if "[COMPATBOOT][DEADLINE_START]" in source:
        return source
    if "#include <chrono>" not in source:
        source = replace_once(source, "#include <kernel/process.h>\n",
                              "#include <kernel/process.h>\n#include <chrono>\n",
                              "state monotonic clock include")
    reset = '''        conf.compat_menu_probe_mode = compat_menu_probe_mode;
        conf.compat_menu_probe_launched = false;
        conf.compat_menu_probe_timed_out = false;
        conf.compat_menu_probe_finished = false;
        conf.compat_menu_probe_deadline_ms = 0;
        conf.compat_target_uid3 = 0;
        conf.compat_menu_probe_timeout_event = -1;
        conf.compat_timeout_event_registered = false;
        conf.compat_seen_file_server = false;
        conf.compat_seen_fbs = false;
        conf.compat_seen_window_server = false;
        conf.compat_seen_cenrep = false;
        conf.compat_seen_apparc = false;
        conf.compat_seen_akncap = false;
'''
    source = replace_once(source,
        "        conf.native_phone_boot = native_phone_mode;\n",
        "        conf.native_phone_boot = native_phone_mode;\n" + reset,
        "reset CompatBoot runtime state")
    anchor = "                            native_boot_handoff_ok = true;\n"
    deadline = anchor + '''                            if (compat_menu_probe_mode) {
                                const auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                    std::chrono::steady_clock::now().time_since_epoch()).count();
                                conf.compat_menu_probe_deadline_ms =
                                    static_cast<std::uint64_t>(now_ms) + 60000;
                                LOG_WARN(FRONTEND_CMDLINE,
                                    "[COMPATBOOT][DEADLINE_START] after=EStart_run timeout_ms=60000");
                                LOG_WARN(FRONTEND_CMDLINE,
                                    "[COMPATBOOT][BARRIER_WAIT] services=6");
                            }
'''
    return replace_once(source, anchor, deadline, "start deadline after EStart")


def patch_svc(source):
    if "[COMPATBOOT][TARGET_LAUNCH]" in source:
        return source
    includes = ("#include <services/fs/fs.h>\n#include <services/fbs/fbs.h>\n"
                "#include <services/window/window.h>\n#include <services/centralrepo/centralrepo.h>\n"
                "#include <services/applist/applist.h>\n#include <services/ui/cap/oom_app.h>\n"
                "#include <chrono>\n#include <sstream>\n")
    source = replace_once(source, "#include <kernel/kernel.h>\n",
                          "#include <kernel/kernel.h>\n" + includes,
                          "COMPATBOOT service interfaces")
    helper = r'''namespace eka2l1::kernel::svc {ӽm�G����ƭy�/fastbuild1_manifest.txt`; run the tests and `python3 ci/fastbuild1_manifest.py validate .` to confirm the pair is registered.**
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
