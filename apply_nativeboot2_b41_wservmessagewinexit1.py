#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B41 WSERVMESSAGEWINEXIT1 after B40.

B40 device evidence proves a host-side shutdown crash:
- iOS EXC_BAD_ACCESS at 0x168 on the "Symbian OS thread";
- screen::need_update_visible_regions
  <- canvas_base::set_visible
  <- messagewin_anim_executor::~messagewin_anim_executor
  <- anim_dll::~anim_dll
  <- window_server_client::~window_server_client
  <- window_server::disconnect
  <- kernel_system::wipeout
  <- system_impl::~system_impl
  <- ios::os_thread;
- the exit trace stops at phase=os_join_begin.

MessageWin's executor stores a raw canvas pointer and its destructor restores the
canvas visibility. During kernel wipeout that canvas can already be in teardown.
B41 captures the kernel pointer while the canvas is known live and uses only
that stable pointer to detect wipeout before touching canvas_ in the destructor.

Normal MessageWin destruction still restores visibility. No generic canvas,
WindowServer dispatch, Loader, Leave/TRAP, scheduler, or iOS exit choreography
semantics are changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B41-WSERVMESSAGEWINEXIT1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b41_wservmessagewinexit1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/window/classes/plugins/anim/clock/messagewin.h"
    src=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    thread=up/"src/emu/ios/src/thread.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"

    for p in (hdr,src,loader,thread,winuser):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    h=hdr.read_text(encoding="utf-8")
    s=src.read_text(encoding="utf-8")
    ld=loader.read_text(encoding="utf-8")
    th=thread.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")

    if "[NBOOT2][LOADER_PDD]" not in ld:
        fail("B40 Loader PDD checkpoint missing")
    if "[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin" not in th:
        fail("B34 exit choreography checkpoint missing")
    if "void canvas_base::set_visible(const bool vis)" not in wu:
        fail("generic canvas visibility baseline missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    marker="[NBOOT2][WSERV_MESSAGEWIN_EXIT]"
    if marker in s:
        if "kernel_system *kern_;" in h and "kern_->wipeout_in_progress()" in s:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B41 state")

    hdr_old='''#include <services/window/classes/plugins/animdll.h>

namespace eka2l1::epoc {
    struct messagewin_anim_executor: public anim_executor {
    public:
'''
    hdr_new='''#include <services/window/classes/plugins/animdll.h>

namespace eka2l1 {
    class kernel_system;
}

namespace eka2l1::epoc {
    struct messagewin_anim_executor: public anim_executor {
    private:
        kernel_system *kern_;

    public:
'''
    h=replace_once(h,hdr_old,hdr_new,"MessageWin stable-kernel declaration")

    inc_old='''#include <services/window/classes/plugins/anim/clock/messagewin.h>
#include <services/window/classes/winuser.h>

#include <common/log.h>
'''
    inc_new='''#include <services/window/classes/plugins/anim/clock/messagewin.h>
#include <services/window/classes/winuser.h>
#include <services/window/window.h>

#include <kernel/kernel.h>

#include <common/log.h>
'''
    s=replace_once(s,inc_old,inc_new,"MessageWin kernel/window includes")

    ctor_old='''    messagewin_anim_executor::messagewin_anim_executor(canvas_base *canvas)
        : anim_executor(canvas) {
        canvas->set_visible(false);
    }
'''
    ctor_new='''    messagewin_anim_executor::messagewin_anim_executor(canvas_base *canvas)
        : anim_executor(canvas)
        , kern_(canvas->client->get_ws().get_kernel_system()) {
        canvas->set_visible(false);
    }
'''
    s=replace_once(s,ctor_old,ctor_new,"MessageWin constructor kernel capture")

    dtor_old='''    messagewin_anim_executor::~messagewin_anim_executor() {
        canvas_->set_visible(true);
    }
'''
    dtor_new='''    messagewin_anim_executor::~messagewin_anim_executor() {
        // During emulator wipeout the owning WindowServer client is destroying its
        // object table. canvas_ is only a borrowed pointer and may already refer to
        // a canvas in teardown, so do not dereference it merely to restore a visual
        // state that is about to be discarded anyway. kern_ was captured while the
        // canvas was live and remains valid for the duration of kernel_system::wipeout().
        if (kern_ && kern_->wipeout_in_progress()) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout");
            return;
        }

        canvas_->set_visible(true);
    }
'''
    s=replace_once(s,dtor_old,dtor_new,"MessageWin wipeout destructor guard")

    # Scope/ordering guards.
    for needle in (
        marker,
        "kernel_system *kern_;",
    ):
        if needle not in (h+"\n"+s):
            fail(f"post-apply semantic missing: {needle}")

    dtor=s.find("messagewin_anim_executor::~messagewin_anim_executor()")
    body=s[dtor:dtor+1800]
    guard=body.find("kern_->wipeout_in_progress()")
    restore=body.find("canvas_->set_visible(true);")
    if guard < 0 or restore < 0 or guard > restore:
        fail("post-apply wipeout guard does not precede canvas restore")

    # Never change generic canvas visibility for this shutdown-specific fix.
    if marker in wu:
        fail("B41 marker leaked into generic canvas visibility")

    hdr.write_text(h,encoding="utf-8")
    src.write_text(s,encoding="utf-8")

    print(f"{MARK}: applied")
    print("scope=MESSAGEWIN_DESTRUCTOR_WIPEOUT_GUARD_ONLY")
    print("evidence=IOS_EXC_BAD_ACCESS_0x168")
    print("normal_messagewin_restore=PRESERVED")
    print("generic_canvas_visibility=UNCHANGED")
    print("B34_B35_B36_B37_B38_B39_B40=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
