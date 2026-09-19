#!/usr/bin/env python3
"""MENUUI32 PENINPUTQUEUE1: diagnostic trace for Nokia PenInput raw RMsgQueue.

V31 device evidence:
- Nokia stock FEP/VKB activates successfully.
- PenInputAnim receives the first key down/up.
- MENUUI31 mirrors both to raweventbufqueue and consumes normal WS delivery.
- Guest then becomes silent until host exit.

This patch makes NO behavioral changes. It traces the existing kernel
msg_queue path only for the global queue named "raweventbufqueue":
  send_enter / send_return
  notify_enter / notify_return
  receive_enter / receive_return

The pre-existing V17 publish-before-notify semantic fix must remain present.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI32 PENINPUTQUEUE1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def function_span(text: str, signature: str):
    start=text.find(signature)
    if start < 0:
        fail(f"signature missing: {signature}")
    brace=text.find("{", start)
    if brace < 0:
        fail(f"opening brace missing: {signature}")
    depth=0
    for i in range(brace, len(text)):
        if text[i]=="{":
            depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0:
                return start, i+1, brace
    fail(f"unterminated function: {signature}")

def inject_function(text: str, signature: str, kind: str) -> str:
    start,end,brace=function_span(text,signature)
    fn=text[start:end]
    if f"MENUUI32 PENINPUT_QUEUE: op={kind}" in fn:
        return text

    if kind=="send":
        pro='''{
        const bool menuui32_peninput_raw = (name() == "raweventbufqueue");
        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=send stage=enter bytes={} queued={} avail_waiters={}",
                buffer_size, msgs_.size(), avail_notifies_.size());
        }
'''
        # replace only the function's opening brace
        rel=brace-start
        fn=fn[:rel]+pro+fn[rel+1:]
        # report every successful return by replacing the final return true
        pos=fn.rfind("        return true;")
        if pos < 0:
            fail("send final return true missing")
        report='''        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=send stage=return result=1 queued={} avail_waiters={}",
                msgs_.size(), avail_notifies_.size());
        }
        return true;'''
        fn=fn[:pos]+report+fn[pos+len("        return true;"):]

    elif kind=="notify":
        pro='''{
        const bool menuui32_peninput_raw = (name() == "raweventbufqueue");
        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=notify stage=enter queued={} avail_waiters={}",
                msgs_.size(), avail_notifies_.size());
        }
'''
        rel=brace-start
        fn=fn[:rel]+pro+fn[rel+1:]
        # add a diagnostic before each return true/false. This intentionally
        # does not alter the expression or notification semantics.
        fn=fn.replace(
'''            info.complete(0);
            return true;''',
'''            info.complete(0);
            if (menuui32_peninput_raw) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=notify stage=return result=1 path=immediate queued={} avail_waiters={}",
                    msgs_.size(), avail_notifies_.size());
            }
            return true;''',1)
        fn=fn.replace(
'''            avail_notifies_.push_back(info);
            return true;''',
'''            avail_notifies_.push_back(info);
            if (menuui32_peninput_raw) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=notify stage=return result=1 path=armed queued={} avail_waiters={}",
                    msgs_.size(), avail_notifies_.size());
            }
            return true;''',1)
        pos=fn.rfind("        return false;")
        if pos < 0:
            fail("notify final return false missing")
        report='''        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=notify stage=return result=0 path=duplicate queued={} avail_waiters={}",
                msgs_.size(), avail_notifies_.size());
        }
        return false;'''
        fn=fn[:pos]+report+fn[pos+len("        return false;"):]

    elif kind=="receive":
        pro='''{
        const bool menuui32_peninput_raw = (name() == "raweventbufqueue");
        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=receive stage=enter bytes={} queued={} free_waiters={}",
                buffer_size, msgs_.size(), free_notifies_.size());
        }
'''
        rel=brace-start
        fn=fn[:rel]+pro+fn[rel+1:]
        # Distinguish empty underflow from success.
        fn=fn.replace(
'''        if (msgs_.empty()) {
            return false;
        }''',
'''        if (msgs_.empty()) {
            if (menuui32_peninput_raw) {
                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=receive stage=return result=0 path=empty queued=0");
            }
            return false;
        }''',1)
        pos=fn.rfind("        return true;")
        if pos < 0:
            fail("receive final return true missing")
        report='''        if (menuui32_peninput_raw) {
            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE: op=receive stage=return result=1 queued={} free_waiters={}",
                msgs_.size(), free_notifies_.size());
        }
        return true;'''
        fn=fn[:pos]+report+fn[pos+len("        return true;"):]

    else:
        fail(f"unknown kind {kind}")

    return text[:start]+fn+text[end:]

def main() -> None:
    if len(sys.argv)!=2:
        fail("usage: apply_menuui32_peninputqueue1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    mq=up/"src/emu/kernel/src/msgqueue.cpp"
    anim=up/"src/emu/services/src/window/classes/plugins/animdll.cpp"
    win=up/"src/emu/services/src/window/window.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (mq,anim,win,svc):
        if not p.is_file():
            fail(f"missing baseline file {p}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    m= mq.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI32 PENINPUT_QUEUE:" in m:
        print("MENUUI32 already present")
        return

    if "V17 MSGQ ORDER: data queued before availability notification" not in m:
        fail("V17 publish-before-notify baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW:" not in win.read_text(encoding="utf-8"):
        fail("MENUUI31 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:" not in anim.read_text(encoding="utf-8"):
        fail("MENUUI28 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI29 baseline missing")

    m=inject_function(m,
        "bool msg_queue::send(const void *target_data, const std::uint32_t buffer_size)",
        "send")
    m=inject_function(m,
        "bool msg_queue::notify_available(epoc::notify_info &info)",
        "notify")
    m=inject_function(m,
        "bool msg_queue::receive(void *target_buffer, const std::uint32_t buffer_size)",
        "receive")
    mq.write_text(m,encoding="utf-8")

    final=mq.read_text(encoding="utf-8")
    for gate in (
        "MENUUI32 PENINPUT_QUEUE: op=send stage=enter",
        "MENUUI32 PENINPUT_QUEUE: op=send stage=return",
        "MENUUI32 PENINPUT_QUEUE: op=notify stage=enter",
        "path=immediate",
        "MENUUI32 PENINPUT_QUEUE: op=receive stage=enter",
        "MENUUI32 PENINPUT_QUEUE: op=receive stage=return",
        "V17 MSGQ ORDER: data queued before availability notification",
    ):
        if gate not in final:
            fail(f"gate missing: {gate}")

    print("MENUUI32 PENINPUTQUEUE1 applied")
    print("behavior_change=NONE")
    print("raweventbufqueue_send_notify_receive=TRACED")
    print("V17_publish_before_notify=PRESERVED")
    print("MENUUI31/MENUUI30/MENUUI29/MENUUI28/prior=PRESERVED")

if __name__=="__main__":
    main()
