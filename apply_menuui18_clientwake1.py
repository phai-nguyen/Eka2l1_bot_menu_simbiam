#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui18_clientwake1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI18 CLIENTWAKE1: required source missing: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI18 CLIENTWAKE1: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS:": 2,
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL:": 2,
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT:": 2,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI18 CLIENTWAKE1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI18 CLIENTWAKE1: partial prior patch detected")

behavior_tokens = [
    "status->set(val, kern->is_eka1());",
    "msg->own_thr->signal_request();",
    "kern->crr_thread()->wait_for_any_request();",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

# 1) Trace the request-status transition and request semaphore signal only for
#    Menu's EAlfGetPointerEvent (opcode 7) completion already identified by
#    MENUUI17's function-scoped menuui17_complete_match predicate.
complete_sig = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n"
complete_pos = svc.find(complete_sig)
if svc.count(complete_sig) != 1 or complete_pos < 0:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: message_complete signature count={svc.count(complete_sig)}"
    )
complete_end = svc.find("\n    BRIDGE_FUNC(", complete_pos + len(complete_sig))
if complete_end < 0:
    raise SystemExit("MENUUI18 CLIENTWAKE1: cannot find end of message_complete")
complete = svc[complete_pos:complete_end]

if "menuui17_complete_match" not in complete:
    raise SystemExit("MENUUI18 CLIENTWAKE1: MENUUI17 completion predicate missing")

status_decl = (
    "            epoc::request_status *status = "
    "msg->request_sts.get(msg->own_thr->owning_process());\n"
)
if complete.count(status_decl) != 1:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: status declaration count={complete.count(status_decl)}"
    )

status_before = r'''            if (menuui17_complete_match) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS: stage=before_set msg_id={} completion={} status_ptr=0x{:08X} status_value={} status_flags=0x{:08X} request_count={}",
                    msg->id, val, msg->request_sts.ptr_address(),
                    status ? status->status : static_cast<std::int32_t>(0x7FFFFFFF),
                    status ? static_cast<std::uint32_t>(status->flags) : 0xFFFFFFFFU,
                    msg->own_thr->request_count());
            }
'''
complete = complete.replace(status_decl, status_decl + status_before, 1)

set_block = (
    "            if (status)\n"
    "                status->set(val, kern->is_eka1());\n"
)
if complete.count(set_block) != 1:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: status set block count={complete.count(set_block)}"
    )
status_after = r'''            if (menuui17_complete_match) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS: stage=after_set msg_id={} completion={} status_ptr=0x{:08X} status_value={} status_flags=0x{:08X} request_count={}",
                    msg->id, val, msg->request_sts.ptr_address(),
                    status ? status->status : static_cast<std::int32_t>(0x7FFFFFFF),
                    status ? static_cast<std::uint32_t>(status->flags) : 0xFFFFFFFFU,
                    msg->own_thr->request_count());
            }
'''
complete = complete.replace(set_block, set_block + status_after, 1)

signal_line = "            msg->own_thr->signal_request();\n"
if complete.count(signal_line) != 1:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: signal_request line count={complete.count(signal_line)}"
    )
signal_trace = r'''            if (menuui17_complete_match) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL: stage=before_signal msg_id={} client_thread={} request_count={} signal_count=1",
                    msg->id, msg->own_thr->name(), msg->own_thr->request_count());
            }
'''
signal_after = r'''            if (menuui17_complete_match) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL: stage=after_signal msg_id={} client_thread={} request_count={} signal_count=1",
                    msg->id, msg->own_thr->name(), msg->own_thr->request_count());
            }
'''
complete = complete.replace(
    signal_line, signal_trace + signal_line + signal_after, 1
)
svc = svc[:complete_pos] + complete + svc[complete_end:]

# 2) Trace User::WaitForAnyRequest at the SVC boundary for the Menu process.
#    This does not alter semaphore behavior; the original call remains exactly once.
wait_sig = "    BRIDGE_FUNC(void, wait_for_any_request) {\n"
wait_pos = svc.find(wait_sig)
if svc.count(wait_sig) != 1 or wait_pos < 0:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: wait_for_any_request signature count={svc.count(wait_sig)}"
    )
wait_end = svc.find("\n    BRIDGE_FUNC(", wait_pos + len(wait_sig))
if wait_end < 0:
    raise SystemExit("MENUUI18 CLIENTWAKE1: cannot find end of wait_for_any_request")
wait_body = svc[wait_pos:wait_end]
wait_call = "        kern->crr_thread()->wait_for_any_request();\n"
if wait_body.count(wait_call) != 1:
    raise SystemExit(
        f"MENUUI18 CLIENTWAKE1: wait call count={wait_body.count(wait_call)}"
    )

wait_before = r'''        kernel::process *menuui18_wait_pr = kern->crr_process();
        kernel::thread *menuui18_wait_thr = kern->crr_thread();
        std::uint32_t menuui18_wait_uid3 = 0;
        if (menuui18_wait_pr) {
            const auto menuui18_wait_uids = menuui18_wait_pr->get_uid_type();
            menuui18_wait_uid3 =
                static_cast<std::uint32_t>(std::get<2>(menuui18_wait_uids));
        }
        const bool menuui18_wait_match =
            menuui18_wait_pr && menuui18_wait_thr
            && menuui18_wait_uid3 == 0x101F4CD2U;

        if (menuui18_wait_match) {
            auto *menuui18_wait_cpu = kern->get_cpu();
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT: stage=before_wait process={} thread={} uid=0x{:08X} request_count={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                menuui18_wait_pr->name(), menuui18_wait_thr->name(),
                menuui18_wait_uid3, menuui18_wait_thr->request_count(),
                menuui18_wait_cpu ? menuui18_wait_cpu->get_pc() : 0U,
                menuui18_wait_cpu ? menuui18_wait_cpu->get_reg(14) : 0U,
                menuui18_wait_cpu ? menuui18_wait_cpu->get_reg(13) : 0U);
        }
'''
wait_after = r'''
        if (menuui18_wait_match) {
            auto *menuui18_wait_cpu = kern->get_cpu();
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT: stage=after_wait_call process={} thread={} uid=0x{:08X} request_count={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                menuui18_wait_pr->name(), menuui18_wait_thr->name(),
                menuui18_wait_uid3, menuui18_wait_thr->request_count(),
                menuui18_wait_cpu ? menuui18_wait_cpu->get_pc() : 0U,
                menuui18_wait_cpu ? menuui18_wait_cpu->get_reg(14) : 0U,
                menuui18_wait_cpu ? menuui18_wait_cpu->get_reg(13) : 0U);
        }
'''
wait_body = wait_body.replace(
    wait_call, wait_before + wait_call + wait_after, 1
)
svc = svc[:wait_pos] + wait_body + svc[wait_end:]

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI18 CLIENTWAKE1: marker postcondition failed: "
            f"{marker} count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI18 CLIENTWAKE1: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI18 CLIENTWAKE1 diagnostic-only traces applied")
print("MENUUI18 target: ALF opcode 7 completion -> status -> signal -> Menu wait")
print("MENUUI18: no request-status, semaphore, scheduler, IPC, pointer or focus semantics changed")
