# COMPATBOOT1 Direct Home Design

Status: design for review; implementation has not started.

## Goal

Create an isolated compatibility-boot path that attempts to reach the Nokia
5800 RM-356 Home/Idle screen sooner by launching the real firmware
`Z:\sys\bin\ailaunch.exe` after the existing six-service UI readiness
barrier. This path is separate from Native Boot and is not evidence that the
normal firmware startup chain succeeded.

## Baseline and isolation

- Base commit: `b14804a4ccd594d837496e2f106c4b5e8a2cdb10` (B99).
- Proposed branch: `codex/compatboot1-directhome`.
- B99's no-bypass branch and artifacts remain unchanged as the comparison
  baseline. This work is not to be merged into B99 or PR #7.
- Native Boot remains the normal/default mode. The new path is explicitly
  selected and scoped to its own CompatBoot profile.
- Only this experimental profile skips the ordinary firmware startup policy
  and its PhoneUI startup sequence. It must not rewrite PhoneUI failure,
  panic, or result handling in the ordinary Native Boot path.

## Proposed startup flow

1. Start EKA2L1 and load the same RM-356 firmware image and resources.
2. Select the new Direct Home CompatBoot profile explicitly; do not enable it
   implicitly for Native Boot.
3. Wait for the existing six UI-substrate services: FileServer, FBS,
   WindowServer, CenRep, AppArc, and AknCapServer. Do not launch the target
   before the barrier is ready.
4. Through the guest process loader, launch the firmware's real
   `Z:\sys\bin\ailaunch.exe`. Do not draw or substitute a host-side Nokia
   Home screen.
5. Preserve target startup errors and report the first decisive missing
   dependency, leave, panic, or loader failure. Do not silently suppress an
   error or fall back to Menu3 in this first Direct Home probe.

The current B99 path already has a CompatBoot mode, six-service barrier, and
real Menu3 probe. The proposed change is to add a distinct Direct Home target
profile rather than changing B99's target or Native Boot behavior.

## Logging and failure behavior

Use a unique build/track identity for this branch; never label it B99. Keep the
existing B88/B89 absence checks. Add bounded markers sufficient to correlate
profile selection, barrier readiness or timeout, target launch/result, and the
first target-scoped failure. Suggested markers:

- `[COMPATBOOT][MODE] profile=direct_home`
- `[COMPATBOOT][BARRIER_READY] services=...`
- `[COMPATBOOT][BARRIER_TIMEOUT] missing=...`
- `[COMPATBOOT][TARGET_LAUNCH] path=Z:\sys\bin\ailaunch.exe result=...`
- `[COMPATBOOT][FIRST_FAILURE] source=... target=ailaunch.exe ...`
- `[COMPATBOOT][TARGET_VISIBLE] target=ailaunch.exe` only when backed by
  actual guest-window/surface evidence.

A timeout must leave the target unlaunched. A target failure must remain
observable; no panic conversion, startup-success rewrite, fabricated system
state, resource substitution, firmware change, or broad service stub is part
of this initial probe.

## Acceptance criteria

### Build and isolation

- Contract tests show Direct Home is opt-in and Native Boot remains the
  default with its existing PhoneUI/SYSSTART behavior.
- The selected profile waits for all six named services before launching the
  target and launches only the real firmware `ailaunch.exe` in this probe.
- Build identity is unique to this experiment; B99 and B88/B89 invariants are
  preserved.
- FASTBUILD, iOS compilation, binary checks, and unsigned IPA packaging pass.

### Device evidence

- The device log identifies this experimental build and records the barrier
  and `ailaunch.exe` launch.
- The actual Symbian Home/Idle screen is visible and accepts touch/input. A
  process-alive marker, a state transition, or a launch marker alone is not
  success.
- Keep B99 logs and artifact available for comparison. Do not change firmware.

## Risks and unresolved implementation checks

- Passing the six-service barrier may still be insufficient for AILaunch;
  its first missing dependency must be observed rather than guessed.
- Verify the firmware's AILaunch executable identity, launch contract, and
  window/surface evidence before implementing target-visible detection.
- Direct Home may fail even though Menu3 can run. This experiment is scoped to
  answer that question; Menu3 remains a separate diagnostic target, not an
  implicit success fallback.
- A successful Direct Home path demonstrates the optional compatibility path,
  not completion of the normal firmware startup chain.

## Out of scope

- Modifying B99, its artifact, logs, or no-bypass behavior.
- Changing firmware, merging PR #7, or changing the Native Boot default.
- Faking Nokia UI, claiming Home success without interactive device evidence,
  or broadly bypassing/suppressing target errors.
- Implementing new service shims or state virtualization before a concrete
  missing dependency is evidenced and separately reviewed.
