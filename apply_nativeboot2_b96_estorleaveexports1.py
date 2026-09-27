#!/usr/bin/env python3
"""Resolve nearby exports and instructions for CompatBoot Menu3 Leave(-5)."""
from __future__ import annotations

import sys
from pathlib import Path


MARK = "NATIVEBOOT2-B96-ESTORLEAVEEXPORTS1"


def fail(message: str) -> None:
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_menu3_leave5_exports(source: str) -> str:
    marker = "[COMPATBOOT][MENU3_LEAVE5_EXPORT]"
    if marker in source:
        return source

    anchor = r'''                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_STACK] index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()),
                        base, candidate - base);
'''
    diagnostic = r'''                    // B96 is a read-only extension of the existing Menu3
                    // Leave(-5) stack trace. Resolve nearby E32 exports and a
                    // bounded instruction window for each guest code pointer.
                    const auto compat_leave_exports = seg->get_export_table(compat_leave_pr);
                    std::uint32_t nearest_export_ordinal = 0;
                    std::uint32_t nearest_export_address = 0;
                    std::uint32_t nearest_export_delta = 0xFFFFFFFFU;
                    const std::uint32_t code_end = base + seg->get_code_size();

                    for (std::size_t export_index = 0;
                         export_index < compat_leave_exports.size(); ++export_index) {
                        const std::uint32_t export_raw = compat_leave_exports[export_index];
                        const std::uint32_t export_address = export_raw & ~1U;
                        if (export_address < base || export_address >= code_end
                            || export_address > candidate) {
                            continue;
                        }

                        const std::uint32_t export_delta = candidate - export_address;
                        if (export_delta < nearest_export_delta) {
                            nearest_export_delta = export_delta;
                            nearest_export_address = export_raw;
                            nearest_export_ordinal =
                                static_cast<std::uint32_t>(export_index + 1);
                        }
                    }

                    LOG_WARN(KERNEL,
                        "[COMPATBOOT][MENU3_LEAVE5_EXPORT] stack_index={} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X} thumb={} nearest_export_ordinal={} nearest_export=0x{:08X} nearest_export_delta=0x{:08X} behavior=OBSERVE_ONLY",
                        i, value, common::ucs2_to_utf8(seg->get_full_path()),
                        base, candidate - base, (value & 1U) ? 1 : 0,
                        nearest_export_ordinal, nearest_export_address,
                        nearest_export_delta);

                    for (std::int32_t relative_halfword = -8;
                         relative_halfword <= 4; ++relative_halfword) {
                        const std::int64_t signed_code_address =
                            static_cast<std::int64_t>(candidate)
                            + static_cast<std::int64_t>(relative_halfword) * 2;
                        if (signed_code_address < 0
                            || signed_code_address > 0xFFFFFFFFLL) {
                            continue;
                        }

                        const std::uint32_t code_address =
                            static_cast<std::uint32_t>(signed_code_address);
                        const std::uint16_t *code16 =
                            eka2l1::ptr<std::uint16_t>(code_address).get(compat_leave_pr);
                        if (!code16) {
                            LOG_WARN(KERNEL,
                                "[COMPATBOOT][MENU3_LEAVE5_CODE16] stack_index={} relative_halfword={} address=0x{:08X} mapped=0 behavior=OBSERVE_ONLY",
                                i, relative_halfword, code_address);
                            continue;
                        }

                        LOG_WARN(KERNEL,
                            "[COMPATBOOT][MENU3_LEAVE5_CODE16] stack_index={} relative_halfword={} address=0x{:08X} code16=0x{:04X} behavior=OBSERVE_ONLY",
                            i, relative_halfword, code_address, *code16);
                    }
'''
    return replace_once(source, anchor, anchor + diagnostic,
                        "B96 Menu3 Leave stack export resolver")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b96_estorleaveexports1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    svc = upstream / "src/emu/kernel/src/svc.cpp"
    if not svc.is_file():
        fail(f"missing baseline file: {svc}")

    source = svc.read_text(encoding="utf-8")
    patched = patch_menu3_leave5_exports(source)
    if patched != source:
        svc.write_text(patched, encoding="utf-8")
    print(f"{MARK}: APPLIED")


if __name__ == "__main__":
    main()
