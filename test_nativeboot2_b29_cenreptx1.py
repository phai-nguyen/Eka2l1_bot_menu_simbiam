#!/usr/bin/env python3
"""Source-level contract for NATIVEBOOT2 B29 CENREPTX1.

B29 fixes the first blocker exposed after B28 device validation:
Eiksrv opens the FEP Central Repository, starts a transaction, then leaves
because EKA2L1's transaction lifecycle is stubbed and Set cannot create a
missing setting coherently.

Contract:
- implement real Start/Commit/Cancel transaction state;
- map Symbian transaction modes 1/2/3 without leaking flag bits into mode;
- register and route cen_rep_transaction_commit;
- stage writes while a transaction is active;
- preserve existing entries when staging an update;
- let Set create a missing key with repository default metadata;
- commit staged changes atomically into the live repository, persist once,
  and notify after commit;
- cancel discards staged changes;
- keep implementation generic (no FEP UID/key hardcode);
- preserve B20 ResetAll and B28 LibraryType markers.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B29-CENREPTX1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def block_between(text: str, start_needle: str, end_needle: str, where: str) -> str:
    start = text.find(start_needle)
    if start < 0:
        fail(f"missing block start in {where}: {start_needle}")
    end = text.find(end_needle, start + len(start_needle))
    if end < 0:
        fail(f"missing block end in {where}: {end_needle}")
    return text[start:end]

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b29_cenreptx1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    cen_cpp = up / "src/emu/services/src/centralrepo/centralrepo.cpp"
    repo_h = up / "src/emu/services/include/services/centralrepo/repo.h"
    common_h = up / "src/emu/services/include/services/centralrepo/common.h"
    svc_cpp = up / "src/emu/kernel/src/svc.cpp"

    for p in (repo_cpp, cen_cpp, repo_h, common_h, svc_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    rp = repo_cpp.read_text(encoding="utf-8")
    cc = cen_cpp.read_text(encoding="utf-8")
    rh = repo_h.read_text(encoding="utf-8")
    ch = common_h.read_text(encoding="utf-8")
    svc = svc_cpp.read_text(encoding="utf-8")

    # Protocol already has these opcodes; B29 must implement the existing ABI.
    for needle in (
        "cen_rep_transaction_start",
        "cen_rep_transaction_commit",
        "cen_rep_transaction_cancel",
    ):
        need(ch, needle, "common.h")

    # Commit must be registered and routed, not left as an unhandled opcode.
    need(
        cc,
        'REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_transaction_commit, "NBOOT2::CenRepTransactionCommit");',
        "centralrepo.cpp",
    )
    need(cc, "case cen_rep_transaction_commit:", "centralrepo.cpp")
    need(cc, "commit_transaction(ctx);", "centralrepo.cpp")
    need(rh, "void commit_transaction(service::ipc_context *ctx);", "repo.h")

    # Active flag lives in the high 16 bits; mode must only read the low bits.
    need(
        rh,
        "return static_cast<central_repo_transaction_mode>(flags & 0x0000FFFF);",
        "repo.h",
    )

    start = block_between(
        rp,
        "void central_repo_client_subsession::start_transaction",
        "void central_repo_client_subsession::commit_transaction",
        "repo.cpp",
    )
    commit = block_between(
        rp,
        "void central_repo_client_subsession::commit_transaction",
        "void central_repo_client_subsession::cancel_transaction",
        "repo.cpp",
    )
    cancel = block_between(
        rp,
        "void central_repo_client_subsession::cancel_transaction",
        "\n}",
        "repo.cpp",
    )
    get_entry = block_between(
        rp,
        "central_repo_entry *central_repo_client_subsession::get_entry",
        "bool central_repos_cacher::free_oldest",
        "repo.cpp",
    )
    set_value = block_between(
        rp,
        "void central_repo_client_subsession::set_value",
        "#ifdef _MSC_VER",
        "repo.cpp",
    )

    for needle in (
        "[NBOOT2][CEN_TX_START]",
        "ctx->get_argument_value<std::uint32_t>(0)",
        "set_active(true);",
        "transactor.changes.clear();",
        "central_repo_transaction_mode::read_only",
        "central_repo_transaction_mode::read_write",
    ):
        need(start, needle, "B29 start_transaction")

    for needle in (
        "[NBOOT2][CEN_TX_COMMIT]",
        "transactor.changes",
        "attach_repo->entries",
        "modification_success",
        "write_changes(io, mngr);",
        "ctx->write_data_to_descriptor_argument<std::uint32_t>(0, changed_count);",
        "transactor.changes.clear();",
        "set_active(false);",
    ):
        need(commit, needle, "B29 commit_transaction")

    for needle in (
        "[NBOOT2][CEN_TX_CANCEL]",
        "transactor.changes.clear();",
        "set_active(false);",
    ):
        need(cancel, needle, "B29 cancel_transaction")

    # A staged update must copy the current value; a missing key must receive
    # its key/default metadata and an unset type ready for Set to establish.
    for needle in (
        "transactor.changes.emplace(key, *result)",
        "created.key = key;",
        "created.metadata_val = attach_repo->get_default_meta_for_new_key(key);",
        "created.data.etype = central_repo_entry_type::none;",
    ):
        need(get_entry, needle, "B29 get_entry")

    # Set-on-missing must become a real setting, while type mismatch on an
    # existing setting remains an argument error.
    for needle in (
        "[NBOOT2][CEN_SET_CREATE]",
        "central_repo_entry_type::none",
        "entry->data.etype = central_repo_entry_type::integer;",
        "entry->data.etype = central_repo_entry_type::real;",
        "entry->data.etype = central_repo_entry_type::string;",
    ):
        need(set_value, needle, "B29 set_value")

    for forbidden in (
        "TransactionStart stubbed",
        "TransactionCancel stubbed",
        "0x10272618",
    ):
        if forbidden in rp:
            fail(f"stub/hardcode remains in repo.cpp: {forbidden}")

    # Preserve prior validated milestones.
    for needle in (
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
    ):
        need(rp, needle, "repo.cpp B20 preservation")
    need(svc, "[NBOOT2][WSERV_LIBRARY_TYPE]", "svc.cpp B28 preservation")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
