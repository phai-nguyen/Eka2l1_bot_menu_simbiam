#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B49 POSTLOGOWSERV1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B49-POSTLOGOWSERV1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b49_postlogowserv1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    win_path=up/"src/emu/services/src/window/window.cpp"
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    files_path=up/"src/emu/services/src/fs/files.cpp"
    svc_path=up/"src/emu/kernel/src/svc.cpp"
    op_path=up/"src/emu/services/include/services/window/op.h"

    for p in (win_path,screen_path,files_path,svc_path,op_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    win=win_path.read_text(encoding="utf-8")
    screen=screen_path.read_text(encoding="utf-8")
    files=files_path.read_text(encoding="utf-8")
    svc=svc_path.read_text(encoding="utf-8")
    op=op_path.read_text(encoding="utf-8")

    for marker in (
        "[NBOOT2][POSTLOGO_WG_FIND]",
        "[NBOOT2][POSTLOGO_WG_CREATE]",
        "[NBOOT2][POSTLOGO_WG_ORDINAL]",
    ):
        need(win,marker,"window.cpp")
    need(screen,"[NBOOT2][POSTLOGO_FOCUS]","screen.cpp")

    # Authority for B48's candidate opcode.
    need(op,"ws_cl_op_find_window_group_identifier = 43","WindowServer opcode authority")

    # Diagnostic-only: preserve original completions.
    find_start=win.find("void window_server_client::find_window_group_id")
    find_end=win.find("void window_server_client::find_window_group_id_thread",find_start)
    if find_start<0 or find_end<0:
        fail("cannot isolate find_window_group_id")
    fb=win[find_start:find_end]
    need(fb,"ctx.complete(group->id);","find success result")
    need(fb,"ctx.complete(epoc::error_not_found);","find not-found result")

    ord_start=win.find("void window_server_client::set_window_group_ordinal_position")
    ord_end=win.find("struct def_mode_max_num_colors",ord_start)
    if ord_start<0 or ord_end<0:
        fail("cannot isolate ordinal handler")
    ob=win[ord_start:ord_end]
    need(ob,"group->set_position(set->ord_pos);","original ordinal mutation")
    need(ob,"ctx.complete(epoc::error_none);","ordinal original completion")
    if "ctx.complete(epoc::error_not_found);" in ob:
        fail("B49 must not substitute not-found for ordinal")

    foc_start=screen.find("epoc::window_group *screen::update_focus")
    foc_end=screen.find("epoc::window_group *screen::get_group_chain",foc_start)
    if foc_start<0 or foc_end<0:
        fail("cannot isolate update_focus")
    fob=screen[foc_start:foc_end]
    need(fob,"focus = find_group_to_focus(root.get());","original focus selection")
    need(fob,"return (new_focus_screen ? alternative_focus : focus);","original focus return")

    # Preserve predecessors.
    need(files,"[NBOOT2][XNTHEME_FSFLUSH]","B48 FileFlush")
    need(svc,"[NBOOT2][XNTHEME_IPC]","B48 xntheme IPC")
    need(svc,"[NBOOT2][AKNSKIN_TFX_WSERV]","B47 WindowServer")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("window_group_result_change=NONE")
    print("focus_result_change=NONE")
    print("ordinal_semantics_change=NONE")
    print("B48_FILEFLUSH_HEALTH=PRESERVED")
    print("B47_STOCK_TFX_SUPPRESSION=PRESERVED")

if __name__=="__main__":
    main()
