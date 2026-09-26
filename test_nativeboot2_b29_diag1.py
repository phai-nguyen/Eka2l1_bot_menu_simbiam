#!/usr/bin/env python3
"""Source-level contract for B29-DIAG1 CenRep transaction diagnostics.

DIAG1 must add observability only. It must not hardcode the FEP repository
or change the B29 transaction/Set state machine.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B29-DIAG1-TEST"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b29_diag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    repo_cpp=up/"src/emu/services/src/centralrepo/repo.cpp"
    if not repo_cpp.is_file():
        fail(f"missing source file: {repo_cpp}")

    rp=repo_cpp.read_text(encoding="utf-8")

    # B29 functional baseline must still be present.
    for needle in (
        "[NBOOT2][CEN_TX_START]",
        "[NBOOT2][CEN_SET_CREATE]",
        "[NBOOT2][CEN_TX_COMMIT]",
        "[NBOOT2][CEN_TX_CANCEL]",
        "set_active(true);",
        "write_changes(io, mngr);",
    ):
        need(rp, needle, "repo.cpp B29 preservation")

    # DIAG1 boundaries.
    for needle in (
        "[NBOOT2][CEN_SET_BEGIN]",
        "[NBOOT2][CEN_SET_RESULT]",
        "[NBOOT2][CEN_SET_FAIL]",
        "[NBOOT2][CEN_TX_COMMIT_BEGIN]",
        "[NBOOT2][CEN_TX_COMMIT_KEY]",
        "[NBOOT2][CEN_TX_COMMIT_RESULT]",
        "[NBOOT2][CEN_TX_COMMIT_FAIL]",
    ):
        need(rp, needle, "repo.cpp DIAG1 markers")

    # Required diagnostic fields. Keep this generic: log runtime UID/key/type,
    # never special-case the FEP repository or its keys.
    for needle in (
        "existing_type=",
        "requested_type=",
        "reason=",
        "staged=",
        "key_info=",
        "completion=",
        "metadata=0x",
    ):
        need(rp, needle, "repo.cpp DIAG1 fields")

    if "0x10272618" in rp:
        fail("FEP repository UID hardcoded into generic CenRep implementation")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")

if __name__=="__main__":
    main()
