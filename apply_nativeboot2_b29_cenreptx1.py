#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B29 CENREPTX1 on top of the B28 FASTBUILD baseline.

B29 fixes the first blocker exposed by the B28 device trace:
UIKON/Eiksrv opens the FEP Central Repository, starts a transaction, writes
settings, and commits. Upstream EKA2L1 currently stubs Start/Cancel, leaves
Commit unregistered/unhandled, and cannot Set a missing key correctly.

This patch is generic Central Repository compatibility. It does not hardcode
the FEP repository UID or any Nokia-specific key/value.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B29-CENREPTX1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def replace_region(text: str, start: str, end: str, replacement: str, label: str) -> str:
    si = text.find(start)
    if si < 0:
        fail(f"{label}: start anchor missing")
    ei = text.find(end, si + len(start))
    if ei < 0:
        fail(f"{label}: end anchor missing")
    return text[:si] + replacement + text[ei:]

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b29_cenreptx1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    cen_cpp = up / "src/emu/services/src/centralrepo/centralrepo.cpp"
    repo_h = up / "src/emu/services/include/services/centralrepo/repo.h"
    common_h = up / "src/emu/services/include/services/centralrepo/common.h"
    svc_cpp = up / "src/emu/kernel/src/svc.cpp"

    for p in (repo_cpp, cen_cpp, repo_h, common_h, svc_cpp):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    ch = common_h.read_text(encoding="utf-8")
    for needle in (
        "cen_rep_transaction_start",
        "cen_rep_transaction_commit",
        "cen_rep_transaction_cancel",
    ):
        if needle not in ch:
            fail(f"protocol opcode missing: {needle}")

    rp = repo_cpp.read_text(encoding="utf-8")
    if "[NBOOT2][CEN_RESET_ALL]" not in rp:
        fail("B20 CENRESETALL1 marker missing")
    if "[NBOOT2][WSERV_LIBRARY_TYPE]" not in svc_cpp.read_text(encoding="utf-8"):
        fail("B28 WSERVLIBTYPE1 marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    # Register and route the already-defined commit opcode.
    cc = cen_cpp.read_text(encoding="utf-8")
    reg_old = (
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_start, "CenRep::TransactionStart");\n'
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_cancel, "CenRep::TransactionCancel");\n'
    )
    reg_new = (
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_start, "CenRep::TransactionStart");\n'
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_commit, "NBOOT2::CenRepTransactionCommit");\n'
        '        REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_cancel, "CenRep::TransactionCancel");\n'
    )
    if "NBOOT2::CenRepTransactionCommit" not in cc:
        cc = replace_once(cc, reg_old, reg_new, "transaction commit registration")

    route_old = """        case cen_rep_transaction_start:
            start_transaction(ctx);
            break;

        case cen_rep_transaction_cancel:
            cancel_transaction(ctx);
            break;
"""
    route_new = """        case cen_rep_transaction_start:
            start_transaction(ctx);
            break;

        case cen_rep_transaction_commit:
            commit_transaction(ctx);
            break;

        case cen_rep_transaction_cancel:
            cancel_transaction(ctx);
            break;
"""
    if "case cen_rep_transaction_commit:" not in cc:
        cc = replace_once(cc, route_old, route_new, "transaction commit route")
    cen_cpp.write_text(cc, encoding="utf-8")

    # Add declaration and fix the low/high-half flag decoding bug.
    rh = repo_h.read_text(encoding="utf-8")
    decl_old = """        void start_transaction(service::ipc_context *ctx);
        void cancel_transaction(service::ipc_context *ctx);
"""
    decl_new = """        void start_transaction(service::ipc_context *ctx);
        void commit_transaction(service::ipc_context *ctx);
        void cancel_transaction(service::ipc_context *ctx);
"""
    if "void commit_transaction(service::ipc_context *ctx);" not in rh:
        rh = replace_once(rh, decl_old, decl_new, "commit declaration")

    mode_old = """        central_repo_transaction_mode get_transaction_mode() {
            return static_cast<central_repo_transaction_mode>(flags);
        }
"""
    mode_new = """        central_repo_transaction_mode get_transaction_mode() {
            return static_cast<central_repo_transaction_mode>(flags & 0x0000FFFF);
        }
"""
    if "flags & 0x0000FFFF" not in rh:
        rh = replace_once(rh, mode_old, mode_new, "transaction mode mask")
    repo_h.write_text(rh, encoding="utf-8")

    rp = repo_cpp.read_text(encoding="utf-8")

    get_entry_new = r'''    central_repo_entry *central_repo_client_subsession::get_entry(const std::uint32_t key, int mode) {
        const bool active = is_active();

        // A write in a read transaction is locked. Outside a transaction,
        // the default mode stored in flags must not affect normal Set calls.
        if (active && (mode == 1)
            && (get_transaction_mode() == central_repo_transaction_mode::read_only)) {
            return nullptr;
        }

        if (active) {
            auto changed = transactor.changes.find(key);
            if (changed != transactor.changes.end()) {
                return &(changed->second);
            }

            auto result = std::find_if(attach_repo->entries.begin(), attach_repo->entries.end(),
                [&](const central_repo_entry &entry) { return entry.key == key; });

            // Reads see committed state when the key has not been staged yet.
            if (mode == 0) {
                return (result == attach_repo->entries.end()) ? nullptr : &(*result);
            }

            // Writes are copy-on-write: preserve type/value/meta for existing
            // keys, or create an empty typed-later staging entry for Set.
            if (result != attach_repo->entries.end()) {
                auto inserted = transactor.changes.emplace(key, *result);
                return &(inserted.first->second);
            }

            central_repo_entry created{};
            created.key = key;
            created.metadata_val = attach_repo->get_default_meta_for_new_key(key);
            created.data.etype = central_repo_entry_type::none;
            auto inserted = transactor.changes.emplace(key, created);
            return &(inserted.first->second);
        }

        auto result = std::find_if(attach_repo->entries.begin(), attach_repo->entries.end(),
            [&](const central_repo_entry &entry) { return entry.key == key; });

        if (result != attach_repo->entries.end()) {
            return &(*result);
        }

        if (mode == 0) {
            return nullptr;
        }

        // Symbian CRepository::Set creates the setting when it does not exist.
        central_repo_entry created{};
        created.key = key;
        created.metadata_val = attach_repo->get_default_meta_for_new_key(key);
        created.data.etype = central_repo_entry_type::none;
        attach_repo->entries.push_back(created);
        return &(attach_repo->entries.back());
    }

'''
    if "Symbian CRepository::Set creates the setting" not in rp:
        rp = replace_region(
            rp,
            "    central_repo_entry *central_repo_client_subsession::get_entry",
            "    bool central_repos_cacher::free_oldest",
            get_entry_new,
            "get_entry replacement",
        )

    set_value_new = r'''    void central_repo_client_subsession::set_value(service::ipc_context *ctx) {
        const std::optional<std::uint32_t> key_arg = ctx->get_argument_value<std::uint32_t>(0);
        if (!key_arg.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }

        const std::uint32_t key = key_arg.value();
        central_repo_entry *existing = get_entry(key, 0);
        central_repo_entry *entry = nullptr;
        bool created = false;

        // Parse and validate before creating a missing setting, so a malformed
        // IPC request cannot leave an empty placeholder behind.
        switch (ctx->msg->function) {
        case cen_rep_set_int: {
            const std::optional<std::uint32_t> data = ctx->get_argument_value<std::uint32_t>(1);
            if (!data.has_value()) {
                ctx->complete(epoc::error_argument);
                return;
            }
            if (existing && (existing->data.etype != central_repo_entry_type::integer)
                && (existing->data.etype != central_repo_entry_type::none)) {
                ctx->complete(epoc::error_argument);
                return;
            }

            entry = get_entry(key, 1);
            if (!entry) {
                ctx->complete(epoc::error_locked);
                return;
            }

            created = (entry->data.etype == central_repo_entry_type::none);
            entry->data.etype = central_repo_entry_type::integer;
            entry->data.intd = static_cast<std::uint64_t>(data.value());
            break;
        }

        case cen_rep_set_real: {
            const std::optional<double> data = ctx->get_argument_data_from_descriptor<double>(1);
            if (!data.has_value()) {
                ctx->complete(epoc::error_argument);
                return;
            }
            if (existing && (existing->data.etype != central_repo_entry_type::real)
                && (existing->data.etype != central_repo_entry_type::none)) {
                ctx->complete(epoc::error_argument);
                return;
            }

            entry = get_entry(key, 1);
            if (!entry) {
                ctx->complete(epoc::error_locked);
                return;
            }

            created = (entry->data.etype == central_repo_entry_type::none);
            entry->data.etype = central_repo_entry_type::real;
            entry->data.reald = data.value();
            break;
        }

        case cen_rep_set_string: {
            const std::optional<std::string> data = ctx->get_argument_value<std::string>(1);
            if (!data.has_value()) {
                ctx->complete(epoc::error_argument);
                return;
            }
            if (existing && (existing->data.etype != central_repo_entry_type::string)
                && (existing->data.etype != central_repo_entry_type::none)) {
                ctx->complete(epoc::error_argument);
                return;
            }

            entry = get_entry(key, 1);
            if (!entry) {
                ctx->complete(epoc::error_locked);
                return;
            }

            created = (entry->data.etype == central_repo_entry_type::none);
            entry->data.etype = central_repo_entry_type::string;
            entry->data.strd = data.value();
            break;
        }

        default:
            ctx->complete(epoc::error_not_supported);
            return;
        }

        if (created) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_CREATE] repo=0x{:X} key=0x{:X} transaction={}",
                attach_repo->uid, key, is_active());
        }

        // Notifications for staged changes are deferred until Commit.
        if (!is_active()) {
            auto &deleted = attach_repo->deleted_settings;
            deleted.erase(std::remove(deleted.begin(), deleted.end(), key), deleted.end());
            modification_success(key);
        }

        ctx->complete(epoc::error_none);
    }

'''
    if "[NBOOT2][CEN_SET_CREATE]" not in rp:
        rp = replace_region(
            rp,
            "    void central_repo_client_subsession::set_value",
            "#ifdef _MSC_VER",
            set_value_new,
            "set_value replacement",
        )

    tx_old = r'''    void central_repo_client_subsession::start_transaction(service::ipc_context *ctx) {
        LOG_TRACE(SERVICE_CENREP, "TransactionStart stubbed");
        ctx->complete(epoc::error_none);
    }

    void central_repo_client_subsession::cancel_transaction(service::ipc_context *ctx) {
        LOG_TRACE(SERVICE_CENREP, "TransactionCancel stubbed");
        ctx->complete(epoc::error_none);
    }
'''
    tx_new = r'''    // NATIVEBOOT2-B29 CENREPTX1:
    // Implement the synchronous transaction path used by S60 UIKON/FEP.
    // Mode values follow CRepository::TTransactionMode:
    // 1=read, 2=concurrent read/write, 3=read/write.
    void central_repo_client_subsession::start_transaction(service::ipc_context *ctx) {
        const std::optional<std::uint32_t> requested_mode = ctx->get_argument_value<std::uint32_t>(0);
        if (!requested_mode.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }

        if (is_active()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_START] repo=0x{:X} mode={} already_active=true completion={}",
                attach_repo->uid, requested_mode.value(), epoc::error_in_use);
            ctx->complete(epoc::error_in_use);
            return;
        }

        central_repo_transaction_mode mode = central_repo_transaction_mode::read_write;
        switch (requested_mode.value()) {
        case 1:
            mode = central_repo_transaction_mode::read_only;
            break;
        case 2:
        case 3:
            mode = central_repo_transaction_mode::read_write;
            break;
        default:
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_START] repo=0x{:X} mode={} invalid=true completion={}",
                attach_repo->uid, requested_mode.value(), epoc::error_argument);
            ctx->complete(epoc::error_argument);
            return;
        }

        transactor.changes.clear();
        set_transaction_mode(mode);
        set_active(true);

        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_START] repo=0x{:X} mode={} active=true completion=0",
            attach_repo->uid, requested_mode.value());
        ctx->complete(epoc::error_none);
    }

    void central_repo_client_subsession::commit_transaction(service::ipc_context *ctx) {
        if (!is_active()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} active=false completion={}",
                attach_repo->uid, epoc::error_argument);
            ctx->complete(epoc::error_argument);
            return;
        }

        io_system *io = ctx->sys->get_io_system();
        device_manager *mngr = ctx->sys->get_device_manager();
        const std::uint32_t changed_count =
            static_cast<std::uint32_t>(transactor.changes.size());
        std::vector<std::uint32_t> changed_keys;
        changed_keys.reserve(transactor.changes.size());

        for (auto &change : transactor.changes) {
            const std::uint32_t key = change.first;
            central_repo_entry &staged = change.second;

            auto result = std::find_if(attach_repo->entries.begin(), attach_repo->entries.end(),
                [&](const central_repo_entry &entry) { return entry.key == key; });

            if (result != attach_repo->entries.end()) {
                *result = staged;
            } else {
                attach_repo->entries.push_back(staged);
            }

            auto &deleted = attach_repo->deleted_settings;
            deleted.erase(std::remove(deleted.begin(), deleted.end(), key), deleted.end());
            changed_keys.push_back(key);
        }

        transactor.changes.clear();
        set_active(false);

        // Persist once after the complete staged set has been installed.
        write_changes(io, mngr);

        for (const std::uint32_t key : changed_keys) {
            modification_success(key);
        }

        // CRepository::CommitTransaction(TUint32&) passes TPckg<TUint32>
        // in descriptor argument 0. On success it contains changed count.
        ctx->write_data_to_descriptor_argument<std::uint32_t>(0, changed_count);

        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} changed={} active=false completion=0",
            attach_repo->uid, changed_count);
        ctx->complete(epoc::error_none);
    }

    void central_repo_client_subsession::cancel_transaction(service::ipc_context *ctx) {
        const std::size_t discarded = transactor.changes.size();
        transactor.changes.clear();
        set_active(false);

        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_CANCEL] repo=0x{:X} discarded={} active=false completion=0",
            attach_repo->uid, discarded);
        ctx->complete(epoc::error_none);
    }
'''
    if "[NBOOT2][CEN_TX_START]" not in rp:
        rp = replace_once(rp, tx_old, tx_new, "transaction implementation")

    repo_cpp.write_text(rp, encoding="utf-8")

    # Post-apply gates.
    cc = cen_cpp.read_text(encoding="utf-8")
    rh = repo_h.read_text(encoding="utf-8")
    rp = repo_cpp.read_text(encoding="utf-8")

    for needle in (
        'cen_rep_transaction_commit, "NBOOT2::CenRepTransactionCommit"',
        "case cen_rep_transaction_commit:",
        "commit_transaction(ctx);",
    ):
        if needle not in cc:
            fail(f"post-apply centralrepo.cpp gate missing: {needle}")

    for needle in (
        "void commit_transaction(service::ipc_context *ctx);",
        "flags & 0x0000FFFF",
    ):
        if needle not in rh:
            fail(f"post-apply repo.h gate missing: {needle}")

    for needle in (
        "[NBOOT2][CEN_TX_START]",
        "[NBOOT2][CEN_TX_COMMIT]",
        "[NBOOT2][CEN_TX_CANCEL]",
        "[NBOOT2][CEN_SET_CREATE]",
        "set_active(true);",
        "set_active(false);",
        "write_changes(io, mngr);",
    ):
        if needle not in rp:
            fail(f"post-apply repo.cpp gate missing: {needle}")

    if "TransactionStart stubbed" in rp or "TransactionCancel stubbed" in rp:
        fail("transaction stub remains")
    if "0x10272618" in rp:
        fail("FEP repository UID hardcoded into generic transaction code")

    print("NATIVEBOOT2-B29 CENREPTX1 applied")
    print("transaction_start=ACTIVE")
    print("transaction_commit=REGISTERED_ROUTED_PERSISTED")
    print("transaction_cancel=DISCARD_STAGED")
    print("set_missing=CREATE_WITH_DEFAULT_META")
    print("notifications=DEFERRED_UNTIL_COMMIT")
    print("fep_hardcode=NONE")
    print("B20_RESETALL1=PRESERVED")
    print("B28_WSERVLIBTYPE1=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
