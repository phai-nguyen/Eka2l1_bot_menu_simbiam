#!/usr/bin/env python3
"""NATIVEBOOT2 B83 PHONEUICENREPDIAG1.

Add read-only Central Repository IPC entry/completion logging to source files
that are part of the stable B28 service build. No guest state is changed.
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
    context_path = upstream / "src/emu/services/src/context.cpp"
    for path in (cenrep_path, context_path):
        if not path.is_file():
            fail(f"missing B28-compatible source: {path}")

    cenrep = cenrep_path.read_text(encoding="utf-8")
    context = context_path.read_text(encoding="utf-8")
    entry_marker = "[NBOOT2][CENREP_IPC_ENTRY]"
    complete_marker = "[NBOOT2][CENREP_IPC_COMPLETE]"
    already = entry_marker in cenrep and complete_marker in context
    if already:
        print(MARK + ": already applied")
        return
    if entry_marker in cenrep or complete_marker in context:
        fail("partial B83 application detected; refusing to duplicate instrumentation")

    cenrep_anchor = """    void central_repo_client_subsession::handle_message(service::ipc_context *ctx) {
        switch (ctx->msg->function) {"""
    cenrep_instrumentation = """    void central_repo_client_subsession::handle_message(service::ipc_context *ctx) {
        LOG_INFO(SERVICE_CENREP,
            "[NBOOT2][CENREP_IPC_ENTRY] msg={} thread={} opcode={} arg0=0x{:08X} arg1=0x{:08X} arg2=0x{:08X} arg3=0x{:08X} behavior=OBSERVE_ONLY",
            ctx->msg->id, ctx->msg->own_thr->name(), ctx->msg->function,
            ctx->msg->args.args[0], ctx->msg->args.args[1],
            ctx->msg->args.args[2], ctx->msg->args.args[3]);
        switch (ctx->msg->function) {"""
    context_anchor = """        void ipc_context::complete(int res) {
            if (msg->request_sts) {"""
    context_instrumentation = """        void ipc_context::complete(int res) {
            if (msg && msg->msg_session && msg->msg_session->get_server()
                && msg->msg_session->get_server()->name() == CENTRAL_REPO_SERVER_NAME) {
                LOG_INFO(SERVICE_CENREP,
                    "[NBOOT2][CENREP_IPC_COMPLETE] msg={} thread={} opcode={} status={} behavior=OBSERVE_ONLY",
                    msg->id, msg->own_thr->name(), msg->function, res);
            }

            if (msg->request_sts) {"""

    # Validate both anchors before writing either source file.
    if cenrep.count(cenrep_anchor) != 1:
        fail(f"CenRep IPC handler anchor expected once, found {cenrep.count(cenrep_anchor)}")
    if context.count(context_anchor) != 1:
        fail(f"IPC completion anchor expected once, found {context.count(context_anchor)}")
    if "CENTRAL_REPO_SERVER_NAME" not in context:
        context = context.replace(
            "#include <kernel/server.h>\n",
            "#include <kernel/server.h>\n#include <kernel/session.h>\n\n#include <services/centralrepo/centralrepo.h>\n",
            1,
        )

    cenrep = replace_once(cenrep, cenrep_anchor, cenrep_instrumentation, "CenRep IPC entry")
    context = replace_once(context, context_anchor, context_instrumentation, "CenRep IPC completion")
    cenrep_path.write_text(cenrep, encoding="utf-8")
    context_path.write_text(context, encoding="utf-8")

    print(MARK + ": applied")
    print("probe=CentralRepository_IPC_entry_and_completion")
    print("guest_register_or_resource_mutations=NONE")


if __name__ == "__main__":
    main()
