#!/usr/bin/env python3
"""Contract for the DirectHome-only AknSkinSrv transition-effects response."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXENABLE1-TEST"
OVERRIDE_MARKER = "[NBOOT2][DIRECTHOME_TFX_ENABLE_OVERRIDE]"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_directhome_tfxenable1.py <upstream-root>")

    repo = Path(sys.argv[1]).resolve() / "src/emu/services/src/centralrepo/repo.cpp"
    if not repo.is_file():
        fail(f"missing source: {repo}")
    source = repo.read_text(encoding="utf-8")

    start = source.find("    void central_repo_client_subsession::get_value(service::ipc_context *ctx) {")
    end = source.find("    void central_repo_client_subsession::append_new_key_to_found_eq_list", start + 1)
    if start < 0 or end < 0:
        fail("cannot isolate central repository GetInt handler")
    handler = source[start:end]

    need(handler, "[NBOOT2][AKNSKIN_TFX_STATE]", "B47 observation preservation")
    if handler.count(OVERRIDE_MARKER) != 1:
        fail("expected exactly one DirectHome override log")

    for needle in (
        "ctx->sys->get_config()->native_phone_boot",
        "b47_aknskin_process",
        "ctx->msg->function == cen_rep_get_int",
        "attach_repo->uid == static_cast<std::uint32_t>(0x102818E8)",
        "the_key.value() == static_cast<std::uint32_t>(0x00000009)",
        "b47_tfx_state",
        "ctx->sys->get_config()->compat_target_kind == 2",
        "result_int == static_cast<std::uint32_t>(0x7FFFFFFF)",
        "const std::uint32_t guest_result_int = b47_directhome_tfx_override ? 0U : result_int;",
        "write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int)",
        "scope=direct_home",
        "repo=0x102818E8",
        "key=0x00000009",
        "stock_value=0x{:08X}",
        "guest_value=0x{:08X}",
        "behavior=GUEST_RESPONSE_ONLY",
    ):
        need(handler, needle, "DirectHome override scope/response")

    if "entry->data.intd =" in handler:
        fail("the override writes the persistent CenRep entry")
    if "write_data_to_descriptor_argument<std::uint32_t>(1, result_int)" in handler:
        fail("GetInt bypasses the guarded guest response value")
    if handler.count("write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int)") != 1:
        fail("expected exactly one GetInt descriptor response through the scoped value")
    if "ctx->complete(epoc::error_argument);" not in handler:
        fail("the original type error path was removed")

    if (Path(sys.argv[1]).resolve() / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(f"{MARK}: PASS")
    print("profile=direct_home; stored_value=0x7FFFFFFF; guest_response=0")
    print("cenrep_write=NONE; firmware_write=NONE; native_boot_default=PRESERVED")


if __name__ == "__main__":
    main()
