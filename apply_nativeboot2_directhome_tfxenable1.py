#!/usr/bin/env python3
"""Enable native AknSkinSrv transition effects only for DirectHome reads."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXENABLE1"
OVERRIDE_MARKER = "[NBOOT2][DIRECTHOME_TFX_ENABLE_OVERRIDE]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def rep_between(text, begin, end, old, new, label):
    start = text.find(begin)
    finish = text.find(end, start + 1)
    if start < 0 or finish < 0:
        fail(f"{label}: function bounds not found")
    region = text[start:finish]
    count = region.count(old)
    if count != 1:
        fail(f"{label}: expected one bounded anchor, found {count}")
    return text[:start] + region.replace(old, new, 1) + text[finish:]


def apply_to_repo(source):
    if OVERRIDE_MARKER in source:
        if source.count(OVERRIDE_MARKER) != 1:
            fail("duplicate override marker")
        if "ctx->write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int);" not in source:
            fail("partial override already present; refusing an incomplete patch")
        return source, False

    if "[NBOOT2][AKNSKIN_TFX_STATE]" not in source:
        fail("missing B47 AknSkinSrv CenRep baseline")

    get_begin = "    void central_repo_client_subsession::get_value(service::ipc_context *ctx) {"
    get_end = "    void central_repo_client_subsession::set_value(service::ipc_context *ctx) {"
    anchor = "            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, result_int);\n"
    replacement = '''            const bool b47_directhome_tfx_override =
                b47_tfx_state
                && ctx->sys->get_config()->compat_target_kind == 2
                && result_int == static_cast<std::uint32_t>(0x7FFFFFFF);
            const std::uint32_t guest_result_int = b47_directhome_tfx_override ? 0U : result_int;
            if (b47_directhome_tfx_override) {
                LOG_WARN(SERVICE_CENREP,
                    "[NBOOT2][DIRECTHOME_TFX_ENABLE_OVERRIDE] scope=direct_home process={} repo=0x102818E8 key=0x00000009 stock_value=0x{:08X} guest_value=0x{:08X} enabled=1 behavior=GUEST_RESPONSE_ONLY",
                    b47_process_name, result_int, guest_result_int);
            }
            ctx->write_data_to_descriptor_argument<std::uint32_t>(1, guest_result_int);
'''
    return rep_between(source, get_begin, get_end, anchor, replacement,
        "DirectHome AknSkinSrv CenRep response"), True


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxenable1.py <upstream-root>")

    repo_cpp = Path(sys.argv[1]).resolve() / "src/emu/services/src/centralrepo/repo.cpp"
    if not repo_cpp.is_file():
        fail(f"missing source: {repo_cpp}")

    source = repo_cpp.read_text(encoding="utf-8")
    patched, changed = apply_to_repo(source)
    if changed:
        repo_cpp.write_text(patched, encoding="utf-8")

    print(MARK + (": applied" if changed else ": already applied"))
    print("scope=native_phone_boot+compat_target_kind_2+AknSkinSrv+repo0x102818E8+key0x9+stock0x7FFFFFFF")
    print("guest_response=0; cenrep_write=NONE; firmware_write=NONE; native_boot_default=PRESERVED")


if __name__ == "__main__":
    main()
