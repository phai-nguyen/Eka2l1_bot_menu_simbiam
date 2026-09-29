#!/usr/bin/env python3
"""NATIVEBOOT2 B92 CENREPFINDEQDIAG1.

Add a read-only FindEqInt trace scoped to the explicit CompatBoot mode.
"""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-B92-CENREPFINDEQDIAG1"
TRACE = "[COMPATBOOT][CENREP_FIND_EQ_INT]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_find_method(source):
    if TRACE in source:
        if source.count(TRACE) != 3:
            fail("partial B92 trace detected; refusing ambiguous method")
        return source

    validation_anchor = """        if (!filter || !found_uid_result_array) {
"""
    validated_anchor = """        // Set found count to 0
"""
    trace_entry = """        const bool b92_compat_find_eq_int = ctx->sys->get_config()->compat_menu_probe_mode
            && (ctx->msg->function == cen_rep_find_eq_int);
        if (b92_compat_find_eq_int) {
            const std::optional<std::int32_t> comparison_value = ctx->get_argument_value<std::int32_t>(1);
            LOG_INFO(SERVICE_CENREP,
                "[COMPATBOOT][CENREP_FIND_EQ_INT] phase=request repo=0x{:08X} repo_valid={} partial_key=0x{:08X} id_mask=0x{:08X} comparison_value={} comparison_valid={} behavior=OBSERVE_ONLY",
                attach_repo ? attach_repo->uid : 0, attach_repo ? 1 : 0,
                filter->partial_key, filter->id_mask,
                comparison_value.value_or(0), comparison_value.has_value() ? 1 : 0);
        }

"""
    if source.count(validation_anchor) != 1:
        fail(f"FindEqInt validation anchor expected once, found {source.count(validation_anchor)}")
    if source.count(validated_anchor) != 1:
        fail(f"FindEqInt post-validation anchor expected once, found {source.count(validated_anchor)}")
    if source.index(validation_anchor) > source.index(validated_anchor):
        fail("FindEqInt validation ordering is unexpected")

    source = replace_once(source, validated_anchor, trace_entry + validated_anchor, "FindEqInt request trace")

    no_result = """            complete_central_repo_ipc(ctx, epoc::error_not_found);
"""
    no_result_trace = """            if (b92_compat_find_eq_int) {
                LOG_INFO(SERVICE_CENREP,
                    "[COMPATBOOT][CENREP_FIND_EQ_INT] phase=result repo=0x{:08X} result_count={} status={} behavior=OBSERVE_ONLY",
                    attach_repo ? attach_repo->uid : 0, found_uid_result_array[0], epoc::error_not_found);
            }
"""
    source = replace_once(source, no_result, no_result_trace + no_result, "FindEqInt not-found result trace")

    success = """        complete_central_repo_ipc(ctx, epoc::error_none);
"""
    success_trace = """        if (b92_compat_find_eq_int) {
            LOG_INFO(SERVICE_CENREP,
                "[COMPATBOOT][CENREP_FIND_EQ_INT] phase=result repo=0x{:08X} result_count={} status={} behavior=OBSERVE_ONLY",
                attach_repo ? attach_repo->uid : 0, found_uid_result_array[0], epoc::error_none);
        }
"""
    source = replace_once(source, success, success_trace + success, "FindEqInt success result trace")
    return source


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b92_cenrepfindeqdiag1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    repo_path = upstream / "src/emu/services/src/centralrepo/repo.cpp"
    if not repo_path.is_file():
        fail(f"missing B28 CenRep source: {repo_path}")

    repo = repo_path.read_text(encoding="utf-8")
    start_anchor = "    void central_repo_client_subsession::find(service::ipc_context *ctx) {"
    end_anchor = "    void central_repo_client_subsession::get_find_result(service::ipc_context *ctx) {"
    if start_anchor not in repo or end_anchor not in repo:
        fail("cannot locate bounded FindEqInt method")
    start = repo.index(start_anchor)
    end = repo.index(end_anchor, start)
    method = repo[start:end]
    patched = patch_find_method(method)
    repo_path.write_text(repo[:start] + patched + repo[end:], encoding="utf-8")

    print(MARK + ": applied")
    print("probe=CompatBoot_CentralRepository_FindEqInt_request_and_result")
    print("guest_register_or_resource_mutations=NONE")
    print("ipc_completion_semantics=UNCHANGED")


if __name__ == "__main__":
    main()
