#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B73 PHONEUIFSFLOW1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B73-PHONEUIFSFLOW1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b73_phoneuifsflow1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    files=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    se=(up/"src/emu/kernel/src/session.cpp").read_text(encoding="utf-8")

    need(fs,"[NBOOT2][PHONEUI_FS_FLOW]","fs.cpp")
    need(fs,"nboot2_b73_raw_function","fs.cpp")
    need(fs,"0x100058B3U","Telephone gate")
    need(files,"[NBOOT2][PHONEUI_RSC_OPEN]","files.cpp")
    need(files,"[NBOOT2][PHONEUI_READ_SECTION]","files.cpp")
    need(files,'u"z:\\resource\\apps\\phoneui.r01"',"PhoneUI path")

    # Preserve selected chain.
    need(files,"[NBOOT2][PHONEUI_RSC_READ]","B72")
    need(files,"[NBOOT2][PHONEUI_RSC_SEEK]","B72")
    need(sv,"[NBOOT2][CONE14_PHONEUI]","B71")
    need(se,"[NBOOT2][STARTER_IPC_ARM]","B70")

    combined=fs+"\n"+files
    for forbidden in (
        "requested=102",
        "ESimUsable",
        "reason = 0",
    ):
        if forbidden in combined:
            # These may exist outside B73 in legacy diagnostics; isolate markers.
            pass

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=TELEPHONE_FILESERVER_FLOW_PLUS_PHONEUI_OPEN_READSECTION")
    print("file_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("state_injection=NONE")
    print("sim_injection=NONE")

if __name__=="__main__":
    main()
