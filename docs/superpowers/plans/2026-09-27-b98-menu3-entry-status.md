# B98 Menu3 File Entry Status Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve the B97 `OpenIniFileLC` failure by logging the exact FileServer `Entry` path and result for the CompatBoot target process.

**Architecture:** Add one read-only diagnostic to the existing FileServer `entry()` implementation. Gate it on the active CompatBoot target UID3, run it after `get_entry_info`, and log the normalized path and the exact status without changing IPC completion behavior.

**Tech Stack:** Python source patcher and contract tests; existing C++ FileServer service and FASTBUILD workflow.

**Spec:** `docs/handoff/history/B97-DEVICE1.md` and the user’s current instruction to continue Branch 1.

## Global Constraints

- Preserve B89 startup bypass behavior, the six-service barrier, and real Menu3 launch.
- Keep Native Boot as the default and do not alter firmware or startup/readiness checks.
- Do not merge PR #6.
- Claim GREEN or an IPA only after GitHub Actions confirms it.

## Review Focus

- Non-target FileServer Entry calls remain unlogged by the new probe; test the target UID gate.
- Missing and successful entry results report the status without changing completion; test both result branches.
- Reapplying the patch must not duplicate the marker; test idempotence.

### Task 1: Add the scoped Entry result trace

**Files:** create `apply_nativeboot2_b98_menu3entrystatus1.py`, create `test_nativeboot2_b98_menu3entrystatus1.py`, modify `ci/fastbuild1_manifest.txt`, modify `.github/workflows/build-ios-nativeboot2-current-fast.yml`.

- [ ] Write and run failing contract tests for the target-only gate, exact result mapping, unchanged original completion branches, marker presence in FASTBUILD, and idempotence.
- [ ] Implement the minimal patcher and make the contract tests pass.
- [ ] Add the pair to the post-bootstrap manifest and require the marker in the compiled binary check.
- [ ] Run the new contract, manifest validation, full test discovery, and `git diff --check`.
- [ ] Update B97 handoff/current evidence with B98's scope and verification limits.
- [ ] Commit to `codex/compatboot1-menuprobe1`, then verify the corresponding GitHub Actions run before reporting its state.
