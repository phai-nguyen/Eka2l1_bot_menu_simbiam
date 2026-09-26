#!/usr/bin/env python3
"""Contract for B84's exact resource-ID provenance window."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B84-PHONEUIRESIDWINDOW1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def require(source, token):
    if token not in source:
        fail(f"missing {token}")


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b84_phoneuiresidwindow1.py <upstream-root>")

    svc = Path(sys.argv[1]).resolve() / "src/emu/kernel/src/svc.cpp"
    if not svc.is_file():
        fail(f"missing source: {svc}")
    source = svc.read_text(encoding="utf-8")

    for token in (
        "[NBOOT2][PHONEUI_RESID_SOURCE]",
        "[NBOOT2][PHONEUI_RESID_WINDOW]",
        "[NBOOT2][PHONEUI_RESID_SUMMARY]",
        "0x1099B02DU",
        "nboot2_b84_stack_words=128U",
        "nboot2_b84_window_radius=8",
        "value==nboot2_b84_resource_id",
        "*slot!=nboot2_b84_resource_id",
        "resource_registration=UNCHANGED boot_behavior=UNCHANGED",
        "behavior=OBSERVE_ONLY",
        "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
    ):
        require(source, token)

    begin = source.index("// B84 PHONEUIRESIDWINDOW1:")
    end = source.index("[NBOOT2][CONE14_SUMMARY]", begin)
    body = source[begin:end]
    for forbidden in (
        "set_reg(",
        "write(",
        "AddResourceFile",
        "add_resource",
        "ctx->complete(",
        "thr->kill(",
    ):
        if forbidden in body:
            fail(f"B84 diagnostic block changes behavior via {forbidden}")

    print(MARK + ": PASS")
    print("resource_id=0x1099B02D")
    print("guest_mutations=NONE")
    print("resource_registration=UNCHANGED")
    print("boot_behavior=UNCHANGED")


if __name__ == "__main__":
    main()
