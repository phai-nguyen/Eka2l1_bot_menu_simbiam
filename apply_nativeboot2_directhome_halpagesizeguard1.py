#!/usr/bin/env python3
"""Reject unmapped HAL page-size destinations and record the guest caller once."""

from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-HAL-PAGESIZE-GUARD1"
PAGE_SIZE_BEFORE = """        int page_size(int *a1, int *a2, const std::uint16_t device_num) {
            *a1 = static_cast<int>(sys->get_memory_system()->get_page_size());
"""
PAGE_SIZE_AFTER = """        int page_size(int *a1, int *a2, const std::uint16_t device_num) {
            if (!a1) {
                return epoc::error_argument;
            }
            *a1 = static_cast<int>(sys->get_memory_system()->get_page_size());
"""
BRIDGE_BEFORE = """        int *arg1 = a1.get(pr);
        int *arg2 = a2.get(pr);

        return do_hal(kern->get_system(), cage, func, arg1, arg2);
"""
BRIDGE_AFTER = """        int *arg1 = a1.get(pr);
        int *arg2 = a2.get(pr);

        // Keep the HAL contract: an unmapped destination is an argument error,
        // not a host write to address zero. Only the first occurrence is logged
        // because a failed guest startup may retry this call indefinitely.
        if (cage == 0 && func == 7 && !arg1) {
            static std::atomic<bool> reported_bad_page_size_destination{false};
            if (!reported_bad_page_size_destination.exchange(true)) {
                LOG_WARN(KERNEL, "[NBOOT2][HAL_PAGE_SIZE_INVALID_DEST] process={} thread={} guest_a1=0x{:08X} guest_a2=0x{:08X} pc=0x{:08X} result=-6",
                    pr ? pr->name() : "<none>", kern->crr_thread() ? kern->crr_thread()->name() : "<none>",
                    a1.ptr_address(), a2.ptr_address(), kern->get_cpu()->get_reg(15));
            }
            return epoc::error_argument;
        }

        return do_hal(kern->get_system(), cage, func, arg1, arg2);
"""


def patch_once(source: str, before: str, after: str, path: str) -> str:
    if source.count(after) == 1:
        return source
    if source.count(before) != 1:
        raise SystemExit(f"{MARK}: expected exactly one vulnerable block in {path}, found {source.count(before)}")
    return source.replace(before, after, 1)


def apply(root: Path) -> bool:
    paths = (
        (root / "src/emu/system/src/hal.cpp", PAGE_SIZE_BEFORE, PAGE_SIZE_AFTER),
        (root / "src/emu/kernel/src/svc.cpp", BRIDGE_BEFORE, BRIDGE_AFTER),
    )
    replacements = []
    for path, before, after in paths:
        original = path.read_text(encoding="utf-8")
        patched = patch_once(original, before, after, str(path))
        if path.name == "svc.cpp" and "#include <atomic>\n" not in patched:
            anchor = "#include <common/uid.h>\n"
            if patched.count(anchor) != 1:
                raise SystemExit(f"{MARK}: cannot locate include insertion point")
            patched = patched.replace(anchor, "#include <atomic>\n\n" + anchor, 1)
        replacements.append((path, original, patched))
    for path, original, patched in replacements:
        if patched != original:
            path.write_text(patched, encoding="utf-8")
    return any(original != patched for _, original, patched in replacements)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"{MARK}: usage: {sys.argv[0]} <upstream-root>")
    print(f"{MARK}: {'applied' if apply(Path(sys.argv[1])) else 'already present'}")
