#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui20_activeqdir1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI20 ACTIVEQDIR1: required source missing: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_TRACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_STATE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_QUEUE:",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI20 ACTIVEQDIR1: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_HEAD:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_TARGET:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_BREAK:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR:": 1,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI20 ACTIVEQDIR1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI20 ACTIVEQDIR1: partial prior patch detected")

behavior_tokens = [
    "status->set(val, kern->is_eka1());",
    "msg->own_thr->signal_request();",
    "kern->crr_thread()->wait_for_any_request();",
    "kern->call_ipc_complete_callbacks(msg, val);",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

# Insert a second, direction-correct queue diagnostic alongside MENUUI19.
# MENUUI19 proved forward reachability (head.next -> next). Original Symbian
# ARM CActiveScheduler traverses the opposite chain (head.prev -> prev), so
# MENUUI20 records both directions and validates doubly-linked reciprocity.
helper_tail = '''            menuui19_link_offset, menuui19_queue_entries, menuui19_ready_count,\n            menuui19_found_index, menuui19_walk_invalid, thr->request_count());\n    }\n'''
if svc.count(helper_tail) != 1:
    raise SystemExit(
        f"MENUUI20 ACTIVEQDIR1: MENUUI19 helper tail count={svc.count(helper_tail)}"
    )

helper = r'''

    struct menuui20_walk_result {
        std::int32_t entries = 0;
        std::int32_t ready_count = 0;
        std::int32_t found_index = -1;
        std::int32_t invalid = 0;
        std::int32_t cycle = 0;
        std::int32_t reciprocal_fail = 0;
        std::int32_t first_bad_kind = 0;
        std::uint32_t first_bad_link = 0;
        std::uint32_t first_bad_neighbor = 0;
    };

    static menuui20_walk_result menuui20_walk_activeq(kernel_system *kern,
        kernel::process *pr, const std::uint32_t head_addr,
        const std::uint32_t start_addr, const std::int32_t link_offset,
        const std::uint32_t target_ao_addr, const std::uint32_t status_offset,
        const bool forward, const char *stage) {
        menuui20_walk_result out;
        if (!kern || !pr || head_addr == 0U || start_addr == 0U
            || link_offset <= 0 || link_offset >= 0x100) {
            out.invalid = 1;
            out.first_bad_kind = 3;
            out.first_bad_link = start_addr;
            return out;
        }

        std::uint32_t seen[64] = {};
        std::uint32_t current = start_addr;

        for (std::int32_t i = 0; i < 64; ++i) {
            if (current == head_addr) {
                break;
            }
            if (current == 0U || current < static_cast<std::uint32_t>(link_offset)) {
                out.invalid = 1;
                out.first_bad_kind = 3;
                out.first_bad_link = current;
                break;
            }

            bool duplicate = false;
            for (std::int32_t j = 0; j < i; ++j) {
                if (seen[j] == current) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) {
                out.cycle = 1;
                out.first_bad_kind = 4;
                out.first_bad_link = current;
                break;
            }
            seen[i] = current;

            eka2l1::ptr<utils::double_queue_link> link_ptr(current);
            utils::double_queue_link *link = link_ptr.get(pr);
            if (!link) {
                out.invalid = 1;
                out.first_bad_kind = 3;
                out.first_bad_link = current;
                break;
            }

            const std::uint32_t prev_addr = link->prev_.ptr_address();
            const std::uint32_t next_addr = link->next_.ptr_address();

            if (!out.reciprocal_fail && next_addr != 0U) {
                utils::double_queue_link *next_link =
                    eka2l1::ptr<utils::double_queue_link>(next_addr).get(pr);
                if (!next_link || next_link->prev_.ptr_address() != current) {
                    out.reciprocal_fail = 1;
                    out.first_bad_kind = 1;
                    out.first_bad_link = current;
                    out.first_bad_neighbor = next_addr;
                }
            }
            if (!out.reciprocal_fail && prev_addr != 0U) {
                utils::double_queue_link *prev_link =
                    eka2l1::ptr<utils::double_queue_link>(prev_addr).get(pr);
                if (!prev_link || prev_link->next_.ptr_address() != current) {
                    out.reciprocal_fail = 1;
                    out.first_bad_kind = 2;
                    out.first_bad_link = current;
                    out.first_bad_neighbor = prev_addr;
                }
            }

            const std::uint32_t ao_addr = current - static_cast<std::uint32_t>(link_offset);
            eka2l1::ptr<utils::active_object> obj_ptr(ao_addr);
            utils::active_object *obj = obj_ptr.get(pr);
            if (!obj) {
                out.invalid = 1;
                if (out.first_bad_kind == 0) {
                    out.first_bad_kind = 3;
                    out.first_bad_link = current;
                }
                break;
            }

            const bool ready =
                (obj->sts_.status != epoc::status_pending)
                && ((obj->sts_.flags & epoc::request_status::active) != 0);
            if (ready) {
                ++out.ready_count;
            }
            if (ao_addr == target_ao_addr) {
                out.found_index = i;
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_TARGET: stage={} dir={} index={} link=0x{:08X} ao=0x{:08X} vtable=0x{:08X} status_ptr=0x{:08X} status={} flags=0x{:08X} ready={} prev=0x{:08X} next=0x{:08X}",
                    stage, forward ? "forward" : "backward", i, current,
                    ao_addr, obj->vtable_, ao_addr + status_offset,
                    obj->sts_.status, static_cast<std::uint32_t>(obj->sts_.flags),
                    ready ? 1 : 0, prev_addr, next_addr);
            }

            ++out.entries;
            current = forward ? next_addr : prev_addr;
        }

        if (out.first_bad_kind != 0) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_BREAK: stage={} dir={} kind={} link=0x{:08X} neighbor=0x{:08X} entries={} invalid={} cycle={} reciprocal_fail={}",
                stage, forward ? "forward" : "backward", out.first_bad_kind,
                out.first_bad_link, out.first_bad_neighbor, out.entries,
                out.invalid, out.cycle, out.reciprocal_fail);
        }

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR: stage={} dir={} entries={} ready_count={} found_index={} invalid={} cycle={} reciprocal_fail={} first_bad_kind={} first_bad_link=0x{:08X} first_bad_neighbor=0x{:08X}",
            stage, forward ? "forward" : "backward", out.entries,
            out.ready_count, out.found_index, out.invalid, out.cycle,
            out.reciprocal_fail, out.first_bad_kind, out.first_bad_link,
            out.first_bad_neighbor);
        return out;
    }

    static void menuui20_log_activeq_directions(kernel_system *kern,
        kernel::process *pr, kernel::thread *thr,
        const std::uint32_t status_addr, const char *stage) {
        if (!kern || !pr || !thr || status_addr == 0U) {
            return;
        }

        kernel::thread_local_data *tld = thr->get_local_data();
        const std::uint32_t sched_addr =
            tld ? tld->scheduler.ptr_address() : 0U;
        utils::active_scheduler *sched = nullptr;
        if (tld && sched_addr != 0U) {
            sched = tld->scheduler.cast<utils::active_scheduler>().get(pr);
        }
        if (!sched) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR: stage={} dir=none entries=0 ready_count=0 found_index=-1 invalid=1 cycle=0 reciprocal_fail=0 first_bad_kind=3 first_bad_link=0x00000000 first_bad_neighbor=0x00000000",
                stage);
            return;
        }

        const std::uint32_t status_offset =
            static_cast<std::uint32_t>(offsetof(utils::active_object, sts_));
        const std::uint32_t target_ao_addr =
            status_addr >= status_offset ? status_addr - status_offset : 0U;
        const std::uint32_t head_addr = sched_addr
            + static_cast<std::uint32_t>(offsetof(utils::active_scheduler, act_queue_))
            + static_cast<std::uint32_t>(offsetof(utils::pri_queue, head_));
        const std::uint32_t head_next = sched->act_queue_.head_.next_.ptr_address();
        const std::uint32_t head_prev = sched->act_queue_.head_.prev_.ptr_address();
        const std::int32_t link_offset = sched->act_queue_.offset_to_link_;

        std::uint32_t head_next_prev = 0U;
        std::uint32_t head_prev_next = 0U;
        std::int32_t head_next_ok = 0;
        std::int32_t head_prev_ok = 0;

        if (head_next != 0U) {
            utils::double_queue_link *n =
                eka2l1::ptr<utils::double_queue_link>(head_next).get(pr);
            if (n) {
                head_next_prev = n->prev_.ptr_address();
                head_next_ok = head_next_prev == head_addr ? 1 : 0;
            }
        }
        if (head_prev != 0U) {
            utils::double_queue_link *p =
                eka2l1::ptr<utils::double_queue_link>(head_prev).get(pr);
            if (p) {
                head_prev_next = p->next_.ptr_address();
                head_prev_ok = head_prev_next == head_addr ? 1 : 0;
            }
        }

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_HEAD: stage={} scheduler=0x{:08X} head=0x{:08X} head_next=0x{:08X} head_prev=0x{:08X} head_next_prev=0x{:08X} head_prev_next=0x{:08X} head_next_ok={} head_prev_ok={} link_offset={} target_status=0x{:08X} target_ao=0x{:08X}",
            stage, sched_addr, head_addr, head_next, head_prev,
            head_next_prev, head_prev_next, head_next_ok, head_prev_ok,
            link_offset, status_addr, target_ao_addr);

        const menuui20_walk_result fwd = menuui20_walk_activeq(
            kern, pr, head_addr, head_next, link_offset,
            target_ao_addr, status_offset, true, stage);
        const menuui20_walk_result back = menuui20_walk_activeq(
            kern, pr, head_addr, head_prev, link_offset,
            target_ao_addr, status_offset, false, stage);

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR: stage={} dir=compare entries={} ready_count={} found_index={} invalid={} cycle={} reciprocal_fail={} first_bad_kind={} first_bad_link=0x{:08X} first_bad_neighbor=0x{:08X}",
            stage,
            back.entries,
            back.ready_count,
            back.found_index,
            back.invalid,
            back.cycle,
            back.reciprocal_fail,
            back.first_bad_kind,
            back.first_bad_link,
            back.first_bad_neighbor);
        (void)fwd;
    }
'''
svc = svc.replace(helper_tail, helper_tail + helper, 1)

# Probe immediately after MENUUI19's after-signal snapshot.
after_signal_anchor = '''                menuui19_log_active_object(kern, menuui17_complete_client_pr,\n                    msg->own_thr, menuui19_tracked_status, "after_signal");\n'''
if svc.count(after_signal_anchor) != 1:
    raise SystemExit(
        f"MENUUI20 ACTIVEQDIR1: after_signal anchor count={svc.count(after_signal_anchor)}"
    )
after_signal_new = after_signal_anchor + '''                menuui20_log_activeq_directions(kern, menuui17_complete_client_pr,\n                    msg->own_thr, menuui19_tracked_status, "after_signal");\n'''
svc = svc.replace(after_signal_anchor, after_signal_new, 1)

# Probe immediately before the actual WaitForAnyRequest call. Do not add a
# post-wait probe: the direction question is whether the guest scan can see the
# ready AO before it blocks/dispatches.
before_wait_anchor = '''            menuui19_log_active_object(kern, menuui18_wait_pr,\n                menuui18_wait_thr, menuui19_tracked_status, "before_wait");\n'''
if svc.count(before_wait_anchor) != 1:
    raise SystemExit(
        f"MENUUI20 ACTIVEQDIR1: before_wait anchor count={svc.count(before_wait_anchor)}"
    )
before_wait_new = before_wait_anchor + '''            menuui20_log_activeq_directions(kern, menuui18_wait_pr,\n                menuui18_wait_thr, menuui19_tracked_status, "before_wait");\n'''
svc = svc.replace(before_wait_anchor, before_wait_new, 1)

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI20 ACTIVEQDIR1: marker postcondition failed: {marker} "
            f"count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI20 ACTIVEQDIR1: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI20 ACTIVEQDIR1 diagnostic-only traces applied")
print("MENUUI20 target: forward next-chain vs guest-exact backward prev-chain + reciprocal invariants")
print("MENUUI20: no guest AO flags, queue links, scheduler, IPC, semaphore, pointer or focus state changed")
