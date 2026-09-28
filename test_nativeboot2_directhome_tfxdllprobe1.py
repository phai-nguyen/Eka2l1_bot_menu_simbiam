#!/usr/bin/env python3
"""Contract for the DirectHome TfxSrvPlugin attach/ordinal observer."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def need(text, needle, label):
    if needle not in text:
        fail(f"missing {label}: {needle}")


def block(source, start, end, label):
    begin = source.find(start)
    finish = source.find(end, begin + 1)
    if begin < 0 or finish < 0:
        fail(f"cannot isolate {label}")
    return source[begin:finish]


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_directhome_tfxxdllprobe1.py <upstream-root>")
    svc_path = Path(sys.argv[1]).resolve() / "src/emu/kernel/src/svc.cpp"
    if not svc_path.is_file():
        fail(f"missing source: {svc_path}")
    source = svc_path.read_text(encoding="utf-8")

    for marker in (
        "NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1_HELPER",
        "[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH]",
        "[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH_ENTRY]",
        "[NBOOT2][DIRECTHOME_TFX_DLL_LOOKUP]",
    ):
        need(source, marker, "DirectHome TfxSrvPlugin observer")

    helper = block(
        source,
        "NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1_HELPER",
        "BRIDGE_FUNC(std::int32_t, library_attach,",
        "plugin filter",
    )
    for condition in (
        "native_phone_boot",
        "compat_menu_probe_mode",
        "compat_target_kind != 2",
        "process_uid3 == 0x10207114U",
        "library_uid3 == 0x10282DBAU",
        'library_path.find("TfxSrvPlugin.dll")',
    ):
        need(helper, condition, "DirectHome/plugin filter")

    attach = block(
        source,
        "BRIDGE_FUNC(std::int32_t, library_attach,",
        "BRIDGE_FUNC(std::int32_t, library_attached,",
        "library_attach",
    )
    attach_call = attach.find("lib->attach(kern->crr_process())")
    attach_log = attach.find("[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH]")
    copy = attach.find("std::memcpy(episode_choose_your_story, entries.data()")
    if min(attach_call, attach_log, copy) < 0 or not (attach_call < attach_log < copy):
        fail("attach observer must follow the original attach and precede the unchanged result copy")
    need(attach, "entries_available={}", "bounded attach result")
    need(attach, "index < 16U", "bounded entrypoint list")
    if attach.count("lib->attach(kern->crr_process())") != 1:
        fail("observer must not repeat library attach")

    lookup = block(
        source,
        "BRIDGE_FUNC(std::int32_t, library_lookup,",
        "BRIDGE_FUNC(std::int32_t, library_attached,",
        "library_lookup",
    )
    lookup_call = lookup.find("lib->get_ordinal_address(kern->crr_process(),")
    lookup_log = lookup.find("[NBOOT2][DIRECTHOME_TFX_DLL_LOOKUP]")
    original_return = lookup.find("return *func_addr;")
    if min(lookup_call, lookup_log, original_return) < 0 or not (lookup_call < lookup_log < original_return):
        fail("lookup observer must preserve the original ordinal result")
    if lookup.count("lib->get_ordinal_address(kern->crr_process(),") != 1:
        fail("observer must not repeat ordinal lookup")
    need(lookup, "func_addr.has_value() ? 1 : 0", "lookup result")
    need(lookup, "func_addr.value_or(0)", "lookup address")
    need(source, "behavior=OBSERVE_ONLY", "read-only classification")
    if "create_and_add<service::server>" in helper + attach + lookup:
        fail("observer must not create or register TfxServer")

    print(f"{MARK}: PASS")
    print("scope=DirectHome+AknSkinSrv+TfxSrvPlugin.dll")
    print("attach_result=UNCHANGED; ordinal_result=UNCHANGED; server_creation=NONE")


if __name__ == "__main__":
    main()
