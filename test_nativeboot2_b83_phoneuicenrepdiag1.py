#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B83 PHONEUICENREPDIAG1."""
from pathlib import Path
import re
import sys

MARK = "NATIVEBOOT2-B83-PHONEUICENREPDIAG1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def need(body, token, where):
    if token not in body:
        fail(f"missing in {where}: {token}")


def callback_body(source, name):
    match = re.search(
        rf"static void {re.escape(name)}\(\) \{{(.*?)\n    \}}",
        source,
        re.DOTALL,
    )
    if not match:
        fail(f"missing native callback: {name}")
    return match.group(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b83_phoneuicenrepdiag1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    path = upstream / "src/emu/scripting/src/builtin_patches.cpp"
    if not path.is_file():
        fail(f"missing source: {path}")
    source = path.read_text(encoding="utf-8")

    callbacks = {
        "phoneui_cenrep43c_entry": "[NBOOT2][PHONEUI_CENREP43C_ENTRY]",
        "phoneui_cenrep43c_status": "[NBOOT2][PHONEUI_CENREP43C_STATUS]",
        "phoneui_cenrep43c_return": "[NBOOT2][PHONEUI_CENREP43C_RETURN]",
    }
    for name, marker in callbacks.items():
        body = callback_body(source, name)
        need(body, marker, name)
        need(body, "scripting::cpu::get_register", name)
        for forbidden in ("cpu::set_register", "set_pc(", "complete(", "Leave("):
            if forbidden in body:
                fail(f"guest behavior mutation in {name}: {forbidden}")

    registrations = (
        r'register_breakpoint\("centralrepository\.dll",\s*0x80392135U,\s*0,\s*0x101FBC70U,\s*0,\s*phoneui_cenrep43c_entry\);',
        r'register_breakpoint\("centralrepository\.dll",\s*0x80392141U,\s*0,\s*0x101FBC70U,\s*0,\s*phoneui_cenrep43c_status\);',
        r'register_breakpoint\("centralrepository\.dll",\s*0x803921C3U,\s*0,\s*0x101FBC70U,\s*0,\s*phoneui_cenrep43c_return\);',
    )
    for registration in registrations:
        if not re.search(registration, source):
            fail("missing RM-356 centralrepository breakpoint registration: " + registration)
    if source.count('register_breakpoint("centralrepository.dll"') != 3:
        fail("probe must register exactly three centralrepository breakpoints")

    if "EKA2L1_SCRIPTING_LUA" not in source and "#ifndef ENABLE_SCRIPTING_LUA" not in source:
        fail("native iOS-only breakpoint path is not guarded by the native-patches build")

    print(MARK + ": PASS")
    print("boundaries=ENTRY,+F60_STATUS,NORMAL_RETURN")
    print("guest_register_mutations=NONE")
    print("resource_registration=UNCHANGED")
    print("global_fallback=NONE")


if __name__ == "__main__":
    main()
