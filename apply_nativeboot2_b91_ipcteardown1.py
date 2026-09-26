#!/usr/bin/env python3
"""NATIVEBOOT2 B91: neutralize IPC references before kernel wipeout reset."""

from pathlib import Path
import re
import sys


MARK = "NATIVEBOOT2-B91-IPCTEARDOWN1"
PATCH_MARK = "B91 IPC messages must not unref dead sessions or threads."


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def apply(upstream_root):
    upstream = Path(upstream_root).resolve()
    kernel = upstream / "src/emu/kernel/src/kernel.cpp"
    if not kernel.is_file():
        fail(f"missing source: {kernel}")

    source = kernel.read_text(encoding="utf-8")
    if PATCH_MARK in source:
        expected = (
            "                msgs_[i]->own_thr = nullptr;",
            "                msgs_[i]->msg_session = nullptr;",
            "                msgs_[i]->ref_count = 0;",
            "            msgs_[i].reset();",
        )
        if all(source.count(item) == 1 for item in expected):
            print(MARK + ": already applied")
            return
        fail("partial B91 application detected")

    for required in (
        "        OBJECT_CONTAINER_CLEANUP(sessions_);",
        "        OBJECT_CONTAINER_CLEANUP(servers_);",
        "            msgs_[i].reset();",
        "        OBJECT_CONTAINER_CLEANUP_KEEP_OBJECTS(threads_);",
    ):
        if source.count(required) != 1:
            fail(f"expected one wipeout anchor: {required.strip()}")

    old = re.compile(
        r"(?m)^        for \(std::size_t i = 0; i < msgs_\.size\(\); i\+\+\) \{\n"
        r"            msgs_\[i\]\.reset\(\);[ \t]*\n"
        r"        \}\n"
    )
    new = """        for (std::size_t i = 0; i < msgs_.size(); i++) {
            if (msgs_[i]) {
                // B91 IPC messages must not unref dead sessions or threads.
                // Sessions and servers were destroyed above; neutralize any
                // remaining references before ipc_msg::~ipc_msg() can unref.
                msgs_[i]->own_thr = nullptr;
                msgs_[i]->msg_session = nullptr;
                msgs_[i]->ref_count = 0;
            }

            msgs_[i].reset();
        }
"""
    if len(old.findall(source)) != 1:
        fail("expected one original IPC message wipeout loop")

    source = old.sub(new, source, count=1)
    kernel.write_text(source, encoding="utf-8")
    print(MARK + ": applied")
    print("scope=kernel wipeout only; guest IPC and NativeBoot unchanged")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b91_ipcteardown1.py <upstream-root>")
    apply(sys.argv[1])


if __name__ == "__main__":
    main()
