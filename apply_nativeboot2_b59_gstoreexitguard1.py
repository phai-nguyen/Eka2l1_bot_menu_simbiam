#!/usr/bin/env python3
"""NATIVEBOOT2 B59 GSTOREEXITGUARD1.

B58 DEVICE1 produced a host iOS crash when the user selected "Thoát Emulator".

Apple .ips:
  EXC_BAD_ACCESS / SIGSEGV / KERN_INVALID_ADDRESS 0x18

Fault stack:
  gdi_store_command_segment::~gdi_store_command_segment
  redraw_msg_canvas::~redraw_msg_canvas
  window_server_client::~window_server_client
  window_server::disconnect
  service::session::destroy
  kernel_system::wipeout

The redraw store retains FBS font/bitmap references. During global wipeout,
session destruction can leave a retained FBS object with no owner container.
ref_count_object::deref() decrements the final reference and then calls
owner->remove(this); if owner is null that final deref is unsafe.

B59 is deliberately narrow: only the redraw-store segment destructor avoids
the final deref when the object is null, already exhausted, or has exactly one
reference and no owner. Normal owned references continue through deref().
No drawing/state/startup behavior is changed.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B59-GSTOREEXITGUARD1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b59_gstoreexitguard1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/services/src/window/classes/gstore.cpp"
    if not p.is_file():
        fail(f"missing source: {p}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][GSTORE_EXIT_GUARD]" in text:
        print(MARK+": already applied")
        return

    if "#include <common/log.h>" not in text:
        anchor="#include <common/time.h>\n"
        if text.count(anchor)!=1:
            fail("common/time include anchor mismatch")
        text=text.replace(anchor,anchor+"#include <common/log.h>\n",1)

    begin="    gdi_store_command_segment::~gdi_store_command_segment() {\n"
    end="\n    void gdi_store_command_segment::add_command"
    b=text.find(begin)
    e=text.find(end,b)
    if b<0 or e<0:
        fail("segment destructor bounds not found")

    old=text[b:e]
    if old.count("reinterpret_cast<fbsfont*>(font_objects_[i])->deref();")!=1:
        fail("font deref anchor mismatch")
    if old.count("reinterpret_cast<fbsbitmap*>(bitmap_objects_[i])->deref();")!=1:
        fail("bitmap deref anchor mismatch")

    new='''    gdi_store_command_segment::~gdi_store_command_segment() {
        for (std::size_t i = 0; i < font_objects_.size(); i++) {
            fbsfont *obj = reinterpret_cast<fbsfont*>(font_objects_[i]);
            if (!obj || obj->count <= 0 || ((obj->count == 1) && !obj->owner)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][GSTORE_EXIT_GUARD] kind=font index={} object_present={} ref_count={} owner_present={} action=SKIP_UNSAFE_FINAL_DEREF",
                    i, obj ? 1 : 0, obj ? obj->count : 0, (obj && obj->owner) ? 1 : 0);
                continue;
            }

            obj->deref();
        }

        for (std::size_t i = 0; i < bitmap_objects_.size(); i++) {
            fbsbitmap *obj = reinterpret_cast<fbsbitmap*>(bitmap_objects_[i]);
            if (!obj || obj->count <= 0 || ((obj->count == 1) && !obj->owner)) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][GSTORE_EXIT_GUARD] kind=bitmap index={} object_present={} ref_count={} owner_present={} action=SKIP_UNSAFE_FINAL_DEREF",
                    i, obj ? 1 : 0, obj ? obj->count : 0, (obj && obj->owner) ? 1 : 0);
                continue;
            }

            obj->deref();
        }
    }
'''
    text=text[:b]+new+text[e:]

    if text.count("[NBOOT2][GSTORE_EXIT_GUARD]")!=2:
        fail("guard marker count mismatch")
    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=WINDOW_REDRAW_STORE_TEARDOWN_ONLY")
    print("crash=EXC_BAD_ACCESS_GDI_STORE_SEGMENT_DESTRUCTOR")
    print("guard=OWNERLESS_FINAL_FBS_REF")
    print("startup_behavior=UNCHANGED")
    print("B58_STATE_TRACE=PRESERVED")

if __name__=="__main__":
    main()
