#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B72 PHONEUIRSCIO1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B72-PHONEUIRSCIO1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b72_phoneuirscio1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    se=(up/"src/emu/kernel/src/session.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    al=(up/"src/emu/services/src/alarm/alarm.cpp").read_text(encoding="utf-8")

    need(fs,"[NBOOT2][PHONEUI_RSC_READ]","files.cpp")
    need(fs,"[NBOOT2][PHONEUI_RSC_SEEK]","files.cpp")
    need(fs,'u"z:\\resource\\apps\\phoneui.r01"',"PhoneUI path")
    need(fs,"0x100058B3U","Telephone UID3")
    need(fs,"index_table_offset=27396","RSC geometry")
    need(fs,"resource_count=368","RSC geometry")
    need(fs,"resource_base=0x4E738000","RSC geometry")
    need(fs,"vfs_file->read_file(read_data.data(), 1, read_len);","original read")
    need(fs,"vfs_file->seek(*seek_off, vfs_seek_mode);","original seek")

    # Preserve chain.
    need(sv,"[NBOOT2][CONE14_PHONEUI]","B71")
    need(sv,"[NBOOT2][STARTER_GLOBAL_STATE]","B62")
    need(sv,"[NBOOT2][STARTER_WAIT_ANY]","B68")
    need(se,"[NBOOT2][STARTER_IPC_ARM]","B70")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64")
    need(al,"[NBOOT2][ALARM_ID_LIST]","B69")
    need(fs,"[NBOOT2][STARTER_SSC_DUMP]","B67")

    # Diagnostic only.
    for forbidden in (
        "read_pos = 27396",
        "read_len = 4",
        "requested=102",
        "ESimUsable",
    ):
        if forbidden in fs:
            fail("behavior-changing token: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=TELEPHONE_PHONEUI_R01_IO_DIAGNOSTIC")
    print("file_behavior=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("state_injection=NONE")
    print("sim_injection=NONE")

if __name__=="__main__":
    main()
