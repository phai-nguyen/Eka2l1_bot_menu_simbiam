#!/usr/bin/env python3
"""Source contract for B34 FOCUSMUTEXSPLIT1.

B33 device evidence plus B33-baseline source inspection proves a same-thread
self-deadlock during Exit Emulator:

window_server_client teardown
  -> lock screen_mutex
  -> objects.clear()
  -> window_group::~window_group()
  -> screen::update_focus()
  -> screen::fire_focus_change_callbacks()
  -> lock screen_mutex again

screen_mutex is std::mutex, so the second acquisition cannot complete.

B34 fixes only that boundary by giving the focus-callback registry its own
std::mutex. Window teardown, screen_mutex, callback invocation, iOS exit, and
all guest behavior remain unchanged.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B34-FOCUSMUTEXSPLIT1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def section(text: str, start: str, end: str, where: str) -> str:
    a=text.find(start)
    if a < 0:
        fail(f"missing section start in {where}: {start}")
    b=text.find(end,a+len(start))
    if b < 0:
        fail(f"missing section end in {where}: {end}")
    return text[a:b]

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b34_focusmutexsplit1.py <upstream-root>")

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
            fail(f"missing source file: {p}")

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

    # B34 keeps the existing screen mutex and introduces exactly a dedicated
    # non-recursive mutex for the focus callback registry.
    need(sh,"std::mutex screen_mutex;","screen.h existing screen mutex")
    need(sh,"std::mutex focus_callback_mutex;","screen.h dedicated focus callback mutex")
    if "std::recursive_mutex" in sh or "std::recursive_mutex" in sc:
        fail("B34 must not use recursive_mutex")
    if "screen_mutex = " in sh or "focus_callback_mutex = " in sh:
        fail("unexpected mutex replacement/alias")

    fire=section(
        sc,
        "void screen::fire_focus_change_callbacks",
        "void screen::fire_screen_redraw_callbacks",
        "screen.cpp fire_focus_change_callbacks")
    add=section(
        sc,
        "std::size_t screen::add_focus_change_callback",
        "bool screen::remove_focus_change_callback",
        "screen.cpp add_focus_change_callback")
    remove=section(
        sc,
        "bool screen::remove_focus_change_callback",
        "std::size_t screen::add_screen_redraw_callback",
        "screen.cpp remove_focus_change_callback")

    for name,body in (("fire",fire),("add",add),("remove",remove)):
        need(body,"focus_callback_mutex",f"{name} focus callback lock")
        if "guard(screen_mutex)" in body or "screen_mutex.lock()" in body:
            fail(f"{name} still acquires screen_mutex")

    need(fire,"const std::lock_guard<std::mutex> guard(focus_callback_mutex);","focus fire lock guard")
    need(fire,"callback.second(callback.first, focus, property);","focus callback invocation")
    need(add,"focus_callbacks.add(callback_pair)","focus callback add semantics")
    need(remove,"focus_callbacks.remove(cb)","focus callback remove semantics")

    # Binary-verifiable marker for the bounded functional change.
    need(add,"[NBOOT2][FOCUS_MUTEX_SPLIT]","B34 binary marker")

    # Preserve the exact teardown pattern that previously self-deadlocked:
    # screen_mutex remains held around objects.clear(); the fix is that focus
    # callbacks no longer try to acquire that same mutex.
    dtor=section(
        win,
        "window_server_client::~window_server_client()",
        "void window_server_client::parse_command_buffer",
        "window.cpp window_server_client destructor")
    need(dtor,"scr->screen_mutex.lock();","Wserv teardown screen lock")
    need(dtor,"objects.clear();","Wserv teardown object destruction")
    need(dtor,"scr->screen_mutex.unlock();","Wserv teardown screen unlock")
    if not (dtor.find("scr->screen_mutex.lock();") < dtor.find("objects.clear();") < dtor.find("scr->screen_mutex.unlock();")):
        fail("Wserv teardown lock/clear/unlock ordering changed")

    # Preserve window-group focus teardown and iOS exit behavior.
    need(wg,"set_receive_focus(false);","window_group destructor behavior")
    need(wg,"scr->update_focus(&client->get_ws(), this);","window_group focus update")
    need(sc,"focus = find_group_to_focus(root.get());","screen update_focus behavior")
    need(sc,"fire_focus_change_callbacks(focus_change_target);","focus notification behavior")

    # Scope: no target-specific behavior and no guest/firmware hardcode.
    combined=(sc+"\n"+sh+"\n"+win+"\n"+wg).lower()
    for forbidden in ("eiksrvs","10003a4a","avkonfep.dll","100056de","rm-356"):
        if forbidden in combined:
            fail(f"target hardcode detected: {forbidden}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
