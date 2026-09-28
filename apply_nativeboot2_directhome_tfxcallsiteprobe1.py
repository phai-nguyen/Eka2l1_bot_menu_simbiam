#!/usr/bin/env python3
"""Observe the exact DirectHome Cone instruction without changing guest state."""
from pathlib import Path
import re
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXCALLSITEPROBE1"
CORE = "src/emu/cpu/include/cpu/arm_interface.h"
DYNCOM = "src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp"
SCHEDULER = "src/emu/kernel/src/scheduler.cpp"
CORE_MARK = "directhome_tfx_callsite_sample"
DYNCOM_MARK = "observe_directhome_tfx_callsite"
SCHEDULER_MARK = "[NBOOT2][DIRECTHOME_TFX_CALLSITE]"


def fail(why):
    raise SystemExit(f"{MARK}: {why}")


def once(source, anchor, label):
    count = source.count(anchor)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")


def apply_to_core(source: str) -> str:
    added = CORE_MARK in source
    if added:
        if source.count("struct " + CORE_MARK) != 1 or source.count("set_directhome_tfx_callsite_observer(") != 1 or source.count("emit_directhome_tfx_callsite(") != 1:
            fail("core has partial or duplicate observer")
        return source
    once(source, "    class core {\n", "core declaration")
    once(source, "        std::size_t core_num_ = 0;\n", "core field")
    once(source, "        virtual ~core() {}\n", "core destructor")
    once(source, "#include <functional>\n", "functional include")
    definition = '''    struct directhome_tfx_callsite_sample {
        std::uint32_t pc, r0, r1, lr, sp, cpsr;
        bool thumb;
    };

'''
    source = source.replace("    class core {\n", definition + "    class core {\n", 1)
    source = source.replace(
        "        std::size_t core_num_ = 0;\n",
        "        std::size_t core_num_ = 0;\n"
        "        std::function<void(const directhome_tfx_callsite_sample &)> directhome_tfx_callsite_observer_;\n", 1)
    source = source.replace(
        "        virtual ~core() {}\n",
        '''        virtual ~core() {}

        void set_directhome_tfx_callsite_observer(
            std::function<void(const directhome_tfx_callsite_sample &)> observer) {
            directhome_tfx_callsite_observer_ = observer;
        }

        void emit_directhome_tfx_callsite(const directhome_tfx_callsite_sample &sample) const {
            if (directhome_tfx_callsite_observer_) {
                directhome_tfx_callsite_observer_(sample);
            }
        }
''', 1)
    return source


def apply_to_dyncom(source: str) -> str:
    if DYNCOM_MARK in source:
        if source.count("static inline void " + DYNCOM_MARK) != 1 or source.count("DIRECTHOME_TFX_OBSERVE(cpu);") != 3:
            fail("Dyncom has partial or duplicate observer")
        return source
    once(source, "unsigned InterpreterMainLoop(ARMul_State *cpu, std::uint32_t &num_instrs) {\n", "interpreter entry")
    once(source, "#include <cpu/arm_interface.h>\n", "core interface include")
    macros = re.findall(r"(?ms)^#define GOTO_NEXT_INST\b.*?(?=^#(?:else|endif)\b)", source)
    if len(macros) != 2 or source.count("#define ENTER_FUSED_BRANCH") != 1:
        fail("expected two dispatch macros and one fused branch")
    for i, block in enumerate(macros):
        if block.count("    num_instrs++;                              \\\n") != 1 or block.count("    if (num_instrs >= cpu->NumInstrsToExecute) \\\n") != 1:
            fail(f"dispatch macro {i}: unknown instruction accounting")
    fused = re.search(r"(?ms)^#define ENTER_FUSED_BRANCH\b.*?(?=^[A-Za-z_]+\s*:\s*\{)", source)
    if not fused or fused.group().count("    num_instrs++") != 1 or "goto END;" not in fused.group():
        fail("fused branch: unknown instruction accounting")
    helper = '''// DirectHome callsite: inspect live flags without invoking STORE_NZCVT or changing guest state.
static inline void observe_directhome_tfx_callsite(ARMul_State *cpu) {
    if (!cpu->TFlag || (cpu->Reg[15] & ~1U) != 0x806EAFC6U) {
        return;
    }
    const std::uint32_t cpsr = (cpu->Cpsr & 0x0FFFFFDFU)
        | (cpu->NFlag << 31) | (cpu->ZFlag << 30) | (cpu->CFlag << 29)
        | (cpu->VFlag << 28) | (cpu->TFlag << 5);
    cpu->parent()->emit_directhome_tfx_callsite({
        cpu->Reg[15] & ~1U, cpu->Reg[0], cpu->Reg[1], cpu->Reg[14], cpu->Reg[13], cpsr, true
    });
}

#define DIRECTHOME_TFX_OBSERVE(cpu) observe_directhome_tfx_callsite(cpu)

'''
    source = source.replace("unsigned InterpreterMainLoop(ARMul_State *cpu, std::uint32_t &num_instrs) {\n", helper + "unsigned InterpreterMainLoop(ARMul_State *cpu, std::uint32_t &num_instrs) {\n", 1)
    for block in macros:
        modified = block.replace(
            "    num_instrs++;                              \\\n",
            "    DIRECTHOME_TFX_OBSERVE(cpu);              \\\n    num_instrs++;                              \\\n", 1)
        source = source.replace(block, modified, 1)
    block = fused.group()
    source = source.replace(block, block.replace(
        "    num_instrs++", "    DIRECTHOME_TFX_OBSERVE(cpu);                 \\\n    num_instrs++", 1), 1)
    return source


def validate_scheduler(source: str) -> None:
    for anchor in (
        "thread_scheduler::~thread_scheduler() {",
        "void thread_scheduler::switch_context(kernel::thread *oldt, kernel::thread *newt) {",
        "run_core->load_context(crr_thread->ctx);",
        "crr_thread = nullptr;",
    ):
        once(source, anchor, "scheduler " + anchor)


def apply_to_scheduler(source: str) -> str:
    validate_scheduler(source)
    if SCHEDULER_MARK in source:
        if source.count(SCHEDULER_MARK) != 2 or source.count("set_directhome_tfx_callsite_observer({});") != 2:
            fail("scheduler has partial or duplicate observer")
        return source
    destructor = "    thread_scheduler::~thread_scheduler() {\n        stop_idling();\n"
    switch = "    void thread_scheduler::switch_context(kernel::thread *oldt, kernel::thread *newt) {\n        if (oldt) {\n"
    once(source, destructor, "scheduler destructor")
    once(source, switch, "scheduler context switch")
    source = source.replace(destructor, '''    thread_scheduler::~thread_scheduler() {
        run_core->set_directhome_tfx_callsite_observer({});
        stop_idling();
''', 1)
    observer = '''    void thread_scheduler::switch_context(kernel::thread *oldt, kernel::thread *newt) {
        const auto *config = kern->get_config();
        if (config && config->native_phone_boot && config->compat_menu_probe_mode
            && config->compat_target_kind == 2) {
            run_core->set_directhome_tfx_callsite_observer([this](const arm::directhome_tfx_callsite_sample &sample) {
                if (!crr_thread || !crr_thread->owning_process()) {
                    LOG_WARN(KERNEL,
                        "[NBOOT2][DIRECTHOME_TFX_CALLSITE] profile=DirectHome context=missing core={} pc=0x{:08X} module=Cone.dll offset=0x215E r0=0x{:08X} r1=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} thumb={} behavior=OBSERVE_ONLY",
                        run_core->core_number(), sample.pc, sample.r0, sample.r1, sample.lr,
                        sample.sp, sample.cpsr, sample.thumb ? 1 : 0);
                    return;
                }
                kernel::process *process = crr_thread->owning_process();
                const std::uint32_t uid3 = static_cast<std::uint32_t>(std::get<2>(process->get_uid_type()));
                LOG_WARN(KERNEL,
                    "[NBOOT2][DIRECTHOME_TFX_CALLSITE] profile=DirectHome context=present core={} pc=0x{:08X} module=Cone.dll offset=0x215E r0=0x{:08X} r1=0x{:08X} lr=0x{:08X} sp=0x{:08X} cpsr=0x{:08X} thumb={} process={} uid3=0x{:08X} pid={} thread={} tid={} behavior=OBSERVE_ONLY",
                    run_core->core_number(), sample.pc, sample.r0, sample.r1, sample.lr,
                    sample.sp, sample.cpsr, sample.thumb ? 1 : 0, process->name(), uid3,
                    process->unique_id(), crr_thread->name(), crr_thread->unique_id());
            });
        } else {
            run_core->set_directhome_tfx_callsite_observer({});
        }
        if (oldt) {
'''
    return source.replace(switch, observer, 1)


def apply(root: Path) -> bool:
    paths = {name: root / name for name in (CORE, DYNCOM, SCHEDULER)}
    for name, path in paths.items():
        if not path.is_file():
            fail("missing source " + name)
    originals = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    validate_scheduler(originals[SCHEDULER])
    has_core = CORE_MARK in originals[CORE]
    has_dyncom = DYNCOM_MARK in originals[DYNCOM]
    if has_core != has_dyncom:
        fail("partial observer install")
    patched = {
        CORE: apply_to_core(originals[CORE]),
        DYNCOM: apply_to_dyncom(originals[DYNCOM]),
        SCHEDULER: apply_to_scheduler(originals[SCHEDULER]),
    }
    for name, data in patched.items():
        if data != originals[name]:
            paths[name].write_text(data, encoding="utf-8")
    return any(patched[name] != originals[name] for name in patched)


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxcallsiteprobe1.py <upstream-root>")
    print(f"{MARK}: {'applied' if apply(Path(sys.argv[1]).resolve()) else 'already applied'}")
    print("scope=OBSERVE_ONLY; guest_state_rewrite=NONE")


if __name__ == "__main__":
    main()
