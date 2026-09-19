#!/usr/bin/env python3
"""NATIVEBOOT2-B12 SAIPC1.

Apply on top of B11 DMINIT1.

Observed B11 device runtime:
- domainSrv completes Domain Manager initialization.
- EStart leaves WaitForInitialization(), launches native SYSSTART.EXE, and exits cleanly.
- SysStart reads Z:\\resource\\starter_arm.RSC and advances into the startup adaptation path.
- StartupAdaptation.dll then calls SAServer opcode 0x1.
- EKA2L1's SAServer implements unk_op1 as KErrNone, but registers it only at opcode 1001.

RM-356/S60v5 therefore reaches an SA IPC ABI mismatch. B12 aliases legacy opcode 1
onto the existing handler while preserving opcode 1001. No component is host-launched;
firmware/SysStart remains the owner of boot ordering.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B12-SAIPC1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b12_saipc1.py <upstream-root>")

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
            fail(f"missing B11 baseline file: {p}")

    # Require the exact B11 baseline invariants before touching SAServer.
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

    text = sa.read_text(encoding="utf-8")
    legacy = 'REGISTER_IPC(sa_server, unk_op1, 1, "NBOOT2::SaServerLegacyOp1");'
    modern = 'REGISTER_IPC(sa_server, unk_op1, 1001, "SaServer::UnkOp1");'

    if legacy not in text:
        old = f"""    sa_server::sa_server(eka2l1::system *sys)
        : service::server(sys->get_kernel_system(), sys, nullptr, "SAServer", true) {{
        {modern}
    }}
"""
        new = f"""    sa_server::sa_server(eka2l1::system *sys)
        : service::server(sys->get_kernel_system(), sys, nullptr, "SAServer", true) {{
        // NATIVEBOOT2-B12 SAIPC1:
        // RM-356 StartupAdaptation.dll uses the S60v5/legacy SA function number 1.
        // Keep the existing 1001 registration for newer clients and alias opcode 1
        // to the same no-op/KErrNone compatibility handler.
        {legacy}
        {modern}
    }}
"""
        text = replace_once(text, old, new, "SAServer opcode registration")
        sa.write_text(text, encoding="utf-8")

    body = sa.read_text(encoding="utf-8")
    for gate in (
        legacy,
        modern,
        "ctx.complete(epoc::error_none);",
        "NATIVEBOOT2-B12 SAIPC1",
    ):
        if gate not in body:
            fail(f"B12 gate missing: {gate}")

    print("NATIVEBOOT2-B12 SAIPC1 applied")
    print("SAServer_opcode_1=unk_op1_KErrNone")
    print("SAServer_opcode_1001=PRESERVED")
    print("boot_owner=firmware_SYSSTART")
    print("B11_DMINIT1=PRESERVED")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
