#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui7_presentationtrace1.py <upstream-root>")

up = Path(sys.argv[1])
svc_path = up / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI7: missing source file: {svc_path}")

svc = svc_path.read_text(encoding="utf-8")

required = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_FRAME:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_STACK:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI6 NEGIPC: path=LLE",
    "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:",
    "static codeseg_ptr get_codeseg_from_addr(",
    "kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());",
]
for marker in required:
    if marker not in svc:
        raise SystemExit("MENUUI7: required MENUUI6 baseline marker missing: " + marker)

markers = [
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND:",
    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_PMFRAME:",
]
if any(marker in svc for marker in markers):
    if all(marker in svc for marker in markers):
        print("MENUUI7 PRESENTATIONTRACE1 already present")
        raise SystemExit(0)
    raise SystemExit("MENUUI7: partial prior patch detected")

anchor = '''        const std::string server_name = ss->get_server()->name();
        kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());
'''
if svc.count(anchor) != 1:
    raise SystemExit(f"MENUUI7: IPC send anchor count={svc.count(anchor)}")

inject = r'''        // MENUUI7 PRESENTATIONTRACE1: diagnostic-only Menu IPC origin trace.
        // Record every IPC submitted by Menu UID 0x101F4CD2, then scan a small
        // slice of the guest stack for presentationmanager.dll frames. The IPC
        // request, status pointer, arguments and original dispatch semantics are
        // left untouched.
        kernel::thread *menuui7_thr = kern->crr_thread();
        kernel::process *menuui7_pr = kern->crr_process();
        if (menuui7_thr && menuui7_pr) {
            const auto menuui7_uids = menuui7_pr->get_uid_type();
            const std::uint32_t menuui7_uid3 = static_cast<std::uint32_t>(std::get<2>(menuui7_uids));
            if (menuui7_uid3 == 0x101F4CD2U) {
                auto *menuui7_cpu = kern->get_cpu();
                const std::uint32_t menuui7_pc = menuui7_cpu ? menuui7_cpu->get_pc() : 0;
                const std::uint32_t menuui7_lr = menuui7_cpu ? menuui7_cpu->get_reg(14) : 0;
                const std::uint32_t menuui7_sp = menuui7_cpu ? menuui7_cpu->get_reg(13) : 0;

                LOG_WARN(KERNEL,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_SEND: process={} uid=0x{:08X} thread={} server={} opcode={} sync={} status=0x{:08X} flags=0x{:08X} raw0=0x{:08X} raw1=0x{:08X} raw2=0x{:08X} raw3=0x{:08X} pc=0x{:08X} lr=0x{:08X} sp=0x{:08X}",
                    menuui7_pr->name(), menuui7_uid3, menuui7_thr->name(), server_name, ord,
                    sync ? 1 : 0, status.ptr_address(), static_cast<std::uint32_t>(arg.flag),
                    static_cast<std::uint32_t>(arg.args[0]), static_cast<std::uint32_t>(arg.args[1]),
                    static_cast<std::uint32_t>(arg.args[2]), static_cast<std::uint32_t>(arg.args[3]),
                    menuui7_pc, menuui7_lr, menuui7_sp);

                if (menuui7_cpu && menuui7_sp) {
                    constexpr std::uint32_t menuui7_stack_words = 24;
                    for (std::uint32_t menuui7_i = 0; menuui7_i < menuui7_stack_words; ++menuui7_i) {
                        const std::uint32_t menuui7_slot_addr = menuui7_sp + menuui7_i * sizeof(std::uint32_t);
                        if (menuui7_slot_addr < menuui7_sp) break;
                        const std::uint32_t *menuui7_slot = eka2l1::ptr<std::uint32_t>(menuui7_slot_addr).get(menuui7_pr);
                        if (!menuui7_slot) break;

                        const std::uint32_t menuui7_raw = *menuui7_slot;
                        const std::uint32_t menuui7_addr = menuui7_raw & ~1U;
                        if (menuui7_addr < 0x10000U) continue;
                        codeseg_ptr menuui7_seg = get_codeseg_from_addr(kern, menuui7_pr, menuui7_addr, false);
                        if (!menuui7_seg) continue;

                        const std::string menuui7_module = common::ucs2_to_utf8(menuui7_seg->get_full_path());
                        if (menuui7_module.find("presentationmanager.dll") == std::string::npos
                            && menuui7_module.find("PRESENTATIONMANAGER.DLL") == std::string::npos) {
                            continue;
                        }

                        const std::uint32_t menuui7_base = menuui7_seg->get_code_run_addr(menuui7_pr);
                        LOG_WARN(KERNEL,
                            "SYMBIAN-SYSTEMAPPS1 MENUUI7 IPC_PMFRAME: server={} opcode={} stack_index={} slot=0x{:08X} raw=0x{:08X} module={} base=0x{:08X} offset=0x{:08X}",
                            server_name, ord, menuui7_i, menuui7_slot_addr, menuui7_raw,
                            menuui7_module, menuui7_base, menuui7_addr - menuui7_base);
                    }
                }
            }
        }

'''

svc = svc.replace(anchor,
    '        const std::string server_name = ss->get_server()->name();\n' + inject +
    '        kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());\n',
    1)

for marker in markers:
    if marker not in svc:
        raise SystemExit("MENUUI7: marker missing after patch: " + marker)
if "kern->call_ipc_send_callbacks(server_name, ord, arg, status.ptr_address(), kern->crr_thread());" not in svc:
    raise SystemExit("MENUUI7: IPC dispatch semantics guard failed")
if "SYMBIAN-SYSTEMAPPS1 MENUUI6 LEAVE_NEG1:" not in svc or "SYMBIAN-SYSTEMAPPS1 MENUUI5 SELFKILL:" not in svc:
    raise SystemExit("MENUUI7: prior diagnostic chain preservation failed")

svc_path.write_text(svc, encoding="utf-8")
print("MENUUI7 PRESENTATIONTRACE1 patch applied")
