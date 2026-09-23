#!/usr/bin/env python3
"""NATIVEBOOT2 B52 REDRAWSCHED1.

Selected from B51 DEVICE1.

B51 proves that during the initial Nokia splash interval:
- screen::redraw(driver) runs 170 times and returns performed=1 every time;
- the iOS redraw callback presents exactly those 170 frames;
- the host-only marker moves one-for-one with those presents;
- both redraw and present stop at 05:05:10.422;
- that B51 test exits only ~80 s after the first splash frame, before the
  normal ~120 s splash handoff seen in B49/B50.

B52 therefore does not fix scheduling. It observes the exact WindowServer
animation scheduler chain at the natural splash -> Startup transition and makes
the host marker much easier to see.

New marker:
  [NBOOT2][REDRAW_SCHED]

Observed scheduler phases:
- schedule_enter / schedule_done
- scan_arm / scan_reuse
- idle_enter
- scan_enter / scan_decision
- invoke_enter / invoke_redraw_done / invoke_done

B52 preserves all timing/event/screen-redraw semantics. It does not force a
redraw, present, focus change, z-order change or framebuffer clear.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B52-REDRAWSCHED1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def rep_between(text, begin, end, old, new, label):
    b=text.find(begin)
    e=text.find(end,b+1)
    if b<0 or e<0:
        fail(f"{label}: bounds not found")
    region=text[b:e]
    n=region.count(old)
    if n!=1:
        fail(f"{label}: expected one bounded anchor, found {n}")
    region=region.replace(old,new,1)
    return text[:b]+region+text[e:]

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b52_redrawsched1.py <upstream-root>")

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

    # B51/B50 authority must survive.
    for marker,where in (
        ("[NBOOT2][DIRECTSCREEN_PRESENT]",state),
        ("[NBOOT2][DIRECTSCREEN_REDRAW]",screen),
        ("[NBOOT2][POSTLOGO_FOCUS]",screen),
        ("[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]",winuser),
    ):
        if marker not in where:
            fail("missing predecessor marker: "+marker)

    sched_marker="[NBOOT2][REDRAW_SCHED]"
    if sched_marker in sched:
        print(MARK+": already applied")
        return

    # --------------------------------------------------------------
    # 1) Make B51 visual marker 4.8x larger and move it below the
    #    tiny top-left status area. Host overlay only.
    # --------------------------------------------------------------
    old='''                        eka2l1::rect b51_marker;
                        b51_marker.top = eka2l1::vec2(6 + b51_phase * 19, 6);
                        b51_marker.size = eka2l1::vec2(15, 15);
'''
    new='''                        eka2l1::rect b51_marker;
                        // B52: larger visual diagnostic requested after B51
                        // device test. 72 host pixels ~= 33 recording pixels.
                        b51_marker.top = eka2l1::vec2(24 + b51_phase * 96, 128);
                        b51_marker.size = eka2l1::vec2(72, 72);
'''
    state=rep_once(state,old,new,"B52 enlarge host marker")

    old='''                            b51_marker.top.x, b51_marker.top.y,
                            b51_marker.size.x, b51_marker.size.y);
'''
    new='''                            b51_marker.top.x, b51_marker.top.y,
                            b51_marker.size.x, b51_marker.size.y);
'''
    # Keep log spelling unchanged; geometry itself proves B52 marker sizing.

    # --------------------------------------------------------------
    # 2) Scheduler tracing. No state mutation is introduced.
    # --------------------------------------------------------------
    inc_anchor='''#include <services/window/screen.h>

#include <cassert>
'''
    inc_new='''#include <services/window/screen.h>

#include <common/log.h>

#include <cassert>
'''
    sched=rep_once(sched,inc_anchor,inc_new,"scheduler log include")

    ns_anchor='''namespace eka2l1::epoc {
    static void on_anim_due'''
    ns_new='''namespace eka2l1::epoc {
    static bool b52_track_screen(screen *scr) {
        if (!scr || scr->number != 0 || !scr->focus) {
            return false;
        }

        const int focus_id = scr->focus->id;
        return (focus_id == 3) || (focus_id == 63) || (focus_id == 75);
    }

    static int b52_focus_id(screen *scr) {
        return (scr && scr->focus) ? scr->focus->id : 0;
    }

    static void on_anim_due'''
    sched=rep_once(sched,ns_anchor,ns_new,"scheduler helper")

    # schedule(): observe request/coalescing state.
    begin="    void animation_scheduler::schedule(drivers::graphics_driver *driver, screen *scr, const std::uint64_t time) {"
    end="\n    void animation_scheduler::unschedule(const int screen_number) {"
    anchor='''        // Get the schedule
        anim_schedule sched;
'''
    block='''        const bool b52_track = b52_track_screen(scr);
        if (b52_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=schedule_enter screen={} focus_id={} request_time={} now={} schedule_before={} state_flags={} callback_scheduled={} behavior=OBSERVE_ONLY",
                scr->number, b52_focus_id(scr), time, timing_->microseconds(),
                schedules_[scr->number].scheduled ? 1 : 0,
                static_cast<int>(states_[scr->number].flags),
                callback_scheduled_ ? 1 : 0);
        }

        // Get the schedule
        anim_schedule sched;
'''
    sched=rep_between(sched,begin,end,anchor,block,"schedule enter")

    anchor='''        schedule_scans(driver);
    }
'''
    block='''        schedule_scans(driver);

        if (b52_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=schedule_done screen={} focus_id={} schedule_after={} scheduled_time={} state_flags={} callback_scheduled={} behavior=OBSERVE_ONLY",
                scr->number, b52_focus_id(scr),
                schedules_[scr->number].scheduled ? 1 : 0,
                schedules_[scr->number].time,
                static_cast<int>(states_[scr->number].flags),
                callback_scheduled_ ? 1 : 0);
        }
    }
'''
    sched=rep_between(sched,begin,end,anchor,block,"schedule done")

    # scan_for_redraw(): capture decision.
    begin="    void animation_scheduler::scan_for_redraw(drivers::graphics_driver *driver, const int screen_number, const bool force_redraw) {"
    end="\n    void animation_scheduler::invoke_due_animation(drivers::graphics_driver *driver, const int screen_number) {"

    anchor='''        if (sched) {
            // Get screen state, check if it's active
'''
    block='''        if (sched) {
            const bool b52_track = b52_track_screen(sched->scr);
            if (b52_track) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][REDRAW_SCHED] phase=scan_enter screen={} focus_id={} force={} state_flags={} scheduled_time={} now={} behavior=OBSERVE_ONLY",
                    screen_number, b52_focus_id(sched->scr), force_redraw ? 1 : 0,
                    static_cast<int>(states_[screen_number].flags),
                    sched->time, timing_->microseconds());
            }

            // Get screen state, check if it's active
'''
    sched=rep_between(sched,begin,end,anchor,block,"scan enter")

    anchor='''                    if (until_due == 0) {
                        // Invoke the due right away.
'''
    block='''                    if (until_due == 0) {
                        if (b52_track) {
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][REDRAW_SCHED] phase=scan_decision screen={} focus_id={} action=invoke_now until_due={} state_flags={} behavior=OBSERVE_ONLY",
                                screen_number, b52_focus_id(sched->scr), until_due,
                                static_cast<int>(scr_state.flags));
                        }

                        // Invoke the due right away.
'''
    sched=rep_between(sched,begin,end,anchor,block,"scan invoke decision")

    anchor='''                    } else {
                        scr_state.time_expected_redraw = now + until_due;
                        scr_state.flags = screen_state::scheduled;
'''
    block='''                    } else {
                        if (b52_track) {
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][REDRAW_SCHED] phase=scan_decision screen={} focus_id={} action=arm_due_event until_due={} expected={} state_flags_before={} behavior=OBSERVE_ONLY",
                                screen_number, b52_focus_id(sched->scr), until_due,
                                now + until_due, static_cast<int>(scr_state.flags));
                        }

                        scr_state.time_expected_redraw = now + until_due;
                        scr_state.flags = screen_state::scheduled;
'''
    sched=rep_between(sched,begin,end,anchor,block,"scan event decision")

    # Existing scheduled event retained: record the coalescing decision.
    anchor='''                    } else {
                        should_update = false;
                    }
'''
    block='''                    } else {
                        if (b52_track) {
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][REDRAW_SCHED] phase=scan_decision screen={} focus_id={} action=reuse_existing until_due={} expected={} now={} behavior=OBSERVE_ONLY",
                                screen_number, b52_focus_id(sched->scr), until_due,
                                scr_state.time_expected_redraw, now);
                        }
                        should_update = false;
                    }
'''
    sched=rep_between(sched,begin,end,anchor,block,"scan reuse decision")

    # invoke_due_animation(): prove arrival at the actual redraw.
    begin="    void animation_scheduler::invoke_due_animation(drivers::graphics_driver *driver, const int screen_number) {"
    end="\n    void animation_scheduler::idle_callback(drivers::graphics_driver *driver) {"

    anchor='''        epoc::screen *scr = sched->scr;

        assert(sched && "The returned schedule should not be nullptr");
'''
    block='''        epoc::screen *scr = sched->scr;
        const bool b52_track = b52_track_screen(scr);

        if (b52_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=invoke_enter screen={} focus_id={} schedule_time={} state_flags={} now={} behavior=OBSERVE_ONLY",
                screen_number, b52_focus_id(scr), sched->time,
                static_cast<int>(states_[screen_number].flags),
                timing_->microseconds());
        }

        assert(sched && "The returned schedule should not be nullptr");
'''
    sched=rep_between(sched,begin,end,anchor,block,"invoke enter")

    anchor='''                scr->redraw(driver);
            }

            kern_->unlock();
'''
    block='''                scr->redraw(driver);
                if (b52_track) {
                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][REDRAW_SCHED] phase=invoke_redraw_done screen={} focus_id={} now={} behavior=OBSERVE_ONLY",
                        screen_number, b52_focus_id(scr), timing_->microseconds());
                }
            }

            kern_->unlock();
'''
    sched=rep_between(sched,begin,end,anchor,block,"invoke redraw done")

    anchor='''            states_[screen_number].flags = screen_state::inactive;
        }
    }
'''
    block='''            states_[screen_number].flags = screen_state::inactive;
        }

        if (b52_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=invoke_done screen={} focus_id={} state_flags={} schedule_pending={} callback_scheduled={} behavior=OBSERVE_ONLY",
                screen_number, b52_focus_id(scr),
                static_cast<int>(states_[screen_number].flags),
                schedules_[screen_number].scheduled ? 1 : 0,
                callback_scheduled_ ? 1 : 0);
        }
    }
'''
    sched=rep_between(sched,begin,end,anchor,block,"invoke done")

    # idle callback: proves the 500-us scan callback fired.
    begin="    void animation_scheduler::idle_callback(drivers::graphics_driver *driver) {"
    end="\n    void animation_scheduler::schedule_scans(drivers::graphics_driver *driver) {"
    anchor='''        callback_scheduled_ = false;

        for (int screen_num = 0; screen_num < states_.size(); screen_num++) {
'''
    block='''        callback_scheduled_ = false;

        if (!schedules_.empty() && schedules_[0].scheduled &&
            b52_track_screen(schedules_[0].scr)) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=idle_enter screen=0 focus_id={} schedule_pending=1 state_flags={} now={} behavior=OBSERVE_ONLY",
                b52_focus_id(schedules_[0].scr),
                static_cast<int>(states_[0].flags), timing_->microseconds());
        }

        for (int screen_num = 0; screen_num < states_.size(); screen_num++) {
'''
    sched=rep_between(sched,begin,end,anchor,block,"idle enter")

    # schedule_scans(): distinguish newly armed scan callback vs coalesced reuse.
    begin="    void animation_scheduler::schedule_scans(drivers::graphics_driver *driver) {"
    anchor='''        if (!callback_scheduled_) {
            // Schedule it
'''
    block='''        const bool b52_track =
            !schedules_.empty() && schedules_[0].scheduled &&
            b52_track_screen(schedules_[0].scr);

        if (!callback_scheduled_) {
            if (b52_track) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][REDRAW_SCHED] phase=scan_arm screen=0 focus_id={} callback_before=0 delay_us={} now={} behavior=OBSERVE_ONLY",
                    b52_focus_id(schedules_[0].scr), scheduled_us,
                    timing_->microseconds());
            }

            // Schedule it
'''
    sched=rep_once(sched,anchor,block,"scan arm")

    anchor='''            callback_scheduled_ = true;
        }
    }
'''
    block='''            callback_scheduled_ = true;
        } else if (b52_track) {
            LOG_WARN(SERVICE_WINDOW,
                "[NBOOT2][REDRAW_SCHED] phase=scan_reuse screen=0 focus_id={} callback_before=1 now={} behavior=OBSERVE_ONLY",
                b52_focus_id(schedules_[0].scr), timing_->microseconds());
        }
    }
'''
    sched=rep_once(sched,anchor,block,"scan reuse")

    # Postconditions.
    if sched.count(sched_marker) < 8:
        fail(f"expected scheduler probe sites, got {sched.count(sched_marker)}")
    if "[NBOOT2][DIRECTSCREEN_PRESENT]" not in state:
        fail("B51 present marker lost")
    if "[NBOOT2][DIRECTSCREEN_REDRAW]" not in screen:
        fail("B51 redraw marker lost")
    if "b51_marker.size = eka2l1::vec2(72, 72);" not in state:
        fail("large B52 marker not applied")

    # No forced redraw/present paths may be added by B52.
    if sched.count("scr->redraw(driver);") != 1:
        fail("scheduler redraw call count changed")

    state_path.write_text(state,encoding="utf-8")
    sched_path.write_text(sched,encoding="utf-8")

    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("marker_size=72x72")
    print("marker_y=128")
    print("scheduler_semantics_change=NONE")
    print("guest_redraw_forced=NONE")
    print("extra_present=NONE")
    print("B51_DIRECTSCREEN=PRESERVED")

if __name__=="__main__":
    main()
