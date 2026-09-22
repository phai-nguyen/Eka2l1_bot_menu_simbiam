#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B33 EIKCANCELORIGIN1 after B32.

B32 device evidence proves the first repeated guest failure is:
AknFep stack -> User::Leave(KErrCancel) -> euser null write -> KERN-EXEC 3.

B33 is diagnostic-only. It traces every KErrCancel completion through:
- native/LLE RMessage completion;
- HLE ipc_context completion;
- generic notify_info completion.

No result value, signal count, message lifetime, leave behavior, SVC table,
FEP selection, or exception behavior is changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="NATIVEBOOT2-B33-EIKCANCELORIGIN1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b33_eikcancelorigin1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    svc=up/"src/emu/kernel/src/svc.cpp"
    ctx=up/"src/emu/services/src/context.cpp"
    thr=up/"src/emu/kernel/src/thread.cpp"
    lib=up/"src/emu/kernel/src/libmanager.cpp"
    kern=up/"src/emu/kernel/src/kernel.cpp"
    sched=up/"src/emu/kernel/src/scheduler.cpp"

    for p in (svc,ctx,thr,lib,kern,sched):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    sv=svc.read_text(encoding="utf-8")
    cx=ctx.read_text(encoding="utf-8")
    th=thr.read_text(encoding="utf-8")
    lm=lib.read_text(encoding="utf-8")
    ke=kern.read_text(encoding="utf-8")
    sc=sched.read_text(encoding="utf-8")

    for needle,text,name in (
        ("[NBOOT2][LDR_ROOT_RESOLVED]",lm,"B30"),
        ("[NBOOT2][SCHED_STALE_READY_DROP]",sc,"B31"),
        ("[NBOOT2][EIKFAULT_SVCMISS]",lm,"B32 SVC"),
        ("[NBOOT2][EIKFAULT_LEAVE]",sv,"B32 leave"),
        ("[NBOOT2][EIKFAULT_AV]",ke,"B32 AV"),
    ):
        if needle not in text:
            fail(f"{name} checkpoint missing: {needle}")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    markers=(
        "[NBOOT2][EIKCANCEL_LLE]",
        "[NBOOT2][EIKCANCEL_HLE]",
        "[NBOOT2][EIKCANCEL_NOTIFY]",
    )
    combined=sv+"\n"+cx+"\n"+th
    present=[m for m in markers if m in combined]
    if present:
        if len(present)==len(markers):
            print(f"{MARK}: already applied")
            return
        fail("partial B33 markers present: "+", ".join(present))

    # 1) Native/LLE message completion. Log immediately after resolving the
    # message object and before any request-status write/signal/callback/unref.
    lle_anchor='''    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {
        ipc_msg_ptr msg = kern->get_msg(msg_handle);

'''
    lle_new='''    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {
        ipc_msg_ptr msg = kern->get_msg(msg_handle);

        // B33 EIKCANCELORIGIN1: diagnostic-only completion provenance.
        if ((val == epoc::error_cancel) && msg && msg->own_thr) {
            kernel::thread *nboot2_b33_client_thr = msg->own_thr;
            kernel::process *nboot2_b33_client_pr = nboot2_b33_client_thr->owning_process();
            std::string nboot2_b33_server_name = "<no-session>";
            if (msg->msg_session && !msg->msg_session->is_server_terminated()
                && msg->msg_session->get_server()) {
                nboot2_b33_server_name = msg->msg_session->get_server()->name();
            }

            kernel::thread *nboot2_b33_current_thr = kern->crr_thread();
            kernel::process *nboot2_b33_current_pr = kern->crr_process();

            LOG_WARN(KERNEL,
                "[NBOOT2][EIKCANCEL_LLE] result={} msg_handle={} msg_id={} server={} opcode={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} request_status=0x{:08X} client_process={} client_thread={} current_process={} current_thread={}",
                val, msg_handle, msg->id, nboot2_b33_server_name, msg->function,
                static_cast<std::uint32_t>(msg->args.flag),
                static_cast<std::uint32_t>(msg->args.args[0]),
                static_cast<std::uint32_t>(msg->args.args[1]),
                static_cast<std::uint32_t>(msg->args.args[2]),
                static_cast<std::uint32_t>(msg->args.args[3]),
                msg->request_sts.ptr_address(),
                nboot2_b33_client_pr ? nboot2_b33_client_pr->name() : "<none>",
                nboot2_b33_client_thr->name(),
                nboot2_b33_current_pr ? nboot2_b33_current_pr->name() : "<none>",
                nboot2_b33_current_thr ? nboot2_b33_current_thr->name() : "<none>");
        }

'''
    sv=replace_once(sv,lle_anchor,lle_new,"LLE completion diagnostics")

    # 2) HLE ipc_context completion. Do not alter the existing request-status
    # write or its one-shot signal guard.
    hle_anchor='''        void ipc_context::complete(int res) {
            if (msg->request_sts) {
'''
    hle_new='''        void ipc_context::complete(int res) {
            // B33 EIKCANCELORIGIN1: diagnostic-only HLE completion provenance.
            if ((res == epoc::error_cancel) && msg && msg->own_thr) {
                kernel::thread *nboot2_b33_client_thr = msg->own_thr;
                kernel::process *nboot2_b33_client_pr = nboot2_b33_client_thr->owning_process();
                std::string nboot2_b33_server_name = "<no-session>";
                if (msg->msg_session && !msg->msg_session->is_server_terminated()
                    && msg->msg_session->get_server()) {
                    nboot2_b33_server_name = msg->msg_session->get_server()->name();
                }

                kernel_system *nboot2_b33_kern = sys->get_kernel_system();
                kernel::thread *nboot2_b33_current_thr =
                    nboot2_b33_kern ? nboot2_b33_kern->crr_thread() : nullptr;
                kernel::process *nboot2_b33_current_pr =
                    nboot2_b33_kern ? nboot2_b33_kern->crr_process() : nullptr;

                LOG_WARN(SERVICE_TRACK,
                    "[NBOOT2][EIKCANCEL_HLE] result={} msg_id={} server={} opcode={} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} request_status=0x{:08X} client_process={} client_thread={} current_process={} current_thread={}",
                    res, msg->id, nboot2_b33_server_name, msg->function,
                    static_cast<std::uint32_t>(msg->args.flag),
                    static_cast<std::uint32_t>(msg->args.args[0]),
                    static_cast<std::uint32_t>(msg->args.args[1]),
                    static_cast<std::uint32_t>(msg->args.args[2]),
                    static_cast<std::uint32_t>(msg->args.args[3]),
                    msg->request_sts.ptr_address(),
                    nboot2_b33_client_pr ? nboot2_b33_client_pr->name() : "<none>",
                    nboot2_b33_client_thr->name(),
                    nboot2_b33_current_pr ? nboot2_b33_current_pr->name() : "<none>",
                    nboot2_b33_current_thr ? nboot2_b33_current_thr->name() : "<none>");
            }

            if (msg->request_sts) {
'''
    cx=replace_once(cx,hle_anchor,hle_new,"HLE completion diagnostics")
    if "#include <common/log.h>" not in cx:
        include_anchor="#include <kernel/kernel.h>\n"
        if include_anchor not in cx:
            fail("context.cpp include anchor missing")
        cx=cx.replace(include_anchor,"#include <common/log.h>\n"+include_anchor,1)

    # 3) Generic notify_info completion. Log requester/status before the
    # original status write, sts reset, and request signal.
    notify_anchor='''        void notify_info::complete(int err_code) {
            if (sts.ptr_address() == 0) {
                return;
            }

            kernel_system *kern = requester->get_kernel_object_owner();

'''
    notify_new='''        void notify_info::complete(int err_code) {
            if (sts.ptr_address() == 0) {
                return;
            }

            kernel_system *kern = requester->get_kernel_object_owner();

            // B33 EIKCANCELORIGIN1: diagnostic-only generic notify provenance.
            if ((err_code == epoc::error_cancel) && requester) {
                kernel::process *nboot2_b33_pr = requester->owning_process();
                LOG_WARN(KERNEL,
                    "[NBOOT2][EIKCANCEL_NOTIFY] result={} request_status=0x{:08X} requester_process={} requester_thread={}",
                    err_code, sts.ptr_address(),
                    nboot2_b33_pr ? nboot2_b33_pr->name() : "<none>",
                    requester->name());
            }

'''
    th=replace_once(th,notify_anchor,notify_new,"notify completion diagnostics")

    # Scope gates: no target-specific process/DLL hardcode.
    patched=(sv+"\n"+cx+"\n"+th).lower()
    for forbidden in ("eiksrvs","10003a4a","avkonfep.dll","100056de"):
        if forbidden in patched:
            fail(f"target hardcode detected: {forbidden}")

    # Do not convert the observed executives into B33 behavior.
    v94_start=sv.find("const eka2l1::hle::func_map svc_register_funcs_v94")
    v94_end=sv.find("const eka2l1::hle::func_map svc_register_funcs_v93",v94_start)
    if v94_start < 0 or v94_end < 0:
        fail("cannot isolate EPOC94 SVC table")
    v94=sv[v94_start:v94_end]
    if "BRIDGE_REGISTER(0x2D," in v94:
        fail("out-of-scope EPOC94 SVC 0x2D implementation detected")
    if "get_module_name_from_address" in sv:
        fail("out-of-scope GetModuleNameFromAddress backport detected")

    svc.write_text(sv,encoding="utf-8")
    ctx.write_text(cx,encoding="utf-8")
    thr.write_text(th,encoding="utf-8")

    final=sv+"\n"+cx+"\n"+th
    for marker in markers:
        if marker not in final:
            fail(f"post-apply marker missing: {marker}")

    # Existing semantics must still be present byte-for-byte.
    for needle in (
        "status->set(val, kern->is_eka1());",
        "msg->own_thr->signal_request();",
        "kern->call_ipc_complete_callbacks(msg, val);",
        "msg->unref();",
    ):
        if needle not in sv:
            fail(f"LLE behavior lost: {needle}")

    for needle in (
        "(msg->request_sts.get(msg->own_thr->owning_process()))->set(res, kern->is_eka1());",
        "msg->own_thr->signal_request();",
    ):
        if needle not in cx:
            fail(f"HLE behavior lost: {needle}")

    for needle in (
        "sts_real->set(err_code, kern->is_eka1());",
        "sts = 0;",
        "requester->signal_request();",
    ):
        if needle not in th:
            fail(f"notify behavior lost: {needle}")

    print(f"{MARK}: applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("completion_values=UNCHANGED")
    print("request_signals=UNCHANGED")
    print("message_lifetimes=UNCHANGED")
    print("leave_behavior=UNCHANGED")
    print("fep_behavior=UNCHANGED")
    print("svc_0x2D=UNCHANGED")
    print("svc_0xE3=UNCHANGED")
    print("B30_B31_B32=PRESERVED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
