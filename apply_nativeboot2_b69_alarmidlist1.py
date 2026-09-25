#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B69 ALARMIDLIST1 after B68.

B68 DEVICE1 proves:
- final profilesettingsmonitor rendezvous completes normally;
- StarterServer is signalled and rescheduled correctly;
- guest execution resumes;
- immediately before the durable post-RID6 wait, !AlarmServer receives
  opcode 0x0C and the B28 baseline logs it as unimplemented.

Upstream EKA2L1 commit 127823a47b76c7edd50ef8e0b52ddb9b71a18782
("alarm: Answer all three alarm id list requests", 2026-08-20) identifies
Symbian opcode 12 as EASShdOpCodeGetAlarmIdList and implements it by sharing
the existing alarm-id list streaming path with opcodes 9 and 11.

B69 is a narrow functional backport of that upstream fix plus one diagnostic
marker. It does not alter Starter state, scheduler, rendezvous, SAServer, P&S,
graphics, or teardown behavior.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B69-ALARMIDLIST1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b69_alarmidlist1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    hdr=up/"src/emu/services/include/services/alarm/alarm.h"
    cpp=up/"src/emu/services/src/alarm/alarm.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    proc=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"

    for p in (hdr,cpp,svc,proc,sa):
        if not p.is_file():
            fail(f"missing source: {p}")

    h=hdr.read_text(encoding="utf-8")
    c=cpp.read_text(encoding="utf-8")

    if "[NBOOT2][ALARM_ID_LIST]" in c:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("[NBOOT2][STARTER_WAIT_ANY]",svc.read_text(encoding="utf-8"),"B68"),
        ("[NBOOT2][STARTER_WAKE]",proc.read_text(encoding="utf-8"),"B68 rendezvous"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sa.read_text(encoding="utf-8"),"B64"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # Exact upstream enum expansion from 127823a...
    old='''    enum alarm_opcode {
        alarm_get_alarm_id_list_by_state = 11,
        alarm_notify_change = 19,
'''
    new='''    enum alarm_opcode {
        alarm_get_alarm_id_list_for_category = 9,
        alarm_get_alarm_id_list_by_state = 11,
        alarm_get_alarm_id_list = 12,
        alarm_notify_change = 19,
'''
    h=rep1(h,old,new,"alarm opcode enum")

    old='''        void get_alarm_id_list_by_state(service::ipc_context *ctx);
'''
    new='''        void stream_alarm_id_list(service::ipc_context *ctx);
'''
    h=rep1(h,old,new,"alarm list method declaration")

    # Exact upstream dispatch widening: 9,11,12 share the same empty-list
    # serialization path.
    old='''        switch (ctx->msg->function) {
        case alarm_get_alarm_id_list_by_state:
            get_alarm_id_list_by_state(ctx);
            break;
'''
    new='''        switch (ctx->msg->function) {
        // B69: exact functional backport of upstream EKA2L1 127823a...
        // Symbian opcodes 9, 11 and 12 are alarm-id list requests. EKA2L1's
        // emulated alarm queue is empty here, so the same serializer is valid
        // for all three and, critically, completes the synchronous request.
        case alarm_get_alarm_id_list_for_category:
        case alarm_get_alarm_id_list_by_state:
        case alarm_get_alarm_id_list:
            stream_alarm_id_list(ctx);
            break;
'''
    c=rep1(c,old,new,"alarm list dispatch")

    old='''    void alarm_session::get_alarm_id_list_by_state(service::ipc_context *ctx) {
        auto state = ctx->get_argument_value<std::uint32_t>(0);

        common::chunkyseri seri(nullptr, 0, common::chunkyseri_mode::SERI_MODE_MEASURE);
'''
    new='''    void alarm_session::stream_alarm_id_list(service::ipc_context *ctx) {
        common::chunkyseri seri(nullptr, 0, common::chunkyseri_mode::SERI_MODE_MEASURE);
'''
    c=rep1(c,old,new,"alarm list serializer rename")

    # Add a device-visible acceptance marker immediately before the normal
    # KErrNone completion. No ABI or completion value is changed.
    old='''        ctx->write_data_to_descriptor_argument<std::uint32_t>(1, static_cast<std::uint32_t>(transfer_buf.size()));
        ctx->complete(epoc::error_none);
    }

    void alarm_session::fetch_transfer_buffer'''
    new='''        ctx->write_data_to_descriptor_argument<std::uint32_t>(1, static_cast<std::uint32_t>(transfer_buf.size()));

        kernel::thread *nboot2_b69_thr = ctx->msg ? ctx->msg->own_thr : nullptr;
        kernel::process *nboot2_b69_pr =
            nboot2_b69_thr ? nboot2_b69_thr->owning_process() : nullptr;
        LOG_WARN(SERVICE_ALARM,
            "[NBOOT2][ALARM_ID_LIST] opcode=0x{:X} alarm_count={} "
            "transfer_bytes={} request_status=0x{:08X} client_process={} "
            "client_thread={} completion=KErrNone "
            "behavior=UPSTREAM_BACKPORT_127823A",
            ctx->msg ? ctx->msg->function : -1,
            alarm_ids.size(), transfer_buf.size(),
            ctx->msg ? ctx->msg->request_sts.ptr_address() : 0,
            nboot2_b69_pr ? nboot2_b69_pr->name() : "<none>",
            nboot2_b69_thr ? nboot2_b69_thr->name() : "<none>");

        ctx->complete(epoc::error_none);
    }

    void alarm_session::fetch_transfer_buffer'''
    c=rep1(c,old,new,"B69 alarm list acceptance marker")

    combined=h+"\n"+c
    for need in (
        "alarm_get_alarm_id_list_for_category = 9",
        "alarm_get_alarm_id_list = 12",
        "case alarm_get_alarm_id_list:",
        "stream_alarm_id_list(ctx);",
        "[NBOOT2][ALARM_ID_LIST]",
        "UPSTREAM_BACKPORT_127823A",
        "ctx->complete(epoc::error_none);",
    ):
        if need not in combined:
            fail("post-apply semantic missing: "+need)

    for forbidden in (
        "requested=102",
        "set_int(0x101F8766",
        "signal_request(2",
        "signal_request(0",
        "EExecuteSelftests",
    ):
        if forbidden in combined:
            fail("B69 scope violation: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    hdr.write_text(h,encoding="utf-8")
    cpp.write_text(c,encoding="utf-8")

    print(MARK+": applied")
    print("upstream_commit=127823a47b76c7edd50ef8e0b52ddb9b71a18782")
    print("symbian_opcode_12=EASShdOpCodeGetAlarmIdList")
    print("completion=KErrNone")
    print("state_injection=NONE")
    print("scheduler_change=NONE")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
