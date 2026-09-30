#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B24 FBSVTABLEABI1.

B23 RM-356 evidence:
- 72-byte TFontSpec now decodes as v2 correctly.
- AknCapServer still crashes KERN-EXEC 3 with PC=0x000000F0.
- At crash r0 equals FbsSharedChunkBase + returned address_offset exactly.

B24 is diagnostic-only. It must not change the CBitmapFont pointer, vtable,
font matcher, AppServer path, or startup policy. It records enough evidence
to compare EKA2L1's current manual ordinal-97 relocation with codeseg::lookup(),
which already handles code-vs-data exports, and dumps the current vtable slots.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B24-FBSVTABLEABI1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b24_fbsvtableabi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    font_cpp = up / "src/emu/services/src/fbs/impls/font.cpp"
    font_h = up / "src/emu/services/include/services/fbs/font.h"
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (font_cpp, font_h, fbs_cpp, store_cpp, repo_cpp, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")
    fbs = fbs_cpp.read_text(encoding="utf-8")
    store = store_cpp.read_text(encoding="utf-8")
    repo = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # Exact object-size facts are needed to interpret the device log.
    need(fh, "static_assert(sizeof(bitmapfont_v1) == 96);", "font.h")
    need(fh, "static_assert(sizeof(bitmapfont_v2) == 104);", "font.h")

    start = fc.find("void fbscli::write_font_handle")
    if start < 0:
        fail("write_font_handle missing")
    end = fc.find("void fbscli::get_nearest_font", start)
    if end < 0:
        fail("cannot isolate write_font_handle")
    ret = fc[start:end]

    # Compare current manual relocation against codeseg's canonical lookup path.
    for needle in (
        "[NBOOT2][FBS_BITMAPFONT_ABI]",
        "[NBOOT2][FBS_VTABLE_EXPORT]",
        "[NBOOT2][FBS_VTABLE_RELOC]",
        "[NBOOT2][FBS_VTABLE_SLOT]",
        "lookup_no_relocate(97)",
        "lookup(font_user, 97)",
        "get_code_base()",
        "get_data_base()",
        "get_code_run_addr(font_user",
        "get_data_run_addr(font_user",
        "serv->bmp_font_vtab.ptr_address()",
        "serv->fntstr_seg->relocate(font_user",
        "VTABLE_DUMP_SLOTS",
        "value < 0x10000",
    ):
        need(ret, needle, "write_font_handle")

    # Diagnostic only: object still exposes the same vtable already assigned by
    # fill_bitmap_information. B24 must not overwrite it.
    if "bmpfont->vtable =" in ret:
        fail("B24 write_font_handle must not mutate the guest vtable")
    if "font->guest_font_offset =" in ret:
        fail("B24 write_font_handle must not mutate returned font offset")

    # B23 and earlier checkpoints stay intact.
    for needle in (
        "[NBOOT2][FBS_FONT_SPEC_ABI]",
        "[NBOOT2][FBS_FONT_RETURN]",
    ):
        need(fc, needle, "font.cpp")
    for needle in (
        "[NBOOT2][FBS_DEFAULT_TYPEFACE]",
        "[NBOOT2][FBS_FONT_ALIAS]",
    ):
        need(fbs, needle, "fbs.cpp")
    need(store, "system_default_typeface_name()", "font_store.cpp")
    need(repo, "[NBOOT2][CEN_RESET_ALL_DONE]", "repo.cpp")
    need(sa, "[NBOOT2][SA_LANG_ABI]", "sa.cpp")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
