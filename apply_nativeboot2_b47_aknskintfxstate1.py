#!/usr/bin/env python3
"""NATIVEBOOT2 B47 AKNSKINTFXSTATE1.

Diagnostic-only tracing for the first source-guided transition-effects gate
after B46 proved the native AknSkinSrv startup path.

Observe:
- AknSkinSrv CRepository::GetInt for KCRUidThemes=0x102818E8,
  KThemesTransitionEffects=0x00000009;
- AknSkinSrv CreateSession to !Windowserver;
- AknSkinSrv IPC sent to !ecomserver.

No guest-visible value/result is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B47-AKNSKINTFXSTATE1"

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
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b47_aknskintfxstate1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    repo_cpp=up/"src/emu/services/src/centralrepo/repo.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    init=up/"src/emu/services/src/init.cpp"
    loader=up/"src/emu/services/src/loader/loader.cpp"

    for p in (repo_cpp,svc,init,loader):
        if not p.is_file():
            fail(f"missing source: {p}")

    rp=repo_cpp.read_text(encoding="utf-8")
    s=svc.read_text(encoding="utf-8")
    i=init.read_text(encoding="utf-8")
    l=loader.read_text(encoding="utf-8")

    for marker,text in (
        ("[NBOOT2][AKNSKIN_ROUTE2]",i),
        ("[NBOOT2][AKNSKIN_NATIVE_REGISTER]",s),
        ("[NBOOT2][AKNSKIN_NATIVE_PROC]",l),
        ("[NBOOT2][TFX_PS]",s),
        ("[NBOOT2][ALF_SESSION]",s),
        ("[NBOOT2][TFX_ECOM_DLL]",l),
    ):
        if marker not in text:
            fail("missing baseline "+marker)

    if "[NBOOT2][AKNSKIN_TFX_STATE]" in rp:
        print(MARK+": already applied")
        return

    # ---------------------------------------------------------------
    # 1. CenRep: exact native AknSkinSrv Themes transition-state GetInt.
    # ---------------------------------------------------------------
    if "#include <config/config.h>" not in rp:
        rp=rep(rp,
            "#include <services/context.h>\n",
            "#include <services/context.h>\n#include <config/config.h>\n",
            "CenRep config include")
    if "#include <kernel/process.h>" not in rp:
        rp=rep(rp,
            "#include <config/config.h>\n",
            "#include <config/config.h>\n#include <kernel/process.h>\n",
            "CenRep process include")

    get_begin="    void central_repo_client_subsession::get_value(service::ipc_context *ctx) {"
    get_end="    void central_repo_client_subsession::append_new_key_to_found_eq_list"

    anchor='''        std::optional<std::uint32_t> the_key = ctx->get_argument_value<std::uint32_t>(0);

        if (!the_key.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }

        central_repo_entry *entry = get_entry(the_key.value(), 0);
'''
    block='''        std::optional<std::uint32_t> the_key = ctx->get_argument_value<std::uint32_t>(0);

        if (!the_key.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }

        auto *b47_thr = ctx->msg ? ctx->msg->own_thr : nullptr;
        auto *b47_pr = b47_thr ? b47_thr->owning_process() : nullptr;
        const std::string b47_process_name = b47_pr ? b47_pr->name() : std::string("<null>");
        const bool b47_aknskin_process =
            b47_process_name.find("AknSkinSrv[10207114]") != std::string::npos
            || b47_process_name.find("aknskinsrv[10207114]") != std::string::npos;
        const bool b47_tfx_state =
            ctx->sys->get_config()->native_phone_boot
            && b47_aknskin_process
            && ctx->msg->function == cen_rep_get_int
            && attach_repo
            && attach_repo->uid == static_cast<std::uint32_t>(0x102818E8)
            && the_key.value() == static_cast<std::uint32_t>(0x00000009);

        if (b47_tfx_state) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][AKNSKIN_TFX_STATE] phase=request process={} thread={} repo=0x102818E8 key=0x00000009 function={} behavior=OBSERVE_ONLY",
                b47_process_name,
                b47_thr ? b47_thr->name() : std::string("<null>"),
                ctx->msg->function);
        }

        central_repo_entry *entry = get_entry(the_key.value(), 0);
'''
    rp=rep_between(rp,get_begin,get_end,anchor,block,"B47 CenRep request")

    anchor='''        if (!entry) {
            ctx->complete(epoc::error_not_found);
            return;
        }
'''
    block='''        if (!entry) {
            if (b47_tfx_state) {
                LOG_WARN(SERVICE_CENREP,
                    "[NBOOT2][AKNSKIN_TFX_STATE] phase=result process={} repo=0x102818E8 key=0x00000009 result={} value_valid=0 value=0xFFFFFFFF behavior=OBSERVE_ONLY",
                    b47_process_name, epoc::error_not_found);
            }
            ctx->complete(epoc::error_not_found);
            return;
        }
'''
    rp=rep_between(rp,get_begin,get_end,anchor,block,"B47 CenRep missing")

    anchor='''        case cen_rep_get_int: {
            if (entry->data.etype != central_repo_entry_type::integer) {
                ctx->complete(epoc::error_argument);
                return;
            }

            const std::uint32_t result_int = static_cast<std::uint32_t>(entry->data.intd);
            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, result_int);

            break;
        }
'''
    block='''        case cen_rep_get_int: {
            if (entry->data.etype != central_repo_entry_type::integer) {
                if (b47_tfx_state) {
                    LOG_WARN(SERVICE_CENREP,
                        "[NBOOT2][AKNSKIN_TFX_STATE] phase=result process={} repo=0x102818E8 key=0x00000009 result={} value_valid=0 value=0xFFFFFFFF entry_type={} behavior=OBSERVE_ONLY",
                        b47_process_name, epoc::error_argument,
                        static_cast<int>(entry->data.etype));
                }
                ctx->complete(epoc::error_argument);
                return;
            }

            const std::uint32_t result_int = static_cast<std::uint32_t>(entry->data.intd);
            if (b47_tfx_state) {
                LOG_WARN(SERVICE_CENREP,
                    "[NBOOT2][AKNSKIN_TFX_STATE] phase=result process={} repo=0x102818E8 key=0x00000009 result=0 value_valid=1 value=0x{:08X} enabled={} suppressed={} behavior=OBSERVE_ONLY",
                    b47_process_name, result_int,
                    result_int != static_cast<std::uint32_t>(0x7FFFFFFF) ? 1 : 0,
                    result_int == static_cast<std::uint32_t>(0x7FFFFFFF) ? 1 : 0);
            }
            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, result_int);

            break;
        }
'''
    rp=rep_between(rp,get_begin,get_end,anchor,block,"B47 CenRep result")

    # ---------------------------------------------------------------
    # 2. CreateSession: observe AknSkinSrv -> !Windowserver.
    # ---------------------------------------------------------------
    sess_begin="    BRIDGE_FUNC(std::int32_t, session_create,"
    sess_end="    BRIDGE_FUNC(std::int32_t, session_create_from_handle,"

    anchor='''        server_ptr server = kern->get_by_name<service::server>(server_name);
        if (b45_aknskin_session) {
'''
    block='''        const std::string b47_session_process =
            pr ? pr->name() : std::string("<null>");
        const bool b47_aknskin_wserv =
            kern->get_config()->native_phone_boot
            && (b47_session_process.find("AknSkinSrv[10207114]") != std::string::npos
                || b47_session_process.find("aknskinsrv[10207114]") != std::string::npos)
            && server_name == "!Windowserver";
        if (b47_aknskin_wserv) {
            kernel::thread *b47_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_TFX_WSERV] phase=request process={} thread={} server={} msg_slots={} mode={} expected_uid3=0x10207114 behavior=OBSERVE_ONLY",
                b47_session_process,
                b47_thr ? b47_thr->name() : std::string("<null>"),
                server_name, msg_slot, mode);
        }

        server_ptr server = kern->get_by_name<service::server>(server_name);
        if (b47_aknskin_wserv) {
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_TFX_WSERV] phase=lookup process={} server={} found={} server_hle={} expected_uid3=0x10207114 behavior=OBSERVE_ONLY",
                b47_session_process, server_name,
                server ? 1 : 0, server ? (server->is_hle() ? 1 : 0) : -1);
        }
        if (b45_aknskin_session) {
'''
    s=rep_between(s,sess_begin,sess_end,anchor,block,"B47 Wserv session")

    # ---------------------------------------------------------------
    # 3. Native ecomserver IPC: log all AknSkinSrv sends without
    #    guessing the guest ECom opcode.
    # ---------------------------------------------------------------
    send_begin="    static std::int32_t session_send_general("
    send_end="    BRIDGE_FUNC(std::int32_t, session_send_sync,"

    anchor='''        const std::string server_name = ss->get_server()->name();
'''
    block='''        const std::string server_name = ss->get_server()->name();
        const std::string b47_send_process =
            crr_pr ? crr_pr->name() : std::string("<null>");
        const bool b47_aknskin_ecom =
            kern->get_config()->native_phone_boot
            && (b47_send_process.find("AknSkinSrv[10207114]") != std::string::npos
                || b47_send_process.find("aknskinsrv[10207114]") != std::string::npos)
            && server_name == "!ecomserver";
        if (b47_aknskin_ecom) {
            kernel::thread *b47_thr = kern->crr_thread();
            const bool b47_literal_controller =
                static_cast<std::uint32_t>(arg.args[0]) == 0x10282DBD
                || static_cast<std::uint32_t>(arg.args[1]) == 0x10282DBD
                || static_cast<std::uint32_t>(arg.args[2]) == 0x10282DBD
                || static_cast<std::uint32_t>(arg.args[3]) == 0x10282DBD;
            const bool b47_literal_server =
                static_cast<std::uint32_t>(arg.args[0]) == 0x10282DBC
                || static_cast<std::uint32_t>(arg.args[1]) == 0x10282DBC
                || static_cast<std::uint32_t>(arg.args[2]) == 0x10282DBC
                || static_cast<std::uint32_t>(arg.args[3]) == 0x10282DBC;
            LOG_WARN(KERNEL,
                "[NBOOT2][AKNSKIN_TFX_ECOM] phase=send process={} thread={} server={} function=0x{:X} sync={} status=0x{:08X} flag=0x{:08X} types=[{},{},{},{}] raw=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] literal_controller={} literal_server={} expected_caller_uid3=0x10207114 expected_controller_if=0x10282DBD expected_server_if=0x10282DBC behavior=OBSERVE_ONLY",
                b47_send_process,
                b47_thr ? b47_thr->name() : std::string("<null>"),
                server_name, static_cast<std::uint32_t>(ord), sync ? 1 : 0,
                status.ptr_address(), static_cast<std::uint32_t>(arg.flag),
                static_cast<int>(arg.get_arg_type(0)),
                static_cast<int>(arg.get_arg_type(1)),
                static_cast<int>(arg.get_arg_type(2)),
                static_cast<int>(arg.get_arg_type(3)),
                static_cast<std::uint32_t>(arg.args[0]),
                static_cast<std::uint32_t>(arg.args[1]),
                static_cast<std::uint32_t>(arg.args[2]),
                static_cast<std::uint32_t>(arg.args[3]),
                b47_literal_controller ? 1 : 0,
                b47_literal_server ? 1 : 0);
        }

'''
    s=rep_between(s,send_begin,send_end,anchor,block,"B47 ECom IPC")

    repo_cpp.write_text(rp,encoding="utf-8")
    svc.write_text(s,encoding="utf-8")

    print(MARK+": applied")
    print("cenrep_target=0x102818E8/key0x9")
    print("cenrep_write=NONE")
    print("force_tfx_enabled=NONE")
    print("wserv_result_change=NONE")
    print("ecom_result_change=NONE")
    print("fake_tfxserver=NONE")
    print("B40_B41_B42_B43_B44_B45_B46=PRESERVED")

if __name__=="__main__":
    main()
