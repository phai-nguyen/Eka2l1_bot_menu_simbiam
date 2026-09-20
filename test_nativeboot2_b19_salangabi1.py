#!/usr/bin/env python3
"""Validation contract for NATIVEBOOT2 B19 SALANGABI1 diagnostic instrumentation.

This is intentionally a source-level regression test. It verifies that B19:
- handles the exact raw RM-356 function 0x01100068, not a guessed 0x68 alias;
- records enough IPC metadata to identify the real SAClient transport ABI;
- does not mutate output descriptors or synthesize a language-list response;
- preserves guest-visible failure semantics by completing KErrNotSupported.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B19-SALANGABI1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b19_salangabi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    sa = up / "src/emu/services/src/sms/sa/sa.cpp"
    if not sa.is_file():
        fail(f"missing {sa}")

    text = sa.read_text(encoding="utf-8")

    required = (
        "[NBOOT2][SA_LANG_ABI]",
        "raw_func=0x{:X}",
        "logical_func=0x{:X}",
        "transport_bits=0x{:X}",
        "raw_args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "types=[{},{},{},{}]",
        "sizes=[{},{},{},{}]",
        "max=[{},{},{},{}]",
        "preview0=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview1=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview2=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "preview3=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}]",
        "ctx.complete(epoc::error_not_supported);",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
    )
    for needle in required:
        if needle not in text:
            fail(f"missing B19 contract marker: {needle}")

    start = text.find("// NATIVEBOOT2-B19 SALANGABI1:")
    end = text.find("// NATIVEBOOT2-B18 SARTC1:", start)
    if start < 0 or end < 0 or end <= start:
        fail("cannot isolate B19 diagnostic block")

    block = text[start:end]

    forbidden = (
        "write_data_to_descriptor_argument",
        "write_arg(",
        "set_descriptor_argument_length",
        "epoc::error_none);",
    )
    for needle in forbidden:
        if needle in block:
            fail(f"B19 diagnostic block mutates/completes success unexpectedly: {needle}")

    if "0x01100068" not in block:
        fail("B19 diagnostic block is not keyed to exact raw opcode 0x01100068")
    if "0xFFFF" not in block or "0xFFFF0000" not in block:
        fail("B19 does not expose logical/transport decomposition")
    if "get_descriptor_argument_ptr" not in block:
        fail("B19 does not inspect descriptor contents")
    if "std::memcpy" not in block:
        fail("B19 does not copy descriptor preview safely")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
