#!/usr/bin/env python3
"""MENUUI22 SCHEDRUN1: diagnostic-only SVC window around a ready CActive.

Baseline: MENUUI22 NOJAVA FULL1 MANIC3 MODALFIX1.

The prior MENUUI21/22 traces prove the ALF request completes, the request
semaphore is signalled, and the target CActive remains ready when Menu enters
WaitForAnyRequest. This probe does not alter guest state. It instruments the
kernel SVC dispatcher so we can observe the target CActive across the guest
instructions that run between one WaitForAnyRequest SVC and the next SVC.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI22 SCHEDRUN1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui22_schedrun1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    kernel_path = up / "src/emu/kernel/src/kernel.cpp"
    svc_path = up / "src/emu/kernel/src/svc.cpp"
    root_path = up / "src/emu/ios/app/RootViewController.mm"

    for p in (kernel_path, svc_path, root_path):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    svc = svc_path.read_text(encoding="utf-8")
    for marker in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI21 VTABLE:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 ALF_WAKE_CONTEXT:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_FRAME:",
    ):
        if marker not in svc:
            fail("missing MENUUI22 authority marker: " + marker)

    root = root_path.read_text(encoding="utf-8")
    if "MANIC_MODALFIX1" not in root:
        fail("MANIC3 MODALFIX1 baseline missing")
    if 'if (i == 7) return @"Manic Skin";' not in root:
        fail("Manic Skin baseline missing")
    if (up / "src/emu/j2me").exists():
        fail("legacy src/emu/j2me unexpectedly present")

    text = kernel_path.read_text(encoding="utf-8")

    markers = (
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_ARM:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_FRAME:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_DONE:",
    )
    if any(m in text for m in markers):
        if all(text.count(m) == 1 for m in markers):
            print("MENUUI22 SCHEDRUN1 already present")
            return
        fail("partial prior SCHEDRUN1 patch detected")

    include_anchor = "#include <mem/ptr.h>\n"
    include_new = (
        "#include <mem/ptr.h>\n"
        "#include <utils/guest/actsched.h>\n"
        "#include <cstddef>\n"
    )
    text = replace_once(text, include_anchor, include_new, "actsched include")

    set_epoc_anchor = "    // For user-provided EPOC version\n    void kernel_system::set_epoc_version(const epocver ver) {\n"
    helper = r'''    // MENUUI22 SCHEDRUN1: host-only diagnostic state.
    // It never modifies guest memory, registers, queues, request statuses,
    // semaphore counts, IPC payloads, priorities, or scheduler state.
    struct menuui22_schedrun_state {
        bool armed = false;
        std::uint32_t seq = 0U;
        std::uint32_t target_ao = 0U;
        std::uint32_t target_status = 0U;
        std::uint32_t last_target_ao = 0U;
        std::int32_t budget = 0;
    };

    static menuui22_schedrun_state menuui22_schedrun_diag;

    static bool menuui22_schedrun_is_menu(kernel::process *pr) {
        if (!pr) {
            return false;
        }
        const auto uids = pr->get_uid_type();
        return static_cast<std::uint32_t>(std::get<2>(uids)) == 0x101F4CD2U;
    }

    static bool menuui22_schedrun_read_u32(kernel::process *pr,
        const std::uint32_t addr, std::uint32_t &value) {
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

    static bool menuui22_schedrun_find_first_ready(kernel::thread *thr,
        kernel::process *pr, std::uint32_t &ao_addr,
        std::uint32_t &status_addr, std::int32_t &queue_index) {
        ao_addr = 0U;
        status_addr = 0U;
        queue_index = -1;
        if (!thr || !pr) {
            return false;
        }

        kernel::thread_local_data *tld = thr->get_local_data();
        const std::uint32_t sched_addr =
            tld ? tld->scheduler.ptr_address() : 0U;
        utils::active_scheduler *sched = nullptr;
        if (tld && sched_addr != 0U) {
            sched = tld->scheduler.cast<utils::active_scheduler>().get(pr);
        }
        if (!sched) {
            return false;
        }

        const std::uint32_t head_addr = sched_addr
            + static_cast<std::uint32_t>(offsetof(utils::active_scheduler, act_queue_))
            + static_cast<std::uint32_t>(offsetof(utils::pri_queue, head_));
        const std::int32_t link_offset = sched->act_queue_.offset_to_link_;
        if (link_offset <= 0 || link_offset >= 0x100) {
            return false;
        }

        std::uint32_t current = sched->act_queue_.head_.prev_.ptr_address();
        for (std::int32_t i = 0; i < 64 && current != head_addr; ++i) {
            if (current == 0U || current < static_cast<std::uint32_t>(link_offset)) {
                return false;
            }
            utils::double_queue_link *link =
                eka2l1::ptr<utils::double_queue_link>(current).get(pr);
            if (!link) {
                return false;
            }
            const std::uint32_t candidate =
                current - static_cast<std::uint32_t>(link_offset);
            utils::active_object *obj =
                eka2l1::ptr<utils::active_object>(candidate).get(pr);
            if (!obj) {
                return false;
            }

            const bool ready =
                obj->sts_.status != epoc::request_status::pending_status
                && ((obj->sts_.flags & epoc::request_status::active) != 0U);
            if (ready) {
                ao_addr = candidate;
                status_addr = candidate
                    + static_cast<std::uint32_t>(offsetof(utils::active_object, sts_));
                queue_index = i;
                return true;
            }
            current = link->prev_.ptr_address();
        }
        return false;
    }

    static std::int32_t menuui22_schedrun_target_queue_index(kernel::thread *thr,
        kernel::process *pr, const std::uint32_t target_ao) {
        if (!thr || !pr || target_ao == 0U) {
            return -1;
        }
        kernel::thread_local_data *tld = thr->get_local_data();
        const std::uint32_t sched_addr =
            tld ? tld->scheduler.ptr_address() : 0U;
        utils::active_scheduler *sched = nullptr;
        if (tld && sched_addr != 0U) {
            sched = tld->scheduler.cast<utils::active_scheduler>().get(pr);
        }
        if (!sched) {
            return -1;
        }

        const std::uint32_t head_addr = sched_addr
            + static_cast<std::uint32_t>(offsetof(utils::active_scheduler, act_queue_))
            + static_cast<std::uint32_t>(offsetof(utils::pri_queue, head_));
        const std::int32_t link_offset = sched->act_queue_.offset_to_link_;
        if (link_offset <= 0 || link_offset >= 0x100) {
            return -1;
        }

        std::uint32_t current = sched->act_queue_.head_.prev_.ptr_address();
        for (std::int32_t i = 0; i < 64 && current != head_addr; ++i) {
            if (current == 0U || current < static_cast<std::uint32_t>(link_offset)) {
                return -1;
            }
            utils::double_queue_link *link =
                eka2l1::ptr<utils::double_queue_link>(current).get(pr);
            if (!link) {
                return -1;
            }
            const std::uint32_t candidate =
                current - static_cast<std::uint32_t>(link_offset);
            if (candidate == target_ao) {
                return i;
            }
            current = link->prev_.ptr_address();
        }
        return -1;
    }

    static void menuui22_schedrun_log_frame(kernel_system *kern,
        kernel::process *pr, const char *stage, const char *role,
        const std::uint32_t raw) {
        if (!kern || !pr || raw < 0x10000U) {
            return;
        }
        const std::uint32_t addr = raw & ~1U;
        for (const auto &seg_obj : kern->get_codeseg_list()) {
            codeseg_ptr seg = reinterpret_cast<codeseg_ptr>(seg_obj.get());
            if (!seg) {
                continue;
            }
            const std::uint32_t base = seg->get_code_run_addr(pr);
            const std::uint32_t size = seg->get_text_size();
            if (base <= addr && addr <= base + size) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_FRAME: stage={} role={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                    stage, role, raw,
                    common::ucs2_to_utf8(seg->get_full_path()),
                    base, addr - base);
                return;
            }
        }
    }

    static void menuui22_schedrun_trace(kernel_system *kern,
        kernel::process *pr, kernel::thread *thr,
        const std::uint32_t ordinal, const char *stage) {
        if (!kern || !pr || !thr || !menuui22_schedrun_diag.armed
            || menuui22_schedrun_diag.budget <= 0
            || !menuui22_schedrun_is_menu(pr)) {
            return;
        }

        utils::active_object *target =
            eka2l1::ptr<utils::active_object>(
                menuui22_schedrun_diag.target_ao).get(pr);
        const std::int32_t target_index =
            menuui22_schedrun_target_queue_index(
                thr, pr, menuui22_schedrun_diag.target_ao);

        const std::int32_t status = target
            ? target->sts_.status : static_cast<std::int32_t>(0x7FFFFFFF);
        const std::uint32_t flags = target
            ? static_cast<std::uint32_t>(target->sts_.flags) : 0xFFFFFFFFU;
        const std::int32_t active = target
            && ((flags & epoc::request_status::active) != 0U) ? 1 : 0;
        const std::int32_t ready = target
            && status != epoc::request_status::pending_status
            && active ? 1 : 0;

        std::uint32_t runl_eabi = 0U;
        std::uint32_t runl_gcc = 0U;
        const std::int32_t runl_eabi_valid = target
            && menuui22_schedrun_read_u32(
                pr, target->vtable_ + 16U, runl_eabi) ? 1 : 0;
        const std::int32_t runl_gcc_valid = target
            && menuui22_schedrun_read_u32(
                pr, target->vtable_ + 20U, runl_gcc) ? 1 : 0;

        arm::core *cpu = kern->get_cpu();
        const std::uint32_t pc = cpu ? cpu->get_pc() : 0U;
        const std::uint32_t lr = cpu ? cpu->get_lr() : 0U;
        const std::uint32_t sp = cpu ? cpu->get_sp() : 0U;

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC: seq={} stage={} budget={} ordinal=0x{:08X} target_ao=0x{:08X} target_status=0x{:08X} target_valid={} status={} flags=0x{:08X} active={} ready={} target_queue_index={} vtable=0x{:08X} runl_eabi=0x{:08X} runl_eabi_valid={} runl_gcc=0x{:08X} runl_gcc_valid={} request_count={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
            menuui22_schedrun_diag.seq, stage,
            menuui22_schedrun_diag.budget, ordinal,
            menuui22_schedrun_diag.target_ao,
            menuui22_schedrun_diag.target_status,
            target ? 1 : 0, status, flags, active, ready,
            target_index, target ? target->vtable_ : 0U,
            runl_eabi, runl_eabi_valid, runl_gcc, runl_gcc_valid,
            thr->request_count(), pc, lr, sp);

        menuui22_schedrun_log_frame(kern, pr, stage, "pc", pc);
        menuui22_schedrun_log_frame(kern, pr, stage, "lr", lr);
        if (runl_eabi_valid) {
            menuui22_schedrun_log_frame(
                kern, pr, stage, "runl_eabi_v16", runl_eabi);
        }
        if (runl_gcc_valid) {
            menuui22_schedrun_log_frame(
                kern, pr, stage, "runl_gcc_v20", runl_gcc);
        }
    }

'''
    text = replace_once(
        text,
        set_epoc_anchor,
        helper + set_epoc_anchor,
        "SCHEDRUN helper insertion",
    )

    old_lambda = '''        // Set CPU SVC handler
        cpu_->system_call_handler = [this](const std::uint32_t ordinal) {
            // crr_thread()->add_last_syscall(ordinal);
            get_lib_manager()->call_svc(ordinal);

            // EKA1 does not use BX LR to jump back, they let kernel do it
'''
    new_lambda = '''        // Set CPU SVC handler
        cpu_->system_call_handler = [this](const std::uint32_t ordinal) {
            // crr_thread()->add_last_syscall(ordinal);

            kernel::process *menuui22_diag_pr = crr_process();
            kernel::thread *menuui22_diag_thr = crr_thread();

            // RM-356/S60v5 uses the EPOC v10 fast executive ordinal
            // 0x00800000 for User::WaitForAnyRequest. Arm only when the Menu
            // process enters that SVC with a ready CActive at the scheduler's
            // exact backward-scan head. Host state only; guest state is read.
            if (!menuui22_schedrun_diag.armed
                && ordinal == 0x00800000U
                && menuui22_schedrun_is_menu(menuui22_diag_pr)) {
                std::uint32_t menuui22_ready_ao = 0U;
                std::uint32_t menuui22_ready_status = 0U;
                std::int32_t menuui22_ready_index = -1;
                if (menuui22_schedrun_find_first_ready(
                        menuui22_diag_thr, menuui22_diag_pr,
                        menuui22_ready_ao, menuui22_ready_status,
                        menuui22_ready_index)
                    && menuui22_ready_ao != 0U
                    && menuui22_ready_ao
                        != menuui22_schedrun_diag.last_target_ao) {
                    menuui22_schedrun_diag.armed = true;
                    ++menuui22_schedrun_diag.seq;
                    menuui22_schedrun_diag.target_ao = menuui22_ready_ao;
                    menuui22_schedrun_diag.target_status =
                        menuui22_ready_status;
                    menuui22_schedrun_diag.last_target_ao =
                        menuui22_ready_ao;
                    menuui22_schedrun_diag.budget = 24;

                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_ARM: seq={} ordinal=0x{:08X} target_ao=0x{:08X} target_status=0x{:08X} first_ready_index={} request_count={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                        menuui22_schedrun_diag.seq, ordinal,
                        menuui22_ready_ao, menuui22_ready_status,
                        menuui22_ready_index,
                        menuui22_diag_thr
                            ? menuui22_diag_thr->request_count() : 0,
                        cpu_->get_pc(), cpu_->get_lr(), cpu_->get_sp());
                }
            }

            menuui22_schedrun_trace(
                this, menuui22_diag_pr, menuui22_diag_thr,
                ordinal, "svc_pre");

            get_lib_manager()->call_svc(ordinal);

            kernel::process *menuui22_post_pr = crr_process();
            kernel::thread *menuui22_post_thr = crr_thread();
            menuui22_schedrun_trace(
                this, menuui22_post_pr, menuui22_post_thr,
                ordinal, "svc_post");

            if (menuui22_schedrun_diag.armed
                && menuui22_schedrun_diag.budget > 0) {
                --menuui22_schedrun_diag.budget;
                if (menuui22_schedrun_diag.budget == 0) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_DONE: seq={} target_ao=0x{:08X} target_status=0x{:08X}",
                        menuui22_schedrun_diag.seq,
                        menuui22_schedrun_diag.target_ao,
                        menuui22_schedrun_diag.target_status);
                    menuui22_schedrun_diag.armed = false;
                }
            }

            // EKA1 does not use BX LR to jump back, they let kernel do it
'''
    text = replace_once(text, old_lambda, new_lambda, "SVC dispatcher lambda")

    for marker in markers:
        if text.count(marker) != 1:
            fail(f"marker gate failed: {marker} count={text.count(marker)}")

    # Source-level behavior preservation: one original dispatcher call remains;
    # no SVC implementation, guest register write, scheduler operation, or
    # request-status mutation is added by this patch.
    if text.count("get_lib_manager()->call_svc(ordinal);") != 1:
        fail("call_svc authority count changed")
    if "cpu_->set_pc(" not in text or "cpu_->set_cpsr(" not in text:
        fail("EKA1 dispatcher return authority unexpectedly missing")

    kernel_path.write_text(text, encoding="utf-8")
    print("MENUUI22 SCHEDRUN1 diagnostic-only SVC window applied")
    print("MENUUI22 SCHEDRUN1 target: ready CActive across WaitForAnyRequest -> next guest SVC")
    print("MENUUI22 SCHEDRUN1 behavior_change=NONE")


if __name__ == "__main__":
    main()
