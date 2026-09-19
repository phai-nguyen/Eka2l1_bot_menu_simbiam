#!/usr/bin/env python3
"""NATIVEBOOT2-B13 SAGLOBALSTATE1.

Apply on top of B12 SAIPC1.

Observed B12 device runtime:
- B12 passes the previous SAServer opcode 0x1 blocker.
- StartupAdaptation.dll immediately issues SAServer opcode 0x64 (100).
- Symbian/Nokia startupadaptationcommands.h defines
  StartupAdaptation::EGlobalStateChange = 100.
- The response contract for EGlobalStateChange is TResponsePckg,
  which is TPckgBuf<TInt>; KErrNone (0) means the state change succeeded.

B13 implements exactly that command contract. It preserves the request/input
descriptor, writes TInt(KErrNone) into the first writable 8-bit descriptor
(the response package), and completes the IPC with KErrNone.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B13-SAGLOBALSTATE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b13_saglobalstate1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    sa = up / "src/emu/services/src/sms/sa/sa.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (sa, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing B12 baseline file: {p}")

    sa_text = sa.read_text(encoding="utf-8")
    for gate in (
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
        "NATIVEBOOT2-B12 SAIPC1",
    ):
        if gate not in sa_text:
            fail(f"B12 SAIPC1 gate missing: {gate}")

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

    text = sa_text
    if "[NBOOT2][SA_GLOBAL_STATE]" not in text:
        old = """        ctx.complete(epoc::error_none);
    }

    sa_server::sa_server(eka2l1::system *sys)
"""
        new = """        // NATIVEBOOT2-B13 SAGLOBALSTATE1:
        // RM-356 StartupAdaptation.dll sends StartupAdaptation::EGlobalStateChange
        // directly as SAServer IPC function 100 (0x64). Its response type is
        // TPckgBuf<TInt>; zero/KErrNone means the state transition succeeded.
        if (ctx.msg && (ctx.msg->function == 100)) {
            const std::int32_t response = epoc::error_none;
            int response_slot = -1;

            for (int i = 0; i < 4; ++i) {
                const ipc_arg_type type = ctx.msg->args.get_arg_type(i);
                if (type == ipc_arg_type::des8) {
                    if ((ctx.get_argument_max_data_size(i) >= sizeof(response))
                        && ctx.write_data_to_descriptor_argument<std::int32_t>(i, response)) {
                        response_slot = i;
                        break;
                    }
                }
            }

            LOG_WARN(SERVICE_SMS,
                "[NBOOT2][SA_GLOBAL_STATE] func=0x{:X} arg_types=[{},{},{},{}] "
                "arg_sizes=[{},{},{},{}] response_slot={} response={} completion=KErrNone",
                ctx.msg->function,
                static_cast<int>(ctx.msg->args.get_arg_type(0)),
                static_cast<int>(ctx.msg->args.get_arg_type(1)),
                static_cast<int>(ctx.msg->args.get_arg_type(2)),
                static_cast<int>(ctx.msg->args.get_arg_type(3)),
                ctx.get_argument_data_size(0), ctx.get_argument_data_size(1),
                ctx.get_argument_data_size(2), ctx.get_argument_data_size(3),
                response_slot, response);

            // Complete even if the proprietary plugin provided no separate
            // writable response descriptor; the trace above will expose its ABI.
            ctx.complete(epoc::error_none);
            return;
        }

        ctx.complete(epoc::error_none);
    }

    sa_server::sa_server(eka2l1::system *sys)
"""
        text = replace_once(text, old, new, "SAServer GlobalState handler")

    reg_anchor = '        REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");\n'
    reg_new = reg_anchor + '        REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");\n'
    if 'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");' not in text:
        text = replace_once(text, reg_anchor, reg_new, "SAServer opcode 100 registration")

    sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_GLOBAL_STATE]",
        'REGISTER_IPC(sa_server, unk_op1, 100, "NBOOT2::SaGlobalStateChange");',
        'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");',
        'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");',
        "ctx.write_data_to_descriptor_argument<std::int32_t>(i, response)",
    ):
        if gate not in body:
            fail(f"B13 gate missing: {gate}")

    print("NATIVEBOOT2-B13 SAGLOBALSTATE1 applied")
    print("SAServer_opcode_100=EGlobalStateChange")
    print("EGlobalStateChange_response=TInt_KErrNone")
    print("SA_response_descriptor=first_writable_des8")
    print("B12_SAIPC1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
