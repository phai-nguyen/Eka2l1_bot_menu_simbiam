#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B71 PHONEUICONE14RES1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B71-PHONEUICONE14RES1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b71_phoneuicone14res1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    fs=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    se=(up/"src/emu/kernel/src/session.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")
    al=(up/"src/emu/services/src/alarm/alarm.cpp").read_text(encoding="utf-8")

    for marker in (
        "[NBOOT2][CONE14_PHONEUI]",
        "[NBOOT2][CONE14_FRAME]",
        "[NBOOT2][CONE14_STACK]",
        "[NBOOT2][CONE14_CODE16]",
        "[NBOOT2][CONE14_FP]",
        "[NBOOT2][CONE14_SUMMARY]",
    ):
        need(sv,marker,"svc.cpp")

    need(fs,"[NBOOT2][PHONEUI_RSC_DUMP]","files.cpp")
    need(fs,'u"z:\\resource\\apps\\phoneui.r01"',
         "exact PhoneUI localized resource")
    need(fs,"io->open_file(path,READ_MODE|BIN_MODE)",
         "separate read-only VFS handle")
    need(fs,"constexpr std::size_t max_capture=262144",
         "bounded resource capture")
    need(fs,"nboot2_b71_dump_phoneui_rsc(io, *name_res);",
         "EFsrv open hook")

    need(sv,"0x100058B3U","Telephone UID3 gate")
    need(sv,'(reason == 14)',"CONE14 reason gate")
    need(sv,'(exit_category == "CONE")',"CONE category gate")
    need(sv,"nboot2_b71_stack_words=128","bounded stack scan")
    need(sv,"resource_range_assumption=NONE",
         "no guessed PhoneUI resource ID range")
    need(sv,"thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
         "panic semantics")

    # The prior unverified candidate range must not remain in B71.
    b=sv.find("// B71 PHONEUICONE14RES1:")
    e=sv.find("thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",b)
    if b<0 or e<0:
        fail("cannot isolate B71 panic block")
    block=sv[b:e]
    for forbidden in (
        "0x4E738000","0x170U","phoneui_resource_count",
        "reason = 0","reason=0","requested=102","ESimUsable",
        "set_int("
    ):
        if forbidden in block:
            fail("unverified/behavior-changing token: "+forbidden)

    # Proven chain must remain present.
    need(sv,"SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:","MENUUI4")
    need(sv,"[NBOOT2][STARTER_GLOBAL_STATE]","B62")
    need(sv,"[NBOOT2][STARTER_WAIT_ANY]","B68")
    need(se,"[NBOOT2][STARTER_IPC_ARM]","B70")
    need(sv,"[NBOOT2][SIM_PS]","B70")
    need(fs,"[NBOOT2][STARTER_SSC_DUMP]","B67")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64")
    need(al,"[NBOOT2][ALARM_ID_LIST]","B69")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=TELEPHONE_CONE14_DIAGNOSTIC_ONLY")
    print("telephone_uid3=0x100058B3")
    print("cone14=ECoePanicNoResourceFileForId")
    print("resource_range_assumption=NONE")
    print("stack_scan=128_WORDS")
    print("phoneui_r01=READ_ONLY_HEX_CAPTURE")
    print("panic_behavior=UNCHANGED")
    print("state_injection=NONE")
    print("sim_injection=NONE")

if __name__=="__main__":
    main()
