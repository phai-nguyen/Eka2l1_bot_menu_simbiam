#!/usr/bin/env python3
"""Apply B29-LOADERDIAG1 after B29 CENREPTX1 + DIAG1.

Diagnostic-only instrumentation for the loader path exposed by the B29 device
trace. This patch is deliberately matched to the exact B28 FASTBUILD bootstrap
source, whose lib_manager::load() treats rooted-no-drive paths as direct VFS
paths instead of trying drives A:..Z:.

No loader search, parser, codeseg, dependency, or completion semantics are
changed. No target DLL/UID is hardcoded.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B29-LOADERDIAG1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b29_loaderdiag1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    ldr=up/"src/emu/services/src/loader/loader.cpp"
    cen=up/"src/emu/services/src/centralrepo/repo.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for p in (lib,ldr,cen,svc):
        if not p.is_file():
            fail(f"missing source file: {p}")

    cr=cen.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    for needle in ("[NBOOT2][CEN_TX_START]","[NBOOT2][CEN_TX_COMMIT]"):
        if needle not in cr:
            fail(f"B29 marker missing: {needle}")
    if "[NBOOT2][WSERV_LIBRARY_TYPE]" not in sv:
        fail("B28 marker missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    lm=lib.read_text(encoding="utf-8")
    ls=ldr.read_text(encoding="utf-8")

    if "[NBOOT2][LDR_ROOT_BEGIN]" in lm or "[NBOOT2][LDR_LIB_REQUEST]" in ls:
        print(f"{MARK}: already applied")
        return

    # Dependency failures: emit only when the pre-existing resolver gives up.
    old='''        if (!cs) {
            // Skip these ordinals
            LOG_TRACE(KERNEL, "Can't find {}", dll_name8);
            crr_idx += static_cast<std::uint32_t>(import_block.ordinals.size());

            return false;
        }
'''
    new='''        if (!cs) {
            // Skip these ordinals
            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_DEP_FAIL] parent={} dependency={} format=PE reason=not_found",
                common::ucs2_to_utf8(parent_codeseg->get_full_path()), dll_name8);
            LOG_TRACE(KERNEL, "Can't find {}", dll_name8);
            crr_idx += static_cast<std::uint32_t>(import_block.ordinals.size());

            return false;
        }
'''
    lm=replace_once(lm,old,new,"PE dependency diagnostics")

    old='''            if (!cs) {
                LOG_TRACE(KERNEL, "Can't find {}", dll_name8);
                return false;
            }
'''
    new='''            if (!cs) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][LDR_DEP_FAIL] parent={} dependency={} format=ELF reason=not_found",
                    common::ucs2_to_utf8(parent_cs->get_full_path()), dll_name8);
                LOG_TRACE(KERNEL, "Can't find {}", dll_name8);
                return false;
            }
'''
    lm=replace_once(lm,old,new,"ELF dependency diagnostics")

    # Structural function-entry insertion, robust to the historical fast-path
    # block present in the B28 cache.
    func_needle="    codeseg_ptr lib_manager::load("
    func_pos=lm.find(func_needle)
    if func_pos < 0:
        fail("lib_manager::load function missing")
    open_brace=lm.find("{",func_pos)
    if open_brace < 0:
        fail("lib_manager::load opening brace missing")
    insert_pos=open_brace+1
    root_diag='''
        const bool nativeboot2_root_diag =
            eka2l1::has_root_dir(name) && eka2l1::root_name(name, true).empty();

        if (nativeboot2_root_diag) {
            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_ROOT_BEGIN] request={} rooted=1 has_drive=0",
                common::ucs2_to_utf8(name));
        }
'''
    lm=lm[:insert_pos]+root_diag+lm[insert_pos:]

    # Instrument the exact B28 cached image-classification branches without
    # adding any parser probe or changing stream position.
    old='''            symfile f = io_->open_file(lib_path, READ_MODE | BIN_MODE | additional_mode_);
            if (!f) {
                LOG_ERROR(KERNEL, "Can't open {}", common::ucs2_to_utf8(lib_path));
                return nullptr;
            }

            eka2l1::ro_file_stream image_data_stream(f.get());

            if (f->is_in_rom()) {
                auto romimg = loader::parse_romimg(reinterpret_cast<common::ro_stream *>(&image_data_stream), mem_, kern_->get_epoc_version(), is_driver_lib);
                if (!romimg) {
                    return nullptr;
                }

                return load_as_romimg(*romimg, lib_path, is_driver_lib);
            } else {
                auto e32img = loader::parse_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream));
                if (!e32img) {
                    return nullptr;
                }

                return load_as_e32img(*e32img, lib_path);
            }

            return nullptr;
'''
    new='''            symfile f = io_->open_file(lib_path, READ_MODE | BIN_MODE | additional_mode_);
            if (!f) {
                if (nativeboot2_root_diag) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_OPEN_FAIL] path={} reason=open_file",
                        common::ucs2_to_utf8(lib_path));
                }
                LOG_ERROR(KERNEL, "Can't open {}", common::ucs2_to_utf8(lib_path));
                return nullptr;
            }

            eka2l1::ro_file_stream image_data_stream(f.get());

            if (f->is_in_rom()) {
                if (nativeboot2_root_diag) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_FORMAT] path={} is_e32=0 is_rom=1 in_rom=1 format=ROM",
                        common::ucs2_to_utf8(lib_path));
                }

                auto romimg = loader::parse_romimg(reinterpret_cast<common::ro_stream *>(&image_data_stream), mem_, kern_->get_epoc_version(), is_driver_lib);
                if (!romimg) {
                    if (nativeboot2_root_diag) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_PARSE_FAIL] path={} format=ROM",
                            common::ucs2_to_utf8(lib_path));
                    }
                    return nullptr;
                }

                return load_as_romimg(*romimg, lib_path, is_driver_lib);
            } else {
                if (nativeboot2_root_diag) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_FORMAT] path={} is_e32=1 is_rom=0 in_rom=0 format=E32",
                        common::ucs2_to_utf8(lib_path));
                }

                auto e32img = loader::parse_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream));
                if (!e32img) {
                    if (nativeboot2_root_diag) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_PARSE_FAIL] path={} format=E32",
                            common::ucs2_to_utf8(lib_path));
                    }
                    return nullptr;
                }

                return load_as_e32img(*e32img, lib_path);
            }

            return nullptr;
'''
    lm=replace_once(lm,old,new,"B28 image branch diagnostics")

    # Preserve the B28 direct rooted-path semantics exactly. We only expose
    # whether the direct VFS lookup succeeds and whether a present file is
    # loadable.
    old='''        if (!io_->exist(lib_path)) {
            return nullptr;
        }

        // Add the codeseg that trying to be loaded path to search path, for dependencies search.
        search_paths.insert(search_paths.begin(), eka2l1::file_directory(lib_path, true));

        if (auto cs = load_depend_on_drive(lib_path, is_driver_lib)) {
            cs->set_full_path(lib_path);
            search_paths.erase(search_paths.begin());
            return cs;
        }

        search_paths.erase(search_paths.begin());
        return nullptr;
'''
    new='''        if (!io_->exist(lib_path)) {
            if (nativeboot2_root_diag) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][LDR_ROOT_DIRECT] request={} path={} has_drive=0 exists=0",
                    common::ucs2_to_utf8(name), common::ucs2_to_utf8(lib_path));
                LOG_WARN(KERNEL,
                    "[NBOOT2][LDR_ROOT_MISS] request={} reason=direct_vfs_miss",
                    common::ucs2_to_utf8(name));
            }
            return nullptr;
        }

        if (nativeboot2_root_diag) {
            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_ROOT_DIRECT] request={} path={} has_drive=0 exists=1",
                common::ucs2_to_utf8(name), common::ucs2_to_utf8(lib_path));
        }

        // Add the codeseg that trying to be loaded path to search path, for dependencies search.
        search_paths.insert(search_paths.begin(), eka2l1::file_directory(lib_path, true));

        if (auto cs = load_depend_on_drive(lib_path, is_driver_lib)) {
            if (nativeboot2_root_diag) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][LDR_CODESEG_RESULT] request={} path={} success=1",
                    common::ucs2_to_utf8(name), common::ucs2_to_utf8(lib_path));
            }
            cs->set_full_path(lib_path);
            search_paths.erase(search_paths.begin());
            return cs;
        }

        if (nativeboot2_root_diag) {
            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_CODESEG_RESULT] request={} path={} success=0",
                common::ucs2_to_utf8(name), common::ucs2_to_utf8(lib_path));
        }
        search_paths.erase(search_paths.begin());
        return nullptr;
'''
    lm=replace_once(lm,old,new,"B28 direct rooted-path diagnostics")

    # Loader service boundary. Insert after the stable own-process assignment;
    # do not depend on the historical search_list container type.
    old='''        kernel::process *own_pr = ctx.msg->own_thr->owning_process();
'''
    new='''        kernel::process *own_pr = ctx.msg->own_thr->owning_process();
        const bool nativeboot2_root_diag =
            eka2l1::has_root_dir(*lib_path) && eka2l1::root_name(*lib_path, true).empty();

        if (nativeboot2_root_diag) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][LDR_LIB_REQUEST] process={} request_path={} rooted_no_drive=1 owner={}",
                own_pr->name(), common::ucs2_to_utf8(*lib_path),
                static_cast<int>(handle_owner));
        }
'''
    # The exact assignment occurs once in load_library in the B28 cache.
    ls=replace_once(ls,old,new,"loader request diagnostics")

    old='''        if (!cs) {
            LOG_DEBUG(SERVICE_LOADER, "Try loading {} to {} failed", lib_name, own_pr->name());
            ctx.complete(epoc::error_not_found);
            return;
        }
'''
    new='''        if (!cs) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][LDR_LIB_RESULT] process={} request_path={} rooted_no_drive={} success=0 completion={}",
                own_pr->name(), common::ucs2_to_utf8(*lib_path),
                nativeboot2_root_diag, epoc::error_not_found);
            LOG_DEBUG(SERVICE_LOADER, "Try loading {} to {} failed", lib_name, own_pr->name());
            ctx.complete(epoc::error_not_found);
            return;
        }
'''
    ls=replace_once(ls,old,new,"loader failure result diagnostics")

    old='''        LOG_TRACE(SERVICE_LOADER, "Loaded library: {}", lib_name);

        if (info) {
'''
    new='''        LOG_TRACE(SERVICE_LOADER, "Loaded library: {}", lib_name);

        if (nativeboot2_root_diag) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][LDR_LIB_RESULT] process={} request_path={} rooted_no_drive=1 success=1 handle=0x{:08X} completion=0",
                own_pr->name(), common::ucs2_to_utf8(*lib_path),
                lib_handle_and_obj.first);
        }

        if (info) {
'''
    ls=replace_once(ls,old,new,"loader success result diagnostics")

    lower=(lm+"\n"+ls).lower()
    if "eiksrvui.dll" in lower:
        fail("target DLL hardcoded into generic loader diagnostics")
    if "0x100053d0" in lower:
        fail("target UID hardcoded into generic loader diagnostics")

    lib.write_text(lm,encoding="utf-8")
    ldr.write_text(ls,encoding="utf-8")

    for needle in (
        "[NBOOT2][LDR_ROOT_BEGIN]",
        "[NBOOT2][LDR_ROOT_DIRECT]",
        "[NBOOT2][LDR_ROOT_MISS]",
        "[NBOOT2][LDR_OPEN_FAIL]",
        "[NBOOT2][LDR_FORMAT]",
        "[NBOOT2][LDR_PARSE_FAIL]",
        "[NBOOT2][LDR_CODESEG_RESULT]",
        "[NBOOT2][LDR_DEP_FAIL]",
    ):
        if needle not in lm:
            fail(f"post-apply libmanager marker missing: {needle}")
    for needle in ("[NBOOT2][LDR_LIB_REQUEST]","[NBOOT2][LDR_LIB_RESULT]"):
        if needle not in ls:
            fail(f"post-apply loader marker missing: {needle}")

    print(f"{MARK}: applied")
    print("semantics=B29_UNCHANGED")
    print("baseline=B28_FASTBUILD_CACHE")
    print("scope=ROOTED_RLIBRARY_DIAGNOSTICS_ONLY")
    print("target_hardcode=NONE")
    print("B28_WSERVLIBTYPE1=PRESERVED")
    print("B29_CENREPTX1=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
