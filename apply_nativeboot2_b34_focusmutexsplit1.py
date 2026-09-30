#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B34 FOCUSMUTEXSPLIT1 after B33.

Root cause proven from B33 device stack + exact B33 reconstructed source:

window_server_client::~window_server_client()
  locks screen_mutex
  -> objects.clear()
  -> window_group::~window_group()
  -> screen::update_focus()
  -> screen::fire_focus_change_callbacks()
  -> attempts to lock the same non-recursive screen_mutex again.

B34 mirrors the narrow focus-callback portion of upstream EKA2L1 commit
2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d: add a dedicated
focus_callback_mutex and use it only for fire/add/remove focus callbacks.

It deliberately does NOT change window teardown, screen_mutex, redraw/mode
callback locking, iOS exit choreography, guest behavior, SVC tables, or FEP.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B34-FOCUSMUTEXSPLIT1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b34_focusmutexsplit1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    screen=up/"src/emu/services/src/window/screen.cpp"
    screen_h=up/"src/emu/services/include/services/window/screen.h"
    window=up/"src/emu/services/src/window/window.cpp"
    wing=up/"src/emu/services/src/window/classes/wingroup.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    ctx=up/"src/emu/services/src/context.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    root=up/"src/emu/ios/app/RootViewController.mm"

    for p in (screen,screen_h,window,wing,svc,ctx,thr,kern,sched,lib,root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sc=screen.read_text(encoding="utf-8")
    sh=screen_h.read_text(encoding="utf-8")
    win=window.read_text(encoding="utf-8")
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

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # Exact B33 baseline gates. These protect against accidentally applying the
    # fix to the newer upstream layout instead of this project's reconstruction.
    if "std::mutex screen_mutex;" not in sh:
        fail("B33 screen_mutex baseline missing")
    if "std::mutex focus_callback_mutex;" in sh:
        # Idempotent only if the functional marker and all three users exist.
        if "[NBOOT2][FOCUS_MUTEX_SPLIT]" in sc and sc.count("guard(focus_callback_mutex)") >= 3:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign focus_callback_mutex state")
    if "std::recursive_mutex" in sh or "std::recursive_mutex" in sc:
        fail("unexpected recursive mutex baseline")

    # Root-cause preservation gate: B34 fixes the nested mutex acquisition,
    # not the outer teardown lock or the object destruction choreography.
    dtor_start=win.find("window_server_client::~window_server_client()")
    dtor_end=win.find("void window_server_client::parse_command_buffer",dtor_start)
    if dtor_start < 0 or dtor_end < 0:
        fail("window_server_client destructor anchors missing")
    dtor=win[dtor_start:dtor_end]
    for needle in ("scr->screen_mutex.lock();","objects.clear();","scr->screen_mutex.unlock();"):
        if needle not in dtor:
            fail(f"root-cause teardown anchor missing: {needle}")
    if not (dtor.find("scr->screen_mutex.lock();") < dtor.find("objects.clear();") < dtor.find("scr->screen_mutex.unlock();")):
        fail("unexpected Wserv teardown lock ordering")

    # 1) Add a dedicated mutex adjacent to the existing screen mutex.
    header_old='''        kernel::chunk *screen_buffer_chunk;
        std::mutex screen_mutex;

        // Position of this screen in graphics driver
'''
    header_new='''        kernel::chunk *screen_buffer_chunk;
        // B34 FOCUSMUTEXSPLIT1:
        // Focus callbacks can be fired while screen_mutex is already held
        // during window teardown. Keep their registry on a separate mutex to
        // avoid same-thread re-lock of the non-recursive screen_mutex.
        std::mutex screen_mutex;
        std::mutex focus_callback_mutex;

        // Position of this screen in graphics driver
'''
    sh=replace_once(sh,header_old,header_new,"dedicated focus callback mutex")

    # 2) fire_focus_change_callbacks: only change the mutex being acquired.
    fire_old='''    void screen::fire_focus_change_callbacks(const focus_change_property property) {
        const std::lock_guard<std::mutex> guard(screen_mutex);

        for (auto &callback : focus_callbacks) {
            if (callback.second)
                callback.second(callback.first, focus, property);
        }
    }
'''
    fire_new='''    void screen::fire_focus_change_callbacks(const focus_change_property property) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);

        for (auto &callback : focus_callbacks) {
            if (callback.second)
                callback.second(callback.first, focus, property);
        }
    }
'''
    sc=replace_once(sc,fire_old,fire_new,"focus callback fire mutex split")

    # 3) add_focus_change_callback: serialize the same registry on the new mutex.
    add_old='''    std::size_t screen::add_focus_change_callback(void *userdata, focus_change_callback_handler handler) {
        const std::lock_guard<std::mutex> guard(screen_mutex);

        focus_change_callback callback_pair = { userdata, handler };
        return focus_callbacks.add(callback_pair);
    }
'''
    add_new='''    std::size_t screen::add_focus_change_callback(void *userdata, focus_change_callback_handler handler) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);
        LOG_INFO(SERVICE_WINDOW,
            "[NBOOT2][FOCUS_MUTEX_SPLIT] dedicated focus callback mutex active");

        focus_change_callback callback_pair = { userdata, handler };
        return focus_callbacks.add(callback_pair);
    }
'''
    sc=replace_once(sc,add_old,add_new,"focus callback add mutex split")

    # 4) remove_focus_change_callback: same registry, same dedicated mutex.
    remove_old='''    bool screen::remove_focus_change_callback(const std::size_t cb) {
        const std::lock_guard<std::mutex> guard(screen_mutex);
        return focus_callbacks.remove(cb);
    }
'''
    remove_new='''    bool screen::remove_focus_change_callback(const std::size_t cb) {
        const std::lock_guard<std::mutex> guard(focus_callback_mutex);
        return focus_callbacks.remove(cb);
    }
'''
    sc=replace_once(sc,remove_old,remove_new,"focus callback remove mutex split")

    # Scope gates.
    if "std::recursive_mutex" in sh or "std::recursive_mutex" in sc:
        fail("recursive mutex behavior change detected")
    if sc.count("guard(focus_callback_mutex)") != 3:
        fail(f"expected exactly 3 focus mutex guards, found {sc.count('guard(focus_callback_mutex)')}")
    if sc.count("[NBOOT2][FOCUS_MUTEX_SPLIT]") != 1:
        fail("B34 marker count is not exactly one")

    # Do not broaden the upstream batch: redraw/mode callback registry behavior
    # remains exactly on B33 for this milestone.
    for needle in (
        "std::size_t screen::add_screen_redraw_callback",
        "bool screen::remove_screen_redraw_callback",
        "std::size_t screen::add_screen_mode_change_callback",
        "bool screen::remove_screen_mode_change_callback",
    ):
        if needle not in sc:
            fail(f"unrelated callback function lost: {needle}")

    # Preserve guest and teardown causal operations.
    for needle in (
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

    combined=(sc+"\n"+sh+"\n"+win+"\n"+wg).lower()
    for forbidden in ("eiksrvs","10003a4a","avkonfep.dll","100056de","rm-356"):
        if forbidden in combined:
            fail(f"target hardcode detected: {forbidden}")

    screen_h.write_text(sh,encoding="utf-8")
    screen.write_text(sc,encoding="utf-8")

    print(f"{MARK}: applied")
    print("scope=FOCUS_CALLBACK_MUTEX_SPLIT_ONLY")
    print("upstream_reference=2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d")
    print("screen_mutex=UNCHANGED")
    print("focus_callback_mutex=DEDICATED_STD_MUTEX")
    print("window_teardown=UNCHANGED")
    print("redraw_mode_callback_locking=B33_UNCHANGED")
    print("ios_exit_choreography=UNCHANGED")
    print("guest_behavior=UNCHANGED")
    print("B30_B31_B32_B33=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
