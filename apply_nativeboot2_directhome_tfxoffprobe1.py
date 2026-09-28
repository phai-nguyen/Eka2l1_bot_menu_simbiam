#!/usr/bin/env python3
"""Keep the stock firmware TFX CenRep response for DirectHome only."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXOFFPROBE1"
RUNTIME_MARKER = "[NBOOT2][DIRECTHOME_TFX_OFF_PROBE]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def rep(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one bounded anchor, found {count}")
    return text.replace(old, new, 1)


def apply_to_source(source):
    if RUNTIME_MARKER in source:
        if source.count(RUNTIME_MARKER) != 1:
            fail("duplicate TFX-off probe marker")
        if "const std::uint32_t guest_result_int = result_int;" not in source:
            fail("partial probe already present; refusing an incomplete patch")
        return source, False

    if "[NBOOT2][DIRECTHOME_TFX_ENABLE_OVERRIDE]" not in source:
        fail("missing DirectHome TFX-enable baseline")

    old_override = '''            const bool b47_directhome_tfx_override =
                b47_tfx_state && b47_directhome_tfx_scope
                && result_int == static_cast<std::uint32_t>(0x7FFFFFFF);'''
    new_override = "            const bool b47_directhome_tfx_override = false;"
    source = rep(source, old_override, new_override, "disable DirectHome guest-only TFX override")

    old_response = "            const std::uint32_t guest_result_int = b47_directhome_tfx_override ? 0U : result_int;\n"
    new_response = '''            const std::uint32_t guest_result_int = result_int;
            if (b47_tfx_state && b47_directhome_tfx_scope) {
                LOG_WARN(SERVICE_CENREP,
                    "[NBOOT2][DIRECTHOME_TFX_OFF_PROBE] scope=direct_home repo=0x102818E8 key=0x00000009 stock_value=0x{:08X} guest_value=0x{:08X} override=0 behavior=STOCK_FIRMWARE_RESPONSE_ONLY",
                    result_int, guest_result_int);
            }
'''
    source = rep(source, old_response, new_response, "preserve stock firmware TFX response")
    return source, True


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxoffprobe1.py <upstream-root>")

    repo_cpp = Path(sys.argv[1]).resolve() / "src/emu/services/src/centralrepo/repo.cpp"
    if not repo_cpp.is_file():
        fail(f"missing source: {repo_cpp}")

    source = repo_cpp.read_text(encoding="utf-8")
    patched, changed = apply_to_source(source)
    if changed:
        repo_cpp.write_text(patched, encoding="utf-8")

    print(MARK + (": applied" if changed else ": already applied"))
    print("scope=DirectHome-only; guest_response=stock_CenRep_value; fake_TfxServer=NONE; native_boot_default=PRESERVED")


if __name__ == "__main__":
    main()
