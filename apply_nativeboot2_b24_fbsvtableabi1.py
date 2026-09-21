#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B24 FBSVTABLEABI1 on top of B23.

B23 device evidence:
- RM-356 EPOC 9.4 now decodes 72-byte TFontSpec as font_spec_v2.
- AknCapServer still dies KERN-EXEC 3, PC=0x000000F0.
- r0 at the crash equals FbsSharedChunkBase + returned font address_offset.

B24 is intentionally diagnostic-only:
- add compile-time CBitmapFont layout-size guards;
- record ordinal-97 raw export and whether it lives in code/data;
- compare EKA2L1's current manual relocate(raw+8) against codeseg::lookup()+8;
- dump the actual vtable entries currently stored in the returned CBitmapFont;
- do not mutate vtable, font object, matcher, AppServer, or startup policy.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B24-FBSVTABLEABI1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b24_fbsvtableabi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    font_cpp = up / "src/emu/services/src/fbs/impls/font.cpp"
    font_h = up / "src/emu/services/include/services/fbs/font.h"
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (font_cpp, font_h, fbs_cpp, store_cpp, repo_cpp, sa_cpp, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")
    fbs = fbs_cpp.read_text(encoding="utf-8")
    store = store_cpp.read_text(encoding="utf-8")
    repo = repo_cpp.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # B23 and prior checkpoint gates.
    for needle in ("[NBOOT2][FBS_FONT_SPEC_ABI]", "[NBOOT2][FBS_FONT_RETURN]"):
        if needle not in fc:
            fail(f"B23 checkpoint missing: {needle}")
    for needle in ("[NBOOT2][FBS_DEFAULT_TYPEFACE]", "[NBOOT2][FBS_FONT_ALIAS]"):
        if needle not in fbs:
            fail(f"B22/B21 checkpoint missing: {needle}")
    if "system_default_typeface_name()" not in store:
        fail("B22 store checkpoint missing")
    if "[NBOOT2][CEN_RESET_ALL_DONE]" not in repo:
        fail("B20 checkpoint missing")
    if "[NBOOT2][SA_LANG_ABI]" not in sa:
        fail("B19 checkpoint missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("EMUHUB1 checkpoint missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # The two existing EKA2L1 layouts have useful exact sizes for interpreting
    # S60v5 vs Symbian^3 device evidence. This is compile-time only.
    v2_anchor = """    struct bitmapfont_v2 : public bitmapfont_base {
        font_spec_v2 spec_in_twips;
        alg_style algorithic_style;

        eka2l1::ptr<void> allocator;
        int fontbitmap_offset;

        // This was not used by Symbian's by default i think
        // Qt generally access this itself by hardcoding offset of this
        eka2l1::ptr<void> openfont;

        std::uint32_t reserved;
        std::uint32_t font_uid;
    };
"""
    v2_new = v2_anchor + """
    static_assert(sizeof(bitmapfont_v1) == 96);
    static_assert(sizeof(bitmapfont_v2) == 104);
"""
    if "static_assert(sizeof(bitmapfont_v2) == 104);" not in fh:
        fh = replace_once(fh, v2_anchor, v2_new, "bitmapfont ABI size guards")
    font_h.write_text(fh, encoding="utf-8")

    fc = font_cpp.read_text(encoding="utf-8")

    old_tail = """        ctx->write_data_to_descriptor_argument(index, result_info);
        ctx->complete(epoc::error_none);
    }

    void fbscli::get_nearest_font(service::ipc_context *ctx) {
"""
    new_tail = """        // NATIVEBOOT2-B24 FBSVTABLEABI1 -- diagnostic only.
        // Compare the current historical relocation path against codeseg::lookup(),
        // which additionally knows how to relocate data-section exports.
        kernel::process *font_user = ctx->msg->own_thr->owning_process();
        static constexpr std::size_t VTABLE_DUMP_SLOTS = 20;

        if (serv->fntstr_seg && font_user) {
            const address raw_export = serv->fntstr_seg->lookup_no_relocate(97);
            const address code_base = serv->fntstr_seg->get_code_base();
            const address data_base = serv->fntstr_seg->get_data_base();
            const std::uint32_t code_size = serv->fntstr_seg->get_code_size();
            const std::uint32_t data_size = serv->fntstr_seg->get_data_size();

            std::uint8_t *code_host = nullptr;
            std::uint8_t *data_host = nullptr;
            const address code_run = serv->fntstr_seg->get_code_run_addr(font_user, &code_host);
            const address data_run = serv->fntstr_seg->get_data_run_addr(font_user, &data_host);

            const address current_address_point_raw = serv->bmp_font_vtab.ptr_address();
            const address current_address_point_guest =
                serv->fntstr_seg->relocate(font_user, current_address_point_raw);
            const address canonical_export_guest = serv->fntstr_seg->lookup(font_user, 97);
            const address canonical_address_point_guest =
                canonical_export_guest ? canonical_export_guest + 2 * sizeof(std::uint32_t) : 0;

            const bool raw_in_code =
                raw_export >= code_base && raw_export < code_base + code_size;
            const bool raw_in_data =
                data_size && raw_export >= data_base && raw_export < data_base + data_size;

            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_VTABLE_EXPORT] ordinal=97 raw=0x{:X} code_base=0x{:X} code_size=0x{:X} data_base=0x{:X} data_size=0x{:X} raw_in_code={} raw_in_data={}",
                raw_export, code_base, code_size, data_base, data_size,
                raw_in_code, raw_in_data);

            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_VTABLE_RELOC] ordinal=97 code_run=0x{:X} data_run=0x{:X} address_point_raw=0x{:X} current=0x{:X} canonical_export=0x{:X} canonical=0x{:X} match={}",
                code_run, data_run, current_address_point_raw,
                current_address_point_guest, canonical_export_guest,
                canonical_address_point_guest,
                current_address_point_guest == canonical_address_point_guest);

            epoc::bitmapfont_base *base_font = reinterpret_cast<epoc::bitmapfont_base *>(
                serv->get_shared_chunk_base() + font->guest_font_offset);
            const address object_vtable = base_font->vtable.ptr_address();
            const address shared_base_guest = serv->shared_chunk->base(font_user).ptr_address();
            const address object_guest =
                shared_base_guest + static_cast<address>(result_info.address_offset);

            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_BITMAPFONT_ABI] func=0x{:X} guest=0x{:X} shared_base=0x{:X} address_offset=0x{:X} object_vtable=0x{:X} sizeof_v1={} sizeof_v2={} s60v5_expected=96 symbian3_expected=104",
                ctx->msg->function, object_guest, shared_base_guest,
                static_cast<std::uint32_t>(result_info.address_offset),
                object_vtable, sizeof(epoc::bitmapfont_v1), sizeof(epoc::bitmapfont_v2));

            const std::uint32_t *slots = nullptr;
            std::size_t available_slots = 0;
            const char *mapped_region = "none";

            if (code_host && object_vtable >= code_run &&
                object_vtable < code_run + code_size) {
                const std::size_t delta =
                    static_cast<std::size_t>(object_vtable - code_run);
                slots = reinterpret_cast<const std::uint32_t *>(code_host + delta);
                available_slots = (code_size - delta) / sizeof(std::uint32_t);
                mapped_region = "code";
            } else if (data_host && data_size && object_vtable >= data_run &&
                       object_vtable < data_run + data_size) {
                const std::size_t delta =
                    static_cast<std::size_t>(object_vtable - data_run);
                slots = reinterpret_cast<const std::uint32_t *>(data_host + delta);
                available_slots = (data_size - delta) / sizeof(std::uint32_t);
                mapped_region = "data";
            }

            if (slots) {
                const std::size_t dump_count =
                    available_slots < VTABLE_DUMP_SLOTS ? available_slots : VTABLE_DUMP_SLOTS;
                for (std::size_t slot = 0; slot < dump_count; ++slot) {
                    const std::uint32_t value = slots[slot];
                    const bool in_code =
                        value >= code_run && value < code_run + code_size;
                    const bool in_data =
                        data_size && value >= data_run && value < data_run + data_size;
                    const bool small = value < 0x10000;
                    LOG_WARN(SERVICE_FBS,
                        "[NBOOT2][FBS_VTABLE_SLOT] region={} slot={} value=0x{:X} small={} thumb={} in_code={} in_data={}",
                        mapped_region, slot, value, small,
                        (value & 1U) != 0, in_code, in_data);
                }
            } else {
                LOG_WARN(SERVICE_FBS,
                    "[NBOOT2][FBS_VTABLE_SLOT] region=unmapped slot=-1 value=0x{:X} small={} thumb={} in_code=false in_data=false",
                    object_vtable, object_vtable < 0x10000,
                    (object_vtable & 1U) != 0);
            }
        } else {
            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_VTABLE_RELOC] ordinal=97 unavailable fntstr_present={} process_present={}",
                static_cast<bool>(serv->fntstr_seg), font_user != nullptr);
        }

        ctx->write_data_to_descriptor_argument(index, result_info);
        ctx->complete(epoc::error_none);
    }

    void fbscli::get_nearest_font(service::ipc_context *ctx) {
"""
    if "[NBOOT2][FBS_VTABLE_RELOC]" not in fc:
        fc = replace_once(fc, old_tail, new_tail, "write_font_handle B24 diagnostics")
    font_cpp.write_text(fc, encoding="utf-8")

    # Post-apply boundedness and contract gates.
    fc = font_cpp.read_text(encoding="utf-8")
    fh = font_h.read_text(encoding="utf-8")
    start = fc.find("void fbscli::write_font_handle")
    end = fc.find("void fbscli::get_nearest_font", start)
    if start < 0 or end < 0:
        fail("post-apply write_font_handle isolation failed")
    ret = fc[start:end]

    for needle in (
        "[NBOOT2][FBS_BITMAPFONT_ABI]",
        "[NBOOT2][FBS_VTABLE_EXPORT]",
        "[NBOOT2][FBS_VTABLE_RELOC]",
        "[NBOOT2][FBS_VTABLE_SLOT]",
        "lookup_no_relocate(97)",
        "lookup(font_user, 97)",
        "VTABLE_DUMP_SLOTS",
    ):
        if needle not in ret:
            fail(f"post-apply diagnostic missing: {needle}")

    if "bmpfont->vtable =" in ret or "font->guest_font_offset =" in ret:
        fail("B24 diagnostic unexpectedly mutates returned font state")

    for needle in (
        "static_assert(sizeof(bitmapfont_v1) == 96);",
        "static_assert(sizeof(bitmapfont_v2) == 104);",
    ):
        if needle not in fh:
            fail(f"post-apply ABI guard missing: {needle}")

    print("NATIVEBOOT2-B24 FBSVTABLEABI1 applied")
    print("behavior_change=NONE_DIAGNOSTIC_ONLY")
    print("ordinal97=RAW+CANONICAL_RELOCATION_COMPARE")
    print("vtable_slots=20")
    print("bitmapfont_sizes=96,104")
    print("B23_FBSFONTSPECV2ABI1=PRESERVED")
    print("B22_FBSDEFAULTTYPEFACE1=PRESERVED")
    print("B21_FBSFONTALIAS1=PRESERVED")
    print("B20_CENRESETALL1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
