#!/usr/bin/env python3
"""Skip DirectHome property notification completion for exiting requesters."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-PROPERTYCANCELGUARD1"
SIGNATURE = "bool property::cancel(const epoc::notify_info &info) {"
COMPLETE = "(*subscription_iterator)->complete(epoc::error_cancel);"
TRACE = "[COMPATBOOT][PROP_CANCEL_GUARD]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


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


def ensure_include(source, include):
    if include in source:
        return source
    anchor = "#include <kernel/kernel.h>\n"
    if source.count(anchor) != 1:
        fail("missing include insertion point")
    return source.replace(anchor, anchor + include + "\n", 1)


def patch_property_cancel(source):
    if TRACE in source:
        if source.count(TRACE) != 1 or source.count("if (nboot2_directhome_mode)") != 1:
            fail("partial or duplicate guard trace detected")
        return source

    def transform(body):
        if body.count(COMPLETE) != 1:
            fail(f"cancel completion: expected one call, found {body.count(COMPLETE)}")
        call_at = body.index(COMPLETE)
        line_start = body.rfind("\n", 0, call_at) + 1
        line_end = body.find("\n", call_at)
        if line_end < 0:
            line_end = len(body)
        line = body[line_start:line_end]
        indent = line[:len(line) - len(line.lstrip(" \t"))]
        if line.strip() != COMPLETE:
            fail("cancel completion is not a standalone statement")

        replacement = f'''{indent}const auto *nboot2_directhome_cancel_config = kern ? kern->get_config() : nullptr;
{indent}const bool nboot2_directhome_mode = nboot2_directhome_cancel_config
{indent}    && nboot2_directhome_cancel_config->native_phone_boot
{indent}    && nboot2_directhome_cancel_config->compat_menu_probe_mode
{indent}    && nboot2_directhome_cancel_config->compat_target_kind == 2;
{indent}if (nboot2_directhome_mode) {{
{indent}    auto *nboot2_directhome_requester = (*subscription_iterator)->requester;
{indent}    bool nboot2_directhome_registered = false;
{indent}    for (const auto &nboot2_directhome_candidate : kern->get_thread_list()) {{
{indent}        if (nboot2_directhome_candidate.get() == reinterpret_cast<kernel::kernel_obj *>(nboot2_directhome_requester)) {{
{indent}            nboot2_directhome_registered = true;
{indent}            break;
{indent}        }}
{indent}    }}
{indent}    auto *nboot2_directhome_process = nboot2_directhome_registered
{indent}        ? nboot2_directhome_requester->owning_process() : nullptr;
{indent}    const int nboot2_directhome_requester_exit_state = nboot2_directhome_registered
{indent}        ? static_cast<int>(nboot2_directhome_requester->get_exit_type()) : -1;
{indent}    const int nboot2_directhome_process_exit_state = nboot2_directhome_process
{indent}        ? static_cast<int>(nboot2_directhome_process->get_exit_type()) : -1;
{indent}    const bool nboot2_directhome_requester_active = nboot2_directhome_registered
{indent}        && nboot2_directhome_requester->get_exit_type() == kernel::entity_exit_type::pending
{indent}        && nboot2_directhome_process
{indent}        && nboot2_directhome_process->get_exit_type() == kernel::entity_exit_type::pending;
{indent}    LOG_INFO(KERNEL,
{indent}        "[COMPATBOOT][PROP_CANCEL_GUARD] requester_ptr={{}} requester_alive={{}} requester_exit_state={{}} process_exit_state={{}} decision={{}} request_status=0x{{:08X}}",
{indent}        static_cast<const void *>(nboot2_directhome_requester),
{indent}        nboot2_directhome_registered ? 1 : 0,
{indent}        nboot2_directhome_requester_exit_state, nboot2_directhome_process_exit_state,
{indent}        nboot2_directhome_requester_active ? "complete" : "skip",
{indent}        info.sts.ptr_address());
{indent}    if (nboot2_directhome_requester_active) {{
{indent}        {COMPLETE}
{indent}    }}
{indent}}} else {{
{indent}    {COMPLETE}
{indent}}}'''
        return body[:line_start] + replacement + body[line_end:]

    return patch_function(source, SIGNATURE, transform, "property::cancel")


def apply(root: Path) -> bool:
    root = Path(root).resolve()
    path = root / "src/emu/kernel/src/property.cpp"
    if not path.is_file():
        fail(f"missing source: {path}")
    original = path.read_text(encoding="utf-8")
    patched = patch_property_cancel(ensure_include(original, "#include <config/config.h>"))
    if patched != original:
        path.write_text(patched, encoding="utf-8")
    return patched != original


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_propertycancelguard1.py <upstream-root>")
    changed = apply(Path(sys.argv[1]))
    print(f"{MARK}: {'applied' if changed else 'already applied'}")
    print("scope=native_phone_boot+compat_menu_probe_mode+compat_target_kind_2; non_directhome=UNCHANGED")


if __name__ == "__main__":
    main()
