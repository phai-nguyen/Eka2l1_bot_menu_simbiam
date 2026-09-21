#!/usr/bin/env python3
"""Source-level contract for NATIVEBOOT2 B20 CENRESETALL1.

B20 must implement Central Repository EResetAll (opcode 0x1A) as a real
repository reset, not a synthetic KErrNone acknowledgement.

Contract:
- register cen_rep_reset_all on !CentralRepository;
- route it through the existing client subsession;
- reject an active transaction with KErrNotSupported;
- load the original repository snapshot with get_initial_repo();
- restore entries and deleted-settings state without replacing the whole
  central_repo object (which owns live attachment/session bookkeeping);
- persist through the existing write_changes() path;
- emit deterministic NATIVEBOOT2 diagnostics;
- preserve B19 and earlier boot markers.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B20-CENRESETALL1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b20_cenresetall1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    cen_cpp = up / "src/emu/services/src/centralrepo/centralrepo.cpp"
    repo_h = up / "src/emu/services/include/services/centralrepo/repo.h"
    common_h = up / "src/emu/services/include/services/centralrepo/common.h"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"

    for p in (repo_cpp, cen_cpp, repo_h, common_h, sa_cpp):
        if not p.is_file():
            fail(f"missing source file: {p}")

    rp = repo_cpp.read_text(encoding="utf-8")
    cc = cen_cpp.read_text(encoding="utf-8")
    rh = repo_h.read_text(encoding="utf-8")
    ch = common_h.read_text(encoding="utf-8")
    sa = sa_cpp.read_text(encoding="utf-8")

    # Upstream already defines opcode 26; B20 must implement it rather than
    # introducing a private opcode.
    need(ch, "cen_rep_reset_all", "common.h")

    required_register = (
        'REGISTER_IPC(central_repo_server, redirect_msg_to_session, '
        'cen_rep_reset_all, "NBOOT2::CenRepResetAll");'
    )
    need(cc, required_register, "centralrepo.cpp")
    need(cc, "case cen_rep_reset_all:", "centralrepo.cpp")
    need(cc, "reset_all(ctx);", "centralrepo.cpp")
    need(rh, "void reset_all(service::ipc_context *ctx);", "repo.h")

    start = rp.find("// NATIVEBOOT2-B20 CENRESETALL1:")
    if start < 0:
        fail("missing B20 implementation block")
    end = rp.find("void central_repo_client_subsession::create_value", start)
    if end < 0:
        fail("cannot isolate B20 reset_all implementation")
    block = rp[start:end]

    for needle in (
        "void central_repo_client_subsession::reset_all(service::ipc_context *ctx)",
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
        "[NBOOT2][CEN_RESET_ALL_FAIL]",
        "if (is_active())",
        "ctx->complete(epoc::error_not_supported);",
        "server->get_initial_repo(io, mngr, attach_repo->uid)",
        "attach_repo->entries = init_repo->entries;",
        "attach_repo->deleted_settings = init_repo->deleted_settings;",
        "write_changes(io, mngr);",
        "ctx->complete(epoc::error_none);",
        "runtime_only_removed",
    ):
        need(block, needle, "B20 reset_all block")

    for forbidden in (
        "*attach_repo = *init_repo",
        "attach_repo = init_repo",
        "ctx->complete(epoc::error_none);\n            return;\n        }\n\n        eka2l1::central_repo *init_repo",
    ):
        if forbidden in block:
            fail(f"unsafe/synthetic ResetAll pattern present: {forbidden}")

    # B19 must remain a diagnostic-only language probe.
    for needle in (
        "[NBOOT2][SA_LANG_ABI]",
        'REGISTER_IPC(sa_server, unk_op1, 0x01100068, "NBOOT2::SaLangAbiProbe");',
        "completion=KErrNotSupported",
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
    ):
        need(sa, needle, "sa.cpp")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__ == "__main__":
    main()
