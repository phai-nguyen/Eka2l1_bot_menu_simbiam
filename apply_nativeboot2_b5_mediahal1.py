#!/usr/bin/env python3
"""NATIVEBOOT2-B5 MEDIAHAL1.

Apply on top of B4 CUSTOMLDD1.

Observed B4 runtime:
  Custom.ldd channel creation succeeds
  Custom control opcodes 1 and 8 return
  HAL category 0x2 function 0 is missing
  EStart panics ESTART_7 / KErrNotFound

Symbian source identifies:
  EHalGroupMedia = 2
  EMediaHalDriveInfo = 0
  UserHal::DriveInfo() -> Exec::HalFunction(2, 0, TDriveInfoV1Buf8, NULL)

The RM-356 firmware's ESTARTCOMP.TXT references registered local drives
0,2,6,9,10,11, giving bitmask 0x00000E45. B5 adds a proper EKA2
TDriveInfoV18 ABI bridge for that media HAL query.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B5-MEDIAHAL1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def patch_hal_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "hal_category_media = 2" not in text:
        old = """    enum hal_category {
        hal_category_kernel = 0,
        hal_category_variant = 1,
        hal_category_display = 4,
"""
        new = """    enum hal_category {
        hal_category_kernel = 0,
        hal_category_variant = 1,
        // NATIVEBOOT2-B5 MEDIAHAL1: Symbian EHalGroupMedia.
        hal_category_media = 2,
        hal_category_display = 4,
"""
        text = replace_once(text, old, new, "HAL media category")

    if "media_hal_drive_info" not in text:
        anchor = """    enum variant_hal_function {
"""
        insert = """    enum media_hal_function {
        // Symbian TMediaHalFunction::EMediaHalDriveInfo
        media_hal_drive_info = 0
    };

""" + anchor
        text = replace_once(text, anchor, insert, "HAL media function enum")

    path.write_text(text, encoding="utf-8")

def patch_hal_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[NBOOT2][MEDIA_DRIVE_INFO]" in text:
        return

    anchor = """    struct variant_hal : public eka2l1::epoc::hal {
"""
    media = r'''    // NATIVEBOOT2-B5 MEDIAHAL1.
    //
    // UserHal::DriveInfo() uses the 8-bit EKA2 compatibility structure
    // TDriveInfoV18 internally. TBuf8<16> has the same in-memory shape as
    // epoc::buf_static<char, 0x10>: descriptor info, max length, 16 data bytes.
    struct media_drive_info_v18 {
        std::int32_t total_supported_drives_;
        epoc::buf_static<char, 0x10> drive_name_[16];
        std::int32_t total_sockets_;
        epoc::buf_static<char, 0x10> socket_name_[4];
        std::int32_t rugged_file_system_;
        std::uint32_t registered_drive_bitmask_;
    };

    static_assert(sizeof(media_drive_info_v18) == 496,
        "TDriveInfoV18 ABI size mismatch");

    struct media_hal : public eka2l1::epoc::hal {
        int drive_info(int *a1, int *, const std::uint16_t) {
            if (!a1) {
                return epoc::error_argument;
            }

            epoc::des8 *package = reinterpret_cast<epoc::des8 *>(a1);
            kernel::process *process = sys->get_kernel_system()->crr_process();
            if (!process || !package->is_valid_descriptor()) {
                LOG_ERROR(SYSTEM, "[NBOOT2][MEDIA_DRIVE_INFO_BADARGS] process={} package={}",
                    process ? 1 : 0, package ? 1 : 0);
                return epoc::error_argument;
            }

            media_drive_info_v18 info;

            // RM-356 ESTARTCOMP.TXT local-drive set:
            // D:0, E:2, C:6, Z/ROFS:9,10,11.
            constexpr std::uint32_t RM356_REGISTERED_DRIVE_MASK = 0x00000E45;
            info.total_supported_drives_ = 6;
            info.total_sockets_ = 0;
            info.rugged_file_system_ = 1;
            info.registered_drive_bitmask_ = RM356_REGISTERED_DRIVE_MASK;

            // Names are informational but must be valid embedded descriptors,
            // because euser.dll copies all sixteen TBuf8 entries into the
            // public Unicode TDriveInfoV1 returned to EStart.
            info.drive_name_[0] = std::string("IRAM");
            info.drive_name_[2] = std::string("MEMCARD");
            info.drive_name_[6] = std::string("MEDUSII");
            info.drive_name_[9] = std::string("ROFS0");
            info.drive_name_[10] = std::string("ROFS1");
            info.drive_name_[11] = std::string("ROFS2");

            const int assign_result = package->assign(process,
                reinterpret_cast<const std::uint8_t *>(&info), sizeof(info));
            if (assign_result != 0) {
                LOG_ERROR(SYSTEM,
                    "[NBOOT2][MEDIA_DRIVE_INFO_ASSIGN_FAIL] result={} max={} size={}",
                    assign_result, package->get_max_length(process), sizeof(info));
                return epoc::error_argument;
            }

            LOG_WARN(SYSTEM,
                "[NBOOT2][MEDIA_DRIVE_INFO] drives={} sockets={} rugged={} mask=0x{:08X} bytes={}",
                info.total_supported_drives_, info.total_sockets_,
                info.rugged_file_system_, info.registered_drive_bitmask_,
                sizeof(info));
            return epoc::error_none;
        }

        explicit media_hal(eka2l1::system *sys)
            : hal(sys) {
            REGISTER_HAL_FUNC(media_hal_drive_info, media_hal, drive_info);
        }
    };

'''
    text = replace_once(text, anchor, media + anchor, "media HAL implementation")

    init_old = """        REGISTER_HAL_D(sys, hal_category_kernel, kern_hal);
        REGISTER_HAL(sys, hal_category_variant, variant_hal);
        REGISTER_HAL(sys, hal_category_display, display_hal);
"""
    init_new = """        REGISTER_HAL_D(sys, hal_category_kernel, kern_hal);
        REGISTER_HAL(sys, hal_category_variant, variant_hal);
        // NATIVEBOOT2-B5: needed by RM-356 EStart UserHal::DriveInfo().
        REGISTER_HAL(sys, hal_category_media, media_hal);
        REGISTER_HAL(sys, hal_category_display, display_hal);
"""
    text = replace_once(text, init_old, init_new, "register media HAL")

    path.write_text(text, encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b5_mediahal1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    hal_h = up / "src/emu/system/include/system/hal.h"
    hal_cpp = up / "src/emu/system/src/hal.cpp"
    custom = up / "src/emu/ldd/src/custom/custom.cpp"
    nokiaisc = up / "src/emu/ldd/src/nokiaisc/nokiaisc.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (hal_h, hal_cpp, custom, nokiaisc, svc, state, root):
        if not p.is_file():
            fail(f"missing B4 baseline file: {p}")

    if "[NBOOT2][CUSTOM_CONTROL]" not in custom.read_text(encoding="utf-8"):
        fail("B4 Custom.ldd marker missing")
    if "[NBOOT2][NOKIAISC_INIT_COMPLETE]" not in nokiaisc.read_text(encoding="utf-8"):
        fail("B3 NokiaISC marker missing")
    if "NATIVEBOOT2-B2 NOKIAISC1 EP94_CHANNEL_ABI" not in svc.read_text(encoding="utf-8"):
        fail("B2 EPOC94 channel ABI marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("Emulator Hub marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    patch_hal_header(hal_h)
    patch_hal_cpp(hal_cpp)

    h = hal_h.read_text(encoding="utf-8")
    c = hal_cpp.read_text(encoding="utf-8")

    required_h = [
        "hal_category_media = 2",
        "media_hal_drive_info = 0",
    ]
    for gate in required_h:
        if gate not in h:
            fail(f"HAL header gate missing: {gate}")

    required_cpp = [
        "static_assert(sizeof(media_drive_info_v18) == 496",
        "RM356_REGISTERED_DRIVE_MASK = 0x00000E45",
        "[NBOOT2][MEDIA_DRIVE_INFO]",
        "REGISTER_HAL(sys, hal_category_media, media_hal)",
    ]
    for gate in required_cpp:
        if gate not in c:
            fail(f"HAL cpp gate missing: {gate}")

    # Preserve RM-356 EPOC94 message ABI invariant.
    svc_body = svc.read_text(encoding="utf-8")
    a = svc_body.find("const eka2l1::hle::func_map svc_register_funcs_v94 = {")
    b = svc_body.find("\n    };", a)
    v94 = svc_body[a:b]
    if "BRIDGE_REGISTER(0xAA," in v94:
        fail("EPOC94 0xAA must remain unmapped")
    if "BRIDGE_REGISTER(0xAB, message_construct)" not in v94:
        fail("EPOC94 0xAB invariant lost")
    if "BRIDGE_REGISTER(0xAC, message_kill)" not in v94:
        fail("EPOC94 0xAC invariant lost")

    print("NATIVEBOOT2-B5 MEDIAHAL1 applied")
    print("HAL_group_2=media")
    print("HAL_media_func_0=DriveInfo")
    print("TDriveInfoV18_size=496")
    print("RM356_registered_drive_mask=0x00000E45")
    print("RM356_total_local_drives=6")
    print("CUSTOMLDD1=PRESERVED")
    print("NOKIAISC2=PRESERVED")
    print("EMUHUB1=PRESERVED")
    print("NOJAVA=PRESERVED")

if __name__ == "__main__":
    main()
