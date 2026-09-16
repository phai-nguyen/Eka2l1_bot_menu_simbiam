#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui16_advflag1.py <upstream-root>")

up = Path(sys.argv[1])
window = up / "src/emu/services/src/window/window.cpp"
winuser = up / "src/emu/services/src/window/classes/winuser.cpp"

for path in (window, winuser):
    if not path.is_file():
        raise SystemExit(f"MENUUI16: required source missing: {path}")

w = window.read_text(encoding="utf-8")
wu = winuser.read_text(encoding="utf-8")

authority_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_GET_FULL:"
if authority_marker not in w:
    raise SystemExit("MENUUI16: MENUUI15 authority marker missing")

if "case EWsWinOpEnableAdvancedPointers:" in wu:
    raise SystemExit("MENUUI16: EnableAdvancedPointers handler appeared; ADVFLAG1 premise changed")

master = "MENUUI16 ADVFLAG1: force legacy pointer modifier for A/B test"
runtime_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI16 ADVFLAG1:"
if runtime_marker in w:
    print("MENUUI16 ADVFLAG1 already present")
    raise SystemExit(0)

old = "        guest_evt_.adv_pointer_evt_.modifier = epoc::event_modifier_adv_pointer;"
if w.count(old) != 1:
    raise SystemExit(f"MENUUI16: expected exactly one unconditional advanced modifier assignment, got {w.count(old)}")

new = '''        // MENUUI16 ADVFLAG1: force legacy pointer semantics for the S60v5 A/B test.
        // MENUUI15 device logs showed no EnableAdvancedPointers/SendAdvancedPointerEvent opcode
        // while every delivered touch still carried event_modifier_adv_pointer.
        guest_evt_.adv_pointer_evt_.modifier = 0;
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI16 ADVFLAG1: forced_legacy=1 modifier=0 pointer={}",
            guest_evt_.adv_pointer_evt_.ptr_num);'''

w = w.replace(old, new, 1)

if old in w:
    raise SystemExit("MENUUI16: unconditional advanced modifier assignment still present")
if "guest_evt_.adv_pointer_evt_.modifier = 0;" not in w:
    raise SystemExit("MENUUI16: legacy modifier assignment missing")
if w.count(runtime_marker) != 1:
    raise SystemExit("MENUUI16: runtime marker postcondition failed")

window.write_text(w, encoding="utf-8")
print(master)
print("MENUUI16 ADVFLAG1: changed make_mouse_event modifier only; event type/coords/FIFO/GetEvent unchanged")
