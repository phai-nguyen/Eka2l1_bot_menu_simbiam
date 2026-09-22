#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B40 LOADERPDD1 after B39.

B39 device evidence proved that the first canonical eiksrvs instance stalls
at !Loader opcode 4 while CEikServAppUiBase::InitializeL calls
User::LoadPhysicalDevice("EUART1"). The old dispatcher drops this synchronous
unknown IPC, so initialization never reaches EikServAppUiSessionFactory setup.

B40 narrowly ports upstream EKA2L1 commit
0987745cc0bde96511fce2a4bfefcfd8fbced3dc:
- declare Loader::LoadPhysicalDevice;
- validate/read descriptor argument 1;
- complete a valid HLE-backed PDD load with KErrNone;
- register ELoadPhysicalDevice / opcode 4;
- add one narrow runtime marker for entry/completion.

It deliberately does NOT port the generic unknown-IPC completion change from
9f28c76fe0f54f43a39319da5f4042c853505807 and does not alter FEP/Leave,
WindowServer, scheduler, SVC, rooted-library resolution, or iOS shutdown.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B40-LOADERPDD1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b40_loaderpdd1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/loader/loader.h"
    src=up/"src/emu/services/src/loader/loader.cpp"
    op=up/"src/emu/services/include/services/loader/op.h"
    context=up/"src/emu/services/src/context.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"

    for p in (hdr,src,op,context,svc,kern):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    h=hdr.read_text(encoding="utf-8")
    s=src.read_text(encoding="utf-8")
    o=op.read_text(encoding="utf-8")
    ct=context.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")

    # Require the exact proven B39/B30 lineage before functional change.
    for needle,text,name in (
        ("[NBOOT2][LDR_LIB_REQUEST]",s,"B29 loader diagnostics"),
        ("[NBOOT2][EIKFEP_STATE]",sv,"B39 FEP diagnostics"),
        ("[NBOOT2][EIKPOSTLEAVE_AV_FRAME]",ke,"B39 AV diagnostics"),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")

    if "ELoadPhysicalDevice = 4" not in o:
        fail("Loader opcode map does not contain ELoadPhysicalDevice = 4")

    # B40 must not absorb the generic unknown-IPC completion commit 9f28c76f.
    old_unknown='LOG_WARN(SERVICE_TRACK, "Unimplemented IPC call: 0x{:x} for server: {}", func, obj_name);'
    if old_unknown not in ct:
        fail("legacy unknown-IPC dispatcher anchor missing; refuse broad semantic change")
    unknown_pos=ct.find(old_unknown)
    if "context.complete(epoc::error_not_supported);" in ct[unknown_pos:unknown_pos+800]:
        fail("generic unknown-IPC completion already present; B40 scope violated")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    marker="[NBOOT2][LOADER_PDD]"
    decl="void load_physical_device(service::ipc_context &context);"
    reg='REGISTER_IPC(loader_server, load_physical_device, ELoadPhysicalDevice, "Loader::LoadPhysicalDevice");'
    present=[x for x in (marker,decl,reg) if x in h+"\n"+s]
    if present:
        if marker in s and decl in h and reg in s:
            print(f"{MARK}: already applied")
            return
        fail("partial/foreign B40 state: "+", ".join(present))

    hdr_old='''        void load_logical_device(service::ipc_context &context);

        void get_info_from_header(service::ipc_context &context);
'''
    hdr_new='''        void load_logical_device(service::ipc_context &context);

        void load_physical_device(service::ipc_context &context);

        void get_info_from_header(service::ipc_context &context);
'''
    h=replace_once(h,hdr_old,hdr_new,"B40 loader declaration")

    func_old='''    void loader_server::load_logical_device(service::ipc_context &context) {
        std::optional<utf16_str> ldd_name = context.get_argument_value<utf16_str>(1);
        if (!ldd_name.has_value()) {
            context.complete(epoc::error_argument);
            return;
        }

        LOG_TRACE(SERVICE_LOADER, "Trying to load LDD {}", common::ucs2_to_utf8(ldd_name.value()));
        context.complete(epoc::error_none);
    }

    void loader_server::load_locale(service::ipc_context &context) {
'''
    func_new='''    void loader_server::load_logical_device(service::ipc_context &context) {
        std::optional<utf16_str> ldd_name = context.get_argument_value<utf16_str>(1);
        if (!ldd_name.has_value()) {
            context.complete(epoc::error_argument);
            return;
        }

        LOG_TRACE(SERVICE_LOADER, "Trying to load LDD {}", common::ucs2_to_utf8(ldd_name.value()));
        context.complete(epoc::error_none);
    }

    void loader_server::load_physical_device(service::ipc_context &context) {
        std::optional<utf16_str> pdd_name = context.get_argument_value<utf16_str>(1);
        if (!pdd_name.has_value()) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][LOADER_PDD] phase=invalid_descriptor result={}",
                epoc::error_argument);
            context.complete(epoc::error_argument);
            return;
        }

        const std::string pdd_name8 = common::ucs2_to_utf8(pdd_name.value());
        LOG_WARN(SERVICE_LOADER,
            "[NBOOT2][LOADER_PDD] phase=enter name={}",
            pdd_name8);

        // Upstream 0987745: the physical device is represented by HLE here,
        // so a valid PDD load succeeds just like LoadLogicalDevice above.
        LOG_WARN(SERVICE_LOADER,
            "[NBOOT2][LOADER_PDD] phase=complete name={} result={}",
            pdd_name8, epoc::error_none);
        context.complete(epoc::error_none);
    }

    void loader_server::load_locale(service::ipc_context &context) {
'''
    s=replace_once(s,func_old,func_new,"B40 LoadPhysicalDevice handler")

    reg_old='''        REGISTER_IPC(loader_server, load_locale, ELoadLocale, "Loader::LoadLocale");
        REGISTER_IPC(loader_server, load_logical_device, ELoadLogicalDevice, "Loader::LoadLogicalDevice");
    }
}
'''
    reg_new='''        REGISTER_IPC(loader_server, load_locale, ELoadLocale, "Loader::LoadLocale");
        REGISTER_IPC(loader_server, load_logical_device, ELoadLogicalDevice, "Loader::LoadLogicalDevice");
        REGISTER_IPC(loader_server, load_physical_device, ELoadPhysicalDevice, "Loader::LoadPhysicalDevice");
    }
}
'''
    s=replace_once(s,reg_old,reg_new,"B40 opcode-4 registration")

    # Scope guards after transformation.
    for needle in (
        marker,
        "phase=enter",
        "phase=complete",
        "context.complete(epoc::error_none);",
        reg,
    ):
        if needle not in s:
            fail(f"post-apply B40 semantic missing: {needle}")
    if decl not in h:
        fail("post-apply loader declaration missing")

    if old_unknown not in ct:
        fail("generic unknown-IPC dispatcher changed unexpectedly")
    if "context.complete(epoc::error_not_supported);" in ct[unknown_pos:unknown_pos+800]:
        fail("generic unknown-IPC completion changed unexpectedly")

    hdr.write_text(h,encoding="utf-8")
    src.write_text(s,encoding="utf-8")

    print(f"{MARK}: applied")
    print("scope=LOADER_PDD_OPCODE4_ONLY")
    print("upstream_reference=0987745cc0bde96511fce2a4bfefcfd8fbced3dc")
    print("ELoadPhysicalDevice=4")
    print("valid_pdd_completion=KErrNone")
    print("generic_unknown_ipc=UNCHANGED")
    print("FEP_LEAVE_WSCHED_SVC_IOS_EXIT=UNCHANGED")
    print("B34_B35_B36_B37_B38_B39=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
