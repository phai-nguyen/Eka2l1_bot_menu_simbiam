#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B34 FOCUSLOCKDIAG1 after B33.

B33 device evidence localizes Exit Emulator hang to Wserv teardown waiting in
screen::fire_focus_change_callbacks() on focus_callback_mutex while the iOS
lifecycle worker is blocked in shutdown_threads()/pthread_join().

B34 is diagnostic-only. It traces the existing focus callback mutex lifecycle
and the window-group teardown/update_focus path. It deliberately does NOT
change the mutex type, lock scope, callback invocation, teardown, or iOS exit
behavior.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B34-FOCUSLOCKDIAG1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b34_focuslockdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen=up/"src/emu/services/src/window/screen.cpp"
    screen_h=up/"src/emu/services/include/services/window/screen.h"
    wing=up/"src/emu/services/src/window/classes/wingroup.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    ctx=up/"src/emu/services/src/context.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"

    for p in (screen,screen_h,wing,svc,ctx,thr,kern,sched,lib,root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sc=screen.read_text(encoding="utf-8")
    sh=screen_h.read_text(encoding="utf-8")
    wg=wing.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    cx=ctx.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sch=sched.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    rt=root.read_text(encoding="utf-8")

    for needle,text,name in (
        ("[NBOOT2][LDR_ROOT_RESOLVED]",lm,"B30"),
        ("[NBOOT2][SCHED_STALE_READY_DROP]",sch,"B31"),
        ("[NBOOT2][EIKFAULT_AV]",ke,"B32 AV"),
        ("[NBOOT2][EIKFAULT_LEAVE]",sv,"B32 leave"),
        ("[NBOOT2][EIKFAULT_SVCMISS]",lm,"B32 SVC"),
        ("[NBOOT2][EIKCANCEL_LLE]",sv,"B33 LLE"),
        ("[NBOOT2][EIKCANCEL_HLE]",cx,"B33 HLE"),
        ("[NBOOT2][EIKCANCEL_NOTIFY]",th,"B33 notify"),
        ("[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested",rt,"B26 exit"),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")

    if "std::mutex focus_callback_mutex;" not in sh:
        fail("focus_callback_mutex baseline type is not std::mutex")
    if "std::recursive_mutex focus_callback_mutex" in sh:
        fail("unexpected recursive focus callback mutex baseline")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][FOCUSLOCK_FIRE_WAIT]",
        "[NBOOT2][FOCUSLOCK_FIRE_ACQUIRED]",
        "[NBOOT2][FOCUSLOCK_CB_BEGIN]",
        "[NBOOT2][FOCUSLOCK_CB_END]",
        "[NBOOT2][FOCUSLOCK_FIRE_RELEASING]",
        "[NBOOT2][FOCUSLOCK_FIRE_RELEASED]",
        "[NBOOT2][FOCUSLOCK_ADD_WAIT]",
        "[NBOOT2][FOCUSLOCK_ADD_ACQUIRED]",
        "[NBOOT2][FOCUSLOCK_ADD_RELEASED]",
        "[NBOOT2][FOCUSLOCK_REMOVE_WAIT]",
        "[NBOOT2][FOCUSLOCK_REMOVE_ACQUIRED]",
        "[NBOOT2][FOCUSLOCK_REMOVE_RELEASED]",
        "[NBOOT2][FOCUS_UPDATE_ENTER]",
        "[NBOOT2][FOCUS_UPDATE_EXIT]",
        "[NBOOT2][WG_DTOR]",
    )
    combined=sc+"\n"+wg
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers):
            print(f"{MARK}: already applied")
            return
        fail("partial B34 markers present: "+", ".join(present))

    include_anchor='''#include <kernel/kernel.h>
#include <kernel/timing.h>
#include <thread>
'''
    include_new='''#include <kernel/kernel.h>
#include <kernel/timing.h>

#include <atomic>
#include <cstdint>
#include <functional>
#include <thread>
'''
    sc=replace_once(sc,include_anchor,include_new,"screen diagnostic includes")

    ns_anchor='''namespace eka2l1::epoc {
    struct window_drawer_walker : public window_tree_walker {
'''
    ns_new='''namespace eka2l1::epoc {
    // B34 FOCUSLOCKDIAG1: diagnostic-only sequencing for the host focus lock.
    // The hash is used only as a stable-in-process host-thread tag in logs.
    static std::atomic<std::uint64_t> nboot2_b34_focus_seq{0};

    static std::uint64_t nboot2_b34_next_focus_seq() {
        return nboot2_b34_focus_seq.fetch_add(1, std::memory_order_relaxed) + 1;
    }

    static std::size_t nboot2_b34_host_thread_tag() {
        return std::hash<std::thread::id>{}(std::this_thread::get_id());
    }

    struct window_drawer_walker : public window_tree_walker {
'''
    sc=replace_once(sc,ns_anchor,ns_new,"screen diagnostic helpers")

    update_anchor='''    epoc::window_group *screen::update_focus(window_server *serv, epoc::window_group *closing_group) {
        epoc::window_group *old_focus = focus;
'''
    update_new='''    epoc::window_group *screen::update_focus(window_server *serv, epoc::window_group *closing_group) {
        const std::uint64_t nboot2_b34_update_seq = nboot2_b34_next_focus_seq();
        const std::size_t nboot2_b34_update_tid = nboot2_b34_host_thread_tag();
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUS_UPDATE_ENTER] seq={} host_tid=0x{:X} screen=0x{:X} focus=0x{:X} closing_group=0x{:X}",
            nboot2_b34_update_seq, nboot2_b34_update_tid,
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(focus),
            reinterpret_cast<std::uintptr_t>(closing_group));

        epoc::window_group *old_focus = focus;
'''
    sc=replace_once(sc,update_anchor,update_new,"update_focus enter diagnostics")

    update_return='''        return (new_focus_screen ? alternative_focus : focus);
    }

    epoc::window_group *screen::get_group_chain() {
'''
    update_return_new='''        epoc::window_group *nboot2_b34_result =
            (new_focus_screen ? alternative_focus : focus);
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUS_UPDATE_EXIT] seq={} host_tid=0x{:X} screen=0x{:X} old_focus=0x{:X} focus=0x{:X} result=0x{:X}",
            nboot2_b34_update_seq, nboot2_b34_update_tid,
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(old_focus),
            reinterpret_cast<std::uintptr_t>(focus),
            reinterpret_cast<std::uintptr_t>(nboot2_b34_result));
        return nboot2_b34_result;
    }

    epoc::window_group *screen::get_group_chain() {
'''
    sc=replace_once(sc,update_return,update_return_new,"update_focus exit diagnostics")

    fire_old='''    void screen::fire_focus_change_callbacks(const focus_change_property property) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);

        for (auto &callback : focus_callbacks) {
            if (callback.second)
                callback.second(callback.first, focus, property);
        }
    }
'''
    fire_new='''    void screen::fire_focus_change_callbacks(const focus_change_property property) {
        const std::uint64_t nboot2_b34_seq = nboot2_b34_next_focus_seq();
        const std::size_t nboot2_b34_tid = nboot2_b34_host_thread_tag();
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_FIRE_WAIT] seq={} host_tid=0x{:X} screen=0x{:X} focus=0x{:X} property={}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(focus),
            static_cast<int>(property));

        {
            const std::lock_guard<std::mutex> guard(focus_callback_mutex);
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][FOCUSLOCK_FIRE_ACQUIRED] seq={} host_tid=0x{:X} screen=0x{:X}",
                nboot2_b34_seq, nboot2_b34_tid,
                reinterpret_cast<std::uintptr_t>(this));

            std::size_t nboot2_b34_callback_index = 0;
            for (auto &callback : focus_callbacks) {
                nboot2_b34_callback_index++;
                if (callback.second) {
                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][FOCUSLOCK_CB_BEGIN] seq={} host_tid=0x{:X} callback_index={} userdata=0x{:X} focus=0x{:X} property={}",
                        nboot2_b34_seq, nboot2_b34_tid, nboot2_b34_callback_index,
                        reinterpret_cast<std::uintptr_t>(callback.first),
                        reinterpret_cast<std::uintptr_t>(focus),
                        static_cast<int>(property));
                    callback.second(callback.first, focus, property);
                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][FOCUSLOCK_CB_END] seq={} host_tid=0x{:X} callback_index={} userdata=0x{:X}",
                        nboot2_b34_seq, nboot2_b34_tid, nboot2_b34_callback_index,
                        reinterpret_cast<std::uintptr_t>(callback.first));
                }
            }

            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][FOCUSLOCK_FIRE_RELEASING] seq={} host_tid=0x{:X} screen=0x{:X}",
                nboot2_b34_seq, nboot2_b34_tid,
                reinterpret_cast<std::uintptr_t>(this));
        }

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_FIRE_RELEASED] seq={} host_tid=0x{:X} screen=0x{:X}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this));
    }
'''
    sc=replace_once(sc,fire_old,fire_new,"focus fire diagnostics")

    add_old='''    std::size_t screen::add_focus_change_callback(void *userdata, focus_change_callback_handler handler) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);

        focus_change_callback callback_pair = { userdata, handler };
        return focus_callbacks.add(callback_pair);
    }
'''
    add_new='''    std::size_t screen::add_focus_change_callback(void *userdata, focus_change_callback_handler handler) {
        const std::uint64_t nboot2_b34_seq = nboot2_b34_next_focus_seq();
        const std::size_t nboot2_b34_tid = nboot2_b34_host_thread_tag();
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_ADD_WAIT] seq={} host_tid=0x{:X} screen=0x{:X} userdata=0x{:X}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(userdata));

        std::size_t nboot2_b34_handle = 0;
        {
            const std::lock_guard<std::mutex> guard(focus_callback_mutex);
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][FOCUSLOCK_ADD_ACQUIRED] seq={} host_tid=0x{:X} screen=0x{:X}",
                nboot2_b34_seq, nboot2_b34_tid,
                reinterpret_cast<std::uintptr_t>(this));

            focus_change_callback callback_pair = { userdata, handler };
            nboot2_b34_handle = focus_callbacks.add(callback_pair);
        }

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_ADD_RELEASED] seq={} host_tid=0x{:X} screen=0x{:X} handle={}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this), nboot2_b34_handle);
        return nboot2_b34_handle;
    }
'''
    sc=replace_once(sc,add_old,add_new,"focus add diagnostics")

    remove_old='''    bool screen::remove_focus_change_callback(const std::size_t cb) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);
        return focus_callbacks.remove(cb);
    }
'''
    remove_new='''    bool screen::remove_focus_change_callback(const std::size_t cb) {
        const std::uint64_t nboot2_b34_seq = nboot2_b34_next_focus_seq();
        const std::size_t nboot2_b34_tid = nboot2_b34_host_thread_tag();
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_REMOVE_WAIT] seq={} host_tid=0x{:X} screen=0x{:X} handle={}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this), cb);

        bool nboot2_b34_removed = false;
        {
            const std::lock_guard<std::mutex> guard(focus_callback_mutex);
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][FOCUSLOCK_REMOVE_ACQUIRED] seq={} host_tid=0x{:X} screen=0x{:X} handle={}",
                nboot2_b34_seq, nboot2_b34_tid,
                reinterpret_cast<std::uintptr_t>(this), cb);
            nboot2_b34_removed = focus_callbacks.remove(cb);
        }

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][FOCUSLOCK_REMOVE_RELEASED] seq={} host_tid=0x{:X} screen=0x{:X} handle={} removed={}",
            nboot2_b34_seq, nboot2_b34_tid,
            reinterpret_cast<std::uintptr_t>(this), cb, nboot2_b34_removed);
        return nboot2_b34_removed;
    }
'''
    sc=replace_once(sc,remove_old,remove_new,"focus remove diagnostics")

    dtor_old='''    window_group::~window_group() {
        if (uid_owner_change_process) {
            uid_owner_change_process->unregister_uid_type_change_callback(uid_owner_change_callback_handle);
        }
        
        remove_from_sibling_list();

        if (this == scr->focus) {
            set_receive_focus(false);
            scr->update_focus(&client->get_ws(), this);
        }

        if (scr) {
            scr->need_update_visible_regions(true);
        }
    }
'''
    dtor_new='''    window_group::~window_group() {
        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WG_DTOR] phase=enter group=0x{:X} screen=0x{:X} screen_focus=0x{:X}",
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(scr),
            reinterpret_cast<std::uintptr_t>(scr ? scr->focus : nullptr));

        if (uid_owner_change_process) {
            uid_owner_change_process->unregister_uid_type_change_callback(uid_owner_change_callback_handle);
        }
        
        remove_from_sibling_list();

        if (this == scr->focus) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][WG_DTOR] phase=focus_update_begin group=0x{:X} screen=0x{:X}",
                reinterpret_cast<std::uintptr_t>(this),
                reinterpret_cast<std::uintptr_t>(scr));
            set_receive_focus(false);
            scr->update_focus(&client->get_ws(), this);
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][WG_DTOR] phase=focus_update_done group=0x{:X} screen=0x{:X}",
                reinterpret_cast<std::uintptr_t>(this),
                reinterpret_cast<std::uintptr_t>(scr));
        }

        if (scr) {
            scr->need_update_visible_regions(true);
        }

        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WG_DTOR] phase=exit group=0x{:X} screen=0x{:X}",
            reinterpret_cast<std::uintptr_t>(this),
            reinterpret_cast<std::uintptr_t>(scr));
    }
'''
    wg=replace_once(wg,dtor_old,dtor_new,"window_group teardown diagnostics")

    # Scope gates: this build must remain an observation probe.
    final_combined=(sc+"\n"+wg).lower()
    for forbidden in ("eiksrvs","10003a4a","avkonfep.dll","100056de","rm-356"):
        if forbidden in final_combined:
            fail(f"target hardcode detected: {forbidden}")
    if "std::recursive_mutex focus_callback_mutex" in sc or "focus_callback_mutex.try_lock" in sc:
        fail("out-of-scope focus mutex behavior change detected")

    # Preserve the exact causal operations.
    for needle in (
        "const std::lock_guard<std::mutex> guard(focus_callback_mutex);",
        "callback.second(callback.first, focus, property);",
        "focus_callbacks.add(callback_pair)",
        "focus_callbacks.remove(cb)",
        "focus = find_group_to_focus(root.get());",
        "fire_focus_change_callbacks(focus_change_target);",
    ):
        if needle not in sc:
            fail(f"screen behavior lost: {needle}")

    for needle in (
        "set_receive_focus(false);",
        "scr->update_focus(&client->get_ws(), this);",
    ):
        if needle not in wg:
            fail(f"window_group behavior lost: {needle}")

    screen.write_text(sc,encoding="utf-8")
    wing.write_text(wg,encoding="utf-8")

    final=sc+"\n"+wg
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("focus_mutex_type=UNCHANGED_STD_MUTEX")
    print("focus_lock_scope=UNCHANGED")
    print("focus_callback_execution=UNCHANGED")
    print("window_group_teardown=UNCHANGED")
    print("ios_exit_choreography=UNCHANGED")
    print("B30_B31_B32_B33=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
