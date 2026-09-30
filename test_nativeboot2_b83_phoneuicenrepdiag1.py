#!/usr/bin/env python3
"""Contract for B83's B28-compatible Central Repository IPC trace."""
from pathlib import Path
import subprocess
import sys
import tempfile

MARK = "NATIVEBOOT2-B83-PHONEUICENREPDIAG1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def require(source, token, where):
    if token not in source:
        fail(f"missing {token} in {where}")


def verify_b20_resetall_is_not_wrapped():
    """Exercise the historical ResetAll boundary with the real patcher."""
    apply_script = Path(__file__).with_name("apply_nativeboot2_b83_phoneuicenrepdiag1.py")
    with tempfile.TemporaryDirectory(prefix="b83-b20-contract-") as temp:
        upstream = Path(temp)
        cenrep_path = upstream / "src/emu/services/src/centralrepo/centralrepo.cpp"
        repo_path = upstream / "src/emu/services/src/centralrepo/repo.cpp"
        header_path = upstream / "src/emu/services/include/services/centralrepo/repo.h"
        for path in (cenrep_path, repo_path, header_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        cenrep_path.write_text(
            "namespace eka2l1 {\n"
            "    void central_repo_client_subsession::handle_message(service::ipc_context *ctx) {\n"
            "        switch (ctx->msg->function) {\n"
            "        }\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        repo_path.write_text(
            "// NATIVEBOOT2-B20 CENRESETALL1:\n"
            "    void central_repo_client_subsession::reset_all(service::ipc_context *ctx) {\n"
            "        ctx->complete(epoc::error_not_supported);\n"
            "    }\n\n"
            "    void central_repo_client_subsession::create_value(service::ipc_context *ctx) {\n"
            "        ctx->complete(epoc::error_none);\n"
            "    }\n",
            encoding="utf-8",
        )
        header_path.write_text(
            "namespace eka2l1 {\n    class central_repo_client;\n}\n",
            encoding="utf-8",
        )

        subprocess.run([sys.executable, str(apply_script), str(upstream)], check=True)
        patched = repo_path.read_text(encoding="utf-8")
        start = patched.index("// NATIVEBOOT2-B20 CENRESETALL1:")
        end = patched.index("void central_repo_client_subsession::create_value", start)
        reset_all = patched[start:end]
        require(reset_all, "ctx->complete(epoc::error_not_supported);", "B20 ResetAll fixture")
        if "complete_central_repo_ipc(ctx," in reset_all:
            fail("B83 must not rewrite the historical B20 ResetAll completion")
        require(patched, "complete_central_repo_ipc(ctx, epoc::error_none);", "post-B20 repo operation")


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
    require(header, "void complete_central_repo_ipc(service::ipc_context *ctx, int res);", "repo.h")
    require(cenrep, "[NBOOT2][CENREP_IPC_COMPLETE]", "centralrepo.cpp")
    require(cenrep, "ctx->complete(res);", "centralrepo.cpp completion wrapper")
    require(cenrep, "ctx->complete(epoc::error_not_found);", "unchanged CenRep session path")

    verify_b20_resetall_is_not_wrapped()

    print(MARK + ": PASS")
    print("probe=CentralRepository_IPC_entry_and_completion")
    print("guest_register_or_resource_mutations=NONE")


if __name__ == "__main__":
    main()
