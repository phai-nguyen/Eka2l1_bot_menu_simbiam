#!/usr/bin/env python3
"""Apply read-only, CompatBoot-scoped B94 teardown diagnostics."""
from pathlib import Path
import re
import sys

MARK = "NATIVEBOOT2-B94-TEARDOWNPROBE1"
HEADER = '''#pragma once
#include <cstdint>
namespace eka2l1::kernel {
    struct notify_status_resolution_context {
        const void *process = nullptr;
        std::uintptr_t guest_address = 0;
    };
    inline thread_local notify_status_resolution_context b94_notify_status_context{};
    class scoped_notify_status_resolution {
        notify_status_resolution_context previous_;
    public:
        scoped_notify_status_resolution(const void *process, std::uintptr_t guest_address)
            : previous_(b94_notify_status_context) {
            b94_notify_status_context = { process, guest_address };
        }
        ~scoped_notify_status_resolution() { b94_notify_status_context = previous_; }
    };
    inline bool notify_status_resolution_matches(const void *process, std::uintptr_t guest_address) {
        return b94_notify_status_context.process == process
            && b94_notify_status_context.guest_address == guest_address;
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
        if len(include_lines) != 1:
            fail(f"{label}: missing unique include insertion point")
        anchor = include_lines[0]
    return source.replace(anchor, anchor + include + "\n", 1)

def patch_notify_complete(source):
    marker = "[COMPATBOOT][NOTIFY_STATUS]"
    if marker in source:
        if source.count(marker) != 2:
            fail("partial notify trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "notify_info")
    source = ensure_include(source, "#include <kernel/b94_teardown_probe.h>", "notify_info")
    signature = "void notify_info::complete(int err_code) {"
    old = "            epoc::request_status *sts_real = sts.get(requester->owning_process());\n            if (sts_real)\n"
    new = '''            kernel::process *nboot2_b94_requester_process = requester->owning_process();
            const bool nboot2_b94_notify_trace = kern->get_config()->compat_menu_probe_mode
                && (err_code == epoc::error_cancel);
            const std::uint32_t nboot2_b94_status_address = static_cast<std::uint32_t>(sts.ptr_address());
            const std::uint32_t nboot2_b94_requester_uid3 = nboot2_b94_requester_process
                ? static_cast<std::uint32_t>(std::get<2>(nboot2_b94_requester_process->get_uid_type())) : 0;
            if (nboot2_b94_notify_trace) {
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][NOTIFY_STATUS] phase=before_resolve requester_ptr={} requester={} requester_process_ptr={} requester_process={} requester_uid3=0x{:08X} request_status=0x{:08X} notify_status_scope=begin",
                    static_cast<const void *>(requester), requester->name(), static_cast<const void *>(nboot2_b94_requester_process),
                    nboot2_b94_requester_process ? nboot2_b94_requester_process->name() : std::string("<none>"),
                    nboot2_b94_requester_uid3, nboot2_b94_status_address);
            }
            kernel::scoped_notify_status_resolution nboot2_b94_status_scope(
                nboot2_b94_notify_trace ? static_cast<const void *>(nboot2_b94_requester_process) : nullptr,
                nboot2_b94_notify_trace ? nboot2_b94_status_address : 0);
            epoc::request_status *sts_real = sts.get(nboot2_b94_requester_process);
            if (nboot2_b94_notify_trace) {
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][NOTIFY_STATUS] phase=after_resolve requester_ptr={} requester_process_ptr={} requester_process={} requester_uid3=0x{:08X} request_status=0x{:08X} resolved_host_ptr={} notify_status_scope=result",
                    static_cast<const void *>(requester), static_cast<const void *>(nboot2_b94_requester_process),
                    nboot2_b94_requester_process ? nboot2_b94_requester_process->name() : std::string("<none>"),
                    nboot2_b94_requester_uid3, nboot2_b94_status_address, static_cast<void *>(sts_real));
            }
            if (sts_real)
'''
    return patch_function(source, signature, lambda body: replace_once(body, old, new, "notify status resolution"), "notify_info::complete")

def patch_property_cancel(source):
    marker = "[COMPATBOOT][PROP_CANCEL]"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial property cancel trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "property::cancel")
    signature = "bool property::cancel(const epoc::notify_info &info) {"
    def patch_body(body):
        call = "kern->is_thread_alive("
        call_positions = [match.start() for match in re.finditer(re.escape(call), body)]
        if len(call_positions) == 0:
            complete_pattern = re.compile(r"(?m)^([ \t]*)(\(\*subscription_iterator\)->complete\(epoc::error_cancel\);)[ \t]*$")
            complete_matches = list(complete_pattern.finditer(body))
            if len(complete_matches) != 1:
                fail(f"property cancel completion: expected one call, found {len(complete_matches)}")
            match = complete_matches[0]
            indent, complete_line = match.group(1), match.group(2)
            trace = f'''{indent}auto *nboot2_b94_requester = (*subscription_iterator)->requester;
{indent}if (kern->get_config()->compat_menu_probe_mode) {{
{indent}    LOG_INFO(KERNEL,
{indent}        "[COMPATBOOT][PROP_CANCEL] phase=before_complete property_ref_ptr={{}} property_ptr={{}} requester_ptr={{}} requester={{}} requester_alive=-1 request_status=0x{{:08X}}",
{indent}        static_cast<const void *>(&info), static_cast<const void *>(this),
{indent}        static_cast<const void *>(nboot2_b94_requester),
{indent}        nboot2_b94_requester ? nboot2_b94_requester->name() : std::string("<none>"), info.sts.ptr_address());
{indent}}}
{indent}{complete_line}'''
            return body[:match.start()] + trace + body[match.end():]
        if len(call_positions) != 1:
            fail(f"property cancel liveness: expected at most one liveness call, found {len(call_positions)}")
        call_pos = call_positions[0]
        expr_start = call_pos + len(call)
        depth = 1
        expr_end = expr_start
        while expr_end < len(body) and depth:
            if body[expr_end] == "(":
                depth += 1
            elif body[expr_end] == ")":
                depth -= 1
            expr_end += 1
        if depth:
            fail("property cancel liveness: unterminated is_thread_alive call")
        requester_expr = body[expr_start:expr_end - 1].strip()
        line_start = body.rfind("\n", 0, call_pos) + 1
        line_end = body.find("\n", expr_end)
        if line_end < 0:
            fail("property cancel liveness: missing conditional line ending")
        original_line = body[line_start:line_end]
        indent = original_line[:len(original_line) - len(original_line.lstrip(" \t"))]
        if "if" not in original_line or "{" not in original_line:
            fail("property cancel liveness: liveness call is not an if condition")
        replacement = f'''{indent}auto *nboot2_b94_requester = (*subscription_iterator)->requester;
{indent}const bool nboot2_b94_requester_alive = kern->is_thread_alive(nboot2_b94_requester);
{indent}if (kern->get_config()->compat_menu_probe_mode) {{
{indent}    LOG_INFO(KERNEL,
{indent}        "[COMPATBOOT][PROP_CANCEL] phase=before_complete property_ref_ptr={{}} property_ptr={{}} requester_ptr={{}} requester={{}} requester_alive={{}} request_status=0x{{:08X}}",
{indent}        static_cast<const void *>(&info), static_cast<const void *>(this),
{indent}        static_cast<const void *>(nboot2_b94_requester),
{indent}        nboot2_b94_requester ? nboot2_b94_requester->name() : std::string("<none>"),
{indent}        nboot2_b94_requester_alive ? 1 : 0, info.sts.ptr_address());
{indent}}}
{indent}if (nboot2_b94_requester_alive) {{'''
        replacement = replacement.replace("(*subscription_iterator)->requester", requester_expr)
        return body[:line_start] + replacement + body[line_end:]
    return patch_function(source, signature, patch_body, "property::cancel")

def patch_process_kill(source):
    marker = "[COMPATBOOT][PROCESS_KILL]"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial process kill trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "process::kill")
    signature = "void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {"
    old = "\n        if (exit_type != entity_exit_type::pending) {\n"
    new = '''
        if (get_kernel_object_owner()->get_config()->compat_menu_probe_mode) {
            const auto nboot2_b94_uids = get_uid_type();
            LOG_INFO(KERNEL,
                "[COMPATBOOT][PROCESS_KILL] phase=begin process_ptr={} process={} uid3=0x{:08X} exit_type={} reason={}",
                static_cast<const void *>(this), name(),
                static_cast<std::uint32_t>(std::get<2>(nboot2_b94_uids)), static_cast<int>(ext), reason);
        }
        if (exit_type != entity_exit_type::pending) {
'''
    return patch_function(source, signature, lambda body: replace_once(body, old, new, "process kill entry"), "process::kill")

def patch_process_address_space(source):
    marker = "[COMPATBOOT][NOTIFY_STATUS_MAP]"
    if marker in source:
        if source.count(marker) != 2:
            fail("partial address-space trace detected")
        return source
    source = ensure_include(source, "#include <kernel/b94_teardown_probe.h>", "process address-space lookup")
    signature = "void *process::get_ptr_on_addr_space(address addr) {"
    old = "        return mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);\n"
    new = '''        const bool nboot2_b94_trace_status_map = notify_status_resolution_matches(this, addr);
        if (nboot2_b94_trace_status_map) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][NOTIFY_STATUS_MAP] phase=begin process_ptr={} guest_status=0x{:08X} address_space={}",
                static_cast<const void *>(this), static_cast<std::uint32_t>(addr), mm_impl_->address_space_id());
        }
        void *nboot2_b94_host_pointer = mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);
        if (nboot2_b94_trace_status_map) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][NOTIFY_STATUS_MAP] phase=result process_ptr={} guest_status=0x{:08X} address_space={} host_pointer={}",
                static_cast<const void *>(this), static_cast<std::uint32_t>(addr),
                mm_impl_->address_space_id(), nboot2_b94_host_pointer);
        }
        return nboot2_b94_host_pointer;
'''
    return patch_function(source, signature, lambda body: replace_once(body, old, new, "address-space host pointer lookup"), "process::get_ptr_on_addr_space")

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b94_teardownprobe1.py <upstream-root>")
    upstream = Path(sys.argv[1]).resolve()
    thread_path = upstream / "src/emu/kernel/src/thread.cpp"
    property_path = upstream / "src/emu/kernel/src/property.cpp"
    process_path = upstream / "src/emu/kernel/src/process.cpp"
    for path in (thread_path, property_path, process_path):
        if not path.is_file():
            fail(f"missing B28 source: {path}")
    thread = patch_notify_complete(thread_path.read_text(encoding="utf-8"))
    prop = patch_property_cancel(property_path.read_text(encoding="utf-8"))
    process = process_path.read_text(encoding="utf-8")
    process = patch_process_kill(process)
    process = patch_process_address_space(process)
    (upstream / "src/emu/kernel/include/kernel/b94_teardown_probe.h").write_text(HEADER, encoding="utf-8")
    thread_path.write_text(thread, encoding="utf-8")
    property_path.write_text(prop, encoding="utf-8")
    process_path.write_text(process, encoding="utf-8")
    print(f"{MARK}: applied; diagnostics=read_only,CompatBoot_scoped")

if __name__ == "__main__":
    main()
