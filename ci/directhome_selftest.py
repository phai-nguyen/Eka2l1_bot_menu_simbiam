#!/usr/bin/env python3
"""Cheap pre-build gate for the EKA2L1 DirectHome workstream.

This deliberately avoids the macOS/iOS toolchain.  Its job is to reject a
broken manifest, missing scripts, syntax errors, known PhoneUI bypasses, or a
lost DirectHome identity before FASTBUILD consumes a macOS runner.
"""
from __future__ import annotations

import argparse
import os
import py_compile
import subprocess
import sys
from pathlib import Path

EXPECTED_BRANCH = "codex/compatboot1-directhome"
MANIFEST_REL = Path("ci/fastbuild1_manifest.txt")
WORKFLOW_REL = Path(".github/workflows/build-ios-nativeboot2-current-fast.yml")
FORBIDDEN_ACTIVE_MARKERS = (
    "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]",
    "[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]",
)
REQUIRED_ORDER = (
    "apply_nativeboot2_b99_buildfingerprint1.py",
    "apply_nativeboot2_compatboot1_directhomefingerprint1.py",
    "apply_nativeboot2_directhome_tfxenable1.py",
    "apply_nativeboot2_directhome_tfxecomtrace1.py",
    "apply_nativeboot2_directhome_tfxcallsiteprobe1.py",
    "apply_nativeboot2_directhome_tfxsessiontrace1.py",
    "apply_nativeboot2_directhome_tfxdllprobe1.py",
    "apply_nativeboot2_directhome_propertycancelguard1.py",
)
FIXTURE_TESTS = (
    "test_nativeboot2_b99_buildfingerprint1.py",
    "test_nativeboot2_compatboot1_directhomefingerprint1.py",
    "test_nativeboot2_directhome_propertycancelguard1.py",
)


class Gate:
    def __init__(self, report: Path):
        self.report = report
        self.lines: list[str] = []
        self.failed = False

    def note(self, message: str) -> None:
        self.lines.append(message)
        print(message)

    def check(self, condition: bool, label: str) -> None:
        if condition:
            self.note(f"PASS: {label}")
        else:
            self.failed = True
            self.note(f"FAIL: {label}")

    def finish(self) -> None:
        self.report.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        if self.failed:
            raise SystemExit(1)


def parse_manifest(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    section = None
    post: list[tuple[str, str]] = []
    regressions: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in ("[post_bootstrap]", "[regressions]"):
            section = line[1:-1]
            continue
        if section == "post_bootstrap":
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 2 or not all(parts):
                raise ValueError(f"invalid post_bootstrap row: {line}")
            post.append((parts[0], parts[1]))
        elif section == "regressions":
            regressions.append(line)
        else:
            raise ValueError(f"row outside manifest section: {line}")
    return post, regressions


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--report", default="DIRECTHOME-SELFTEST-REPORT.txt")
    ap.add_argument("--expected-branch", default=EXPECTED_BRANCH)
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    report = (root / args.report).resolve()
    gate = Gate(report)
    gate.note("DIRECTHOME SELFTEST v1")
    gate.note(f"repo={root}")

    manifest = root / MANIFEST_REL
    gate.check(manifest.is_file(), f"manifest exists: {MANIFEST_REL}")
    if not manifest.is_file():
        gate.finish()
        return

    try:
        post, regressions = parse_manifest(manifest)
        gate.check(True, "manifest parses")
    except Exception as exc:
        gate.note(f"FAIL: manifest parse: {exc}")
        gate.failed = True
        gate.finish()
        return

    apply_scripts = [a for a, _ in post]
    test_scripts = [t for _, t in post]
    gate.check(len(apply_scripts) == len(set(apply_scripts)), "no duplicate apply scripts")
    gate.check(len(test_scripts) == len(set(test_scripts)), "no duplicate post-bootstrap tests")
    gate.check(len(regressions) == len(set(regressions)), "no duplicate regression entries")

    referenced = apply_scripts + test_scripts + regressions
    missing = [name for name in referenced if not (root / name).is_file()]
    gate.check(not missing, "all manifest-referenced scripts exist")
    for name in missing:
        gate.note(f"  missing={name}")

    positions = []
    for required in REQUIRED_ORDER:
        if required in apply_scripts:
            positions.append(apply_scripts.index(required))
            gate.check(True, f"active milestone: {required}")
        else:
            gate.check(False, f"active milestone: {required}")
    if len(positions) == len(REQUIRED_ORDER):
        gate.check(positions == sorted(positions) and len(set(positions)) == len(positions),
                   "B99 -> DirectHome -> TFX -> cancel-guard ordering preserved")

    active_text = "\n".join(
        (root / name).read_text(encoding="utf-8", errors="replace")
        for name in apply_scripts
        if (root / name).is_file()
    )
    for marker in FORBIDDEN_ACTIVE_MARKERS:
        gate.check(marker not in active_text, f"forbidden active bypass absent: {marker}")

    direct_fp = root / "apply_nativeboot2_compatboot1_directhomefingerprint1.py"
    if direct_fp.is_file():
        fp_text = direct_fp.read_text(encoding="utf-8", errors="replace")
        gate.check(
            "COMPATBOOT1_DIRECTHOME1" in fp_text and "H2_COMPATBOOT1_DIRECTHOME1" in fp_text,
            "DirectHome build identity patch remains present",
        )

    compile_targets = [root / "ci/fastbuild1_manifest.py", root / "ci/directhome_selftest.py"]
    compile_targets.extend(root / name for name in referenced if name.endswith(".py"))
    compile_failed: list[str] = []
    for path in dict.fromkeys(compile_targets):
        if not path.is_file():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_failed.append(f"{path.relative_to(root)}: {exc.msg}")
    gate.check(not compile_failed, "Python syntax check for active FASTBUILD scripts")
    for item in compile_failed:
        gate.note(f"  syntax={item}")

    shell_gate = root / "ci/fastbuild1_reject_phoneui_bypass_markers.sh"
    if shell_gate.is_file():
        result = run(["bash", "-n", str(shell_gate)], root)
        gate.check(result.returncode == 0, "PhoneUI binary-gate shell syntax")
        if result.returncode:
            gate.note(result.stderr.strip())

    for test_name in FIXTURE_TESTS:
        path = root / test_name
        if not path.is_file():
            gate.check(False, f"fixture test exists: {test_name}")
            continue
        result = run([sys.executable, str(path)], root)
        gate.check(result.returncode == 0, f"fixture contract: {test_name}")
        if result.returncode:
            gate.note((result.stdout + "\n" + result.stderr).strip())

    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or ""
    if branch:
        gate.check(branch == args.expected_branch, f"CI branch is {args.expected_branch}")
        gate.note(f"ci_branch={branch}")
    else:
        gate.note("INFO: branch check skipped outside GitHub Actions")

    workflow = root / WORKFLOW_REL
    if workflow.is_file():
        workflow_text = workflow.read_text(encoding="utf-8")
        gate.check("needs: selftest" in workflow_text, "FASTBUILD requires selftest job")
        gate.check("Verify binary invariants" in workflow_text, "binary invariant gate retained")
        gate.check("Package unsigned IPA" in workflow_text, "IPA packaging stage retained")
        if "Verify binary invariants" in workflow_text and "Package unsigned IPA" in workflow_text:
            gate.check(
                workflow_text.index("Verify binary invariants") < workflow_text.index("Package unsigned IPA"),
                "binary verification precedes IPA packaging",
            )

    gate.note(f"post_bootstrap_count={len(post)}")
    gate.note(f"regression_count={len(regressions)}")
    gate.note("result=" + ("FAIL" if gate.failed else "PASS"))
    gate.finish()


if __name__ == "__main__":
    main()
