#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui19_activeobj1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI19 ACTIVEOBJ1: required source missing: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT:",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI19 ACTIVEOBJ1: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_TRACK:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_STATE:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_QUEUE:": 1,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI19 ACTIVEOBJ1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI19 ACTIVEOBJ1: partial prior patch detected")

behavior_tokens = [
    "status->set(val, kern->is_eka1());",
    "msg->own_thr->signal_request();",
    "kern->crr_thread()->wait_for_any_request();",
    "kern->call_ipc_complete_callbacks(msg, val);",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

# Make the existing guest ActiveScheduler/ActiveObject layouts available only
# for diagnostics. This does not change guest memory or scheduler behavior.
include_anchor = "#include <utils/handle.h>\n"
include_new = "#include <utils/handle.h>\n#include <utils/guest/actsched.h>\n#include <cstddef>\n"
if svc.count(include_anchor) != 1:
    raise SystemExit(
        f"MENUUI19 ACTIVEOBJ1: include anchor count={svc.count(include_anchor)}"
    )
svc = svc.replace(include_anchor, include_new, 1)

local_data_anchor = '''    static eka2l1::kernel::thread_local_data *current_local_data(kernel_system *kern) {
        return kern->crr_thread()->get_local_data();
    }
'''
if svc.count(local_data_anchor) != 1:
    raise SystemExit(
        f"MENUUI19 ACTIVEOBJ1: current_local_data anchor count={svc.count(local_data_anchor)}"
    )

helper = r'''

    // MENUUI19 ACTIVEOBJ1: host-side diagnostic state only. It remembers the
    // most recent Menu EAlfGetPointerEvent request status so the next
    // WaitForAnyRequest SVC can inspect the same CActive object.
    static std::uint32_t menuui19_tracked_status = 0;
    static std::uint32_t menuui19_tracked_msg_id = 0;

    static void menuui19_log_active_object(kernel_system *kern, kernel::process *pr,
        kernel::thread *thr, const std::uint32_t status_addr, const char *stage) {
        if (!kern || !pr || !thr || status_addr == 0) {
            return;
        }

        kernel::thread_local_data *menuui19_tld = thr->get_local_data();
        const std::uint32_t menuui19_sched_addr =
            menuui19_tld ? menuui19_tld->scheduler.ptr_address() : 0U;
        utils::active_scheduler *menuui19_sched = nullptr;
        if (menuui19_tld && menuui19_sched_addr != 0U) {
            menuui19_sched = menuui19_tld->scheduler.cast<utils::active_scheduler>().get(pr);
        }

        const std::uint32_t menuui19_status_offset =
            static_cast<std::uint32_t>(offsetof(utils::active_object, sts_));
        const std::uint32_t menuui19_ao_addr =
            (status_addr >= menuui19_status_offset)
                ? (status_addr - menuui19_status_offset)
                : 0U;
        eka2l1::ptr<utils::active_object> menuui19_ao_ptr(menuui19_ao_addr);
        utils::active_object *menuui19_ao =
            menuui19_ao_addr ? menuui19_ao_ptr.get(pr) : nullptr;

        std::int32_t menuui19_found_index = -1;
        std::int32_t menuui19_queue_entries = 0;
        std::int32_t menuui19_ready_count = 0;
        std::int32_t menuui19_walk_invalid = 0;
        std::uint32_t menuui19_head_addr = 0;
        std::uint32_t menuui19_head_next = 0;
        std::uint32_t menuui19_head_prev = 0;
        std::int32_t menuui19_link_offset = 0;

        if (menuui19_sched) {
            menuui19_head_addr = menuui19_sched_addr
                + static_cast<std::uint32_t>(offsetof(utils::active_scheduler, act_queue_))
                + static_cast<std::uint32_t>(offsetof(utils::pri_queue, head_));
            menuui19_head_next = menuui19_sched->act_queue_.head_.next_.ptr_address();
            menuui19_head_prev = menuui19_sched->act_queue_.head_.prev_.ptr_address();
            menuui19_link_offset = menuui19_sched->act_queue_.offset_to_link_;

            eka2l1::ptr<utils::double_queue_link> menuui19_link =
                menuui19_sched->act_queue_.head_.next_;
            if (menuui19_link.ptr_address() != 0U
                && menuui19_link.ptr_address() != menuui19_head_addr
                && menuui19_link_offset > 0 && menuui19_link_offset < 0x100) {
                for (std::int32_t menuui19_i = 0; menuui19_i < 64; ++menuui19_i) {
                    utils::double_queue_link *menuui19_real_link = menuui19_link.get(pr);
                    if (!menuui19_real_link) {
                        menuui19_walk_invalid = 1;
                        break;
                    }

                    eka2l1::ptr<utils::active_object> menuui19_obj_ptr =
                        (menuui19_link + (-menuui19_link_offset)).cast<utils::active_object>();
                    utils::active_object *menuui19_obj = menuui19_obj_ptr.get(pr);
                    if (!menuui19_obj) {
                        menuui19_walk_invalid = 1;
                        break;
                    }

                    const bool menuui19_ready =
                        (menuui19_obj->sts_.status != epoc::status_pending)
                        && ((menuui19_obj->sts_.flags & epoc::request_status::active) != 0);
                    if (menuui19_ready) {
                        ++menuui19_ready_count;
                    }
                    if (menuui19_obj_ptr.ptr_address() == menuui19_ao_addr) {
                        menuui19_found_index = menuui19_i;
                    }

                    if (menuui19_ready || menuui19_obj_ptr.ptr_address() == menuui19_ao_addr) {
                        LOG_WARN(KERNEL,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_QUEUE: stage={} index={} link=0x{:08X} ao=0x{:08X} vtable=0x{:08X} status_ptr=0x{:08X} status={} flags=0x{:08X} ready={} prev=0x{:08X} next=0x{:08X}",
                            stage, menuui19_i, menuui19_link.ptr_address(),
                            menuui19_obj_ptr.ptr_address(), menuui19_obj->vtable_,
                            menuui19_obj_ptr.ptr_address() + menuui19_status_offset,
                            menuui19_obj->sts_.status,
                            static_cast<std::uint32_t>(menuui19_obj->sts_.flags),
                            menuui19_ready ? 1 : 0,
                            menuui19_obj->link_.prev_.ptr_address(),
                            menuui19_obj->link_.next_.ptr_address());
                    }

                    ++menuui19_queue_entries;
                    if (menuui19_link.ptr_address() == menuui19_head_prev) {
                        break;
                    }
                    menuui19_link = menuui19_real_link->next_;
                    if (menuui19_link.ptr_address() == 0U
                        || menuui19_link.ptr_address() == menuui19_head_addr) {
                        break;
                    }
                }
            }
        }

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_STATE: stage={} tracked_msg_id={} process={} thread={} status_ptr=0x{:08X} ao=0x{:08X} ao_valid={} vtable=0x{:08X} status={} flags=0x{:08X} link_prev=0x{:08X} link_next=0x{:08X} scheduler=0x{:08X} scheduler_valid={} head=0x{:08X} head_next=0x{:08X} head_prev=0x{:08X} link_offset={} queue_entries={} ready_count={} found_index={} walk_invalid={} request_count={}",
            stage, menuui19_tracked_msg_id, pr->name(), thr->name(), status_addr,
            menuui19_ao_addr, menuui19_ao ? 1 : 0,
            menuui19_ao ? menuui19_ao->vtable_ : 0U,
            menuui19_ao ? menuui19_ao->sts_.status : static_cast<std::int32_t>(0x7FFFFFFF),
            menuui19_ao ? static_cast<std::uint32_t>(menuui19_ao->sts_.flags) : 0xFFFFFFFFU,
            menuui19_ao ? menuui19_ao->link_.prev_.ptr_address() : 0U,
            menuui19_ao ? menuui19_ao->link_.next_.ptr_address() : 0U,
            menuui19_sched_addr, menuui19_sched ? 1 : 0,
            menuui19_head_addr, menuui19_head_next, menuui19_head_prev,
            menuui19_link_offset, menuui19_queue_entries, menuui19_ready_count,
            menuui19_found_index, menuui19_walk_invalid, thr->request_count());
    }
'''
svc = svc.replace(local_data_anchor, local_data_anchor + helper, 1)

# 1) Immediately after MENUUI18 proves signal_request() completed, remember the
# exact opcode-7 status and inspect its active object + current scheduler queue.
complete_sig = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {\n"
complete_pos = svc.find(complete_sig)
if svc.count(complete_sig) != 1 or complete_pos < 0:
    raise SystemExit(
        f"MENUUI19 ACTIVEOBJ1: message_complete signature count={svc.count(complete_sig)}"
    )
complete_end = svc.find("\n    BRIDGE_FUNC(", complete_pos + len(complete_sig))
if complete_end < 0:
    raise SystemExit("MENUUI19 ACTIVEOBJ1: cannot find end of message_complete")
complete = svc[complete_pos:complete_end]

after_signal_anchor = r'''            if (menuui17_complete_match) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL: stage=after_signal msg_id={} client_thread={} request_count={} signal_count=1",
                    msg->id, msg->own_thr->name(), msg->own_thr->request_count());
            }
'''
if complete.count(after_signal_anchor) != 1:
    raise SystemExit(
        "MENUUI19 ACTIVEOBJ1: MENUUI18 after-signal anchor count="
        + str(complete.count(after_signal_anchor))
    )
track_block = r'''            if (menuui17_complete_match) {
                menuui19_tracked_status = msg->request_sts.ptr_address();
                menuui19_tracked_msg_id = msg->id;
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_TRACK: stage=after_signal msg_id={} status_ptr=0x{:08X} client_process={} client_thread={} request_count={}",
                    msg->id, menuui19_tracked_status,
                    menuui17_complete_client_pr ? menuui17_complete_client_pr->name() : std::string("<null>"),
                    msg->own_thr ? msg->own_thr->name() : std::string("<null>"),
                    msg->own_thr ? msg->own_thr->request_count() : 0);
                menuui19_log_active_object(kern, menuui17_complete_client_pr,
                    msg->own_thr, menuui19_tracked_status, "after_signal");
            }
'''
complete = complete.replace(after_signal_anchor, after_signal_anchor + track_block, 1)
svc = svc[:complete_pos] + complete + svc[complete_end:]

# 2) Inspect the exact tracked AO immediately before and immediately after the
# host-side WaitForAnyRequest call. The latter is still inside the SVC bridge;
# it records semaphore state after wait() mutates it, not a second guest resume.
wait_sig = "    BRIDGE_FUNC(void, wait_for_any_request) {\n"
wait_pos = svc.find(wait_sig)
if svc.count(wait_sig) != 1 or wait_pos < 0:
    raise SystemExit(
        f"MENUUI19 ACTIVEOBJ1: wait_for_any_request signature count={svc.count(wait_sig)}"
    )
wait_end = svc.find("\n    BRIDGE_FUNC(", wait_pos + len(wait_sig))
if wait_end < 0:
    raise SystemExit("MENUUI19 ACTIVEOBJ1: cannot find end of wait_for_any_request")
wait_body = svc[wait_pos:wait_end]
wait_call = "        kern->crr_thread()->wait_for_any_request();\n"
if wait_body.count(wait_call) != 1:
    raise SystemExit(
        f"MENUUI19 ACTIVEOBJ1: wait call count={wait_body.count(wait_call)}"
    )
wait_probe_before = r'''        if (menuui18_wait_match && menuui19_tracked_status != 0U) {
            menuui19_log_active_object(kern, menuui18_wait_pr,
                menuui18_wait_thr, menuui19_tracked_status, "before_wait");
        }
'''
wait_probe_after = r'''        if (menuui18_wait_match && menuui19_tracked_status != 0U) {
            menuui19_log_active_object(kern, menuui18_wait_pr,
                menuui18_wait_thr, menuui19_tracked_status, "after_wait_call");
        }
'''
wait_body = wait_body.replace(
    wait_call, wait_probe_before + wait_call + wait_probe_after, 1
)
svc = svc[:wait_pos] + wait_body + svc[wait_end:]

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI19 ACTIVEOBJ1: marker postcondition failed: {marker} "
            f"count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI19 ACTIVEOBJ1: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI19 ACTIVEOBJ1 diagnostic-only traces applied")
print("MENUUI19 target: completed ALF pointer CActive object -> scheduler queue -> WaitForAnyRequest")
print("MENUUI19: no guest AO flags, queue links, scheduler, IPC, semaphore, pointer or focus state changed")
