#!/usr/bin/env python3
"""Apply B29-DIAG1 diagnostics after B29 CENREPTX1.

Diagnostics only: no transaction state, persistence, or Set semantics are
changed. The patch adds high-signal logging around Start/Set/Commit/Cancel
so one device trace can identify the first CenRep divergence.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B29-DIAG1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def replace_in_region(text: str, region_start: str, region_end: str,
                      old: str, new: str, label: str) -> str:
    si=text.find(region_start)
    if si < 0:
        fail(f"{label}: region start missing")
    ei=text.find(region_end, si+len(region_start))
    if ei < 0:
        fail(f"{label}: region end missing")
    region=text[si:ei]
    count=region.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor in region, found {count}")
    region=region.replace(old,new,1)
    return text[:si]+region+text[ei:]

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b29_diag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    repo_cpp=up/"src/emu/services/src/centralrepo/repo.cpp"
    if not repo_cpp.is_file():
        fail(f"missing source file: {repo_cpp}")

    rp=repo_cpp.read_text(encoding="utf-8")

    # Require the build-validated B29 functional baseline.
    for needle in (
        "[NBOOT2][CEN_TX_START]",
        "[NBOOT2][CEN_SET_CREATE]",
        "[NBOOT2][CEN_TX_COMMIT]",
        "[NBOOT2][CEN_TX_CANCEL]",
        "set_active(true);",
        "write_changes(io, mngr);",
    ):
        if needle not in rp:
            fail(f"B29 baseline marker missing: {needle}")

    if "[NBOOT2][CEN_SET_BEGIN]" in rp:
        print(f"{MARK}: already applied")
        return

    # 1) Set entry diagnostics. This is observational only.
    old="""        const std::uint32_t key = key_arg.value();
        central_repo_entry *existing = get_entry(key, 0);
        central_repo_entry *entry = nullptr;
        bool created = false;

        // Parse and validate before creating a missing setting, so a malformed
"""
    new="""        const std::uint32_t key = key_arg.value();
        central_repo_entry *existing = get_entry(key, 0);
        central_repo_entry *entry = nullptr;
        bool created = false;

        int requested_type = -1;
        switch (ctx->msg->function) {
        case cen_rep_set_int:
            requested_type = static_cast<int>(central_repo_entry_type::integer);
            break;
        case cen_rep_set_real:
            requested_type = static_cast<int>(central_repo_entry_type::real);
            break;
        case cen_rep_set_string:
            requested_type = static_cast<int>(central_repo_entry_type::string);
            break;
        default:
            break;
        }

        const int existing_type = existing
            ? static_cast<int>(existing->data.etype)
            : -1;
        const int transaction_mode = is_active()
            ? static_cast<int>(get_transaction_mode())
            : 0;

        if (is_active()) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_BEGIN] repo=0x{:X} key=0x{:08X} function={} active=1 mode={} existing={} existing_type={} requested_type={}",
                attach_repo->uid, key, ctx->msg->function, transaction_mode,
                existing != nullptr, existing_type, requested_type);
        }

        // Parse and validate before creating a missing setting, so a malformed
"""
    rp=replace_once(rp,old,new,"set begin diagnostics")

    old="""        if (!key_arg.has_value()) {
            ctx->complete(epoc::error_argument);
            return;
        }
"""
    new="""        if (!key_arg.has_value()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_FAIL] repo=0x{:X} key_mapped=false reason=missing_key requested_type=-1 existing_type=-1 completion={}",
                attach_repo->uid, epoc::error_argument);
            ctx->complete(epoc::error_argument);
            return;
        }
"""
    rp=replace_once(rp,old,new,"missing key diagnostics")

    # Three typed Set cases: missing input, type mismatch, and write-lock.
    typed=[
        ("integer", "        case cen_rep_set_int: {", "        case cen_rep_set_real: {"),
        ("real", "        case cen_rep_set_real: {", "        case cen_rep_set_string: {"),
        ("string", "        case cen_rep_set_string: {", "        default:"),
    ]
    for enum_name,region_start,region_end in typed:
        old="""            if (!data.has_value()) {
                ctx->complete(epoc::error_argument);
                return;
            }
"""
        new=f"""            if (!data.has_value()) {{
                LOG_ERROR(SERVICE_CENREP,
                    "[NBOOT2][CEN_SET_FAIL] repo=0x{{:X}} key=0x{{:08X}} reason=missing_data requested_type={{}} existing_type={{}} completion={{}}",
                    attach_repo->uid, key,
                    static_cast<int>(central_repo_entry_type::{enum_name}),
                    existing_type, epoc::error_argument);
                ctx->complete(epoc::error_argument);
                return;
            }}
"""
        rp=replace_in_region(rp,region_start,region_end,old,new,
            f"{enum_name} missing-data diagnostics")

        old=f"""            if (existing && (existing->data.etype != central_repo_entry_type::{enum_name})
                && (existing->data.etype != central_repo_entry_type::none)) {{
                ctx->complete(epoc::error_argument);
                return;
            }}
"""
        new=f"""            if (existing && (existing->data.etype != central_repo_entry_type::{enum_name})
                && (existing->data.etype != central_repo_entry_type::none)) {{
                LOG_ERROR(SERVICE_CENREP,
                    "[NBOOT2][CEN_SET_FAIL] repo=0x{{:X}} key=0x{{:08X}} reason=type_mismatch requested_type={{}} existing_type={{}} completion={{}}",
                    attach_repo->uid, key,
                    static_cast<int>(central_repo_entry_type::{enum_name}),
                    existing_type, epoc::error_argument);
                ctx->complete(epoc::error_argument);
                return;
            }}
"""
        rp=replace_in_region(rp,region_start,region_end,old,new,
            f"{enum_name} type diagnostics")

        old="""            if (!entry) {
                ctx->complete(epoc::error_locked);
                return;
            }
"""
        new=f"""            if (!entry) {{
                LOG_ERROR(SERVICE_CENREP,
                    "[NBOOT2][CEN_SET_FAIL] repo=0x{{:X}} key=0x{{:08X}} reason=write_locked requested_type={{}} existing_type={{}} completion={{}}",
                    attach_repo->uid, key,
                    static_cast<int>(central_repo_entry_type::{enum_name}),
                    existing_type, epoc::error_locked);
                ctx->complete(epoc::error_locked);
                return;
            }}
"""
        rp=replace_in_region(rp,region_start,region_end,old,new,
            f"{enum_name} lock diagnostics")

    old="""        if (created) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_CREATE] repo=0x{:X} key=0x{:X} transaction={}",
                attach_repo->uid, key, is_active());
        }
"""
    new="""        if (is_active()) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_RESULT] repo=0x{:X} key=0x{:08X} requested_type={} final_type={} created={} staged=1 completion=0",
                attach_repo->uid, key, requested_type,
                static_cast<int>(entry->data.etype), created);
        }

        if (created) {
            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_SET_CREATE] repo=0x{:X} key=0x{:X} transaction={}",
                attach_repo->uid, key, is_active());
        }
"""
    rp=replace_once(rp,old,new,"set result diagnostics")

    # 2) Commit boundary diagnostics.
    old="""    void central_repo_client_subsession::commit_transaction(service::ipc_context *ctx) {
        if (!is_active()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} active=false completion={}",
                attach_repo->uid, epoc::error_argument);
"""
    new="""    void central_repo_client_subsession::commit_transaction(service::ipc_context *ctx) {
        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_COMMIT_BEGIN] repo=0x{:X} active={} mode={} staged={}",
            attach_repo->uid, is_active(),
            static_cast<int>(get_transaction_mode()), transactor.changes.size());

        if (!is_active()) {
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_COMMIT_FAIL] repo=0x{:X} active=false staged={} key_info=0xFFFFFFFF reason=not_active completion={}",
                attach_repo->uid, transactor.changes.size(), epoc::error_argument);
            LOG_ERROR(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} active=false completion={}",
                attach_repo->uid, epoc::error_argument);
"""
    rp=replace_once(rp,old,new,"commit begin/fail diagnostics")

    old="""            const std::uint32_t key = change.first;
            central_repo_entry &staged = change.second;

            auto result = std::find_if(attach_repo->entries.begin(), attach_repo->entries.end(),
"""
    new="""            const std::uint32_t key = change.first;
            central_repo_entry &staged = change.second;

            LOG_WARN(SERVICE_CENREP,
                "[NBOOT2][CEN_TX_COMMIT_KEY] repo=0x{:X} key=0x{:08X} type={} metadata=0x{:08X}",
                attach_repo->uid, key, static_cast<int>(staged.data.etype),
                staged.metadata_val);

            auto result = std::find_if(attach_repo->entries.begin(), attach_repo->entries.end(),
"""
    rp=replace_once(rp,old,new,"commit per-key diagnostics")

    old="""        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} changed={} active=false completion=0",
            attach_repo->uid, changed_count);
        ctx->complete(epoc::error_none);
"""
    new="""        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_COMMIT_RESULT] repo=0x{:X} changed={} key_info={} active=false completion=0",
            attach_repo->uid, changed_count, changed_count);
        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_COMMIT] repo=0x{:X} changed={} active=false completion=0",
            attach_repo->uid, changed_count);
        ctx->complete(epoc::error_none);
"""
    rp=replace_once(rp,old,new,"commit result diagnostics")

    # 3) Cancel retains the B29 marker but gains mode/staged context.
    old="""        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_CANCEL] repo=0x{:X} discarded={} active=false completion=0",
            attach_repo->uid, discarded);
"""
    new="""        LOG_WARN(SERVICE_CENREP,
            "[NBOOT2][CEN_TX_CANCEL] repo=0x{:X} discarded={} staged=0 mode={} active=false completion=0",
            attach_repo->uid, discarded, static_cast<int>(get_transaction_mode()));
"""
    rp=replace_once(rp,old,new,"cancel diagnostics")

    if "0x10272618" in rp:
        fail("diagnostic patch must remain generic; FEP UID found in repo.cpp")

    repo_cpp.write_text(rp,encoding="utf-8")

    # Post-apply source gates.
    for needle in (
        "[NBOOT2][CEN_SET_BEGIN]",
        "[NBOOT2][CEN_SET_RESULT]",
        "[NBOOT2][CEN_SET_FAIL]",
        "[NBOOT2][CEN_TX_COMMIT_BEGIN]",
        "[NBOOT2][CEN_TX_COMMIT_KEY]",
        "[NBOOT2][CEN_TX_COMMIT_RESULT]",
        "[NBOOT2][CEN_TX_COMMIT_FAIL]",
    ):
        if needle not in rp:
            fail(f"post-apply marker missing: {needle}")

    print(f"{MARK}: applied")
    print("semantics=B29_UNCHANGED")
    print("scope=CENREP_TRANSACTION_DIAGNOSTICS_ONLY")
    print("hardcoded_fep_uid=NONE")

if __name__=="__main__":
    main()
