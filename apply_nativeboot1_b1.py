#!/usr/bin/env python3
"""NATIVEBOOT1-B1: hand EKA2L1's post-kernel boot to the ROM EStart chain.

Diagnostic-first hybrid boot:
- dedicated transient native_phone_boot mode,
- native ownership for guest UI/startup servers that collide with HLE names,
- retain hardware-facing / graphics-critical HLE services,
- publish C32 core-ready for the already-live HLE comm/socket stack,
- launch ONLY z:\\sys\\bin\\EStart.exe after normal EKA2L1 user-side setup,
- trace process/server/rendezvous/collision/missing-server events.

It does NOT host-launch SysStart, Menu3, or a component plan.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT1-B1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_config(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "bool native_phone_boot" in text:
        return
    anchor = "        bool enable_srv_drm{ true };\n"
    insert = anchor + """
        // NATIVEBOOT1-B1: transient build-mode flag. Do not serialize this.
        // The dedicated NATIVEBOOT1 IPA hands user-space boot to the ROM's
        // EStart/SysStart chain while retaining selected hardware-facing HLEs.
        bool native_phone_boot{ true };
"""
    text = replace_once(text, anchor, insert, "config native_phone_boot")
    path.write_text(text, encoding="utf-8")

def wrap_server_once(text: str, server: str, reason: str) -> str:
    anchor = f"            CREATE_SERVER(sys, {server});"
    if anchor not in text:
        fail(f"init services: missing {server} anchor")
    replacement = (
        f"            if (!native_phone_boot) {{\n"
        f"                // NATIVEBOOT1-B1: {reason}\n"
        f"                CREATE_SERVER(sys, {server});\n"
        f"            }}"
    )
    return replace_once(text, anchor, replacement, f"wrap {server}")

def patch_services(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT1][HLE_POLICY]" in text:
        return
    if "#include <common/log.h>" not in text:
        text = replace_once(
            text, "#include <common/algorithm.h>\n",
            "#include <common/algorithm.h>\n#include <common/log.h>\n",
            "init common/log include")
    cfg_anchor = "            config::state *cfg = sys->get_config();\n"
    policy = cfg_anchor + """
            const bool native_phone_boot = cfg->native_phone_boot;
            LOG_WARN(SYSTEM,
                "[NBOOT1][HLE_POLICY] enabled={} fs=HLE loader=HLE fbs=HLE wserv=HLE hwrm=HLE etel=HLE "
                "applist=NATIVE akncap=NATIVE view=NATIVE notifier=NATIVE keysound=NATIVE eikappui=NATIVE sysagt=NATIVE domain=NATIVE_FIRST",
                native_phone_boot ? 1 : 0);
"""
    text = replace_once(text, cfg_anchor, policy, "init native boot policy")
    text = wrap_server_once(text, "applist_server", "ROM APSEXE/AppArc must own its public server")
    text = wrap_server_once(text, "oom_ui_app_server", "ROM AknCapServer must create the UI-capability service")
    text = wrap_server_once(text, "view_server", "EikSrv must own the native ViewServer")
    text = wrap_server_once(text, "notifier_server", "EikSrv must own the native !Notifier server")
    text = wrap_server_once(text, "keysound_server", "EikSrv must own the native KeySoundServer")
    text = wrap_server_once(text, "eikappui_server", "ROM EikSrv/EikAppUI startup path must own this service")
    text = wrap_server_once(text, "system_agent_server", "ROM sysagt2svr.exe must own SystemAgent")
    comm_anchor = "            CREATE_SERVER(sys, comm_server);\n"
    comm_insert = comm_anchor + """            if (native_phone_boot) {
                // Hybrid keeps EKA2L1 socket/serial. Native StartC32 still waits
                // for ECoreComponentsStarted, so publish only this minimum state.
                DEFINE_INT_PROP_D(sys, 0x101F75B6, 0x102045DD, 10);
                LOG_WARN(SYSTEM, "[NBOOT1][C32_READY] category=0x101F75B6 key=0x102045DD value=10");
            }
"""
    text = replace_once(text, comm_anchor, comm_insert, "C32 ready property")
    # EStart itself creates domainSrv.exe and then waits for its initialization
    # property. If a newer baseline happens to have an HLE Domain Manager, do
    # not pre-register it in native boot: let the ROM process own the first try.
    if "CREATE_SERVER(sys, dm_domain_server);" in text:
        text = wrap_server_once(text, "dm_domain_server", "EStart launches ROM domainSrv.exe; native ownership gets the first attempt")
    path.write_text(text, encoding="utf-8")

def patch_system_boot(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT1][ESTART_CREATE]" in text:
        return
    anchor = "        kern_->start_bootload();\n"
    block = anchor + r'''

        if (conf_->native_phone_boot) {
            static const std::u16string estart_path = u"z:\sys\bin\estart.exe";
            LOG_WARN(SYSTEM,
                "[NBOOT1][BOOT_MODE] native_phone_boot=1 handoff={} host_sysstart=0 host_menu=0",
                common::ucs2_to_utf8(estart_path));

            if (!io_->exist(estart_path)) {
                LOG_ERROR(SYSTEM, "[NBOOT1][ESTART_MISSING] path={}", common::ucs2_to_utf8(estart_path));
            } else {
                bool already_running = false;
                for (const auto &process_obj : kern_->get_process_list()) {
                    const kernel::process *process = reinterpret_cast<const kernel::process *>(process_obj.get());
                    if ((process->get_exit_type() == kernel::entity_exit_type::pending)
                        && (common::compare_ignore_case(
                                eka2l1::filename(process->get_exe_path(), true), u"estart.exe") == 0)) {
                        already_running = true;
                        LOG_WARN(SYSTEM, "[NBOOT1][ESTART_ALREADY_RUNNING] name={}", process->name());
                        break;
                    }
                }

                if (!already_running) {
                    process_ptr estart = kern_->spawn_new_process(estart_path, u"");
                    if (!estart) {
                        LOG_ERROR(SYSTEM, "[NBOOT1][ESTART_CREATE_FAIL] path={}", common::ucs2_to_utf8(estart_path));
                    } else {
                        estart->logon([](kernel::process *process) {
                            LOG_WARN(SYSTEM,
                                "[NBOOT1][ESTART_EXIT] name={} type={} reason={} category={}",
                                process->name(), static_cast<int>(process->get_exit_type()), process->get_exit_reason(),
                                common::ucs2_to_utf8(process->get_exit_category()));
                        });
                        LOG_WARN(SYSTEM, "[NBOOT1][ESTART_CREATE] name={} path={}",
                            estart->name(), common::ucs2_to_utf8(estart_path));
                        if (!estart->run()) {
                            LOG_ERROR(SYSTEM, "[NBOOT1][ESTART_RUN_FAIL] name={}", estart->name());
                        } else {
                            LOG_WARN(SYSTEM, "[NBOOT1][ESTART_RUN] name={}", estart->name());
                        }
                    }
                }
            }
        }
'''
    text = replace_once(text, anchor, block, "EStart handoff")
    path.write_text(text, encoding="utf-8")

def patch_kernel_spawn(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT1][PROC_CREATE]" in text:
        return
    miss_anchor = """        if (!imgs.first && !imgs.second) {
            return nullptr;
        }
"""
    miss_new = """        if (!imgs.first && !imgs.second) {
            LOG_WARN(KERNEL, "[NBOOT1][PROC_CREATE_FAIL] path={} cmd={} reason=image_not_found",
                common::ucs2_to_utf8(path), common::ucs2_to_utf8(cmd_arg));
            return nullptr;
        }
"""
    text = replace_once(text, miss_anchor, miss_new, "process image miss trace")
    cs_anchor = """        if (!cs) {
            destroy(pr);
            return nullptr;
        }
"""
    cs_new = """        if (!cs) {
            LOG_WARN(KERNEL, "[NBOOT1][PROC_CREATE_FAIL] path={} cmd={} reason=codeseg_load_failed",
                common::ucs2_to_utf8(path), common::ucs2_to_utf8(cmd_arg));
            destroy(pr);
            return nullptr;
        }
"""
    text = replace_once(text, cs_anchor, cs_new, "process codeseg fail trace")
    done_anchor = "        pr->construct_with_codeseg(cs, new_stack_size, heap_min, heap_max, pri);\n\n        return pr;\n"
    done_new = """        pr->construct_with_codeseg(cs, new_stack_size, heap_min, heap_max, pri);

        LOG_WARN(KERNEL,
            "[NBOOT1][PROC_CREATE] name={} path={} resolved={} cmd={} uid3=0x{:08X} entry=0x{:08X}",
            pr->name(), common::ucs2_to_utf8(path), common::ucs2_to_utf8(full_path),
            common::ucs2_to_utf8(cmd_arg), pr->get_uid(), cs->get_code_run_addr(&(*pr)));
        if (common::compare_ignore_case(eka2l1::filename(path, true), u"sysstart.exe") == 0) {
            LOG_WARN(KERNEL, "[NBOOT1][SYSSTART_CREATE] name={} path={}", pr->name(), common::ucs2_to_utf8(path));
        }

        return pr;
"""
    text = replace_once(text, done_anchor, done_new, "process create trace")
    path.write_text(text, encoding="utf-8")

def patch_process_lifecycle(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT1][PROC_RUN]" in text:
        return
    run_anchor = """    bool process::run() {
        return kern->get_thread_scheduler()->schedule(&(*primary_thread));
    }
"""
    run_new = """    bool process::run() {
        LOG_WARN(KERNEL, "[NBOOT1][PROC_RUN] name={} path={} uid3=0x{:08X}",
            name(), common::ucs2_to_utf8(exe_path), get_uid());
        return kern->get_thread_scheduler()->schedule(&(*primary_thread));
    }
"""
    text = replace_once(text, run_anchor, run_new, "process run trace")
    kill_anchor = """    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {
        if (exit_type != entity_exit_type::pending) {
            return;
        }

        exit_type = ext;
"""
    kill_new = """    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {
        if (exit_type != entity_exit_type::pending) {
            return;
        }

        LOG_WARN(KERNEL,
            "[NBOOT1][PROC_EXIT] name={} path={} type={} reason={} category={}",
            name(), common::ucs2_to_utf8(exe_path), static_cast<int>(ext), reason,
            common::ucs2_to_utf8(category));

        exit_type = ext;
"""
    text = replace_once(text, kill_anchor, kill_new, "process exit trace")
    rend_anchor = """    void process::rendezvous(int rendezvous_reason) {
        exit_reason = rendezvous_reason;
"""
    rend_new = """    void process::rendezvous(int rendezvous_reason) {
        LOG_WARN(KERNEL, "[NBOOT1][RENDEZVOUS] name={} path={} reason={}",
            name(), common::ucs2_to_utf8(exe_path), rendezvous_reason);
        exit_reason = rendezvous_reason;
"""
    text = replace_once(text, rend_anchor, rend_new, "process rendezvous trace")
    path.write_text(text, encoding="utf-8")

def patch_svc(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT1][SERVER_REGISTER]" in text:
        return
    server_anchor = """        if (handle != kernel::INVALID_HANDLE) {
            LOG_TRACE(KERNEL, "Server {} created", server_name);
        }

        return handle;
"""
    server_new = """        if (handle != kernel::INVALID_HANDLE) {
            LOG_TRACE(KERNEL, "Server {} created", server_name);
            LOG_WARN(KERNEL, "[NBOOT1][SERVER_REGISTER] process={} server={} handle={} mode={}",
                crr_pr->name(), server_name, handle, mode);
        } else {
            server_ptr existing = kern->get_by_name<service::server>(server_name);
            LOG_WARN(KERNEL,
                "[NBOOT1][COLLISION] process={} server={} mode={} existing={} existing_hle={}",
                crr_pr->name(), server_name, mode, existing ? existing->name() : std::string("<none>"),
                (existing && existing->is_hle()) ? 1 : 0);
        }

        return handle;
"""
    text = replace_once(text, server_anchor, server_new, "server registration trace")
    missing_anchor = """        if (!server) {
            LOG_TRACE(KERNEL, "Create session to unexist server: {}", server_name);
            return epoc::error_not_found;
        }
"""
    missing_new = """        if (!server) {
            LOG_TRACE(KERNEL, "Create session to unexist server: {}", server_name);
            LOG_WARN(KERNEL, "[NBOOT1][MISSING_SERVER] process={} server={} msg_slots={} mode={}",
                pr->name(), server_name, msg_slot, mode);
            return epoc::error_not_found;
        }
"""
    text = replace_once(text, missing_anchor, missing_new, "missing server trace")
    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot1_b1.py <upstream-root>")
    up = Path(sys.argv[1]).resolve()
    paths = {
        "config": up / "src/emu/config/include/config/config.h",
        "services": up / "src/emu/services/src/init.cpp",
        "system": up / "src/emu/system/src/epoc.cpp",
        "kernel": up / "src/emu/kernel/src/kernel.cpp",
        "process": up / "src/emu/kernel/src/process.cpp",
        "svc": up / "src/emu/kernel/src/svc.cpp",
    }
    for name, path in paths.items():
        if not path.is_file():
            fail(f"missing {name} baseline file: {path}")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")
    menuui_marker = up / "src/emu/services/src/window/classes/wingroup.cpp"
    if not menuui_marker.is_file() or "SYMBIAN-SYSTEMAPPS1 MENUUI36 WG_FOCUS:" not in menuui_marker.read_text(encoding="utf-8"):
        fail("MENUUI36 baseline marker missing")

    patch_config(paths["config"])
    patch_services(paths["services"])
    patch_system_boot(paths["system"])
    patch_kernel_spawn(paths["kernel"])
    patch_process_lifecycle(paths["process"])
    patch_svc(paths["svc"])

    gates = {
        paths["config"]: ["bool native_phone_boot{ true }"],
        paths["services"]: ["[NBOOT1][HLE_POLICY]", "[NBOOT1][C32_READY]", "if (!native_phone_boot)"],
        paths["system"]: ["[NBOOT1][BOOT_MODE]", "[NBOOT1][ESTART_CREATE]", 'u"z:\\\\sys\\\\bin\\\\estart.exe"', "host_sysstart=0 host_menu=0"],
        paths["kernel"]: ["[NBOOT1][PROC_CREATE]", "[NBOOT1][SYSSTART_CREATE]", "[NBOOT1][PROC_CREATE_FAIL]"],
        paths["process"]: ["[NBOOT1][PROC_RUN]", "[NBOOT1][PROC_EXIT]", "[NBOOT1][RENDEZVOUS]"],
        paths["svc"]: ["[NBOOT1][SERVER_REGISTER]", "[NBOOT1][COLLISION]", "[NBOOT1][MISSING_SERVER]"],
    }
    for path, required in gates.items():
        body = path.read_text(encoding="utf-8")
        for gate in required:
            if gate not in body:
                fail(f"gate missing in {path}: {gate}")

    system_body = paths["system"].read_text(encoding="utf-8")
    forbidden = ("PHONE_BOOT_PLAN", "menu3.exe", "sysstart_path", 'spawn_new_process(u"z:\\sys\\bin\\sysstart.exe"')
    for token in forbidden:
        if token in system_body:
            fail(f"forbidden host-driven startup token present: {token}")

    print("NATIVEBOOT1-B1 applied")
    print("handoff=EStart_only")
    print("host_sysstart=DISABLED")
    print("host_menu=DISABLED")
    print("HLE_core=fs,loader,fbs,wserv,hwrm,etel,comm,socket,bt,accessory,skin")
    print("NATIVE_ownership=domainSrv,applist,akncap,view,notifier,keysound,eikappui,system_agent")
    print("C32_core_property=PUBLISHED")
    print("NOJAVA=PRESERVED")
    print("MENUUI36=PRESERVED")

if __name__ == "__main__":
    main()
