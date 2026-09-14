#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui6_errororigintrace1_fix1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
eik_path = up / "src/emu/services/src/ui/eikappui.cpp"
ctx_path = up / "src/emu/services/src/context.cpp"

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
if any(m in svc or m in eik or m in ctx for m in markers):
    raise SystemExit("MENUUI6 FIX1: prior MENUUI6 markers already present; expected clean MENUUI5 input")

for required in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 LEAVE ENTER:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 LEAVE RETURN:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 FRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK:",
    "static codeseg_ptr get_codeseg_from_addr(",
]:
    if required not in svc:
        raise SystemExit("MENUUI6 FIX1: missing svc baseline marker: " + required)
if "Unimplemented app ui session opcode 0x{:X}" not in eik or "ctx->complete(epoc::error_none);" not in eik:
    raise SystemExit("MENUUI6 FIX1: EikAppUi baseline semantics not found")
if "void ipc_context::complete(int res)" not in ctx:
    raise SystemExit("MENUUI6 FIX1: ipc_context::complete not found")

# 1) Deep leave(-1) trace. Keep the original leave path unchanged.
leave_sig = "    BRIDGE_FUNC(eka2l1::ptr<void>, leave_start) {"
start = svc.find(leave_sig)
end = svc.find("\n    BRIDGE_FUNC(", start + len(leave_sig))
if start < 0 or end < 0:
    raise SystemExit("MENUUI6 FIX1: leave_start block not found")
body = svc[start:end]
anchor = "        kernel::thread *thr = kern->crr_thread();\n"
if body.count(anchor) != 1:
    raise SystemExit(f"MENUUI6 FIX1: leave thread anchor count={body.count(anchor)}")
leave_inject = r'''        auto *menuui6_cpu = kern->get_cpu();
        kernel::process *menuui6_pr = kern->crr_process();
        const std::int32_t menuui6_leave_code = menuui6_cpu
            ? static_cast<std::int32_t>(menuui6_cpu->get_reg(0)) : 0;
        if (menuui6_cpu && menuui6_pr && thr && (menuui6_leave_code == epoc::error_not_found)) {
            const std::uint32_t pc = menuui6_cpu->get_pc();
            const std::uint32_t lr = menuui6_cpu->get_reg(14);
            const std::uint32_t sp = menuui6_cpu->get_reg(13);
            const std::uint32_t cpsr = menuui6_cpu->get_cpsr();
            const std::uint32_t trap = current_local_data(kern)->trap_handler.ptr_address();
            const auto uids = menuui6_pr->get_uid_type();
            const std::uint32_t uid3 = static_cast<std::uint32_t>(std::get<2>(uids));
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1: process={} uid=0x{:08X} thread={} leave_code={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} trap=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                menuui6_pr->name(), uid3, thr->name(), menuui6_leave_code, pc, lr, sp, cpsr, trap,
                menuui6_cpu->get_reg(0), menuui6_cpu->get_reg(1), menuui6_cpu->get_reg(2), menuui6_cpu->get_reg(3),
                menuui6_cpu->get_reg(4), menuui6_cpu->get_reg(5), menuui6_cpu->get_reg(6), menuui6_cpu->get_reg(7),
                menuui6_cpu->get_reg(8), menuui6_cpu->get_reg(9), menuui6_cpu->get_reg(10), menuui6_cpu->get_reg(11),
                menuui6_cpu->get_reg(12));
            auto log_addr = [&](const char *kind, std::uint32_t raw) {
                const std::uint32_t addr = raw & ~1U;
                codeseg_ptr seg = get_codeseg_from_addr(kern, menuui6_pr, addr, false);
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(menuui6_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        kind, raw, addr, common::ucs2_to_utf8(seg->get_full_path()), base, addr - base);
                } else {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module=<unresolved>", kind, raw, addr);
                }
            };
            log_addr("pc", pc); log_addr("lr", lr); log_addr("trap", trap);
            for (std::uint32_t i = 0; i < 32; ++i) {
                const std::uint32_t slot_addr = sp + i * sizeof(std::uint32_t);
                if (slot_addr < sp) break;
                const std::uint32_t *slot = eka2l1::ptr<std::uint32_t>(slot_addr).get(menuui6_pr);
                if (!slot) {
                    LOG_WARN(KERNEL, "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} mapped=0 stopping=1", i, slot_addr);
                    break;
                }
                const std::uint32_t value = *slot;
                const std::uint32_t candidate = value & ~1U;
                codeseg_ptr seg = candidate >= 0x10000U ? get_codeseg_from_addr(kern, menuui6_pr, candidate, false) : nullptr;
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(menuui6_pr);
                    LOG_WARN(KERNEL, "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()), base, candidate - base);
                } else {
                    LOG_WARN(KERNEL, "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=0", i, slot_addr, value);
                }
            }
        }

'''
body = body.replace(anchor, anchor + leave_inject, 1)
svc = svc[:start] + body + svc[end:]

# 2) LLE/native negative completion trace to Menu.
lle_anchor = "        kern->call_ipc_complete_callbacks(msg, val);\n        msg->unref();"
if svc.count(lle_anchor) != 1:
    raise SystemExit(f"MENUUI6 FIX1: LLE completion anchor count={svc.count(lle_anchor)}")
lle_inject = r'''        if ((val < 0) && msg && msg->own_thr) {
            kernel::thread *ct = msg->own_thr;
            kernel::process *cp = ct->owning_process();
            if (cp) {
                const auto uids = cp->get_uid_type();
                const std::uint32_t uid3 = static_cast<std::uint32_t>(std::get<2>(uids));
                if (uid3 == 0x101F4CD2U) {
                    std::string sname = "<no-session>";
                    if (msg->msg_session && !msg->msg_session->is_server_terminated() && msg->msg_session->get_server())
                        sname = msg->msg_session->get_server()->name();
                    kernel::thread *st = kern->crr_thread();
                    kernel::process *sp = kern->crr_process();
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=LLE server={} opcode={} result={} msg_id={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} client_process={} client_uid=0x{:08X} client_thread={} server_process={} server_thread={}",
                        sname, msg->function, val, msg->id, static_cast<std::uint32_t>(msg->args.flag),
                        static_cast<std::uint32_t>(msg->args.args[0]), static_cast<std::uint32_t>(msg->args.args[1]),
                        static_cast<std::uint32_t>(msg->args.args[2]), static_cast<std::uint32_t>(msg->args.args[3]),
                        cp->name(), uid3, ct->name(), sp ? sp->name() : "<none>", st ? st->name() : "<none>");
                }
            }
        }

'''
svc = svc.replace(lle_anchor, lle_inject + lle_anchor, 1)

# 3) EikAppUi opcode 7 trace only; preserve generic default completion.
eik_anchor = "        switch (ctx->msg->function) {\n"
if eik.count(eik_anchor) != 1:
    raise SystemExit(f"MENUUI6 FIX1: Eik switch anchor count={eik.count(eik_anchor)}")
eik_inject = r'''        if (ctx->msg->function == eik_app_ui_resolve_error) {
            auto *ct = ctx->msg->own_thr;
            auto *cp = ct ? ct->owning_process() : nullptr;
            std::uint32_t uid3 = 0;
            if (cp) uid3 = static_cast<std::uint32_t>(std::get<2>(cp->get_uid_type()));
            LOG_WARN(SERVICE_UI,
                "SYMBIAN-SYSTEMAPPS1 MENUUI6 EIK_RESOLVE_ERROR: opcode=0x{:X} client_process={} client_uid=0x{:08X} client_thread={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} int1_error={} int2_uid=0x{:08X}",
                ctx->msg->function, cp ? cp->name() : "<none>", uid3, ct ? ct->name() : "<none>",
                static_cast<std::uint32_t>(ctx->msg->args.flag),
                static_cast<std::uint32_t>(ctx->msg->args.args[0]), static_cast<std::uint32_t>(ctx->msg->args.args[1]),
                static_cast<std::uint32_t>(ctx->msg->args.args[2]), static_cast<std::uint32_t>(ctx->msg->args.args[3]),
                static_cast<std::int32_t>(ctx->msg->args.args[1]), static_cast<std::uint32_t>(ctx->msg->args.args[2]));
        }

'''
eik = eik.replace(eik_anchor, eik_inject + eik_anchor, 1)

# 4) HLE completion trace. FIX1 deliberately anchors only on the function
# signature because V10/IPCCTX patches legitimately change the body.
ctx_sig = "        void ipc_context::complete(int res) {\n"
if ctx.count(ctx_sig) != 1:
    raise SystemExit(f"MENUUI6 FIX1: ipc_context::complete signature count={ctx.count(ctx_sig)}")
ctx_inject = r'''            if ((res < 0) && msg && msg->own_thr) {
                kernel::thread *ct = msg->own_thr;
                kernel::process *cp = ct->owning_process();
                if (cp) {
                    const auto uids = cp->get_uid_type();
                    const std::uint32_t uid3 = static_cast<std::uint32_t>(std::get<2>(uids));
                    if (uid3 == 0x101F4CD2U) {
                        std::string sname = "<no-session>";
                        if (msg->msg_session && !msg->msg_session->is_server_terminated() && msg->msg_session->get_server())
                            sname = msg->msg_session->get_server()->name();
                        kernel_system *menuui6_kern = sys->get_kernel_system();
                        kernel::thread *st = menuui6_kern ? menuui6_kern->crr_thread() : nullptr;
                        kernel::process *sp = menuui6_kern ? menuui6_kern->crr_process() : nullptr;
                        LOG_WARN(SERVICE_TRACK,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=HLE server={} opcode={} result={} msg_id={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} client_process={} client_uid=0x{:08X} client_thread={} server_process={} server_thread={}",
                            sname, msg->function, res, msg->id, static_cast<std::uint32_t>(msg->args.flag),
                            static_cast<std::uint32_t>(msg->args.args[0]), static_cast<std::uint32_t>(msg->args.args[1]),
                            static_cast<std::uint32_t>(msg->args.args[2]), static_cast<std::uint32_t>(msg->args.args[3]),
                            cp->name(), uid3, ct->name(), sp ? sp->name() : "<none>", st ? st->name() : "<none>");
                    }
                }
            }

'''
ctx = ctx.replace(ctx_sig, ctx_sig + ctx_inject, 1)

svc_path.write_text(svc, encoding="utf-8")
eik_path.write_text(eik, encoding="utf-8")
ctx_path.write_text(ctx, encoding="utf-8")

check = svc + eik + ctx
for marker in markers:
    if marker not in check:
        raise SystemExit("MENUUI6 FIX1: marker missing after patch: " + marker)
if "Unimplemented app ui session opcode 0x{:X}" not in eik or "ctx->complete(epoc::error_none);" not in eik:
    raise SystemExit("MENUUI6 FIX1: Eik semantics guard failed")
if "kern->call_ipc_complete_callbacks(msg, val);" not in svc:
    raise SystemExit("MENUUI6 FIX1: LLE semantics guard failed")
print("MENUUI6 ERRORORIGINTRACE1 FIX1 patch applied")
