#!/usr/bin/env python3
"""Trace TfxSrvPlugin attach and export lookup in DirectHome without changing results."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1"
ATTACH_MARKER = "[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH] process="
LOOKUP_MARKER = "[NBOOT2][DIRECTHOME_TFX_DLL_LOOKUP]"
HELPER_MARKER = "NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1_HELPER"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def function_region(source, begin, end, label):
    start = source.find(begin)
    finish = source.find(end, start + 1)
    if start < 0 or finish < 0:
        fail(f"{label}: function boundary missing")
    region = source[start:finish]
    next_begin = source.find(begin, start + 1)
    if next_begin >= 0 and next_begin < finish:
        fail(f"{label}: duplicate function anchor")
    return start, finish, region


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def apply_to_svc(source):
    present = (ATTACH_MARKER in source, LOOKUP_MARKER in source, HELPER_MARKER in source)
    if any(present):
        if not all(present):
            fail("partial probe marker; refusing an incomplete patch")
        if any(source.count(marker) != 1 for marker in (ATTACH_MARKER, LOOKUP_MARKER, HELPER_MARKER)):
            fail("duplicate probe marker")

    attach_begin = "    BRIDGE_FUNC(std::int32_t, library_attach,"
    attach_end = "    BRIDGE_FUNC(std::int32_t, library_lookup,"
    lookup_begin = "    BRIDGE_FUNC(std::int32_t, library_lookup,"
    lookup_end = "    BRIDGE_FUNC(std::int32_t, library_attached,"
    attach_start, attach_finish, attach = function_region(source, attach_begin, attach_end, "library_attach")
    lookup_start, lookup_finish, lookup = function_region(source, lookup_begin, lookup_end, "library_lookup")
    if not (attach_finish <= lookup_start or lookup_finish <= attach_start):
        fail("library_attach/library_lookup function bounds overlap")

    if all(present):
        if "lib->attach(kern->crr_process())" not in attach or "entries_available={}" not in attach:
            fail("partial library_attach observer")
        if "lib->get_ordinal_address(kern->crr_process()," not in lookup or "return *func_addr;" not in lookup:
            fail("partial library_lookup observer")
        return source

    helper = '''    // NATIVEBOOT2-DIRECTHOME-TFXDLLPROBE1_HELPER
    static bool directhome_tfx_plugin_library(kernel_system *kern, kernel::library *lib) {
        if (!kern || !lib || !kern->get_config()) {
            return false;
        }

        const auto *config = kern->get_config();
        if (!config->native_phone_boot || !config->compat_menu_probe_mode || config->compat_target_kind != 2) {
            return false;
        }

        kernel::process *process = kern->crr_process();
        kernel::codeseg *codeseg = lib->get_codeseg();
        if (!process || !codeseg) {
            return false;
        }

        const auto process_uids = process->get_uid_type();
        const auto library_uids = codeseg->get_uids();
        const std::uint32_t process_uid3 = static_cast<std::uint32_t>(std::get<2>(process_uids));
        const std::uint32_t library_uid3 = static_cast<std::uint32_t>(std::get<2>(library_uids));
        const std::string library_path = common::ucs2_to_utf8(codeseg->get_full_path());
        return process_uid3 == 0x10207114U && library_uid3 == 0x10282DBAU
            && library_path.find("TfxSrvPlugin.dll") != std::string::npos;
    }

'''
    source = replace_once(source, attach_begin, helper + attach_begin, "probe helper insertion")

    attach_anchor = "        std::vector<uint32_t> entries = lib->attach(kern->crr_process());\n"
    attach_trace = '''        std::vector<uint32_t> entries = lib->attach(kern->crr_process());
        if (directhome_tfx_plugin_library(kern, lib)) {
            kernel::process *probe_process = kern->crr_process();
            kernel::codeseg *probe_codeseg = lib->get_codeseg();
            LOG_WARN(KERNEL,
                "[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH] process={} uid3=0x{:08X} library={} library_uid3=0x10282DBA handle=0x{:08X} entries_available={} behavior=OBSERVE_ONLY",
                probe_process->name(), static_cast<std::uint32_t>(std::get<2>(probe_process->get_uid_type())),
                common::ucs2_to_utf8(probe_codeseg->get_full_path()), static_cast<std::uint32_t>(h),
                static_cast<std::uint32_t>(entries.size()));
            for (std::uint32_t index = 0; index < entries.size() && index < 16U; ++index) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][DIRECTHOME_TFX_DLL_ATTACH_ENTRY] index={} address=0x{:08X} behavior=OBSERVE_ONLY",
                    index, entries[index]);
            }
        }
'''
    attach = replace_once(attach, attach_anchor, attach_trace, "library_attach observation")
    attach_start, attach_finish, _ = function_region(source, attach_begin, attach_end, "library_attach")
    source = source[:attach_start] + attach + source[attach_finish:]

    lookup_start, lookup_finish, lookup = function_region(source, lookup_begin, lookup_end, "library_lookup")
    lookup_anchor = "        std::optional<uint32_t> func_addr = lib->get_ordinal_address(kern->crr_process(),\n            ord_index);\n"
    lookup_trace = '''        std::optional<uint32_t> func_addr = lib->get_ordinal_address(kern->crr_process(),
            ord_index);
        if (directhome_tfx_plugin_library(kern, lib)) {
            kernel::process *probe_process = kern->crr_process();
            kernel::codeseg *probe_codeseg = lib->get_codeseg();
            LOG_WARN(KERNEL,
                "[NBOOT2][DIRECTHOME_TFX_DLL_LOOKUP] process={} uid3=0x{:08X} library={} library_uid3=0x10282DBA handle=0x{:08X} ordinal={} success={} address=0x{:08X} behavior=OBSERVE_ONLY",
                probe_process->name(), static_cast<std::uint32_t>(std::get<2>(probe_process->get_uid_type())),
                common::ucs2_to_utf8(probe_codeseg->get_full_path()), static_cast<std::uint32_t>(h), ord_index,
                func_addr.has_value() ? 1 : 0, func_addr.value_or(0));
        }
'''
    lookup = replace_once(lookup, lookup_anchor, lookup_trace, "library_lookup observation")
    source = source[:lookup_start] + lookup + source[lookup_finish:]
    return source


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxdllprobe1.py <upstream-root>")
    svc_path = Path(sys.argv[1]).resolve() / "src/emu/kernel/src/svc.cpp"
    if not svc_path.is_file():
        fail(f"missing source: {svc_path}")
    source = svc_path.read_text(encoding="utf-8")
    patched = apply_to_svc(source)
    if patched != source:
        svc_path.write_text(patched, encoding="utf-8")
        print(MARK + ": applied")
    else:
        print(MARK + ": already applied")
    print("scope=DirectHome+AknSkinSrv+TfxSrvPlugin.dll(uid3=0x10282DBA)")
    print("attach_and_lookup_results=UNCHANGED; behavior=OBSERVE_ONLY")


if __name__ == "__main__":
    main()
