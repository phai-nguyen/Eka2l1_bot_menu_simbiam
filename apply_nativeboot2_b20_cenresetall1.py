#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B20 CENRESETALL1 on top of the B19 cache.

B20 fixes the first blocker observed after B19:
    Unimplemented IPC call: 0x1a for server: !CentralRepository

Symbian srvreqs.h defines opcode 26/0x1A as EResetAll, and CRepository::Reset()
is a whole-repository reset to the initialization state. EKA2L1 already defines
cen_rep_reset_all but does not register or route it.

Implementation scope:
- register cen_rep_reset_all on the existing Central Repository server;
- route to a new central_repo_client_subsession::reset_all();
- reject active transaction with KErrNotSupported;
- restore entries + deleted_settings from get_initial_repo();
- preserve the live central_repo object itself (attachments/session pointers);
- persist with the existing write_changes() path;
- emit NATIVEBOOT2 diagnostics.

Intentionally deferred:
- full Symbian PlatSec enforcement;
- exact aggregate notification semantics;
- broader transaction implementation.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B20-CENRESETALL1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b20_cenresetall1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    cen_cpp = up / "src/emu/services/src/centralrepo/centralrepo.cpp"
    repo_h = up / "src/emu/services/include/services/centralrepo/repo.h"
    common_h = up / "src/emu/services/include/services/centralrepo/common.h"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (repo_cpp, cen_cpp, repo_h, common_h, sa_cpp, svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    ch = common_h.read_text(encoding="utf-8")
    if "cen_rep_reset_all" not in ch:
        fail("upstream enum cen_rep_reset_all missing")

    sa = sa_cpp.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_LANG_ABI]",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
        "[NBOOT2][SA_RESPONSE]",
    ):
        if gate not in sa:
            fail(f"B19/B18 SAServer gate missing: {gate}")

    svc_text = svc.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][DM_INIT_SET_INT]",
        "[NBOOT2][DM_INIT_SUBSCRIBE]",
        "[NBOOT2][DM_INIT_GET_INT]",
        "[NBOOT2][RM356_CREATOR_SECURITY]",
        "BRIDGE_REGISTER(0xB1, creator_security_info)",
    ):
        if gate not in svc_text:
            fail(f"B11 gate missing: {gate}")

    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" not in fs.read_text(encoding="utf-8"):
        fail("B10 marker missing")
    if "[NBOOT2][RM356_LOADER_FSY]" not in loader.read_text(encoding="utf-8"):
        fail("B8 marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("ESTART marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    cc = cen_cpp.read_text(encoding="utf-8")

    reg_anchor = '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, cen_rep_reset, "CenRep::Reset");\n'
    reg_new = reg_anchor + (
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_reset_all, "NBOOT2::CenRepResetAll");\n'
    )
    if "NBOOT2::CenRepResetAll" not in cc:
        cc = replace_once(cc, reg_anchor, reg_new, "ResetAll registration")

    route_anchor = """        case cen_rep_reset:
            reset(ctx);
            break;

"""
    route_new = """        case cen_rep_reset:
            reset(ctx);
            break;

        case cen_rep_reset_all:
            reset_all(ctx);
            break;

"""
    if "case cen_rep_reset_all:" not in cc:
        cc = replace_once(cc, route_anchor, route_new, "ResetAll route")

    cen_cpp.write_text(cc, encoding="utf-8")

    rh = repo_h.read_text(encoding="utf-8")
    decl_anchor = "        void reset(service::ipc_context *ctx);\n"
    decl_new = decl_anchor + "        void reset_all(service::ipc_context *ctx);\n"
    if "void reset_all(service::ipc_context *ctx);" not in rh:
        rh = replace_once(rh, decl_anchor, decl_new, "ResetAll declaration")
    repo_h.write_text(rh, encoding="utf-8")

    rp = repo_cpp.read_text(encoding="utf-8")
    impl_anchor = "    void central_repo_client_subsession::create_value(service::ipc_context *ctx) {\n"

    impl = r'''    // NATIVEBOOT2-B20 CENRESETALL1:
    // CRepository::Reset() maps to EResetAll (0x1A). Restore the repository
    // contents from EKA2L1's original ROM/init snapshot, while preserving the
    // live central_repo object's session/attachment bookkeeping.
    void central_repo_client_subsession::reset_all(service::ipc_context *ctx) {
        io_system *io = ctx->sys->get_io_system();
        device_manager *mngr = ctx->sys->get_device_manager();

        if (is_active()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_RESET_ALL_FAIL] repo=0x{:X} reason=transaction_active completion={}",
                attach_repo->uid, epoc::error_not_supported);
            ctx->complete(epoc::error_not_supported);
            return;
        }

        eka2l1::central_repo *init_repo = server->get_initial_repo(io, mngr, attach_repo->uid);
        if (!init_repo) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_RESET_ALL_FAIL] repo=0x{:X} reason=initial_repo_missing completion={}",
                attach_repo->uid, epoc::error_not_found);
            ctx->complete(epoc::error_not_found);
            return;
        }

        const std::size_t runtime_entries = attach_repo->entries.size();
        const std::size_t initial_entries = init_repo->entries.size();
        const std::size_t deleted_before = attach_repo->deleted_settings.size();
        const std::size_t deleted_initial = init_repo->deleted_settings.size();

        std::size_t runtime_only_removed = 0;
        for (const central_repo_entry &runtime_entry : attach_repo->entries) {
            const bool present_in_initial = std::any_of(init_repo->entries.begin(), init_repo->entries.end(),
                [&](const central_repo_entry &initial_entry) {
                    return initial_entry.key == runtime_entry.key;
                });

            if (!present_in_initial) {
                ++runtime_only_removed;
            }
        }

        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_RESET_ALL] repo=0x{:X} runtime_entries={} initial_entries={} "
            "deleted_before={} deleted_initial={} transaction=false",
            attach_repo->uid, runtime_entries, initial_entries, deleted_before, deleted_initial);

        // Do not assign the whole central_repo object: attach_repo->attached
        // contains live subsession pointers and must retain object identity.
        // Entry assignment restores key values and per-entry metadata; copying
        // deleted_settings restores persisted delete state from the init image.
        attach_repo->entries = init_repo->entries;
        attach_repo->deleted_settings = init_repo->deleted_settings;

        write_changes(io, mngr);

        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_RESET_ALL_DONE] repo=0x{:X} restored={} runtime_only_removed={} "
            "deleted_after={} completion=0",
            attach_repo->uid, attach_repo->entries.size(), runtime_only_removed,
            attach_repo->deleted_settings.size());

        ctx->complete(epoc::error_none);
    }

'''
    if "// NATIVEBOOT2-B20 CENRESETALL1:" not in rp:
        rp = replace_once(rp, impl_anchor, impl + impl_anchor, "ResetAll implementation")
    repo_cpp.write_text(rp, encoding="utf-8")

    # Post-apply gates.
    cc = cen_cpp.read_text(encoding="utf-8")
    rh = repo_h.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")

    for needle in (
        'REGISTER_IPC(central_repo_server, redirect_msg_to_session, cen_rep_reset_all, "NBOOT2::CenRepResetAll");',
        "case cen_rep_reset_all:",
        "reset_all(ctx);",
    ):
        if needle not in cc:
            fail(f"post-apply centralrepo.cpp gate missing: {needle}")

    if "void reset_all(service::ipc_context *ctx);" not in rh:
        fail("post-apply repo.h declaration missing")

    for needle in (
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
        "[NBOOT2][CEN_RESET_ALL_FAIL]",
        "attach_repo->entries = init_repo->entries;",
        "attach_repo->deleted_settings = init_repo->deleted_settings;",
        "write_changes(io, mngr);",
    ):
        if needle not in rp:
            fail(f"post-apply repo.cpp gate missing: {needle}")

    print("NATIVEBOOT2-B20 CENRESETALL1 applied")
    print("central_repository_opcode=0x1A_EResetAll")
    print("semantics=RESTORE_INIT_SNAPSHOT")
    print("whole_object_assignment=DISABLED")
    print("transaction_active=KErrNotSupported")
    print("persist=write_changes")
    print("notifications=UNCHANGED_DEFERRED")
    print("platsec=UNCHANGED_DEFERRED")
    print("B19_SALANGABI1=PRESERVED")
    print("B18_SARTC1=PRESERVED")
    print("B17_SAHIDDENRESET1=PRESERVED")
    print("B16_SAMODE1=PRESERVED")
    print("B15_SAASYNC1=PRESERVED")
    print("B14_SARESPONSE1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
