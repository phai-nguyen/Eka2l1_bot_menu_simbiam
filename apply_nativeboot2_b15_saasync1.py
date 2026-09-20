#!/usr/bin/env python3
"""NATIVEBOOT2-B15 SAASYNC1.

Apply on top of B14 SARESPONSE1.

B14 device evidence:
- EGlobalStateChange/0x64 response ABI now completes with header_ok=true,
  payload_ok=true and KErrNone.
- B14 then emits ~417k SAServer opcode-1 completions and never advances to
  EWSRV/Window Server.
- Opcode-1 descriptor layouts distinguish a short control path from the
  long-lived event path: the event-shaped request has writable des8 slots
  2 and 3.

B15 keeps the control-form opcode 1 synchronous, but retains the event-form
request as a real asynchronous notification instead of completing KErrNone
immediately. No synthetic event is injected in this diagnostic build.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B15-SAASYNC1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b15_saasync1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    sa = up / "src/emu/services/src/sms/sa/sa.cpp"
    sah = up / "src/emu/services/include/services/sms/sa/sa.h"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (sa, sah, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing B14 baseline file: {p}")

    text = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_RESPONSE_FAIL]",
        "[NBOOT2][SA_OP1]",
        "NATIVEBOOT2-B14 SARESPONSE1",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in text:
            fail(f"B14 gate missing: {gate}")

    svc_text = svc.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][DM_INIT_SET_INT]",
        "[NBOOT2][DM_INIT_SUBSCRIBE]",
        "[NBOOT2][DM_INIT_GET_INT]",
        "[NBOOT2][RM356_CREATOR_SECURITY]",
        "BRIDGE_REGISTER(0xB1, creator_security_info)",
        "const bool res = prop->set_int(value);",
    ):
        if gate not in svc_text:
            fail(f"B11 gate missing: {gate}")
    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" not in fs.read_text(encoding="utf-8"):
        fail("B10 FSFORMAT1 marker missing")
    if "[NBOOT2][RM356_LOADER_FSY]" not in loader.read_text(encoding="utf-8"):
        fail("B8 LOADERFSY1 marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 BSP marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    htext = sah.read_text(encoding="utf-8")
    old_h = """    class sa_server : public service::server {
    private:
        void unk_op1(service::ipc_context &context);

    public:
        explicit sa_server(eka2l1::system *sys);
    };
"""
    new_h = """    class sa_server : public service::server {
    private:
        // NATIVEBOOT2-B15 SAASYNC1: RM-356 keeps one long-lived opcode-1
        // notification outstanding. Store only the request status/thread;
        // descriptor marshalling will be added once a real event producer is
        // observed. The session pointer is used solely for disconnect cleanup.
        epoc::notify_info pending_sa_event_;
        service::session *pending_sa_event_session_ = nullptr;
        std::uint64_t sa_op1_control_count_ = 0;
        std::uint64_t sa_op1_pending_count_ = 0;

        void unk_op1(service::ipc_context &context);
        void disconnect(service::ipc_context &context) override;

    public:
        explicit sa_server(eka2l1::system *sys);
    };
"""
    htext = replace_once(htext, old_h, new_h, "sa_server header")
    sah.write_text(htext, encoding="utf-8")

    old_cpp = """        // Opcode 1 is used by the RM-356 SAClient control/event path.  B14
        // intentionally preserves B12's completion behaviour, but records its
        // real ABI so the long-lived notification request can be separated from
        // the synchronous registration call in the next iteration if needed.
        if (ctx.msg && (ctx.msg->function == 1)) {
            std::uint32_t words[4] = {};
            for (int i = 0; i < 4; ++i) {
                const std::uint8_t *ptr = ctx.get_descriptor_argument_ptr(i);
                if (ptr && (ctx.get_argument_data_size(i) >= sizeof(std::uint32_t))) {
                    std::memcpy(&words[i], ptr, sizeof(std::uint32_t));
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_OP1] types=[{},{},{},{}] sizes=[{},{},{},{}] "
                "max=[{},{},{},{}] words=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] completion=KErrNone",
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                ctx.get_argument_max_data_size(2), ctx.get_argument_max_data_size(3),
                words[0], words[1], words[2], words[3]);
        }

        ctx.complete(epoc::error_none);
    }

    sa_server::sa_server(eka2l1::system *sys)
"""
    new_cpp = """        // NATIVEBOOT2-B15 SAASYNC1:
        // B14 proved that treating every opcode-1 call as immediate success
        // creates a ~417k-call busy loop. RM-356 also showed two opcode-1 ABI
        // shapes. Preserve immediate success for the short control form, but
        // retain the event form (writable slots 2+3) as a real async request.
        if (ctx.msg && (ctx.msg->function == 1)) {
            std::uint32_t words[4] = {};
            for (int i = 0; i < 4; ++i) {
                const std::uint8_t *ptr = ctx.get_descriptor_argument_ptr(i);
                if (ptr && (ctx.get_argument_data_size(i) >= sizeof(std::uint32_t))) {
                    std::memcpy(&words[i], ptr, sizeof(std::uint32_t));
                }
            }

            const bool event_shape =
                (ctx.msg->args.get_arg_type(2) == ipc_arg_type::des8)
                && (ctx.msg->args.get_arg_type(3) == ipc_arg_type::des8);

            if (!event_shape) {
                ++sa_op1_control_count_;
                LOG_WARN(SERVICE_SMS,
                    "[NBOOT2][SA_OP1_CONTROL] count={} types=[{},{},{},{}] sizes=[{},{},{},{}] "
                    "max=[{},{},{},{}] words=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] completion=KErrNone",
                    sa_op1_control_count_,
                    static_cast<int>(ctx.msg->args.get_arg_type(0)),
                    static_cast<int>(ctx.msg->args.get_arg_type(1)),
                    static_cast<int>(ctx.msg->args.get_arg_type(2)),
                    static_cast<int>(ctx.msg->args.get_arg_type(3)),
                    ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                    ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                    ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                    ctx.get_argument_max_data_size(2), ctx.get_argument_max_data_size(3),
                    words[0], words[1], words[2], words[3]);
                ctx.complete(epoc::error_none);
                return;
            }

            if (!pending_sa_event_.empty()) {
                LOG_ERROR(SERVICE_SMS,
                    "[NBOOT2][SA_OP1_DUP] types=[{},{},{},{}] pending_count={} completion=KErrInUse",
                    static_cast<int>(ctx.msg->args.get_arg_type(0)),
                    static_cast<int>(ctx.msg->args.get_arg_type(1)),
                    static_cast<int>(ctx.msg->args.get_arg_type(2)),
                    static_cast<int>(ctx.msg->args.get_arg_type(3)),
                    sa_op1_pending_count_);
                ctx.complete(epoc::error_in_use);
                return;
            }

            pending_sa_event_.requester = ctx.msg->own_thr;
            pending_sa_event_.sts = ctx.msg->request_sts;
            pending_sa_event_.pending();
            pending_sa_event_session_ = ctx.msg->msg_session;
            ++sa_op1_pending_count_;

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_OP1_PENDING] count={} session={} types=[{},{},{},{}] "
                "sizes=[{},{},{},{}] max=[{},{},{},{}] "
                "words=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] completion=PENDING",
                sa_op1_pending_count_,
                pending_sa_event_session_ ? pending_sa_event_session_->unique_id() : 0,
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                ctx.get_argument_max_data_size(0), ctx.get_argument_max_data_size(1),
                ctx.get_argument_max_data_size(2), ctx.get_argument_max_data_size(3),
                words[0], words[1], words[2], words[3]);

            // Deliberately do not call ctx.complete(). The guest TRequestStatus
            // stays pending until a real adaptation event source is implemented
            // or the owning session disconnects.
            return;
        }

        ctx.complete(epoc::error_none);
    }

    void sa_server::disconnect(service::ipc_context &ctx) {
        if (ctx.msg && (pending_sa_event_session_ == ctx.msg->msg_session)
            && !pending_sa_event_.empty()) {
            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_OP1_CANCEL] session={} completion=KErrCancel",
                pending_sa_event_session_->unique_id());
            pending_sa_event_.complete(epoc::error_cancel);
            pending_sa_event_session_ = nullptr;
        }

        service::server::disconnect(ctx);
    }

    sa_server::sa_server(eka2l1::system *sys)
"""
    text = replace_once(text, old_cpp, new_cpp, "B14 opcode1 block")
    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    hbody = sah.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_RESPONSE]",
        "[NBOOT2][SA_RESPONSE_FAIL]",
        "[NBOOT2][SA_OP1_CONTROL]",
        "[NBOOT2][SA_OP1_PENDING]",
        "[NBOOT2][SA_OP1_DUP]",
        "[NBOOT2][SA_OP1_CANCEL]",
        "pending_sa_event_.pending();",
        "service::server::disconnect(ctx);",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
    ):
        if gate not in body:
            fail(f"B15 cpp gate missing: {gate}")
    for gate in ("pending_sa_event_", "pending_sa_event_session_", "void disconnect(service::ipc_context &context) override;"):
        if gate not in hbody:
            fail(f"B15 header gate missing: {gate}")

    print("NATIVEBOOT2-B15 SAASYNC1 applied")
    print("SA_opcode1_control=immediate_KErrNone")
    print("SA_opcode1_event=one_pending_request_per_server_session")
    print("SA_event_injection=DISABLED_DIAGNOSTIC")
    print("SA_disconnect_cleanup=KErrCancel")
    print("B14_SARESPONSE1=PRESERVED")
    print("B13_SAGLOBALSTATE1=PRESERVED")
    print("B12_SAIPC1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
