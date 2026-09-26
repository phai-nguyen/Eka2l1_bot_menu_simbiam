#!/usr/bin/env python3
"""Contract for B83's B28-compatible Central Repository IPC trace."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B83-PHONEUICENREPDIAG1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def require(source, token, where):
    if token not in source:
        fail(f"missing {token} in {where}")


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_b83_phoneuicenrepdiag1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    cenrep_path = upstream / "src/emu/services/src/centralrepo/centralrepo.cpp"
    repo_path = upstream / "src/emu/services/src/centralrepo/repo.cpp"
    header_path = upstream / "src/emu/services/include/services/centralrepo/repo.h"
    for path in (cenrep_path, repo_path, header_path):
        if not path.is_file():
            fail(f"missing B28 CenRep source: {path}")

    cenrep = cenrep_path.read_text(encoding="utf-8")
    repo = repo_path.read_text(encoding="utf-8")
    header = header_path.read_text(encoding="utf-8")
    require(cenrep, "[NBOOT2][CENREP_IPC_ENTRY]", "centralrepo.cpp")
    require(cenrep, "ctx->msg->args.args[0]", "centralrepo.cpp")
    require(repo, "complete_central_repo_ipc(ctx, ", "repo.cpp")
    require(cenrep, "complete_central_repo_ipc(ctx, ", "centralrepo.cpp")
    require(header, "void complete_central_repo_ipc(service::ipc_context *ctx, int res);", "repo.h")
    require(cenrep, "[NBOOT2][CENREP_IPC_COMPLETE]", "centralrepo.cpp")
    require(cenrep, "ctx->complete(res);", "centralrepo.cpp completion wrapper")

    print(MARK + ": PASS")
    print("probe=CentralRepository_IPC_entry_and_completion")
    print("guest_register_or_resource_mutations=NONE")


if __name__ == "__main__":
    main()
