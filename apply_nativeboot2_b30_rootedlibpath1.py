#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B30 ROOTEDLIBPATH1 after B29 LOADERDIAG1.

Device evidence shows rooted RLibrary requests such as \\sys\\bin\\EiksrvUi.dll
reach lib_manager::load() without a drive and fail at the historical direct VFS
existence check. Upstream EKA2L1 commit 437b29006bd8a0186f4070c9445f43e98e5c7435
fixes this class by trying drive-qualified candidates.

This backport is intentionally narrower than that upstream batch:
- only lib_manager::load() rooted-no-drive resolution is added;
- existing B29 LOADERDIAG1 remains in place for the first B30 device trace;
- ROM/E32 classification, parsing, dependencies, relocations and SVCs are untouched;
- no Nokia DLL name or UID is hardcoded.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B30-ROOTEDLIBPATH1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b30_rootedlibpath1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    ldr=up/"src/emu/services/src/loader/loader.cpp"
    cen=up/"src/emu/services/src/centralrepo/repo.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (lib,ldr,cen,svc):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    lm=lib.read_text(encoding="utf-8")
    ls=ldr.read_text(encoding="utf-8")
    cr=cen.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")

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
            fail(f"B29 LOADERDIAG1 marker missing: {needle}")
    for needle in ("[NBOOT2][LDR_LIB_REQUEST]","[NBOOT2][LDR_LIB_RESULT]"):
        if needle not in ls:
            fail(f"B29 loader-service marker missing: {needle}")
    for needle in ("[NBOOT2][CEN_TX_START]","[NBOOT2][CEN_TX_COMMIT]"):
        if needle not in cr:
            fail(f"B29 CENREPTX1 marker missing: {needle}")
    if "[NBOOT2][WSERV_LIBRARY_TYPE]" not in sv:
        fail("B28 WSERVLIBTYPE1 marker missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    if "[NBOOT2][LDR_ROOT_RESOLVED]" in lm:
        print(f"{MARK}: already applied")
        return

    # Insert immediately before the historical direct rooted-path VFS check.
    # nativeboot2_root_diag was introduced by LOADERDIAG1 and exactly denotes
    # has_root_dir(name) && root_name(name,true).empty().
    old='''        if (!io_->exist(lib_path)) {
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
'''
    new='''        // B30 ROOTEDLIBPATH1: Symbian may pass an absolute image path with
        // no drive (for example, "\\\\sys\\\\bin\\\\foo.dll"). The historical
        // B28 loader opened that string verbatim. Resolve only this form across
        // drives, matching the narrow behavior from upstream commit 437b290.
        if (nativeboot2_root_diag) {
            for (drive_number drv = drive_a; drv <= drive_z;
                 drv = static_cast<drive_number>(static_cast<int>(drv) + 1)) {
                std::u16string candidate(1, drive_to_char16(drv));
                candidate += u':';
                candidate += lib_path;

                const bool candidate_exists = io_->exist(candidate);
                if (candidate_exists) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_ROOT_CANDIDATE] request={} candidate={} exists=1",
                        common::ucs2_to_utf8(name), common::ucs2_to_utf8(candidate));

                    if (codeseg_ptr result = load_depend_on_drive(candidate, is_driver_lib)) {
                        result->set_full_path(candidate);
                        LOG_WARN(KERNEL,
                            "[NBOOT2][LDR_ROOT_RESOLVED] request={} candidate={} success=1",
                            common::ucs2_to_utf8(name), common::ucs2_to_utf8(candidate));
                        return result;
                    }

                    LOG_WARN(KERNEL,
                        "[NBOOT2][LDR_ROOT_CANDIDATE] request={} candidate={} exists=1 loadable=0",
                        common::ucs2_to_utf8(name), common::ucs2_to_utf8(candidate));
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][LDR_ROOT_EXHAUSTED] request={} success=0",
                common::ucs2_to_utf8(name));
            return nullptr;
        }

        if (!io_->exist(lib_path)) {
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
'''
    lm=replace_once(lm,old,new,"rooted-no-drive resolution insertion")

    # Guard against accidentally absorbing other parts of the large upstream batch.
    if "loader::is_e32img(reinterpret_cast<common::ro_stream *>(&image_data_stream))" in lm:
        fail("out-of-scope ROM/E32 classification change detected")

    lower=(lm+"\n"+ls).lower()
    if "eiksrvui.dll" in lower or "0x100053d0" in lower:
        fail("target EiksrvUi DLL/UID hardcoded")

    lib.write_text(lm,encoding="utf-8")

    for needle in (
        "[NBOOT2][LDR_ROOT_CANDIDATE]",
        "[NBOOT2][LDR_ROOT_RESOLVED]",
        "[NBOOT2][LDR_ROOT_EXHAUSTED]",
        "load_depend_on_drive(candidate, is_driver_lib)",
        "result->set_full_path(candidate);",
    ):
        if needle not in lm:
            fail(f"post-apply B30 marker/semantic missing: {needle}")

    print(f"{MARK}: applied")
    print("scope=ROOTED_NO_DRIVE_LIB_MANAGER_LOAD_ONLY")
    print("upstream_reference=437b29006bd8a0186f4070c9445f43e98e5c7435")
    print("drive_resolution=A_TO_Z_AS_UPSTREAM")
    print("B29_LOADERDIAG1=PRESERVED")
    print("ROM_E32_CLASSIFICATION=UNCHANGED")
    print("DEPENDENCIES=UNCHANGED")
    print("SVC_TABLES=UNCHANGED")
    print("target_hardcode=NONE")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
