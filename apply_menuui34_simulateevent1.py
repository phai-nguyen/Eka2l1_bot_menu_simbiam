#!/usr/bin/env python3
"""MENUUI34 SIMULATEEVENT1: implement Nokia PenInputAnim opcode 510 PostRawEvent.

V33 device evidence:
- Stock Nokia VKB is active and responsive.
- Raw touch queue is consumed correctly.
- KeySound opcode 13 now completes.
- After every VKB key action PenInputServer calls PenInputAnim opcode 510.
- MENUUI28 currently logs opcode 510 as passthrough=stub, so the translated
  TRawEvent never re-enters WindowServer and Msg. editor receives no key.

Nokia source semantics:
  EPeninputOpSimulateEvent = 510
  CommandReplyL reads TRawEvent from descriptor slot 1 and calls
  MAnimGeneralFunctions::PostRawEvent(event), while iIsSimulatedEvent prevents
  PenInputAnim from re-consuming its own injected event.

This patch implements the equivalent narrow bridge:
- EKeyDown/EKeyUp/EKeyRepeat -> WindowServer key_raw path.
- Pointer move/button1 down/up -> WindowServer raw-screen touch path.
- simulated-event guard bypasses MENUUI31 PenInput raw mirror to prevent loops.
No key/character mapping is hardcoded; Nokia's own TRawEvent scancode is used.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI34 SIMULATEEVENT1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text, old, new, name):
    n=text.count(old)
    if n!=1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_menuui34_simulateevent1.py <upstream-root>")
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
    if "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13:" not in key.read_text(encoding="utf-8"):
        fail("MENUUI33 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE:" not in mq.read_text(encoding="utf-8"):
        fail("MENUUI32 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW:" not in win.read_text(encoding="utf-8"):
        fail("MENUUI31 baseline missing")

    ac=anim.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI34 SIMULATE_EVENT:" in ac:
        print("MENUUI34 already present")
        return

    ac=replace_once(ac,
"""        constexpr std::int32_t PENINPUT_OP_CAPTURE_POINTER = 509;
        // RM-356's PenInput build includes RD_TACTILE_FEEDBACK, making
        // EPeninputOpEnalbeSprite opcode 516.
""",
"""        constexpr std::int32_t PENINPUT_OP_CAPTURE_POINTER = 509;
        constexpr std::int32_t PENINPUT_OP_SIMULATE_EVENT = 510;
        // RM-356's PenInput build includes RD_TACTILE_FEEDBACK, making
        // EPeninputOpEnalbeSprite opcode 516.
""","opcode 510 constant")

    ac=replace_once(ac,
"""                case PENINPUT_OP_CAPTURE_POINTER:
                    if (args) {
                        const bool captured = (*reinterpret_cast<const std::int32_t *>(args) != 0);
                        serv_->set_peninput_anim_pointer_capture(captured);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=capture captured={}",
                            opcode, captured ? 1 : 0);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=capture args=null",
                            opcode);
                    }
                    break;

                case PENINPUT_OP_ENABLE_SPRITE:
""",
"""                case PENINPUT_OP_CAPTURE_POINTER:
                    if (args) {
                        const bool captured = (*reinterpret_cast<const std::int32_t *>(args) != 0);
                        serv_->set_peninput_anim_pointer_capture(captured);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=capture captured={}",
                            opcode, captured ? 1 : 0);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=capture args=null",
                            opcode);
                    }
                    break;

                case PENINPUT_OP_SIMULATE_EVENT:
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

                case PENINPUT_OP_ENABLE_SPRITE:
""","opcode 510 handler")
    anim.write_text(ac,encoding="utf-8")

    wh=winh.read_text(encoding="utf-8")
    if "    struct raw_event;\n" not in wh:
        wh=replace_once(wh,
"""    struct window;
    struct window_key_shipper;
""",
"""    struct window;
    struct window_key_shipper;
    struct raw_event;
""","raw_event forward declaration")

    wh=replace_once(wh,
"""        std::atomic<bool> peninput_anim_pointer_captured_{ false };
        std::atomic<bool> peninput_anim_pen_down_{ false };
        std::atomic<bool> peninput_anim_sprite_enabled_{ true };
""",
"""        std::atomic<bool> peninput_anim_pointer_captured_{ false };
        std::atomic<bool> peninput_anim_pen_down_{ false };
        std::atomic<bool> peninput_anim_sprite_enabled_{ true };
        std::atomic<bool> peninput_anim_simulating_{ false };
""","simulated event guard state")

    wh=replace_once(wh,
"""        // Returns true exactly when real CPeninputAnim would consume the
        // pointer event and prevent normal WindowServer hit-test delivery.
        bool mirror_peninput_raw_event(const epoc::event &evt);
""",
"""        // Returns true exactly when real CPeninputAnim would consume the
        // pointer event and prevent normal WindowServer hit-test delivery.
        bool mirror_peninput_raw_event(const epoc::event &evt);

        // Equivalent of MAnimGeneralFunctions::PostRawEvent used by Nokia
        // PenInputAnim opcode 510.
        bool post_peninput_simulated_raw_event(const epoc::raw_event &evt);
""","PostRawEvent API")
    winh.write_text(wh,encoding="utf-8")

    wc=win.read_text(encoding="utf-8")
    wc=replace_once(wc,
"""    bool window_server::mirror_peninput_raw_event(const epoc::event &evt) {
        if (!peninput_anim_present_.load(std::memory_order_acquire)
            || !peninput_anim_active_.load(std::memory_order_acquire)
            || evt.type != epoc::event_code::touch) {
            return false;
        }
""",
"""    bool window_server::mirror_peninput_raw_event(const epoc::event &evt) {
        // Nokia CPeninputAnim::OfferRawEvent returns EFalse while processing
        // an event injected by its own SimulateEvent/PostRawEvent path.
        if (peninput_anim_simulating_.load(std::memory_order_acquire)) {
            return false;
        }

        if (!peninput_anim_present_.load(std::memory_order_acquire)
            || !peninput_anim_active_.load(std::memory_order_acquire)
            || evt.type != epoc::event_code::touch) {
            return false;
        }
""","simulated bypass in raw mirror")

    anchor="""    void window_server::queue_input_from_driver(drivers::input_event &evt) {
"""
    method="""    bool window_server::post_peninput_simulated_raw_event(const epoc::raw_event &raw) {
        // Symbian TRawEvent::TType values (e32event.h).
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
                "SYMBIAN-SYSTEMAPPS1 MENUUI34 POST_RAW_EVENT: type={} result=unsupported",
                static_cast<std::uint32_t>(raw.type_));
            return false;
        }

        // Match CPeninputAnim::iIsSimulatedEvent: injected raw events must
        // traverse normal WindowServer delivery but not be captured again by
        // the active PenInputAnim bridge.
        peninput_anim_simulating_.store(true, std::memory_order_release);
        queue_input_from_driver(evt);
        peninput_anim_simulating_.store(false, std::memory_order_release);

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI34 POST_RAW_EVENT: type={} scancode={} repeats={} pointer={} result=posted",
            static_cast<std::uint32_t>(raw.type_),
            raw.data_.key_data_.scancode_, raw.data_.key_data_.repeats_,
            static_cast<std::uint32_t>(raw.pointer_num_));
        return true;
    }

"""
    wc=replace_once(wc,anchor,method+anchor,"PostRawEvent implementation")
    win.write_text(wc,encoding="utf-8")

    final_a=anim.read_text(encoding="utf-8")
    final_h=winh.read_text(encoding="utf-8")
    final_w=win.read_text(encoding="utf-8")
    for gate in (
        "PENINPUT_OP_SIMULATE_EVENT = 510",
        "SYMBIAN-SYSTEMAPPS1 MENUUI34 SIMULATE_EVENT:",
        "post_peninput_simulated_raw_event(event)",
    ):
        if gate not in final_a:
            fail(f"anim gate missing: {gate}")
    for gate in (
        "peninput_anim_simulating_",
        "post_peninput_simulated_raw_event(const epoc::raw_event &raw)",
        "drivers::input_event_type::key_raw",
        "SYMBIAN-SYSTEMAPPS1 MENUUI34 POST_RAW_EVENT:",
        "queue_input_from_driver(evt);",
    ):
        if gate not in final_h+final_w:
            fail(f"window gate missing: {gate}")

    print("MENUUI34 SIMULATEEVENT1 applied")
    print("opcode510=EPeninputOpSimulateEvent_IMPLEMENTED")
    print("TRawEvent_key_down_up_repeat=POSTED_TO_WS")
    print("TRawEvent_pointer=POSTED_TO_WS_WITH_SIMULATED_GUARD")
    print("hardcoded_character_mapping=NONE")
    print("MENUUI33/MENUUI32/MENUUI31/MENUUI30/prior=PRESERVED")

if __name__=="__main__":
    main()
