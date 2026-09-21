#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B23 FBSFONTSPECV2ABI1 on top of B22.

B22 RM-356 device evidence:
- AknCapServer rendezvous now completes.
- FBS opcode 0x23 receives slot0 packed=72, but the active EPOC 9.4 path
  decodes font_spec_v1=64 and clamps the last 8 bytes.
- AknCapServer then crashes KERN-EXEC 3 with PC=0x000000F0.

Root cause in the cached baseline:
- font_spec_v2 support already exists, but is incorrectly gated by
  epoc_version >= epoc95.
- Nokia 5800 is EPOC 9.4 and nevertheless uses the 72-byte TFontSpec ABI.

B23 is deliberately bounded:
- choose font_spec_v2 when slot0 is exactly 72 bytes;
- keep font_spec_v1 when slot0 is exactly 64 bytes;
- reject any other package size instead of silently clamping;
- add ABI and returned-font diagnostics;
- do not change font matching, vtable relocation, AppServer, or startup policy.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B23-FBSFONTSPECV2ABI1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b23_fbsfontspecv2abi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    font_cpp = up / "src/emu/services/src/fbs/impls/font.cpp"
    font_h = up / "src/emu/services/include/services/fbs/font.h"
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    bridge = up / "src/emu/ios/src/emu_bridge.mm"
    thread_cpp = up / "src/emu/ios/src/thread.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (font_cpp, font_h, fbs_cpp, store_cpp, bridge, thread_cpp,
              repo_cpp, sa_cpp, state, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")
    fbs = fbs_cpp.read_text(encoding="utf-8")
    store = store_cpp.read_text(encoding="utf-8")
    br = bridge.read_text(encoding="utf-8")
    th = thread_cpp.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # B22/B21/B20 checkpoint gates.
    for needle in ("[NBOOT2][FBS_DEFAULT_TYPEFACE]", "[NBOOT2][FBS_FONT_ALIAS]"):
        if needle not in fbs:
            fail(f"FBS checkpoint missing: {needle}")
    if "system_default_typeface_name()" not in store:
        fail("B22 default-typeface store checkpoint missing")
    if "[NBOOT2][CEN_RESET_ALL_DONE]" not in rp:
        fail("B20 CenRep checkpoint missing")
    if "[NBOOT2][SA_LANG_ABI]" not in sa:
        fail("B19 SA language checkpoint missing")
    if "[NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done" not in br:
        fail("B22 bridge-exit checkpoint missing")
    if "[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_done" not in th:
        fail("B22 thread-exit checkpoint missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("ESTART checkpoint missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("EMUHUB1 checkpoint missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # Compile-time ABI guards. EKA2L1's ptr<> is a 32-bit guest pointer, so
    # these sizes model the real Symbian packages independent of host ABI.
    spec_anchor = """    struct font_spec_v2 : public font_spec_base {
        font_style_v2 style;
    };
"""
    spec_new = spec_anchor + """
    static_assert(sizeof(font_spec_v1) == 64);
    static_assert(sizeof(font_spec_v2) == 72);
"""
    if "static_assert(sizeof(font_spec_v2) == 72);" not in fh:
        fh = replace_once(fh, spec_anchor, spec_new, "font-spec ABI static asserts")
    font_h.write_text(fh, encoding="utf-8")

    fc = font_cpp.read_text(encoding="utf-8")

    old_decode = """        epoc::font_spec_v1 spec{};
        const std::size_t spec_size = ctx->get_argument_data_size(0);
        const epocver epoc_version = server<fbs_server>()->get_system()->get_symbian_version_use();

        // Symbian^3/Anna (epoc95) sends font_spec_v2: the same semantic fields as
        // v1 plus two reserved pointer slots in font_style_v2. V9 IPC diagnostics
        // observed 72-byte packets being truncated to the 64-byte v1 ABI.
        if ((epoc_version >= epocver::epoc95) && (spec_size >= sizeof(epoc::font_spec_v2))) {
            std::optional<epoc::font_spec_v2> spec_v2 =
                ctx->get_argument_data_from_descriptor<epoc::font_spec_v2>(0);
            if (!spec_v2) {
                ctx->complete(epoc::error_argument);
                return;
            }

            spec.tf = spec_v2->tf;
            spec.height = spec_v2->height;
            spec.style.flags = spec_v2->style.flags;

            if (epoc_version == epocver::epoc95) {
                LOG_INFO(SERVICE_FBS,
                    "V11 FBS95 FONT: layout=v2 spec_size={} height={} style=0x{:X} reserved1=0x{:X} reserved2=0x{:X}",
                    spec_size, spec.height, spec.style.flags,
                    spec_v2->style.reserved1.ptr_address(), spec_v2->style.reserved2.ptr_address());
            }
        } else {
            std::optional<epoc::font_spec_v1> spec_v1 =
                ctx->get_argument_data_from_descriptor<epoc::font_spec_v1>(0);
            if (!spec_v1) {
                ctx->complete(epoc::error_argument);
                return;
            }
            spec = spec_v1.value();

            if ((epoc_version >= epocver::epoc95) && (spec_size < sizeof(epoc::font_spec_v2))) {
                LOG_WARN(SERVICE_FBS,
                    "V11 FBS95 FONT LEGACY64: spec_size={} using font_spec_v1 fallback",
                    spec_size);
            }
        }
"""

    new_decode = """        epoc::font_spec_v1 spec{};
        const std::size_t spec_size = ctx->get_argument_data_size(0);
        const epocver epoc_version = server<fbs_server>()->get_system()->get_symbian_version_use();

        // NATIVEBOOT2-B23 FBSFONTSPECV2ABI1:
        // RM-356 is Symbian 9.4 but sends the 72-byte TFontSpec package.
        // Select the ABI by the descriptor that actually crossed IPC, not by
        // a guessed OS-version boundary.
        if (spec_size == sizeof(epoc::font_spec_v2)) {
            std::optional<epoc::font_spec_v2> spec_v2 =
                ctx->get_argument_data_from_descriptor<epoc::font_spec_v2>(0);
            if (!spec_v2) {
                ctx->complete(epoc::error_argument);
                return;
            }

            spec.tf = spec_v2->tf;
            spec.height = spec_v2->height;
            spec.style.flags = spec_v2->style.flags;

            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_SPEC_ABI] func=0x{:X} epoc={} packed={} decode=v2 height={} style_flags=0x{:X} reserved1=0x{:X} reserved2=0x{:X}",
                ctx->msg->function, static_cast<int>(epoc_version), spec_size,
                spec.height, spec.style.flags,
                spec_v2->style.reserved1.ptr_address(), spec_v2->style.reserved2.ptr_address());
        } else if (spec_size == sizeof(epoc::font_spec_v1)) {
            std::optional<epoc::font_spec_v1> spec_v1 =
                ctx->get_argument_data_from_descriptor<epoc::font_spec_v1>(0);
            if (!spec_v1) {
                ctx->complete(epoc::error_argument);
                return;
            }

            spec = spec_v1.value();

            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_SPEC_ABI] func=0x{:X} epoc={} packed={} decode=v1 height={} style_flags=0x{:X}",
                ctx->msg->function, static_cast<int>(epoc_version), spec_size,
                spec.height, spec.style.flags);
        } else {
            LOG_ERROR(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_SPEC_ABI] func=0x{:X} epoc={} packed={} decode=invalid expected_v1={} expected_v2={} completion={}",
                ctx->msg->function, static_cast<int>(epoc_version), spec_size,
                sizeof(epoc::font_spec_v1), sizeof(epoc::font_spec_v2),
                epoc::error_argument);
            ctx->complete(epoc::error_argument);
            return;
        }
"""
    if "[NBOOT2][FBS_FONT_SPEC_ABI]" not in fc:
        fc = replace_once(fc, old_decode, new_decode, "RM-356 font-spec ABI decode")

    # Diagnostic only: capture exactly what CFbsTypefaceStore will consume
    # after the server returns the font. No returned value or object is changed.
    old_return = """    void fbscli::write_font_handle(service::ipc_context *ctx, fbsfont *font, const int index) {
        font_info result_info;

        result_info.handle = obj_table_.add(font);
        result_info.address_offset = font->guest_font_offset;
        result_info.server_handle = static_cast<std::int32_t>(font->id);

        ctx->write_data_to_descriptor_argument(index, result_info);
        ctx->complete(epoc::error_none);
    }
"""
    new_return = """    void fbscli::write_font_handle(service::ipc_context *ctx, fbsfont *font, const int index) {
        font_info result_info;

        result_info.handle = obj_table_.add(font);
        result_info.address_offset = font->guest_font_offset;
        result_info.server_handle = static_cast<std::int32_t>(font->id);

        fbs_server *serv = server<fbs_server>();
        if (!serv->kern->is_eka1()) {
            epoc::bitmapfont_v2 *bmpfont = reinterpret_cast<epoc::bitmapfont_v2 *>(
                serv->get_shared_chunk_base() + font->guest_font_offset);
            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_RETURN] func=0x{:X} layout=v2 handle={} address_offset=0x{:X} server_handle=0x{:X} vtable=0x{:X} openfont=0x{:X}",
                ctx->msg->function, result_info.handle,
                static_cast<std::uint32_t>(result_info.address_offset),
                static_cast<std::uint32_t>(result_info.server_handle),
                bmpfont->vtable.ptr_address(), bmpfont->openfont.ptr_address());
        } else {
            epoc::bitmapfont_v1 *bmpfont = reinterpret_cast<epoc::bitmapfont_v1 *>(
                serv->get_shared_chunk_base() + font->guest_font_offset);
            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_RETURN] func=0x{:X} layout=v1 handle={} address_offset=0x{:X} server_handle=0x{:X} vtable=0x{:X} openfont=0x{:X}",
                ctx->msg->function, result_info.handle,
                static_cast<std::uint32_t>(result_info.address_offset),
                static_cast<std::uint32_t>(result_info.server_handle),
                bmpfont->vtable.ptr_address(), bmpfont->openfont.ptr_address());
        }

        ctx->write_data_to_descriptor_argument(index, result_info);
        ctx->complete(epoc::error_none);
    }
"""
    if "[NBOOT2][FBS_FONT_RETURN]" not in fc:
        fc = replace_once(fc, old_return, new_return, "font return diagnostics")

    font_cpp.write_text(fc, encoding="utf-8")

    # Post-apply gates.
    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")

    nearest_start = fc.find("void fbscli::get_nearest_font(service::ipc_context *ctx)")
    nearest_end = fc.find("void fbscli::get_font_by_uid", nearest_start)
    if nearest_start < 0 or nearest_end < 0:
        fail("post-apply get_nearest_font isolation failed")
    nearest = fc[nearest_start:nearest_end]

    for needle in (
        "if (spec_size == sizeof(epoc::font_spec_v2))",
        "else if (spec_size == sizeof(epoc::font_spec_v1))",
        "get_argument_data_from_descriptor<epoc::font_spec_v2>(0)",
        "get_argument_data_from_descriptor<epoc::font_spec_v1>(0)",
        "[NBOOT2][FBS_FONT_SPEC_ABI]",
        "decode=v2",
        "decode=v1",
    ):
        if needle not in nearest:
            fail(f"post-apply nearest-font gate missing: {needle}")

    if "(epoc_version >= epocver::epoc95) && (spec_size" in nearest:
        fail("post-apply v2 decode is still epoc95-gated")

    for needle in (
        "static_assert(sizeof(font_spec_v1) == 64);",
        "static_assert(sizeof(font_spec_v2) == 72);",
    ):
        if needle not in fh:
            fail(f"post-apply font.h ABI gate missing: {needle}")

    if "[NBOOT2][FBS_FONT_RETURN]" not in fc:
        fail("font-return diagnostic missing")

    print("NATIVEBOOT2-B23 FBSFONTSPECV2ABI1 applied")
    print("root_cause=RM356_EPOC94_72BYTE_TFONTSPEC_MISROUTED_TO_V1")
    print("abi_select=DESCRIPTOR_SIZE")
    print("font_spec_v1=64")
    print("font_spec_v2=72")
    print("unknown_size=KErrArgument")
    print("font_matcher=UNCHANGED")
    print("vtable_relocation=UNCHANGED")
    print("font_return=DIAGNOSTIC_ONLY")
    print("B22_FBSDEFAULTTYPEFACE1=PRESERVED")
    print("B21_FBSFONTALIAS1=PRESERVED")
    print("B20_CENRESETALL1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
