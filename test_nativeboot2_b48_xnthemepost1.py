#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B48 XNTHEMEPOST1.

B48 is diagnostic-only. It must expose the Home screen/xnthemeserver IPC
completion boundary and xnthemeserver FileFlush result without changing any
completion value, FileServer result, FS-DIRUID1 semantics, or B47 TFX state.
"""
from pathlib import Path
import re
import sys

MARK = "NATIVEBOOT2-B48-XNTHEMEPOST1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b48_xnthemepost1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc_path = up / "src/emu/kernel/src/svc.cpp"
    repo_path = up / "src/emu/services/src/centralrepo/repo.cpp"
    files_path = up / "src/emu/services/src/fs/files.cpp"
    dirs_path = up / "src/emu/services/src/fs/dirs.cpp"
    op_path = up / "src/emu/services/include/services/fs/op.h"

    for p in (svc_path, repo_path, files_path, dirs_path, op_path):
        if not p.is_file():
            fail(f"missing source: {p}")

    svc = svc_path.read_text(encoding="utf-8")
    repo = repo_path.read_text(encoding="utf-8")
    files = files_path.read_text(encoding="utf-8")
    dirs = dirs_path.read_text(encoding="utf-8")
    op = op_path.read_text(encoding="utf-8")

    # New B48 boundaries.
    need(svc, "[NBOOT2][XNTHEME_IPC]", "xntheme IPC marker")
    need(svc, "phase=send", "xntheme request trace")
    need(svc, "phase=complete", "xntheme completion trace")
    need(svc, 'server_name == "xnthemeserver"', "xntheme target")
    need(svc, "0x10207254U", "xntheme server UID")
    need(svc, "behavior=OBSERVE_ONLY", "B48 observe-only marker")
    need(files, "[NBOOT2][XNTHEME_FSFLUSH]", "FileFlush marker")
    need(files, "b48_flush_ok = vfs_file->flush()", "single FileFlush result")
    need(files, "opcode=0x27", "FileFlush opcode annotation")

    # Confirm what 0x27 actually is in the current FileServer ABI.
    need(op, "fs_msg_file_flush = 39", "FileServer opcode authority")

    # Preserve the already device-validated theme enumeration fix.
    need(dirs, "SYMBIAN-SYSTEMAPPS1 MENUUI13 FS_DIRUID1:",
         "MENUUI13 FS-DIRUID1 runtime marker")
    need(dirs, "attrib |= io_attrib_allow_uid;", "allow-UID behavior")
    open_start = dirs.find("void fs_server_client::open_dir")
    open_end = dirs.find("void fs_server_client::close_dir", open_start)
    if open_start < 0 or open_end < 0:
        fail("cannot isolate open_dir")
    open_block = dirs[open_start:open_end]
    if "attrib &= ~io_attrib_include_dir;" in open_block:
        fail("B48 regressed FS-DIRUID1 directory inclusion")

    # Preserve B47's stock-firmware conclusion and diagnostics. The state
    # marker is in CentralRepository; the Wserv/ECom markers are in svc.cpp.
    need(repo, "[NBOOT2][AKNSKIN_TFX_STATE]", "B47 CenRep preservation")
    for needle in (
        "[NBOOT2][AKNSKIN_TFX_WSERV]",
        "[NBOOT2][AKNSKIN_TFX_ECOM]",
        "SYMBIAN-SYSTEMAPPS1 MENUUI12 XNTHEME_COMPLETE:",
    ):
        need(svc, needle, "predecessor preservation")

    # FileFlush behavior must remain the original three-way result:
    # bad handle, flush failure, success. No KErrNotSupported substitution.
    fs = files.find("void fs_server_client::file_flush")
    fe = files.find("void fs_server_client::file_rename", fs)
    if fs < 0 or fe < 0:
        fail("cannot isolate file_flush")
    fb = files[fs:fe]
    for needle in (
        "ctx->complete(epoc::error_bad_handle);",
        "ctx->complete(epoc::error_general);",
        "ctx->complete(epoc::error_none);",
    ):
        need(fb, needle, "FileFlush original completion")
    if fb.count("vfs_file->flush()") != 1:
        fail("FileFlush must call VFS flush exactly once")
    if "ctx->complete(epoc::error_not_supported);" in fb:
        fail("B48 must not synthesize KErrNotSupported")

    # xntheme logging must not rewrite request opcode/arguments or completion.
    ss = svc.find("static std::int32_t session_send_general")
    se = svc.find("BRIDGE_FUNC(std::int32_t, session_send_sync", ss)
    if ss < 0 or se < 0:
        fail("cannot isolate session_send_general")
    sb = svc[ss:se]
    need(sb, "ss->send_receive_sync(ord, arg, status)", "sync dispatch")
    need(sb, "ss->send_receive(ord, arg, status)", "async dispatch")
    need(sb, "return result;", "original send result")

    cs = svc.find("BRIDGE_FUNC(void, message_complete")
    ce = svc.find("\n    BRIDGE_FUNC(", cs + 1)
    if cs < 0 or ce < 0:
        fail("cannot isolate message_complete")
    cb = svc[cs:ce]
    need(cb, "kern->call_ipc_complete_callbacks(msg, val);",
         "original completion callback")
    # The B48 completion block logs val; it must never assign to val.
    m = cb.find("[NBOOT2][XNTHEME_IPC] phase=complete")
    if m < 0:
        fail("cannot isolate B48 completion marker")
    around = cb[max(0, m-1600):m+1800]
    if re.search(r"\bval\s*=(?!=)", around):
        fail("B48 appears to rewrite completion value")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("scope=DIAGNOSTIC_ONLY")
    print("FS_DIRUID1=PRESERVED")
    print("B47_STOCK_TFX_SUPPRESSION=PRESERVED")
    print("xntheme_completion_rewrite=NONE")
    print("fileflush_completion_rewrite=NONE")

if __name__ == "__main__":
    main()
