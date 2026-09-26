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
    context_path = upstream / "src/emu/services/src/context.cpp"
    if not cenrep_path.is_file():
        fail(f"missing B28 CenRep service source: {cenrep_path}")
    if not context_path.is_file():
        fail(f"missing B28 IPC completion source: {context_path}")

    cenrep = cenrep_path.read_text(encoding="utf-8")
    context = context_path.read_text(encoding="utf-8")
    require(cenrep, "[NBOOT2][CENREP_IPC_ENTRY]", "centralrepo.cpp")
    require(cenrep, "ctx->msg->function", "centralrepo.cpp")
    require(cenrep, "ctx->msg->args.args[0]", "centralrepo.cpp")
    require(context, "[NBOOT2][CENREP_IPC_COMPLETE]", "context.cpp")
    require(context, "CENTRAL_REPO_SERVER_NAME", "context.cpp")
    require(context, "status={}", "context.cpp")

    print(MARK + ": PASS")
    print("probe=CentralRepository_IPC_entry_and_completion")
    print("guest_register_or_resource_mutations=NONE")


if __name__ == "__main__":
    main()
