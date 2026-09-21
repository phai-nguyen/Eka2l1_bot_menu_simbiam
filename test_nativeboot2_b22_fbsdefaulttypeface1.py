#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B22 FBSDEFAULTTYPEFACE1.

B21 device evidence:
- FBS 0x1E FontNameAlias now completes successfully.
- AknCapServer immediately issues FBS 0x2D and stalls.
- ~30 seconds later Domino kills AknCapServer with KErrTimedOut.
- Emulator exit logs BRIDGE_EXIT then never reaches normal-mode restart.

Symbian 9.4 defines 0x2D/45 as EFbsSetSystemDefaultTypefaceName.
CFbsTypefaceStore::SetSystemDefaultTypefaceNameL sends one UTF-16
descriptor in slot 0. The server stores the name, completes synchronously,
and uses it when nearest-font lookup receives an empty typeface name.

B22 functional scope:
- implement the real FBS 0x2D semantics with KMaxTypefaceNameLength=0x18;
- apply the stored default only when the requested typeface name is empty;
- preserve B21 alias behavior and all prior native-boot checkpoints.

B22 diagnostic-only scope:
- instrument native-mode exit/shutdown phases to localize the teardown hang;
- do not alter shutdown behavior in this build.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B22-FBSDEFAULTTYPEFACE1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b22_fbsdefaulttypeface1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    fbs_h = up / "src/emu/services/include/services/fbs/fbs.h"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    store_h = up / "src/emu/services/include/services/fbs/font_store.h"
    bridge = up / "src/emu/ios/src/emu_bridge.mm"
    thread_cpp = up / "src/emu/ios/src/thread.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (fbs_cpp, fbs_h, store_cpp, store_h, bridge, thread_cpp, repo_cpp, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    fc = fbs_cpp.read_text(encoding="utf-8")
    fh = fbs_h.read_text(encoding="utf-8")
    sc = store_cpp.read_text(encoding="utf-8")
    sh = store_h.read_text(encoding="utf-8")
    br = bridge.read_text(encoding="utf-8")
    th = thread_cpp.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # Public TFbsMessage-compatible enum already has opcode 45 / 0x2D.
    need(fh, "fbs_set_system_default_typeface_name", "fbs.h")

    # Explicit route and handler.
    need(fh, "void set_system_default_typeface_name(service::ipc_context *ctx);", "fbs.h")
    need(fc, "case fbs_set_system_default_typeface_name:", "fbs.cpp")
    need(fc, "set_system_default_typeface_name(ctx);", "fbs.cpp")
    need(fc, "[NBOOT2][FBS_DEFAULT_TYPEFACE]", "fbs.cpp")

    start = fc.find("// NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1:")
    if start < 0:
        fail("missing B22 FBS implementation block")
    end = fc.find("void fbscli::fetch", start)
    if end < 0:
        fail("cannot isolate B22 FBS implementation")
    block = fc[start:end]

    for needle in (
        "void fbscli::set_system_default_typeface_name(service::ipc_context *ctx)",
        "get_argument_value<std::u16string>(0)",
        "KMaxTypefaceNameLength = 0x18",
        "epoc::error_too_big",
        "epoc::error_bad_descriptor",
        "persistent_font_store.set_system_default_typeface_name",
        "ctx->complete(epoc::error_none);",
    ):
        need(block, needle, "B22 FBS block")

    # Persistent server-side state.
    for needle in (
        "system_default_typeface_name_",
        "void set_system_default_typeface_name(const std::u16string &name);",
        "const std::u16string &system_default_typeface_name() const;",
    ):
        need(sh, needle, "font_store.h")

    for needle in (
        "void font_store::set_system_default_typeface_name",
        "font_store::system_default_typeface_name() const",
    ):
        need(sc, needle, "font_store.cpp")

    # Default typeface affects nearest-font lookup only for an empty requested name.
    seek_start = sc.find("open_font_info *font_store::seek_the_open_font")
    if seek_start < 0:
        fail("seek_the_open_font missing")
    seek_end = sc.find("open_font_info *font_store::", seek_start + 10)
    seek_block = sc[seek_start:] if seek_end < 0 else sc[seek_start:seek_end]
    for needle in (
        "requested_name.empty()",
        "system_default_typeface_name()",
        "effective_requested_name",
        "resolve_font_name_alias(effective_requested_name)",
    ):
        need(seek_block, needle, "seek_the_open_font")

    # B21 alias support remains functional and precedes B22 in the chain.
    for needle in (
        "[NBOOT2][FBS_FONT_ALIAS]",
        "case fbs_font_name_alias:",
        "set_font_name_alias(ctx);",
    ):
        need(fc, needle, "fbs.cpp")
    need(sc, "font_store::resolve_font_name_alias", "font_store.cpp")

    # Exit path is diagnostic only: bridge markers bracket helper, state
    # destruction and restart without changing any teardown operation.
    for phase in (
        "exit_requested",
        "shutdown_begin",
        "shutdown_threads_begin",
        "shutdown_threads_done",
        "state_reset_begin",
        "state_reset_done",
        "shutdown_done",
        "normal_restart_begin",
        "normal_restart_done",
    ):
        need(br, f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}", "emu_bridge.mm")

    # Internal thread teardown markers localize a hang to the existing B21
    # request_exit/core-wakeup/join sequence. They are instrumentation only.
    for phase in (
        "flags_set",
        "request_exit",
        "core_wakeup",
        "os_join_begin",
        "os_join_done",
        "graphics_abort",
        "graphics_join_begin",
        "graphics_join_done",
    ):
        need(th, f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}", "thread.cpp")

    # Earlier checkpoints remain present.
    for needle in (
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
    ):
        need(rp, needle, "repo.cpp")

    for needle in (
        "[NBOOT2][SA_LANG_ABI]",
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
    ):
        need(sa, needle, "sa.cpp")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
