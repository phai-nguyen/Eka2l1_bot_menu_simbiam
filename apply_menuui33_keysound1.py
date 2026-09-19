#!/usr/bin/env python3
"""MENUUI33 KEYSOUND1: implement S60 KeySound opcode 13.

V32 device evidence:
- PenInput raw down is sent to raweventbufqueue and immediately received.
- Immediately after that peninputserver issues KeySoundServer opcode 13.
- EKA2L1 logs "Unimplemented keysound server opcode: 13" and does not
  complete the IPC.
- CEventQueue::RunL therefore never reaches GetEvent(); the subsequent raw
  button-up remains queued with avail_waiters=0.

Symbian TKeySoundServerCommands maps:
  13 = EKeySoundServerDisableNextKeySound
and stock ServiceL stores aMessage.Int0() as the disabled scan code and then
completes the message.

This patch implements only that missing semantic and keeps all MENUUI32/31
PenInput diagnostics and prior fixes intact.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI33 KEYSOUND1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text, old, new, name):
    n=text.count(old)
    if n!=1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_menuui33_keysound1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    ops=up/"src/emu/services/include/services/audio/keysound/ops.h"
    hdr=up/"src/emu/services/include/services/audio/keysound/keysound.h"
    cpp=up/"src/emu/services/src/audio/keysound/keysound.cpp"
    mq=up/"src/emu/kernel/src/msgqueue.cpp"
    win=up/"src/emu/services/src/window/window.cpp"
    for p in (ops,hdr,cpp,mq,win):
        if not p.is_file():
            fail(f"missing baseline file {p}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE:" not in mq.read_text(encoding="utf-8"):
        fail("MENUUI32 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW:" not in win.read_text(encoding="utf-8"):
        fail("MENUUI31 baseline missing")

    c=cpp.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13:" in c:
        print("MENUUI33 already present")
        return

    o=ops.read_text(encoding="utf-8")
    o=replace_once(o,
"""        opcode_bring_to_foreground = 7,
        opcode_lock_context = 9
""",
"""        opcode_bring_to_foreground = 7,
        opcode_lock_context = 9,
        opcode_disable_next_key_sound = 13
""","keysound opcode 13 enum")
    ops.write_text(o,encoding="utf-8")

    h=hdr.read_text(encoding="utf-8")
    h=replace_once(h,
"""        void bring_to_foreground(service::ipc_context *ctx);
        void lock_context(service::ipc_context *ctx);
    };

    class keysound_server : public service::typical_server {
        bool inited_;
        std::vector<epoc::keysound::sound_info> sounds_;
""",
"""        void bring_to_foreground(service::ipc_context *ctx);
        void lock_context(service::ipc_context *ctx);
        void disable_next_key_sound(service::ipc_context *ctx);
    };

    class keysound_server : public service::typical_server {
        bool inited_;
        std::int32_t disabled_scan_code_;
        std::vector<epoc::keysound::sound_info> sounds_;
""","keysound declarations")

    h=replace_once(h,
"""        void initialized(const bool is_it) {
            inited_ = is_it;
        }
""",
"""        void initialized(const bool is_it) {
            inited_ = is_it;
        }

        void disabled_scan_code(const std::int32_t scancode) {
            disabled_scan_code_ = scancode;
        }

        std::int32_t disabled_scan_code() const {
            return disabled_scan_code_;
        }
""","keysound disabled scan code accessors")
    hdr.write_text(h,encoding="utf-8")

    c=cpp.read_text(encoding="utf-8")
    anchor="""    void keysound_session::lock_context(eka2l1::service::ipc_context *ctx) {
        ctx->complete(epoc::error_none);
    }

"""
    insert="""    void keysound_session::lock_context(eka2l1::service::ipc_context *ctx) {
        ctx->complete(epoc::error_none);
    }

    void keysound_session::disable_next_key_sound(service::ipc_context *ctx) {
        const auto scan_code = ctx->get_argument_value<std::int32_t>(0);
        if (!scan_code.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }

        server<keysound_server>()->disabled_scan_code(scan_code.value());
        LOG_WARN(SERVICE_KEYSOUND,
            "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13: result=complete opcode=13 scan_code={}",
            scan_code.value());
        ctx->complete(epoc::error_none);
    }

"""
    c=replace_once(c,anchor,insert,"disable next key sound handler")

    c=replace_once(c,
"""        case epoc::keysound::opcode_lock_context: {
            lock_context(ctx);
            break;
        }

        default:
""",
"""        case epoc::keysound::opcode_lock_context: {
            lock_context(ctx);
            break;
        }

        case epoc::keysound::opcode_disable_next_key_sound: {
            disable_next_key_sound(ctx);
            break;
        }

        default:
""","keysound fetch dispatch")

    c=replace_once(c,
"""    keysound_server::keysound_server(system *sys)
        : service::typical_server(sys, SERVICE_KEYSOUND_SERVER_NAME)
        , inited_(false) {
    }
""",
"""    keysound_server::keysound_server(system *sys)
        : service::typical_server(sys, SERVICE_KEYSOUND_SERVER_NAME)
        , inited_(false)
        , disabled_scan_code_(-1) {
    }
""","keysound server init")
    cpp.write_text(c,encoding="utf-8")

    final=cpp.read_text(encoding="utf-8")
    for gate in (
        "opcode_disable_next_key_sound",
        "disable_next_key_sound(service::ipc_context *ctx)",
        "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13:",
        "disabled_scan_code_( -1"  # handled below with flexible check
    ):
        if gate.startswith("disabled_scan_code_"):
            continue
        if gate not in final and gate not in hdr.read_text(encoding="utf-8") and gate not in ops.read_text(encoding="utf-8"):
            fail(f"gate missing: {gate}")
    if ", disabled_scan_code_(-1)" not in final:
        fail("disabled scan code init missing")

    print("MENUUI33 KEYSOUND1 applied")
    print("opcode13=EKeySoundServerDisableNextKeySound_IMPLEMENTED")
    print("sync_ipc_completion=IMPLEMENTED")
    print("MENUUI32/MENUUI31/MENUUI30/prior=PRESERVED")

if __name__=="__main__":
    main()
