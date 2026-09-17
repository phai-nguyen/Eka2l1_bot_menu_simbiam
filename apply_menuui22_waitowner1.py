#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui22_waitowner1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI22 WAITOWNER1: required source missing: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_TRACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_STATE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_HEAD:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 VTABLE:",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI22 WAITOWNER1: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_SEND:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI22 ALF_WAKE_CONTEXT:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_FRAME:": 1,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI22 WAITOWNER1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI22 WAITOWNER1: partial prior patch detected")

behavior_tokens = [
    "status->set(val, kern->is_eka1());",
    "msg->own_thr->signal_request();",
    "kern->crr_thread()->wait_for_any_request();",
    "kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());",
    "kern->call_ipc_complete_callbacks(msg, val);",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

# Diagnostic-only host bookkeeping.  It never mutates guest memory, CPU
# registers, request status, semaphore counts, scheduler queues, IPC payloads,
# pointer state, or focus state.
forward_decl = '''    static codeseg_ptr get_codeseg_from_addr(kernel_system *kern,\n        kernel::process *pr, const std::uint32_t addr, const bool ep);\n'''
if svc.count(forward_decl) != 1:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: get_codeseg forward declaration count={svc.count(forward_decl)}"
    )

helper = r'''

    static std::uint32_t menuui22_sync_seq = 0U;
    static std::uint32_t menuui22_sync_status = 0U;
    static std::int32_t menuui22_sync_opcode = 0;
    static std::uint32_t menuui22_sync_server_hash = 0U;
    static bool menuui22_sync_active = false;
    static std::uint32_t menuui22_alf_msg_id = 0U;
    static std::int32_t menuui22_post_alf_wait_budget = 0;
    static std::uint32_t menuui22_wait_seq = 0U;

    static std::uint32_t menuui22_hash_server(const std::string &name) {
        std::uint32_t hash = 2166136261U;
        for (const unsigned char ch : name) {
            hash ^= static_cast<std::uint32_t>(ch);
            hash *= 16777619U;
        }
        return hash;
    }

    static bool menuui22_is_menu_process(kernel::process *pr) {
        if (!pr) {
            return false;
        }
        const auto uids = pr->get_uid_type();
        return static_cast<std::uint32_t>(std::get<2>(uids)) == 0x101F4CD2U;
    }

    static void menuui22_log_wait_frame(kernel_system *kern, kernel::process *pr,
        const char *stage, const std::int32_t index, const std::uint32_t raw) {
        if (!kern || !pr || raw < 0x10000U) {
            return;
        }
        const std::uint32_t addr = raw & ~1U;
        codeseg_ptr seg = get_codeseg_from_addr(kern, pr, addr, false);
        if (!seg) {
            return;
        }
        const std::string module = common::ucs2_to_utf8(seg->get_full_path());
        const std::uint32_t base = seg->get_code_run_addr(pr);
        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_FRAME: stage={} wait_seq={} index={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
            stage, menuui22_wait_seq, index, raw, module, base, addr - base);
    }

    static void menuui22_log_wait_owner(kernel_system *kern,
        kernel::process *pr, kernel::thread *thr, const char *stage,
        const bool consume_budget) {
        if (!kern || !pr || !thr || !menuui22_is_menu_process(pr)
            || menuui22_alf_msg_id == 0U
            || menuui22_post_alf_wait_budget <= 0) {
            return;
        }

        auto *cpu = kern->get_cpu();
        const std::uint32_t pc = cpu ? cpu->get_pc() : 0U;
        const std::uint32_t lr = cpu ? cpu->get_reg(14) : 0U;
        const std::uint32_t sp = cpu ? cpu->get_reg(13) : 0U;

        std::uint32_t ao_addr = 0U;
        std::int32_t ao_status = static_cast<std::int32_t>(0x7FFFFFFF);
        std::uint32_t ao_flags = 0xFFFFFFFFU;
        std::int32_t ao_ready = -1;
        if (menuui19_tracked_status != 0U) {
            const std::uint32_t status_offset =
                static_cast<std::uint32_t>(offsetof(utils::active_object, sts_));
            if (menuui19_tracked_status >= status_offset) {
                ao_addr = menuui19_tracked_status - status_offset;
                utils::active_object *ao =
                    eka2l1::ptr<utils::active_object>(ao_addr).get(pr);
                if (ao) {
                    ao_status = ao->sts_.status;
                    ao_flags = static_cast<std::uint32_t>(ao->sts_.flags);
                    ao_ready = ao_status != epoc::request_status::pending_status
                        && ((ao_flags & epoc::request_status::active) != 0U) ? 1 : 0;
                }
            }
        }

        if (!consume_budget) {
            ++menuui22_wait_seq;
        }

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER: stage={} wait_seq={} alf_msg_id={} budget={} sync_active={} sync_seq={} sync_status=0x{:08X} sync_opcode={} sync_server_hash=0x{:08X} request_count={} tracked_status=0x{:08X} ao=0x{:08X} ao_status={} ao_flags=0x{:08X} ao_ready={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
            stage, menuui22_wait_seq, menuui22_alf_msg_id,
            menuui22_post_alf_wait_budget, menuui22_sync_active ? 1 : 0,
            menuui22_sync_seq, menuui22_sync_status, menuui22_sync_opcode,
            menuui22_sync_server_hash, thr->request_count(),
            menuui19_tracked_status, ao_addr, ao_status, ao_flags, ao_ready,
            pc, lr, sp);

        if (cpu) {
            menuui22_log_wait_frame(kern, pr, stage, -2, pc);
            menuui22_log_wait_frame(kern, pr, stage, -1, lr);
        }
        if (sp != 0U) {
            std::int32_t emitted = 0;
            for (std::int32_t i = 0; i < 32 && emitted < 10; ++i) {
                const std::uint32_t slot_addr =
                    sp + static_cast<std::uint32_t>(i * sizeof(std::uint32_t));
                if (slot_addr < sp) {
                    break;
                }
                const std::uint32_t *slot =
                    eka2l1::ptr<std::uint32_t>(slot_addr).get(pr);
                if (!slot) {
                    break;
                }
                const std::uint32_t raw = *slot;
                if (raw < 0x10000U) {
                    continue;
                }
                const std::uint32_t addr = raw & ~1U;
                if (get_codeseg_from_addr(kern, pr, addr, false)) {
                    menuui22_log_wait_frame(kern, pr, stage, i, raw);
                    ++emitted;
                }
            }
        }

        if (consume_budget && menuui22_post_alf_wait_budget > 0) {
            --menuui22_post_alf_wait_budget;
        }
    }
'''
svc = svc.replace(forward_decl, forward_decl + helper, 1)

# 1) Tag every synchronous Menu IPC immediately before the original IPC send
# callback.  The existing MENUUI7 trace provides the textual server name; the
# stable hash lets WAIT_OWNER correlate that exact send without storing a
# std::string in diagnostic state.
send_call = (
    "        kern->call_ipc_send_callbacks(server_name, ord, arg, "
    "status.ptr_address(), kern->crr_thread());\n"
)
if svc.count(send_call) != 1:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: IPC send callback count={svc.count(send_call)}"
    )
sync_send = r'''        if (sync) {
            kernel::process *menuui22_send_pr = kern->crr_process();
            kernel::thread *menuui22_send_thr = kern->crr_thread();
            if (menuui22_is_menu_process(menuui22_send_pr) && menuui22_send_thr) {
                ++menuui22_sync_seq;
                menuui22_sync_status = status.ptr_address();
                menuui22_sync_opcode = ord;
                menuui22_sync_server_hash = menuui22_hash_server(server_name);
                menuui22_sync_active = true;
                auto *menuui22_send_cpu = kern->get_cpu();
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_SEND: sync_seq={} server={} server_hash=0x{:08X} opcode={} status=0x{:08X} request_count={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                    menuui22_sync_seq, server_name, menuui22_sync_server_hash,
                    menuui22_sync_opcode, menuui22_sync_status,
                    menuui22_send_thr->request_count(),
                    menuui22_send_cpu ? menuui22_send_cpu->get_pc() : 0U,
                    menuui22_send_cpu ? menuui22_send_cpu->get_reg(14) : 0U,
                    menuui22_send_cpu ? menuui22_send_cpu->get_reg(13) : 0U);
            }
        }

'''
svc = svc.replace(send_call, sync_send + send_call, 1)

# 2) Observe completions after the original request semaphore signal.  A
# matching sync-status completion closes the diagnostic sync owner.  For the
# tracked ALF opcode-7 completion, freeze a short post-completion wait window.
complete_sig = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n"
complete_pos = svc.find(complete_sig)
if svc.count(complete_sig) != 1 or complete_pos < 0:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: message_complete signature count={svc.count(complete_sig)}"
    )
complete_end = svc.find("\n    BRIDGE_FUNC(", complete_pos + len(complete_sig))
if complete_end < 0:
    raise SystemExit("MENUUI22 WAITOWNER1: cannot find end of message_complete")
complete = svc[complete_pos:complete_end]
signal_line = "            msg->own_thr->signal_request();\n"
if complete.count(signal_line) != 1:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: signal_request line count={complete.count(signal_line)}"
    )
complete_probe = r'''            if (msg->own_thr && menuui22_sync_active
                && msg->request_sts.ptr_address() == menuui22_sync_status
                && menuui22_is_menu_process(msg->own_thr->owning_process())) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE: sync_seq={} msg_id={} completion={} status=0x{:08X} opcode={} server_hash=0x{:08X} request_count={} stage=after_signal",
                    menuui22_sync_seq, msg->id, val, menuui22_sync_status,
                    menuui22_sync_opcode, menuui22_sync_server_hash,
                    msg->own_thr->request_count());
                menuui22_sync_active = false;
            }
            if (menuui17_complete_match) {
                menuui22_alf_msg_id = msg->id;
                menuui22_post_alf_wait_budget = 6;
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI22 ALF_WAKE_CONTEXT: msg_id={} completion={} status=0x{:08X} sync_active={} sync_seq={} sync_status=0x{:08X} sync_opcode={} sync_server_hash=0x{:08X} request_count={} stage=after_signal",
                    msg->id, val, msg->request_sts.ptr_address(),
                    menuui22_sync_active ? 1 : 0, menuui22_sync_seq,
                    menuui22_sync_status, menuui22_sync_opcode,
                    menuui22_sync_server_hash, msg->own_thr->request_count());
            }
'''
complete = complete.replace(signal_line, signal_line + complete_probe, 1)
svc = svc[:complete_pos] + complete + svc[complete_end:]

# 3) Log the exact owner context immediately around the original host-side
# WaitForAnyRequest call.  Existing MENUUI18/19/20/21 probes remain untouched.
wait_sig = "    BRIDGE_FUNC(void, wait_for_any_request) {\n"
wait_pos = svc.find(wait_sig)
if svc.count(wait_sig) != 1 or wait_pos < 0:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: wait_for_any_request signature count={svc.count(wait_sig)}"
    )
wait_end = svc.find("\n    BRIDGE_FUNC(", wait_pos + len(wait_sig))
if wait_end < 0:
    raise SystemExit("MENUUI22 WAITOWNER1: cannot find end of wait_for_any_request")
wait_body = svc[wait_pos:wait_end]
wait_call = "        kern->crr_thread()->wait_for_any_request();\n"
if wait_body.count(wait_call) != 1:
    raise SystemExit(
        f"MENUUI22 WAITOWNER1: wait call count={wait_body.count(wait_call)}"
    )
wait_wrapped = r'''        menuui22_log_wait_owner(kern, menuui18_wait_pr,
            menuui18_wait_thr, "enter", false);
        kern->crr_thread()->wait_for_any_request();
        menuui22_log_wait_owner(kern, menuui18_wait_pr,
            menuui18_wait_thr, "exit", true);
'''
wait_body = wait_body.replace(wait_call, wait_wrapped, 1)
svc = svc[:wait_pos] + wait_body + svc[wait_end:]

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI22 WAITOWNER1: marker postcondition failed: {marker} "
            f"count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI22 WAITOWNER1: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI22 WAITOWNER1 diagnostic-only traces applied")
print("MENUUI22 target: synchronous IPC ownership across ALF completion and post-completion WaitForAnyRequest")
print("MENUUI22: no guest memory, CPU register, AO, queue, scheduler, semaphore, IPC, pointer or focus state changed")
