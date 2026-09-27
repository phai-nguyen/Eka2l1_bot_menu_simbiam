#!/usr/bin/env python3
"""Add a read-only, CompatBoot-scoped FileServer Entry result trace."""
from __future__ import annotations

import sys
from pathlib import Path


MARK = "NATIVEBOOT2-B98-MENU3ENTRYSTATUS1"
TRACE = "[COMPATBOOT][MENU3_ENTRY]"


def fail(message: str) -> None:
    raise SystemExit(f"{MARK}: {message}")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_entry_status(source: str) -> str:
    begin = "    void fs_server_client::entry(service::ipc_context *ctx) {"
    end = "\n    void fs_server_client::set_entry(service::ipc_context *ctx) {"
    start = source.find(begin)
    finish = source.find(end, start + 1)
    if start < 0 or finish < 0:
        fail("FileServer Entry method bounds are missing")

    body = source[start:finish]
    if TRACE in body:
        return source

    anchor = "        std::optional<entry_info> entry_hle = io->get_entry_info(fname);\n"
    diagnostic = '''        std::optional<entry_info> entry_hle = io->get_entry_info(fname);
        auto *compat_menu_entry_cfg = ctx->sys->get_config();
        kernel::thread *compat_menu_entry_thr = ctx->msg ? ctx->msg->own_thr : nullptr;
        kernel::process *compat_menu_entry_pr = compat_menu_entry_thr
            ? compat_menu_entry_thr->owning_process() : nullptr;
        const std::uint32_t compat_menu_entry_uid3 = compat_menu_entry_pr
            ? static_cast<std::uint32_t>(std::get<2>(compat_menu_entry_pr->get_uid_type())) : 0U;
        const bool compat_menu_entry = compat_menu_entry_cfg
            && compat_menu_entry_cfg->compat_menu_probe_mode
            && compat_menu_entry_cfg->compat_target_uid3 != 0
            && compat_menu_entry_pr
            && compat_menu_entry_uid3 == compat_menu_entry_cfg->compat_target_uid3;
        if (compat_menu_entry) {
            const std::int32_t compat_menu_entry_status = entry_hle
                ? epoc::error_none : epoc::error_not_found;
            LOG_WARN(SERVICE_EFSRV,
                "[COMPATBOOT][MENU3_ENTRY] process={} uid3=0x{:08X} path={} status={} entry_found={} behavior=OBSERVE_ONLY",
                compat_menu_entry_pr->name(), compat_menu_entry_uid3,
                common::ucs2_to_utf8(fname), compat_menu_entry_status,
                entry_hle ? 1 : 0);
        }
'''
    body = replace_once(body, anchor, diagnostic, "Menu3 FileServer Entry result")
    return source[:start] + body + source[finish:]


def patch_file(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    patched = patch_entry_status(source)
    if "#include <config/config.h>" not in patched:
        patched = replace_once(
            patched,
            "#include <kernel/kernel.h>\n",
            "#include <kernel/kernel.h>\n#include <config/config.h>\n",
            "complete config state definition for CompatBoot trace",
        )
    path.write_text(patched, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b98_menu3entrystatus1.py <upstream-root>")

    fs_cpp = Path(sys.argv[1]).resolve() / "src/emu/services/src/fs/fs.cpp"
    if not fs_cpp.is_file():
        fail(f"missing FileServer source: {fs_cpp}")
    patch_file(fs_cpp)
    print(f"{MARK}: applied")
    print("probe=CompatBoot_target_FileServer_Entry_path_and_status")
    print("guest_filesystem_and_IPC_completion_mutations=NONE")


if __name__ == "__main__":
    main()
