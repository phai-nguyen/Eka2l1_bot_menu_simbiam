#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B25 FBSSHAREDHEAP1.

B24 device evidence:
- Native fbserv creates FbsSharedChunk at 0x40200000 and FbsLargeChunk at 0x44200000.
- HLE FBS later creates a second canonical FbsSharedChunk at 0x54200000.
- HLE returns address_offset=0x1598 for object 0x54201598.
- RFbsSession reconstructs pointer from the canonical global chunk it opened:
  0x40200000 + 0x1598 = 0x40201598, exactly r0 at KERN-EXEC 3.
- B24 proved CBitmapFont ordinal 97 relocation itself is correct.

Symbian source confirms RFbsSession::DoConnect opens global FbsSharedChunk by name.
The native fbserv creates the global chunks during startup and keeps handles.

B25 scope:
- preserve native fbserv startup/rendezvous;
- on first HLE FBS initialization, if canonical FBS chunks already exist and are
  guest-process-owned, rename those existing native chunks to internal names;
- then let HLE FBS create the canonical FbsSharedChunk/FbsLargeChunk as before;
- do not adopt/native-heap-allocate, do not block fbserv, do not alter vtable,
  TFontSpec, font matcher, AppServer, or startup ownership.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B25-FBSSHAREDHEAP1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b25_fbssharedheap1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    font_cpp = up / "src/emu/services/src/fbs/impls/font.cpp"
    loader_cpp = up / "src/emu/services/src/loader/loader.cpp"
    state_cpp = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (fbs_cpp, font_cpp, loader_cpp, state_cpp, root, repo_cpp, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    fbs = fbs_cpp.read_text(encoding="utf-8")
    font = font_cpp.read_text(encoding="utf-8")
    loader = loader_cpp.read_text(encoding="utf-8")
    state = state_cpp.read_text(encoding="utf-8")
    root_text = root.read_text(encoding="utf-8")
    repo = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    start = fbs.find("void fbs_server::initialize_server()")
    if start < 0:
        fail("initialize_server missing")
    end = fbs.find("void fbs_server::connect", start)
    if end < 0:
        fail("cannot isolate initialize_server")
    init = fbs[start:end]

    # Handoff must happen before HLE creates canonical chunks.
    for needle in (
        "// NATIVEBOOT2-B25 FBSSHAREDHEAP1:",
        'get_by_name_and_type<kernel::chunk>("FbsSharedChunk"',
        'get_by_name_and_type<kernel::chunk>("FbsLargeChunk"',
        'get_own_process()',
        'rename("FbsSharedChunk.NativeBoot")',
        'rename("FbsLargeChunk.NativeBoot")',
        "[NBOOT2][FBS_SHARED_HEAP_HANDOFF]",
        "[NBOOT2][FBS_SHARED_HEAP_READY]",
    ):
        need(init, needle, "fbs_server::initialize_server")

    handoff_pos = init.find("[NBOOT2][FBS_SHARED_HEAP_HANDOFF]")
    create_pos = init.find('"FbsSharedChunk",')
    if handoff_pos < 0 or create_pos < 0 or handoff_pos >= create_pos:
        fail("native chunk handoff must occur before HLE canonical chunk creation")

    # Only guest-process-owned existing chunks are renamed; HLE/kernel-owned chunks
    # must not be renamed on a re-entry path.
    need(init, "native_shared->get_own_process()", "fbs_server::initialize_server")
    need(init, "native_large->get_own_process()", "fbs_server::initialize_server")

    # B25 must continue creating its own HLE chunks/allocators rather than adopting
    # the native RHeap memory directly.
    for needle in (
        'kernel::owner_type::kernel',
        'std::make_unique<epoc::chunk_allocator>(shared_chunk)',
        'std::make_unique<epoc::chunk_allocator>(large_chunk)',
    ):
        need(init, needle, "fbs_server::initialize_server")

    if "shared_chunk = native_shared" in init or "large_chunk = native_large" in init:
        fail("B25 must not adopt native fbserv heap into HLE allocator")

    # Do not suppress/spoof native fbserv startup.
    if 'name_process == "fbserv"' in loader or 'name_process == "fbserv.exe"' in loader:
        fail("B25 loader must not special-case/block fbserv")
    need(state, "[NBOOT2][ESTART_RUN]", "state.cpp")

    # Earlier diagnostics/fixes remain.
    for needle in (
        "[NBOOT2][FBS_FONT_SPEC_ABI]",
        "[NBOOT2][FBS_FONT_RETURN]",
        "[NBOOT2][FBS_VTABLE_RELOC]",
    ):
        need(font, needle, "font.cpp")
    need(fbs, "[NBOOT2][FBS_DEFAULT_TYPEFACE]", "fbs.cpp")
    need(fbs, "[NBOOT2][FBS_FONT_ALIAS]", "fbs.cpp")
    need(repo, "[NBOOT2][CEN_RESET_ALL_DONE]", "repo.cpp")
    need(sa, "[NBOOT2][SA_LANG_ABI]", "sa.cpp")
    need(root_text, "NATIVEBOOT2 EMUHUB1", "RootViewController.mm")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
