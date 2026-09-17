#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui21_schedctx1.py <upstream-root>")

up = Path(sys.argv[1]).resolve()
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI21 SCHEDCTX1: required source missing: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_ARM:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COMPLETE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_STATUS:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_SIGNAL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI18 CLIENT_WAIT:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_TRACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI19 AO_STATE:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_HEAD:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR:",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI21 SCHEDCTX1: missing authority marker: " + marker)

markers = {
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_REG_A:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_REG_B:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_BIND:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 AO_RAW:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 VTABLE:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 STACK_WORD:": 1,
    "SYMBIAN-SYSTEMAPPS1 MENUUI21 FRAME:": 1,
}
if any(marker in svc for marker in markers):
    if all(svc.count(marker) == expected for marker, expected in markers.items()):
        print("MENUUI21 SCHEDCTX1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI21 SCHEDCTX1: partial prior patch detected")

behavior_tokens = [
    "status->set(val, kern->is_eka1());",
    "msg->own_thr->signal_request();",
    "kern->crr_thread()->wait_for_any_request();",
    "kern->call_ipc_complete_callbacks(msg, val);",
]
behavior_before = {token: svc.count(token) for token in behavior_tokens}

# MENUUI20's helper is the authority anchor. Add a read-only guest scheduler
# context snapshot beside it; no guest memory, CPU register, queue, status,
# semaphore, IPC, pointer, or focus state is changed.
helper_tail = '''            back.first_bad_neighbor);\n        (void)fwd;\n    }\n'''
if svc.count(helper_tail) != 1:
    raise SystemExit(
        f"MENUUI21 SCHEDCTX1: MENUUI20 helper tail count={svc.count(helper_tail)}"
    )

helper = r'''

    static std::uint32_t menuui21_last_logged_msg_id = 0U;

    static codeseg_ptr get_codeseg_from_addr(kernel_system *kern,
        kernel::process *pr, const std::uint32_t addr, const bool ep);

    static bool menuui21_read_u32(kernel::process *pr, const std::uint32_t addr,
        std::uint32_t &value) {
        if (!pr || addr == 0U) {
            value = 0U;
            return false;
        }
        const std::uint32_t *word = reinterpret_cast<const std::uint32_t *>(
            pr->get_ptr_on_addr_space(addr));
        if (!word) {
            value = 0U;
            return false;
        }
        value = *word;
        return true;
    }

    static void menuui21_log_frame(kernel_system *kern, kernel::process *pr,
        const char *role, const std::int32_t index, const std::uint32_t raw) {
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
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 FRAME: role={} index={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
            role, index, raw, module, base, addr - base);
    }

    static void menuui21_log_scheduler_context(kernel_system *kern,
        kernel::process *pr, kernel::thread *thr,
        const std::uint32_t status_addr, const char *stage) {
        if (!kern || !pr || !thr || status_addr == 0U
            || menuui19_tracked_msg_id == 0U
            || menuui21_last_logged_msg_id == menuui19_tracked_msg_id) {
            return;
        }

        const std::uint32_t status_offset =
            static_cast<std::uint32_t>(offsetof(utils::active_object, sts_));
        const std::uint32_t link_offset =
            static_cast<std::uint32_t>(offsetof(utils::active_object, link_));
        if (status_addr < status_offset) {
            return;
        }

        const std::uint32_t ao_addr = status_addr - status_offset;
        const std::uint32_t target_link = ao_addr + link_offset;
        utils::active_object *ao =
            eka2l1::ptr<utils::active_object>(ao_addr).get(pr);
        if (!ao) {
            return;
        }

        menuui21_last_logged_msg_id = menuui19_tracked_msg_id;

        auto *cpu = kern->get_cpu();
        std::uint32_t r[16] = {};
        if (cpu) {
            for (std::int32_t i = 0; i < 16; ++i) {
                r[i] = cpu->get_reg(static_cast<std::size_t>(i));
            }
        }
        const std::uint32_t cpsr = cpu ? cpu->get_cpsr() : 0U;
        const std::int32_t thumb = cpu && cpu->is_thumb_mode() ? 1 : 0;

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_REG_A: stage={} msg_id={} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X}",
            stage, menuui19_tracked_msg_id,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6]);
        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_REG_B: stage={} msg_id={} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X} sp=0x{:08X} lr=0x{:08X} pc=0x{:08X} cpsr=0x{:08X} thumb={}",
            stage, menuui19_tracked_msg_id,
            r[7], r[8], r[9], r[10], r[11], r[12], r[13], r[14], r[15],
            cpsr, thumb);

        kernel::thread_local_data *tld = thr->get_local_data();
        const std::uint32_t sched_addr =
            tld ? tld->scheduler.ptr_address() : 0U;
        utils::active_scheduler *sched = nullptr;
        if (tld && sched_addr != 0U) {
            sched = tld->scheduler.cast<utils::active_scheduler>().get(pr);
        }

        const std::uint32_t head_addr = sched_addr
            ? sched_addr
                + static_cast<std::uint32_t>(offsetof(utils::active_scheduler, act_queue_))
                + static_cast<std::uint32_t>(offsetof(utils::pri_queue, head_))
            : 0U;
        const std::uint32_t head_prev =
            sched ? sched->act_queue_.head_.prev_.ptr_address() : 0U;
        const std::uint32_t sched_vtable = sched ? sched->vtable_ : 0U;

        std::uint32_t loop_value = 0U;
        std::uint32_t current_obj_value = 0U;
        const std::int32_t loop_valid = menuui21_read_u32(pr, r[5], loop_value) ? 1 : 0;
        const std::int32_t current_obj_valid =
            menuui21_read_u32(pr, r[7], current_obj_value) ? 1 : 0;

        std::uint32_t wait_eabi = 0U;
        std::uint32_t wait_gcc = 0U;
        const std::int32_t wait_eabi_valid =
            menuui21_read_u32(pr, sched_vtable + 12U, wait_eabi) ? 1 : 0;
        const std::int32_t wait_gcc_valid =
            menuui21_read_u32(pr, sched_vtable + 16U, wait_gcc) ? 1 : 0;
        const std::int32_t wait_match_eabi = wait_eabi_valid
            && ((wait_eabi & ~1U) == (r[6] & ~1U)) ? 1 : 0;
        const std::int32_t wait_match_gcc = wait_gcc_valid
            && ((wait_gcc & ~1U) == (r[6] & ~1U)) ? 1 : 0;

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_BIND: stage={} scheduler=0x{:08X} head=0x{:08X} head_prev=0x{:08X} r4=0x{:08X} r4_is_head={} r5_loop=0x{:08X} loop_valid={} loop_value=0x{:08X} r6_wait=0x{:08X} wait_eabi=0x{:08X} wait_gcc=0x{:08X} wait_match_eabi={} wait_match_gcc={} r7_current_slot=0x{:08X} current_valid={} current_value=0x{:08X}",
            stage, sched_addr, head_addr, head_prev, r[4],
            r[4] == head_addr ? 1 : 0, r[5], loop_valid, loop_value,
            r[6], wait_eabi, wait_gcc, wait_match_eabi, wait_match_gcc,
            r[7], current_obj_valid, current_obj_value);

        std::uint32_t raw_status = 0U;
        std::uint32_t raw_flags = 0U;
        std::uint32_t raw_prev = 0U;
        std::uint32_t raw_next = 0U;
        const std::int32_t raw_status_valid =
            menuui21_read_u32(pr, target_link - 8U, raw_status) ? 1 : 0;
        const std::int32_t raw_flags_valid =
            menuui21_read_u32(pr, target_link - 4U, raw_flags) ? 1 : 0;
        const std::int32_t raw_prev_valid =
            menuui21_read_u32(pr, target_link, raw_prev) ? 1 : 0;
        const std::int32_t raw_next_valid =
            menuui21_read_u32(pr, target_link + 4U, raw_next) ? 1 : 0;
        const std::int32_t raw_ready = raw_status_valid && raw_flags_valid
            && static_cast<std::int32_t>(raw_status) != epoc::request_status::pending_status
            && ((raw_flags & epoc::request_status::active) != 0U) ? 1 : 0;

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 AO_RAW: stage={} ao=0x{:08X} link=0x{:08X} status_addr=0x{:08X} raw_status=0x{:08X} status_valid={} raw_flags=0x{:08X} flags_valid={} raw_prev=0x{:08X} prev_valid={} raw_next=0x{:08X} next_valid={} raw_ready={} struct_status={} struct_flags=0x{:08X}",
            stage, ao_addr, target_link, status_addr,
            raw_status, raw_status_valid, raw_flags, raw_flags_valid,
            raw_prev, raw_prev_valid, raw_next, raw_next_valid, raw_ready,
            ao->sts_.status, static_cast<std::uint32_t>(ao->sts_.flags));

        std::int32_t scan_entries = 0;
        std::int32_t scan_invalid = 0;
        std::int32_t target_index = -1;
        std::int32_t first_ready_index = -1;
        std::uint32_t first_ready_ao = 0U;
        std::uint32_t first_ready_status = 0U;
        std::uint32_t first_ready_flags = 0U;
        std::uint32_t current = head_prev;

        for (std::int32_t i = 0; i < 64 && current != head_addr; ++i) {
            if (current == 0U || current < 8U) {
                scan_invalid = 1;
                break;
            }
            std::uint32_t scan_status = 0U;
            std::uint32_t scan_flags = 0U;
            std::uint32_t scan_prev = 0U;
            if (!menuui21_read_u32(pr, current - 8U, scan_status)
                || !menuui21_read_u32(pr, current - 4U, scan_flags)
                || !menuui21_read_u32(pr, current, scan_prev)) {
                scan_invalid = 1;
                break;
            }
            const std::uint32_t scan_ao = current - link_offset;
            const bool ready =
                static_cast<std::int32_t>(scan_status) != epoc::request_status::pending_status
                && ((scan_flags & epoc::request_status::active) != 0U);
            if (current == target_link) {
                target_index = i;
            }
            if (ready && first_ready_index < 0) {
                first_ready_index = i;
                first_ready_ao = scan_ao;
                first_ready_status = scan_status;
                first_ready_flags = scan_flags;
            }
            ++scan_entries;
            current = scan_prev;
        }

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN: stage={} mode=arm_ldmda_exact start=0x{:08X} entries={} invalid={} target_index={} target_ready={} first_ready_index={} first_ready_ao=0x{:08X} first_ready_status=0x{:08X} first_ready_flags=0x{:08X} target_is_first_ready={}",
            stage, head_prev, scan_entries, scan_invalid, target_index, raw_ready,
            first_ready_index, first_ready_ao, first_ready_status, first_ready_flags,
            first_ready_ao == ao_addr ? 1 : 0);

        std::uint32_t ao_v12 = 0U;
        std::uint32_t ao_v16 = 0U;
        std::uint32_t ao_v20 = 0U;
        const std::int32_t ao_v12_valid =
            menuui21_read_u32(pr, ao->vtable_ + 12U, ao_v12) ? 1 : 0;
        const std::int32_t ao_v16_valid =
            menuui21_read_u32(pr, ao->vtable_ + 16U, ao_v16) ? 1 : 0;
        const std::int32_t ao_v20_valid =
            menuui21_read_u32(pr, ao->vtable_ + 20U, ao_v20) ? 1 : 0;

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI21 VTABLE: stage={} sched_vtable=0x{:08X} wait_eabi=0x{:08X} wait_eabi_valid={} wait_gcc=0x{:08X} wait_gcc_valid={} ao_vtable=0x{:08X} ao_v12=0x{:08X} v12_valid={} runl_eabi_v16=0x{:08X} v16_valid={} runl_gcc_v20=0x{:08X} v20_valid={}",
            stage, sched_vtable, wait_eabi, wait_eabi_valid,
            wait_gcc, wait_gcc_valid, ao->vtable_,
            ao_v12, ao_v12_valid, ao_v16, ao_v16_valid,
            ao_v20, ao_v20_valid);

        menuui21_log_frame(kern, pr, "pc", -1, r[15]);
        menuui21_log_frame(kern, pr, "lr", -1, r[14]);
        menuui21_log_frame(kern, pr, "r6_wait", -1, r[6]);
        menuui21_log_frame(kern, pr, "wait_eabi", -1, wait_eabi);
        menuui21_log_frame(kern, pr, "wait_gcc", -1, wait_gcc);
        menuui21_log_frame(kern, pr, "ao_v12", -1, ao_v12);
        menuui21_log_frame(kern, pr, "runl_eabi_v16", -1, ao_v16);
        menuui21_log_frame(kern, pr, "runl_gcc_v20", -1, ao_v20);

        for (std::int32_t row = 0; row < 8; ++row) {
            std::uint32_t word[4] = {};
            std::int32_t valid[4] = {};
            for (std::int32_t col = 0; col < 4; ++col) {
                const std::int32_t index = row * 4 + col;
                valid[col] = menuui21_read_u32(
                    pr, r[13] + static_cast<std::uint32_t>(index * 4), word[col]) ? 1 : 0;
            }
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI21 STACK_WORD: stage={} row={} sp_addr=0x{:08X} w0=0x{:08X} v0={} w1=0x{:08X} v1={} w2=0x{:08X} v2={} w3=0x{:08X} v3={}",
                stage, row, r[13] + static_cast<std::uint32_t>(row * 16),
                word[0], valid[0], word[1], valid[1],
                word[2], valid[2], word[3], valid[3]);
            for (std::int32_t col = 0; col < 4; ++col) {
                if (valid[col]) {
                    menuui21_log_frame(kern, pr, "stack", row * 4 + col, word[col]);
                }
            }
        }
    }
'''

svc = svc.replace(helper_tail, helper_tail + helper, 1)

# Capture once, at the first Menu WaitForAnyRequest after the tracked ALF
# pointer completion. MENUUI20's before-wait call proves this is the exact
# observation point and remains unchanged.
before_wait_anchor = '''            menuui20_log_activeq_directions(kern, menuui18_wait_pr,\n                menuui18_wait_thr, menuui19_tracked_status, "before_wait");\n'''
if svc.count(before_wait_anchor) != 1:
    raise SystemExit(
        f"MENUUI21 SCHEDCTX1: MENUUI20 before_wait anchor count={svc.count(before_wait_anchor)}"
    )
before_wait_new = before_wait_anchor + '''            menuui21_log_scheduler_context(kern, menuui18_wait_pr,\n                menuui18_wait_thr, menuui19_tracked_status, "before_wait");\n'''
svc = svc.replace(before_wait_anchor, before_wait_new, 1)

for marker, expected in markers.items():
    actual = svc.count(marker)
    if actual != expected:
        raise SystemExit(
            f"MENUUI21 SCHEDCTX1: marker postcondition failed: {marker} "
            f"count={actual} expected={expected}"
        )

for token, before in behavior_before.items():
    after = svc.count(token)
    if after != before:
        raise SystemExit(
            "MENUUI21 SCHEDCTX1: behavior-preservation count changed: "
            f"token={token!r} before={before} after={after}"
        )

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI21 SCHEDCTX1 diagnostic-only traces applied")
print("MENUUI21 target: guest ActiveScheduler registers + ABI vtables + exact ARM LDMDA scan + stack frames")
print("MENUUI21: no guest memory, CPU register, AO, queue, scheduler, semaphore, IPC, pointer or focus state changed")
