#!/usr/bin/env python3
"""Unlink collected code-segment attach info before freeing it."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-CODESEG-COLLECTOR-UNLINK1"
SIGNATURE = "void codeseg::free_attached_data(attached_info &info) {"
NEXT_FUNCTION = "bool codeseg::detach("
UNLINK = "kern->get_codedump_collector().remove(info);"
ANCHOR = "info.closing_lib_link.deque();"
ERASE = "attaches.erase(ite);"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def patch_free_attached_data(source: str) -> str:
    if source.count(SIGNATURE) != 1:
        fail(f"expected one free_attached_data definition, found {source.count(SIGNATURE)}")
    start = source.index(SIGNATURE)
    end = source.find(NEXT_FUNCTION, start + len(SIGNATURE))
    if end < 0:
        fail("cannot locate codeseg::detach after free_attached_data")

    function = source[start:end]
    if function.count(ERASE) != 1:
        fail(f"expected one attach erase, found {function.count(ERASE)}")
    if function.count(ANCHOR) != 1:
        fail(f"expected one closing link dequeue, found {function.count(ANCHOR)}")

    if UNLINK in function:
        if function.count(UNLINK) != 1:
            fail("duplicate collector unlink")
        if function.index(UNLINK) > function.index(ANCHOR) or function.index(UNLINK) > function.index(ERASE):
            fail("collector unlink must precede link teardown and attach erase")
        return source

    anchor_at = function.index(ANCHOR)
    line_start = function.rfind("\n", 0, anchor_at) + 1
    indent = function[line_start:anchor_at]
    if indent.strip():
        fail("unexpected formatting before closing link dequeue")
    replacement = f"{indent}{UNLINK}\n{indent}{ANCHOR}"
    patched_function = function[:line_start] + replacement + function[anchor_at + len(ANCHOR):]
    return source[:start] + patched_function + source[end:]


def apply(root: Path) -> bool:
    path = Path(root).resolve() / "src/emu/kernel/src/codeseg.cpp"
    if not path.is_file():
        fail(f"missing source: {path}")
    original = path.read_text(encoding="utf-8")
    patched = patch_free_attached_data(original)
    if patched != original:
        path.write_text(patched, encoding="utf-8")
    return patched != original


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_codesegcollectorunlink1.py <upstream-root>")
    changed = apply(Path(sys.argv[1]))
    print(f"{MARK}: {'applied' if changed else 'already present'}")
    print("invariant=collector_link_removed_before_attached_info_erase")


if __name__ == "__main__":
    main()
