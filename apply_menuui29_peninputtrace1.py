#!/usr/bin/env python3
"""MENUUI29 PENINPUTTRACE1: trace guest IPC to Nokia peninputserver.

MENUUI28 device evidence:
- peninputanim.dll native bridge loads successfully.
- CreateInstanceSprite succeeds and FinishConstruction(501) is observed.
- No Activate(502) and no raw_mirror are observed.
- Therefore the next unknown is whether Avkon FEP/client ever sends the
  PenInput server requests that create/activate a UI layout.

This patch is diagnostic only. It instruments session_send_general() for the
guest CServer2 named "peninputserver" and logs every IPC before and after the
send/receive call. No return values, IPC arguments, scheduling, WindowServer,
PenInput animation, or application behavior are modified.

Relevant Nokia S60 PenInput request opcodes:
  0x0D ActivateLayout
  0x0E SetUiLayoutId
  0x0F SetUiLayoutIdWithData
  0x12 SetForeground
  0x13 IsForeground
  0x1D ServerThreadId

Preserves MENUUI28 PENINPUTANIM1 and the full prior lineage.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI29 PENINPUTTRACE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n = text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui29_peninputtrace1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc = up / "src/emu/kernel/src/svc.cpp"
    anim_cpp = up / "src/emu/services/src/window/classes/plugins/animdll.cpp"
    win_cpp = up / "src/emu/services/src/window/window.cpp"
    wg_cpp = up / "src/emu/services/src/window/classes/wingroup.cpp"
    fs_cpp = up / "src/emu/services/src/fs/fs.cpp"
    applist = up / "src/emu/services/src/applist/applist.cpp"
    oom = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (svc, anim_cpp, win_cpp, wg_cpp, fs_cpp, applist, oom, kernel, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    text = svc.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC:" in text:
        print("MENUUI29 PENINPUTTRACE1 already present")
        return

    # Proven lineage gates.
    if "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:" not in anim_cpp.read_text(encoding="utf-8"):
        fail("MENUUI28 PENINPUTANIM1 baseline missing")
    if "mirror_peninput_raw_event" not in win_cpp.read_text(encoding="utf-8"):
        fail("MENUUI28 raw-event bridge missing")
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
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:" not in text:
        fail("MENUUI22 sync diagnostics missing")
    if "MANIC_MODALFIX1" not in root.read_text(encoding="utf-8"):
        fail("MANIC3 baseline missing")

    old = """        const std::string server_name = ss->get_server()->name();
"""
    new = """        const std::string server_name = ss->get_server()->name();

        const bool menuui29_peninput = (server_name == "peninputserver");
        if (menuui29_peninput) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC: stage=send sync={} opcode={} handle={} caller='{}' status=0x{:08X} flags=0x{:08X} args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
                sync ? 1 : 0, ord, h, crr_pr ? crr_pr->name() : std::string("<null>"),
                status.ptr_address(), arg.flag,
                arg.args[0], arg.args[1], arg.args[2], arg.args[3]);
        }
"""
    text = replace_once(text, old, new, "peninput send trace")

    old = """        const int result = sync ? ss->send_receive_sync(ord, arg, status) : ss->send_receive(ord, arg, status);
"""
    new = """        const int result = sync ? ss->send_receive_sync(ord, arg, status) : ss->send_receive(ord, arg, status);

        if (menuui29_peninput) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC: stage=return sync={} opcode={} handle={} caller='{}' result={} status=0x{:08X}",
                sync ? 1 : 0, ord, h, crr_pr ? crr_pr->name() : std::string("<null>"),
                result, status.ptr_address());
        }
"""
    text = replace_once(text, old, new, "peninput return trace")
    svc.write_text(text, encoding="utf-8")

    final = svc.read_text(encoding="utf-8")
    for gate in (
        'server_name == "peninputserver"',
        "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC: stage=send",
        "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC: stage=return",
        "arg.args[0]",
        "status.ptr_address()",
    ):
        if gate not in final:
            fail(f"trace gate missing: {gate}")

    print("MENUUI29 PENINPUTTRACE1 applied")
    print("behavior_change=NONE")
    print("peninputserver_guest_ipc_send_return=TRACED")
    print("opcodes_0D_0E_0F_12_13_1D=INTERPRETABLE")
    print("MENUUI28/MENUUI27/MENUUI26/MENUUI25/MENUUI24/MENUUI23/SCHEDRUN1/MANIC3/NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
