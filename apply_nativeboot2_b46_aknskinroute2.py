#!/usr/bin/env python3
"""NATIVEBOOT2 B46 AKNSKINROUTE2.

Repair only B45 route selection.

B45 device evidence showed:
- current RM-356 runtime enum did not satisfy exact epoc94 equality;
- Z-overlay existence was queried before the device Z profile was mounted.

B46 uses device-manager metadata that is available before service creation.
The route is enabled only for native_phone_boot and firmware_code beginning
with RM-356 (case variants accepted). B45 epoc/Z checks are retained as
diagnostic fields only.

No global epoc version change and no TFX/ALF/IPC synthesis.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B46-AKNSKINROUTE2"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep(text, old, new, label):
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b46_aknskinroute2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    init=up/"src/emu/services/src/init.cpp"
    if not init.is_file():
        fail(f"missing source file: {init}")

    i=init.read_text(encoding="utf-8")

    for marker in (
        "[NBOOT2][AKNSKIN_ROUTE]",
        "b45_aknskin_exe_sysbin",
        "epocver::epoc94",
        "CREATE_SERVER(sys, akn_skin_server);",
    ):
        if marker not in i:
            fail("missing B45 baseline: "+marker)

    if "[NBOOT2][AKNSKIN_ROUTE2]" in i:
        print(MARK+": already applied")
        return

    if "#include <system/devices.h>" not in i:
        i=rep(i,
            "#include <system/epoc.h>\n",
            "#include <system/epoc.h>\n#include <system/devices.h>\n",
            "device metadata include")

    old='''            const bool b45_aknskin_exe_sysbin =
                sys->get_io_system()->exist(u"z:\\sys\\bin\\aknskinsrv.exe");
            const bool b45_aknskin_exe_legacy =
                sys->get_io_system()->exist(u"z:\\system\\programs\\aknskinsrv.exe");
            const bool b45_aknskin_native_route =
                cfg->native_phone_boot
                && sys->get_symbian_version_use() == epocver::epoc94
                && (b45_aknskin_exe_sysbin || b45_aknskin_exe_legacy);

            if (b45_aknskin_native_route) {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_skip epoc=94 native_phone_boot=1 exe_sysbin={} exe_legacy={} expected_exe_uid3=0x10207114 behavior=GUEST_NATIVE_ROUTE",
                    b45_aknskin_exe_sysbin ? 1 : 0, b45_aknskin_exe_legacy ? 1 : 0);
            } else {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_keep epoc={} native_phone_boot={} exe_sysbin={} exe_legacy={} expected_exe_uid3=0x10207114 behavior=UNCHANGED_HLE",
                    static_cast<int>(sys->get_symbian_version_use()), cfg->native_phone_boot ? 1 : 0,
                    b45_aknskin_exe_sysbin ? 1 : 0, b45_aknskin_exe_legacy ? 1 : 0);
                CREATE_SERVER(sys, akn_skin_server);
            }
'''

    new='''            device *b46_current_device = sys->get_device_manager()->get_current();
            const std::string b46_firmware_code =
                b46_current_device ? b46_current_device->firmware_code : std::string();
            const std::string b46_model =
                b46_current_device ? b46_current_device->model : std::string();
            const bool b46_rm356_device =
                b46_firmware_code.rfind("rm-356", 0) == 0
                || b46_firmware_code.rfind("RM-356", 0) == 0;

            // B45 probes are intentionally preserved for chronology only.
            // They are not route gates: at this point the extracted Z-profile
            // overlay may not be mounted yet, and the current RM-356 runtime
            // enum is not a reliable product discriminator.
            const bool b45_epoc94_diag =
                sys->get_symbian_version_use() == epocver::epoc94;
            const bool b45_aknskin_exe_sysbin =
                sys->get_io_system()->exist(u"z:\\sys\\bin\\aknskinsrv.exe");
            const bool b45_aknskin_exe_legacy =
                sys->get_io_system()->exist(u"z:\\system\\programs\\aknskinsrv.exe");

            const bool b46_rm356_native_route =
                cfg->native_phone_boot && b46_rm356_device;

            if (b46_rm356_native_route) {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE2] decision=skip_hle firmware_code={} model={} epoc={} epoc94_diag={} native_phone_boot=1 pre_mount_exe_sysbin={} pre_mount_exe_legacy={} behavior=GUEST_NATIVE_ROUTE",
                    b46_firmware_code, b46_model,
                    static_cast<int>(sys->get_symbian_version_use()),
                    b45_epoc94_diag ? 1 : 0,
                    b45_aknskin_exe_sysbin ? 1 : 0,
                    b45_aknskin_exe_legacy ? 1 : 0);
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_skip epoc={} native_phone_boot=1 exe_sysbin={} exe_legacy={} expected_exe_uid3=0x10207114 behavior=GUEST_NATIVE_ROUTE",
                    static_cast<int>(sys->get_symbian_version_use()),
                    b45_aknskin_exe_sysbin ? 1 : 0,
                    b45_aknskin_exe_legacy ? 1 : 0);
            } else {
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE2] decision=keep_hle firmware_code={} model={} epoc={} epoc94_diag={} native_phone_boot={} pre_mount_exe_sysbin={} pre_mount_exe_legacy={} behavior=UNCHANGED_HLE",
                    b46_firmware_code, b46_model,
                    static_cast<int>(sys->get_symbian_version_use()),
                    b45_epoc94_diag ? 1 : 0,
                    cfg->native_phone_boot ? 1 : 0,
                    b45_aknskin_exe_sysbin ? 1 : 0,
                    b45_aknskin_exe_legacy ? 1 : 0);
                LOG_WARN(SERVICE_UI,
                    "[NBOOT2][AKNSKIN_ROUTE] phase=hle_keep epoc={} native_phone_boot={} exe_sysbin={} exe_legacy={} expected_exe_uid3=0x10207114 behavior=UNCHANGED_HLE",
                    static_cast<int>(sys->get_symbian_version_use()),
                    cfg->native_phone_boot ? 1 : 0,
                    b45_aknskin_exe_sysbin ? 1 : 0,
                    b45_aknskin_exe_legacy ? 1 : 0);
                CREATE_SERVER(sys, akn_skin_server);
            }
'''

    i=rep(i,old,new,"B46 route2 replacement")
    init.write_text(i,encoding="utf-8")

    print(MARK+": applied")
    print("route=RM356_DEVICE_METADATA")
    print("global_epoc_change=NONE")
    print("premount_z_gate=REMOVED")
    print("non_rm356=UNCHANGED_HLE")
    print("non_native_boot=UNCHANGED_HLE")
    print("fake_tfxserver=NONE")
    print("force_alfred=NONE")
    print("ecom_synthesis=NONE")
    print("ps_synthesis=NONE")

if __name__=="__main__":
    main()
