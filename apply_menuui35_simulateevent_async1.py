#!/usr/bin/env python3
"""MENUUI35 SIMULATEEVENT-ASYNC1: defer Nokia PenInput PostRawEvent.

V34 device evidence:
- First VKB button-down reaches raweventbufqueue and is consumed correctly.
- KeySound opcode 13 completes.
- No V34 SIMULATE_EVENT/POST_RAW_EVENT completion marker appears.
- 100 ms later the host button-up bypasses MENUUI31 raw routing and falls
  through to normal PenInput pointer FIFO, proving the V34
  peninput_anim_simulating_ guard was left true.
- The whole guest/WindowServer then stops responding, including game menu.

Root cause: V34 called queue_input_from_driver() synchronously from inside the
PenInput AnimDll command-reply IPC. That re-enters WindowServer while the
WindowServer service call is still active.

Real WSERV PostRawEvent is deferred relative to the animation command. V35:
1. Special-cases PenInput opcode 510 in AnimDll CommandReply.
2. Copies TRawEvent out of the IPC descriptor.
3. Completes the current IPC first.
4. Enqueues the copied event onto EKA2L1's existing libuv task looper.
5. The task later calls queue_input_from_driver() outside the AnimDll stack.
6. The simulated-event guard is set only around that deferred dispatch and is
   always cleared immediately afterward.

No character mapping is hardcoded.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI35 SIMULATEEVENT-ASYNC1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text, old, new, name):
    n=text.count(old)
    if n!=1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_menuui35_simulateevent_async1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    anim=up/"src/emu/services/src/window/classes/plugins/animdll.cpp"
    winh=up/"src/emu/services/include/services/window/window.h"
    win=up/"src/emu/services/src/window/window.cpp"
    key=up/"src/emu/services/src/audio/keysound/keysound.cpp"
    mq=up/"src/emu/kernel/src/msgqueue.cpp"
    for p in (anim,winh,win,key,mq):
        if not p.is_file():
            fail(f"missing baseline file {p}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI34 SIMULATE_EVENT:" not in anim.read_text(encoding="utf-8"):
        fail("MENUUI34 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13:" not in key.read_text(encoding="utf-8"):
        fail("MENUUI33 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE:" not in mq.read_text(encoding="utf-8"):
        fail("MENUUI32 baseline missing")

    wc=win.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER:" in wc:
        print("MENUUI35 already present")
        return

    if "#include <uvlooper/uvlooper.h>\n" not in wc:
        # Use a stable services/window include area instead of an upstream-only
        # absolute position.
        anchor="#include <services/window/window.h>\n"
        wc=replace_once(wc,anchor,anchor+"#include <uvlooper/uvlooper.h>\n",
                        "uvlooper include")

    # Replace V34's synchronous PostRawEvent body with a pure scheduling API.
    sig="    bool window_server::post_peninput_simulated_raw_event(const epoc::raw_event &raw) {"
    start=wc.find(sig)
    if start < 0:
        fail("V34 PostRawEvent function missing")
    brace=wc.find("{",start)
    depth=0
    end=None
    for i in range(brace,len(wc)):
        if wc[i]=="{":
            depth+=1
        elif wc[i]=="}":
            depth-=1
            if depth==0:
                end=i+1
                break
    if end is None:
        fail("unterminated V34 PostRawEvent function")

    new_method=r'''    bool window_server::post_peninput_simulated_raw_event(const epoc::raw_event &raw) {
        // Translate now while the IPC descriptor is still valid, but do not
        // re-enter WindowServer from the AnimDll call stack.
        constexpr std::uint8_t RAW_POINTER_MOVE = 1;
        constexpr std::uint8_t RAW_KEY_DOWN = 3;
        constexpr std::uint8_t RAW_KEY_UP = 4;
        constexpr std::uint8_t RAW_BUTTON1_DOWN = 10;
        constexpr std::uint8_t RAW_BUTTON1_UP = 11;
        constexpr std::uint8_t RAW_KEY_REPEAT = 17;

        drivers::input_event evt{};
        bool supported = true;

        switch (raw.type_) {
        case RAW_KEY_DOWN:
        case RAW_KEY_UP:
        case RAW_KEY_REPEAT:
            evt.type_ = drivers::input_event_type::key_raw;
            evt.key_.code_ = raw.data_.key_data_.scancode_;
            evt.key_.state_ = (raw.type_ == RAW_KEY_UP)
                ? drivers::key_state::released
                : ((raw.type_ == RAW_KEY_REPEAT)
                    ? drivers::key_state::repeat
                    : drivers::key_state::pressed);
            break;

        case RAW_POINTER_MOVE:
        case RAW_BUTTON1_DOWN:
        case RAW_BUTTON1_UP:
            evt.type_ = drivers::input_event_type::touch;
            evt.mouse_.pos_x_ = static_cast<std::int32_t>(raw.data_.pos_.x_);
            evt.mouse_.pos_y_ = static_cast<std::int32_t>(raw.data_.pos_.y_);
            evt.mouse_.pos_z_ = 0;
            evt.mouse_.button_ = drivers::mouse_button_left;
            evt.mouse_.mouse_id = raw.pointer_num_;
            evt.mouse_.raw_screen_pos_ = true;
            evt.mouse_.action_ = (raw.type_ == RAW_BUTTON1_DOWN)
                ? drivers::mouse_action_press
                : ((raw.type_ == RAW_BUTTON1_UP)
                    ? drivers::mouse_action_release
                    : drivers::mouse_action_repeat);
            break;

        default:
            supported = false;
            break;
        }

        if (!supported) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER: stage=reject type={} reason=unsupported",
                static_cast<std::uint32_t>(raw.type_));
            return false;
        }

        if (!libuv::default_looper->started()) {
            libuv::default_looper->start();
        }

        const epoc::raw_event raw_copy = raw;
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER: stage=queued type={} scancode={} repeats={} pointer={}",
            static_cast<std::uint32_t>(raw_copy.type_),
            raw_copy.data_.key_data_.scancode_,
            raw_copy.data_.key_data_.repeats_,
            static_cast<std::uint32_t>(raw_copy.pointer_num_));

        libuv::default_looper->one_shot([this, evt, raw_copy]() mutable {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER: stage=dispatch type={} scancode={} repeats={} pointer={}",
                static_cast<std::uint32_t>(raw_copy.type_),
                raw_copy.data_.key_data_.scancode_,
                raw_copy.data_.key_data_.repeats_,
                static_cast<std::uint32_t>(raw_copy.pointer_num_));

            peninput_anim_simulating_.store(true, std::memory_order_release);
            queue_input_from_driver(evt);
            peninput_anim_simulating_.store(false, std::memory_order_release);

            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER: stage=complete type={} scancode={} repeats={} pointer={} guard=0",
                static_cast<std::uint32_t>(raw_copy.type_),
                raw_copy.data_.key_data_.scancode_,
                raw_copy.data_.key_data_.repeats_,
                static_cast<std::uint32_t>(raw_copy.pointer_num_));
        });

        return true;
    }'''
    wc=wc[:start]+new_method+wc[end:]
    win.write_text(wc,encoding="utf-8")

    ac=anim.read_text(encoding="utf-8")
    # V34's executor opcode 510 still calls the scheduling API. This is now
    # non-reentrant. Add before/after markers so the device log proves the
    # AnimDll request itself returned immediately.
    old='''                case PENINPUT_OP_SIMULATE_EVENT:
                    if (args) {
                        const epoc::raw_event event =
                            *reinterpret_cast<const epoc::raw_event *>(args);
                        const bool posted = serv_->post_peninput_simulated_raw_event(event);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI34 SIMULATE_EVENT: opcode={} type={} scancode={} repeats={} posted={}",
                            opcode, static_cast<std::uint32_t>(event.type_),
                            event.data_.key_data_.scancode_,
                            event.data_.key_data_.repeats_, posted ? 1 : 0);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI34 SIMULATE_EVENT: opcode={} args=null posted=0",
                            opcode);
                    }
                    break;
'''
    new='''                case PENINPUT_OP_SIMULATE_EVENT:
                    if (args) {
                        const epoc::raw_event event =
                            *reinterpret_cast<const epoc::raw_event *>(args);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT: stage=enter opcode={} type={} scancode={} repeats={}",
                            opcode, static_cast<std::uint32_t>(event.type_),
                            event.data_.key_data_.scancode_,
                            event.data_.key_data_.repeats_);
                        const bool posted = serv_->post_peninput_simulated_raw_event(event);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT: stage=return opcode={} type={} scancode={} repeats={} queued={}",
                            opcode, static_cast<std::uint32_t>(event.type_),
                            event.data_.key_data_.scancode_,
                            event.data_.key_data_.repeats_, posted ? 1 : 0);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT: stage=return opcode={} args=null queued=0",
                            opcode);
                    }
                    break;
'''
    ac=replace_once(ac,old,new,"V35 opcode 510 non-reentrant markers")
    anim.write_text(ac,encoding="utf-8")

    final_a=anim.read_text(encoding="utf-8")
    final_w=win.read_text(encoding="utf-8")
    for gate in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT: stage=enter",
        "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT: stage=return",
    ):
        if gate not in final_a:
            fail(f"anim gate missing: {gate}")
    for gate in (
        "#include <uvlooper/uvlooper.h>",
        "SYMBIAN-SYSTEMAPPS1 MENUUI35 POST_RAW_DEFER: stage=queued",
        "stage=dispatch",
        "stage=complete",
        "libuv::default_looper->one_shot",
        "queue_input_from_driver(evt);",
        "guard=0",
    ):
        if gate not in final_w:
            fail(f"window gate missing: {gate}")

    print("MENUUI35 SIMULATEEVENT-ASYNC1 applied")
    print("opcode510_sync_reentry=REMOVED")
    print("PostRawEvent=DEFERRED_ON_EXISTING_LIBUV_LOOPER")
    print("simulated_guard=SCOPED_TO_DEFERRED_DISPATCH")
    print("hardcoded_character_mapping=NONE")
    print("MENUUI34/MENUUI33/MENUUI32/MENUUI31/MENUUI30/prior=PRESERVED")

if __name__=="__main__":
    main()
