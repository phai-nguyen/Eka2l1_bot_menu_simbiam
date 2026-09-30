#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B41 WSERVMESSAGEWINEXIT1.

B40 device crash evidence:
- host iOS EXC_BAD_ACCESS / SIGSEGV at 0x168;
- faulting host thread: "Symbian OS thread";
- stack:
  screen::need_update_visible_regions(bool)
  <- canvas_base::set_visible(bool)
  <- messagewin_anim_executor::~messagewin_anim_executor()
  <- anim_dll::~anim_dll()
  <- window_server_client::~window_server_client()
  <- window_server::disconnect()
  <- kernel_system::wipeout()
  <- system_impl::~system_impl()
  <- ios::os_thread()
- bridge log stops at [NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin.

B41 is narrowly scoped to the MessageWin animation destructor: retain a stable
kernel pointer when the executor is created and, while kernel wipeout is in
progress, do not touch the raw canvas pointer to restore visibility.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B41-WSERVMESSAGEWINEXIT1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b41_wservmessagewinexit1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/window/classes/plugins/anim/clock/messagewin.h"
    src=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    thread=up/"src/emu/ios/src/thread.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    window=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for p in (hdr,src,thread,loader,window,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    h=hdr.read_text(encoding="utf-8")
    s=src.read_text(encoding="utf-8")
    th=thread.read_text(encoding="utf-8")
    ld=loader.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

    # Canonical RED fails before B41 implementation.
    need(s,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 runtime marker")

    need(h,"kernel_system *kern_;","stable kernel pointer")
    need(s,"kern_(canvas->client->get_ws().get_kernel_system())","constructor kernel capture")
    need(s,"kern_->wipeout_in_progress()","wipeout guard")
    need(s,"phase=skip_restore_wipeout","wipeout skip marker")
    need(s,"canvas_->set_visible(true);","normal destructor restore preserved")

    # Guard ordering: wipeout check must occur before the raw canvas is touched.
    dtor=s.find("messagewin_anim_executor::~messagewin_anim_executor()")
    if dtor < 0:
        fail("messagewin destructor missing")
    body=s[dtor:dtor+1400]
    guard=body.find("wipeout_in_progress()")
    restore=body.find("canvas_->set_visible(true);")
    if guard < 0 or restore < 0 or guard > restore:
        fail("wipeout guard must precede canvas visibility restore")

    # Existing B40 / B34-B39 behavior must remain.
    need(ld,"[NBOOT2][LOADER_PDD]","B40 Loader PDD")
    need(th,"[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin","B34 exit choreography")
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral")
    need(sv,"[NBOOT2][EIKFEP_STATE]","B39 FEP diagnostics")

    # No blanket change to canvas visibility semantics.
    winuser=(up/"src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")
    need(winuser,"void canvas_base::set_visible(const bool vis)","canvas visibility implementation")
    if "[NBOOT2][WSERV_MESSAGEWIN_EXIT]" in winuser:
        fail("B41 marker leaked into generic canvas visibility path")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=MESSAGEWIN_DESTRUCTOR_WIPEOUT_GUARD_ONLY")
    print("host_crash=EXC_BAD_ACCESS_0x168")
    print("normal_messagewin_restore=PRESERVED")
    print("B34_B35_B36_B37_B38_B39_B40=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
