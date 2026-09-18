#!/usr/bin/env python3
"""MENUUI23 APPTYPE1: implement AppListServer GetAppType (opcode 73).

Baseline: MENUUI22 SCHEDRUN1 NOJAVA MANIC3.

Device logs prove Menu issues a synchronous !AppListServer opcode 73 request
for a registered native application and the request never completes because
EKA2L1 falls through to "Unimplemented applist opcode 0x49".

Symbian AppArc defines opcode 73 as GetAppType. For a native application the
returned type is KNullUid. This NOJAVA build only models native registrations,
so return KNullUid for a known registration, KErrNotFound for an unknown UID,
and KErrBadDescriptor if the output TPckg<TUid> cannot be written.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI23 APPTYPE1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui23_apptype1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    applist = up / "src/emu/services/src/applist/applist.cpp"
    op = up / "src/emu/services/include/services/applist/op.h"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (applist, op, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("legacy src/emu/j2me unexpectedly present")

    op_text = op.read_text(encoding="utf-8")
    enum_window = """        applist_request_deregister_non_native_app, // = 70
        applist_request_commit_non_native_application,
        applist_request_rollback_non_native_application,
        applist_request_get_app_type,
"""
    if enum_window not in op_text:
        fail("modern AppList opcode 73 enum window not found")

    kernel_text = kernel.read_text(encoding="utf-8")
    for marker in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_ARM:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_DONE:",
    ):
        if marker not in kernel_text:
            fail("SCHEDRUN1 baseline marker missing: " + marker)

    svc_text = svc.read_text(encoding="utf-8")
    for marker in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_SEND:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER:",
        "SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN:",
    ):
        if marker not in svc_text:
            fail("MENUUI22 authority marker missing: " + marker)

    root_text = root.read_text(encoding="utf-8")
    if "MANIC_MODALFIX1" not in root_text:
        fail("MANIC3 MODALFIX1 baseline missing")
    if 'if (i == 7) return @"Manic Skin";' not in root_text:
        fail("Manic Skin baseline missing")

    text = applist.read_text(encoding="utf-8")
    marker = "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:"
    if marker in text:
        if text.count(marker) == 4 and "case applist_request_get_app_type:" in text:
            print("MENUUI23 APPTYPE1 already present")
            return
        fail("partial prior APPTYPE1 patch detected")

    # Put the implementation in the modern AppArc switch. Keep the scope
    # deliberately narrow: no Java MIDlet mapping and no global behavior
    # change for other unimplemented AppList opcodes.
    anchor = """            case applist_request_app_language:
                server<applist_server>()->app_language(*ctx);
                break;

            case applist_request_rule_based_launching:
"""
    replacement = """            case applist_request_app_language:
                server<applist_server>()->app_language(*ctx);
                break;

            case applist_request_get_app_type: {
                // Symbian AppArc EAppListServGetAppType (opcode 73).
                // RApaLsSession::GetAppType passes app UID in arg0 and a
                // TPckg<TUid> output descriptor in arg1. Native applications
                // must report KNullUid. This NOJAVA port has no host J2ME
                // registration model, so all registrations represented here
                // are handled as native.
                const std::optional<epoc::uid> app_uid =
                    ctx->get_argument_value<epoc::uid>(0);
                if (!app_uid.has_value()) {
                    LOG_WARN(SERVICE_APPLIST,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE: result=bad_argument opcode=73");
                    ctx->complete(epoc::error_argument);
                    break;
                }

                apa_app_registry *reg =
                    server<applist_server>()->get_registration(app_uid.value());
                if (!reg) {
                    LOG_WARN(SERVICE_APPLIST,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE: result=not_found opcode=73 app_uid=0x{:08X}",
                        static_cast<std::uint32_t>(app_uid.value()));
                    ctx->complete(epoc::error_not_found);
                    break;
                }

                const epoc::uid native_type_uid = 0; // KNullUid
                if (!ctx->write_data_to_descriptor_argument<epoc::uid>(
                        1, native_type_uid)) {
                    LOG_WARN(SERVICE_APPLIST,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE: result=bad_descriptor opcode=73 app_uid=0x{:08X}",
                        static_cast<std::uint32_t>(app_uid.value()));
                    ctx->complete(epoc::error_bad_descriptor);
                    break;
                }

                LOG_WARN(SERVICE_APPLIST,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE: result=native opcode=73 app_uid=0x{:08X} type_uid=0x00000000",
                    static_cast<std::uint32_t>(app_uid.value()));
                ctx->complete(epoc::error_none);
                break;
            }

            case applist_request_rule_based_launching:
"""
    text = replace_once(text, anchor, replacement, "modern AppList switch")

    if text.count("case applist_request_get_app_type:") != 1:
        fail("GetAppType case gate failed")
    if text.count(marker) != 4:
        fail(f"APPTYPE marker gate failed: count={text.count(marker)}")
    for required in (
        "const epoc::uid native_type_uid = 0; // KNullUid",
        "ctx->complete(epoc::error_not_found);",
        "ctx->complete(epoc::error_bad_descriptor);",
        "ctx->complete(epoc::error_none);",
        "write_data_to_descriptor_argument<epoc::uid>",
    ):
        if required not in text:
            fail("implementation gate missing: " + required)

    # Do not add the Java/non-native UID mappings from the full Symbian
    # implementation to this intentionally NOJAVA build.
    for forbidden in ("0xB031C52A", "0x10210E26"):
        if forbidden in text:
            fail("NOJAVA invariant violated by Java app-type mapping")

    applist.write_text(text, encoding="utf-8")
    print("MENUUI23 APPTYPE1 applied")
    print("MENUUI23 APPTYPE1 opcode73=GetAppType known_native=>KNullUid")
    print("MENUUI23 APPTYPE1 unknown_uid=>KErrNotFound bad_descriptor=>KErrBadDescriptor")
    print("MENUUI23 APPTYPE1 Java/J2ME mapping=NOT_ADDED")


if __name__ == "__main__":
    main()
