#!/usr/bin/env python3
"""Source contract for NATIVEBOOT2 B23 FBSFONTSPECV2ABI1.

B22 device evidence (RM-356 / Symbian 9.4):
- AknCapServer now rendezvous-completes after FBS 0x1E + 0x2D.
- Its next font request is opcode 0x23
  EFbsMessGetNearestFontToDesignHeightInPixels.
- Slot 0 carries packed=72 bytes, while EKA2L1 decodes font_spec_v1=64.
- AknCapServer then crashes KERN-EXEC 3 with PC=0x000000F0.

Primary Symbian source defines TFontSpec as:
  TTypeface (56) + TInt iHeight (4) + TFontStyle (12) = 72 bytes
on 32-bit Symbian 9.4. TFontStyle contains flags plus two reserved pointers.
EKA2L1 already models this layout as font_spec_v2.

B23 scope:
- decode 72-byte font specs as font_spec_v2, preserving a 64-byte v1 path;
- reject any other slot-0 size instead of silently clamping;
- zero v2 reserved fields in the server-created bitmap-font spec;
- log input ABI and returned font object metadata;
- preserve B22/B21/B20 and NOJAVA/MANIC3.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B23-FBSFONTSPECV2ABI1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b23_fbsfontspecv2abi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    font_cpp = up / "src/emu/services/src/fbs/impls/font.cpp"
    font_h = up / "src/emu/services/include/services/fbs/font.h"
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    bridge = up / "src/emu/ios/src/emu_bridge.mm"
    thread_cpp = up / "src/emu/ios/src/thread.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (font_cpp, font_h, fbs_cpp, store_cpp, bridge, thread_cpp, repo_cpp, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")
    fbs = fbs_cpp.read_text(encoding="utf-8")
    store = store_cpp.read_text(encoding="utf-8")
    br = bridge.read_text(encoding="utf-8")
    th = thread_cpp.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    start = fc.find("void fbscli::get_nearest_font(service::ipc_context *ctx)")
    if start < 0:
        fail("get_nearest_font missing")
    end = fc.find("void fbscli::get_font_by_uid", start)
    if end < 0:
        fail("cannot isolate get_nearest_font")
    nearest = fc[start:end]

    # Root cause: RM-356 is EPOC 9.4 but sends the 72-byte TFontSpec.
    # ABI selection therefore follows the descriptor size, not epoc95+.
    for needle in (
        "ctx->get_argument_data_size(0)",
        "if (spec_size == sizeof(epoc::font_spec_v2))",
        "else if (spec_size == sizeof(epoc::font_spec_v1))",
        "get_argument_data_from_descriptor<epoc::font_spec_v2>(0)",
        "get_argument_data_from_descriptor<epoc::font_spec_v1>(0)",
        "[NBOOT2][FBS_FONT_SPEC_ABI]",
        'decode=v2',
        'decode=v1',
        "ctx->complete(epoc::error_argument)",
    ):
        need(nearest, needle, "get_nearest_font")

    if "(epoc_version >= epocver::epoc95) && (spec_size" in nearest:
        fail("72-byte v2 decode is still incorrectly gated on epoc95")

    if nearest.count("get_argument_data_from_descriptor<epoc::font_spec_v1>(0)") != 1:
        fail("v1 decode must exist exactly once as the explicit 64-byte compatibility branch")
    if nearest.count("get_argument_data_from_descriptor<epoc::font_spec_v2>(0)") != 1:
        fail("v2 decode must exist exactly once as the explicit 72-byte RM-356 branch")

    # ABI sizes are explicit and compile-time guarded.
    need(fh, "static_assert(sizeof(font_spec_v1) == 64);", "font.h")
    need(fh, "static_assert(sizeof(font_spec_v2) == 72);", "font.h")

    # Return marker captures the data consumed immediately before the guest crash.
    ret_start = fc.find("void fbscli::write_font_handle")
    if ret_start < 0:
        fail("write_font_handle missing")
    ret_end = fc.find("void fbscli::get_nearest_font", ret_start)
    if ret_end < 0:
        fail("cannot isolate write_font_handle")
    ret = fc[ret_start:ret_end]
    for needle in (
        "[NBOOT2][FBS_FONT_RETURN]",
        "result_info.handle",
        "result_info.address_offset",
        "result_info.server_handle",
        "bmpfont->vtable.ptr_address()",
        "bmpfont->openfont.ptr_address()",
    ):
        need(ret, needle, "write_font_handle")

    # Previous checkpoints stay intact.
    need(fbs, "[NBOOT2][FBS_DEFAULT_TYPEFACE]", "fbs.cpp")
    need(fbs, "[NBOOT2][FBS_FONT_ALIAS]", "fbs.cpp")
    need(store, "system_default_typeface_name()", "font_store.cpp")
    need(rp, "[NBOOT2][CEN_RESET_ALL_DONE]", "repo.cpp")
    need(sa, "[NBOOT2][SA_LANG_ABI]", "sa.cpp")

    for phase in ("os_join_done", "graphics_join_done"):
        need(th, f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}", "thread.cpp")
    for phase in ("state_reset_done", "normal_restart_done"):
        need(br, f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}", "emu_bridge.mm")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
