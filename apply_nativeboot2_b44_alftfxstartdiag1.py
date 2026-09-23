#!/usr/bin/env python3
"""NATIVEBOOT2 B44 ALFTFXSTARTDIAG1.

Source-guided, diagnostic-only instrumentation for the Nokia 5800 ALF/TFX
provider startup chain. No guest-visible behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B44-ALFTFXSTARTDIAG1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep(text, old, new, label):
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def rep_between(text, begin, end, old, new, label):
    b=text.find(begin)
    e=text.find(end,b+1)
    if b < 0 or e < 0:
        fail(f"{label}: function bounds not found")
    region=text[b:e]
    count=region.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor in bounded region, found {count}")
    region=region.replace(old,new,1)
    return text[:b]+region+text[e:]

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b44_alftfxstartdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    applist=up/"src/emu/services/src/applist/applist.cpp"
    files=up/"src/emu/services/src/fs/files.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"

    for p in (svc,loader,applist,files,sa):
        if not p.is_file():
            fail(f"missing source file: {p}")

    s=svc.read_text()
    l=loader.read_text()
    a=applist.read_text()
    f=files.read_text()
    sat=sa.read_text()

    for marker,text in (
        ("[NBOOT2][TFX_SESSION]",s),
        ("[NBOOT2][TFX_RESOLVE]",l),
        ("[NBOOT2][SA_HWRM_ABI]",sat),
        ("[NBOOT2][LOADER_PDD]",l),
    ):
        if marker not in text:
            fail("missing baseline "+marker)

    if "[NBOOT2][ALF_SESSION]" in s:
        print(MARK+": already applied")
        return

    # ------------------------------------------------------------------
    # Kernel session/provider + P&S diagnostics
    # ------------------------------------------------------------------
    anchor='''        kernel::thread *b43_thr = kern->crr_thread();
        auto *b43_cpu = kern->get_cpu();

        if (b43_tfx && pr && b43_thr && b43_cpu) {
'''
    block='''        kernel::thread *b43_thr = kern->crr_thread();
        auto *b43_cpu = kern->get_cpu();

        // NATIVEBOOT2-B44 ALFTFXSTARTDIAG1: observe the ALF endpoints that
        // source-guided TFX startup can use. No session result is changed.
        const bool b44_alf_session = kern->get_config()->native_phone_boot
            && (server_name == "alfstreamerserver"
                || server_name == "10282845_10282845_AppServer"
                || server_name == "10282848_10282848_AppServer");
        if (b44_alf_session) {
            LOG_WARN(KERNEL,
                "[NBOOT2][ALF_SESSION] phase=request process={} thread={} server={} msg_slots={} mode={} sec=0x{:08X} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b43_thr ? b43_thr->name() : std::string("<null>"),
                server_name, msg_slot, mode, sec.ptr_address());
        }

        if (b43_tfx && pr && b43_thr && b43_cpu) {
'''
    s=rep(s,anchor,block,"B44 ALF session request")

    anchor='''        server_ptr server = kern->get_by_name<service::server>(server_name);

        if (!server) {
'''
    block='''        server_ptr server = kern->get_by_name<service::server>(server_name);

        if (b44_alf_session) {
            LOG_WARN(KERNEL,
                "[NBOOT2][ALF_SESSION] phase=lookup process={} thread={} server={} found={} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b43_thr ? b43_thr->name() : std::string("<null>"),
                server_name, server ? 1 : 0);
        }

        if (!server) {
'''
    s=rep_between(
        s,
        "    BRIDGE_FUNC(std::int32_t, session_create,",
        "    BRIDGE_FUNC(std::int32_t, session_create_from_handle,",
        anchor, block, "B44 ALF session lookup")

    anchor='''            if (b43_tfx) {
                b43_tfx_miss.valid = true;
                LOG_WARN(KERNEL,
                    "[NBOOT2][TFX_SESSION] phase=missing process={} thread={} server={} result={} behavior=UNCHANGED_KErrNotFound",
                    pr ? pr->name() : std::string("<null>"),
                    b43_thr ? b43_thr->name() : std::string("<null>"),
                    server_name, epoc::error_not_found);
            }
            return epoc::error_not_found;
'''
    block='''            if (b43_tfx) {
                b43_tfx_miss.valid = true;
                LOG_WARN(KERNEL,
                    "[NBOOT2][TFX_SESSION] phase=missing process={} thread={} server={} result={} behavior=UNCHANGED_KErrNotFound",
                    pr ? pr->name() : std::string("<null>"),
                    b43_thr ? b43_thr->name() : std::string("<null>"),
                    server_name, epoc::error_not_found);
            }
            if (b44_alf_session) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][ALF_SESSION] phase=missing process={} thread={} server={} result={} behavior=OBSERVE_ONLY",
                    pr ? pr->name() : std::string("<null>"),
                    b43_thr ? b43_thr->name() : std::string("<null>"),
                    server_name, epoc::error_not_found);
            }
            return epoc::error_not_found;
'''
    s=rep(s,anchor,block,"B44 ALF missing")

    anchor='''        if (b43_tfx) {
            b43_tfx_miss.valid = false;
            LOG_WARN(KERNEL,
                "[NBOOT2][TFX_SESSION] phase=found process={} thread={} server={} server_hle={} behavior=UNCHANGED",
                pr ? pr->name() : std::string("<null>"),
                b43_thr ? b43_thr->name() : std::string("<null>"),
                server_name, server->is_hle() ? 1 : 0);
        }

        return do_create_session_from_server(kern, server, msg_slot, sec, mode);
'''
    block='''        if (b43_tfx) {
            b43_tfx_miss.valid = false;
            LOG_WARN(KERNEL,
                "[NBOOT2][TFX_SESSION] phase=found process={} thread={} server={} server_hle={} behavior=UNCHANGED",
                pr ? pr->name() : std::string("<null>"),
                b43_thr ? b43_thr->name() : std::string("<null>"),
                server_name, server->is_hle() ? 1 : 0);
        }
        if (b44_alf_session) {
            LOG_WARN(KERNEL,
                "[NBOOT2][ALF_SESSION] phase=found process={} thread={} server={} server_hle={} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b43_thr ? b43_thr->name() : std::string("<null>"),
                server_name, server->is_hle() ? 1 : 0);
        }

        return do_create_session_from_server(kern, server, msg_slot, sec, mode);
'''
    s=rep(s,anchor,block,"B44 ALF found")

    # Observe successful ALF endpoint registration.
    anchor='''                LOG_WARN(KERNEL,
                    "[NBOOT2][TFX_SERVER_REGISTER] process={} server={} handle={} mode={} behavior=OBSERVE_ONLY",
                    crr_pr->name(), server_name, handle, mode);
            }
'''
    block='''                LOG_WARN(KERNEL,
                    "[NBOOT2][TFX_SERVER_REGISTER] process={} server={} handle={} mode={} behavior=OBSERVE_ONLY",
                    crr_pr->name(), server_name, handle, mode);
            }
            if (kern->get_config()->native_phone_boot
                && (server_name == "alfstreamerserver"
                    || server_name == "10282845_10282845_AppServer"
                    || server_name == "10282848_10282848_AppServer")) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][ALF_SERVER_REGISTER] process={} server={} handle={} mode={} behavior=OBSERVE_ONLY",
                    crr_pr ? crr_pr->name() : std::string("<null>"),
                    server_name, handle, mode);
            }
'''
    s=rep(s,anchor,block,"B44 ALF server register")

    # TFX P&S helper. Source ground truth:
    # category=KPSUidAvkonDomain=0x10207218, key=KAknTfxServerStatus=2.
    anchor='''    /*****************************/
    /* PROPERTY */
    /****************************/

'''
    block='''    /*****************************/
    /* PROPERTY */
    /****************************/

    static bool b44_tfx_ps_target(const std::int32_t cage, const std::int32_t key) {
        return cage == static_cast<std::int32_t>(0x10207218)
            && key == static_cast<std::int32_t>(0x00000002);
    }

    static void b44_tfx_ps_log(kernel_system *kern, const char *op, const char *phase,
        const std::int32_t cage, const std::int32_t key, const std::int32_t old_value,
        const std::int32_t new_value, const std::int32_t result) {
        if (!kern || !kern->get_config()->native_phone_boot || !b44_tfx_ps_target(cage, key)) {
            return;
        }

        kernel::process *pr = kern->crr_process();
        kernel::thread *thr = kern->crr_thread();
        LOG_WARN(KERNEL,
            "[NBOOT2][TFX_PS] op={} phase={} category=0x{:08X} key=0x{:08X} old=0x{:08X} new=0x{:08X} result={} process={} thread={} behavior=OBSERVE_ONLY",
            op, phase, static_cast<std::uint32_t>(cage), static_cast<std::uint32_t>(key),
            static_cast<std::uint32_t>(old_value), static_cast<std::uint32_t>(new_value), result,
            pr ? pr->name() : std::string("<null>"),
            thr ? thr->name() : std::string("<null>"));
    }

'''
    s=rep(s,anchor,block,"B44 P&S helper")

    # Find/Get direct.
    anchor='''    BRIDGE_FUNC(std::int32_t, property_find_get_int, std::int32_t cage, std::int32_t key, eka2l1::ptr<std::int32_t> value) {
        property_ptr prop = kern->get_prop(cage, key);

        if (!prop || !prop->is_defined()) {
            LOG_WARN(KERNEL, "Property not found: category = 0x{:x}, key = 0x{:x}", cage, key);
            return epoc::error_not_found;
        }

        std::int32_t *val_ptr = value.get(kern->crr_process());
        *val_ptr = prop->get_int();

        return epoc::error_none;
    }
'''
    block='''    BRIDGE_FUNC(std::int32_t, property_find_get_int, std::int32_t cage, std::int32_t key, eka2l1::ptr<std::int32_t> value) {
        property_ptr prop = kern->get_prop(cage, key);

        if (!prop || !prop->is_defined()) {
            LOG_WARN(KERNEL, "Property not found: category = 0x{:x}, key = 0x{:x}", cage, key);
            b44_tfx_ps_log(kern, "find_get", "missing", cage, key, 0, 0, epoc::error_not_found);
            return epoc::error_not_found;
        }

        std::int32_t *val_ptr = value.get(kern->crr_process());
        *val_ptr = prop->get_int();
        b44_tfx_ps_log(kern, "find_get", "result", cage, key, *val_ptr, *val_ptr, epoc::error_none);

        return epoc::error_none;
    }
'''
    s=rep(s,anchor,block,"B44 P&S find_get")

    # Attach.
    anchor='''        if (property_ref_handle_and_obj.first == kernel::INVALID_HANDLE) {
            return epoc::error_general;
        }

        return property_ref_handle_and_obj.first;
    }

    BRIDGE_FUNC(std::int32_t, property_define'''
    block='''        if (property_ref_handle_and_obj.first == kernel::INVALID_HANDLE) {
            b44_tfx_ps_log(kern, "attach", "result", cage, val, 0, 0, epoc::error_general);
            return epoc::error_general;
        }

        b44_tfx_ps_log(kern, "attach", "result", cage, val,
            prop && prop->is_defined() ? prop->get_int() : 0,
            prop && prop->is_defined() ? prop->get_int() : 0,
            static_cast<std::int32_t>(property_ref_handle_and_obj.first));
        return property_ref_handle_and_obj.first;
    }

    BRIDGE_FUNC(std::int32_t, property_define'''
    s=rep(s,anchor,block,"B44 P&S attach")

    # Define.
    anchor='''        prop->define(prop_type, info->size);

        return epoc::error_none;
    }

    BRIDGE_FUNC(std::int32_t, property_delete'''
    block='''        prop->define(prop_type, info->size);
        b44_tfx_ps_log(kern, "define", "result", cage, key, 0,
            prop_type == service::property_type::int_data ? prop->get_int() : 0,
            epoc::error_none);

        return epoc::error_none;
    }

    BRIDGE_FUNC(std::int32_t, property_delete'''
    s=rep(s,anchor,block,"B44 P&S define")

    # Handle-based set.
    anchor='''    BRIDGE_FUNC(std::int32_t, property_set_int, kernel::handle h, std::int32_t val) {
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop || !prop->get_property_object()->is_defined()) {
            return epoc::error_not_found;
        }

        bool res = prop->get_property_object()->set_int(val);

        if (!res) {
            return epoc::error_argument;
        }

        return epoc::error_none;
    }
'''
    block='''    BRIDGE_FUNC(std::int32_t, property_set_int, kernel::handle h, std::int32_t val) {
        property_ref_ptr prop = kern->get<service::property_reference>(h);

        if (!prop || !prop->get_property_object()->is_defined()) {
            return epoc::error_not_found;
        }

        service::property *b44_obj = prop->get_property_object();
        const std::int32_t b44_old = b44_obj->get_int();
        bool res = b44_obj->set_int(val);

        if (!res) {
            b44_tfx_ps_log(kern, "set", "result", b44_obj->first, b44_obj->second,
                b44_old, val, epoc::error_argument);
            return epoc::error_argument;
        }

        b44_tfx_ps_log(kern, "set", "result", b44_obj->first, b44_obj->second,
            b44_old, val, epoc::error_none);
        return epoc::error_none;
    }
'''
    s=rep(s,anchor,block,"B44 P&S set")

    # Handle-based get. Use bounded text surgery because prior milestones may
    # have changed the exact error-handling body.
    b44_get_begin="    BRIDGE_FUNC(std::int32_t, property_get_int,"
    b44_get_end="    BRIDGE_FUNC(std::int32_t, property_get_bin"
    b=s.find(b44_get_begin)
    e=s.find(b44_get_end,b+1)
    if b < 0 or e < 0:
        fail("B44 P&S get: function bounds not found")
    region=s[b:e]
    get_anchor='''        *value_ptr.get(pr) = prop->get_property_object()->get_int();
'''
    get_insert='''        *value_ptr.get(pr) = prop->get_property_object()->get_int();
        service::property *b44_obj = prop->get_property_object();
        if (b44_obj && b44_tfx_ps_target(b44_obj->first, b44_obj->second)) {
            b44_tfx_ps_log(kern, "get", "read", b44_obj->first, b44_obj->second,
                b44_obj->get_int(), b44_obj->get_int(), epoc::error_none);
        }
'''
    if region.count(get_anchor) != 1:
        fail(f"B44 P&S get: expected read anchor once, found {region.count(get_anchor)}")
    region=region.replace(get_anchor,get_insert,1)
    s=s[:b]+region+s[e:]

    # Direct find/set.
    anchor='''    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
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
'''
    block='''    BRIDGE_FUNC(std::int32_t, property_find_set_int, std::int32_t cage, std::int32_t key, std::int32_t value) {
        property_ptr prop = kern->get_prop(cage, key);

        if (!prop || !prop->is_defined()) {
            b44_tfx_ps_log(kern, "find_set", "missing", cage, key, 0, value, epoc::error_not_found);
            return epoc::error_not_found;
        }

        const std::int32_t b44_old = prop->get_int();
        const bool res = prop->set(value);

        if (!res) {
            b44_tfx_ps_log(kern, "find_set", "result", cage, key, b44_old, value, epoc::error_argument);
            return epoc::error_argument;
        }

        b44_tfx_ps_log(kern, "find_set", "result", cage, key, b44_old, value, epoc::error_none);
        return epoc::error_none;
    }
'''
    s=rep(s,anchor,block,"B44 P&S find_set")

    # ------------------------------------------------------------------
    # Loader: exact TFX ECom DLL and Alfred process creation.
    # ------------------------------------------------------------------
    anchor='''        const bool b43_tfx_process =
            name_process.find("tfx") != std::string::npos || name_process.find("Tfx") != std::string::npos
            || name_process.find("alfred") != std::string::npos || name_process.find("Alfred") != std::string::npos;
        if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
'''
    block='''        const bool b43_tfx_process =
            name_process.find("tfx") != std::string::npos || name_process.find("Tfx") != std::string::npos
            || name_process.find("alfred") != std::string::npos || name_process.find("Alfred") != std::string::npos;
        const bool b44_alf_process =
            name_process == "alfredserver" || name_process == "alfredserver.exe"
            || name_process == "AlfredServer" || name_process == "AlfredServer.exe"
            || name_process == "alfserver" || name_process == "alfserver.exe"
            || name_process == "AlfServer" || name_process == "AlfServer.exe";
        if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
            kernel::process *caller = ctx.msg->own_thr ? ctx.msg->own_thr->owning_process() : nullptr;
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][ALF_PROC_CREATE] phase=request caller={} path={} file={} uid3=0x{:08X} stack=0x{:X} behavior=OBSERVE_ONLY",
                caller ? caller->name() : std::string("<null>"),
                b43_process_path, name_process, uid3, stack_size);
        }
        if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
'''
    l=rep(l,anchor,block,"B44 Alfred process request")

    anchor='''            if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][TFX_RESOLVE] kind=process phase=result path={} success=0 completion={} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found);
            }
            ctx.complete(epoc::error_not_found);
'''
    block='''            if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][TFX_RESOLVE] kind=process phase=result path={} success=0 completion={} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found);
            }
            if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=0 result={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found, uid3);
            }
            ctx.complete(epoc::error_not_found);
'''
    l=rep(l,anchor,block,"B44 Alfred process fail")

    anchor='''        if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][TFX_RESOLVE] kind=process phase=result path={} success=1 spawned={} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name());
        }

        process_ptr request_pr'''
    block='''        if (b43_tfx_process && ctx.sys->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][TFX_RESOLVE] kind=process phase=result path={} success=1 spawned={} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name());
        }
        if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
            const auto b44_uids = pr->get_uid_type();
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=1 result=0 spawned={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name(), static_cast<std::uint32_t>(std::get<2>(b44_uids)));
        }

        process_ptr request_pr'''
    l=rep(l,anchor,block,"B44 Alfred process success")

    anchor='''        const bool b43_tfx_library =
            lib_name.find("tfx") != std::string::npos || lib_name.find("Tfx") != std::string::npos
            || lib_name.find("alfred") != std::string::npos || lib_name.find("Alfred") != std::string::npos
            || lib_name.find("transition") != std::string::npos || lib_name.find("Transition") != std::string::npos;
        if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
'''
    block='''        const bool b43_tfx_library =
            lib_name.find("tfx") != std::string::npos || lib_name.find("Tfx") != std::string::npos
            || lib_name.find("alfred") != std::string::npos || lib_name.find("Alfred") != std::string::npos
            || lib_name.find("transition") != std::string::npos || lib_name.find("Transition") != std::string::npos;
        const bool b44_tfx_ecom_dll =
            lib_name.find("tfxsrvplugin") != std::string::npos
            || lib_name.find("TfxSrvPlugin") != std::string::npos
            || lib_name.find("TFXSRVPLUGIN") != std::string::npos;
        if (b44_tfx_ecom_dll && ctx.sys->get_config()->native_phone_boot) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][TFX_ECOM_DLL] phase=request process={} path={} file={} expected_uid3=0x10282DBA behavior=OBSERVE_ONLY",
                own_pr ? own_pr->name() : std::string("<null>"), b43_lib_path, lib_name);
        }
        if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
'''
    l=rep(l,anchor,block,"B44 TFX DLL request")

    anchor='''            if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][TFX_RESOLVE] kind=library phase=result process={} path={} success=0 completion={} behavior=OBSERVE_ONLY",
                    own_pr ? own_pr->name() : std::string("<null>"), b43_lib_path, epoc::error_not_found);
            }
            LOG_WARN(SERVICE_LOADER,
'''
    block='''            if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][TFX_RESOLVE] kind=library phase=result process={} path={} success=0 completion={} behavior=OBSERVE_ONLY",
                    own_pr ? own_pr->name() : std::string("<null>"), b43_lib_path, epoc::error_not_found);
            }
            if (b44_tfx_ecom_dll && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][TFX_ECOM_DLL] phase=result process={} path={} success=0 result={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                    own_pr ? own_pr->name() : std::string("<null>"), b43_lib_path,
                    epoc::error_not_found, 0U);
            }
            LOG_WARN(SERVICE_LOADER,
'''
    l=rep(l,anchor,block,"B44 TFX DLL fail")

    anchor='''        LOG_TRACE(SERVICE_LOADER, "Loaded library: {}", lib_name);
        if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
'''
    block='''        LOG_TRACE(SERVICE_LOADER, "Loaded library: {}", lib_name);
        if (b44_tfx_ecom_dll && ctx.sys->get_config()->native_phone_boot) {
            const auto b44_uids = cs->get_uids();
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][TFX_ECOM_DLL] phase=result process={} path={} success=1 result=0 uid1=0x{:08X} uid2=0x{:08X} uid3=0x{:08X} handle=0x{:08X} behavior=OBSERVE_ONLY",
                own_pr ? own_pr->name() : std::string("<null>"), b43_lib_path,
                static_cast<std::uint32_t>(std::get<0>(b44_uids)),
                static_cast<std::uint32_t>(std::get<1>(b44_uids)),
                static_cast<std::uint32_t>(std::get<2>(b44_uids)),
                lib_handle_and_obj.first);
        }
        if (b43_tfx_library && ctx.sys->get_config()->native_phone_boot) {
'''
    l=rep(l,anchor,block,"B44 TFX DLL success")

    # ------------------------------------------------------------------
    # AppList/AppArc: ROM inventory, Alfred registration, GetAppInfo.
    # ------------------------------------------------------------------
    anchor='''    static bool commit_registry(std::vector<apa_app_registry> &regs, apa_app_registry &&reg) {
        auto same_path = std::find_if'''
    block='''    static bool commit_registry(std::vector<apa_app_registry> &regs, apa_app_registry &&reg) {
        const bool b44_alf_reg = reg.mandatory_info.uid == 0x10282845
            || common::ucs2_to_utf8(reg.rsc_path).find("alfredserver") != std::string::npos
            || common::ucs2_to_utf8(reg.rsc_path).find("AlfredServer") != std::string::npos;
        if (b44_alf_reg) {
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][ALF_APPARC_REG] phase=parsed uid=0x{:08X} rsc={} app_path={} drive={} behavior=OBSERVE_ONLY",
                reg.mandatory_info.uid, common::ucs2_to_utf8(reg.rsc_path),
                common::ucs2_to_utf8(reg.mandatory_info.app_path.to_std_string(nullptr)),
                static_cast<int>(reg.land_drive));
        }

        auto same_path = std::find_if'''
    a=rep(a,anchor,block,"B44 AppArc registry parsed")

    anchor='''            if (same_path->last_rsc_modified == reg.last_rsc_modified) {
                return false;
            }
'''
    block='''            if (same_path->last_rsc_modified == reg.last_rsc_modified) {
                if (b44_alf_reg) {
                    LOG_WARN(SERVICE_APPLIST,
                        "[NBOOT2][ALF_APPARC_REG] phase=duplicate_rejected reason=same_path uid=0x{:08X} rsc={} behavior=OBSERVE_ONLY",
                        reg.mandatory_info.uid, common::ucs2_to_utf8(reg.rsc_path));
                }
                return false;
            }
'''
    a=rep(a,anchor,block,"B44 AppArc same path")

    anchor='''                if (!should_replace_duplicate_registry(reg, *same_uid)) {
                    return false;
                }
'''
    block='''                if (!should_replace_duplicate_registry(reg, *same_uid)) {
                    if (b44_alf_reg) {
                        LOG_WARN(SERVICE_APPLIST,
                            "[NBOOT2][ALF_APPARC_REG] phase=duplicate_rejected reason=same_uid uid=0x{:08X} rsc={} existing_rsc={} behavior=OBSERVE_ONLY",
                            reg.mandatory_info.uid, common::ucs2_to_utf8(reg.rsc_path),
                            common::ucs2_to_utf8(same_uid->rsc_path));
                    }
                    return false;
                }
'''
    a=rep(a,anchor,block,"B44 AppArc same uid")

    anchor='''        regs.push_back(std::move(reg));
        return true;
    }
'''
    block='''        if (b44_alf_reg) {
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][ALF_APPARC_REG] phase=committed uid=0x{:08X} rsc={} behavior=OBSERVE_ONLY",
                reg.mandatory_info.uid, common::ucs2_to_utf8(reg.rsc_path));
        }
        regs.push_back(std::move(reg));
        return true;
    }
'''
    a=rep(a,anchor,block,"B44 AppArc committed")

    anchor='''    bool applist_server::rescan_registries(eka2l1::io_system *io) {
        LOG_INFO(SERVICE_APPLIST, "Loading app registries");

        std::atomic_bool global_modified = false;
'''
    block='''    bool applist_server::rescan_registries(eka2l1::io_system *io) {
        LOG_INFO(SERVICE_APPLIST, "Loading app registries");

        static bool b44_inventory_logged = false;
        if (!b44_inventory_logged && kern->get_config()->native_phone_boot) {
            b44_inventory_logged = true;
            const std::array<std::u16string, 7> b44_paths = {
                u"z:\\sys\\bin\\alfredserver.exe",
                u"z:\\sys\\bin\\alfserver.exe",
                u"z:\\sys\\bin\\tfxsrvplugin.dll",
                u"z:\\resource\\effects\\manifest.mf",
                u"z:\\private\\10003a3f\\apps\\alfredserver_reg.rsc",
                u"z:\\resource\\plugins\\tfxsrvplugin.rsc",
                u"z:\\resource\\plugins\\10282dba.rsc"
            };
            for (const auto &b44_path : b44_paths) {
                LOG_WARN(SERVICE_APPLIST,
                    "[NBOOT2][ALF_ROM_ARTIFACT] path={} exists={} behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(b44_path), io->exist(b44_path) ? 1 : 0);
            }
        }

        std::atomic_bool global_modified = false;
'''
    a=rep(a,anchor,block,"B44 ROM inventory")

    anchor='''    void applist_server::get_app_info(service::ipc_context &ctx) {
        const epoc::uid app_uid = *ctx.get_argument_value<epoc::uid>(0);
        apa_app_registry *reg = get_registration(app_uid);

        if (!reg) {
            ctx.complete(epoc::error_not_found);
            return;
        }
        
        apa_app_info info_copy = reg->mandatory_info;
'''
    block='''    void applist_server::get_app_info(service::ipc_context &ctx) {
        const epoc::uid app_uid = *ctx.get_argument_value<epoc::uid>(0);
        const bool b44_alf_uid = app_uid == static_cast<epoc::uid>(0x10282845);
        kernel::thread *b44_thr = ctx.msg->own_thr;
        kernel::process *b44_pr = b44_thr ? b44_thr->owning_process() : nullptr;
        if (b44_alf_uid) {
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][ALF_APPARC_GETINFO] phase=enter uid=0x{:08X} process={} thread={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(app_uid),
                b44_pr ? b44_pr->name() : std::string("<null>"),
                b44_thr ? b44_thr->name() : std::string("<null>"));
        }

        apa_app_registry *reg = get_registration(app_uid);

        if (!reg) {
            if (b44_alf_uid) {
                LOG_WARN(SERVICE_APPLIST,
                    "[NBOOT2][ALF_APPARC_GETINFO] phase=result uid=0x{:08X} found=0 result={} behavior=OBSERVE_ONLY",
                    static_cast<std::uint32_t>(app_uid), epoc::error_not_found);
            }
            ctx.complete(epoc::error_not_found);
            return;
        }

        if (b44_alf_uid) {
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][ALF_APPARC_GETINFO] phase=resolve uid=0x{:08X} found=1 rsc={} exe={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(app_uid),
                common::ucs2_to_utf8(reg->rsc_path),
                common::ucs2_to_utf8(reg->mandatory_info.app_path.to_std_string(nullptr)));
        }

        apa_app_info info_copy = reg->mandatory_info;
'''
    a=rep(a,anchor,block,"B44 GetAppInfo enter/result")

    anchor='''        ctx.write_data_to_descriptor_argument<apa_app_info>(1, info_copy);
        ctx.complete(epoc::error_none);
    }

    void applist_server::get_app_icon_file_name'''
    block='''        ctx.write_data_to_descriptor_argument<apa_app_info>(1, info_copy);
        if (b44_alf_uid) {
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][ALF_APPARC_GETINFO] phase=complete uid=0x{:08X} result=0 exe={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(app_uid), common::ucs2_to_utf8(info_copy.app_path.to_std_string(nullptr)));
        }
        ctx.complete(epoc::error_none);
    }

    void applist_server::get_app_icon_file_name'''
    a=rep(a,anchor,block,"B44 GetAppInfo complete")

    # ------------------------------------------------------------------
    # FileServer: observe native ECom resource and TFX manifest access.
    # ------------------------------------------------------------------
    anchor='''        *name_res = get_full_symbian_path(ss_path, *name_res);
        std::string name_utf8 = common::ucs2_to_utf8(*name_res);

        io_system *io = ctx->sys->get_io_system();
'''
    block='''        *name_res = get_full_symbian_path(ss_path, *name_res);
        std::string name_utf8 = common::ucs2_to_utf8(*name_res);

        const bool b44_tfx_ecom_rsc =
            name_utf8.find("tfxsrvplugin") != std::string::npos
            || name_utf8.find("TfxSrvPlugin") != std::string::npos
            || name_utf8.find("TFXSRVPLUGIN") != std::string::npos
            || name_utf8.find("10282dba") != std::string::npos
            || name_utf8.find("10282DBA") != std::string::npos;
        const bool b44_tfx_manifest =
            name_utf8.find("manifest.mf") != std::string::npos
            || name_utf8.find("MANIFEST.MF") != std::string::npos;
        kernel::thread *b44_thr = ctx->msg->own_thr;
        kernel::process *b44_pr = b44_thr ? b44_thr->owning_process() : nullptr;
        auto b44_log_file = [&](const char *phase, const std::int32_t result) {
            if (b44_tfx_ecom_rsc) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][TFX_ECOM_RSC] phase={} path={} process={} thread={} result={} behavior=OBSERVE_ONLY",
                    phase, name_utf8,
                    b44_pr ? b44_pr->name() : std::string("<null>"),
                    b44_thr ? b44_thr->name() : std::string("<null>"), result);
            }
            if (b44_tfx_manifest) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][TFX_MANIFEST] phase={} path={} process={} thread={} result={} behavior=OBSERVE_ONLY",
                    phase, name_utf8,
                    b44_pr ? b44_pr->name() : std::string("<null>"),
                    b44_thr ? b44_thr->name() : std::string("<null>"), result);
            }
        };
        if (b44_tfx_ecom_rsc || b44_tfx_manifest) {
            b44_log_file("request", 0);
        }

        io_system *io = ctx->sys->get_io_system();
'''
    f=rep(f,anchor,block,"B44 FS request")

    anchor='''                ctx->complete(epoc::error_path_not_found);
                return;
            }
        }

        const bool is_it_avail'''
    block='''                b44_log_file("result", epoc::error_path_not_found);
                ctx->complete(epoc::error_path_not_found);
                return;
            }
        }

        const bool is_it_avail'''
    f=rep(f,anchor,block,"B44 FS missing directory")

    anchor='''        if (!is_it_avail && (existence == exist_mode_neccessary)) {
            LOG_ERROR(SERVICE_EFSRV, "Trying to open a non-existent file: {} while the open mode requires its availbility!",
                name_utf8);

            ctx->complete(epoc::error_not_found);
            return;
        }
'''
    block='''        if (!is_it_avail && (existence == exist_mode_neccessary)) {
            LOG_ERROR(SERVICE_EFSRV, "Trying to open a non-existent file: {} while the open mode requires its availbility!",
                name_utf8);

            b44_log_file("result", epoc::error_not_found);
            ctx->complete(epoc::error_not_found);
            return;
        }
'''
    f=rep(f,anchor,block,"B44 FS missing file")

    anchor='''        if (handle <= 0) {
            ctx->complete(handle);
            return;
        }

        LOG_TRACE(SERVICE_EFSRV, "Handle opened: {}", handle);
'''
    block='''        if (handle <= 0) {
            b44_log_file("result", handle);
            ctx->complete(handle);
            return;
        }

        b44_log_file("result", epoc::error_none);
        LOG_TRACE(SERVICE_EFSRV, "Handle opened: {}", handle);
'''
    f=rep(f,anchor,block,"B44 FS open result")

    svc.write_text(s)
    loader.write_text(l)
    applist.write_text(a)
    files.write_text(f)
    print(MARK+": applied")
    print("scope=ALF_TFX_PROVIDER_STARTUP_MULTI_BOUNDARY_DIAGNOSTIC_ONLY")
    print("guest_semantics=UNCHANGED")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ps_mutation=NONE")

if __name__=="__main__":
    main()
