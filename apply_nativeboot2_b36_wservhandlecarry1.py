#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B36 WSERVHANDLECARRY1 after B35.

B35 device evidence provides three converging signals:
- ws32.dll + 0x370A resolves to EABI export ordinal 206,
  RWindowTreeNode::SetNonFading(TBool);
- the immediate guest stack contains WindowServer opcode 0x5D;
- EikAppUiServerThread startup repeatedly logs invalid WindowServer object
  handles (including 0 and 0x14000000).

Symbian's own WindowServer protocol omits the destination handle when it is
unchanged. Its server keeps the previous destination object and reuses it for
subsequent commands without EWsOpcodeHandle (0x8000).

The EKA2L1 baseline instead creates a fresh ws_cmd and leaves obj_handle
uninitialized when 0x8000 is absent. B36 fixes only that generic protocol
mismatch: value-initialize ws_cmd, remember the last explicit handle within
one command buffer, and copy it into implicit-handle commands.

Narrow runtime markers are added for opcode 0x5D and SetNonFading so the first
device test can prove the corrected path. SetNonFading's existing KErrNone
completion is preserved exactly.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B36-WSERVHANDLECARRY1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b36_wservhandlecarry1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    window=up/"src/emu/services/src/window/window.cpp"
    winuser=up/"src/emu/services/src/window/classes/winuser.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    screen_h=up/"src/emu/services/include/services/window/screen.h"
    for p in (window,winuser,svc,screen_h):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    ws=window.read_text(encoding="utf-8")
    wu=winuser.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sh=screen_h.read_text(encoding="utf-8")

    # Require the exact validated chain we are extending.
    for needle,name,text in (
        ("[NBOOT2][EIKCALLSITE]","B35 EIKCALLSITE",sv),
        ("[NBOOT2][EIKCODE16]","B35 EIKCODE16",sv),
        ("std::mutex focus_callback_mutex;","B34 focus mutex split",sh),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][WSERV_HANDLE_CARRY]",
        "[NBOOT2][WSERV_NONFADING_ENTER]",
        "[NBOOT2][WSERV_NONFADING_COMPLETE]",
    )
    combined=ws+"\n"+wu
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers) and "cmd.obj_handle = nboot2_b36_previous_handle;" in ws:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B36 state: "+", ".join(present))

    # ------------------------------------------------------------------
    # 1) Correct WindowServer command-buffer destination-handle semantics.
    # Symbian RWsBuffer emits EWsOpcodeHandle only when the destination
    # changes. The server must therefore retain the previous destination for
    # commands in the same buffer that omit the handle.
    # ------------------------------------------------------------------
    parser_old='''        std::vector<ws_cmd> cmds;

        while (beg < end) {
            ws_cmd cmd;

            cmd.header = *reinterpret_cast<ws_cmd_header *>(beg);

            if (cmd.header.op & 0x8000) {
                cmd.header.op &= ~0x8000;
                cmd.obj_handle = *reinterpret_cast<std::uint32_t *>(beg + sizeof(ws_cmd_header));

                beg += sizeof(ws_cmd_header) + sizeof(cmd.obj_handle);
            } else {
                beg += sizeof(ws_cmd_header);
            }

            cmd.data_ptr = reinterpret_cast<void *>(beg);
'''
    parser_new='''        std::vector<ws_cmd> cmds;

        // B36 WSERVHANDLECARRY1: Symbian command buffers include a
        // destination handle only when it changes. Keep the last explicit
        // handle for following commands in this same buffer.
        std::uint32_t nboot2_b36_previous_handle = 0;

        while (beg < end) {
            // Value-initialize so a malformed first implicit-handle command
            // can never inherit arbitrary host stack bytes.
            ws_cmd cmd{};

            cmd.header = *reinterpret_cast<ws_cmd_header *>(beg);
            const bool nboot2_b36_explicit_handle = (cmd.header.op & 0x8000) != 0;

            if (nboot2_b36_explicit_handle) {
                cmd.header.op &= ~0x8000;
                cmd.obj_handle = *reinterpret_cast<std::uint32_t *>(beg + sizeof(ws_cmd_header));
                nboot2_b36_previous_handle = cmd.obj_handle;

                beg += sizeof(ws_cmd_header) + sizeof(cmd.obj_handle);
            } else {
                cmd.obj_handle = nboot2_b36_previous_handle;
                beg += sizeof(ws_cmd_header);
            }

            if (cmd.header.op == EWsWinOpSetNonFading) {
                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][WSERV_HANDLE_CARRY] op=0x{:X} explicit_handle={} effective_handle=0x{:08X} cmd_len={}",
                    cmd.header.op, nboot2_b36_explicit_handle ? 1 : 0,
                    cmd.obj_handle, cmd.header.cmd_len);
            }

            cmd.data_ptr = reinterpret_cast<void *>(beg);
'''
    ws=replace_once(ws,parser_old,parser_new,"WindowServer implicit-handle carry")

    # ------------------------------------------------------------------
    # 2) Trace the already-existing SetNonFading KErrNone completion.
    # Do not add/change any completion value.
    # ------------------------------------------------------------------
    fn_match=re.search(
        r"    void\s+(?:canvas_base|window_user)::set_non_fading"
        r"\s*\([^\)]*\)\s*\{",
        wu,
    )
    if not fn_match:
        fail("set_non_fading function not found")
    fn_end=wu.find("\n    void ",fn_match.end())
    if fn_end < 0:
        fail("could not bound set_non_fading function")
    block=wu[fn_match.start():fn_end]

    payload_match=re.search(
        r"(        const\s+[^\n]*\bnon_fading\s*=\s*\*reinterpret_cast<[^\n]+\n)",
        block,
    )
    if not payload_match:
        fail("SetNonFading payload anchor missing")
    enter='''        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WSERV_NONFADING_ENTER] op=0x{:X} obj_handle=0x{:08X} cmd_len={} signaled_before={}",
            cmd.header.op, cmd.obj_handle, cmd.header.cmd_len,
            context.signaled ? 1 : 0);
'''
    block=block[:payload_match.start()]+enter+block[payload_match.start():]

    completion="        context.complete(epoc::error_none);\n"
    if block.count(completion) != 1:
        fail(f"SetNonFading completion anchor count={block.count(completion)}")
    completion_trace=completion+'''        LOG_WARN(SERVICE_WINDOW,
            "[NBOOT2][WSERV_NONFADING_COMPLETE] op=0x{:X} obj_handle=0x{:08X} result={} signaled_after={}",
            cmd.header.op, cmd.obj_handle, epoc::error_none,
            context.signaled ? 1 : 0);
'''
    block=block.replace(completion,completion_trace,1)
    wu=wu[:fn_match.start()]+block+wu[fn_end:]

    # Scope gates: parser protocol + diagnostics only.
    if "context.complete(epoc::error_cancel);" in block:
        fail("SetNonFading KErrCancel behavior change detected")
    if "avkonfep_general.dll" in (ws+"\n"+wu):
        fail("stock FEP invariant violated")
    for needle in (
        "execute_commands(ctx, std::move(cmds));",
        "context.complete(epoc::error_none);",
        "cmd.obj_handle = nboot2_b36_previous_handle;",
        "nboot2_b36_previous_handle = cmd.obj_handle;",
        "ws_cmd cmd{};",
    ):
        if needle not in (ws+"\n"+wu):
            fail(f"post-apply semantic missing: {needle}")

    window.write_text(ws,encoding="utf-8")
    winuser.write_text(wu,encoding="utf-8")

    out=ws+"\n"+wu
    for marker in markers:
        if marker not in out:
            fail(f"post-apply marker missing: {marker}")

    print(f"{MARK}: applied")
    print("scope=WSERV_COMMAND_BUFFER_IMPLICIT_HANDLE_ONLY")
    print("symbian_protocol=PREVIOUS_DESTINATION_HANDLE_REUSED")
    print("set_non_fading_completion=UNCHANGED_KErrNone")
    print("stock_fep=PRESERVED")
    print("leave_trap_behavior=UNCHANGED")
    print("B34_B35=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
