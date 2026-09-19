#!/usr/bin/env python3
"""NATIVEBOOT2-B7 LOCALEABI1.

Apply on top of B6 RM356-BSP1.

Observed B6 runtime:
  Media DriveInfo OK
  StartupReason OK
  SVCMISS 0xE4 twice with r0=0 then r0=1
  EStart panic ESTART_6 / 1

Symbian source proves ESTART_6 is UserSvr::LocalePropertiesSetDefaults() failure.
That function ends with:
  Exec::SetGlobalUserData(ELocaleDefaultCharSet, charSet)
  Exec::SetGlobalUserData(ELocalePreferredCharSet, charSet)

ELocaleDefaultCharSet=0, ELocalePreferredCharSet=1. RM-356's EUSER uses slow
SVC 0xE4 for SetGlobalUserData. EKA2L1 already has fast GetGlobalUserData but
its implementation is a zero-return stub and has the wrong no-argument ABI.

B7 implements both sides using kernel_global_data::char_set_ storage:
  index 0 -> char_data_set_
  index 1 -> collation_data_set_
and registers slow 0xE4 in the EPOC94 table.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B7-LOCALEABI1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_svc(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][RM356_SET_GLOBAL_USERDATA]" in text:
        return

    old_get = """    BRIDGE_FUNC(eka2l1::ptr<void>, get_global_userdata) {
        //LOG_INFO(KERNEL, "get_global_userdata stubbed with zero");
        return 0;
    }
"""
    new_get = """    BRIDGE_FUNC(std::int32_t, get_global_userdata, const std::int32_t index) {
        kernel_global_data *global = kern->get_global_user_data_pointer().get(kern->crr_process());
        if (!global) {
            return 0;
        }

        std::int32_t value = 0;
        switch (index) {
        case 0: // ELocaleDefaultCharSet
            value = static_cast<std::int32_t>(global->char_set_.char_data_set_);
            break;
        case 1: // ELocalePreferredCharSet
            value = static_cast<std::int32_t>(global->char_set_.collation_data_set_);
            break;
        default:
            LOG_WARN(KERNEL, "[NBOOT2][RM356_GET_GLOBAL_USERDATA_BAD] index={}", index);
            return 0;
        }

        LOG_WARN(KERNEL, "[NBOOT2][RM356_GET_GLOBAL_USERDATA] index={} value=0x{:08X}",
            index, static_cast<std::uint32_t>(value));
        return value;
    }

    BRIDGE_FUNC(std::int32_t, set_global_userdata, const std::int32_t index,
        const std::int32_t value) {
        kernel_global_data *global = kern->get_global_user_data_pointer().get(kern->crr_process());
        if (!global) {
            return epoc::error_no_memory;
        }

        switch (index) {
        case 0: // ELocaleDefaultCharSet
            global->char_set_.char_data_set_ = static_cast<address>(value);
            break;
        case 1: // ELocalePreferredCharSet
            global->char_set_.collation_data_set_ = static_cast<address>(value);
            break;
        default:
            LOG_WARN(KERNEL,
                "[NBOOT2][RM356_SET_GLOBAL_USERDATA_BAD] index={} value=0x{:08X}",
                index, static_cast<std::uint32_t>(value));
            return epoc::error_argument;
        }

        LOG_WARN(KERNEL,
            "[NBOOT2][RM356_SET_GLOBAL_USERDATA] index={} value=0x{:08X} completion=KErrNone",
            index, static_cast<std::uint32_t>(value));
        return epoc::error_none;
    }
"""
    text = replace_once(text, old_get, new_get, "global userdata ABI implementation")

    start = text.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    if start < 0:
        fail("EPOC94 SVC table missing")
    end = text.find("\n    };", start)
    if end < 0:
        fail("EPOC94 SVC table end missing")

    before = text[:start]
    block = text[start:end]
    after = text[end:]

    if "BRIDGE_REGISTER(0xE4," in block:
        fail("EPOC94 0xE4 already occupied")

    # Registration order is irrelevant to func_map lookup. Append the RM-356
    # slot at the end of the v94 initializer so this patch is independent of
    # historical shifts in the neighbouring E2/E3/E5 executive numbers.
    if not block.endswith("\n"):
        block += "\n"
    block += """        // NATIVEBOOT2-B7: RM-356 EUSER SetGlobalUserData.
        BRIDGE_REGISTER(0xE4, set_global_userdata),
"""

    # Preserve all existing RM-356 ABI invariants.
    if "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)" not in block:
        fail("EPOC94 0x0A mapping lost")
    if "BRIDGE_REGISTER(0x83, logical_channel_create_v95)" not in block:
        fail("EPOC94 0x83 mapping lost")
    if "BRIDGE_REGISTER(0xAA," in block:
        fail("EPOC94 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)" not in block:
        fail("EPOC94 0xAB invariant lost")
    if "BRIDGE_REGISTER(0xAC, message_kill)" not in block:
        fail("EPOC94 0xAC invariant lost")

    path.write_text(before + block + after, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b7_localeabi1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc = up / "src/emu/kernel/src/svc.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (svc, hal, fs, state, root):
        if not p.is_file():
            fail(f"missing B6 baseline file: {p}")

    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 StartupReason marker missing")
    if "[NBOOT2][RM356_FS_MAPPING]" not in fs.read_text(encoding="utf-8"):
        fail("B6 FileServer BSP marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_svc(svc)

    body = svc.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][RM356_SET_GLOBAL_USERDATA]",
        "[NBOOT2][RM356_GET_GLOBAL_USERDATA]",
        "BRIDGE_FUNC(std::int32_t, set_global_userdata",
        "BRIDGE_FUNC(std::int32_t, get_global_userdata",
    ):
        if gate not in body:
            fail(f"SVC implementation gate missing: {gate}")

    a = body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = body.find("\n    };", a)
    v94 = body[a:b]
    if "BRIDGE_REGISTER(0xE4, set_global_userdata)" not in v94:
        fail("EPOC94 0xE4 mapping missing")

    print("NATIVEBOOT2-B7 LOCALEABI1 applied")
    print("EP94_0xE4=SetGlobalUserData")
    print("GlobalUserData_index0=DefaultCharSet")
    print("GlobalUserData_index1=PreferredCharSet")
    print("Fast_GetGlobalUserData=REAL_STORAGE")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
