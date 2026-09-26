#!/usr/bin/env python3
"""NATIVEBOOT2 B88 PHONEUICONE14CONTINUE1.

Let EStart continue past the one confirmed PhoneUI Telephone CONE 14 startup
panic by ending only that failing process with a clean exit result. This is a
deliberate compatibility bypass, not a fix for the missing guest resource.
Every other thread exit and panic retains its original type/category/reason.
"""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-B88-PHONEUICONE14CONTINUE1"
LOG_MARKER = "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]"
ANCHOR = "        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def apply(upstream_root):
    upstream = Path(upstream_root).resolve()
    svc = upstream / "src/emu/kernel/src/svc.cpp"
    fs = upstream / "src/emu/services/src/fs/files.cpp"
    if not svc.is_file() or not fs.is_file():
        fail("expected B28 source files svc.cpp and files.cpp")

    source = svc.read_text(encoding="utf-8")
    fs_source = fs.read_text(encoding="utf-8")
    if LOG_MARKER in source:
        if source.count(LOG_MARKER) == 2 and source.count(ANCHOR) == 1:
            print(MARK + ": already applied")
            return
        fail("partial B88 application detected")

    if "[NBOOT2][CONE14_PHONEUI]" not in source:
        fail("B71 Telephone CONE14 evidence gate missing")
    if "const bool nboot2_b71_phoneui_cone14" not in source:
        fail("B71 exact Telephone/UID3/reason/category predicate missing")
    if "[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B87]" not in fs_source:
        fail("B87 callhandlingui owner evidence gate missing")
    if source.count(ANCHOR) != 1:
        fail("expected one original thread-kill dispatch")

    injected = f'''        // B88 intentionally lets native startup continue after the one
        // proven Telephone/PhoneUI CONE 14 resource panic. This does not
        // repair the missing guest resource; all other exits are unchanged.
        if (nboot2_b71_phoneui_cone14) {{
            LOG_WARN(KERNEL,
                "{LOG_MARKER} phase=before process={{}} uid3=0x{{:08X}} "
                "type={{}} category={{}} reason={{}} action=CLEAN_EXIT",
                target_pr ? target_pr->name() : "<null>",
                nboot2_b71_target_uid3, static_cast<int>(etype),
                exit_category, reason);
            etype = kernel::entity_exit_type::terminate;
            exit_category = "None";
            reason = 0;
            LOG_WARN(KERNEL,
                "{LOG_MARKER} phase=after process={{}} uid3=0x{{:08X}} "
                "type={{}} category={{}} reason={{}} "
                "scope=TELEPHONE_CONE14_ONLY",
                target_pr ? target_pr->name() : "<null>",
                nboot2_b71_target_uid3, static_cast<int>(etype),
                exit_category, reason);
        }}

'''
    source = source.replace(ANCHOR, injected + ANCHOR, 1)
    svc.write_text(source, encoding="utf-8")
    print(MARK + ": applied")
    print("gate=Telephone UID3 0x100058B3 / CONE / reason 14")
    print("action=terminate process with reason 0 so native startup can proceed")
    print("other_panics=unchanged")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b88_phoneuicone14continue1.py <upstream-root>")
    apply(sys.argv[1])


if __name__ == "__main__":
    main()
