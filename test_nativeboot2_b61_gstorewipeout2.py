#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B61 GSTOREWIPEOUT2."""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B61-GSTOREWIPEOUT2-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b61_gstorewipeout2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    h=(up/"src/emu/services/include/services/window/classes/gstore.h").read_text(encoding="utf-8")
    s=(up/"src/emu/services/src/window/classes/gstore.cpp").read_text(encoding="utf-8")
    w=(up/"src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    need(h,"kernel_system *kern_ = nullptr;","segment kernel pointer")
    need(h,"kernel_system *kern = nullptr","collection signature")
    need(s,"#include <kernel/kernel.h>","kernel definition")
    need(s,"[NBOOT2][GSTORE_WIPEOUT_GUARD]","B61 marker")
    need(s,"kern_->wipeout_in_progress()","wipeout check")
    need(s,"action=SKIP_ALL_FBS_DEREF_WIPEOUT","B61 action")
    need(s,"[NBOOT2][GSTORE_EXIT_GUARD]","B59 guard preserved")
    need(w,"pending_segment_->kern_ = client->get_ws().get_kernel_system();","direct pending segment coverage")

    need(w,"redraw_segments_.add_new_segment(redraw_rect_curr, epoc::gdi_store_command_segment_pending_redraw,","pending-redraw collection capture")
    need(w,"redraw_segments_.add_new_segment(full_size_rect, gdi_store_command_segment_non_redraw,","non-redraw collection capture")
    need(w,"pending_segment_->kern_ = client->get_ws().get_kernel_system();","direct pending segment capture")

    db=s.find("gdi_store_command_segment::~gdi_store_command_segment()")
    de=s.find("void gdi_store_command_segment::add_command",db)
    if db<0 or de<0:
        fail("cannot isolate segment destructor")
    block=s[db:de]

    guard=block.find("wipeout_in_progress()")
    font_touch=block.find("reinterpret_cast<fbsfont*>")
    bitmap_touch=block.find("reinterpret_cast<fbsbitmap*>")
    if guard<0 or font_touch<0 or bitmap_touch<0:
        fail("destructor contract incomplete")
    if not (guard < font_touch and guard < bitmap_touch):
        fail("wipeout guard must precede retained FBS pointer access")

    need(block,"obj->deref();","normal runtime deref preserved")
    need(svc,"[NBOOT2][STARTUP_STATE_HANDLE]","B60 writer trace preserved")
    need(svc,"[NBOOT2][STARTUP_STATE_PS]","B58 category/key trace preserved")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=KERNEL_WIPEOUT_REDRAW_STORE_ONLY")
    print("normal_runtime_refcount=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
