#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B22 FBSDEFAULTTYPEFACE1 on top of B21.

B21 device evidence:
- EFbsMessFontNameAlias/0x1E now completes with System One -> Series 60 Sans.
- In the same millisecond AknCapServer issues FBS opcode 0x2D and stalls.
- ~30 seconds later Domino kills AknCapServer with KErrTimedOut.
- native-mode exit logs BRIDGE_EXIT but never reaches the stable restart.

Symbian 9.4 identifies opcode 45/0x2D as
EFbsSetSystemDefaultTypefaceName. CFbsTypefaceStore sends a single UTF-16
descriptor in slot 0; FBServ stores the typeface name and uses it when a
nearest-font request has an empty typeface name. KMaxTypefaceNameLength is
0x18 characters. Empty name disables the system default.

B22 functional change:
- implement the real 0x2D IPC and persistent font-store state;
- honor the default typeface only for empty requested names;
- preserve B21 FontNameAlias semantics.

B22 exit change is diagnostic ONLY:
- add deterministic phase markers around the existing shutdown_threads,
  pthread joins, state destruction and stable restart;
- do not reorder, add, remove or otherwise alter teardown operations.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B22-FBSDEFAULTTYPEFACE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b22_fbsdefaulttypeface1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    fbs_h = up / "src/emu/services/include/services/fbs/fbs.h"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    store_h = up / "src/emu/services/include/services/fbs/font_store.h"
    bridge = up / "src/emu/ios/src/emu_bridge.mm"
    thread_cpp = up / "src/emu/ios/src/thread.cpp"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (fbs_cpp, fbs_h, store_cpp, store_h, bridge, thread_cpp,
              repo_cpp, sa_cpp, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    # B21 checkpoint gates.
    fc = fbs_cpp.read_text(encoding="utf-8")
    fh = fbs_h.read_text(encoding="utf-8")
    sc = store_cpp.read_text(encoding="utf-8")
    sh = store_h.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][FBS_FONT_ALIAS]",
        "case fbs_font_name_alias:",
        "set_font_name_alias(ctx);",
    ):
        if gate not in fc:
            fail(f"B21 fbs.cpp gate missing: {gate}")
    for gate in (
        "font_name_aliases_",
        "resolve_font_name_alias(const std::u16string &alias) const",
    ):
        if gate not in sh:
            fail(f"B21 font_store.h gate missing: {gate}")
    for gate in (
        "font_store::set_font_name_alias",
        "font_store::resolve_font_name_alias",
        "resolve_font_name_alias(requested_name)",
    ):
        if gate not in sc:
            fail(f"B21 font_store.cpp gate missing: {gate}")

    rp = repo_cpp.read_text(encoding="utf-8")
    for gate in ("[NBOOT2][CEN_RESET_ALL]", "[NBOOT2][CEN_RESET_ALL_DONE]"):
        if gate not in rp:
            fail(f"B20 gate missing: {gate}")

    sa = sa_cpp.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_LANG_ABI]",
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
    ):
        if gate not in sa:
            fail(f"SA gate missing: {gate}")

    if "fbs_set_system_default_typeface_name" not in fh:
        fail("public FBS enum lacks fbs_set_system_default_typeface_name")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("ESTART marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # ------------------------------------------------------------------
    # FBS public session API.
    # ------------------------------------------------------------------
    decl_anchor = "        void set_font_name_alias(service::ipc_context *ctx);\n"
    decl_new = decl_anchor + "        void set_system_default_typeface_name(service::ipc_context *ctx);\n"
    if "void set_system_default_typeface_name(service::ipc_context *ctx);" not in fh:
        fh = replace_once(fh, decl_anchor, decl_new, "FBS default-typeface declaration")
    fbs_h.write_text(fh, encoding="utf-8")

    # ------------------------------------------------------------------
    # Persistent font-store state/API.
    # ------------------------------------------------------------------
    member_anchor = "        std::vector<std::pair<std::u16string, std::u16string>> font_name_aliases_;\n"
    member_new = member_anchor + (
        "\n        // NATIVEBOOT2-B22: FBServ's system default typeface. An empty\n"
        "        // value disables the override, matching CFbTop.\n"
        "        std::u16string system_default_typeface_name_;\n"
    )
    if "system_default_typeface_name_;" not in sh:
        sh = replace_once(sh, member_anchor, member_new, "system default typeface storage")

    api_anchor = (
        "        std::optional<std::u16string> resolve_font_name_alias(const std::u16string &alias) const;\n\n"
        "        open_font_info *seek_the_open_font(epoc::font_spec_base &spec);\n"
    )
    api_new = (
        "        std::optional<std::u16string> resolve_font_name_alias(const std::u16string &alias) const;\n"
        "        void set_system_default_typeface_name(const std::u16string &name);\n"
        "        const std::u16string &system_default_typeface_name() const;\n\n"
        "        open_font_info *seek_the_open_font(epoc::font_spec_base &spec);\n"
    )
    if "void set_system_default_typeface_name(const std::u16string &name);" not in sh:
        sh = replace_once(sh, api_anchor, api_new, "system default typeface API")
    store_h.write_text(sh, encoding="utf-8")

    sc = store_cpp.read_text(encoding="utf-8")
    seek_anchor = "    open_font_info *font_store::seek_the_open_font(epoc::font_spec_base &spec) {\n"
    store_impl = r'''    // NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1:
    void font_store::set_system_default_typeface_name(const std::u16string &name) {
        system_default_typeface_name_ = name;
    }

    const std::u16string &font_store::system_default_typeface_name() const {
        return system_default_typeface_name_;
    }

'''
    if "// NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1:" not in sc:
        sc = replace_once(sc, seek_anchor, store_impl + seek_anchor, "default typeface store implementation")

    old_lookup = """        const std::u16string requested_name = spec.tf.name.to_std_string(nullptr);

        // Symbian tries the requested name before consulting the alias table.
        for (auto &info : open_font_store) {
            if (info.face_attrib.name.to_std_string(nullptr) == requested_name) {
                return &info;
            }
        }

        const std::optional<std::u16string> aliased_name = resolve_font_name_alias(requested_name);
        const std::u16string my_name = aliased_name.has_value() ? *aliased_name : requested_name;
"""
    new_lookup = """        const std::u16string requested_name = spec.tf.name.to_std_string(nullptr);
        const bool using_system_default =
            requested_name.empty() && !system_default_typeface_name().empty();
        const std::u16string effective_requested_name =
            using_system_default ? system_default_typeface_name() : requested_name;

        // A system default is a real typeface name, not an alias. For a normal
        // named request preserve B21: requested name first, alias only if needed.
        for (auto &info : open_font_store) {
            if (info.face_attrib.name.to_std_string(nullptr) == effective_requested_name) {
                return &info;
            }
        }

        const std::optional<std::u16string> aliased_name =
            using_system_default ? std::nullopt : resolve_font_name_alias(effective_requested_name);
        const std::u16string my_name =
            aliased_name.has_value() ? *aliased_name : effective_requested_name;
"""
    if "effective_requested_name" not in sc:
        sc = replace_once(sc, old_lookup, new_lookup, "default-aware legacy font lookup")
    store_cpp.write_text(sc, encoding="utf-8")

    # ------------------------------------------------------------------
    # FBS 0x2D handler.
    # ------------------------------------------------------------------
    fc = fbs_cpp.read_text(encoding="utf-8")
    fetch_anchor = "    void fbscli::fetch(service::ipc_context *ctx) {\n"
    handler = r'''    // NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1:
    // Symbian 9.4 CFbsTypefaceStore::SetSystemDefaultTypefaceNameL sends a
    // single UTF-16 descriptor in slot 0. KMaxTypefaceNameLength is 0x18.
    void fbscli::set_system_default_typeface_name(service::ipc_context *ctx) {
        constexpr std::size_t KMaxTypefaceNameLength = 0x18;

        const std::optional<std::u16string> name =
            ctx->get_argument_value<std::u16string>(0);

        if (!name.has_value()) {
            LOG_ERROR(SERVICE_FBS,
                "[NBOOT2][FBS_DEFAULT_TYPEFACE] action=invalid reason=descriptor completion={}",
                epoc::error_bad_descriptor);
            ctx->complete(epoc::error_bad_descriptor);
            return;
        }

        if (name->size() > KMaxTypefaceNameLength) {
            LOG_ERROR(SERVICE_FBS,
                "[NBOOT2][FBS_DEFAULT_TYPEFACE] action=invalid reason=too_big length={} max={} completion={}",
                name->size(), KMaxTypefaceNameLength, epoc::error_too_big);
            ctx->complete(epoc::error_too_big);
            return;
        }

        server<fbs_server>()->persistent_font_store.set_system_default_typeface_name(*name);

        LOG_WARN(SERVICE_FBS,
            "[NBOOT2][FBS_DEFAULT_TYPEFACE] action={} name={} length={} completion=0",
            name->empty() ? "clear" : "set", common::ucs2_to_utf8(*name), name->size());

        ctx->complete(epoc::error_none);
    }

'''
    if "// NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1:" not in fc:
        fc = replace_once(fc, fetch_anchor, handler + fetch_anchor, "FBS default-typeface handler")

    route_anchor = """        case fbs_font_name_alias:
            set_font_name_alias(ctx);
            break;

"""
    route_new = route_anchor + """        case fbs_set_system_default_typeface_name:
            set_system_default_typeface_name(ctx);
            break;

"""
    if "case fbs_set_system_default_typeface_name:" not in fc:
        fc = replace_once(fc, route_anchor, route_new, "FBS 0x2D route")
    fbs_cpp.write_text(fc, encoding="utf-8")

    # ------------------------------------------------------------------
    # Exit diagnostics ONLY. No teardown semantics are changed.
    # ------------------------------------------------------------------
    br = bridge.read_text(encoding="utf-8")
    shutdown_old = """        void shutdown_locked() {
            if (!g_running || !g_state) {
                return;
            }
            eka2l1::ios::shutdown_threads(*g_state);
            g_state.reset();
            g_running = false;
            g_has_device = false;
        }
"""
    shutdown_new = """        void shutdown_locked() {
            if (!g_running || !g_state) {
                return;
            }
            LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_threads_begin");
            eka2l1::ios::shutdown_threads(*g_state);
            LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_threads_done");
            LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=state_reset_begin");
            g_state.reset();
            LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=state_reset_done");
            g_running = false;
            g_has_device = false;
        }
"""
    if "phase=shutdown_threads_begin" not in br:
        br = replace_once(br, shutdown_old, shutdown_new, "shutdown_locked diagnostics")

    stop_old = """    void stop_native_phone() {
        std::lock_guard<std::mutex> guard(g_mutex);
        if (!g_native_phone_mode) {
            return;
        }
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode");
        g_native_phone_mode = false;
        shutdown_locked();
        start_locked();
    }
"""
    stop_new = """    void stop_native_phone() {
        std::lock_guard<std::mutex> guard(g_mutex);
        if (!g_native_phone_mode) {
            return;
        }
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode");
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=exit_requested");
        g_native_phone_mode = false;
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_begin");
        shutdown_locked();
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_done");
        LOG_WARN(FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_begin");
        start_locked();
        LOG_WARN(FRONTEND_CMDLINE,
            "[NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done has_device={}",
            g_has_device ? 1 : 0);
    }
"""
    if "phase=exit_requested" not in br:
        br = replace_once(br, stop_old, stop_new, "stop_native_phone diagnostics")
    bridge.write_text(br, encoding="utf-8")

    th = thread_cpp.read_text(encoding="utf-8")
    if "#include <common/log.h>" not in th:
        first_include = th.find("#include ")
        if first_include < 0:
            fail("thread.cpp has no include anchor")
        th = th[:first_include] + "#include <common/log.h>\n" + th[first_include:]

    # Instrument exact existing operations. The calls/order are unchanged.
    if "phase=flags_set" not in th:
        th = replace_once(
            th,
            """        state.should_emu_quit = true;
        state.should_emu_pause = false;
        state.should_graphics_pause = false;
""",
            """        state.should_emu_quit = true;
        state.should_emu_pause = false;
        state.should_graphics_pause = false;
        LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=flags_set");
""",
            "shutdown flags marker")

        th = replace_once(
            th,
            """        if (os_thread_started && state.symsys) {
            state.symsys->request_exit();
            if (auto *kern = state.symsys->get_kernel_system()) {
                kern->stop_cores_idling();
            }
        }
""",
            """        if (os_thread_started && state.symsys) {
            LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=request_exit");
            state.symsys->request_exit();
            if (auto *kern = state.symsys->get_kernel_system()) {
                LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=core_wakeup");
                kern->stop_cores_idling();
            }
        }
""",
            "request_exit/core wake markers")

        th = replace_once(
            th,
            """        state.pause_sema.notify();
        if (os_thread_started) {
            pthread_join(os_thread_handle, nullptr);
            os_thread_started = false;
        }
""",
            """        state.pause_sema.notify();
        if (os_thread_started) {
            LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin");
            pthread_join(os_thread_handle, nullptr);
            LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_done");
            os_thread_started = false;
        }
""",
            "OS join markers")

        th = replace_once(
            th,
            """        state.pause_graphics_sema.notify();
        if (state.graphics_driver) {
            state.graphics_driver->abort();
        }
        if (gr_thread_started) {
            pthread_join(gr_thread_handle, nullptr);
            gr_thread_started = false;
        }
""",
            """        state.pause_graphics_sema.notify();
        LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=graphics_abort");
        if (state.graphics_driver) {
            state.graphics_driver->abort();
        }
        if (gr_thread_started) {
            LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=graphics_join_begin");
            pthread_join(gr_thread_handle, nullptr);
            LOG_WARN(eka2l1::FRONTEND_CMDLINE, "[NBOOT2][BRIDGE_EXIT_PHASE] phase=graphics_join_done");
            gr_thread_started = false;
        }
""",
            "graphics teardown markers")

    thread_cpp.write_text(th, encoding="utf-8")

    # ------------------------------------------------------------------
    # Post-apply gates.
    # ------------------------------------------------------------------
    fc = fbs_cpp.read_text(encoding="utf-8")
    fh = fbs_h.read_text(encoding="utf-8")
    sc = store_cpp.read_text(encoding="utf-8")
    sh = store_h.read_text(encoding="utf-8")
    br = bridge.read_text(encoding="utf-8")
    th = thread_cpp.read_text(encoding="utf-8")

    for needle in (
        "[NBOOT2][FBS_DEFAULT_TYPEFACE]",
        "case fbs_set_system_default_typeface_name:",
        "set_system_default_typeface_name(ctx);",
        "KMaxTypefaceNameLength = 0x18",
        "epoc::error_too_big",
        "persistent_font_store.set_system_default_typeface_name",
        "[NBOOT2][FBS_FONT_ALIAS]",
    ):
        if needle not in fc:
            fail(f"post-apply fbs.cpp gate missing: {needle}")

    for needle in (
        "system_default_typeface_name_",
        "set_system_default_typeface_name(const std::u16string &name)",
        "system_default_typeface_name() const",
    ):
        if needle not in sh:
            fail(f"post-apply font_store.h gate missing: {needle}")

    for needle in (
        "font_store::set_system_default_typeface_name",
        "font_store::system_default_typeface_name() const",
        "requested_name.empty()",
        "effective_requested_name",
        "resolve_font_name_alias(effective_requested_name)",
        "using_system_default",
    ):
        if needle not in sc:
            fail(f"post-apply font_store.cpp gate missing: {needle}")

    for phase in (
        "exit_requested", "shutdown_begin", "shutdown_threads_begin",
        "shutdown_threads_done", "state_reset_begin", "state_reset_done",
        "shutdown_done", "normal_restart_begin", "normal_restart_done",
    ):
        if f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}" not in br:
            fail(f"bridge exit marker missing: {phase}")

    for phase in (
        "flags_set", "request_exit", "core_wakeup", "os_join_begin",
        "os_join_done", "graphics_abort", "graphics_join_begin",
        "graphics_join_done",
    ):
        if f"[NBOOT2][BRIDGE_EXIT_PHASE] phase={phase}" not in th:
            fail(f"thread exit marker missing: {phase}")

    print("NATIVEBOOT2-B22 FBSDEFAULTTYPEFACE1 applied")
    print("fbs_opcode=0x2D_EFbsSetSystemDefaultTypefaceName")
    print("ipc_abi=slot0_utf16_typeface_descriptor")
    print("max_typeface_chars=0x18")
    print("empty_name=CLEAR_SYSTEM_DEFAULT")
    print("nearest_font_empty_name=USE_SYSTEM_DEFAULT")
    print("default_alias_resolution=DISABLED")
    print("valid_completion=KErrNone")
    print("oversize_completion=KErrTooBig")
    print("malformed_completion=KErrBadDescriptor")
    print("exit_behavior=UNCHANGED_DIAGNOSTIC_ONLY")
    print("B21_FBSFONTALIAS1=PRESERVED")
    print("B20_CENRESETALL1=PRESERVED")
    print("B19_SALANGABI1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
