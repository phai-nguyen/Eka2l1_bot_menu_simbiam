#!/usr/bin/env python3
"""NATIVEBOOT2 B45 AKNSKINNTFX1.

Narrow source-guided native AknSkinServer route experiment.

Only for native_phone_boot + EPOC9.4 + a native AknSkinSrv image in ROM, do not
pre-create EKA2L1's HLE !AknSkinServer. This restores the guest-visible
KErrNotFound condition expected by RAknsSrvSession::Connect(), allowing the
firmware client to invoke its own StartServer() / RProcess::Create path.

All other modes and versions keep the HLE service exactly as before.

No TfxServer, ECom result, P&S value, ALF server, or IPC completion is
fabricated.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B45-AKNSKINNTFX1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep(text, old, new, label):
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def rep_between(text, begin, end, old, new, label):
    b=text.find(begin)
    e=text.find(end,b+1)
    if b < 0 or e < 0:
        fail(f"{label}: bounds not found")
    region=text[b:e]
    n=region.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor in bounded region, found {n}")
    region=region.replace(old,new,1)
    return text[:b]+region+text[e:]

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b45_aknskinntfx1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    init=up/"src/emu/services/src/init.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"
    applist=up/"src/emu/services/src/applist/applist.cpp"

    for p in (init,svc,loader,applist):
        if not p.is_file():
            fail(f"missing source file: {p}")

    i=init.read_text()
    s=svc.read_text()
    l=loader.read_text()
    a=applist.read_text()

    for marker,text in (
        ("[NBOOT2][ALF_SESSION]",s),
        ("[NBOOT2][TFX_PS]",s),
        ("[NBOOT2][TFX_ECOM_DLL]",l),
        ("[NBOOT2][ALF_ROM_ARTIFACT]",a),
        ("[NBOOT2][TFX_SESSION]",s),
        ("[NBOOT2][LOADER_PDD]",l),
    ):
        if marker not in text:
            fail("missing baseline "+marker)

    if "[NBOOT2][AKNSKIN_ROUTE]" in i:
        print(MARK+": already applied")
        return

    # ---------------------------------------------------------------
    # 1. Native route: skip only the EPOC9.4 native-phone-boot HLE
    #    when a native ROM image is actually present.
    # ---------------------------------------------------------------
    if "#include <common/log.h>" not in i:
        i=rep(i,
            "#include <common/platform.h>\n",
            "#include <common/platform.h>\n#include <common/log.h>\n",
            "init log include")

    anchor='''            CREATE_SERVER(sys, akn_skin_server);

            CREATE_SERVER(sys, system_agent_server);
'''
    block='''            const bool b45_aknskin_exe_sysbin =
                sys->get_io_system()->exist(u"z:\\sys\\bin\\aknskinsrv.exe");
            const bool b45_aknskin_exe_legacy =
                sys->get_io_system()->exist(u"z:\\system\\programs\\aknskinsrv.exe");
            const bool b45_aknskin_native_route =
                cfg->native_phone_boot
                && sys->get_symbian_version_use() == epocver::epoc94
                && (b45_aknskin_exe_sysbin || b45_aknskin_exe_legacy);

            if (b45_aknskin_native_route) {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_skip epoc=94 native_phone_boot=1 exe_sysbin={} exe_legacy={} behavior=GUEST_NATIVE_ROUTE",
                    b45_aknskin_exe_sysbin ? 1 : 0, b45_aknskin_exe_legacy ? 1 : 0);
            } else {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_keep epoc={} native_phone_boot={} exe_sysbin={} exe_legacy={} behavior=UNCHANGED_HLE",
                    static_cast<int>(sys->get_symbian_version_use()), cfg->native_phone_boot ? 1 : 0,
                    b45_aknskin_exe_sysbin ? 1 : 0, b45_aknskin_exe_legacy ? 1 : 0);
                CREATE_SERVER(sys, akn_skin_server);
            }

            CREATE_SERVER(sys, system_agent_server);
'''
    i=rep(i,anchor,block,"native AknSkin route")

    # ---------------------------------------------------------------
    # 2. Exact !AknSkinServer session provenance.
    # ---------------------------------------------------------------
    session_begin="    BRIDGE_FUNC(std::int32_t, session_create,"
    session_end="    BRIDGE_FUNC(std::int32_t, session_create_from_handle,"

    anchor='''        const std::string server_name = server_name_des.get(pr)->to_std_string(pr);
'''
    block='''        const std::string server_name = server_name_des.get(pr)->to_std_string(pr);
        const bool b45_aknskin_session =
            kern->get_config()->native_phone_boot && (server_name == "!AknSkinServer");
        if (b45_aknskin_session) {
            kernel::thread *b45_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_SESSION] phase=request process={} thread={} server={} msg_slots={} mode={} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b45_thr ? b45_thr->name() : std::string("<null>"),
                server_name, msg_slot, mode);
        }
'''
    s=rep_between(s,session_begin,session_end,anchor,block,"AknSkin session request")

    anchor='''        server_ptr server = kern->get_by_name<service::server>(server_name);
'''
    block='''        server_ptr server = kern->get_by_name<service::server>(server_name);
        if (b45_aknskin_session) {
            kernel::thread *b45_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_SESSION] phase=lookup process={} thread={} server={} found={} server_hle={} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b45_thr ? b45_thr->name() : std::string("<null>"),
                server_name, server ? 1 : 0, server ? (server->is_hle() ? 1 : 0) : -1);
        }
'''
    s=rep_between(s,session_begin,session_end,anchor,block,"AknSkin session lookup")

    # Insert missing log immediately before the real KErrNotFound return.
    anchor='''            return epoc::error_not_found;
        }

        if (b43_tfx) {
'''
    block='''            if (b45_aknskin_session) {
                kernel::thread *b45_thr = kern->crr_thread();
                LOG_WARN(KERNEL,
                    "[NBOOT2][AKNSKIN_SESSION] phase=missing process={} thread={} server={} result={} server_hle=-1 behavior=OBSERVE_ONLY",
                    pr ? pr->name() : std::string("<null>"),
                    b45_thr ? b45_thr->name() : std::string("<null>"),
                    server_name, epoc::error_not_found);
            }
            return epoc::error_not_found;
        }

        if (b43_tfx) {
'''
    s=rep_between(s,session_begin,session_end,anchor,block,"AknSkin session missing")

    anchor='''        return do_create_session_from_server(kern, server, msg_slot, sec, mode);
'''
    block='''        if (b45_aknskin_session) {
            kernel::thread *b45_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_SESSION] phase=found process={} thread={} server={} server_hle={} behavior=OBSERVE_ONLY",
                pr ? pr->name() : std::string("<null>"),
                b45_thr ? b45_thr->name() : std::string("<null>"),
                server_name, server->is_hle() ? 1 : 0);
        }
        return do_create_session_from_server(kern, server, msg_slot, sec, mode);
'''
    s=rep_between(s,session_begin,session_end,anchor,block,"AknSkin session found")

    # ---------------------------------------------------------------
    # 3. Exact native !AknSkinServer registration.
    # ---------------------------------------------------------------
    anchor='''            LOG_TRACE(KERNEL, "Server {} created", server_name);
'''
    block='''            LOG_TRACE(KERNEL, "Server {} created", server_name);
            if (kern->get_config()->native_phone_boot && server_name == "!AknSkinServer") {
                LOG_WARN(KERNEL,
                    "[NBOOT2][AKNSKIN_NATIVE_REGISTER] process={} server={} handle={} mode={} process_hle={} behavior=OBSERVE_ONLY",
                    crr_pr ? crr_pr->name() : std::string("<null>"),
                    server_name, handle, mode, crr_pr ? 0 : -1);
            }
'''
    s=rep(s,anchor,block,"AknSkin native register")

    # ---------------------------------------------------------------
    # 4. Loader provenance for AknSkinSrv.exe.
    # ---------------------------------------------------------------
    anchor='''        const bool b44_alf_process =
            name_process == "alfredserver" || name_process == "alfredserver.exe"
            || name_process == "AlfredServer" || name_process == "AlfredServer.exe"
            || name_process == "alfserver" || name_process == "alfserver.exe"
            || name_process == "AlfServer" || name_process == "AlfServer.exe";
'''
    block='''        const bool b44_alf_process =
            name_process == "alfredserver" || name_process == "alfredserver.exe"
            || name_process == "AlfredServer" || name_process == "AlfredServer.exe"
            || name_process == "alfserver" || name_process == "alfserver.exe"
            || name_process == "AlfServer" || name_process == "AlfServer.exe";
        const bool b45_aknskin_process =
            name_process == "aknskinsrv" || name_process == "aknskinsrv.exe"
            || name_process == "AknSkinSrv" || name_process == "AknSkinSrv.exe"
            || b43_process_path.find("aknskinsrv.exe") != std::string::npos
            || b43_process_path.find("AknSkinSrv.exe") != std::string::npos;
        if (b45_aknskin_process && ctx.sys->get_config()->native_phone_boot) {
            kernel::process *caller = ctx.msg->own_thr ? ctx.msg->own_thr->owning_process() : nullptr;
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][AKNSKIN_NATIVE_PROC] phase=request caller={} path={} file={} uid3=0x{:08X} stack=0x{:X} behavior=OBSERVE_ONLY",
                caller ? caller->name() : std::string("<null>"),
                b43_process_path, name_process, uid3, stack_size);
        }
'''
    l=rep(l,anchor,block,"AknSkin native process request")

    anchor='''            if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=0 result={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found, uid3);
            }
            ctx.complete(epoc::error_not_found);
'''
    block='''            if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=0 result={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found, uid3);
            }
            if (b45_aknskin_process && ctx.sys->get_config()->native_phone_boot) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][AKNSKIN_NATIVE_PROC] phase=result path={} success=0 result={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                    b43_process_path, epoc::error_not_found, uid3);
            }
            ctx.complete(epoc::error_not_found);
'''
    l=rep(l,anchor,block,"AknSkin native process fail")

    anchor='''        if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
            const auto b44_uids = pr->get_uid_type();
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=1 result=0 spawned={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name(), static_cast<std::uint32_t>(std::get<2>(b44_uids)));
        }

        process_ptr request_pr'''
    block='''        if (b44_alf_process && ctx.sys->get_config()->native_phone_boot) {
            const auto b44_uids = pr->get_uid_type();
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][ALF_PROC_CREATE] phase=result path={} success=1 result=0 spawned={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name(), static_cast<std::uint32_t>(std::get<2>(b44_uids)));
        }
        if (b45_aknskin_process && ctx.sys->get_config()->native_phone_boot) {
            const auto b45_uids = pr->get_uid_type();
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][AKNSKIN_NATIVE_PROC] phase=result path={} success=1 result=0 spawned={} uid3=0x{:08X} behavior=OBSERVE_ONLY",
                b43_process_path, pr->name(), static_cast<std::uint32_t>(std::get<2>(b45_uids)));
        }

        process_ptr request_pr'''
    l=rep(l,anchor,block,"AknSkin native process success")

    # ---------------------------------------------------------------
    # 5. ROM artifact inventory. This does not change route selection.
    # ---------------------------------------------------------------
    anchor='''        std::atomic_bool global_modified = false;
'''
    block='''        static bool b45_aknskin_inventory_logged = false;
        if (!b45_aknskin_inventory_logged && kern->get_config()->native_phone_boot) {
            b45_aknskin_inventory_logged = true;
            const std::u16string b45_exe_sysbin = u"z:\\sys\\bin\\aknskinsrv.exe";
            const std::u16string b45_exe_legacy = u"z:\\system\\programs\\aknskinsrv.exe";
            const std::u16string b45_dll = u"z:\\sys\\bin\\aknskinsrv.dll";
            LOG_WARN(SERVICE_APPLIST,
                "[NBOOT2][AKNSKIN_ROM] exe_sysbin={} exists={} exe_legacy={} exists_legacy={} dll={} dll_exists={} expected_dll_uid3=0x10005A35 behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(b45_exe_sysbin), io->exist(b45_exe_sysbin) ? 1 : 0,
                common::ucs2_to_utf8(b45_exe_legacy), io->exist(b45_exe_legacy) ? 1 : 0,
                common::ucs2_to_utf8(b45_dll), io->exist(b45_dll) ? 1 : 0);
        }

        std::atomic_bool global_modified = false;
'''
    # B44 creates only one occurrence of this exact post-inventory anchor in this function.
    a=rep(a,anchor,block,"AknSkin ROM inventory")

    init.write_text(i)
    svc.write_text(s)
    loader.write_text(l)
    applist.write_text(a)

    print(MARK+": applied")
    print("scope=EPOC94_NATIVE_AKNSKIN_ROUTE_EXPERIMENT")
    print("route_guard=NATIVE_PHONE_BOOT_AND_ROM_IMAGE")
    print("other_modes=UNCHANGED_HLE")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ecom_synthesis=NONE")
    print("ps_synthesis=NONE")

if __name__=="__main__":
    main()
