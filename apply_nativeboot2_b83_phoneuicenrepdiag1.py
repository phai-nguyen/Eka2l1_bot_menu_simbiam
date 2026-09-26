#!/usr/bin/env python3
"""NATIVEBOOT2 B83 PHONEUICENREPDIAG1.

Trace Central Repository request entry and completion at the HLE service
boundary present in the stable B28-derived source tree. The probe is read-only.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B83-PHONEUICENREPDIAG1"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b83_phoneuicenrepdiag1.py <upstream-root>")

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
    entry_marker = "[NBOOT2][CENREP_IPC_ENTRY]"
    complete_marker = "[NBOOT2][CENREP_IPC_COMPLETE]"
    if entry_marker in cenrep and complete_marker in cenrep and "complete_central_repo_ipc" in header:
        print(MARK + ": already applied")
        return
    if entry_marker in cenrep or complete_marker in cenrep or "complete_central_repo_ipc" in header:
        fail("partial B83 application detected; refusing to duplicate instrumentation")

    entry_anchor = """    void central_repo_client_subsession::handle_message(service::ipc_context *ctx) {
        switch (ctx->msg->function) {"""
    entry_code = """    void central_repo_client_subsession::handle_message(service::ipc_context *ctx) {
        LOG_INFO(SERVICE_CENREP,
            "[NBOOT2][CENREP_IPC_ENTRY] msg={} thread={} opcode={} arg0=0x{:08X} arg1=0x{:08X} arg2=0x{:08X} arg3=0x{:08X} behavior=OBSERVE_ONLY",
            ctx->msg->id, ctx->msg->own_thr->name(), ctx->msg->function,
            ctx->msg->args.args[0], ctx->msg->args.args[1],
            ctx->msg->args.args[2], ctx->msg->args.args[3]);
        switch (ctx->msg->function) {"""
    complete_declaration = "    void complete_central_repo_ipc(service::ipc_context *ctx, int res);"
    header_anchor = "    class central_repo_client;\n"
    completion_definition = """    void complete_central_repo_ipc(service::ipc_context *ctx, int res) {
        LOG_INFO(SERVICE_CENREP,
            "[NBOOT2][CENREP_IPC_COMPLETE] msg={} thread={} opcode={} status={} behavior=OBSERVE_ONLY",
            ctx->msg->id, ctx->msg->own_thr->name(), ctx->msg->function, res);
        ctx->complete(res);
    }

"""
    namespace_anchor = "namespace eka2l1 {\n"

    if cenrep.count(entry_anchor) != 1:
        fail(f"CenRep IPC handler anchor expected once, found {cenrep.count(entry_anchor)}")
    if header.count(header_anchor) != 1:
        fail(f"CenRep declaration anchor expected once, found {header.count(header_anchor)}")
    if cenrep.count(namespace_anchor) != 1:
        fail(f"CenRep namespace anchor expected once, found {cenrep.count(namespace_anchor)}")
    if cenrep.count("ctx->complete(") + repo.count("ctx->complete(") == 0:
        fail("no CenRep completion call sites found")

    # Redirect only existing CenRep service completions through the observer;
    # the helper itself delegates to the original ipc_context::complete.
    cenrep = cenrep.replace("ctx->complete(", "complete_central_repo_ipc(ctx, ")
    repo = repo.replace("ctx->complete(", "complete_central_repo_ipc(ctx, ")
    cenrep = replace_once(cenrep, entry_anchor, entry_code, "CenRep IPC entry")
    header = replace_once(header, header_anchor, header_anchor + complete_declaration + "\n", "CenRep completion declaration")
    cenrep = replace_once(cenrep, namespace_anchor, namespace_anchor + completion_definition, "CenRep completion wrapper")

    cenrep_path.write_text(cenrep, encoding="utf-8")
    repo_path.write_text(repo, encoding="utf-8")
    header_path.write_text(header, encoding="utf-8")

    print(MARK + ": applied")
    print("probe=CentralRepository_IPC_entry_and_completion")
    print("guest_register_or_resource_mutations=NONE")


if __name__ == "__main__":
    main()
