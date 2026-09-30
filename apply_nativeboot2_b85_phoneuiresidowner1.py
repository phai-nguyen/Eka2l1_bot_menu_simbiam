#!/usr/bin/env python3
"""NATIVEBOOT2 B85 PHONEUIRESIDOWNER1.

Correct B84's unverified resource-owner label and dump the actual VPbk
resource file observed immediately before Telephone/CONE14, through a separate
read-only VFS handle. Guest boot/resource/panic behavior remains unchanged.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B85-PHONEUIRESIDOWNER1"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b85_phoneuiresidowner1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    svc = upstream / "src/emu/kernel/src/svc.cpp"
    files = upstream / "src/emu/services/src/fs/files.cpp"
    if not svc.is_file() or not files.is_file():
        fail("B84 svc.cpp or B71 files.cpp is missing")

    source = svc.read_text(encoding="utf-8")
    file_source = files.read_text(encoding="utf-8")
    if "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP]" in file_source:
        if ("source=CPU_REGISTER" in source
                and "owner=UNVERIFIED" in source
                and "owner=callhandlingui.r01" not in source):
            print(MARK + ": already applied")
            return
        fail("partial B85 application detected")

    for token in (
        "[NBOOT2][PHONEUI_RESID_SOURCE]",
        "[NBOOT2][PHONEUI_RESID_SUMMARY]",
        "source=REGISTER ",
        "owner=callhandlingui.r01",
        "resource_registration=UNCHANGED boot_behavior=UNCHANGED",
    ):
        if token not in source:
            fail(f"B84 evidence gate missing: {token}")

    source = source.replace("source=REGISTER ", "source=CPU_REGISTER ")
    source = source.replace("owner=callhandlingui.r01", "owner=UNVERIFIED")
    source = source.replace(
        "resource_registration=UNCHANGED boot_behavior=UNCHANGED",
        "owner=UNVERIFIED resource_registration=UNCHANGED "
        "boot_behavior=UNCHANGED",
    )
    svc.write_text(source, encoding="utf-8")

    helper_anchor = "    static void nboot2_b71_dump_phoneui_rsc(io_system *io,"
    if file_source.count(helper_anchor) != 1:
        fail("B71 read-only RSC helper anchor expected exactly once")
    hook_anchor = "        nboot2_b71_dump_phoneui_rsc(io, *name_res);"
    if file_source.count(hook_anchor) != 1:
        fail("B71 RSC open hook expected exactly once")

    helper = r'''    static void nboot2_b85_dump_vpbk_candidate_rsc(
        io_system *io,const std::u16string &path) {
        if (!io) {
            return;
        }
        const std::u16string lower=
            common::lowercase_ucs2_string(path);
        if (lower!=uR"(z:\resource\VPbkCntModelRes.r01)") {
            return;
        }

        // The B84 stack contains VPbkCntModel/VPbkEng frames. Capture this
        // exact file once through a separate read-only handle for offline
        // resource-ID ownership analysis.
        static bool captured=false;
        if (captured) {
            return;
        }

        symfile probe=io->open_file(path,READ_MODE|BIN_MODE);
        if (!probe || !probe->valid()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP] "
                "phase=open_fail path={} resource_id=0x1099B02D "
                "owner=UNVERIFIED behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
            return;
        }
        captured=true;

        const std::uint64_t raw_size=probe->size();
        constexpr std::size_t max_capture=262144;
        const std::size_t capture_size=static_cast<std::size_t>(
            raw_size>max_capture?max_capture:raw_size);
        std::string raw;
        raw.resize(capture_size);
        std::size_t bytes_read=0;
        if (capture_size>0) {
            bytes_read=probe->read_file(
                raw.data(),1,static_cast<std::uint32_t>(capture_size));
            if (bytes_read>capture_size) {
                bytes_read=capture_size;
            }
            raw.resize(bytes_read);
        }

        static constexpr char digits[]="0123456789ABCDEF";
        constexpr std::size_t chunk_bytes=512;
        const std::size_t chunks=raw.empty()?1:
            ((raw.size()+chunk_bytes-1)/chunk_bytes);
        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP] phase=begin "
            "path={} resource_id=0x1099B02D owner=UNVERIFIED raw_size={} "
            "captured={} truncated={} chunks={} encoding=HEX "
            "handle=SEPARATE_READ_ONLY behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path),raw_size,bytes_read,
            raw_size>max_capture,chunks);

        if (raw.empty()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP] phase=data "
                "path={} chunk=1/1 offset=0 bytes=0 hex=<EMPTY> "
                "behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
        } else {
            for (std::size_t off=0,index=0;
                 off<raw.size();off+=chunk_bytes,++index) {
                const std::size_t count=std::min(
                    chunk_bytes,raw.size()-off);
                std::string hex;
                hex.resize(count*2);
                for (std::size_t i=0;i<count;++i) {
                    const unsigned char ch=
                        static_cast<unsigned char>(raw[off+i]);
                    hex[i*2]=digits[(ch>>4)&0xF];
                    hex[i*2+1]=digits[ch&0xF];
                }
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP] "
                    "phase=data path={} chunk={}/{} offset={} bytes={} "
                    "hex={} behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(path),index+1,chunks,
                    off,count,hex);
            }
        }
        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][PHONEUI_RESID_RSC_CANDIDATE_DUMP] phase=end "
            "path={} owner=UNVERIFIED behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path));
    }

'''
    file_source = file_source.replace(helper_anchor, helper + helper_anchor, 1)
    file_source = file_source.replace(
        hook_anchor,
        "        nboot2_b85_dump_vpbk_candidate_rsc(io, *name_res);\n"
        + hook_anchor,
        1,
    )
    files.write_text(file_source, encoding="utf-8")

    print(MARK + ": applied")
    print("resource_id=0x1099B02D")
    print("owner=UNVERIFIED")
    print("candidate=Z:\\resource\\VPbkCntModelRes.r01")
    print("resource_registration=UNCHANGED")
    print("boot_behavior=UNCHANGED")


if __name__ == "__main__":
    main()
