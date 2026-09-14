#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui6_errororigintrace1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
eik_path = up / "src/emu/services/src/ui/eikappui.cpp"
ctx_path = up / "src/emu/services/src/context.cpp"

for path in (svc_path, eik_path, ctx_path):
    if not path.is_file():
        raise SystemExit(f"MENUUI6: required source file missing: {path}")

svc = svc_path.read_text(encoding="utf-8")
eik = eik_path.read_text(encoding="utf-8")
ctx = ctx_path.read_text(encoding="utf-8")

markers = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 EIK_RESOLVE_ERROR:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC:",
]
present = [m for m in markers if (m in svc or m in eik or m in ctx)]
if present:
    if len(present) == len(markers):
        print("MENUUI6 ERRORORIGINTRACE1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI6: partial prior patch detected: " + ", ".join(present))

# Hard regression gates: MENUUI6 is layered on the exact diagnostic/fix chain that
# reached MENUUI5. It must not silently apply to a source tree missing those fixes.
svc_required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 LEAVE ENTER:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 LEAVE RETURN:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 FRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK:",
    "static codeseg_ptr get_codeseg_from_addr(",
]
missing = [m for m in svc_required if m not in svc]
if missing:
    raise SystemExit("MENUUI6: required MENUUI2/4/5 svc baseline missing: " + ", ".join(missing))

if "Unimplemented app ui session opcode 0x{:X}" not in eik:
    raise SystemExit("MENUUI6: EikAppUi generic unimplemented path not found")
if "ctx->complete(epoc::error_none);" not in eik:
    raise SystemExit("MENUUI6: EikAppUi existing completion semantics not found")
if "void ipc_context::complete(int res)" not in ctx:
    raise SystemExit("MENUUI6: ipc_context::complete not found")

# -----------------------------------------------------------------------------
# 1) Deep trace every leave_start whose guest leave code is KErrNotFound (-1).
#    This is intentionally NOT filtered to Menu: the point is to disambiguate
#    the interleaved Menu/xnthemeserver leaves seen in MENUUI5.
# -----------------------------------------------------------------------------
leave_sig = "    BRIDGE_FUNC(eka2l1::ptr<void>, leave_start) {"
leave_start = svc.find(leave_sig)
if leave_start < 0:
    raise SystemExit("MENUUI6: leave_start signature not found")
leave_end = svc.find("\n    BRIDGE_FUNC(", leave_start + len(leave_sig))
if leave_end < 0:
    raise SystemExit("MENUUI6: leave_start end anchor not found")
leave_body = svc[leave_start:leave_end]
leave_anchor = "        kernel::thread *thr = kern->crr_thread();\n"
if leave_body.count(leave_anchor) != 1:
    raise SystemExit(f"MENUUI6: expected one leave_start thread anchor, found {leave_body.count(leave_anchor)}")

leave_inject = r'''        // MENUUI6 ERRORORIGINTRACE1: diagnostic-only deep trace for KErrNotFound.
        // Do not consume, rewrite or suppress the leave. All original leave_start
        // control flow below remains untouched.
        auto *menuui6_cpu = kern->get_cpu();
        kernel::process *menuui6_pr = kern->crr_process();
        const std::int32_t menuui6_leave_code = menuui6_cpu
            ? static_cast<std::int32_t>(menuui6_cpu->get_reg(0))
            : 0;

        if (menuui6_cpu && menuui6_pr && thr && (menuui6_leave_code == epoc::error_not_found)) {
            const std::uint32_t menuui6_pc = menuui6_cpu->get_pc();
            const std::uint32_t menuui6_lr = menuui6_cpu->get_reg(14);
            const std::uint32_t menuui6_sp = menuui6_cpu->get_reg(13);
            const std::uint32_t menuui6_cpsr = menuui6_cpu->get_cpsr();
            const std::uint32_t menuui6_trap = current_local_data(kern)->trap_handler.ptr_address();
            const auto menuui6_uids = menuui6_pr->get_uid_type();
            const std::uint32_t menuui6_uid3 = static_cast<std::uint32_t>(std::get<2>(menuui6_uids));

            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1: process={} uid=0x{:08X} thread={} leave_code={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} trap=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                menuui6_pr->name(), menuui6_uid3, thr->name(), menuui6_leave_code,
                menuui6_pc, menuui6_lr, menuui6_sp, menuui6_cpsr, menuui6_trap,
                menuui6_cpu->get_reg(0), menuui6_cpu->get_reg(1), menuui6_cpu->get_reg(2), menuui6_cpu->get_reg(3),
                menuui6_cpu->get_reg(4), menuui6_cpu->get_reg(5), menuui6_cpu->get_reg(6), menuui6_cpu->get_reg(7),
                menuui6_cpu->get_reg(8), menuui6_cpu->get_reg(9), menuui6_cpu->get_reg(10), menuui6_cpu->get_reg(11),
                menuui6_cpu->get_reg(12));

            auto menuui6_log_code_addr = [&](const char *kind, const std::uint32_t raw_addr) {
                const std::uint32_t addr = raw_addr & ~1U;
                codeseg_ptr seg = get_codeseg_from_addr(kern, menuui6_pr, addr, false);
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(menuui6_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        kind, raw_addr, addr, common::ucs2_to_utf8(seg->get_full_path()), base, addr - base);
                } else {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module=<unresolved>",
                        kind, raw_addr, addr);
                }
            };

            menuui6_log_code_addr("pc", menuui6_pc);
            menuui6_log_code_addr("lr", menuui6_lr);
            menuui6_log_code_addr("trap", menuui6_trap);

            constexpr std::uint32_t menuui6_stack_word_count = 32;
            for (std::uint32_t i = 0; i < menuui6_stack_word_count; ++i) {
                const std::uint32_t slot_addr = menuui6_sp + i * sizeof(std::uint32_t);
                if (slot_addr < menuui6_sp) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=<overflow> stopping=1", i);
                    break;
                }

                const std::uint32_t *slot = eka2l1::ptr<std::uint32_t>(slot_addr).get(menuui6_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} mapped=0 stopping=1",
                        i, slot_addr);
                    break;
                }

                const std::uint32_t value = *slot;
                const std::uint32_t candidate = value & ~1U;
                codeseg_ptr seg = nullptr;
                if (candidate >= 0x10000U) {
                    seg = get_codeseg_from_addr(kern, menuui6_pr, candidate, false);
                }

                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(menuui6_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()), base, candidate - base);
                } else {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                        i, slot_addr, value);
                }
            }
        }

'''
leave_body = leave_body.replace(leave_anchor, leave_anchor + leave_inject, 1)
svc = svc[:leave_start] + leave_body + svc[leave_end:]

# -----------------------------------------------------------------------------
# 2) Trace native/LLE negative IPC completions delivered to Menu. This is placed
#    on the already-existing message completion path immediately before EKA2L1's
#    normal completion callbacks; val is not modified.
# -----------------------------------------------------------------------------
lle_anchor = "        kern->call_ipc_complete_callbacks(msg, val);\n        msg->unref();"
if svc.count(lle_anchor) != 1:
    raise SystemExit(f"MENUUI6: expected one LLE completion anchor, found {svc.count(lle_anchor)}")

lle_inject = r'''        if ((val < 0) && msg && msg->own_thr) {
            kernel::thread *menuui6_client_thr = msg->own_thr;
            kernel::process *menuui6_client_pr = menuui6_client_thr->owning_process();
            if (menuui6_client_pr) {
                const auto menuui6_client_uids = menuui6_client_pr->get_uid_type();
                const std::uint32_t menuui6_client_uid = static_cast<std::uint32_t>(std::get<2>(menuui6_client_uids));
                if (menuui6_client_uid == 0x101F4CD2U) {
                    std::string menuui6_server_name = "<no-session>";
                    if (msg->msg_session && !msg->msg_session->is_server_terminated()
                        && msg->msg_session->get_server()) {
                        menuui6_server_name = msg->msg_session->get_server()->name();
                    }

                    kernel::thread *menuui6_server_thr = kern->crr_thread();
                    kernel::process *menuui6_server_pr = kern->crr_process();
                    std::string menuui6_server_process = menuui6_server_pr ? menuui6_server_pr->name() : "<none>";
                    std::string menuui6_server_thread = menuui6_server_thr ? menuui6_server_thr->name() : "<none>";

                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=LLE server={} opcode={} result={} msg_id={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} client_process={} client_uid=0x{:08X} client_thread={} server_process={} server_thread={}",
                        menuui6_server_name, msg->function, val, msg->id,
                        static_cast<std::uint32_t>(msg->args.flag),
                        static_cast<std::uint32_t>(msg->args.args[0]), static_cast<std::uint32_t>(msg->args.args[1]),
                        static_cast<std::uint32_t>(msg->args.args[2]), static_cast<std::uint32_t>(msg->args.args[3]),
                        menuui6_client_pr->name(), menuui6_client_uid, menuui6_client_thr->name(),
                        menuui6_server_process, menuui6_server_thread);
                }
            }
        }

'''
svc = svc.replace(lle_anchor, lle_inject + lle_anchor, 1)

# -----------------------------------------------------------------------------
# 3) Trace EikAppUi opcode 0x7 (EEikAppUiResolveError) and its raw arguments.
#    The following switch/default remains byte-for-byte semantically equivalent:
#    opcode 7 still falls through to the existing generic warning + KErrNone.
# -----------------------------------------------------------------------------
eik_anchor = "        switch (ctx->msg->function) {\n"
if eik.count(eik_anchor) != 1:
    raise SystemExit(f"MENUUI6: expected one EikAppUi switch anchor, found {eik.count(eik_anchor)}")

eik_inject = r'''        if (ctx->msg->function == eik_app_ui_resolve_error) {
            auto *menuui6_client_thr = ctx->msg->own_thr;
            auto *menuui6_client_pr = menuui6_client_thr ? menuui6_client_thr->owning_process() : nullptr;
            std::uint32_t menuui6_client_uid = 0;
            std::string menuui6_client_process = "<none>";
            std::string menuui6_client_thread = "<none>";
            if (menuui6_client_pr) {
                const auto menuui6_client_uids = menuui6_client_pr->get_uid_type();
                menuui6_client_uid = static_cast<std::uint32_t>(std::get<2>(menuui6_client_uids));
                menuui6_client_process = menuui6_client_pr->name();
            }
            if (menuui6_client_thr) {
                menuui6_client_thread = menuui6_client_thr->name();
            }

            const std::int32_t menuui6_error_code = static_cast<std::int32_t>(ctx->msg->args.args[1]);
            const std::uint32_t menuui6_app_uid = static_cast<std::uint32_t>(ctx->msg->args.args[2]);
            LOG_WARN(SERVICE_UI,
                "SYMBIAN-SYSTEMAPPS1 MENUUI6 EIK_RESOLVE_ERROR: server={} opcode=0x{:X} client_process={} client_uid=0x{:08X} client_thread={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} int1_error={} int2_uid=0x{:08X}",
                get_eik_app_ui_server_name_by_epocver(ctx->sys->get_symbian_version_use()),
                ctx->msg->function, menuui6_client_process, menuui6_client_uid, menuui6_client_thread,
                static_cast<std::uint32_t>(ctx->msg->args.flag),
                static_cast<std::uint32_t>(ctx->msg->args.args[0]), static_cast<std::uint32_t>(ctx->msg->args.args[1]),
                static_cast<std::uint32_t>(ctx->msg->args.args[2]), static_cast<std::uint32_t>(ctx->msg->args.args[3]),
                menuui6_error_code, menuui6_app_uid);
        }

'''
eik = eik.replace(eik_anchor, eik_inject + eik_anchor, 1)

# -----------------------------------------------------------------------------
# 4) Trace HLE negative completions delivered to Menu at the central HLE
#    ipc_context::complete path. The request status write/signal logic below is
#    not changed.
# -----------------------------------------------------------------------------
ctx_anchor = "        void ipc_context::complete(int res) {\n            if (msg->request_sts) {"
if ctx.count(ctx_anchor) != 1:
    raise SystemExit(f"MENUUI6: expected one ipc_context::complete anchor, found {ctx.count(ctx_anchor)}")

ctx_inject = r'''        void ipc_context::complete(int res) {
            if ((res < 0) && msg && msg->own_thr) {
                kernel::thread *menuui6_client_thr = msg->own_thr;
                kernel::process *menuui6_client_pr = menuui6_client_thr->owning_process();
                if (menuui6_client_pr) {
                    const auto menuui6_client_uids = menuui6_client_pr->get_uid_type();
                    const std::uint32_t menuui6_client_uid = static_cast<std::uint32_t>(std::get<2>(menuui6_client_uids));
                    if (menuui6_client_uid == 0x101F4CD2U) {
                        std::string menuui6_server_name = "<no-session>";
                        if (msg->msg_session && !msg->msg_session->is_server_terminated()
                            && msg->msg_session->get_server()) {
                            menuui6_server_name = msg->msg_session->get_server()->name();
                        }

                        kernel_system *menuui6_kern = sys->get_kernel_system();
                        kernel::thread *menuui6_current_thr = menuui6_kern->crr_thread();
                        kernel::process *menuui6_current_pr = menuui6_kern->crr_process();
                        std::string menuui6_current_process = menuui6_current_pr ? menuui6_current_pr->name() : "<none>";
                        std::string menuui6_current_thread = menuui6_current_thr ? menuui6_current_thr->name() : "<none>";

                        LOG_WARN(SERVICE_TRACK,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=HLE server={} opcode={} result={} msg_id={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} client_process={} client_uid=0x{:08X} client_thread={} current_process={} current_thread={}",
                            menuui6_server_name, msg->function, res, msg->id,
                            static_cast<std::uint32_t>(msg->args.flag),
                            static_cast<std::uint32_t>(msg->args.args[0]), static_cast<std::uint32_t>(msg->args.args[1]),
                            static_cast<std::uint32_t>(msg->args.args[2]), static_cast<std::uint32_t>(msg->args.args[3]),
                            menuui6_client_pr->name(), menuui6_client_uid, menuui6_client_thr->name(),
                            menuui6_current_process, menuui6_current_thread);
                    }
                }
            }

            if (msg->request_sts) {'''
ctx = ctx.replace(ctx_anchor, ctx_inject, 1)

# common/log.h is normally transitively available, but context.cpp did not
# previously log. Add an explicit include so this diagnostic does not rely on
# incidental include order.
if "#include <common/log.h>" not in ctx:
    include_anchor = "#include <kernel/kernel.h>\n"
    if include_anchor not in ctx:
        raise SystemExit("MENUUI6: context.cpp kernel include anchor not found")
    ctx = ctx.replace(include_anchor, "#include <common/log.h>\n" + include_anchor, 1)

svc_path.write_text(svc, encoding="utf-8")
eik_path.write_text(eik, encoding="utf-8")
ctx_path.write_text(ctx, encoding="utf-8")

# Post-write diagnostics and semantic guards.
svc_check = svc_path.read_text(encoding="utf-8")
eik_check = eik_path.read_text(encoding="utf-8")
ctx_check = ctx_path.read_text(encoding="utf-8")
for marker in markers:
    combined = svc_check + eik_check + ctx_check
    if marker not in combined:
        raise SystemExit("MENUUI6: marker verification failed: " + marker)

for preserved in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 LEAVE ENTER:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
    "kern->call_ipc_complete_callbacks(msg, val);",
]:
    if preserved not in svc_check:
        raise SystemExit("MENUUI6: preserved svc behavior/marker missing after patch: " + preserved)

if "Unimplemented app ui session opcode 0x{:X}" not in eik_check or "ctx->complete(epoc::error_none);" not in eik_check:
    raise SystemExit("MENUUI6: EikAppUi generic opcode-7 semantics changed unexpectedly")
if "(msg->request_sts.get(msg->own_thr->owning_process()))->set(res, kern->is_eka1());" not in ctx_check:
    raise SystemExit("MENUUI6: ipc_context completion write semantics changed unexpectedly")

if svc_check.count("SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:") != 1:
    raise SystemExit("MENUUI6: LEAVE_NEG1 marker count invalid")
if svc_check.count("SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC:") != 1:
    raise SystemExit("MENUUI6: LLE NEGIPC marker count invalid")
if ctx_check.count("SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC:") != 1:
    raise SystemExit("MENUUI6: HLE NEGIPC marker count invalid")
if eik_check.count("SYMBIAN-SYSTEMAPPS1 MENUUI6 EIK_RESOLVE_ERROR:") != 1:
    raise SystemExit("MENUUI6: EIK_RESOLVE_ERROR marker count invalid")

print("MENUUI6 ERRORORIGINTRACE1 patch applied (diagnostic-only)")
