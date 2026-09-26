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
        std::atomic<bool> compat_first_failure_logged{ false };
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
    if "#include <kernel/timing.h>" not in source:
        source = replace_once(source, "#include <kernel/process.h>\n",
                              "#include <kernel/process.h>\n#include <kernel/timing.h>\n",
                              "CompatBoot startup timeout API")
    reset = '''        conf.compat_menu_probe_mode = compat_menu_probe_mode;
        conf.compat_menu_probe_launched = false;
        conf.compat_menu_probe_timed_out = false;
        conf.compat_menu_probe_finished = false;
        conf.compat_first_failure_logged = false;
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
                                auto *compat_cfg = &conf;
                                auto *compat_kern = symsys->get_kernel_system();
                                const int compat_event = compat_kern->get_ntimer()->register_event(
                                    "COMPATBOOT1_STARTUP_TIMEOUT",
                                    [compat_cfg](std::uint64_t, int) {
                                        if (!compat_cfg->compat_menu_probe_mode || compat_cfg->compat_menu_probe_finished) return;
                                        std::string missing;
                                        if (!compat_cfg->compat_seen_file_server) missing += "FileServer,";
                                        if (!compat_cfg->compat_seen_fbs) missing += "FBS,";
                                        if (!compat_cfg->compat_seen_window_server) missing += "WindowServer,";
                                        if (!compat_cfg->compat_seen_cenrep) missing += "CenRep,";
                                        if (!compat_cfg->compat_seen_apparc) missing += "AppArc,";
                                        if (!compat_cfg->compat_seen_akncap) missing += "AknCapServer,";
                                        if (!missing.empty()) missing.pop_back();
                                        bool expected = false;
                                        if (compat_cfg->compat_menu_probe_finished.compare_exchange_strong(expected, true)) {
                                            compat_cfg->compat_menu_probe_timed_out = true;
                                            LOG_ERROR(FRONTEND_CMDLINE,
                                                "[COMPATBOOT][BARRIER_TIMEOUT] missing_or_unobserved={}", missing);
                                        }
                                    });
                                conf.compat_menu_probe_timeout_event = compat_event;
                                if (compat_event >= 0) {
                                    compat_kern->get_ntimer()->schedule_event(60000000, compat_event, 0);
                                    conf.compat_timeout_event_registered = true;
                                } else {
                                    LOG_ERROR(FRONTEND_CMDLINE,
                                        "[COMPATBOOT][BARRIER_TIMEOUT_REGISTER_FAIL] event_id={}", compat_event);
                                }
                                LOG_WARN(FRONTEND_CMDLINE,
                                    "[COMPATBOOT][DEADLINE_START] after=EStart_run timeout_ms=60000");
                                LOG_WARN(FRONTEND_CMDLINE,
                                    "[COMPATBOOT][BARRIER_WAIT] services=6");
                            }
'''
    return replace_once(source, anchor, deadline, "start deadline after EStart")


def patch_menu3_leave5(source):
    marker = "[COMPATBOOT][MENU3_LEAVE5]"
    if marker in source:
        return source

    sig = "    BRIDGE_FUNC(eka2l1::ptr<void>, leave_start) {"
    start = source.find(sig)
    if start < 0:
        fail("leave_start block is missing for Menu3 Leave(-5) trace")
    after = start + len(sig)
    ends = [pos for pos in (
        source.find("\n    BRIDGE_FUNC(", after),
        source.find("\n}", after),
    ) if pos >= 0]
    if not ends:
        fail("leave_start block boundary is missing for Menu3 Leave(-5) trace")
    end = min(ends)
    body = source[start:end]
    anchor = "        thr->increase_leave_depth();\n"
    if body.count(anchor) != 1:
        fail(f"leave-depth anchor count={body.count(anchor)}")

    trace = r'''        // COMPATBOOT1 Menu3 follow-up: observe trapped KErrNotSupported.
        auto *compat_leave_cfg = kern->get_config();
        auto *compat_leave_pr = kern->crr_process();
        auto *compat_leave_cpu = kern->get_cpu();
        const std::uint32_t compat_leave_uid3 = compat_leave_pr
            ? static_cast<std::uint32_t>(std::get<2>(compat_leave_pr->get_uid_type()))
            : 0U;
        const std::int32_t compat_leave_code = compat_leave_cpu
            ? static_cast<std::int32_t>(compat_leave_cpu->get_reg(0))
            : 0;

        if (compat_leave_cfg && compat_leave_pr && compat_leave_cpu && thr
            && compat_leave_cfg->compat_menu_probe_mode
            && compat_leave_cfg->compat_target_uid3 != 0
            && compat_leave_uid3 == compat_leave_cfg->compat_target_uid3
            && compat_leave_code == epoc::error_not_supported) {
            const std::uint32_t compat_leave_pc = compat_leave_cpu->get_pc();
            const std::uint32_t compat_leave_lr = compat_leave_cpu->get_reg(14);
            const std::uint32_t compat_leave_sp = compat_leave_cpu->get_reg(13);
            const std::uint32_t compat_leave_trap =
                current_local_data(kern)->trap_handler.ptr_address();

            LOG_WARN(KERNEL,
                "[COMPATBOOT][MENU3_LEAVE5] process={} uid3=0x{:08X} thread={} leave={} trap=0x{:08X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X} behavior=OBSERVE_ONLY",
                compat_leave_pr->name(), compat_leave_uid3, thr->name(),
                compat_leave_code, compat_leave_trap, compat_leave_pc, compat_leave_lr,
                compat_leave_sp, compat_leave_cpu->get_cpsr(),
                compat_leave_cpu->get_reg(0), compat_leave_cpu->get_reg(1),
                compat_leave_cpu->get_reg(2), compat_leave_cpu->get_reg(3),
                compat_leave_cpu->get_reg(4), compat_leave_cpu->get_reg(5),
                compat_leave_cpu->get_reg(6), compat_leave_cpu->get_reg(7),
                compat_leave_cpu->get_reg(8), compat_leave_cpu->get_reg(9),
                compat_leave_cpu->get_reg(10), compat_leave_cpu->get_reg(11),
                compat_leave_cpu->get_reg(12));

            auto compat_leave_log_frame = [&](const char *kind, const std::uint32_t raw) {
                const std::uint32_t addr = raw & ~1U;
                codeseg_ptr seg = get_codeseg_from_addr(kern, compat_leave_pr, addr, false);
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(compat_leave_pr);
                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_FRAME] kind={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        kind, raw, common::ucs2_to_utf8(seg->get_full_path()),
                        base, addr - base);
                } else {
                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_FRAME] kind={} raw=0x{:08X} module=<unresolved>",
                        kind, raw);
                }
            };

            compat_leave_log_frame("pc", compat_leave_pc);
            compat_leave_log_frame("lr", compat_leave_lr);
            compat_leave_log_frame("trap", compat_leave_trap);

            for (std::uint32_t i = 0; i < 32; ++i) {
                const std::uint32_t slot_addr = compat_leave_sp + i * sizeof(std::uint32_t);
                if (slot_addr < compat_leave_sp) break;
                const std::uint32_t *slot =
                    eka2l1::ptr<std::uint32_t>(slot_addr).get(compat_leave_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_STACK] index={} slot=0x{:08X} mapped=0 stopping=1",
                        i, slot_addr);
                    break;
                }

                const std::uint32_t value = *slot;
                const std::uint32_t candidate = value & ~1U;
                codeseg_ptr seg = candidate >= 0x10000U
                    ? get_codeseg_from_addr(kern, compat_leave_pr, candidate, false)
                    : nullptr;
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(compat_leave_pr);
                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()),
                        base, candidate - base);
                }
            }
        }

'''
    body = body.replace(anchor, trace + anchor, 1)
    return source[:start] + body + source[end:]


def patch_svc(source):
    if "[COMPATBOOT][TARGET_LAUNCH]" in source:
        return patch_menu3_leave5(source)
    includes = "#include <sstream>\n"
    source = replace_once(source, "#include <kernel/kernel.h>\n",
                          "#include <kernel/kernel.h>\n" + includes,
                          "COMPATBOOT service interfaces")
    helper = r'''namespace eka2l1::kernel::svc {
    static std::string compatboot1_missing_services(kernel_system *kern, config::state *cfg) {
        const epocver ver = kern->get_epoc_version();
        auto ready = [kern](const std::string &name, bool guest_ready) {
            service::server *registered = kern->get_by_name<service::server>(name);
            return registered && (registered->is_hle() || guest_ready);
        };
        std::ostringstream missing;
        if (!ready(epoc::fs::get_server_name_through_epocver(ver), cfg->compat_seen_file_server)) missing << "FileServer,";
        if (!ready(epoc::get_fbs_server_name_by_epocver(ver), cfg->compat_seen_fbs)) missing << "FBS,";
        if (!ready(get_winserv_name_by_epocver(ver), cfg->compat_seen_window_server)) missing << "WindowServer,";
        if (!ready("!CentralRepository", cfg->compat_seen_cenrep)) missing << "CenRep,";
        if (!ready(get_app_list_server_name_by_epocver(ver), cfg->compat_seen_apparc)) missing << "AppArc,";
        if (!ready("101fdfae_10207218_AppServer", cfg->compat_seen_akncap)) missing << "AknCapServer,";
        std::string result = missing.str();
        if (!result.empty()) result.pop_back();
        return result;
    }

    static void compatboot1_check_barrier(kernel_system *kern, service::server *current) {
        config::state *cfg = kern->get_config();
        if (!cfg->compat_menu_probe_mode || cfg->compat_menu_probe_finished) return;
        const epocver ver = kern->get_epoc_version();
        if (current) {
            const std::string &name = current->name();
            if (name == epoc::fs::get_server_name_through_epocver(ver)) cfg->compat_seen_file_server = true;
            if (name == epoc::get_fbs_server_name_by_epocver(ver)) cfg->compat_seen_fbs = true;
            if (name == get_winserv_name_by_epocver(ver)) cfg->compat_seen_window_server = true;
            if (name == "!CentralRepository") cfg->compat_seen_cenrep = true;
            if (name == get_app_list_server_name_by_epocver(ver)) cfg->compat_seen_apparc = true;
            if (name == "101fdfae_10207218_AppServer") cfg->compat_seen_akncap = true;
        }
        const std::string missing = compatboot1_missing_services(kern, cfg);
        if (!missing.empty()) {
            LOG_WARN(KERNEL, "[COMPATBOOT][BARRIER_WAIT] missing={}", missing);
            return;
        }
        bool expected = false;
        if (!cfg->compat_menu_probe_finished.compare_exchange_strong(expected, true)) return;
        cfg->compat_menu_probe_launched = true;
        kern->get_ntimer()->unschedule_event(cfg->compat_menu_probe_timeout_event, 0);
        LOG_WARN(KERNEL, "[COMPATBOOT][BARRIER_READY] services=FileServer,FBS,WindowServer,CenRep,AppArc,AknCapServer");
        static const std::u16string menu_path = u"Z:\\sys\\bin\\menu3.exe";
        process_ptr menu = kern->spawn_new_process(menu_path, u"");
        if (!menu) {
            LOG_ERROR(KERNEL, "[COMPATBOOT][TARGET_LAUNCH] path={} result=CREATE_FAILED",
                common::ucs2_to_utf8(menu_path));
            return;
        }
        cfg->compat_target_uid3 = static_cast<std::uint32_t>(
            std::get<2>(menu->get_uid_type()));
        if (!menu->run()) {
            LOG_ERROR(KERNEL, "[COMPATBOOT][TARGET_LAUNCH] path={} result=RUN_FAILED process={}",
                common::ucs2_to_utf8(menu_path), menu->name());
            return;
        }
        LOG_WARN(KERNEL, "[COMPATBOOT][TARGET_LAUNCH] path={} result=RUNNING process={} one_shot=1",
            common::ucs2_to_utf8(menu_path), menu->name());
    }
}
'''
    declarations = '''namespace eka2l1::epoc {
    std::string get_fbs_server_name_by_epocver(const epocver ver);
}
namespace eka2l1::epoc::fs {
    std::string get_server_name_through_epocver(const epocver ver);
}
namespace eka2l1 {
    std::string get_winserv_name_by_epocver(const epocver ver);
    const std::string get_app_list_server_name_by_epocver(const epocver ver);
}
'''
    source = replace_once(source, "namespace eka2l1::epoc {\n",
                          declarations + helper + "\nnamespace eka2l1::epoc {\n",
                          "serialized CompatBoot barrier helper")
    receive = ("    BRIDGE_FUNC(void, server_receive, kernel::handle h, eka2l1::ptr<epoc::request_status> req_sts, eka2l1::ptr<void> data_ptr) {\n"
               "        server_ptr server = kern->get<service::server>(h);\n\n"
               "        if (!server) {\n            return;\n        }\n")
    source = replace_once(source, receive,
                          receive + "\n        eka2l1::kernel::svc::compatboot1_check_barrier(kern, server);\n",
                          "poll from server readiness SVC")
    return patch_menu3_leave5(source)


def patch_missing_server(source):
    if "[COMPATBOOT][FIRST_FAILURE]" in source:
        return source
    anchor = '                LOG_WARN(KERNEL, "[NBOOT2][MISSING_SERVER] process={} server={} msg_slots={} mode={}",\n'
    trace = '''                if (kern->get_config()->compat_menu_probe_mode && pr &&
                    kern->get_config()->compat_target_uid3 != 0) {
                    const auto compat_uid3 = static_cast<std::uint32_t>(std::get<2>(pr->get_uid_type()));
                    bool compat_expected = false;
                    if (compat_uid3 == kern->get_config()->compat_target_uid3 &&
                        kern->get_config()->compat_first_failure_logged.compare_exchange_strong(compat_expected, true)) {
                        LOG_WARN(KERNEL,
                            "[COMPATBOOT][MISSING_SERVER] target_uid3=0x{:08X} caller={} server={} result={}",
                            compat_uid3, pr->name(), server_name, epoc::error_not_found);
                        LOG_WARN(KERNEL,
                            "[COMPATBOOT][FIRST_FAILURE] source=MISSING_SERVER target_uid3=0x{:08X} server={}",
                            compat_uid3, server_name);
                    }
                }
'''
    return replace_once(source, anchor, trace + anchor, "profile-scoped first missing-server trace")


def patch_target_visible(source):
    marker = "[COMPATBOOT][TARGET_VISIBLE]"
    if marker in source:
        return source
    start = source.find("[NBOOT2][POSTLOGO_CANVAS_VISIBLE]")
    if start < 0:
        fail("B50 canvas visibility trace is missing")
    end = source.find("            ctx.complete(epoc::error_none);", start)
    if end < 0:
        fail("B50 canvas visibility completion anchor is missing")
    trace = '''            eka2l1::config::state *compat_cfg = client->get_ws().get_kernel_system()->get_config();
            if (compat_cfg->compat_menu_probe_mode &&
                b50_uid3 == compat_cfg->compat_target_uid3 && b50_group &&
                is_visible() && can_be_physically_seen()) {
                LOG_WARN(SERVICE_WINDOW,
                    "[COMPATBOOT][TARGET_VISIBLE] uid3=0x{:08X} process={} group_id={} group_name={} visible=1 physically_seen=1",
                    b50_uid3, b50_pr ? b50_pr->name() : std::string("<null>"),
                    b50_group->id, common::ucs2_to_utf8(b50_group->name));
            }
'''
    return source[:end] + trace + source[end:]


# Exported so the manifest contract exercises the same source transformation as apply().
ROOT_VIEW_FIXTURE = '''- (void)onEmulator {
    // NATIVEBOOT2 EMUHUB1: native Nokia startup is explicit.
    if (!eka2l1::ios::bridge::has_device()) {
        [self showAlert:EKAL(@"Emulator unavailable")
                 message:EKAL(@"Install a Symbian device before starting Emulator.")];
        return;
    }
    if (self.phoneRunning) { return; }
    // Existing NATIVEBOOT2 launch body
}

- (void)onShowApps { [self showAppsScreen]; }
'''
STATE_H_FIXTURE = '''        bool native_phone_mode = false;
        bool native_boot_handoff_ok = false;
'''


def apply(upstream_root):
    upstream = Path(upstream_root).resolve()
    state_h = upstream / "src/emu/ios/include/ios/state.h"
    root = upstream / "src/emu/ios/app/RootViewController.mm"
    bridge_h = upstream / "src/emu/ios/include/ios/emu_bridge.h"
    bridge_mm = upstream / "src/emu/ios/src/emu_bridge.mm"
    localization = upstream / "src/emu/ios/app/EKALocalization.mm"
    config_h = upstream / "src/emu/config/include/config/config.h"
    state_cpp = upstream / "src/emu/ios/src/state.cpp"
    svc = upstream / "src/emu/kernel/src/svc.cpp"
    winuser = upstream / "src/emu/services/src/window/classes/winuser.cpp"
    for path in (state_h, root, bridge_h, bridge_mm, localization, config_h, state_cpp, svc, winuser):
        if not path.is_file():
            fail(f"missing source: {path}")
    state_text = patch_state_header(state_h.read_text(encoding="utf-8"))
    root_text = patch_emulator_choice(root.read_text(encoding="utf-8"))
    bridge_h_text = patch_bridge_header(bridge_h.read_text(encoding="utf-8"))
    bridge_mm_text = patch_bridge_cpp(bridge_mm.read_text(encoding="utf-8"))
    localization_text = patch_localization(localization.read_text(encoding="utf-8"))
    config_text = patch_config_header(config_h.read_text(encoding="utf-8"))
    state_cpp_text = patch_state_cpp(state_cpp.read_text(encoding="utf-8"))
    svc_text = patch_missing_server(patch_svc(svc.read_text(encoding="utf-8")))
    winuser_text = patch_target_visible(winuser.read_text(encoding="utf-8"))
    state_h.write_text(state_text, encoding="utf-8")
    root.write_text(root_text, encoding="utf-8")
    bridge_h.write_text(bridge_h_text, encoding="utf-8")
    bridge_mm.write_text(bridge_mm_text, encoding="utf-8")
    localization.write_text(localization_text, encoding="utf-8")
    config_h.write_text(config_text, encoding="utf-8")
    state_cpp.write_text(state_cpp_text, encoding="utf-8")
    svc.write_text(svc_text, encoding="utf-8")
    winuser.write_text(winuser_text, encoding="utf-8")
    print(MARK + ": applied; explicit CompatBoot choice is wired")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_compatboot1_menuprobe1.py <upstream-root>")
    apply(sys.argv[1])


if __name__ == "__main__":
    main()
