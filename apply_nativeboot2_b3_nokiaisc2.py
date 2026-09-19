#!/usr/bin/env python3
"""NATIVEBOOT2-B3 NOKIAISC2.

Apply on top of B2 NOKIAISC1.

Observed B2 runtime:
  NokiaISC loaded
  [NBOOT2][NOKIAISC_CONTROL] opcode=0
  ... no further guest activity ...

Nokia/Symbian ISC reference source defines opcode 0 as
EIscAsyncInitializeModemInterface. RIscApi::InitializeModemInterface sets a
TRequestStatus pending, puts its address in params[0], and calls DoSvControl(0,
params). The real LDD completes that status asynchronously. B2 returned KErrNone
without completing the status, so EStart waited forever.

This patch emulates the minimum startup semantics:
- opcode 0 (InitializeModemInterface): complete params[0] with KErrNone,
- opcode 1 (AsyncOpen): complete params[0] with KErrNone,
- leave existing synchronous status queries returning zero (connected / no flow
  control), which is appropriate for the inert offline adapter.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B3-NOKIAISC2"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b3_nokiaisc2.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    src = up / "src/emu/ldd/src/nokiaisc/nokiaisc.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (src, svc, state, root):
        if not p.is_file():
            fail(f"missing B2 baseline file: {p}")

    if "[NBOOT2][NOKIAISC_CONTROL]" not in src.read_text(encoding="utf-8"):
        fail("B2 NokiaISC baseline marker missing")
    if "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI" not in svc.read_text(encoding="utf-8"):
        fail("B2 EPOC94 channel ABI marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 baseline marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub UI marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    text = src.read_text(encoding="utf-8")
    if "[NBOOT2][NOKIAISC_INIT_COMPLETE]" not in text:
        old = """    std::int32_t nokiaisc_channel::do_control(kernel::thread *, const std::uint32_t opcode,
        const eka2l1::ptr<void>, const eka2l1::ptr<void>) {
        // The iPhone host has no Nokia baseband/secure-element transport.
        // EStart only needs the ISC channel to initialise far enough to hand
        // startup to domainSrv/SysStart, so expose a present inert device.
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_CONTROL] opcode={}", opcode);
        return epoc::error_none;
    }
"""
        new = """    std::int32_t nokiaisc_channel::do_control(kernel::thread *thread, const std::uint32_t opcode,
        const eka2l1::ptr<void> arg1, const eka2l1::ptr<void>) {
        // Nokia ISC API uses DoSvControl for its first asynchronous operations.
        // arg1 points to a guest array of three TAny* values; params[0] is the
        // TRequestStatus that the real LDD completes when initialization/open
        // finishes.
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_CONTROL] opcode={} arg1=0x{:08X}",
            opcode, arg1.ptr_address());

        if ((opcode == 0) || (opcode == 1)) {
            kernel::process *process = thread ? thread->owning_process() : nullptr;
            if (!process || !arg1) {
                LOG_ERROR(LDD_MMCIF,
                    "[NBOOT2][NOKIAISC_ASYNC_BADARGS] opcode={} process={} arg1=0x{:08X}",
                    opcode, process ? 1 : 0, arg1.ptr_address());
                return epoc::error_argument;
            }

            eka2l1::ptr<std::uint32_t> params_ptr(arg1.ptr_address());
            std::uint32_t *params = params_ptr.get(process);
            if (!params || params[0] == 0) {
                LOG_ERROR(LDD_MMCIF,
                    "[NBOOT2][NOKIAISC_ASYNC_BADARGS] opcode={} params={} status=0x{:08X}",
                    opcode, params ? 1 : 0, params ? params[0] : 0);
                return epoc::error_argument;
            }

            eka2l1::ptr<epoc::request_status> status_ptr(params[0]);
            epoc::request_status *status = status_ptr.get(process);
            if (!status) {
                LOG_ERROR(LDD_MMCIF,
                    "[NBOOT2][NOKIAISC_ASYNC_BADSTATUS] opcode={} status=0x{:08X}",
                    opcode, params[0]);
                return epoc::error_bad_descriptor;
            }

            LOG_WARN(LDD_MMCIF,
                "[NBOOT2][NOKIAISC_ASYNC] opcode={} status=0x{:08X} before={} p1=0x{:08X} p2=0x{:08X}",
                opcode, params[0], status->status, params[1], params[2]);

            eka2l1::ptr<epoc::request_status> completion_ptr(params[0]);
            epoc::notify_info completion(completion_ptr, thread);
            completion.complete(epoc::error_none);

            LOG_WARN(LDD_MMCIF,
                "[NBOOT2][NOKIAISC_INIT_COMPLETE] opcode={} status=0x{:08X} completion=KErrNone",
                opcode, params[0]);
            return epoc::error_none;
        }

        // Synchronous ConnectionStatus / FlowControlStatus queries use zero for
        // the healthy/offline-inert state. Other unsupported startup controls
        // remain benign until a real log shows they need richer semantics.
        return epoc::error_none;
    }
"""
        text = replace_once(text, old, new, "NokiaISC async completion")
        src.write_text(text, encoding="utf-8")

    body = src.read_text(encoding="utf-8")
    required = [
        "[NBOOT2][NOKIAISC_ASYNC]",
        "[NBOOT2][NOKIAISC_INIT_COMPLETE]",
        "completion.complete(epoc::error_none)",
        "(opcode == 0) || (opcode == 1)",
    ]
    for gate in required:
        if gate not in body:
            fail(f"runtime gate missing: {gate}")

    # Preserve B2 / RM-356 ABI invariants.
    svc_body = svc.read_text(encoding="utf-8")
    a = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = svc_body.find("\n    };", a)
    v94 = svc_body[a:b]
    if "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)" not in v94:
        fail("v94 0x0A mapping lost")
    if "BRIDGE_REGISTER(0x83, logical_channel_create_v95)" not in v94:
        fail("v94 0x83 mapping lost")
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)" not in v94:
        fail("EPOC94 0xAB invariant lost")
    if "BRIDGE_REGISTER(0xAC, message_kill)" not in v94:
        fail("EPOC94 0xAC invariant lost")

    print("NATIVEBOOT2-B3 NOKIAISC2 applied")
    print("NOKIAISC_opcode0=InitializeModemInterface_complete_KErrNone")
    print("NOKIAISC_opcode1=AsyncOpen_complete_KErrNone")
    print("EP94_0x83=ChannelCreate_PRESERVED")
    print("EP94_0x0A=ChannelRequest_PRESERVED")
    print("EMUHUB1=PRESERVED")
    print("NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
