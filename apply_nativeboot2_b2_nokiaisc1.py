#!/usr/bin/env python3
"""NATIVEBOOT2-B2 NOKIAISC1.

Apply on top of NATIVEBOOT2 EMUHUB1 (stable MENUUI36 frontend).

Observed RM-356 EStart blocker:
  NokiaISC loaded
  SVCMISS 0x83
  SVCMISS 0x0A

For EPOC 9.4 these are EExecChannelCreate and EExecChannelRequest.
The baseline already contains the EPOC9.x channel ABI implementation, but only
registers it in the v95 extras table. This patch:
- registers 0x83 -> logical_channel_create_v95 for the v94 map,
- registers 0x0A -> logical_channel_request_v95 for the v94 map,
- adds an inert NokiaISC HLE logical-device factory used during phone startup.

Do not alter the established EPOC94 message invariant:
  0xAA unmapped, 0xAB=message_construct, 0xAC=message_kill.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B2-NOKIAISC1"

NOKIAISC_H = r'''/*
 * NATIVEBOOT2-B2 NOKIAISC1
 * Minimal Nokia ISC logical-device bridge for firmware startup.
 */
#pragma once

#include <kernel/ldd.h>

namespace eka2l1::ldd {
    constexpr const char *NOKIA_ISC_FACTORY_NAME = "nokiaiscdriver";

    class nokiaisc_channel : public channel {
    public:
        nokiaisc_channel(kernel_system *kern, system *sys, epoc::version ver);

        std::int32_t do_control(kernel::thread *thread, std::uint32_t opcode,
            eka2l1::ptr<void> arg1, eka2l1::ptr<void> arg2) override;
        std::int32_t do_request(epoc::notify_info info, std::uint32_t opcode,
            eka2l1::ptr<void> arg1, eka2l1::ptr<void> arg2, bool is_supervisor) override;
    };

    class nokiaisc_factory : public factory {
    public:
        nokiaisc_factory(kernel_system *kern, system *sys);

        void install() override;
        std::unique_ptr<channel> make_channel(epoc::version ver) override;
    };
}
'''

NOKIAISC_CPP = r'''/*
 * NATIVEBOOT2-B2 NOKIAISC1
 * Minimal Nokia ISC logical-device bridge for firmware startup.
 */
#include <ldd/nokiaisc/nokiaisc.h>

#include <common/log.h>
#include <kernel/thread.h>
#include <utils/err.h>

namespace eka2l1::ldd {
    nokiaisc_factory::nokiaisc_factory(kernel_system *kern, system *sys)
        : factory(kern, sys) {
    }

    void nokiaisc_factory::install() {
        obj_name = NOKIA_ISC_FACTORY_NAME;
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_INSTALL] factory={}", obj_name);
    }

    std::unique_ptr<channel> nokiaisc_factory::make_channel(epoc::version ver) {
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_CHANNEL] create");
        return std::make_unique<nokiaisc_channel>(kern, sys_, ver);
    }

    nokiaisc_channel::nokiaisc_channel(kernel_system *kern, system *sys, epoc::version ver)
        : channel(kern, sys, ver) {
    }

    std::int32_t nokiaisc_channel::do_control(kernel::thread *, const std::uint32_t opcode,
        const eka2l1::ptr<void>, const eka2l1::ptr<void>) {
        // The iPhone host has no Nokia baseband/secure-element transport.
        // EStart only needs the ISC channel to initialise far enough to hand
        // startup to domainSrv/SysStart, so expose a present inert device.
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_CONTROL] opcode={}", opcode);
        return epoc::error_none;
    }

    std::int32_t nokiaisc_channel::do_request(epoc::notify_info info, const std::uint32_t opcode,
        const eka2l1::ptr<void>, const eka2l1::ptr<void>, const bool) {
        LOG_WARN(LDD_MMCIF, "[NBOOT2][NOKIAISC_REQUEST] opcode={} completion=KErrNone", opcode);
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

def patch_svc(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI" in text:
        return

    start = text.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    if start < 0:
        fail("svc v94 map not found")
    end = text.find("\n    };", start)
    if end < 0:
        fail("svc v94 map end not found")

    before = text[:start]
    block = text[start:end]
    after = text[end:]

    if "BRIDGE_REGISTER(0x0A," in block or "BRIDGE_REGISTER(0x83," in block:
        fail("v94 channel SVC slots already occupied")

    tick_anchor = "        BRIDGE_REGISTER(0x05, tick_count),\n"
    tick_new = tick_anchor + """        // NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI:
        // RM-356 EStart uses EPOC9.4 ChannelRequest at slow SVC 0x0A.
        BRIDGE_REGISTER(0x0A, logical_channel_request_v95),
"""
    block = replace_once(block, tick_anchor, tick_new, "v94 channel request 0x0A")

    timer_anchor = "        BRIDGE_REGISTER(0x84, timer_create),\n"
    timer_new = """        // NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI:
        // RM-356 EStart uses EPOC9.4 ChannelCreate at slow SVC 0x83.
        BRIDGE_REGISTER(0x83, logical_channel_create_v95),
""" + timer_anchor
    block = replace_once(block, timer_anchor, timer_new, "v94 channel create 0x83")

    # Preserve the long-standing RM-356 message ABI invariant.
    if "BRIDGE_REGISTER(0xAA," in block:
        fail("EPOC94 invariant violated: 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)," not in block:
        fail("EPOC94 invariant violated: 0xAB must be message_construct")
    if "BRIDGE_REGISTER(0xAC, message_kill)," not in block:
        fail("EPOC94 invariant violated: 0xAC must be message_kill")

    path.write_text(before + block + after, encoding="utf-8")

def patch_collection(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "ldd/nokiaisc/nokiaisc.h" in text:
        return

    text = replace_once(
        text,
        "#include <ldd/mmcif/mmcif.h>\n",
        "#include <ldd/mmcif/mmcif.h>\n#include <ldd/nokiaisc/nokiaisc.h>\n",
        "collection nokiaisc include")

    text = replace_once(
        text,
        "    FACTORY_DECLARE(old_camera_factory)\n",
        "    FACTORY_DECLARE(old_camera_factory)\n    FACTORY_DECLARE(nokiaisc_factory)\n",
        "collection nokiaisc factory declare")

    text = replace_once(
        text,
        '        FACTORY_REGISTER("cameraldd", old_camera_factory),\n',
        '        FACTORY_REGISTER("cameraldd", old_camera_factory),\n'
        '        // NATIVEBOOT2-B2: Nokia 5800 EStart opens this after loading NokiaISC.\n'
        '        FACTORY_REGISTER("nokiaiscdriver", nokiaisc_factory),\n',
        "collection nokiaisc factory register")

    path.write_text(text, encoding="utf-8")

def patch_cmake(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "include/ldd/nokiaisc/nokiaisc.h" in text:
        return

    text = replace_once(
        text,
        "        include/ldd/mmcif/mmcif.h\n",
        "        include/ldd/mmcif/mmcif.h\n        include/ldd/nokiaisc/nokiaisc.h\n",
        "cmake nokiaisc header")

    text = replace_once(
        text,
        "        src/mmcif/mmcif.cpp\n",
        "        src/mmcif/mmcif.cpp\n        src/nokiaisc/nokiaisc.cpp\n",
        "cmake nokiaisc source")

    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b2_nokiaisc1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    svc = up / "src/emu/kernel/src/svc.cpp"
    collection = up / "src/emu/ldd/src/collection.cpp"
    cmake = up / "src/emu/ldd/CMakeLists.txt"
    header = up / "src/emu/ldd/include/ldd/nokiaisc/nokiaisc.h"
    source = up / "src/emu/ldd/src/nokiaisc/nokiaisc.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (svc, collection, cmake, state, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("NATIVEBOOT2 EMUHUB1 baseline marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub UI baseline marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_svc(svc)

    header.parent.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    header.write_text(NOKIAISC_H, encoding="utf-8")
    source.write_text(NOKIAISC_CPP, encoding="utf-8")

    patch_collection(collection)
    patch_cmake(cmake)

    svc_body = svc.read_text(encoding="utf-8")
    v94_start = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    v94_end = svc_body.find("\n    };", v94_start)
    v94 = svc_body[v94_start:v94_end]

    required = [
        "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI",
        "BRIDGE_REGISTER(0x0A, logical_channel_request_v95)",
        "BRIDGE_REGISTER(0x83, logical_channel_create_v95)",
        "BRIDGE_REGISTER(0xAB, message_construct)",
        "BRIDGE_REGISTER(0xAC, message_kill)",
    ]
    for gate in required:
        if gate not in v94:
            fail(f"v94 gate missing: {gate}")
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("v94 0xAA unexpectedly mapped")

    coll_body = collection.read_text(encoding="utf-8")
    if 'FACTORY_REGISTER("nokiaiscdriver", nokiaisc_factory)' not in coll_body:
        fail("NokiaISC factory registration missing")
    if "[NBOOT2][NOKIAISC_CONTROL]" not in source.read_text(encoding="utf-8"):
        fail("NokiaISC runtime trace marker missing")

    print("NATIVEBOOT2-B2 NOKIAISC1 applied")
    print("EP94_SVC_0x83=logical_channel_create_v95")
    print("EP94_SVC_0x0A=logical_channel_request_v95")
    print("LDD_nokiaiscdriver=HLE_INERT_PRESENT")
    print("EPOC94_0xAA=UNMAPPED")
    print("EPOC94_0xAB=message_construct")
    print("EPOC94_0xAC=message_kill")
    print("EMUHUB1=PRESERVED")
    print("NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
