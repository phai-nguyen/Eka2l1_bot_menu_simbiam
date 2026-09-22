#!/usr/bin/env python3
"""Source contract for B34 FOCUSLOCKDIAG1.

B33 device evidence localizes Exit Emulator hang to:
bridge shutdown -> os_join_begin -> Symbian OS thread teardown
-> window_group::~window_group -> screen::update_focus
-> screen::fire_focus_change_callbacks -> wait on focus_callback_mutex.

B34 is diagnostic-only. It must trace focus callback lock ownership/reentry
without changing the mutex type, callback execution semantics, window teardown,
or iOS exit choreography.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B34-FOCUSLOCKDIAG1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b34_focuslockdiag1.py <upstream-root>")

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
            fail(f"missing source file: {p}")

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

    # Preserve the device-proven chain and prior diagnostics.
    need(lm,"[NBOOT2][LDR_ROOT_RESOLVED]","B30 preservation")
    need(sch,"[NBOOT2][SCHED_STALE_READY_DROP]","B31 preservation")
    need(ke,"[NBOOT2][EIKFAULT_AV]","B32 preservation")
    need(sv,"[NBOOT2][EIKFAULT_LEAVE]","B32 preservation")
    need(lm,"[NBOOT2][EIKFAULT_SVCMISS]","B32 preservation")
    need(sv,"[NBOOT2][EIKCANCEL_LLE]","B33 preservation")
    need(cx,"[NBOOT2][EIKCANCEL_HLE]","B33 preservation")
    need(th,"[NBOOT2][EIKCANCEL_NOTIFY]","B33 preservation")
    need(rt,"[NBOOT2][IOS_EXIT_UI] phase=shutdown_requested","B26 exit preservation")

    # B34 lock lifecycle markers.
    for needle in (
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
    ):
        need(sc,needle,"screen.cpp B34 diagnostics")

    for needle in (
        "[NBOOT2][WG_DTOR]",
        "phase=enter",
        "phase=focus_update_begin",
        "phase=focus_update_done",
        "phase=exit",
    ):
        need(wg,needle,"wingroup.cpp B34 teardown diagnostics")

    # Every lock trace must carry a monotonic sequence and host-thread identity.
    need(sc,"nboot2_b34_focus_seq","screen.cpp sequence counter")
    need(sc,"nboot2_b34_host_thread_tag","screen.cpp host thread tag")
    need(sc,"seq={}","screen.cpp sequence fields")
    need(sc,"host_tid=0x{:X}","screen.cpp host-thread fields")

    # Diagnostic-only: preserve the exact non-recursive mutex and callback-under-lock behavior.
    need(sh,"std::mutex focus_callback_mutex;","screen.h mutex type")
    if "std::recursive_mutex focus_callback_mutex" in sh or "std::recursive_mutex focus_callback_mutex" in sc:
        fail("focus callback mutex changed to recursive mutex")
    if "focus_callback_mutex.try_lock" in sc:
        fail("B34 must not change lock acquisition semantics")

    need(sc,"const std::lock_guard<std::mutex> guard(focus_callback_mutex);","focus mutex lock guard")
    need(sc,"callback.second(callback.first, focus, property);","focus callback invocation")
    need(sc,"focus_callbacks.add(callback_pair)","focus callback add semantics")
    need(sc,"focus_callbacks.remove(cb)","focus callback remove semantics")

    # Preserve teardown/focus behavior byte-for-byte at the causal boundary.
    need(wg,"set_receive_focus(false);","window_group destructor behavior")
    need(wg,"scr->update_focus(&client->get_ws(), this);","window_group destructor focus update")
    need(sc,"focus = find_group_to_focus(root.get());","screen update_focus behavior")
    need(sc,"fire_focus_change_callbacks(focus_change_target);","focus notification behavior")

    # B34 must not special-case the observed app/firmware.
    combined=(sc+"\n"+wg).lower()
    for forbidden in ("eiksrvs","10003a4a","avkonfep.dll","100056de","rm-356"):
        if forbidden in combined:
            fail(f"target hardcode detected: {forbidden}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
