#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B52 REDRAWSCHED1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B52-REDRAWSCHED1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b52_redrawsched1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    state_path=up/"src/emu/ios/src/state.cpp"
    screen_path=up/"src/emu/services/src/window/screen.cpp"
    sched_path=up/"src/emu/services/src/window/scheduler.cpp"
    winuser_path=up/"src/emu/services/src/window/classes/winuser.cpp"

    for p in (state_path,screen_path,sched_path,winuser_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    state=state_path.read_text(encoding="utf-8")
    screen=screen_path.read_text(encoding="utf-8")
    sched=sched_path.read_text(encoding="utf-8")
    winuser=winuser_path.read_text(encoding="utf-8")

    # New B52 scheduler marker and phases.
    need(sched,"[NBOOT2][REDRAW_SCHED]","scheduler.cpp")
    for phase in (
        "phase=schedule_enter",
        "phase=schedule_done",
        "phase=scan_arm",
        "phase=scan_reuse",
        "phase=idle_enter",
        "phase=scan_enter",
        "phase=scan_decision",
        "phase=invoke_enter",
        "phase=invoke_redraw_done",
        "phase=invoke_done",
    ):
        need(sched,phase,"scheduler phase")

    # B52 visual marker must be clearly larger than B51.
    need(state,"b51_marker.size = eka2l1::vec2(72, 72);","large marker")
    need(state,"b51_marker.top = eka2l1::vec2(24 + b51_phase * 96, 128);","large marker position")

    # Preserve B51/B50 diagnostics.
    need(state,"[NBOOT2][DIRECTSCREEN_PRESENT]","B51 host present")
    need(screen,"[NBOOT2][DIRECTSCREEN_REDRAW]","B51 redraw")
    need(screen,"[NBOOT2][POSTLOGO_FOCUS]","B49/B50 focus")
    need(winuser,"[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]","B50 canvas activation")

    # Scheduler semantics must remain the same.
    s=sched.find("void animation_scheduler::schedule(")
    e=sched.find("void animation_scheduler::unschedule",s)
    if s<0 or e<0:
        fail("cannot isolate scheduler::schedule")
    sb=sched[s:e]
    need(sb,"const std::lock_guard<std::mutex> guard(lock_);","schedule lock")
    need(sb,"schedules_[scr->number].time = time;","schedule coalesce")
    need(sb,"schedules_[scr->number] = sched;","schedule replace")
    need(sb,"schedule_scans(driver);","schedule scan arm")

    s=sched.find("void animation_scheduler::scan_for_redraw")
    e=sched.find("void animation_scheduler::invoke_due_animation",s)
    if s<0 or e<0:
        fail("cannot isolate scan_for_redraw")
    scan=sched[s:e]
    need(scan,"timing_->unschedule_event(anim_due_evt_","existing event cancel")
    need(scan,"timing_->schedule_event(static_cast<int64_t>(until_due), anim_due_evt_","existing due event")
    need(scan,"invoke_due_animation(driver, screen_number);","existing immediate invoke")

    s=sched.find("void animation_scheduler::invoke_due_animation")
    e=sched.find("void animation_scheduler::idle_callback",s)
    if s<0 or e<0:
        fail("cannot isolate invoke_due_animation")
    ib=sched[s:e]
    if ib.count("scr->redraw(driver);")!=1:
        fail("invoke_due_animation must call redraw exactly once")
    need(ib,"states_[screen_number].flags = screen_state::inactive;","state reset")

    s=sched.find("void animation_scheduler::schedule_scans")
    if s<0:
        fail("cannot isolate schedule_scans")
    ss=sched[s:]
    need(ss,"static constexpr std::uint16_t scheduled_us = 500;","scan delay")
    if ss.count("timing_->schedule_event(scheduled_us, callback_evt_")!=1:
        fail("scan callback schedule count changed")

    # B52 must not create a timer/present/redraw outside existing paths.
    if "builder.present(" in sched or "screen::redraw(" in sched:
        fail("unexpected host/forced-redraw code in scheduler")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("marker_size=72x72")
    print("scheduler_semantics_change=NONE")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("B51_DIRECTSCREEN=PRESERVED")

if __name__=="__main__":
    main()
