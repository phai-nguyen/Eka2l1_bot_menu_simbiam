#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui8_xntheme_svcabtrace1.py <upstream-root>")

up = Path(sys.argv[1])
lib_path = up / "src/emu/kernel/src/libmanager.cpp"
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not lib_path.is_file() or not svc_path.is_file():
    raise SystemExit("MENUUI8: required kernel source file missing")

lib = lib_path.read_text(encoding="utf-8")
svc = svc_path.read_text(encoding="utf-8")

required_lib = [
    "V5 SVCMISS:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:",
    "svcnum == 0xAB",
]
required_svc = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
]
for marker in required_lib:
    if marker not in lib:
        raise SystemExit("MENUUI8: missing libmanager baseline marker: " + marker)
for marker in required_svc:
    if marker not in svc:
        raise SystemExit("MENUUI8: missing svc baseline marker: " + marker)

markers = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_REGFRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_PTR:",
]
if any(m in lib for m in markers):
    if all(m in lib for m in markers):
        print("MENUUI8 XNTHEME-SVCABTRACE1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI8: partial prior patch detected")

# Insert immediately before MENUUI2's SVCMISS log. This keeps the original
# missing-SVC behavior byte-for-byte at the control-flow level: MENUUI8 only
# observes state and never dispatches, completes, kills, or rewrites svcnum.
marker_pos = lib.find('"SYMBIAN-SYSTEMAPPS1 MENUUI2 SVCMISS:')
if marker_pos < 0:
    raise SystemExit("MENUUI8: MENUUI2 SVCMISS string not found")
log_pos = lib.rfind("LOG_ERROR(KERNEL,", 0, marker_pos)
if log_pos < 0:
    raise SystemExit("MENUUI8: enclosing MENUUI2 LOG_ERROR not found")
line_start = lib.rfind("\n", 0, log_pos) + 1
indent = lib[line_start:log_pos]
if not indent.isspace():
    raise SystemExit("MENUUI8: unexpected MENUUI2 SVCMISS indentation")

inject = r'''if (svcnum == 0xAB) {
    kernel::process *menuui8_pr = kern_->crr_process();
    kernel::thread *menuui8_thr = kern_->crr_thread();
    auto *menuui8_cpu = kern_->get_cpu();
    std::uint32_t menuui8_uid3 = 0;
    if (menuui8_pr) {
        menuui8_uid3 = static_cast<std::uint32_t>(std::get<2>(menuui8_pr->get_uid_type()));
    }

    // Trace only the RM-356 XN Theme Server. Other users of slot 0xAB remain
    // untouched and do not generate MENUUI8 noise.
    if (menuui8_pr && menuui8_thr && menuui8_cpu && menuui8_uid3 == 0x10207254U) {
        const std::uint32_t menuui8_pc = menuui8_cpu->get_pc();
        const std::uint32_t menuui8_lr = menuui8_cpu->get_reg(14);
        const std::uint32_t menuui8_sp = menuui8_cpu->get_reg(13);
        const std::uint32_t menuui8_cpsr = menuui8_cpu->get_cpsr();

        LOG_ERROR(KERNEL,
            "SYMBIAN-SYSTEMAPPS1 MENUUI8 XNTHEME_SVCAB: process={} uid=0x{:08X} thread={} svc=0x{:X} epocver={} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} r0=0x{:08X} r1=0x{:08X} r2=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} r6=0x{:08X} r7=0x{:08X} r8=0x{:08X} r9=0x{:08X} r10=0x{:08X} r11=0x{:08X} r12=0x{:08X}",
            menuui8_pr->name(), menuui8_uid3, menuui8_thr->name(), svcnum,
            static_cast<int>(kern_->get_epoc_version()), menuui8_pc, menuui8_lr, menuui8_sp, menuui8_cpsr,
            menuui8_cpu->get_reg(0), menuui8_cpu->get_reg(1), menuui8_cpu->get_reg(2), menuui8_cpu->get_reg(3),
            menuui8_cpu->get_reg(4), menuui8_cpu->get_reg(5), menuui8_cpu->get_reg(6), menuui8_cpu->get_reg(7),
            menuui8_cpu->get_reg(8), menuui8_cpu->get_reg(9), menuui8_cpu->get_reg(10), menuui8_cpu->get_reg(11),
            menuui8_cpu->get_reg(12));

        auto menuui8_log_code = [&](const char *kind, std::uint32_t index, std::uint32_t raw) {
            const std::uint32_t addr = raw & ~1U;
            codeseg_ptr found = nullptr;
            if (addr >= 0x10000U) {
                for (const auto &seg_obj : kern_->get_codeseg_list()) {
                    codeseg_ptr seg = reinterpret_cast<codeseg_ptr>(seg_obj.get());
                    if (!seg) continue;
                    const std::uint32_t base = seg->get_code_run_addr(menuui8_pr);
                    const std::uint32_t size = seg->get_text_size();
                    if (base <= addr && addr - base <= size) {
                        found = seg;
                        break;
                    }
                }
            }
            if (found) {
                const std::uint32_t base = found->get_code_run_addr(menuui8_pr);
                LOG_ERROR(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_REGFRAME: kind={} index={} raw=0x{:08X} addr=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                    kind, index, raw, addr, common::ucs2_to_utf8(found->get_full_path()), base, addr - base);
            }
        };

        menuui8_log_code("pc", 0, menuui8_pc);
        menuui8_log_code("lr", 0, menuui8_lr);
        for (std::uint32_t r = 0; r <= 12; ++r) {
            menuui8_log_code("reg", r, menuui8_cpu->get_reg(r));
        }

        // Walk enough stack to recover the caller chain in xnthemeserver/euser
        // without modifying guest memory or exception state.
        for (std::uint32_t i = 0; i < 48; ++i) {
            const std::uint32_t slot_addr = menuui8_sp + i * sizeof(std::uint32_t);
            if (slot_addr < menuui8_sp) break;
            const std::uint32_t *slot = eka2l1::ptr<std::uint32_t>(slot_addr).get(menuui8_pr);
            if (!slot) {
                LOG_ERROR(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK: index={} slot=0x{:08X} mapped=0 stopping=1",
                    i, slot_addr);
                break;
            }
            const std::uint32_t value = *slot;
            const std::uint32_t candidate = value & ~1U;
            codeseg_ptr found = nullptr;
            if (candidate >= 0x10000U) {
                for (const auto &seg_obj : kern_->get_codeseg_list()) {
                    codeseg_ptr seg = reinterpret_cast<codeseg_ptr>(seg_obj.get());
                    if (!seg) continue;
                    const std::uint32_t base = seg->get_code_run_addr(menuui8_pr);
                    const std::uint32_t size = seg->get_text_size();
                    if (base <= candidate && candidate - base <= size) {
                        found = seg;
                        break;
                    }
                }
            }
            if (found) {
                const std::uint32_t base = found->get_code_run_addr(menuui8_pr);
                LOG_ERROR(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=1 module={} base=0x{:08X} offset=0x{:08X}",
                    i, slot_addr, value, common::ucs2_to_utf8(found->get_full_path()), base, candidate - base);
            } else {
                LOG_ERROR(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_STACK: index={} slot=0x{:08X} value=0x{:08X} code_candidate=0",
                    i, slot_addr, value);
            }
        }

        // r1/r2 repeatedly look pointer-like in the MENUUI7 capture. Dump a
        // small read-only window so we can distinguish descriptor/message/
        // context structures. r3 is included when it is mapped as data.
        for (std::uint32_t r = 1; r <= 3; ++r) {
            const std::uint32_t base = menuui8_cpu->get_reg(r) & ~3U;
            if (base < 0x1000U || base >= 0x80000000U) continue;
            for (std::uint32_t w = 0; w < 8; ++w) {
                const std::uint32_t addr = base + w * sizeof(std::uint32_t);
                if (addr < base) break;
                const std::uint32_t *word = eka2l1::ptr<std::uint32_t>(addr).get(menuui8_pr);
                if (!word) break;
                LOG_ERROR(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI8 SVCAB_PTR: reg={} word={} addr=0x{:08X} value=0x{:08X}",
                    r, w, addr, *word);
            }
        }
    }
}

'''

# Reindent the injected block to match the existing diagnostic block.
indented = "".join((indent + row if row else row) for row in inject.splitlines(True))
lib = lib[:line_start] + indented + lib[line_start:]

for marker in markers:
    if marker not in lib:
        raise SystemExit("MENUUI8: marker missing after patch: " + marker)
for guard in required_lib:
    if guard not in lib:
        raise SystemExit("MENUUI8: MENUUI2 preservation guard failed: " + guard)
for guard in required_svc:
    if guard not in svc:
        raise SystemExit("MENUUI8: prior diagnostic chain preservation failed: " + guard)

lib_path.write_text(lib, encoding="utf-8")
print("MENUUI8 XNTHEME-SVCABTRACE1 patch applied")
