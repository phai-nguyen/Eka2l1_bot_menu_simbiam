#!/usr/bin/env python3
"""NATIVEBOOT2 B75 PHONEUIRESCALLER2.

B74 DEVICE1 proved the B74 caller probe was present in the exact tested Mach-O,
but its generated C++ path literals used single backslashes. C++ interpreted
"\r" and "\a" inside z:\resource\apps\..., so the path predicate could never
match the real FileServer path.

B75 is diagnostic-only. It corrects those C++ literals to escaped Symbian
paths, emits an explicit exact-path match marker, and preserves the existing
B74 saved-context/stack capture. No resource registration or guest behavior is
changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B75-PHONEUIRESCALLER2"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b75_phoneuirescaller2.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs_cpp=up/"src/emu/services/src/fs/fs.cpp"
    if not fs_cpp.is_file():
        fail(f"missing source: {fs_cpp}")

    fs=fs_cpp.read_text(encoding="utf-8")

    for gate in (
        "[NBOOT2][PHONEUI_FS_FLOW]",
        "[NBOOT2][PHONEUI_RES_CALLER]",
        "[NBOOT2][PHONEUI_RES_FRAME]",
        "[NBOOT2][PHONEUI_RES_ID]",
        "[NBOOT2][PHONEUI_RES_CONTEXT_DONE]",
    ):
        if gate not in fs:
            fail("B74/B73 gate missing: "+gate)

    if "[NBOOT2][PHONEUI_RES_MATCH2]" in fs:
        print(MARK+": already applied")
        return

    malformed_phone = r'u"z:\resource\apps\phoneui.r01"'
    malformed_call = r'u"z:\resource\apps\callhandlingui.r01"'
    corrected_phone = r'u"z:\\resource\\apps\\phoneui.r01"'
    corrected_call = r'u"z:\\resource\\apps\\callhandlingui.r01"'

    fs=rep1(fs, malformed_phone, corrected_phone, "phoneui escaped path")
    fs=rep1(fs, malformed_call, corrected_call, "callhandling escaped path")

    anchor = r'''            const bool nboot2_b74_callhandling =
                nboot2_b74_lower ==
                    u"z:\\resource\\apps\\callhandlingui.r01";

            if ((nboot2_b74_phoneui || nboot2_b74_callhandling) &&
'''

    inject = r'''            const bool nboot2_b74_callhandling =
                nboot2_b74_lower ==
                    u"z:\\resource\\apps\\callhandlingui.r01";

            if (nboot2_b74_phoneui || nboot2_b74_callhandling) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][PHONEUI_RES_MATCH2] path={} kind={} "
                    "opcode=0x{:02X} exact_path_match=1 "
                    "behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(nboot2_b74_path),
                    nboot2_b74_phoneui ? "PHONEUI" : "CALLHANDLINGUI",
                    nboot2_b74_opcode);
            }

            if ((nboot2_b74_phoneui || nboot2_b74_callhandling) &&
'''

    fs=rep1(fs, anchor, inject, "B75 exact-path match marker")

    for need in (
        corrected_phone,
        corrected_call,
        "[NBOOT2][PHONEUI_RES_MATCH2]",
        "[NBOOT2][PHONEUI_RES_CALLER]",
        "nboot2_b74_words=96",
        "0x1099B02DU",
    ):
        if need not in fs:
            fail("post-apply gate missing: "+need)

    if malformed_phone in fs or malformed_call in fs:
        fail("malformed B74 C++ path literal still present")

    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "set_int(",
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "kill(",
    ):
        if forbidden in inject:
            fail("behavior-changing token in B75 diagnostic: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fs_cpp.write_text(fs, encoding="utf-8")

    print(MARK+": applied")
    print("scope=B74_PATH_LITERAL_FIX_PLUS_EXACT_MATCH_MARKER")
    print(r"phoneui_literal=z:\\resource\\apps\\phoneui.r01")
    print(r"callhandling_literal=z:\\resource\\apps\\callhandlingui.r01")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("sim_state=UNCHANGED")
    print("host_teardown_fix=DEFERRED")
    print("B74_CONTEXT_CAPTURE=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__ == "__main__":
    main()
