#!/usr/bin/env python3
"""NATIVEBOOT2 B83 PHONEUICENREPDIAG1.

Install a narrow, native-only observation probe at the RM-356
centralrepository.dll descriptor consumer. It logs entry registers, the
status returned from +0xF60, and whether control reaches the normal caller
continuation. It does not alter guest registers or resource behavior.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B83-PHONEUICENREPDIAG1"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b83_phoneuicenrepdiag1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    path = upstream / "src/emu/scripting/src/builtin_patches.cpp"
    if not path.is_file():
        fail(f"missing source: {path}")
    source = path.read_text(encoding="utf-8")

    for dependency in (
        "#ifndef ENABLE_SCRIPTING_LUA",
        "#include <scripting/cpu.h>",
        "#include <scripting/manager.h>",
        "void scripts::register_builtin_patches() {",
        "        current_module = nullptr;",
    ):
        if dependency not in source:
            fail(f"native patch integration anchor missing: {dependency}")

    if "[NBOOT2][PHONEUI_CENREP43C_ENTRY]" in source:
        print(MARK + ": already applied")
        return

    callbacks = r'''    // --- RM-356 PhoneUI CentralRepository descriptor probe (diagnostic only) ---
    static void phoneui_cenrep43c_entry() {
        LOG_INFO(SCRIPTING,
            "[NBOOT2][PHONEUI_CENREP43C_ENTRY] object=0x{:08X} descriptor=0x{:08X} lr=0x{:08X} behavior=OBSERVE_ONLY",
            scripting::cpu::get_register(0), scripting::cpu::get_register(1),
            scripting::cpu::get_lr());
    }

    static void phoneui_cenrep43c_status() {
        LOG_INFO(SCRIPTING,
            "[NBOOT2][PHONEUI_CENREP43C_STATUS] status=0x{:08X} status_signed={} object=0x{:08X} descriptor=0x{:08X} behavior=OBSERVE_ONLY",
            scripting::cpu::get_register(0),
            static_cast<std::int32_t>(scripting::cpu::get_register(0)),
            scripting::cpu::get_register(5), scripting::cpu::get_register(6));
    }

    static void phoneui_cenrep43c_return() {
        LOG_INFO(SCRIPTING,
            "[NBOOT2][PHONEUI_CENREP43C_RETURN] status=0x{:08X} object=0x{:08X} behavior=OBSERVE_ONLY",
            scripting::cpu::get_register(0), scripting::cpu::get_register(4));
    }

'''
    source = replace_once(source, "    void scripts::register_builtin_patches() {", callbacks +
        "    void scripts::register_builtin_patches() {", "native PhoneUI callbacks")

    registrations = r'''        // RM-356 centralrepository.dll: verified E32 code base 0x80391CF8,
        // UID3 0x101FBC70. Addresses are Thumb pointers (bit 0 set):
        // +0x43C entry, +0x448 after +0xF60, +0x4CA normal caller continuation.
        register_breakpoint("centralrepository.dll", 0x80392135U, 0,
            0x101FBC70U, 0, phoneui_cenrep43c_entry);
        register_breakpoint("centralrepository.dll", 0x80392141U, 0,
            0x101FBC70U, 0, phoneui_cenrep43c_status);
        register_breakpoint("centralrepository.dll", 0x803921C3U, 0,
            0x101FBC70U, 0, phoneui_cenrep43c_return);

'''
    source = replace_once(source, "        current_module = nullptr;", registrations +
        "        current_module = nullptr;", "RM-356 PhoneUI breakpoint registrations")

    required = (
        "[NBOOT2][PHONEUI_CENREP43C_ENTRY]",
        "[NBOOT2][PHONEUI_CENREP43C_STATUS]",
        "[NBOOT2][PHONEUI_CENREP43C_RETURN]",
        "0x80392135U",
        "0x80392141U",
        "0x803921C3U",
        "0x101FBC70U",
        "behavior=OBSERVE_ONLY",
    )
    for token in required:
        if token not in source:
            fail(f"post-apply gate missing: {token}")

    path.write_text(source, encoding="utf-8")

    print(MARK + ": applied")
    print("boundaries=ENTRY,+F60_STATUS,NORMAL_RETURN")
    print("descriptor_capture=R1_POINTER_AND_SAVED_R6")
    print("guest_register_mutations=NONE")
    print("resource_registration=UNCHANGED")
    print("global_fallback=NONE")


if __name__ == "__main__":
    main()
