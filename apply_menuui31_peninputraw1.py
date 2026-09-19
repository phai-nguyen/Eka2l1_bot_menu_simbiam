#!/usr/bin/env python3
"""MENUUI31 PENINPUTRAW1: restore Nokia PenInputAnim raw-pointer consume semantics.

V30 proves the stock Nokia FEP/VKB now activates, but a key touch is delivered
twice by MENUUI28:
  1) mirrored to raweventbufqueue, and
  2) delivered again by normal WindowServer pointer hit-testing.
After the first such touch peninputserver stops re-arming EventReady and its
normal pointer FIFO grows.

Nokia's CPeninputAnim does not do that. While active it:
- tracks layout position/size;
- for pointer down/up/move inside the PenInput sprite (or while captured),
  queues the TRawEvent to peninputserver and returns ETrue to WSERV, consuming
  the normal pointer event;
- outside the PenInput area, down/up are still reported to the layout but are
  not consumed.

This patch implements the missing state opcodes used by RM-356 and makes the
MENUUI28 raw bridge return the real consume decision:
  506 SetLayoutPos
  507 LayoutSizeChangedWithSize
  509 CapturePointer
  516 EnableSprite (S60 5th / RD_TACTILE_FEEDBACK numbering)
No application UID or screen coordinate is hardcoded.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI31 PENINPUTRAW1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n=text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui31_peninputraw1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    anim_cpp=up/"src/emu/services/src/window/classes/plugins/animdll.cpp"
    win_h=up/"src/emu/services/include/services/window/window.h"
    win_cpp=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (anim_cpp,win_h,win_cpp,svc):
        if not p.is_file():
            fail(f"missing baseline file: {p}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:" not in anim_cpp.read_text(encoding="utf-8"):
        fail("MENUUI28 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI29 baseline missing")
    found30=False
    for p in (up/"src/emu/ios").rglob("*"):
        if p.is_file() and p.suffix.lower() in {".cpp",".cc",".mm",".m"}:
            try:
                if "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP:" in p.read_text(encoding="utf-8"):
                    found30=True
                    break
            except UnicodeDecodeError:
                pass
    if not found30:
        fail("MENUUI30 STOCKFEP1 baseline missing")

    ac=anim_cpp.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE:" in ac:
        print("MENUUI31 PENINPUTRAW1 already present")
        return

    old="""        constexpr std::int32_t PENINPUT_OP_FINISH_CONSTRUCTION = 501;
        constexpr std::int32_t PENINPUT_OP_ACTIVATE = 502;
        constexpr std::int32_t PENINPUT_OP_DEACTIVATE = 503;
"""
    new="""        constexpr std::int32_t PENINPUT_OP_FINISH_CONSTRUCTION = 501;
        constexpr std::int32_t PENINPUT_OP_ACTIVATE = 502;
        constexpr std::int32_t PENINPUT_OP_DEACTIVATE = 503;
        constexpr std::int32_t PENINPUT_OP_SET_LAYOUT_POS = 506;
        constexpr std::int32_t PENINPUT_OP_LAYOUT_SIZE_WITH_SIZE = 507;
        constexpr std::int32_t PENINPUT_OP_CAPTURE_POINTER = 509;
        // RM-356's PenInput build includes RD_TACTILE_FEEDBACK, making
        // EPeninputOpEnalbeSprite opcode 516.
        constexpr std::int32_t PENINPUT_OP_ENABLE_SPRITE = 516;
"""
    ac=replace_once(ac,old,new,"PenInput opcode constants")

    old="""                case PENINPUT_OP_DEACTIVATE:
                    active_ = false;
                    serv_->set_peninput_anim_active(false);
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=deactivate opcode={} active=0",
                        opcode);
                    break;

                default:
"""
    new="""                case PENINPUT_OP_DEACTIVATE:
                    active_ = false;
                    serv_->set_peninput_anim_active(false);
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=deactivate opcode={} active=0",
                        opcode);
                    break;

                case PENINPUT_OP_SET_LAYOUT_POS:
                    if (args) {
                        const std::int32_t *pt = reinterpret_cast<const std::int32_t *>(args);
                        serv_->set_peninput_anim_position(pt[0], pt[1]);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=position x={} y={}",
                            opcode, pt[0], pt[1]);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=position args=null",
                            opcode);
                    }
                    break;

                case PENINPUT_OP_LAYOUT_SIZE_WITH_SIZE:
                    if (args) {
                        const std::int32_t *sz = reinterpret_cast<const std::int32_t *>(args);
                        serv_->set_peninput_anim_size(sz[0], sz[1]);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=size width={} height={}",
                            opcode, sz[0], sz[1]);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=size args=null",
                            opcode);
                    }
                    break;

                case PENINPUT_OP_CAPTURE_POINTER:
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
                    if (args) {
                        const bool enabled = (*reinterpret_cast<const std::int32_t *>(args) != 0);
                        serv_->set_peninput_anim_sprite_enabled(enabled);
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=enable_sprite enabled={}",
                            opcode, enabled ? 1 : 0);
                    } else {
                        LOG_WARN(SERVICE_WINDOW,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE: opcode={} kind=enable_sprite args=null",
                            opcode);
                    }
                    break;

                default:
"""
    ac=replace_once(ac,old,new,"PenInput state opcode handlers")
    anim_cpp.write_text(ac,encoding="utf-8")

    wh=win_h.read_text(encoding="utf-8")
    old="""        std::atomic<bool> peninput_anim_present_{ false };
        std::atomic<bool> peninput_anim_active_{ false };

        chunk_ptr ws_global_mem_chunk;
"""
    new="""        std::atomic<bool> peninput_anim_present_{ false };
        std::atomic<bool> peninput_anim_active_{ false };
        std::atomic<std::int32_t> peninput_anim_pos_x_{ 0 };
        std::atomic<std::int32_t> peninput_anim_pos_y_{ 0 };
        std::atomic<std::int32_t> peninput_anim_width_{ 0 };
        std::atomic<std::int32_t> peninput_anim_height_{ 0 };
        std::atomic<bool> peninput_anim_pointer_captured_{ false };
        std::atomic<bool> peninput_anim_pen_down_{ false };
        std::atomic<bool> peninput_anim_sprite_enabled_{ true };

        chunk_ptr ws_global_mem_chunk;
"""
    wh=replace_once(wh,old,new,"PenInput geometry state")

    old="""        void set_peninput_anim_present(const bool present) {
            peninput_anim_present_.store(present, std::memory_order_release);
            if (!present) {
                peninput_anim_active_.store(false, std::memory_order_release);
            }
        }

        void set_peninput_anim_active(const bool active) {
            if (active) {
                peninput_anim_present_.store(true, std::memory_order_release);
            }
            peninput_anim_active_.store(active, std::memory_order_release);
        }

        bool mirror_peninput_raw_event(const epoc::event &evt);
"""
    new="""        void set_peninput_anim_present(const bool present) {
            peninput_anim_present_.store(present, std::memory_order_release);
            if (!present) {
                peninput_anim_active_.store(false, std::memory_order_release);
                peninput_anim_pointer_captured_.store(false, std::memory_order_release);
                peninput_anim_pen_down_.store(false, std::memory_order_release);
                peninput_anim_pos_x_.store(0, std::memory_order_release);
                peninput_anim_pos_y_.store(0, std::memory_order_release);
                peninput_anim_width_.store(0, std::memory_order_release);
                peninput_anim_height_.store(0, std::memory_order_release);
            }
        }

        void set_peninput_anim_active(const bool active) {
            if (active) {
                peninput_anim_present_.store(true, std::memory_order_release);
            } else {
                peninput_anim_pen_down_.store(false, std::memory_order_release);
            }
            peninput_anim_active_.store(active, std::memory_order_release);
        }

        void set_peninput_anim_position(const std::int32_t x, const std::int32_t y) {
            peninput_anim_pos_x_.store(x, std::memory_order_release);
            peninput_anim_pos_y_.store(y, std::memory_order_release);
        }

        void set_peninput_anim_size(const std::int32_t width, const std::int32_t height) {
            peninput_anim_width_.store(width, std::memory_order_release);
            peninput_anim_height_.store(height, std::memory_order_release);
        }

        void set_peninput_anim_pointer_capture(const bool captured) {
            peninput_anim_pointer_captured_.store(captured, std::memory_order_release);
        }

        void set_peninput_anim_sprite_enabled(const bool enabled) {
            peninput_anim_sprite_enabled_.store(enabled, std::memory_order_release);
        }

        // Returns true exactly when real CPeninputAnim would consume the
        // pointer event and prevent normal WindowServer hit-test delivery.
        bool mirror_peninput_raw_event(const epoc::event &evt);
"""
    wh=replace_once(wh,old,new,"PenInput state API")
    win_h.write_text(wh,encoding="utf-8")

    wc=win_cpp.read_text(encoding="utf-8")
    start=wc.index("    bool window_server::mirror_peninput_raw_event(const epoc::event &evt) {")
    end=wc.index("\n    void window_server::queue_input_from_driver",start)
    old=wc[start:end]
    new="""    bool window_server::mirror_peninput_raw_event(const epoc::event &evt) {
        if (!peninput_anim_present_.load(std::memory_order_acquire)
            || !peninput_anim_active_.load(std::memory_order_acquire)
            || evt.type != epoc::event_code::touch) {
            return false;
        }

        constexpr std::uint8_t RAW_POINTER_MOVE = 1;
        constexpr std::uint8_t RAW_BUTTON1_DOWN = 10;
        constexpr std::uint8_t RAW_BUTTON1_UP = 11;

        std::uint8_t raw_type = 0;
        switch (evt.adv_pointer_evt_.evtype) {
        case epoc::event_type::button1down:
            raw_type = RAW_BUTTON1_DOWN;
            break;
        case epoc::event_type::button1up:
            raw_type = RAW_BUTTON1_UP;
            break;
        case epoc::event_type::drag:
        case epoc::event_type::move:
            raw_type = RAW_POINTER_MOVE;
            break;
        default:
            return false;
        }

        const std::int32_t x = evt.adv_pointer_evt_.pos.x;
        const std::int32_t y = evt.adv_pointer_evt_.pos.y;
        const std::int32_t left = peninput_anim_pos_x_.load(std::memory_order_acquire);
        const std::int32_t top = peninput_anim_pos_y_.load(std::memory_order_acquire);
        const std::int32_t width = peninput_anim_width_.load(std::memory_order_acquire);
        const std::int32_t height = peninput_anim_height_.load(std::memory_order_acquire);
        const bool captured = peninput_anim_pointer_captured_.load(std::memory_order_acquire);
        const bool pen_down_before = peninput_anim_pen_down_.load(std::memory_order_acquire);
        const bool inside = width > 0 && height > 0
            && x >= left && y >= top && x < (left + width) && y < (top + height);

        bool should_mirror = false;
        bool consume = false;
        switch (raw_type) {
        case RAW_BUTTON1_DOWN:
            // CPeninputAnim::OnRawButton1Down always informs the layout.
            should_mirror = true;
            consume = inside || captured;
            if (inside) {
                peninput_anim_pen_down_.store(true, std::memory_order_release);
            }
            break;

        case RAW_BUTTON1_UP:
            // OnRawButton1Up also informs the layout even when outside.
            should_mirror = true;
            if (pen_down_before) {
                peninput_anim_pen_down_.store(false, std::memory_order_release);
                consume = inside;
            }
            if (captured) {
                consume = true;
            }
            break;

        case RAW_POINTER_MOVE:
            // Real PenInputAnim forwards move only during an active pen-down
            // sequence or explicit pointer capture.
            should_mirror = captured || pen_down_before;
            consume = should_mirror;
            break;

        default:
            break;
        }

        if (!should_mirror) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW: raw_type={} pos=({}, {}) rect=({}, {}, {}, {}) inside={} pen_down_before={} captured={} mirrored=0 consume=0",
                raw_type, x, y, left, top, width, height, inside ? 1 : 0,
                pen_down_before ? 1 : 0, captured ? 1 : 0);
            return false;
        }

        struct peninput_raw_event_buffer {
            std::int32_t count;
            epoc::raw_event events[6];
        };

        static_assert(sizeof(epoc::raw_event) == 32,
            "MENUUI31 expects the EKA2 raw-event ABI used by S60 5th Edition");
        static_assert(sizeof(peninput_raw_event_buffer) == 196,
            "MENUUI31 TRawEventBuffer ABI mismatch");

        peninput_raw_event_buffer buffer{};
        buffer.count = 1;
        epoc::raw_event &raw = buffer.events[0];
        raw.type_ = raw_type;
        raw.tip_ = 0;
        raw.pointer_num_ = evt.adv_pointer_evt_.ptr_num;
        raw.screen_num_ = 0;
        raw.time_in_ticks_ = 0;
        raw.data_.pos_.x_ = static_cast<std::uint32_t>(x);
        raw.data_.pos_.y_ = static_cast<std::uint32_t>(y);

        kernel_system *kern = get_kernel_system();
        bool queue_found = false;
        bool size_ok = false;
        bool sent = false;
        std::uint32_t queue_msg_size = 0;
        {
            kernel_lock guard(kern);
            kernel::msg_queue *queue =
                kern->get_by_name<kernel::msg_queue>("raweventbufqueue");
            if (queue) {
                queue_found = true;
                queue_msg_size = queue->max_message_length();
                size_ok = queue_msg_size == sizeof(peninput_raw_event_buffer);
                if (size_ok) {
                    sent = queue->send(&buffer, sizeof(buffer));
                }
            }
        }

        // Never swallow a pointer that failed to reach the raw-event queue.
        const bool consume_effective = consume && sent;
        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW: raw_type={} pointer={} pos=({}, {}) rect=({}, {}, {}, {}) inside={} pen_down_before={} captured={} sprite_enabled={} queue_found={} queue_msg_size={} size_ok={} mirrored={} consume={}",
            raw_type, raw.pointer_num_, x, y, left, top, width, height,
            inside ? 1 : 0, pen_down_before ? 1 : 0, captured ? 1 : 0,
            peninput_anim_sprite_enabled_.load(std::memory_order_acquire) ? 1 : 0,
            queue_found ? 1 : 0, queue_msg_size, size_ok ? 1 : 0,
            sent ? 1 : 0, consume_effective ? 1 : 0);

        return consume_effective;
    }
"""
    wc=wc[:start]+new+wc[end:]

    old="""                    // Real peninputanim.dll registers for WSERV raw events.
                    // Mirror before hit-testing so coordinates are still in
                    // guest screen space; normal delivery continues below.
                    mirror_peninput_raw_event(guest_event);

                    touch_shipper.add_new_event(guest_event);
                    root_current->walk_tree(&touch_shipper, epoc::window_tree_walk_style::bonjour_children_and_previous_siblings);
                    touch_shipper.clear();
"""
    new="""                    // MENUUI31: CPeninputAnim::OfferRawEvent returns ETrue for
                    // events inside the PenInput area (or while captured).
                    // WSERV must not deliver those a second time to the normal
                    // pointer-event FIFO.
                    const bool peninput_consumed = mirror_peninput_raw_event(guest_event);
                    if (!peninput_consumed) {
                        touch_shipper.add_new_event(guest_event);
                        root_current->walk_tree(&touch_shipper, epoc::window_tree_walk_style::bonjour_children_and_previous_siblings);
                        touch_shipper.clear();
                    }
"""
    wc=replace_once(wc,old,new,"consume raw PenInput touch before hit-test")
    win_cpp.write_text(wc,encoding="utf-8")

    final_ac=anim_cpp.read_text(encoding="utf-8")
    final_wh=win_h.read_text(encoding="utf-8")
    final_wc=win_cpp.read_text(encoding="utf-8")
    for gate in (
        "PENINPUT_OP_SET_LAYOUT_POS = 506",
        "PENINPUT_OP_LAYOUT_SIZE_WITH_SIZE = 507",
        "PENINPUT_OP_CAPTURE_POINTER = 509",
        "PENINPUT_OP_ENABLE_SPRITE = 516",
        "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_STATE:",
    ):
        if gate not in final_ac:
            fail(f"anim gate missing: {gate}")
    for gate in (
        "peninput_anim_width_",
        "peninput_anim_pen_down_",
        "set_peninput_anim_pointer_capture",
        "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW:",
        "const bool peninput_consumed = mirror_peninput_raw_event(guest_event);",
        "if (!peninput_consumed)",
    ):
        if gate not in final_wh+final_wc:
            fail(f"window gate missing: {gate}")

    print("MENUUI31 PENINPUTRAW1 applied")
    print("PenInput_506_position=IMPLEMENTED")
    print("PenInput_507_size=IMPLEMENTED")
    print("PenInput_509_capture=IMPLEMENTED")
    print("PenInput_516_enable_sprite=IMPLEMENTED")
    print("raw_pointer_inside_or_capture=NOKIA_CONSUME_SEMANTICS")
    print("raw_queue_failure=FALLBACK_TO_NORMAL_WS_DELIVERY")
    print("MENUUI30/MENUUI29/MENUUI28/prior=Preserved")

if __name__=="__main__":
    main()
