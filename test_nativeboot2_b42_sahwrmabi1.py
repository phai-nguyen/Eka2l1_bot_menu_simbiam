#!/usr/bin/env python3
"""RED source contract for NATIVEBOOT2 B42 SAHWRMABI1.

B41 device evidence leaves one earlier boot blocker before the later
Starter shutdown path:
- HWRMServer loads lightsadaptation.dll;
- SAServer receives raw function 0x2000000A;
- the old dispatcher reports it as unimplemented and leaves the request
  outstanding;
- about 30 seconds later SYSSTART begins HWRM failure recovery.

The public Nokia/Symbian sources do not document the proprietary raw SA
transport encoding for 0x2000000A. B42 is therefore diagnostic-only: register
only that exact raw function, log its IPC ABI and caller identity, and preserve
the historical outstanding-request semantics by returning without completing
or mutating descriptors.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B42-SAHWRMABI1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b42_sahwrmabi1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    messagewin=up/"src/emu/services/src/window/classes/plugins/anim/clock/messagewin.cpp"
    window=up/"src/emu/services/src/window/window.cpp"

    for p in (sa,loader,messagewin,window):
        if not p.is_file():
            fail(f"missing source file: {p}")

    s=sa.read_text(encoding="utf-8")
    ld=loader.read_text(encoding="utf-8")
    mw=messagewin.read_text(encoding="utf-8")
    ws=window.read_text(encoding="utf-8")

    # Canonical RED: B41 baseline must not already contain the B42 probe.
    need(s,"[NBOOT2][SA_HWRM_ABI]","B42 runtime marker")

    for needle in (
        "ctx.msg->function == 0x2000000A",
        "raw_func=0x{:08X}",
        "logical_func=0x{:X}",
        "transport_bits=0x{:08X}",
        "ipc_flag=0x{:X}",
        "process={} thread={} session={}",
        "raw_args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "types=[{},{},{},{}]",
        "sizes=[{},{},{},{}]",
        "max=[{},{},{},{}]",
        "preview0=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview1=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview2=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview3=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "completion=UNCHANGED_PENDING",
        'REGISTER_IPC(sa_server, unk_op1, 0x2000000A, "NBOOT2::SaHwrmAbiProbe");',
    ):
        need(s,needle,"B42 SA ABI contract")

    start=s.find("// NATIVEBOOT2-B42 SAHWRMABI1:")
    end=s.find("// NATIVEBOOT2-B19 SALANGABI1:",start)
    if start < 0 or end < 0 or end <= start:
        fail("cannot isolate B42 diagnostic block")
    block=s[start:end]

    # Diagnostic-only means no guest-visible completion or descriptor mutation.
    for forbidden in (
        "ctx.complete(",
        "write_data_to_descriptor_argument",
        "set_descriptor_argument_length",
        "pending_sa_event_.complete(",
    ):
        if forbidden in block:
            fail(f"B42 diagnostic block changes guest semantics: {forbidden}")

    if "return;" not in block:
        fail("B42 diagnostic handler must return with request still outstanding")
    if "get_descriptor_argument_ptr" not in block or "std::memcpy" not in block:
        fail("B42 does not safely inspect descriptor contents")
    if "own_thr->owning_process()->raw_name()" not in block:
        fail("B42 does not identify caller process")
    if "own_thr->name()" not in block:
        fail("B42 does not identify caller thread")
    if "msg_session->unique_id()" not in block:
        fail("B42 does not identify caller session")

    # Existing device-validated baseline must remain intact.
    need(s,"[NBOOT2][SA_LANG_ABI]","B19 SA language diagnostic")
    need(ld,"[NBOOT2][LOADER_PDD]","B40 Loader PDD")
    need(mw,"[NBOOT2][WSERV_MESSAGEWIN_EXIT]","B41 MessageWin exit guard")
    need(ws,"[NBOOT2][WSERV_HANDLE_CARRY]","B36 handle carry")
    need(ws,"[NBOOT2][WSERV_BATCH_DEFER_BEGIN]","B37 batch deferral")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=EXACT_RAW_SASERVER_0x2000000A_DIAGNOSTIC_ONLY")
    print("descriptor_writes=NONE")
    print("completion=UNCHANGED_PENDING")
    print("B19_B36_B37_B40_B41=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
