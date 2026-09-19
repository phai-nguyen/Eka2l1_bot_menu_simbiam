#!/usr/bin/env python3
"""NATIVEBOOT2 EMUHUB1.

Start from the stable MENUUI36/NOJAVA/MANIC3 iOS baseline.

Architecture:
- normal EKA2L1 mode is the default and remains the device-install/home UI,
- replace the top-level Apps toolbar action with Emulator,
- entering Emulator performs a transient reboot with native_phone_boot enabled,
- native mode keeps critical hardware/graphics HLE services but releases guest UI server names,
- Z: is mounted before launching the *only* host handoff: Z:\\sys\\bin\\EStart.exe,
- no host-side SysStart/Menu3/component launch plan,
- if the EStart handoff fails, automatically roll back to normal EKA2L1 mode,
- firmware install completion no longer waits up to 45 seconds for an app list.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-EMUHUB1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_config(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "bool native_phone_boot" in text:
        text = text.replace("bool native_phone_boot{ true };", "bool native_phone_boot{ false };")
        path.write_text(text, encoding="utf-8")
        return
    anchor = "        bool enable_srv_drm{ true };\n"
    insert = anchor + """
        // NATIVEBOOT2 EMUHUB1: transient runtime mode, deliberately not serialized.
        // The iOS Emulator toolbar action sets this before rebuilding the guest.
        bool native_phone_boot{ false };
"""
    text = replace_once(text, anchor, insert, "config native_phone_boot")
    path.write_text(text, encoding="utf-8")

def wrap_server_once(text: str, server: str, reason: str) -> str:
    anchor = f"            CREATE_SERVER(sys, {server});"
    if anchor not in text:
        fail(f"init services: missing {server} anchor")
    replacement = (
        f"            if (!native_phone_boot) {{\n"
        f"                // NATIVEBOOT2 EMUHUB1: {reason}\n"
        f"                CREATE_SERVER(sys, {server});\n"
        f"            }}"
    )
    return replace_once(text, anchor, replacement, f"wrap {server}")

def patch_services(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][HLE_POLICY]" in text:
        return
    if "#include <common/log.h>" not in text:
        text = replace_once(
            text, "#include <common/algorithm.h>\n",
            "#include <common/algorithm.h>\n#include <common/log.h>\n",
            "init common/log include")
    cfg_anchor = "            config::state *cfg = sys->get_config();\n"
    policy = cfg_anchor + """
            const bool native_phone_boot = cfg->native_phone_boot;
            if (native_phone_boot) {
                LOG_WARN(SYSTEM,
                    "[NBOOT2][HLE_POLICY] mode=native fs=HLE loader=HLE fbs=HLE wserv=HLE "
                    "hwrm=HLE etel=HLE applist=NATIVE akncap=NATIVE view=NATIVE "
                    "notifier=NATIVE keysound=NATIVE eikappui=NATIVE sysagt=NATIVE domain=NATIVE_FIRST");
            }
"""
    text = replace_once(text, cfg_anchor, policy, "native boot policy")
    text = wrap_server_once(text, "applist_server", "ROM APSEXE/AppArc owns AppList")
    text = wrap_server_once(text, "oom_ui_app_server", "ROM AknCapServer owns the UI capability server")
    text = wrap_server_once(text, "view_server", "ROM EikSrv owns ViewServer")
    text = wrap_server_once(text, "notifier_server", "ROM EikSrv owns !Notifier")
    text = wrap_server_once(text, "keysound_server", "ROM EikSrv owns KeySoundServer")
    text = wrap_server_once(text, "eikappui_server", "ROM EikSrv/EikAppUI owns this service")
    text = wrap_server_once(text, "system_agent_server", "ROM sysagt2svr.exe owns SystemAgent")
    comm_anchor = "            CREATE_SERVER(sys, comm_server);\n"
    comm_insert = comm_anchor + """            if (native_phone_boot) {
                // The HLE socket/serial stack is already live. Native StartC32
                // waits for this minimum core-components-ready publication.
                DEFINE_INT_PROP_D(sys, 0x101F75B6, 0x102045DD, 10);
                LOG_WARN(SYSTEM, "[NBOOT2][C32_READY] category=0x101F75B6 key=0x102045DD value=10");
            }
"""
    text = replace_once(text, comm_anchor, comm_insert, "C32 ready property")
    # If a newer baseline gains an HLE Domain Manager, do not pre-register it:
    # EStart launches the ROM domainSrv.exe itself.
    if "CREATE_SERVER(sys, dm_domain_server);" in text:
        text = wrap_server_once(text, "dm_domain_server", "EStart gives ROM domainSrv.exe first ownership")
    path.write_text(text, encoding="utf-8")

def patch_state_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "native_phone_mode" in text:
        return
    anchor = "        config::state conf;\n        window_server *winserv;\n"
    replacement = """        config::state conf;
        // NATIVEBOOT2 EMUHUB1: transient frontend-selected mode. It survives
        // only the in-process rebuild requested by the Emulator toolbar item.
        bool native_phone_mode = false;
        bool native_boot_handoff_ok = false;
        window_server *winserv;
"""
    text = replace_once(text, anchor, replacement, "iOS emulator native mode state")
    path.write_text(text, encoding="utf-8")

def patch_state_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][ESTART_RUN]" in text:
        return
    if "#include <common/cvt.h>" not in text:
        text = replace_once(text, "#include <common/algorithm.h>\n",
                            "#include <common/algorithm.h>\n#include <common/cvt.h>\n",
                            "state cvt include")
    if "#include <kernel/process.h>" not in text:
        text = replace_once(text, "#include <kernel/kernel.h>\n",
                            "#include <kernel/kernel.h>\n#include <kernel/process.h>\n",
                            "state process include")

    deserialize = "        conf.deserialize();\n"
    deserialize_new = deserialize + """
        // The mode is supplied by the iOS bridge and is intentionally not persisted.
        conf.native_phone_boot = native_phone_mode;
        native_boot_handoff_ok = false;
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][MODE] native_phone_boot={}",
            conf.native_phone_boot ? 1 : 0);
"""
    text = replace_once(text, deserialize, deserialize_new, "state native mode injection")

    anchor = """            register_draw_callback();

            stage_two_inited = true;
"""
    launch = r'''            register_draw_callback();

            if (native_phone_mode) {
                // Z: is mounted above. This is deliberately the sole host handoff:
                // EStart must create domainSrv/SysStart and the firmware resource chain.
                static const std::u16string estart_path = u"Z:\sys\bin\EStart.exe";
                LOG_WARN(FRONTEND_CMDLINE,
                    "[NBOOT2][BOOT_MODE] handoff={} host_sysstart=0 host_menu=0",
                    common::ucs2_to_utf8(estart_path));

                if (!io->exist(estart_path)) {
                    LOG_ERROR(FRONTEND_CMDLINE, "[NBOOT2][ESTART_MISSING] path={}",
                        common::ucs2_to_utf8(estart_path));
                } else {
                    process_ptr estart = symsys->get_kernel_system()->spawn_new_process(estart_path, u"");
                    if (!estart) {
                        LOG_ERROR(FRONTEND_CMDLINE, "[NBOOT2][ESTART_CREATE_FAIL] path={}",
                            common::ucs2_to_utf8(estart_path));
                    } else {
                        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][ESTART_CREATE] name={} path={}",
                            estart->name(), common::ucs2_to_utf8(estart_path));
                        if (!estart->run()) {
                            LOG_ERROR(FRONTEND_CMDLINE, "[NBOOT2][ESTART_RUN_FAIL] name={}", estart->name());
                        } else {
                            native_boot_handoff_ok = true;
                            LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][ESTART_RUN] name={}", estart->name());
                        }
                    }
                }
            }

            stage_two_inited = true;
'''
    text = replace_once(text, anchor, launch, "stage-two EStart handoff")
    path.write_text(text, encoding="utf-8")

def patch_bridge_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "start_native_phone" in text:
        return
    anchor = """    bool is_running();
    bool has_device();
"""
    replacement = anchor + """
    // NATIVEBOOT2 EMUHUB1. These rebuild the active device in a transient
    // firmware-driven startup mode. start_native_phone rolls back to normal
    // mode automatically if the EStart handoff cannot be created/run.
    bool start_native_phone();
    void stop_native_phone();
    bool native_phone_running();
"""
    text = replace_once(text, anchor, replacement, "bridge native phone API")
    path.write_text(text, encoding="utf-8")

def patch_bridge_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][BRIDGE_ENTER]" in text:
        return

    globals_anchor = """        bool g_running = false;
        bool g_has_device = false;
"""
    globals_new = globals_anchor + """        bool g_native_phone_mode = false;
"""
    text = replace_once(text, globals_anchor, globals_new, "bridge mode global")

    state_anchor = """            g_state = std::make_unique<eka2l1::ios::emulator>();
            // emulator_entry runs stage_one/stage_two inline (which mounts and parses the
"""
    state_new = """            g_state = std::make_unique<eka2l1::ios::emulator>();
            g_state->native_phone_mode = g_native_phone_mode;
            // emulator_entry runs stage_one/stage_two inline (which mounts and parses the
"""
    text = replace_once(text, state_anchor, state_new, "bridge pass native mode")

    has_anchor = """    bool has_device() {
        std::lock_guard<std::mutex> guard(g_mutex);
        return g_has_device;
    }

"""
    native_api = has_anchor + """    bool start_native_phone() {
        std::lock_guard<std::mutex> guard(g_mutex);
        if (!g_running || !g_state || !g_has_device) {
            LOG_ERROR(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_ENTER_FAIL] reason=no_active_device");
            return false;
        }

        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_ENTER] rebuilding active device in native mode");
        g_native_phone_mode = true;
        shutdown_locked();
        const bool has_device = start_locked();
        const bool handoff_ok = has_device && g_state && g_state->native_boot_handoff_ok;
        if (!handoff_ok) {
            LOG_ERROR(FRONTEND_CMDLINE,
                "[NBOOT2][BRIDGE_ROLLBACK] native handoff failed; restoring normal EKA2L1 mode");
            g_native_phone_mode = false;
            shutdown_locked();
            start_locked();
            return false;
        }

        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_ENTER_OK] EStart handoff running");
        return true;
    }

    void stop_native_phone() {
        std::lock_guard<std::mutex> guard(g_mutex);
        if (!g_native_phone_mode) {
            return;
        }
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode");
        g_native_phone_mode = false;
        shutdown_locked();
        start_locked();
    }

    bool native_phone_running() {
        std::lock_guard<std::mutex> guard(g_mutex);
        return g_native_phone_mode && g_running && g_has_device;
    }

"""
    text = replace_once(text, has_anchor, native_api, "bridge native phone implementation")

    wipe_anchor = """    bool wipe_app_data() {
        std::lock_guard<std::mutex> guard(g_mutex);

        // 1. Tear the emulator down"""
    wipe_new = """    bool wipe_app_data() {
        std::lock_guard<std::mutex> guard(g_mutex);
        g_native_phone_mode = false;

        // 1. Tear the emulator down"""
    text = replace_once(text, wipe_anchor, wipe_new, "wipe exits native mode")

    install_anchor = """    int install_device(const std::string &rpkg_path, const std::string &rom_path,
        bool install_rpkg, std::function<void(int)> progress) {
        std::lock_guard<std::mutex> guard(g_mutex);
"""
    install_new = install_anchor + """        // Firmware import always belongs to the stable frontend mode.
        g_native_phone_mode = false;
"""
    text = replace_once(text, install_anchor, install_new, "install stable mode")

    exit_anchor = """    void exit_game() {
        std::lock_guard<std::mutex> guard(g_mutex);
        // Reboot the emulator instance, returning to the booted (menu) state.
        shutdown_locked();
        start_locked();
    }
"""
    exit_new = """    void exit_game() {
        std::lock_guard<std::mutex> guard(g_mutex);
        // Ordinary app/game exit always returns to the stable frontend mode.
        g_native_phone_mode = false;
        shutdown_locked();
        start_locked();
    }
"""
    text = replace_once(text, exit_anchor, exit_new, "game exit stable mode")
    path.write_text(text, encoding="utf-8")

def patch_root_view(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "NATIVEBOOT2 EMUHUB1" in text:
        return

    prop_anchor = "@property (nonatomic, assign) BOOL gameRunning;\n"
    prop_new = prop_anchor + "@property (nonatomic, assign) BOOL phoneRunning;       // NATIVEBOOT2 EMUHUB1 native firmware session\n"
    text = replace_once(text, prop_anchor, prop_new, "phoneRunning property")

    toolbar_old = """    NSArray<NSString *> *titles = @[EKAL(@"Add Mode"), EKAL(@"Install Game"), EKAL(@"Settings"), EKAL(@"Apps")];
    NSArray<NSString *> *selectors = @[@"onDeviceButton", @"onInstallGame", @"onSettings", @"onShowApps"];
"""
    toolbar_new = """    // NATIVEBOOT2 EMUHUB1: keep the proven MENUUI36 frontend, but replace
    // the host-side Apps toolbar action with a dedicated firmware Emulator mode.
    NSArray<NSString *> *titles = @[EKAL(@"Add Mode"), EKAL(@"Install Game"), EKAL(@"Settings"), EKAL(@"Emulator")];
    NSArray<NSString *> *selectors = @[@"onDeviceButton", @"onInstallGame", @"onSettings", @"onEmulator"];
"""
    text = replace_once(text, toolbar_old, toolbar_new, "toolbar Emulator item")

    show_anchor = "- (void)onShowApps { [self showAppsScreen]; }\n"
    emulator_method = r'''- (void)onEmulator {
    // NATIVEBOOT2 EMUHUB1: native Nokia startup is explicit, never part of
    // app launch or firmware import. This keeps the normal frontend recoverable.
    if (!eka2l1::ios::bridge::has_device()) {
        [self showAlert:EKAL(@"Emulator unavailable")
                 message:EKAL(@"Install a Symbian device before starting Emulator.")];
        return;
    }
    if (self.phoneRunning) {
        return;
    }

    [self beginProgress:EKAL(@"Starting Emulator…")];
    [self climbProgressToward:0.92f];
    self.emuView.userInteractionEnabled = NO;
    self.controlsView.userInteractionEnabled = NO;
    self.inputManager.enabled = NO;

    dispatch_async(EKANgageLifecycleQueue(), ^{
        const bool ok = eka2l1::ios::bridge::start_native_phone();
        dispatch_async(dispatch_get_main_queue(), ^{
            [self endProgress];
            self.emuView.userInteractionEnabled = YES;
            self.controlsView.userInteractionEnabled = YES;

            if (!ok) {
                self.phoneRunning = NO;
                [self showAppsScreen];
                [self showAlert:EKAL(@"Emulator failed")
                         message:EKAL(@"The Nokia startup chain could not reach EStart. EKA2L1 was restored to normal mode.")];
                return;
            }

            self.phoneRunning = YES;
            self.gameRunning = YES;   // Reuse the proven full-screen guest/input chrome.
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
            NSLog(@"NATIVEBOOT2 EMUHUB1: native Nokia emulator surface entered");
        });
    });
}

- (void)onShowApps { [self showAppsScreen]; }
'''
    text = replace_once(text, show_anchor, emulator_method, "onEmulator method")

    show_apps_anchor = """- (void)showAppsScreen {
    self.gameRunning = NO;
"""
    show_apps_new = """- (void)showAppsScreen {
    self.phoneRunning = NO;
    self.gameRunning = NO;
"""
    text = replace_once(text, show_apps_anchor, show_apps_new, "showApps clears phone mode")

    select_anchor = """    if (self.gameRunning) {
        EKAGameSettings *s = [GameSettingsStore settingsForUid:self.currentGameUid];
"""
    select_new = """    if (self.gameRunning && !self.phoneRunning) {
        EKAGameSettings *s = [GameSettingsStore settingsForUid:self.currentGameUid];
"""
    text = replace_once(text, select_anchor, select_new, "do not persist emulator layout as UID 0")

    menu_anchor = """    if (!self.gameRunning) {
        return;
    }
    GameMenuView *menu = [[GameMenuView alloc] initWithTitle:EKAL(@"Game Menu")];
"""
    menu_new = """    if (!self.gameRunning) {
        return;
    }
    if (self.phoneRunning) {
        GameMenuView *menu = [[GameMenuView alloc] initWithTitle:EKAL(@"Emulator")];
        [menu addOption:EKAL(@"Exit Emulator") destructive:YES handler:^{ [self exitEmulator]; }];
        [menu addOption:EKAL(@"Cancel") destructive:NO handler:nil];
        [self presentGameMenu:menu];
        return;
    }
    GameMenuView *menu = [[GameMenuView alloc] initWithTitle:EKAL(@"Game Menu")];
"""
    text = replace_once(text, menu_anchor, menu_new, "native emulator menu")

    exit_anchor = "// ---- Install (device + game) ----------------------------------------------\n"
    exit_method = r'''- (void)exitEmulator {
    if (![NSThread isMainThread]) {
        dispatch_async(dispatch_get_main_queue(), ^{ [self exitEmulator]; });
        return;
    }
    if (!self.phoneRunning) {
        return;
    }

    self.phoneRunning = NO;
    self.gameRunning = NO;
    self.emuView.userInteractionEnabled = NO;
    self.controlsView.userInteractionEnabled = NO;
    self.inputManager.enabled = NO;
    [self stopPollTimer];
    self.controlsView.layout = 0;
    self.controlsView.hidden = YES;
    self.menuButton.hidden = YES;
    self.statusLabel.hidden = NO;
    self.statusLabel.text = EKAL(@"Exiting Emulator…");

    dispatch_async(EKANgageLifecycleQueue(), ^{
        eka2l1::ios::bridge::stop_native_phone();
        dispatch_async(dispatch_get_main_queue(), ^{
            self.emuView.userInteractionEnabled = YES;
            self.controlsView.userInteractionEnabled = YES;
            [self showAppsScreen];
            [self pollForAppsWithAttemptsLeft:20];
            NSLog(@"NATIVEBOOT2 EMUHUB1: restored normal EKA2L1 frontend mode");
        });
    });
}

'''
    text = replace_once(text, exit_anchor, exit_method + exit_anchor, "exitEmulator method")

    install_wait_old = """            if (result == 0) {
                // Extraction done; the guest now boots asynchronously. Keep the bar moving
                // until its apps register, then finish.
                self.statusLabel.text = EKAL(@"Booting device…");
                [self climbProgressToward:0.98f];
                [self pollUntilAppsThen:^(BOOL found) {
                    [self endProgress];
                    [self showAppsScreen];
                    if (self.pendingInstallAfterFirmware.length > 0) {
                        NSString *resumePath = [self.pendingInstallAfterFirmware copy];
                        self.pendingInstallAfterFirmware = nil;
                        [self installImportedContentAtPath:resumePath];
                        return;
                    }
                    [self showAlert:EKAL(@"Device installed") message:EKAL(@"The Symbian device was installed and booted.")];
                } attemptsLeft:30];
            } else {
"""
    install_wait_new = """            if (result == 0) {
                // NATIVEBOOT2 EMUHUB1: bridge::install_device already rebuilt the
                // stable guest before returning. Do not block the UI at 98% waiting
                // up to 45 seconds for AppArc; the Apps toolbar no longer exists.
                [self endProgress];
                [self showAppsScreen];
                [self pollForAppsWithAttemptsLeft:20]; // non-blocking background refresh
                if (self.pendingInstallAfterFirmware.length > 0) {
                    NSString *resumePath = [self.pendingInstallAfterFirmware copy];
                    self.pendingInstallAfterFirmware = nil;
                    [self installImportedContentAtPath:resumePath];
                    return;
                }
                [self showAlert:EKAL(@"Device installed") message:EKAL(@"The Symbian device was installed and is ready for Emulator.")];
            } else {
"""
    text = replace_once(text, install_wait_old, install_wait_new, "remove 98 percent app wait")
    path.write_text(text, encoding="utf-8")

def patch_localization(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if '@"Exit Emulator" : @"Thoát Emulator"' in text:
        return
    anchor = '            @"Add Mode" : @"Thêm chế độ",\n'
    insert = anchor + '''            @"Emulator" : @"Emulator",
            @"Starting Emulator…" : @"Đang khởi động Emulator…",
            @"Exiting Emulator…" : @"Đang thoát Emulator…",
            @"Exit Emulator" : @"Thoát Emulator",
            @"Emulator unavailable" : @"Emulator chưa sẵn sàng",
            @"Install a Symbian device before starting Emulator." : @"Hãy cài thiết bị Symbian trước khi khởi động Emulator.",
            @"Emulator failed" : @"Emulator khởi động thất bại",
            @"The Nokia startup chain could not reach EStart. EKA2L1 was restored to normal mode." : @"Chuỗi khởi động Nokia không thể chạy EStart. EKA2L1 đã tự khôi phục về chế độ bình thường.",
            @"The Symbian device was installed and is ready for Emulator." : @"Thiết bị Symbian đã được cài và sẵn sàng cho Emulator.",
'''
    text = replace_once(text, anchor, insert, "Vietnamese Emulator strings")
    path.write_text(text, encoding="utf-8")

def patch_svc_trace(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][COLLISION]" in text:
        return
    server_anchor = """        if (handle != kernel::INVALID_HANDLE) {
            LOG_TRACE(KERNEL, "Server {} created", server_name);
        }

        return handle;
"""
    server_new = """        if (handle != kernel::INVALID_HANDLE) {
            LOG_TRACE(KERNEL, "Server {} created", server_name);
            if (kern->get_config()->native_phone_boot) {
                LOG_WARN(KERNEL, "[NBOOT2][SERVER_REGISTER] process={} server={} handle={} mode={}",
                    crr_pr->name(), server_name, handle, mode);
            }
        } else if (kern->get_config()->native_phone_boot) {
            server_ptr existing = kern->get_by_name<service::server>(server_name);
            LOG_WARN(KERNEL,
                "[NBOOT2][COLLISION] process={} server={} mode={} existing={} existing_hle={}",
                crr_pr->name(), server_name, mode, existing ? existing->name() : std::string("<none>"),
                (existing && existing->is_hle()) ? 1 : 0);
        }

        return handle;
"""
    text = replace_once(text, server_anchor, server_new, "native server trace")

    missing_anchor = """        if (!server) {
            LOG_TRACE(KERNEL, "Create session to unexist server: {}", server_name);
            return epoc::error_not_found;
        }
"""
    missing_new = """        if (!server) {
            LOG_TRACE(KERNEL, "Create session to unexist server: {}", server_name);
            if (kern->get_config()->native_phone_boot) {
                LOG_WARN(KERNEL, "[NBOOT2][MISSING_SERVER] process={} server={} msg_slots={} mode={}",
                    pr->name(), server_name, msg_slot, mode);
            }
            return epoc::error_not_found;
        }
"""
    text = replace_once(text, missing_anchor, missing_new, "native missing server trace")
    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_emuhub1.py <upstream-root>")
    up = Path(sys.argv[1]).resolve()
    paths = {
        "config": up / "src/emu/config/include/config/config.h",
        "services": up / "src/emu/services/src/init.cpp",
        "state_h": up / "src/emu/ios/include/ios/state.h",
        "state_cpp": up / "src/emu/ios/src/state.cpp",
        "bridge_h": up / "src/emu/ios/include/ios/emu_bridge.h",
        "bridge_cpp": up / "src/emu/ios/src/emu_bridge.mm",
        "root": up / "src/emu/ios/app/RootViewController.mm",
        "loc": up / "src/emu/ios/app/EKALocalization.mm",
        "svc": up / "src/emu/kernel/src/svc.cpp",
    }
    for name, path in paths.items():
        if not path.is_file():
            fail(f"missing {name} baseline file: {path}")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")
    menuui_marker = up / "src/emu/services/src/window/classes/wingroup.cpp"
    if not menuui_marker.is_file() or "SYMBIAN-SYSTEMAPPS1 MENUUI36 WG_FOCUS:" not in menuui_marker.read_text(encoding="utf-8"):
        fail("MENUUI36 baseline marker missing")

    patch_config(paths["config"])
    patch_services(paths["services"])
    patch_state_header(paths["state_h"])
    patch_state_cpp(paths["state_cpp"])
    patch_bridge_header(paths["bridge_h"])
    patch_bridge_cpp(paths["bridge_cpp"])
    patch_root_view(paths["root"])
    patch_localization(paths["loc"])
    patch_svc_trace(paths["svc"])

    gates = {
        paths["config"]: ["bool native_phone_boot{ false }"],
        paths["services"]: ["[NBOOT2][HLE_POLICY]", "[NBOOT2][C32_READY]"],
        paths["state_h"]: ["native_phone_mode", "native_boot_handoff_ok"],
        paths["state_cpp"]: ["[NBOOT2][BOOT_MODE]", "[NBOOT2][ESTART_CREATE]", "[NBOOT2][ESTART_RUN]",
                             'u"Z:\\\\sys\\\\bin\\\\EStart.exe"'],
        paths["bridge_h"]: ["start_native_phone", "stop_native_phone", "native_phone_running"],
        paths["bridge_cpp"]: ["[NBOOT2][BRIDGE_ENTER]", "[NBOOT2][BRIDGE_ROLLBACK]", "[NBOOT2][BRIDGE_EXIT]"],
        paths["root"]: ["NATIVEBOOT2 EMUHUB1", 'EKAL(@"Emulator")', "onEmulator", "exitEmulator",
                        "Do not block the UI at 98%"],
        paths["svc"]: ["[NBOOT2][COLLISION]", "[NBOOT2][MISSING_SERVER]"],
    }
    for path, required in gates.items():
        body = path.read_text(encoding="utf-8")
        for gate in required:
            if gate not in body:
                fail(f"gate missing in {path}: {gate}")

    # Architectural invariants: native boot is on-demand and EStart-only.
    state_body = paths["state_cpp"].read_text(encoding="utf-8")
    root_body = paths["root"].read_text(encoding="utf-8")
    forbidden = ("PHONE_BOOT_PLAN", "sysstart_path", 'spawn_new_process(u"Z:\\sys\\bin\\sysstart.exe"',
                 'spawn_new_process(u"Z:\\sys\\bin\\menu3.exe"')
    for token in forbidden:
        if token in state_body:
            fail(f"forbidden host-driven startup token present: {token}")
    if 'EKAL(@"Apps")];' in root_body or '@[@"onDeviceButton", @"onInstallGame", @"onSettings", @"onShowApps"]' in root_body:
        fail("top-level Apps toolbar action still present")

    print("NATIVEBOOT2 EMUHUB1 applied")
    print("baseline=MENUUI36_NOJAVA_MANIC3")
    print("default_mode=stable_EKA2L1")
    print("toolbar=Devices,InstallGame,Settings,Emulator")
    print("native_entry=explicit_Emulator_action")
    print("handoff=Z:\\sys\\bin\\EStart.exe_ONLY_AFTER_Z_MOUNT")
    print("rollback_on_handoff_failure=ENABLED")
    print("firmware_98pct_app_wait=REMOVED")
    print("host_sysstart=DISABLED")
    print("host_menu=DISABLED")
    print("NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
