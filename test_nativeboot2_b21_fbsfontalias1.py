#!/usr/bin/env python3
"""Source-level contract for NATIVEBOOT2 B21 FBSFONTALIAS1.

B21 fixes the first deterministic UI blocker observed on RM-356 after B20:
    Unhandled FBScli opcode 0x1E
followed ~30 s later by akncapserver.exe being killed with KErrTimedOut.

Symbian 9.4 defines opcode 0x1E as EFbsMessFontNameAlias. The real client
sends:
    slot0 = TDesC16 alias
    slot1 = alias length (TInt)
    slot2 = TDesC16 target font name
    slot3 = target length (TInt)
and the server adds/updates/removes a case-insensitive alias then completes.

Contract:
- route fbs_font_name_alias in fbscli::fetch();
- decode descriptors and explicit lengths;
- implement add/update/delete semantics;
- resolve aliases before exact typeface lookup;
- complete the IPC (never leave it pending);
- emit deterministic NATIVEBOOT2 diagnostics;
- preserve B20 and all earlier boot markers/invariants.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B21-FBSFONTALIAS1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b21_fbsfontalias1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    fbs_h = up / "src/emu/services/include/services/fbs/fbs.h"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    store_h = up / "src/emu/services/include/services/fbs/font_store.h"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (fbs_cpp, fbs_h, store_cpp, store_h, repo_cpp, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    fc = fbs_cpp.read_text(encoding="utf-8")
    fh = fbs_h.read_text(encoding="utf-8")
    sc = store_cpp.read_text(encoding="utf-8")
    sh = store_h.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # Opcode 30 / 0x1E already exists in the public TFbsMessage-compatible enum.
    need(fh, "fbs_font_name_alias", "fbs.h")

    # FBS session must explicitly route the command.
    need(fc, "case fbs_font_name_alias:", "fbs.cpp")
    need(fc, "set_font_name_alias(ctx);", "fbs.cpp")
    need(fh, "void set_font_name_alias(service::ipc_context *ctx);", "fbs.h")

    start = fc.find("// NATIVEBOOT2-B21 FBSFONTALIAS1:")
    if start < 0:
        fail("missing B21 FBS IPC implementation block")
    end = fc.find("void fbscli::fetch", start)
    if end < 0:
        fail("cannot isolate B21 FBS IPC implementation")
    block = fc[start:end]

    for needle in (
        "void fbscli::set_font_name_alias(service::ipc_context *ctx)",
        "get_argument_value<std::u16string>(0)",
        "get_argument_value<std::int32_t>(1)",
        "get_argument_value<std::u16string>(2)",
        "get_argument_value<std::int32_t>(3)",
        "[NBOOT2][FBS_FONT_ALIAS]",
        "font_name_alias",
        "ctx->complete(epoc::error_none);",
        "ctx->complete(epoc::error_bad_descriptor);",
    ):
        need(block, needle, "B21 FBS IPC block")

    # Persistent alias storage and case-insensitive add/update/delete semantics.
    for needle in (
        "font_name_aliases_",
        "void set_font_name_alias(const std::u16string &alias, const std::u16string &font_name);",
        "std::optional<std::u16string> resolve_font_name_alias(const std::u16string &alias) const;",
    ):
        need(sh, needle, "font_store.h")

    for needle in (
        "void font_store::set_font_name_alias",
        "std::optional<std::u16string> font_store::resolve_font_name_alias",
        "common::compare_ignore_case",
        "font_name_aliases_.erase",
        "font_name_aliases_.emplace_back",
    ):
        need(sc, needle, "font_store.cpp")

    # Alias must affect real lookup, not merely be acknowledged.
    seek_start = sc.find("open_font_info *font_store::seek_the_open_font")
    if seek_start < 0:
        fail("seek_the_open_font missing")
    seek_end = sc.find("open_font_info *font_store::", seek_start + 10)
    seek_block = sc[seek_start:] if seek_end < 0 else sc[seek_start:seek_end]
    need(seek_block, "resolve_font_name_alias(requested_name)", "seek_the_open_font")
    need(seek_block, "aliased_name", "seek_the_open_font")
    need(seek_block, "my_name", "seek_the_open_font")

    # No synthetic-only implementation: the IPC handler must call into font_store.
    need(block, "persistent_font_store.set_font_name_alias", "B21 FBS IPC block")

    # B20 and earlier boot-chain contracts remain present.
    for needle in (
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
        "[NBOOT2][CEN_RESET_ALL_FAIL]",
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
