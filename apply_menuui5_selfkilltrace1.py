#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui5_selfkilltrace1.py <upstream-root>")

up = Path(sys.argv[1])
path = up / "src/emu/kernel/src/svc.cpp"
text = path.read_text(encoding="utf-8")

sig = "    BRIDGE_FUNC(std::int32_t, thread_kill, kernel::handle h, kernel::entity_exit_type etype, std::int32_t reason, eka2l1::ptr<desc8> reason_des) {"
start = text.find(sig)
if start < 0:
    raise SystemExit("MENUUI5: thread_kill signature not found")
end = text.find("\n    BRIDGE_FUNC(", start + len(sig))
if end < 0:
    raise SystemExit("MENUUI5: thread_kill end anchor not found")
body = text[start:end]

marker = "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:"
if marker in body:
    print("MENUUI5 SELFKILLTRACE1 already present")
    raise SystemExit(0)

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
    "kernel::thread *caller_thr = kern->crr_thread();",
    "kernel::process *caller_pr = kern->crr_process();",
    "kernel::process *target_pr = thr->owning_process();",
    "auto *cpu = kern->get_cpu();",
    "thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);",
]
missing = [item for item in required if item not in body]
if missing:
    raise SystemExit("MENUUI5: expected MENUUI4 baseline missing: " + ", ".join(missing))

if "static codeseg_ptr get_codeseg_from_addr(" not in text:
    raise SystemExit("MENUUI5: get_codeseg_from_addr helper not found in svc.cpp")

anchor = "        thr->kill(etype, common::utf8_to_ucs2(exit_category), reason);\n"
if body.count(anchor) != 1:
    raise SystemExit(f"MENUUI5: expected one thread_kill dispatch anchor, found {body.count(anchor)}")

inject = r'''        // MENUUI5 is diagnostic-only.  The detailed dump is deliberately gated to
        // a thread killing itself with reason -1, the exact MENUUI4 case
        // observed for Menu3.  Normal thread/process termination stays on the
        // compact MENUUI4 marker above.
        if (cpu && caller_thr && caller_pr && target_pr
            && (caller_thr->unique_id() == thr->unique_id()) && (reason == -1)) {
            const std::uint32_t pc = cpu->get_pc();
            const std::uint32_t lr = cpu->get_reg(14);
            const std::uint32_t sp = cpu->get_reg(13);
            const std::uint32_t cpsr = cpu->get_cpsr();

            LOG_WARN(KERNEL,
                "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL: caller_process={} caller_thread={} target_process={} target_thread={} handle=0x{:X} exit_type={} reason={} category={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
                caller_pr->name(), caller_thr->name(), target_pr->name(), thr->name(),
                h, static_cast<std::int32_t>(etype), reason, exit_category,
                pc, lr, sp, cpsr,
                cpu->get_reg(0), cpu->get_reg(1), cpu->get_reg(2), cpu->get_reg(3),
                cpu->get_reg(4), cpu->get_reg(5), cpu->get_reg(6), cpu->get_reg(7),
                cpu->get_reg(8), cpu->get_reg(9), cpu->get_reg(10), cpu->get_reg(11),
                cpu->get_reg(12));

            auto log_code_addr = [&](const char *kind, const std::uint32_t raw_addr) {
                const std::uint32_t addr = raw_addr & ~1U;
                codeseg_ptr seg = get_codeseg_from_addr(kern, caller_pr, addr, false);
                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(caller_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                        kind, raw_addr, addr, common::ucs2_to_utf8(seg->get_full_path()),
                        base, addr - base);
                } else {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 FRAME: kind={} raw=0x{:08X} addr=0x{:08X} module=<unresolved>",
                        kind, raw_addr, addr);
                }
            };

            log_code_addr("pc", pc);
            log_code_addr("lr", lr);

            // Scan 0x80 bytes from the guest stack. Every word is logged raw;
            // words that fall inside a loaded code segment are additionally
            // symbolized as module + offset. This is a candidate-return-address
            // scan, not a claim that every matching word is a true frame.
            constexpr std::uint32_t stack_word_count = 32;
            for (std::uint32_t i = 0; i < stack_word_count; ++i) {
                const std::uint32_t slot_addr = sp + i * sizeof(std::uint32_t);
                if (slot_addr < sp) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK: index={} slot=<overflow> stopping=1", i);
                    break;
                }

                const std::uint32_t *slot =
                    eka2l1::ptr<std::uint32_t>(slot_addr).get(caller_pr);
                if (!slot) {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK: index={} slot=0x{:08X} mapped=0 stopping=1",
                        i, slot_addr);
                    break;
                }

                const std::uint32_t value = *slot;
                const std::uint32_t candidate = value & ~1U;
                codeseg_ptr seg = nullptr;
                if (candidate >= 0x10000U) {
                    seg = get_codeseg_from_addr(kern, caller_pr, candidate, false);
                }

                if (seg) {
                    const std::uint32_t base = seg->get_code_run_addr(caller_pr);
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                        i, slot_addr, value, common::ucs2_to_utf8(seg->get_full_path()),
                        base, candidate - base);
                } else {
                    LOG_WARN(KERNEL,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                        i, slot_addr, value);
                }
            }
        }

'''

new_body = body.replace(anchor, inject + anchor, 1)
text = text[:start] + new_body + text[end:]
path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for expected in [
    "SYMBIAN-SYSTEMAPPS1 MENUUI4 THREADKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 FRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 STACK:",
]:
    if expected not in check:
        raise SystemExit("MENUUI5: marker verification failed: " + expected)
if check.count(marker) != 1:
    raise SystemExit(f"MENUUI5: expected one SELFKILL marker after patch, found {check.count(marker)}")
print("MENUUI5 SELFKILLTRACE1 patch applied")
