#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B25 FBSSHAREDHEAP1 on top of B24.

B24 device evidence:
- Native fbserv creates FbsSharedChunk at 0x40200000 and FbsLargeChunk at 0x44200000.
- HLE FBS later creates another canonical FbsSharedChunk at 0x54200000.
- HLE returns address_offset=0x1598 for object 0x54201598.
- RFbsSession reconstructs 0x40200000 + 0x1598 = 0x40201598, exactly the
  AknCapServer r0 at KERN-EXEC 3.
- B24 proved CBitmapFont ordinal-97 relocation itself is correct.

B25 keeps native fbserv startup/rendezvous and its chunk handles intact. Before
HLE FBS creates its canonical chunks, guest-process-owned chunks currently
using the canonical names are renamed to internal NativeBoot names. HLE then
creates its own canonical chunks and allocators exactly as before.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B25-FBSSHAREDHEAP1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b25_fbssharedheap1.py <upstream-root>")

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
            fail(f"missing baseline file: {p}")

    fbs = fbs_cpp.read_text(encoding="utf-8")
    font = font_cpp.read_text(encoding="utf-8")
    loader = loader_cpp.read_text(encoding="utf-8")
    state = state_cpp.read_text(encoding="utf-8")
    root_text = root.read_text(encoding="utf-8")
    repo = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # B24 and prior checkpoint gates.
    for needle in (
        "[NBOOT2][FBS_FONT_SPEC_ABI]",
        "[NBOOT2][FBS_FONT_RETURN]",
        "[NBOOT2][FBS_VTABLE_RELOC]",
    ):
        if needle not in font:
            fail(f"B23/B24 checkpoint missing: {needle}")
    for needle in ("[NBOOT2][FBS_DEFAULT_TYPEFACE]", "[NBOOT2][FBS_FONT_ALIAS]"):
        if needle not in fbs:
            fail(f"B21/B22 checkpoint missing: {needle}")
    if "[NBOOT2][CEN_RESET_ALL_DONE]" not in repo:
        fail("B20 checkpoint missing")
    if "[NBOOT2][SA_LANG_ABI]" not in sa:
        fail("B19 checkpoint missing")
    if "[NBOOT2][ESTART_RUN]" not in state:
        fail("native boot ownership checkpoint missing")
    if "NATIVEBOOT2 EMUHUB1" not in root_text:
        fail("EMUHUB1 checkpoint missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # B25 must not suppress/spoof the firmware fbserv process.
    if 'name_process == "fbserv"' in loader or 'name_process == "fbserv.exe"' in loader:
        fail("baseline unexpectedly special-cases fbserv")

    init_anchor = """    void fbs_server::initialize_server() {
        // Initialize those chunks
"""
    handoff = r'''    void fbs_server::initialize_server() {
        // NATIVEBOOT2-B25 FBSSHAREDHEAP1:
        // The firmware fbserv may already own globally named FBS chunks.
        // RFbsSession opens the canonical global name and later reconstructs
        // returned object pointers as HeapBase + address_offset. Keep native
        // fbserv and its handles alive, but free the canonical names so the
        // HLE heap that produces those offsets is the one clients open.
        LOG_WARN(SERVICE_FBS,
            "[NBOOT2][FBS_SHARED_HEAP_HANDOFF] phase=probe");

        kernel::chunk *native_shared =
            kern->get_by_name_and_type<kernel::chunk>("FbsSharedChunk",
                kernel::object_type::chunk);
        kernel::chunk *native_large =
            kern->get_by_name_and_type<kernel::chunk>("FbsLargeChunk",
                kernel::object_type::chunk);

        const bool native_shared_guest_owned =
            native_shared && native_shared->get_own_process();
        const bool native_large_guest_owned =
            native_large && native_large->get_own_process();

        if (native_shared_guest_owned) {
            native_shared->rename("FbsSharedChunk.NativeBoot");
        }

        if (native_large_guest_owned) {
            native_large->rename("FbsLargeChunk.NativeBoot");
        }

        LOG_WARN(SERVICE_FBS,
            "[NBOOT2][FBS_SHARED_HEAP_HANDOFF] shared_found={} shared_guest_owned={} shared_renamed={} large_found={} large_guest_owned={} large_renamed={}",
            native_shared != nullptr, native_shared_guest_owned, native_shared_guest_owned,
            native_large != nullptr, native_large_guest_owned, native_large_guest_owned);

        // Initialize those chunks
'''
    if "// NATIVEBOOT2-B25 FBSSHAREDHEAP1:" not in fbs:
        fbs = replace_once(fbs, init_anchor, handoff, "FBS native shared-heap handoff")

    ready_anchor = """        if (!shared_chunk || !large_chunk) {
            LOG_CRITICAL(SERVICE_FBS, "Can't create shared chunk and large chunk of FBS, exiting");
            return;
        }

"""
    ready_new = ready_anchor + r'''        LOG_WARN(SERVICE_FBS,
            "[NBOOT2][FBS_SHARED_HEAP_READY] shared_created={} large_created={} canonical_owner=kernel native_shared_renamed={} native_large_renamed={}",
            shared_chunk != nullptr, large_chunk != nullptr,
            native_shared_guest_owned, native_large_guest_owned);

'''
    if "[NBOOT2][FBS_SHARED_HEAP_READY]" not in fbs:
        fbs = replace_once(fbs, ready_anchor, ready_new, "FBS canonical shared-heap ready marker")

    fbs_cpp.write_text(fbs, encoding="utf-8")

    # Post-apply boundedness and contract gates.
    fbs = fbs_cpp.read_text(encoding="utf-8")
    start = fbs.find("void fbs_server::initialize_server()")
    end = fbs.find("void fbs_server::connect", start)
    if start < 0 or end < 0:
        fail("post-apply initialize_server isolation failed")
    init = fbs[start:end]

    for needle in (
        "// NATIVEBOOT2-B25 FBSSHAREDHEAP1:",
        'get_by_name_and_type<kernel::chunk>("FbsSharedChunk"',
        'get_by_name_and_type<kernel::chunk>("FbsLargeChunk"',
        "get_own_process()",
        'rename("FbsSharedChunk.NativeBoot")',
        'rename("FbsLargeChunk.NativeBoot")',
        "[NBOOT2][FBS_SHARED_HEAP_HANDOFF]",
        "[NBOOT2][FBS_SHARED_HEAP_READY]",
        "kernel::owner_type::kernel",
        "std::make_unique<epoc::chunk_allocator>(shared_chunk)",
        "std::make_unique<epoc::chunk_allocator>(large_chunk)",
    ):
        if needle not in init:
            fail(f"post-apply initialize_server gate missing: {needle}")

    handoff_pos = init.find("[NBOOT2][FBS_SHARED_HEAP_HANDOFF]")
    create_pos = init.find('"FbsSharedChunk",')
    if handoff_pos < 0 or create_pos < 0 or handoff_pos >= create_pos:
        fail("handoff marker must precede canonical FbsSharedChunk creation")

    if "shared_chunk = native_shared" in init or "large_chunk = native_large" in init:
        fail("B25 must not adopt native fbserv heap into HLE allocators")

    loader = loader_cpp.read_text(encoding="utf-8")
    if 'name_process == "fbserv"' in loader or 'name_process == "fbserv.exe"' in loader:
        fail("B25 unexpectedly special-cases fbserv startup")

    print("NATIVEBOOT2-B25 FBSSHAREDHEAP1 applied")
    print("root_cause=FBS_CANONICAL_GLOBAL_CHUNK_NAME_COLLISION")
    print("native_fbserv=PRESERVED")
    print("native_chunk_handles=PRESERVED")
    print("guest_owned_native_chunks=RENAMED_INTERNAL")
    print("hle_canonical_chunks=CREATED_AS_BEFORE")
    print("native_heap_adoption=DISABLED")
    print("vtable=TFontSpec=font_matcher=AppServer=UNCHANGED")
    print("B24_FBSVTABLEABI1=PRESERVED")
    print("B23_FBSFONTSPECV2ABI1=PRESERVED")
    print("B22_FBSDEFAULTTYPEFACE1=PRESERVED")
    print("B21_FBSFONTALIAS1=PRESERVED")
    print("B20_CENRESETALL1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")


if __name__ == "__main__":
    main()
