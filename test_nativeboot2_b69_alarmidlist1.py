#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B69 ALARMIDLIST1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B69-ALARMIDLIST1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b69_alarmidlist1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=(up/"src/emu/services/include/services/alarm/alarm.h").read_text(encoding="utf-8")
    cpp=(up/"src/emu/services/src/alarm/alarm.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")
    proc=(up/"src/emu/kernel/src/process.cpp").read_text(encoding="utf-8")
    sa=(up/"src/emu/services/src/sms/sa/sa.cpp").read_text(encoding="utf-8")

    need(hdr,"alarm_get_alarm_id_list_for_category = 9","alarm enum")
    need(hdr,"alarm_get_alarm_id_list_by_state = 11","alarm enum")
    need(hdr,"alarm_get_alarm_id_list = 12","alarm enum")
    need(hdr,"void stream_alarm_id_list(service::ipc_context *ctx);","alarm API")

    need(cpp,"case alarm_get_alarm_id_list_for_category:","alarm dispatch")
    need(cpp,"case alarm_get_alarm_id_list_by_state:","alarm dispatch")
    need(cpp,"case alarm_get_alarm_id_list:","alarm dispatch")
    need(cpp,"stream_alarm_id_list(ctx);","alarm dispatch")
    need(cpp,"void alarm_session::stream_alarm_id_list","alarm serializer")
    need(cpp,"populate_alarm_ids(seri, alarm_ids);","alarm serializer")
    need(cpp,"write_data_to_descriptor_argument<std::uint32_t>(1","alarm serializer")
    need(cpp,"ctx->complete(epoc::error_none);","alarm completion")
    need(cpp,"[NBOOT2][ALARM_ID_LIST]","B69 marker")
    need(cpp,"behavior=UPSTREAM_BACKPORT_127823A","B69 marker")

    # B68/B64 chain stays intact.
    need(svc,"[NBOOT2][STARTER_WAIT_ANY]","B68")
    need(proc,"[NBOOT2][STARTER_WAKE]","B68")
    need(sa,"[NBOOT2][SA_SELFTEST_RESPONSE]","B64")

    combined=hdr+"\n"+cpp
    for forbidden in (
        "requested=102",
        "set_int(0x101F8766",
        "signal_request(2",
        "signal_request(0",
        "EExecuteSelftests",
    ):
        if forbidden in combined:
            fail("functional scope violation: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("upstream_commit=127823a47b76c7edd50ef8e0b52ddb9b71a18782")
    print("opcode_12=IMPLEMENTED")
    print("completion=KErrNone")
    print("state_injection=NONE")

if __name__=="__main__":
    main()
