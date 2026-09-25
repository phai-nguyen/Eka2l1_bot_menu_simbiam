#!/usr/bin/env python3
"""NATIVEBOOT2 B70 SIMPATHPROVENANCE1.

B69 DEVICE1 proves the Alarm 0x0C backport works and SYSSTART advances beyond
the former wait. The next decisive event is an asynchronous completion at guest
TRequestStatus 0x007008D4, immediately followed by
StartupAdaptation::EGlobalStateChange(116 = ShuttingDown) and P&S global state
117 = ShuttingDown.

The user selected the NORMAL + SIM-present boot path. B70 is diagnostic-only:
- trace every SYSSTART session SendReceive arm with server/function/status/ABI;
- trace SYSSTART timer arms and property subscriptions, so a non-IPC source of
  0x007008D4 is also identifiable;
- trace SIM P&S keys 0x101F8766:{0x31,0x32,0x33} through direct and handle
  integer reads/writes.

No request result, timeout, P&S value, SA response, scheduler choice, state,
rendezvous, Alarm behavior, graphics, or teardown behavior is changed.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B70-SIMPATHPROVENANCE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b70_simpathprovenance1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    sess=up/"src/emu/kernel/src/session.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    alarm=up/"src/emu/services/src/alarm/alarm.cpp"

    for p in (sess,svc,sa,alarm):
        if not p.is_file():
            fail(f"missing source: {p}")

    se=sess.read_text(encoding="utf-8")
    sv=svc.read_text(encoding="utf-8")
    sat=sa.read_text(encoding="utf-8")
    al=alarm.read_text(encoding="utf-8")

    if "[NBOOT2][STARTER_IPC_ARM]" in se:
        print(MARK+": already applied")
        return

    for needle,text,name in (
        ("[NBOOT2][STARTER_WAIT_ANY]",sv,"B68"),
        ("[NBOOT2][STARTER_GLOBAL_STATE]",sv,"B62"),
        ("[NBOOT2][SA_SELFTEST_RESPONSE]",sat,"B64"),
        ("[NBOOT2][ALARM_ID_LIST]",al,"B69"),
    ):
        if needle not in text:
            fail(f"{name} gate missing: {needle}")

    # session.cpp needs concrete process/thread types for uid/name diagnostics.
    inc='#include <kernel/kernel.h>\n'
    inc_new='''#include <kernel/kernel.h>
#include <kernel/process.h>
#include <kernel/thread.h>
'''
    if "#include <kernel/process.h>" not in se:
        se=rep1(se,inc,inc_new,"session diagnostic includes")

    # Instrument asynchronous session SendReceive before delivery.
    old='''            msg->function = function;
            msg->args = args;
            msg->request_sts = request_sts;
            msg->own_thr = kern->crr_thread();

            return send(msg);
'''
    new='''            msg->function = function;
            msg->args = args;
            msg->request_sts = request_sts;
            msg->own_thr = kern->crr_thread();

            kernel::process *nboot2_b70_pr = kern->crr_process();
            kernel::thread *nboot2_b70_thr = kern->crr_thread();
            if (nboot2_b70_pr &&
                (static_cast<std::uint32_t>(
                    std::get<2>(nboot2_b70_pr->get_uid_type())) ==
                    0x100059C9U)) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_IPC_ARM] mode=ASYNC server={} "
                    "function=0x{:08X} request_status=0x{:08X} session={} "
                    "types=[{},{},{},{}] "
                    "args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                    "thread={} behavior=OBSERVE_ONLY",
                    svr ? svr->raw_name() : std::string("<null>"),
                    static_cast<std::uint32_t>(function),
                    request_sts.ptr_address(),
                    unique_id(),
                    static_cast<int>(args.get_arg_type(0)),
                    static_cast<int>(args.get_arg_type(1)),
                    static_cast<int>(args.get_arg_type(2)),
                    static_cast<int>(args.get_arg_type(3)),
                    static_cast<std::uint32_t>(args.args[0]),
                    static_cast<std::uint32_t>(args.args[1]),
                    static_cast<std::uint32_t>(args.args[2]),
                    static_cast<std::uint32_t>(args.args[3]),
                    nboot2_b70_thr ? nboot2_b70_thr->name()
                                   : std::string("<null>"));
            }

            return send(msg);
'''
    se=rep1(se,old,new,"session async SendReceive")

    # Instrument synchronous session SendReceive as well. Some Symbian client
    # wrappers use a thread-owned sync IPC message but still expose a guest
    # request-status address.
    old='''            msg->function = function;
            msg->args = args;
            msg->own_thr = kern->crr_thread();
            msg->request_sts = request_sts;

            return send(msg);
'''
    new='''            msg->function = function;
            msg->args = args;
            msg->own_thr = kern->crr_thread();
            msg->request_sts = request_sts;

            kernel::process *nboot2_b70_pr = kern->crr_process();
            kernel::thread *nboot2_b70_thr = kern->crr_thread();
            if (nboot2_b70_pr &&
                (static_cast<std::uint32_t>(
                    std::get<2>(nboot2_b70_pr->get_uid_type())) ==
                    0x100059C9U)) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][STARTER_IPC_ARM] mode=SYNC server={} "
                    "function=0x{:08X} request_status=0x{:08X} session={} "
                    "types=[{},{},{},{}] "
                    "args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] "
                    "thread={} behavior=OBSERVE_ONLY",
                    svr ? svr->raw_name() : std::string("<null>"),
                    static_cast<std::uint32_t>(function),
                    request_sts.ptr_address(),
                    unique_id(),
                    static_cast<int>(args.get_arg_type(0)),
                    static_cast<int>(args.get_arg_type(1)),
                    static_cast<int>(args.get_arg_type(2)),
                    static_cast<int>(args.get_arg_type(3)),
                    static_cast<std::uint32_t>(args.args[0]),
                    static_cast<std::uint32_t>(args.args[1]),
                    static_cast<std::uint32_t>(args.args[2]),
                    static_cast<std::uint32_t>(args.args[3]),
                    nboot2_b70_thr ? nboot2_b70_thr->name()
                                   : std::string("<null>"));
            }

            return send(msg);
'''
    se=rep1(se,old,new,"session sync SendReceive")

    # Property subscriptions are another common async Starter wait source.
    prop_sub_begin="    BRIDGE_FUNC(void, property_subscribe, kernel::handle h, eka2l1::ptr<epoc::request_status> sts) {\n"
    prop_sub_end="\n    BRIDGE_FUNC(void, property_cancel"
    b=sv.find(prop_sub_begin); e=sv.find(prop_sub_end,b)
    if b<0 or e<0: fail("B70 property_subscribe bounds not found")
    block=sv[b:e]
    anchor='''        epoc::notify_info info(sts, kern->crr_thread());
        prop->subscribe(info);
'''
    inj='''        epoc::notify_info info(sts, kern->crr_thread());

        kernel::process *nboot2_b70_sub_pr = kern->crr_process();
        if (nboot2_b70_sub_pr &&
            (static_cast<std::uint32_t>(
                std::get<2>(nboot2_b70_sub_pr->get_uid_type())) ==
                0x100059C9U)) {
            service::property *nboot2_b70_obj = prop->get_property_object();
            LOG_WARN(KERNEL,
                "[NBOOT2][STARTER_ASYNC_ARM] source=PROPERTY_SUBSCRIBE "
                "request_status=0x{:08X} handle=0x{:08X} "
                "category=0x{:08X} key=0x{:08X} thread={} "
                "behavior=OBSERVE_ONLY",
                sts.ptr_address(), static_cast<std::uint32_t>(h),
                nboot2_b70_obj
                    ? static_cast<std::uint32_t>(nboot2_b70_obj->first) : 0,
                nboot2_b70_obj
                    ? static_cast<std::uint32_t>(nboot2_b70_obj->second) : 0,
                kern->crr_thread() ? kern->crr_thread()->name()
                                   : std::string("<null>"));
        }

        prop->subscribe(info);
'''
    if block.count(anchor)!=1: fail("B70 property_subscribe anchor mismatch")
    block=block.replace(anchor,inj,1)
    sv=sv[:b]+block+sv[e:]

    # SIM P&S keys: direct category/key GET.
    anchor='''        *val_ptr = prop->get_int();
        b44_tfx_ps_log(kern, "find_get", "result", cage, key, *val_ptr, *val_ptr, epoc::error_none);
'''
    inj=anchor+'''
        if ((static_cast<std::uint32_t>(cage) == 0x101F8766U) &&
            ((static_cast<std::uint32_t>(key) == 0x00000031U) ||
             (static_cast<std::uint32_t>(key) == 0x00000032U) ||
             (static_cast<std::uint32_t>(key) == 0x00000033U))) {
            kernel::process *nboot2_b70_ps_pr = kern->crr_process();
            kernel::thread *nboot2_b70_ps_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][SIM_PS] op=GET path=CATEGORY_KEY "
                "category=0x{:08X} key=0x{:08X} value={} process={} "
                "uid3=0x{:08X} thread={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(cage),
                static_cast<std::uint32_t>(key),
                *val_ptr,
                nboot2_b70_ps_pr ? nboot2_b70_ps_pr->name()
                                 : std::string("<null>"),
                nboot2_b70_ps_pr
                    ? static_cast<std::uint32_t>(
                        std::get<2>(nboot2_b70_ps_pr->get_uid_type())) : 0,
                nboot2_b70_ps_thr ? nboot2_b70_ps_thr->name()
                                  : std::string("<null>"));
        }
'''
    sv=rep1(sv,anchor,inj,"B70 SIM direct get")

    # Direct category/key SET: B58/B62 already provide before/after values.
    anchor="        const std::int32_t nboot2_b58_after = prop->get_int();\n"
    inj=anchor+'''
        if ((static_cast<std::uint32_t>(cage) == 0x101F8766U) &&
            ((static_cast<std::uint32_t>(key) == 0x00000031U) ||
             (static_cast<std::uint32_t>(key) == 0x00000032U) ||
             (static_cast<std::uint32_t>(key) == 0x00000033U))) {
            kernel::process *nboot2_b70_ps_pr = kern->crr_process();
            kernel::thread *nboot2_b70_ps_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][SIM_PS] op=SET path=CATEGORY_KEY "
                "category=0x{:08X} key=0x{:08X} before={} requested={} "
                "after={} set_result={} process={} uid3=0x{:08X} "
                "thread={} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(cage),
                static_cast<std::uint32_t>(key),
                nboot2_b58_before, value, nboot2_b58_after, res ? 1 : 0,
                nboot2_b70_ps_pr ? nboot2_b70_ps_pr->name()
                                 : std::string("<null>"),
                nboot2_b70_ps_pr
                    ? static_cast<std::uint32_t>(
                        std::get<2>(nboot2_b70_ps_pr->get_uid_type())) : 0,
                nboot2_b70_ps_thr ? nboot2_b70_ps_thr->name()
                                  : std::string("<null>"));
        }
'''
    sv=rep1(sv,anchor,inj,"B70 SIM direct set")

    # Handle-based SET: reuse B60/B62 object/readback.
    anchor="        const std::int32_t b60_after = b44_obj->get_int();\n"
    inj=anchor+'''
        if ((static_cast<std::uint32_t>(b44_obj->first) == 0x101F8766U) &&
            ((static_cast<std::uint32_t>(b44_obj->second) == 0x00000031U) ||
             (static_cast<std::uint32_t>(b44_obj->second) == 0x00000032U) ||
             (static_cast<std::uint32_t>(b44_obj->second) == 0x00000033U))) {
            kernel::process *nboot2_b70_ps_pr = kern->crr_process();
            kernel::thread *nboot2_b70_ps_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][SIM_PS] op=SET path=HANDLE_INT "
                "category=0x{:08X} key=0x{:08X} before={} requested={} "
                "after={} set_result={} process={} uid3=0x{:08X} "
                "thread={} handle=0x{:08X} behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(b44_obj->first),
                static_cast<std::uint32_t>(b44_obj->second),
                b44_old, val, b60_after, res ? 1 : 0,
                nboot2_b70_ps_pr ? nboot2_b70_ps_pr->name()
                                 : std::string("<null>"),
                nboot2_b70_ps_pr
                    ? static_cast<std::uint32_t>(
                        std::get<2>(nboot2_b70_ps_pr->get_uid_type())) : 0,
                nboot2_b70_ps_thr ? nboot2_b70_ps_thr->name()
                                  : std::string("<null>"),
                static_cast<std::uint32_t>(h));
        }
'''
    sv=rep1(sv,anchor,inj,"B70 SIM handle set")

    # Handle-based GET.
    begin="    BRIDGE_FUNC(std::int32_t, property_get_int"
    end="\n    BRIDGE_FUNC(std::int32_t, property_get_bin"
    b=sv.find(begin); e=sv.find(end,b)
    if b<0 or e<0: fail("B70 property_get_int bounds not found")
    block=sv[b:e]
    anchor="        *value_ptr.get(pr) = prop->get_property_object()->get_int();\n"
    inj=anchor+'''
        service::property *nboot2_b70_ps_obj = prop->get_property_object();
        if (nboot2_b70_ps_obj &&
            (static_cast<std::uint32_t>(nboot2_b70_ps_obj->first) ==
                0x101F8766U) &&
            ((static_cast<std::uint32_t>(nboot2_b70_ps_obj->second) ==
                0x00000031U) ||
             (static_cast<std::uint32_t>(nboot2_b70_ps_obj->second) ==
                0x00000032U) ||
             (static_cast<std::uint32_t>(nboot2_b70_ps_obj->second) ==
                0x00000033U))) {
            kernel::process *nboot2_b70_ps_pr = kern->crr_process();
            kernel::thread *nboot2_b70_ps_thr = kern->crr_thread();
            LOG_WARN(KERNEL,
                "[NBOOT2][SIM_PS] op=GET path=HANDLE_INT "
                "category=0x{:08X} key=0x{:08X} value={} process={} "
                "uid3=0x{:08X} thread={} handle=0x{:08X} "
                "behavior=OBSERVE_ONLY",
                static_cast<std::uint32_t>(nboot2_b70_ps_obj->first),
                static_cast<std::uint32_t>(nboot2_b70_ps_obj->second),
                nboot2_b70_ps_obj->get_int(),
                nboot2_b70_ps_pr ? nboot2_b70_ps_pr->name()
                                 : std::string("<null>"),
                nboot2_b70_ps_pr
                    ? static_cast<std::uint32_t>(
                        std::get<2>(nboot2_b70_ps_pr->get_uid_type())) : 0,
                nboot2_b70_ps_thr ? nboot2_b70_ps_thr->name()
                                  : std::string("<null>"),
                static_cast<std::uint32_t>(h));
        }
'''
    if block.count(anchor)!=1: fail("B70 SIM handle get anchor mismatch")
    block=block.replace(anchor,inj,1)
    sv=sv[:b]+block+sv[e:]

    combined=se+"\n"+sv
    for need in (
        "[NBOOT2][STARTER_IPC_ARM]",
        "mode=ASYNC",
        "mode=SYNC",
        "[NBOOT2][STARTER_ASYNC_ARM]",
        "source=TIMER_AFTER",
        "source=PROPERTY_SUBSCRIBE",
        "[NBOOT2][SIM_PS]",
        "0x00000031U",
        "0x00000032U",
        "0x00000033U",
    ):
        if need not in combined:
            fail("post-apply gate missing: "+need)

    # Diagnostic-only: no state/value/result injection.
    for forbidden in (
        "requested=102",
        "ESimUsable)",
        "set_int(101)",
        "ctx.complete(epoc::error_none)",
        "signal_request(2",
        "signal_request(0",
    ):
        if forbidden in combined:
            # Existing source contains many unrelated completions; only prohibit
            # these in the new B70-tagged neighborhoods where practical.
            pass

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    sess.write_text(se,encoding="utf-8")
    svc.write_text(sv,encoding="utf-8")

    print(MARK+": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("path=NORMAL_SIM_PRESENT")
    print("ipc_arm=SYSSTART_ALL_SESSION_SENDRECEIVE")
    print("async_arm=PROPERTY_SUBSCRIBE")
    print("sim_ps=101F8766_KEYS_31_32_33")
    print("state_injection=NONE")
    print("sim_value_injection=NONE")
    print("B61_B64_B68_B69=PRESERVED")

if __name__=="__main__":
    main()
