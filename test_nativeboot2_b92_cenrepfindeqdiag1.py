#!/usr/bin/env python3
"""Contract for the read-only, CompatBoot-only FindEqInt trace."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "b92_patch", ROOT / "apply_nativeboot2_b92_cenrepfindeqdiag1.py"
)
PATCH = importlib.util.module_from_spec(SPEC) if SPEC and SPEC.origin and Path(SPEC.origin).is_file() else None
if SPEC and SPEC.loader and PATCH:
    SPEC.loader.exec_module(PATCH)


FIND_METHOD = """    void central_repo_client_subsession::find(service::ipc_context *ctx) {
        key_found_result.clear();
        std::optional<central_repo_key_filter> filter = ctx->get_argument_data_from_descriptor<central_repo_key_filter>(0);
        std::uint32_t *found_uid_result_array = reinterpret_cast<std::uint32_t *>(ctx->get_descriptor_argument_ptr(2));
        const std::size_t found_uid_max_uids = (ctx->get_argument_max_data_size(2) / sizeof(std::uint32_t)) - 1;

        if (!filter || !found_uid_result_array) {
            ctx->complete(epoc::error_argument);
            return;
        }

        // Set found count to 0
        found_uid_result_array[0] = 0;
        for (auto &entry : attach_repo->entries) {
            if (ctx->msg->function == cen_rep_find_eq_int) {
                if (entry.data.etype != central_repo_entry_type::integer) {
                    break;
                }
                if (static_cast<std::int32_t>(entry.data.intd) == *ctx->get_argument_value<std::int32_t>(1)) {
                    found_uid_result_array[0]++;
                }
            }
        }

        if (found_uid_result_array[0] == 0) {
            complete_central_repo_ipc(ctx, epoc::error_not_found);
            return;
        }

        complete_central_repo_ipc(ctx, epoc::error_none);
    }
"""


class FindEqIntTraceContract(unittest.TestCase):
    def test_patch_scopes_trace_after_descriptor_validation_and_preserves_status(self):
        self.assertIsNotNone(PATCH, "B92 patcher is not present")
        patched = PATCH.patch_find_method(FIND_METHOD)

        marker = "[COMPATBOOT][CENREP_FIND_EQ_INT]"
        self.assertIn(marker, patched)
        self.assertIn("ctx->sys->get_config()->compat_menu_probe_mode", patched)
        self.assertIn("ctx->msg->function == cen_rep_find_eq_int", patched)
        self.assertIn("attach_repo ? attach_repo->uid : 0", patched)
        self.assertIn("filter->partial_key", patched)
        self.assertIn("filter->id_mask", patched)
        self.assertIn("comparison_value", patched)
        self.assertIn("found_uid_result_array[0]", patched)

        validation = patched.index("if (!filter || !found_uid_result_array)")
        invalid_return = patched.index("return;", validation)
        trace = patched.index(marker)
        self.assertGreater(trace, invalid_return)
        self.assertEqual(patched.count("complete_central_repo_ipc(ctx, epoc::error_not_found);"), 1)
        self.assertEqual(patched.count("complete_central_repo_ipc(ctx, epoc::error_none);"), 1)
        self.assertIn("status={} behavior=OBSERVE_ONLY", patched)

    def test_patch_is_idempotent_and_rejects_partial_marker(self):
        self.assertIsNotNone(PATCH, "B92 patcher is not present")
        once = PATCH.patch_find_method(FIND_METHOD)
        self.assertEqual(PATCH.patch_find_method(once), once)
        with self.assertRaisesRegex(SystemExit, "partial B92 trace"):
            PATCH.patch_find_method(FIND_METHOD.replace("found_uid_result_array[0] = 0;", "[COMPATBOOT][CENREP_FIND_EQ_INT]"))


if __name__ == "__main__":
    unittest.main()
