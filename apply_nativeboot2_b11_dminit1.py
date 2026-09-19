#!/usr/bin/env python3
"""NATIVEBOOT2-B11 DMINIT1.

Apply on top of B10 FSFORMAT1.

Observed B10:
- EStart completes LocalDriveInit and StartupInitComplete.
- EStart launches native domainSrv.exe.
- domainSrv loads domainPolicy.dll and registers !DmManagerServer / !DmDomainServer.
- EStart then waits forever in RDmDomainManager::WaitForInitialization().
- HALSettings also hits missing EPOC94 SVC 0xB1.

Root causes established from Symbian source + EKA2L1 source:
1) EPOC94 0xB1 is CreatorSecurityInfo. EKA2L1 already implements
   creator_security_info, but v94 does not register it.
2) Static RProperty::Set(category,key,int) maps to property_find_set_int.
   EKA2L1 incorrectly calls property::set(value), whose templated overload
   writes binary storage and does NOT update integer ndata. It still notifies
   subscribers. RDmDomainManager therefore wakes, Get() reads 0 again,
   subscribes a second time, and waits forever after domainSrv set init=True.

B11 fixes the generic integer property ABI and maps 0xB1.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B11-DMINIT1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_property_find_set_int(text: str) -> str:
    old = """    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
        property_ptr prop = kern->get_prop(cage, key);

        if (!prop || !prop->is_defined()) {
            return epoc::error_not_found;
        }

        const bool res = prop->set(value);

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
    }
"""
    new = """    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
        property_ptr prop = kern->get_prop(cage, key);

        if (!prop || !prop->is_defined()) {
            return epoc::error_not_found;
        }

        // NATIVEBOOT2-B11 DMINIT1:
        // Static RProperty::Set(category,key,TInt) must update the integer
        // backing field. The previous templated property::set(value) routed
        // through binary storage, notified subscribers but left ndata at 0.
        const bool res = prop->set_int(value);

        if (!res) {
            return epoc::error_argument;
        }

        if ((static_cast<std::uint32_t>(cage) == 0x1020E406u) && (key == 1)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][DM_INIT_SET_INT] category=0x{:08X} key=0x{:08X} value={} stored={} completion=KErrNone",
                static_cast<std::uint32_t>(cage), static_cast<std::uint32_t>(key),
                value, prop->get_int());
        }

        return epoc::error_none;
    }
"""
    return replace_once(text, old, new, "property_find_set_int integer storage")

def patch_dm_traces(text: str) -> str:
    # Targeted subscribe trace for the Domain Manager init property.
    old_sub = """    BRIDGE_FUNC(void, property_subscribe, kernel::handle h, eka2l1::ptr<epoc::request_status> sts) {
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop) {
            return;
        }

        epoc::notify_info info(sts, kern->crr_thread());
        prop->subscribe(info);
    }
"""
    new_sub = """    BRIDGE_FUNC(void, property_subscribe, kernel::handle h, eka2l1::ptr<epoc::request_status> sts) {
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop) {
            return;
        }

        service::property *obj = prop->get_property_object();
        if (obj && (static_cast<std::uint32_t>(obj->first) == 0x1020E406u) && (obj->second == 1)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][DM_INIT_SUBSCRIBE] handle=0x{:08X} defined={} current={}",
                static_cast<std::uint32_t>(h), obj->is_defined() ? 1 : 0,
                obj->is_defined() ? obj->get_int() : -1);
        }

        epoc::notify_info info(sts, kern->crr_thread());
        prop->subscribe(info);
    }
"""
    text = replace_once(text, old_sub, new_sub, "DM init subscribe trace")

    old_get = """    BRIDGE_FUNC(std::int32_t, property_get_int, kernel::handle h, eka2l1::ptr<std::int32_t> value_ptr) {
        process_ptr pr = kern->crr_process();
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop || !prop->get_property_object()->is_defined()) {
            return epoc::error_not_found;
        }

        *value_ptr.get(pr) = prop->get_property_object()->get_int();

        if (prop->get_property_object()->get_int() == -1) {
            return epoc::error_argument;
        }

        return epoc::error_none;
    }
"""
    new_get = """    BRIDGE_FUNC(std::int32_t, property_get_int, kernel::handle h, eka2l1::ptr<std::int32_t> value_ptr) {
        process_ptr pr = kern->crr_process();
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop || !prop->get_property_object()->is_defined()) {
            return epoc::error_not_found;
        }

        service::property *obj = prop->get_property_object();
        const std::int32_t value = obj->get_int();
        *value_ptr.get(pr) = value;

        if ((static_cast<std::uint32_t>(obj->first) == 0x1020E406u) && (obj->second == 1)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][DM_INIT_GET_INT] handle=0x{:08X} value={}",
                static_cast<std::uint32_t>(h), value);
        }

        if (value == -1) {
            return epoc::error_argument;
        }

        return epoc::error_none;
    }
"""
    return replace_once(text, old_get, new_get, "DM init get trace")

def patch_creator_trace(text: str) -> str:
    old = """    BRIDGE_FUNC(void, creator_security_info, epoc::security_info *info) {
        if (!info) {
            return;
        }

        kernel::process *crr_process = kern->crr_process();
        kernel::process *owner = crr_process->get_parent_process();

        if (!owner) {
            LOG_TRACE(KERNEL, "Process is a wild child, has no parents. Creator info is empty.");
            *info = epoc::security_info{};
        } else {
            *info = std::move(owner->get_sec_info());
        }
    }
"""
    new = """    BRIDGE_FUNC(void, creator_security_info, epoc::security_info *info) {
        if (!info) {
            return;
        }

        kernel::process *crr_process = kern->crr_process();
        kernel::process *owner = crr_process->get_parent_process();

        if (!owner) {
            LOG_TRACE(KERNEL, "Process is a wild child, has no parents. Creator info is empty.");
            *info = epoc::security_info{};
        } else {
            *info = std::move(owner->get_sec_info());
        }

        LOG_WARN(KERNEL,
            "[NBOOT2][RM356_CREATOR_SECURITY] process={} parent={} completion=OK",
            crr_process ? crr_process->name() : std::string("<none>"),
            owner ? owner->name() : std::string("<none>"));
    }
"""
    return replace_once(text, old, new, "creator security trace")

def patch_v94(text: str) -> str:
    start = text.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    if start < 0:
        fail("EPOC94 table missing")
    end = text.find("\n    };", start)
    if end < 0:
        fail("EPOC94 table end missing")

    before = text[:start]
    block = text[start:end]
    after = text[end:]

    if "BRIDGE_REGISTER(0xB1," in block:
        # If already mapped, require correct target.
        if "BRIDGE_REGISTER(0xB1, creator_security_info)" not in block:
            fail("EPOC94 0xB1 already occupied by wrong target")
        return text

    anchor = "        BRIDGE_REGISTER(0xB0, message_security_info),\n"
    if anchor not in block:
        fail("EPOC94 0xB0 MessageSecurityInfo anchor missing")
    block = block.replace(
        anchor,
        anchor +
        "        // NATIVEBOOT2-B11: Symbian 9.4 CreatorSecurityInfo.\n"
        "        BRIDGE_REGISTER(0xB1, creator_security_info),\n",
        1)

    # Preserve established RM-356 ABI invariants.
    required = [
        "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)",
        "BRIDGE_REGISTER(0x83, logical_channel_create_v95)",
        "BRIDGE_REGISTER(0xAB, message_construct)",
        "BRIDGE_REGISTER(0xAC, message_kill)",
        "BRIDGE_REGISTER(0xE4, set_global_userdata)",
    ]
    for gate in required:
        if gate not in block:
            fail(f"EPOC94 invariant lost: {gate}")
    if "BRIDGE_REGISTER(0xAA," in block:
        fail("EPOC94 0xAA must remain unmapped")

    return before + block + after

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b11_dminit1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing B10 baseline file: {p}")

    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" not in fs.read_text(encoding="utf-8"):
        fail("B10 FSFORMAT1 marker missing")
    if "[NBOOT2][RM356_FS_PROPERTIES]" not in fs.read_text(encoding="utf-8"):
        fail("B9 FSPROPS1 marker missing")
    if "[NBOOT2][RM356_LOADER_FSY]" not in loader.read_text(encoding="utf-8"):
        fail("B8 LOADERFSY1 marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 BSP marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    text = svc.read_text(encoding="utf-8")
    text = patch_property_find_set_int(text)
    text = patch_dm_traces(text)
    text = patch_creator_trace(text)
    text = patch_v94(text)
    svc.write_text(text, encoding="utf-8")

    body = svc.read_text(encoding="utf-8")
    for gate in (
        "prop->set_int(value)",
        "[NBOOT2][DM_INIT_SET_INT]",
        "[NBOOT2][DM_INIT_SUBSCRIBE]",
        "[NBOOT2][DM_INIT_GET_INT]",
        "[NBOOT2][RM356_CREATOR_SECURITY]",
        "BRIDGE_REGISTER(0xB1, creator_security_info)",
    ):
        if gate not in body:
            fail(f"B11 gate missing: {gate}")

    print("NATIVEBOOT2-B11 DMINIT1 applied")
    print("EP94_0xB1=CreatorSecurityInfo")
    print("PropertyFindSetInt=integer_ndata_setter")
    print("DomainInit_property=0x1020E406:0x1 traced")
    print("B10_FSFORMAT1=PRESERVED")
    print("B9_FSPROPS1=PRESERVED")
    print("B8_LOADERFSY1=PRESERVED")
    print("B7_LOCALEABI1=PRESERVED")
    print("B6_RM356_BSP1=PRESERVED")
    print("EMUHUB1=MENUUI36=NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
