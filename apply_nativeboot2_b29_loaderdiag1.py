#!/usr/bin/env python3
"""Apply B29-LOADERDIAG1 diagnostics after B29 CENREPTX1 + DIAG1.

Diagnostics only. No loader search, parse, codeseg, dependency, or completion
semantics are changed. The instrumentation targets the generic rooted-no-drive
RLibrary path class exposed by the B29 device trace.
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

    # E32 dependency failure telemetry. This is generic and only emits on failure.
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

    # Rooted-no-drive request classifier and begin marker.
    old='''    codeseg_ptr lib_manager::load(const std::u16string &name) {
        bool is_driver_lib = false;
'''
    new='''    codeseg_ptr lib_manager::load(const std::u16string &name) {
        const bool nativeboot2_root_diag =
            eka2l1::has_root_dir(name) && eka2l1::root_name(name, true).empty();

        if (nativeboot2_root_diag) {
            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_ROOT_BEGIN] request={}",
                common::ucs2_to_utf8(name));
        }

        bool is_driver_lib = false;
'''
    lm=replace_once(lm,old,new,"root begin diagnostics")

    # Open/format/parse/stage diagnostics inside the existing loader lambda.
    old='''            symfile f = io_->open_file(lib_path, READ_MODE | BIN_MODE | additional_mode_);
            if (!f) {
                LOG_ERROR(KERNEL, "Can't open {}", common::ucs2_to_utf8(lib_path));
                return nullptr;
            }

            eka2l1::ro_file_stream image_data_stream(f.get());

            const bool is_e32 = loader::is_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream));
            const bool is_rom = !is_e32 && (f->is_in_rom() || (kern_->get_epoc_version() == epocver::epoc91));

            if (is_rom) {
                auto romimg = loader::parse_romimg(reinterpret_cast<common::ro_stream *>(&image_data_stream), mem_, kern_->get_epoc_version(), is_driver_lib);
                if (!romimg) {
                    return nullptr;
                }

                if ((kern_->get_epoc_version() == epocver::epoc91)
                    && !stage_rom_image_outside_core(reinterpret_cast<common::ro_stream *>(&image_data_stream),
                        romimg->header.code_address)) {
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

            const bool is_e32 = loader::is_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream));
            const bool in_rom = f->is_in_rom();
            const bool is_rom = !is_e32 && (in_rom || (kern_->get_epoc_version() == epocver::epoc91));

            if (nativeboot2_root_diag) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][LDR_FORMAT] path={} is_e32={} is_rom={} in_rom={}",
                    common::ucs2_to_utf8(lib_path), is_e32, is_rom, in_rom);
            }

            if (is_rom) {
                auto romimg = loader::parse_romimg(reinterpret_cast<common::ro_stream *>(&image_data_stream), mem_, kern_->get_epoc_version(), is_driver_lib);
                if (!romimg) {
                    if (nativeboot2_root_diag) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_PARSE_FAIL] path={} format=ROM",
                            common::ucs2_to_utf8(lib_path));
                    }
                    return nullptr;
                }

                if ((kern_->get_epoc_version() == epocver::epoc91)
                    && !stage_rom_image_outside_core(reinterpret_cast<common::ro_stream *>(&image_data_stream),
                        romimg->header.code_address)) {
                    if (nativeboot2_root_diag) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_STAGE_FAIL] path={} format=ROM code_address=0x{:08X}",
                            common::ucs2_to_utf8(lib_path), romimg->header.code_address);
                    }
                    return nullptr;
                }

                return load_as_romimg(*romimg, lib_path, is_driver_lib);
            } else {
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
'''
    lm=replace_once(lm,old,new,"format/parse diagnostics")

    # Per-drive candidate + final rooted load result.
    old='''        if (eka2l1::has_root_dir(lib_path) && eka2l1::root_name(lib_path, true).empty()) {
            for (drive_number drv = drive_a; drv <= drive_z; drv = static_cast<drive_number>(static_cast<int>(drv) + 1)) {
                std::u16string candidate(1, drive_to_char16(drv));
                candidate += u':';
                candidate += lib_path;

                if (io_->exist(candidate)) {
                    if (codeseg_ptr result = load_depend_on_drive(candidate, is_driver_lib)) {
                        result->set_full_path(candidate);
                        return result;
                    }
                }
            }

            return nullptr;
        }
'''
    new='''        if (eka2l1::has_root_dir(lib_path) && eka2l1::root_name(lib_path, true).empty()) {
            for (drive_number drv = drive_a; drv <= drive_z; drv = static_cast<drive_number>(static_cast<int>(drv) + 1)) {
                std::u16string candidate(1, drive_to_char16(drv));
                candidate += u':';
                candidate += lib_path;

                if (io_->exist(candidate)) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_ROOT_CANDIDATE] request={} candidate={} exists=1",
                        common::ucs2_to_utf8(lib_path), common::ucs2_to_utf8(candidate));

                    if (codeseg_ptr result = load_depend_on_drive(candidate, is_driver_lib)) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_CODESEG_RESULT] request={} candidate={} success=1",
                            common::ucs2_to_utf8(lib_path), common::ucs2_to_utf8(candidate));
                        result->set_full_path(candidate);
                        return result;
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_CODESEG_RESULT] request={} candidate={} success=0",
                        common::ucs2_to_utf8(lib_path), common::ucs2_to_utf8(candidate));
                } else {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_ROOT_CANDIDATE] request={} candidate={} exists=0",
                        common::ucs2_to_utf8(lib_path), common::ucs2_to_utf8(candidate));
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_ROOT_MISS] request={} reason=no_loadable_candidate",
                common::ucs2_to_utf8(lib_path));
            return nullptr;
        }
'''
    lm=replace_once(lm,old,new,"root candidate diagnostics")

    # Loader service request/result boundary. Only rooted-no-drive requests emit.
    old='''        // Access to this library manager is locked by kernel lock, so we directly append additional search path
        hle::lib_manager *mngr = ctx.sys->get_lib_manager();
        kernel::process *own_pr = ctx.msg->own_thr->owning_process();

        std::vector<std::u16string> search_list;
'''
    new='''        // Access to this library manager is locked by kernel lock, so we directly append additional search path
        hle::lib_manager *mngr = ctx.sys->get_lib_manager();
        kernel::process *own_pr = ctx.msg->own_thr->owning_process();
        const bool nativeboot2_root_diag =
            eka2l1::has_root_dir(*lib_path) && eka2l1::root_name(*lib_path, true).empty();

        if (nativeboot2_root_diag) {
            LOG_WARN(SERVICE_LOADER,
                "[NBOOT2][LDR_LIB_REQUEST] process={} request_path={} owner={}",
                own_pr->name(), common::ucs2_to_utf8(*lib_path),
                static_cast<int>(handle_owner));
        }

        std::vector<std::u16string> search_list;
'''
    ls=replace_once(ls,old,new,"loader request diagnostics")

    old='''        if (!cs) {
            LOG_DEBUG(SERVICE_LOADER, "Try loading {} to {} failed", lib_name, own_pr->name());
            ctx.complete(epoc::error_not_found);
            return;
        }
'''
    new='''        if (!cs) {
            if (nativeboot2_root_diag) {
                LOG_WARN(SERVICE_LOADER,
                    "[NBOOT2][LDR_LIB_RESULT] process={} request_path={} success=0 completion={}",
                    own_pr->name(), common::ucs2_to_utf8(*lib_path),
                    epoc::error_not_found);
            }
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
                "[NBOOT2][LDR_LIB_RESULT] process={} request_path={} success=1 handle=0x{:08X} completion=0",
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
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_MISS]",
        "[NBOOT2][LDR_OPEN_FAIL]",
        "[NBOOT2][LDR_FORMAT]",
        "[NBOOT2][LDR_PARSE_FAIL]",
        "[NBOOT2][LDR_STAGE_FAIL]",
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
    print("scope=ROOTED_RLIBRARY_DIAGNOSTICS_ONLY")
    print("target_hardcode=NONE")
    print("B28_WSERVLIBTYPE1=PRESERVED")
    print("B29_CENREPTX1=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
