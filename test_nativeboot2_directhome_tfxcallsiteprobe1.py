#!/usr/bin/env python3
"""Behavior contracts for the optional DirectHome Dyncom callsite observer."""
import importlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CORE = """#pragma once
#include <functional>
namespace eka2l1::arm {
    class core {
    private:
        std::size_t core_num_ = 0;
    public:
        virtual ~core() {}
        std::size_t core_number() const { return core_num_; }
    };
}
"""

DYNCOM = """#include <cpu/arm_interface.h>
unsigned InterpreterMainLoop(ARMul_State *cpu, std::uint32_t &num_instrs) {
#if defined __GNUC__ || defined __clang__
#define GOTO_NEXT_INST                         \\
    PROF_STEP(cpu, inst_base->idx);            \\
    if (num_instrs >= cpu->NumInstrsToExecute) \\
        goto END;                              \\
    num_instrs++;                              \\
    goto *InstLabel[inst_base->idx]
#else
#define GOTO_NEXT_INST                         \\
    PROF_STEP(cpu, inst_base->idx);            \\
    if (num_instrs >= cpu->NumInstrsToExecute) \\
        goto END;                              \\
    num_instrs++;                              \\
    switch (inst_base->idx) {                  \\
    case 0:                                    \\
        goto VMLA_INST;
#endif
#define ENTER_FUSED_BRANCH                     \\
    inst_base = (arm_inst *)&cpu->trans_cache_buf[ptr]; \\
    PROF_STEP(cpu, inst_base->idx);            \\
    if (num_instrs >= cpu->NumInstrsToExecute) \\
        goto END;                              \\
    num_instrs++
CMP_INST : {
}
}
"""

SCHEDULER = """    thread_scheduler::~thread_scheduler() {
        stop_idling();
    }
    void thread_scheduler::stop_idling() { }
    void thread_scheduler::switch_context(kernel::thread *oldt, kernel::thread *newt) {
        if (oldt) {
            run_core->save_context(oldt->ctx);
        }
        if (newt) {
            crr_thread = newt;
            run_core->load_context(crr_thread->ctx);
        } else {
            crr_thread = nullptr;
        }
    }
"""

FILES = {
    "src/emu/cpu/include/cpu/arm_interface.h": CORE,
    "src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp": DYNCOM,
    "src/emu/kernel/src/scheduler.cpp": SCHEDULER,
}


def fixture(root, files=FILES):
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class CallsiteProbeTests(unittest.TestCase):
    def patcher(self):
        self.assertIsNotNone(importlib.util.find_spec("apply_nativeboot2_directhome_tfxcallsiteprobe1"),
                             "DirectHome callsite patcher missing")
        return importlib.import_module("apply_nativeboot2_directhome_tfxcallsiteprobe1")

    def test_only_thumb_exact_pc_before_dispatch(self):
        patcher = self.patcher()
        result = patcher.apply_to_dyncom(DYNCOM)
        self.assertEqual(result.count("0x806EAFC6"), 1)
        self.assertIn("if (!cpu->TFlag || (cpu->Reg[15] & ~1U) != 0x806EAFC6U)", result)
        self.assertIn("cpu->Reg[15]", result)
        for reg in (0, 1, 13, 14):
            self.assertIn(f"cpu->Reg[{reg}]", result)
        self.assertIn("cpu->Cpsr", result)
        self.assertIn("cpu->NFlag", result)
        self.assertEqual(result.count("DIRECTHOME_TFX_OBSERVE(cpu);"), 3)
        for branch in result.split("#define GOTO_NEXT_INST")[1:]:
            self.assertLess(branch.index("DIRECTHOME_TFX_OBSERVE(cpu);"), branch.index("num_instrs++"))
        fused = result.split("#define ENTER_FUSED_BRANCH", 1)[1]
        self.assertLess(fused.index("DIRECTHOME_TFX_OBSERVE(cpu);"), fused.index("num_instrs++"))
        self.assertEqual(result.count("num_instrs++"), DYNCOM.count("num_instrs++"))
        self.assertEqual(result.count("goto *InstLabel[inst_base->idx]"), 1)
        self.assertNotIn("cpu->Reg[15] =", result)
        core = patcher.apply_to_core(CORE)
        self.assertIn("set_directhome_tfx_callsite_observer", core)
        self.assertIn("directhome_tfx_callsite_sample", core)
        self.assertIn("directhome_tfx_callsite_observer_ = observer;", core)
        self.assertIn("if (directhome_tfx_callsite_observer_)", core)

    def test_dispatch_accounting_error_reports_observed_lines(self):
        patcher = self.patcher()
        unsupported = DYNCOM.replace("num_instrs++;", "num_instrs += 1;", 1)
        with self.assertRaises(SystemExit) as raised:
            patcher.apply_to_dyncom(unsupported)
        self.assertIn("observed lines=", str(raised.exception))
        self.assertIn("num_instrs += 1;", str(raised.exception))

    def test_dispatch_accounting_accepts_relaxed_atomic_instruction_limit(self):
        patcher = self.patcher()
        atomic_dispatch = DYNCOM.replace(
            "cpu->NumInstrsToExecute)",
            "cpu->NumInstrsToExecute.load(std::memory_order_relaxed))",
            2,
        )
        self.assertEqual(atomic_dispatch.count("NumInstrsToExecute.load(std::memory_order_relaxed)"), 2)
        result = patcher.apply_to_dyncom(atomic_dispatch)
        self.assertEqual(result.count("DIRECTHOME_TFX_OBSERVE(cpu);"), 3)
        self.assertEqual(result.count("num_instrs++"), atomic_dispatch.count("num_instrs++"))

    def test_dispatch_accounting_allows_different_horizontal_spacing(self):
        patcher = self.patcher()
        slash = chr(92)
        lines = []
        for line in DYNCOM.splitlines(keepends=True):
            if "num_instrs++;" in line:
                ending = "\r\n" if line.endswith("\r\n") else "\n"
                body = line[:-len(ending)] if ending else line
                pos = body.rfind(slash)
                body = body[:pos].rstrip() + " " + slash
                line = body + ending
            lines.append(line)
        baseline = "".join(lines)
        self.assertNotEqual(baseline, DYNCOM)
        result = patcher.apply_to_dyncom(baseline)
        self.assertEqual(result.count("DIRECTHOME_TFX_OBSERVE(cpu);"), 3)
        self.assertEqual(result.count("num_instrs++"), baseline.count("num_instrs++"))
        for branch in result.split("#define GOTO_NEXT_INST")[1:]:
            self.assertLess(branch.index("DIRECTHOME_TFX_OBSERVE(cpu);"), branch.index("num_instrs++"))

    def test_dispatch_shape_error_reports_observed_definition_counts(self):
        patcher = self.patcher()
        malformed = DYNCOM + "\n#define GOTO_NEXT_INST \\\n    num_instrs++\n#endif\n"
        with self.assertRaises(SystemExit) as raised:
            patcher.apply_to_dyncom(malformed)
        self.assertIn("GOTO_NEXT_INST definitions=3", str(raised.exception))
        self.assertIn("ENTER_FUSED_BRANCH definitions=1", str(raised.exception))

    def test_apply_to_dyncom_supports_baseline_without_fused_branch(self):
        patcher = self.patcher()
        start = DYNCOM.index("#define ENTER_FUSED_BRANCH")
        end = DYNCOM.index("CMP_INST : {", start)
        baseline = DYNCOM[:start] + DYNCOM[end:]
        result = patcher.apply_to_dyncom(baseline)
        self.assertEqual(result.count("DIRECTHOME_TFX_OBSERVE(cpu);"), 2)
        self.assertEqual(result.count("num_instrs++"), 2)
        for branch in result.split("#define GOTO_NEXT_INST")[1:]:
            self.assertLess(branch.index("DIRECTHOME_TFX_OBSERVE(cpu);"), branch.index("num_instrs++"))

    def test_missing_duplicate_anchor_is_atomic_and_idempotent(self):
        patcher = self.patcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            patcher.apply(root)
            first = {name: (root / name).read_text(encoding="utf-8") for name in FILES}
            patcher.apply(root)
            self.assertEqual(first, {name: (root / name).read_text(encoding="utf-8") for name in FILES})

        for bad_name, bad_value in (
            ("src/emu/cpu/include/cpu/arm_interface.h", CORE.replace("    class core {", "    class wrong {")),
            ("src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp", DYNCOM + "\n#define ENTER_FUSED_BRANCH \\\n    num_instrs++\n"),
            ("src/emu/kernel/src/scheduler.cpp", SCHEDULER + SCHEDULER),
        ):
            with self.subTest(bad_name=bad_name), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                files = dict(FILES, **{bad_name: bad_value})
                fixture(root, files)
                with self.assertRaises(SystemExit):
                    patcher.apply(root)
                self.assertEqual(files, {name: (root / name).read_text(encoding="utf-8") for name in FILES})

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            (root / "src/emu/kernel/src/scheduler.cpp").unlink()
            with self.assertRaises(SystemExit):
                patcher.apply(root)
            self.assertEqual(CORE, (root / "src/emu/cpu/include/cpu/arm_interface.h").read_text())

    def test_scheduler_profile_gate_and_same_thread_identity(self):
        patcher = self.patcher()
        self.assertTrue(hasattr(patcher, "apply_to_scheduler"), "scheduler observer absent")
        result = patcher.apply_to_scheduler(SCHEDULER)
        self.assertIn("[NBOOT2][DIRECTHOME_TFX_CALLSITE]", result)
        for gate in ("native_phone_boot", "compat_menu_probe_mode", "compat_target_kind == 2"):
            self.assertIn(gate, result)
        self.assertIn("[this](const arm::directhome_tfx_callsite_sample &sample)", result)
        self.assertIn("crr_thread->owning_process()", result)
        self.assertIn("crr_thread->unique_id()", result)
        self.assertIn("process->unique_id()", result)
        self.assertIn("process->get_uid_type()", result)
        self.assertIn("core_number()", result)
        for field in ("sample.pc", "sample.r0", "sample.r1", "sample.lr", "sample.sp", "sample.cpsr", "sample.thumb"):
            self.assertIn(field, result)
        self.assertIn("behavior=OBSERVE_ONLY", result)
        self.assertNotIn("[newt]", result)

    def test_missing_context_and_destroy_clear_callback(self):
        patcher = self.patcher()
        self.assertTrue(hasattr(patcher, "apply_to_scheduler"), "scheduler observer absent")
        result = patcher.apply_to_scheduler(SCHEDULER)
        self.assertIn("if (!crr_thread || !crr_thread->owning_process())", result)
        self.assertIn("context=missing", result)
        self.assertIn("set_directhome_tfx_callsite_observer({});", result)
        destructor = result.split("thread_scheduler::~thread_scheduler() {", 1)[1].split("void thread_scheduler::stop_idling", 1)[0]
        self.assertLess(destructor.index("set_directhome_tfx_callsite_observer({});"), destructor.index("stop_idling();"))
        switch = result.split("thread_scheduler::switch_context(", 1)[1]
        self.assertLess(switch.index("compat_target_kind == 2"), switch.index("if (oldt)"))
        self.assertIn("} else {\n            run_core->set_directhome_tfx_callsite_observer({});\n        }", switch)

    def test_manifest_contract_checks_patched_upstream(self):
        patcher = self.patcher()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            cmd = [sys.executable, str(Path(__file__).resolve()), str(root)]
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            patcher.apply(root)
            result = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def contract(root: Path):
    paths = {name: root / name for name in FILES}
    if any(not path.is_file() for path in paths.values()):
        raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: missing source")
    core = paths["src/emu/cpu/include/cpu/arm_interface.h"].read_text(encoding="utf-8")
    dyncom = paths["src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp"].read_text(encoding="utf-8")
    scheduler = paths["src/emu/kernel/src/scheduler.cpp"].read_text(encoding="utf-8")
    if core.count("struct directhome_tfx_callsite_sample") != 1 or core.count("set_directhome_tfx_callsite_observer(") != 1:
        raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: missing/duplicate core interface")
    fused_definitions = dyncom.count("#define ENTER_FUSED_BRANCH")
    if (fused_definitions not in (0, 1)
            or dyncom.count("DIRECTHOME_TFX_OBSERVE(cpu);") != 2 + fused_definitions
            or dyncom.count("0x806EAFC6U") != 1):
        raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: wrong dispatch/PC")
    for block in dyncom.split("#define GOTO_NEXT_INST")[1:]:
        if block.index("DIRECTHOME_TFX_OBSERVE(cpu);") > block.index("num_instrs++"):
            raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: hook after dispatch")
    if scheduler.count("[NBOOT2][DIRECTHOME_TFX_CALLSITE]") != 2:
        raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: missing/duplicate scheduler log")
    for gate in ("native_phone_boot", "compat_menu_probe_mode", "compat_target_kind == 2"):
        if gate not in scheduler:
            raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: missing profile gate " + gate)
    if "run_core->set_directhome_tfx_callsite_observer({});" not in scheduler:
        raise SystemExit("DIRECTHOME-TFXCALLSITEPROBE1-TEST: missing teardown")
    print("DIRECTHOME-TFXCALLSITEPROBE1-TEST: PASS")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        contract(Path(sys.argv[1]).resolve())
    else:
        unittest.main()
