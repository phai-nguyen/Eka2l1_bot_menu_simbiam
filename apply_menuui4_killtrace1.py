#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui4_killtrace1.py <upstream-root>")

up = Path(sys.argv[1])
path = up / "src/emu/kernel/src/svc.cpp"
text = path.read_text(encoding="utf-8")

sig = "    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h, kernel::entity_exit_type etype, std::int32_t reason, eka2l1::ptr<desc8> reason_des) {"
start = text.find(sig)
if start < 0:
    raise SystemExit("MENUUI4: thread_kill signature not found")
end = text.find("\n    BRIDGE_FUNC(", start + len(sig))
if end < 0:
    raise SystemExit("MENUUI4: thread_kill end anchor not found")
body = text[start:end]

marker = "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:"
if marker in body:
    print("MENUUI4 KILLTRACE1 already present")
    raise SystemExit(0)

required = [
    "thread_ptr thr = kern->get<kernel::thread>(h);",
    "std::string exit_category = \"None\";",
    "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
]
missing = [item for item in required if item not in body]
if missing:
    raise SystemExit("MENUUI4: unexpected pre-patch thread_kill body: " + ", ".join(missing))

anchor = "        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"
if body.count(anchor) != 1:
    raise SystemExit(f"MENUUI4: expected one thread_kill dispatch anchor, found {body.count(anchor)}")

inject = '''        kernel::thread *caller_thr = kern->crr_thread();
        kernel::process *caller_pr = kern->crr_process();
        kernel::process *target_pr = thr->owning_process();
        auto *cpu = kern->get_cpu();

        LOG_WARN(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL: caller_process={} caller_thread={} target_process={} target_thread={} handle=0x{:X} exit_type={} reason={} category={} pc=0x{:08X} lr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X}",
            caller_pr ? caller_pr->name() : "<null>",
            caller_thr ? caller_thr->name() : "<null>",
            target_pr ? target_pr->name() : "<null>",
            thr->name(), h, static_cast<std::int32_t>(etype), reason, exit_category,
            cpu ? cpu->get_pc() : 0,
            cpu ? cpu->get_reg(14) : 0,
            cpu ? cpu->get_reg(0) : 0,
            cpu ? cpu->get_reg(1) : 0,
            cpu ? cpu->get_reg(2) : 0,
            cpu ? cpu->get_reg(3) : 0);

'''

new_body = body.replace(anchor, inject + anchor, 1)
text = text[:start] + new_body + text[end:]
path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
if marker not in check:
    raise SystemExit("MENUUI4: marker verification failed")
if check.count(marker) != 1:
    raise SystemExit(f"MENUUI4: expected one marker after patch, found {check.count(marker)}")
print("MENUUI4 KILLTRACE1 patch applied")
