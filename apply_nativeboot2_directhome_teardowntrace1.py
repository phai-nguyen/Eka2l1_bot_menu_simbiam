#!/usr/bin/env python3
"""Apply read-only, DirectHome-scoped kernel teardown tracing."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TEARDOWNTRACE1"
HEADER = '''#pragma once
#include <atomic>
#include <cstdint>

namespace eka2l1::kernel {
    inline std::uint64_t next_directhome_teardown_trace_seq() {
        static std::atomic<std::uint64_t> sequence{ 0 };
        return sequence.fetch_add(1, std::memory_order_relaxed) + 1;
    }
}
'''


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_function(source, signature, transformer, label):
    if source.count(signature) != 1:
        fail(f"{label}: expected one function signature, found {source.count(signature)}")
    start = source.index(signature)
    open_brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = open_brace
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                return source[:start] + transformer(source[start:end]) + source[end:]
        index += 1
    fail(f"{label}: unterminated function body")


def ensure_include(source, include, label):
    if include in source:
        return source
    anchor = "#include <kernel/kernel.h>\n"
    if source.count(anchor) != 1:
        include_lines = [line for line in source.splitlines(keepends=True) if line.startswith("#include ")]
        if not include_lines:
            fail(f"{label}: missing include insertion point")
        anchor = include_lines[0]
    return source.replace(anchor, anchor + include + "\n", 1)


def trace_scope():
    return '''
        const auto *nboot2_directhome_config = kern ? kern->get_config() : nullptr;
        const bool nboot2_directhome_trace = nboot2_directhome_config
            && nboot2_directhome_config->native_phone_boot
            && nboot2_directhome_config->compat_menu_probe_mode
            && nboot2_directhome_config->compat_target_kind == 2;
'''


def patch_process_kill(source):
    marker = "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=process_kill_entry"
    if marker in source:
        if source.count(marker) != 1 or source.count("phase=process_kill_decision") != 2:
            fail("partial process::kill trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "process::kill")
    source = ensure_include(source, "#include <kernel/directhome_teardown_trace.h>", "process::kill")
    signature = "void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {"

    def patch_body(body):
        scope_anchor = signature + "\n"
        if body.count(scope_anchor) != 1:
            fail("process::kill: missing body insertion point")
        body = body.replace(scope_anchor, scope_anchor + trace_scope(), 1)
        old_guard = '''        if (exit_type != entity_exit_type::pending) {
            return;
        }
'''
        new_guard = '''        const auto nboot2_directhome_uid_tuple = get_uid_type();
        const auto nboot2_directhome_uid3 = static_cast<std::uint32_t>(std::get<2>(nboot2_directhome_uid_tuple));
        if (nboot2_directhome_trace) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=process_kill_entry seq={} process_ptr={} uid3=0x{:08X} exit_state={} requested_exit_type={} reason={}",
                next_directhome_teardown_trace_seq(), static_cast<const void *>(this), nboot2_directhome_uid3,
                static_cast<int>(exit_type), static_cast<int>(ext), reason);
        }
        if (exit_type != entity_exit_type::pending) {
            if (nboot2_directhome_trace) {
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=process_kill_decision decision=already_exiting seq={} process_ptr={} uid3=0x{:08X} exit_state={} reason={}",
                    next_directhome_teardown_trace_seq(), static_cast<const void *>(this), nboot2_directhome_uid3,
                    static_cast<int>(exit_type), reason);
            }
            return;
        }
        if (nboot2_directhome_trace) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=process_kill_decision decision=accepted seq={} process_ptr={} uid3=0x{:08X} exit_state={} requested_exit_type={} reason={}",
                next_directhome_teardown_trace_seq(), static_cast<const void *>(this), nboot2_directhome_uid3,
                static_cast<int>(exit_type), static_cast<int>(ext), reason);
        }
'''
        return replace_once(body, old_guard, new_guard, "process::kill guard")

    return patch_function(source, signature, patch_body, "process::kill")


def patch_kernel_destroy(source):
    marker = "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=kernel_destroy"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial kernel_system::destroy trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "kernel_system::destroy")
    source = ensure_include(source, "#include <kernel/directhome_teardown_trace.h>", "kernel_system::destroy")
    signature = "bool kernel_system::destroy(kernel_obj_ptr obj) {"

    def patch_body(body):
        anchor = '''        if (!obj || wiping_) {
            return true;
        }

        switch (obj->get_object_type()) {
'''
        insert = '''        if (!obj || wiping_) {
            return true;
        }

        const auto *nboot2_directhome_config = get_config();
        const bool nboot2_directhome_trace = nboot2_directhome_config
            && nboot2_directhome_config->native_phone_boot
            && nboot2_directhome_config->compat_menu_probe_mode
            && nboot2_directhome_config->compat_target_kind == 2;
        if (nboot2_directhome_trace) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=kernel_destroy seq={} object_ptr={} object_type={}",
                kernel::next_directhome_teardown_trace_seq(), static_cast<const void *>(obj),
                static_cast<int>(obj->get_object_type()));
        }

        switch (obj->get_object_type()) {
'''
        return replace_once(body, anchor, insert, "kernel_system::destroy entry")

    return patch_function(source, signature, patch_body, "kernel_system::destroy")


def patch_property_reference_destructor(source):
    marker = "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=property_reference_destructor"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial property_reference destructor trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "property_reference destructor")
    source = ensure_include(source, "#include <kernel/directhome_teardown_trace.h>", "property_reference destructor")
    signature = "property_reference::~property_reference() {"

    def patch_body(body):
        anchor = "property_reference::~property_reference() {\n            cancel();\n        }"
        replacement = '''        property_reference::~property_reference() {
            auto *nboot2_directhome_kernel = get_kernel_object_owner();
            const auto *nboot2_directhome_config = nboot2_directhome_kernel
                ? nboot2_directhome_kernel->get_config() : nullptr;
            const bool nboot2_directhome_trace = nboot2_directhome_config
                && nboot2_directhome_config->native_phone_boot
                && nboot2_directhome_config->compat_menu_probe_mode
                && nboot2_directhome_config->compat_target_kind == 2;
            if (nboot2_directhome_trace) {
                const auto nboot2_directhome_guest_status = static_cast<std::uint32_t>(nof_.sts.ptr_address());
                const bool nboot2_directhome_requester_known = nboot2_directhome_guest_status != 0;
                const void *nboot2_directhome_requester = nboot2_directhome_requester_known
                    ? static_cast<const void *>(nof_.requester) : nullptr;
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][DIRECTHOME_TEARDOWN] phase=property_reference_destructor seq={} object_ptr={} property_ptr={} requester_ptr={} requester_known={} guest_status=0x{:08X}",
                    kernel::next_directhome_teardown_trace_seq(), static_cast<const void *>(this),
                    static_cast<const void *>(prop_), nboot2_directhome_requester,
                    nboot2_directhome_requester_known ? 1 : 0, nboot2_directhome_guest_status);
            }
            cancel();
        }'''
        return replace_once(body, anchor, replacement, "property_reference destructor")

    return patch_function(source, signature, patch_body, "property_reference destructor")


def apply(upstream: Path) -> None:
    upstream = Path(upstream).resolve()
    process_path = upstream / "src/emu/kernel/src/process.cpp"
    kernel_path = upstream / "src/emu/kernel/src/kernel.cpp"
    property_path = upstream / "src/emu/kernel/src/property.cpp"
    paths = (process_path, kernel_path, property_path)
    for path in paths:
        if not path.is_file():
            fail(f"missing B28 source: {path}")

    process = patch_process_kill(process_path.read_text(encoding="utf-8"))
    kernel = patch_kernel_destroy(kernel_path.read_text(encoding="utf-8"))
    prop = patch_property_reference_destructor(property_path.read_text(encoding="utf-8"))
    header_path = upstream / "src/emu/kernel/include/kernel/directhome_teardown_trace.h"
    header_path.write_text(HEADER, encoding="utf-8")
    process_path.write_text(process, encoding="utf-8")
    kernel_path.write_text(kernel, encoding="utf-8")
    property_path.write_text(prop, encoding="utf-8")
    print(f"{MARK}: applied; scope=native_phone_boot+compat_menu_probe_mode+compat_target_kind_2; diagnostics=read_only")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_teardowntrace1.py <upstream-root>")
    apply(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
