#!/usr/bin/env python3
"""NATIVEBOOT2 B61 GSTOREWIPEOUT2.

B60 DEVICE1 reproduces the same host teardown crash as B58:
  EXC_BAD_ACCESS / SIGSEGV / invalid address 0x18
  gdi_store_command_segment::~gdi_store_command_segment
   -> redraw_msg_canvas::~redraw_msg_canvas
   -> window_server_client::~window_server_client
   -> kernel_system::wipeout

B59 protected only one narrow retained-FBS case (ownerless final ref) and one
device run exited cleanly, but B60 crashed again without the B59 guard firing.

B61 makes the teardown rule explicit and broader while remaining shutdown-only:
every redraw-store segment records the kernel pointer at creation time. If its
destructor runs while kernel_system::wipeout() is active, it does not touch any
retained FBS font/bitmap pointer at all.

Normal runtime destruction still executes the existing B59 refcount checks and
deref behavior unchanged.

This covers both:
- redraw_segments_ segments created by gdi_store_command_collection
- pending_segment_ created directly by redraw_msg_canvas

No guest boot, drawing, P&S, focus or compositor behavior is changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B61-GSTOREWIPEOUT2"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b61_gstorewipeout2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/window/classes/gstore.h"
    src=up/"src/emu/services/src/window/classes/gstore.cpp"
    win=up/"src/emu/services/src/window/classes/winuser.cpp"

    for p in (hdr,src,win):
        if not p.is_file():
            fail(f"missing source: {p}")

    h=hdr.read_text(encoding="utf-8")
    s=src.read_text(encoding="utf-8")
    w=win.read_text(encoding="utf-8")

    if "[NBOOT2][GSTORE_WIPEOUT_GUARD]" in s:
        print(MARK+": already applied")
        return

    if "[NBOOT2][GSTORE_EXIT_GUARD]" not in s:
        fail("B59 teardown guard missing")
    if "[NBOOT2][STARTUP_STATE_HANDLE]" not in (up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8"):
        fail("B60 writer trace missing")

    # Forward-declare kernel_system for a stable non-owning pointer on each segment.
    h=rep1(h,
'''namespace eka2l1::drivers {
    class graphics_driver;
}

namespace eka2l1::epoc {
''',
'''namespace eka2l1::drivers {
    class graphics_driver;
}

namespace eka2l1 {
    class kernel_system;
}

namespace eka2l1::epoc {
''',"kernel forward declaration")

    h=rep1(h,
'''    struct gdi_store_command_segment {
        gdi_store_command_segment_type type_;
        std::uint64_t creation_date_;

        common::region region_;
''',
'''    struct gdi_store_command_segment {
        gdi_store_command_segment_type type_;
        std::uint64_t creation_date_;
        kernel_system *kern_ = nullptr;

        common::region region_;
''',"segment kernel pointer")

    h=rep1(h,
'''        gdi_store_command_segment *add_new_segment(const eka2l1::rect &draw_rect, const gdi_store_command_segment_type type_);
''',
'''        gdi_store_command_segment *add_new_segment(const eka2l1::rect &draw_rect,
            const gdi_store_command_segment_type type_, kernel_system *kern = nullptr);
''',"add_new_segment signature")

    if "#include <kernel/kernel.h>" not in s:
        s=rep1(s,
'''#include <services/fbs/bitmap.h>

#include <common/time.h>
''',
'''#include <services/fbs/bitmap.h>

#include <kernel/kernel.h>

#include <common/time.h>
''',"kernel include")

    # B61 must run before B59 touches any retained pointer.
    dtor_anchor='''    gdi_store_command_segment::~gdi_store_command_segment() {
        for (std::size_t i = 0; i < font_objects_.size(); i++) {
'''
    dtor_new='''    gdi_store_command_segment::~gdi_store_command_segment() {
        if (kern_ && kern_->wipeout_in_progress()) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][GSTORE_WIPEOUT_GUARD] font_refs={} bitmap_refs={} action=SKIP_ALL_FBS_DEREF_WIPEOUT",
                font_objects_.size(), bitmap_objects_.size());
            return;
        }

        for (std::size_t i = 0; i < font_objects_.size(); i++) {
'''
    s=rep1(s,dtor_anchor,dtor_new,"wipeout early guard")

    old_sig='''    gdi_store_command_segment *gdi_store_command_collection::add_new_segment(const eka2l1::rect &draw_rect, const gdi_store_command_segment_type type) {
        std::unique_ptr<gdi_store_command_segment> new_segment = std::make_unique<gdi_store_command_segment>();

        new_segment->type_ = type;
'''
    new_sig='''    gdi_store_command_segment *gdi_store_command_collection::add_new_segment(const eka2l1::rect &draw_rect,
            const gdi_store_command_segment_type type, kernel_system *kern) {
        std::unique_ptr<gdi_store_command_segment> new_segment = std::make_unique<gdi_store_command_segment>();

        new_segment->kern_ = kern;
        new_segment->type_ = type;
'''
    s=rep1(s,old_sig,new_sig,"collection segment kernel capture")

    # Pass kernel to both collection-created segment sites.
    old1='''        redraw_segments_.add_new_segment(redraw_rect_curr, epoc::gdi_store_command_segment_pending_redraw);
'''
    new1='''        redraw_segments_.add_new_segment(redraw_rect_curr, epoc::gdi_store_command_segment_pending_redraw,
            client->get_ws().get_kernel_system());
'''
    w=rep1(w,old1,new1,"pending-redraw collection segment")

    old2='''                redraw_segments_.add_new_segment(full_size_rect, gdi_store_command_segment_non_redraw);
'''
    new2='''                redraw_segments_.add_new_segment(full_size_rect, gdi_store_command_segment_non_redraw,
                    client->get_ws().get_kernel_system());
'''
    w=rep1(w,old2,new2,"non-redraw collection segment")

    # Direct pending_segment_ does not pass through the collection.
    old3='''        if (!pending_segment_) {
            pending_segment_ = std::make_unique<gdi_store_command_segment>();
        }
'''
    new3='''        if (!pending_segment_) {
            pending_segment_ = std::make_unique<gdi_store_command_segment>();
            pending_segment_->kern_ = client->get_ws().get_kernel_system();
        }
'''
    w=rep1(w,old3,new3,"direct pending segment kernel capture")

    # Ordering/scope checks.
    db=s.find("gdi_store_command_segment::~gdi_store_command_segment()")
    de=s.find("void gdi_store_command_segment::add_command",db)
    block=s[db:de]
    guard=block.find("wipeout_in_progress()")
    first_obj_touch=min(
        x for x in [block.find("reinterpret_cast<fbsfont*>"),block.find("reinterpret_cast<fbsbitmap*>")]
        if x>=0)
    if guard<0 or guard>first_obj_touch:
        fail("wipeout guard must precede every retained FBS pointer dereference")
    if block.count("[NBOOT2][GSTORE_WIPEOUT_GUARD]")!=1:
        fail("B61 marker count mismatch in destructor")
    if block.count("[NBOOT2][GSTORE_EXIT_GUARD]")!=2:
        fail("B59 runtime guards not preserved")

    hdr.write_text(h,encoding="utf-8")
    src.write_text(s,encoding="utf-8")
    win.write_text(w,encoding="utf-8")

    print(MARK+": applied")
    print("scope=KERNEL_WIPEOUT_REDRAW_STORE_ONLY")
    print("policy=SKIP_ALL_RETAINED_FBS_DEREF_DURING_WIPEOUT")
    print("normal_runtime_refcount=PRESERVED")
    print("B59_RUNTIME_GUARDS=PRESERVED")
    print("B60_BOOT_DIAGNOSTICS=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
