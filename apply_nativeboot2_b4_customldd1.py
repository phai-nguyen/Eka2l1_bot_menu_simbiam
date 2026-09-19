#!/usr/bin/env python3
"""NATIVEBOOT2-B4 CUSTOMLDD1.

Apply on top of B3 NOKIAISC2.

Observed B3 runtime:
  [NBOOT2][NOKIAISC_INIT_COMPLETE] ... KErrNone
  [NBOOT2][NOKIAISC_CONTROL] opcode=15
  Trying to load LDD Custom.ldd
  Trying to load LDD Custom
  V5 CHANCREATE: unsupported logical device 'custom' (unit -1)
  EStart panic category=Custom.ldd reason=-1

This patch adds a diagnostic, inert HLE logical-device factory named "custom".
The goal is deliberately narrow: let RM-356 EStart create the channel and
record the first real control/request opcodes. We do not guess undocumented
hardware semantics ahead of evidence.

Existing NokiaISC and EPOC94 ABI invariants are preserved.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B4-CUSTOMLDD1"

CUSTOM_H = r'''/*
 * NATIVEBOOT2-B4 CUSTOMLDD1
 * Diagnostic startup Custom.ldd bridge.
 */
#pragma once

#include <kernel/ldd.h>

namespace eka2l1::ldd {
    constexpr const char *CUSTOM_STARTUP_FACTORY_NAME = "custom";

    class custom_startup_channel : public channel {
    public:
        custom_startup_channel(kernel_system *kern, system *sys, epoc::version ver);

        std::int32_t do_control(kernel::thread *thread, std::uint32_t opcode,
            eka2l1::ptr<void> arg1, eka2l1::ptr<void> arg2) override;
        std::int32_t do_request(epoc::notify_info info, std::uint32_t opcode,
            eka2l1::ptr<void> arg1, eka2l1::ptr<void> arg2, bool is_supervisor) override;
    };

    class custom_startup_factory : public factory {
    public:
        custom_startup_factory(kernel_system *kern, system *sys);

        void install() override;
        std::unique_ptr<channel> make_channel(epoc::version ver) override;
    };
}
'''

CUSTOM_CPP = r'''/*
 * NATIVEBOOT2-B4 CUSTOMLDD1
 * Diagnostic startup Custom.ldd bridge.
 */
#include <ldd/custom/custom.h>

#include <common/log.h>
#include <kernel/process.h>
#include <kernel/thread.h>
#include <utils/err.h>

namespace eka2l1::ldd {
    custom_startup_factory::custom_startup_factory(kernel_system *kern, system *sys)
        : factory(kern, sys) {
    }

    void custom_startup_factory::install() {
        obj_name = CUSTOM_STARTUP_FACTORY_NAME;
        LOG_WARN(LDD_MMCIF, "[NBOOT2][CUSTOM_INSTALL] factory={}", obj_name);
    }

    std::unique_ptr<channel> custom_startup_factory::make_channel(epoc::version ver) {
        LOG_WARN(LDD_MMCIF, "[NBOOT2][CUSTOM_CHANNEL] create");
        return std::make_unique<custom_startup_channel>(kern, sys_, ver);
    }

    custom_startup_channel::custom_startup_channel(kernel_system *kern, system *sys, epoc::version ver)
        : channel(kern, sys, ver) {
    }

    std::int32_t custom_startup_channel::do_control(kernel::thread *thread,
        const std::uint32_t opcode, const eka2l1::ptr<void> arg1,
        const eka2l1::ptr<void> arg2) {
        kernel::process *process = thread ? thread->owning_process() : nullptr;
        LOG_WARN(LDD_MMCIF,
            "[NBOOT2][CUSTOM_CONTROL] process={} opcode={} arg1=0x{:08X} arg2=0x{:08X}",
            process ? process->name() : std::string("<none>"), opcode,
            arg1.ptr_address(), arg2.ptr_address());

        // Diagnostic-first adapter: Custom.ldd is a vendor hardware/startup
        // dependency. Return presence/success until a concrete opcode proves
        // that guest-visible output or richer semantics are required.
        return epoc::error_none;
    }

    std::int32_t custom_startup_channel::do_request(epoc::notify_info info,
        const std::uint32_t opcode, const eka2l1::ptr<void> arg1,
        const eka2l1::ptr<void> arg2, const bool is_supervisor) {
        LOG_WARN(LDD_MMCIF,
            "[NBOOT2][CUSTOM_REQUEST] opcode={} arg1=0x{:08X} arg2=0x{:08X} supervisor={} completion=KErrNone",
            opcode, arg1.ptr_address(), arg2.ptr_address(), is_supervisor ? 1 : 0);
        info.complete(epoc::error_none);
        return epoc::error_none;
    }
}
'''

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_collection(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "ldd/custom/custom.h" in text:
        return

    text = replace_once(
        text,
        "#include <ldd/nokiaisc/nokiaisc.h>\n",
        "#include <ldd/nokiaisc/nokiaisc.h>\n#include <ldd/custom/custom.h>\n",
        "collection custom include")

    text = replace_once(
        text,
        "    FACTORY_DECLARE(nokiaisc_factory)\n",
        "    FACTORY_DECLARE(nokiaisc_factory)\n    FACTORY_DECLARE(custom_startup_factory)\n",
        "collection custom factory declare")

    text = replace_once(
        text,
        '        FACTORY_REGISTER("nokiaiscdriver", nokiaisc_factory),\n',
        '        FACTORY_REGISTER("nokiaiscdriver", nokiaisc_factory),\n'
        '        // NATIVEBOOT2-B4: RM-356 EStart requires Custom.ldd after NokiaISC.\n'
        '        FACTORY_REGISTER("custom", custom_startup_factory),\n',
        "collection custom factory register")

    path.write_text(text, encoding="utf-8")

def patch_cmake(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "include/ldd/custom/custom.h" in text:
        return

    text = replace_once(
        text,
        "        include/ldd/nokiaisc/nokiaisc.h\n",
        "        include/ldd/nokiaisc/nokiaisc.h\n        include/ldd/custom/custom.h\n",
        "cmake custom header")

    text = replace_once(
        text,
        "        src/nokiaisc/nokiaisc.cpp\n",
        "        src/nokiaisc/nokiaisc.cpp\n        src/custom/custom.cpp\n",
        "cmake custom source")

    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b4_customldd1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    collection = up / "src/emu/ldd/src/collection.cpp"
    cmake = up / "src/emu/ldd/CMakeLists.txt"
    header = up / "src/emu/ldd/include/ldd/custom/custom.h"
    source = up / "src/emu/ldd/src/custom/custom.cpp"
    nokiaisc = up / "src/emu/ldd/src/nokiaisc/nokiaisc.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (collection, cmake, nokiaisc, svc, state, root):
        if not p.is_file():
            fail(f"missing B3 baseline file: {p}")

    if "[NBOOT2][NOKIAISC_INIT_COMPLETE]" not in nokiaisc.read_text(encoding="utf-8"):
        fail("B3 NokiaISC completion marker missing")
    if "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI" not in svc.read_text(encoding="utf-8"):
        fail("B2 EPOC94 channel ABI marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub UI marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    header.parent.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    header.write_text(CUSTOM_H, encoding="utf-8")
    source.write_text(CUSTOM_CPP, encoding="utf-8")

    patch_collection(collection)
    patch_cmake(cmake)

    coll_body = collection.read_text(encoding="utf-8")
    cmake_body = cmake.read_text(encoding="utf-8")
    source_body = source.read_text(encoding="utf-8")

    if 'FACTORY_REGISTER("custom", custom_startup_factory)' not in coll_body:
        fail("custom factory registration missing")
    if "src/custom/custom.cpp" not in cmake_body:
        fail("custom source missing from CMake")
    for gate in ("[NBOOT2][CUSTOM_INSTALL]", "[NBOOT2][CUSTOM_CHANNEL]",
                 "[NBOOT2][CUSTOM_CONTROL]", "[NBOOT2][CUSTOM_REQUEST]"):
        if gate not in source_body:
            fail(f"custom trace gate missing: {gate}")

    svc_body = svc.read_text(encoding="utf-8")
    a = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = svc_body.find("\n    };", a)
    v94 = svc_body[a:b]
    if "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)" not in v94:
        fail("v94 0x0A mapping lost")
    if "BRIDGE_REGISTER(0x83, logical_channel_create_v95)" not in v94:
        fail("v94 0x83 mapping lost")
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)" not in v94:
        fail("EPOC94 0xAB invariant lost")
    if "BRIDGE_REGISTER(0xAC, message_kill)" not in v94:
        fail("EPOC94 0xAC invariant lost")

    print("NATIVEBOOT2-B4 CUSTOMLDD1 applied")
    print("Custom.ldd=factory_custom_HLE_DIAGNOSTIC")
    print("Custom_control=trace_and_KErrNone")
    print("Custom_request=trace_complete_KErrNone")
    print("NOKIAISC2=PRESERVED")
    print("EP94_0x83_0x0A=PRESERVED")
    print("EMUHUB1=PRESERVED")
    print("NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
