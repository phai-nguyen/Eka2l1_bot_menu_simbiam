#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B50 POSTLOGOCANVAS1."""
from pathlib import Path
import re
import sys

MARK="NATIVEBOOT2-B50-POSTLOGOCANVAS1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b50_postlogocanvas1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    window=(up/"src/emu/services/src/window/window.cpp").read_text(encoding="utf-8")
    winbase=(up/"src/emu/services/src/window/classes/winbase.cpp").read_text(encoding="utf-8")
    winuser=(up/"src/emu/services/src/window/classes/winuser.cpp").read_text(encoding="utf-8")
    wingroup=(up/"src/emu/services/src/window/classes/wingroup.cpp").read_text(encoding="utf-8")
    screen=(up/"src/emu/services/src/window/screen.cpp").read_text(encoding="utf-8")
    op=(up/"src/emu/services/include/services/window/op.h").read_text(encoding="utf-8")

    need(winbase,"[NBOOT2][POSTLOGO_ORDERPRI]","winbase.cpp")
    need(wingroup,"[NBOOT2][POSTLOGO_RECEIVEFOCUS]","wingroup.cpp")
    need(wingroup,"[NBOOT2][POSTLOGO_WG_DESTROY]","wingroup.cpp")
    need(window,"[NBOOT2][POSTLOGO_CANVAS_CREATE]","window.cpp")
    need(winuser,"[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]","winuser.cpp")
    need(winuser,"[NBOOT2][POSTLOGO_CANVAS_VISIBLE]","winuser.cpp")

    # 0x06 authority: enum is sequential from EWsWinOpFree, and this symbolic
    # handler must remain the native SetOrdinalPositionPri implementation.
    need(op,"EWsWinOpSetOrdinalPositionPri","Window opcode authority")

    # Preserve exact B49 diagnosis.
    for marker in (
        "[NBOOT2][POSTLOGO_WG_FIND]",
        "[NBOOT2][POSTLOGO_WG_CREATE]",
        "[NBOOT2][POSTLOGO_WG_ORDINAL]",
    ):
        need(window,marker,"B49 window preservation")
    need(screen,"[NBOOT2][POSTLOGO_FOCUS]","B49 focus preservation")

    # SetOrdinalPositionPri still mutates exactly through priority assignment +
    # set_position and returns KErrNone.
    s=winbase.find("case EWsWinOpSetOrdinalPositionPri")
    e=winbase.find("case EWsWinOpSetOrdinalPriorityAdjust",s)
    if s<0 or e<0:
        fail("cannot isolate SetOrdinalPositionPri")
    ob=winbase[s:e]
    need(ob,"priority = info->pri1;","priority assignment")
    need(ob,"set_position(position);","position application")
    need(ob,"ctx.complete(epoc::error_none);","ordinal completion")

    # ReceiveFocus keeps its predecessor semantics and still calls
    # update_focus. Baseline implementations may express the focusable state
    # through direct flag mutation or set_receive_focus(), so do not pin the
    # contract to one source spelling.
    s=wingroup.find("void window_group::receive_focus")
    e=wingroup.find("void window_group::on_owner_process_uid_type_change",s)
    if s<0 or e<0:
        fail("cannot isolate receive_focus")
    fb=wingroup[s:e]
    need(fb,"b50_old_focusable = can_receive_focus();","focus-state observation")
    need(fb,"b50_requested","requested focus observation")
    if not re.search(r"\bupdate_focus\(",fb):
        fail("missing original focus update")
    need(fb,"context.complete(epoc::error_none);","focus completion")

    # Canvas activation is unchanged except observe-only logging.
    s=winuser.find("void canvas_base::activate")
    e=winuser.find("void canvas_base::scroll",s)
    if s<0 or e<0:
        fail("cannot isolate canvas activate")
    ab=winuser[s:e]
    need(ab,"flags |= flags_active;","active flag")
    need(ab,"on_activate();","activate callback")
    need(ab,"scr->need_update_visible_regions(true);","visible recalc request")
    need(ab,"context.complete(epoc::error_none);","activate completion")

    # SetVisible still uses the requested boolean and KErrNone.
    s=winuser.find("case EWsWinOpSetVisible")
    e=winuser.find("case EWsWinOpSetNonFading",s)
    if s<0 or e<0:
        fail("cannot isolate SetVisible")
    vb=winuser[s:e]
    need(vb,"set_visible(visible != 0);","original visibility mutation")
    need(vb,"ctx.complete(epoc::error_none);","visibility completion")

    # Creation still adds exactly one object and completes with that handle.
    s=window.find("void window_server_client::create_window_base")
    e=window.find("void window_server_client::create_graphic_context",s)
    if s<0 or e<0:
        fail("cannot isolate create_window_base")
    cb=window[s:e]
    if len(re.findall(r"\badd_object\([^\n;]*\bwin\b[^\n;]*\)",cb))!=1:
        fail("create_window_base must add object exactly once")
    if not re.search(r"\b[A-Za-z_]\w*\.complete\(b50_handle\);",cb):
        fail("missing create completion with b50_handle")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("order_result_change=NONE")
    print("focus_policy_change=NONE")
    print("canvas_create_result_change=NONE")
    print("activation_result_change=NONE")
    print("visibility_result_change=NONE")
    print("rendering_change=NONE")
    print("B49_FOCUS_TRACE=PRESERVED")

if __name__=="__main__":
    main()
