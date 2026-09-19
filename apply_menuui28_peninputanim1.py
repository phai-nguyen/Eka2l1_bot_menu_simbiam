#!/usr/bin/env python3
"""MENUUI28 PENINPUTANIM1: provide the S60 PenInput WindowServer animation bridge.

MENUUI27 real-device evidence:
- UniEditor opens and MENUUI27 handles SetTextCursorClipped/CancelTextCursor.
- Tapping the message body reaches Msg. editor, but no VKB appears.
- peninputserver starts, creates its raw-event queues, then RPeninputAnim is
  constructed on an RWsSprite.
- EKA2L1 logs both:
    Create ANIMDLL for peninputanim.dll, stubbed object
    Unimplemented AnimDll opcode: 0x5
- Symbian WSERV defines AnimDll opcode 0x5 as CreateInstanceSprite.
- RPeninputAnim uses CommandReply(501/502/503) for FinishConstruction,
  Activate and Deactivate. The real animation calls GetRawEvents(ETrue) while
  active and mirrors raw pointer events to the global "raweventbufqueue"
  consumed by peninputserver.

This patch adds a narrow native bridge for peninputanim.dll:
1. Create a real executor for CreateInstanceSprite (opcode 0x5).
2. Route AnimDll Command and CommandReply to that executor.
3. Track PenInput activation/deactivation.
4. While active, mirror touch raw events into raweventbufqueue while still
   delivering the original touch normally to the focused app/window.

It does NOT emulate T9/VKB layout code, CNTSRV, MsvServer, or scheduler logic.
Sprite drawing/member opcode 0x5 remains untouched in this patch; Nokia's
opaque PenInput layouts use their normal window control path, while the
animation bridge restores the missing raw-event channel.

Preserves MENUUI27 TEXTCURSOR1, MENUUI26 FSRESERVE1, MENUUI25 APPSERVICE1,
MENUUI24 AKN-ZORDER1, MENUUI23 APPTYPE1, MENUUI22 SCHEDRUN1, MANIC3, NOJAVA.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI28 PENINPUTANIM1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n = text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui28_peninputanim1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    anim_h = up / "src/emu/services/include/services/window/classes/plugins/animdll.h"
    anim_cpp = up / "src/emu/services/src/window/classes/plugins/animdll.cpp"
    window_h = up / "src/emu/services/include/services/window/window.h"
    window_cpp = up / "src/emu/services/src/window/window.cpp"
    wg_cpp = up / "src/emu/services/src/window/classes/wingroup.cpp"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    applist = up / "src/emu/services/src/applist/applist.cpp"
    oom = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (anim_h, anim_cpp, window_h, window_cpp, wg_cpp, fs_cpp, applist,
              oom, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    if "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:" in anim_cpp.read_text(encoding="utf-8"):
        print("MENUUI28 PENINPUTANIM1 already present")
        return

    # Proven lineage.
    if "SYMBIAN-SYSTEMAPPS1 MENUUI27 TEXT_CURSOR:" not in wg_cpp.read_text(encoding="utf-8"):
        fail("MENUUI27 TEXTCURSOR1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI26 FS_RESERVE:" not in fs_cpp.read_text(encoding="utf-8"):
        fail("MENUUI26 FSRESERVE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI25 APPSERVICE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER:" not in oom.read_text(encoding="utf-8"):
        fail("MENUUI24 AKN-ZORDER1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:" not in applist.read_text(encoding="utf-8"):
        fail("MENUUI23 APPTYPE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:" not in kernel.read_text(encoding="utf-8"):
        fail("MENUUI22 SCHEDRUN1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI22 sync diagnostics missing")
    if "MANIC_MODALFIX1" not in root.read_text(encoding="utf-8"):
        fail("MANIC3 baseline missing")

    # animdll.h: retain a discriminator for the guest PenInput animation DLL.
    h = anim_h.read_text(encoding="utf-8")
    old = """    struct anim_dll : public window_client_obj {
    protected:
        anim_executor_factory *factory_;
        common::identity_container<std::unique_ptr<anim_executor>> executors_;

    public:
        explicit anim_dll(window_server_client_ptr client, screen *scr, anim_executor_factory *factory);
        bool execute_command(service::ipc_context &context, ws_cmd &cmd) override;
    };
"""
    new = """    struct anim_dll : public window_client_obj {
    protected:
        anim_executor_factory *factory_;
        bool peninput_anim_;
        common::identity_container<std::unique_ptr<anim_executor>> executors_;

    public:
        explicit anim_dll(window_server_client_ptr client, screen *scr,
            anim_executor_factory *factory, bool peninput_anim = false);
        bool execute_command(service::ipc_context &context, ws_cmd &cmd) override;
    };
"""
    h = replace_once(h, old, new, "anim_dll discriminator")
    anim_h.write_text(h, encoding="utf-8")

    # window.h: WindowServer owns the bridge state so input-thread delivery
    # never points at an executor that may be concurrently destroyed.
    wh = window_h.read_text(encoding="utf-8")
    old = """        bool key_block_active{ true };

        chunk_ptr ws_global_mem_chunk;
"""
    new = """        bool key_block_active{ true };

        // MENUUI28: peninputanim.dll runs inside real WSERV on the phone.
        // EKA2L1 cannot execute guest WSERV animation DLLs, so keep the small
        // activation state in WindowServer and mirror raw touch to the queue
        // consumed by the real guest peninputserver.
        std::atomic<bool> peninput_anim_present_{ false };
        std::atomic<bool> peninput_anim_active_{ false };

        chunk_ptr ws_global_mem_chunk;
"""
    wh = replace_once(wh, old, new, "WindowServer PenInput state")

    old = """        void queue_input_from_driver(drivers::input_event &evt);
        void do_base_init();

        void send_event_to_window_group(epoc::window_group *group, const epoc::event &evt);
"""
    new = """        void queue_input_from_driver(drivers::input_event &evt);
        void do_base_init();

        void set_peninput_anim_present(const bool present) {
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

        void send_event_to_window_group(epoc::window_group *group, const epoc::event &evt);
"""
    wh = replace_once(wh, old, new, "WindowServer PenInput public bridge")
    window_h.write_text(wh, encoding="utf-8")

    # animdll.cpp: create/drive a native executor for the guest PenInput
    # animation. Existing clock animation factory behavior is preserved.
    ac = anim_cpp.read_text(encoding="utf-8")
    old = """#include <services/window/classes/plugins/animdll.h>
#include <services/window/classes/winuser.h>
#include <services/window/window.h>
"""
    new = """#include <services/window/classes/plugins/animdll.h>
#include <services/window/classes/plugins/sprite.h>
#include <services/window/classes/winuser.h>
#include <services/window/window.h>
"""
    ac = replace_once(ac, old, new, "animdll sprite include")

    old = """namespace eka2l1::epoc {
    anim_dll::anim_dll(window_server_client_ptr client, screen *scr, anim_executor_factory *factory)
        : window_client_obj(client, scr)
        , factory_(factory) {
    }
"""
    new = """namespace eka2l1::epoc {
    namespace {
        // From S60 PenInput's peninputcmd.h.
        constexpr std::int32_t PENINPUT_OP_FINISH_CONSTRUCTION = 501;
        constexpr std::int32_t PENINPUT_OP_ACTIVATE = 502;
        constexpr std::int32_t PENINPUT_OP_DEACTIVATE = 503;

        class peninput_anim_executor final : public anim_executor {
            eka2l1::window_server *serv_;
            sprite *sprite_;
            bool active_;

        public:
            peninput_anim_executor(eka2l1::window_server *serv, sprite *spr)
                : anim_executor(nullptr)
                , serv_(serv)
                , sprite_(spr)
                , active_(false) {
                serv_->set_peninput_anim_present(true);
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=executor_create sprite={} present=1",
                    reinterpret_cast<std::uintptr_t>(sprite_));
            }

            ~peninput_anim_executor() override {
                if (active_) {
                    serv_->set_peninput_anim_active(false);
                }
                serv_->set_peninput_anim_present(false);
                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=executor_destroy active_before={}",
                    active_ ? 1 : 0);
            }

            std::int32_t handle_request(const std::int32_t opcode, void *args) override {
                (void)args;

                switch (opcode) {
                case PENINPUT_OP_FINISH_CONSTRUCTION:
                    serv_->set_peninput_anim_present(true);
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=finish_construction opcode={} active={}",
                        opcode, active_ ? 1 : 0);
                    break;

                case PENINPUT_OP_ACTIVATE:
                    active_ = true;
                    serv_->set_peninput_anim_active(true);
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=activate opcode={} active=1",
                        opcode);
                    break;

                case PENINPUT_OP_DEACTIVATE:
                    active_ = false;
                    serv_->set_peninput_anim_active(false);
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=deactivate opcode={} active=0",
                        opcode);
                    break;

                default:
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=request opcode={} active={} passthrough=stub",
                        opcode, active_ ? 1 : 0);
                    break;
                }

                return epoc::error_none;
            }
        };
    }

    anim_dll::anim_dll(window_server_client_ptr client, screen *scr,
        anim_executor_factory *factory, bool peninput_anim)
        : window_client_obj(client, scr)
        , factory_(factory)
        , peninput_anim_(peninput_anim) {
    }
"""
    ac = replace_once(ac, old, new, "PenInput executor and anim_dll ctor")

    old = """        case ws_anim_dll_op_command_reply: {
            if (!factory_) {
                ctx.complete(epoc::error_none);
                break;
            }

            anim_request_info *req_info = reinterpret_cast<anim_request_info *>(cmd.data_ptr);
            std::unique_ptr<anim_executor> *executor = executors_.get(req_info->handle_);

            if (!executor) {
                ctx.complete(epoc::error_bad_handle);
                break;
            }

            void *data_ptr = ctx.get_descriptor_argument_ptr(1);
            ctx.complete((*executor)->handle_request(req_info->opcode_, data_ptr));

            break;
        }
"""
    new = """        case ws_anim_dll_op_command:
        case ws_anim_dll_op_command_reply: {
            anim_request_info *req_info = reinterpret_cast<anim_request_info *>(cmd.data_ptr);
            std::unique_ptr<anim_executor> *executor = executors_.get(req_info->handle_);

            if (!executor) {
                // Preserve the historical fake-success behavior for unrelated
                // guest animation DLLs that still have no native factory.
                if (!factory_ && !peninput_anim_) {
                    ctx.complete(epoc::error_none);
                } else {
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=request result=bad_handle ws_op={} handle={} opcode={}",
                        cmd.header.op, req_info->handle_, req_info->opcode_);
                    ctx.complete(epoc::error_bad_handle);
                }
                break;
            }

            void *data_ptr = nullptr;
            if (op == ws_anim_dll_op_command_reply) {
                data_ptr = ctx.get_descriptor_argument_ptr(1);
            } else if (cmd.header.cmd_len > sizeof(anim_request_info)) {
                data_ptr = reinterpret_cast<std::uint8_t *>(cmd.data_ptr) + sizeof(anim_request_info);
            }

            const std::int32_t result = (*executor)->handle_request(req_info->opcode_, data_ptr);
            ctx.complete(op == ws_anim_dll_op_command_reply ? result : epoc::error_none);
            break;
        }

        case ws_anim_dll_op_create_instance_sprite: {
            anim_create_instance_args *anim_args = reinterpret_cast<anim_create_instance_args *>(cmd.data_ptr);
            window_client_obj *obj = client->get_object(anim_args->win_handle_);

            if (!obj) {
                if (peninput_anim_) {
                    LOG_WARN(SERVICE_WINDOW,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=create_instance_sprite result=bad_handle win={} anim_type={}",
                        anim_args->win_handle_, anim_args->anim_type_);
                }
                ctx.complete(epoc::error_bad_handle);
                break;
            }

            if (peninput_anim_) {
                // RAnim::Construct(const RWsSprite&) guarantees that this is
                // an RWsSprite handle. The PenInput bridge does not dereference
                // sprite drawing members; it only needs the WSERV instance.
                sprite *spr = reinterpret_cast<sprite *>(obj);
                std::unique_ptr<anim_executor> executor =
                    std::make_unique<peninput_anim_executor>(&client->get_ws(), spr);
                const std::uint32_t handle = executors_.add(executor);

                LOG_WARN(SERVICE_WINDOW,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=create_instance_sprite result=ok win={} anim_type={} executor_handle={}",
                    anim_args->win_handle_, anim_args->anim_type_, handle);
                ctx.complete(static_cast<std::int32_t>(handle));
                break;
            }

            // No other sprite-backed animation has a native executor yet.
            LOG_TRACE(SERVICE_WINDOW,
                "CreateInstanceSprite for non-PenInput animation remains stubbed");
            ctx.complete(epoc::error_none);
            break;
        }
"""
    ac = replace_once(ac, old, new, "AnimDll command/CreateInstanceSprite routing")

    old = """        case ws_anim_dll_op_destroy_instance: {
            if (!factory_) {
                ctx.complete(epoc::error_none);
                break;
            }
            executors_.remove(*reinterpret_cast<std::uint32_t *>(cmd.data_ptr));
            ctx.complete(epoc::error_none);
            break;
        }
"""
    new = """        case ws_anim_dll_op_destroy_instance: {
            if (!factory_ && !peninput_anim_) {
                ctx.complete(epoc::error_none);
                break;
            }
            executors_.remove(*reinterpret_cast<std::uint32_t *>(cmd.data_ptr));
            ctx.complete(epoc::error_none);
            break;
        }
"""
    ac = replace_once(ac, old, new, "AnimDll destroy PenInput executor")
    anim_cpp.write_text(ac, encoding="utf-8")

    # window.cpp: recognize the guest DLL by basename, then mirror active raw
    # touch events into the real PenInputServer RMsgQueue.
    wc = window_cpp.read_text(encoding="utf-8")
    old = """        if (!factory_to_pass) {
            LOG_TRACE(SERVICE_WINDOW, "Create ANIMDLL for {}, stubbed object", common::ucs2_to_utf8(dll_name));
        }

        window_client_obj_ptr animdll = std::make_unique<epoc::anim_dll>(this, nullptr, factory_to_pass);
        ctx.complete(add_object(animdll));
"""
    new = """        std::u16string dll_basename = dll_name;
        const std::u16string::size_type sep = dll_basename.find_last_of(u"\\\\/");
        if (sep != std::u16string::npos) {
            dll_basename = dll_basename.substr(sep + 1);
        }
        const bool peninput_anim =
            common::compare_ignore_case(dll_basename, u"peninputanim.dll") == 0;

        if (!factory_to_pass && !peninput_anim) {
            LOG_TRACE(SERVICE_WINDOW, "Create ANIMDLL for {}, stubbed object", common::ucs2_to_utf8(dll_name));
        }

        if (peninput_anim) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=load dll={} native_bridge=1",
                common::ucs2_to_utf8(dll_name));
        }

        window_client_obj_ptr animdll =
            std::make_unique<epoc::anim_dll>(this, nullptr, factory_to_pass, peninput_anim);
        ctx.complete(add_object(animdll));
"""
    wc = replace_once(wc, old, new, "PenInput DLL recognition")

    old = """    void window_server::queue_input_from_driver(drivers::input_event &evt) {
        if (!loaded) {
            return;
        }
"""
    new = """    bool window_server::mirror_peninput_raw_event(const epoc::event &evt) {
        if (!peninput_anim_present_.load(std::memory_order_acquire)
            || !peninput_anim_active_.load(std::memory_order_acquire)
            || evt.type != epoc::event_code::touch) {
            return false;
        }

        // Symbian TRawEvent::TType values from e32event.h.
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

        // peninputmsgqueue.h:
        //   KMaxEvent = 5;
        //   class TRawEventBuffer { TInt iNum; TRawEvent iEvent[KMaxEvent+1]; };
        struct peninput_raw_event_buffer {
            std::int32_t count;
            epoc::raw_event events[6];
        };

        static_assert(sizeof(epoc::raw_event) == 32,
            "MENUUI28 expects the EKA2 raw-event ABI used by S60 5th Edition");
        static_assert(sizeof(peninput_raw_event_buffer) == 196,
            "MENUUI28 TRawEventBuffer ABI mismatch");

        peninput_raw_event_buffer buffer{};
        buffer.count = 1;

        epoc::raw_event &raw = buffer.events[0];
        raw.type_ = raw_type;
        raw.tip_ = 0;
        raw.pointer_num_ = evt.adv_pointer_evt_.ptr_num;
        raw.screen_num_ = 0; // Default TRawEvent device number is unset.
        raw.time_in_ticks_ = 0;
        raw.data_.pos_.x_ = static_cast<std::uint32_t>(evt.adv_pointer_evt_.pos.x);
        raw.data_.pos_.y_ = static_cast<std::uint32_t>(evt.adv_pointer_evt_.pos.y);

        kernel_system *kern = get_kernel_system();
        bool queue_found = false;
        bool size_ok = false;
        bool sent = false;
        std::uint32_t queue_msg_size = 0;

        {
            // Host input arrives outside the emulated kernel lock. Sending to
            // RMsgQueue may complete PenInputServer's NotifyDataAvailable, so
            // perform lookup + send under the normal kernel lock.
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

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM: phase=raw_mirror raw_type={} pointer={} pos=({}, {}) queue_found={} queue_msg_size={} bridge_msg_size={} size_ok={} sent={}",
            raw_type, raw.pointer_num_,
            evt.adv_pointer_evt_.pos.x, evt.adv_pointer_evt_.pos.y,
            queue_found ? 1 : 0, queue_msg_size,
            static_cast<std::uint32_t>(sizeof(peninput_raw_event_buffer)),
            size_ok ? 1 : 0, sent ? 1 : 0);

        // Mirroring is observational/compatibility delivery only. The same
        // touch still goes through normal WindowServer hit-testing, matching
        // real PenInputAnim behavior for events outside the pen UI.
        return sent;
    }

    void window_server::queue_input_from_driver(drivers::input_event &evt) {
        if (!loaded) {
            return;
        }
"""
    wc = replace_once(wc, old, new, "PenInput raw-event mirror")

    old = """                    make_mouse_event(original_input_evt, guest_event, get_current_focus_screen());

                    touch_shipper.add_new_event(guest_event);
"""
    new = """                    make_mouse_event(original_input_evt, guest_event, get_current_focus_screen());

                    // Real peninputanim.dll registers for WSERV raw events.
                    // Mirror before hit-testing so coordinates are still in
                    // guest screen space; normal delivery continues below.
                    mirror_peninput_raw_event(guest_event);

                    touch_shipper.add_new_event(guest_event);
"""
    wc = replace_once(wc, old, new, "PenInput mirror hook")
    window_cpp.write_text(wc, encoding="utf-8")

    # Final safety gates.
    final_anim = anim_cpp.read_text(encoding="utf-8")
    final_win = window_cpp.read_text(encoding="utf-8")
    final_wh = window_h.read_text(encoding="utf-8")
    for gate in (
        "case ws_anim_dll_op_create_instance_sprite:",
        "case ws_anim_dll_op_command:",
        "PENINPUT_OP_FINISH_CONSTRUCTION = 501",
        "PENINPUT_OP_ACTIVATE = 502",
        "PENINPUT_OP_DEACTIVATE = 503",
        "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:",
    ):
        if gate not in final_anim:
            fail(f"anim implementation gate missing: {gate}")

    for gate in (
        "peninput_anim_present_",
        "peninput_anim_active_",
        "mirror_peninput_raw_event",
        '"raweventbufqueue"',
        "TRawEventBuffer ABI mismatch",
        "mirror_peninput_raw_event(guest_event);",
        "native_bridge=1",
    ):
        if gate not in final_wh + final_win:
            fail(f"WindowServer bridge gate missing: {gate}")

    print("MENUUI28 PENINPUTANIM1 applied")
    print("AnimDll_0x5_CreateInstanceSprite=IMPLEMENTED_FOR_PENINPUT")
    print("PenInput_501_FinishConstruction=ROUTED")
    print("PenInput_502_Activate=ROUTED")
    print("PenInput_503_Deactivate=ROUTED")
    print("PenInput_raw_touch_to_raweventbufqueue=IMPLEMENTED_NON_SWALLOWING")
    print("Sprite_append_member=UNCHANGED CNTSRV=UNCHANGED MsvServer=UNCHANGED scheduler=UNCHANGED")
    print("MENUUI27/MENUUI26/MENUUI25/MENUUI24/MENUUI23/SCHEDRUN1/MANIC3/NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
