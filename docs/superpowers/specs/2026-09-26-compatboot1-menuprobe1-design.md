# COMPATBOOT1-MENUPROBE1 Design

Date: 2026-09-26  
Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`  
Branch: `nativeboot2-current`

## Goal

After B89, the RM-356 firmware publishes global system state `109` following
the exact Telephone `CONE 14` exit, and the emulator shuts down normally. The
device log does not show `menu3.exe` being launched. This probe adds a separate
compatibility-boot path that waits for the UI substrate and then starts the
real `Z:\sys\bin\menu3.exe` from the RM-356 firmware. The target outcome is a
real Symbian Applications Menu, not a host-rendered imitation.

The probe is the first target-first experiment. It should expose the first
missing dependency without preemptively faking broad P&S, CenRep, or server
state.

## Approved architecture

- Keep NATIVEBOOT2 as the default and fidelity/reference path.
- Add COMPATBOOT as a separately selectable profile; do not silently change
  native-boot behavior.
- Reuse the real RM-356 firmware executables and resources, including
  `menu3.exe`, Avkon/Eikon, RSC, MIF, and MBM content.
- Limit this first probe to a UI-readiness barrier, a real Menu3 launch, and
  diagnostics. Do not implement speculative shims in the probe.
- Scope any COMPATBOOT state policy or future shim to its profile and the
  narrowest possible target/process/server/property predicate.

## Runtime flow

1. COMPATBOOT is selected explicitly for a run; the existing NATIVEBOOT2 path
   remains the default.
2. The bootstrap observes readiness of FileServer, FBS, WindowServer, CenRep,
   AppArc, and AknCapServer using existing runtime service/process evidence.
3. It emits a barrier-ready record only after all required services are
   available. A timeout or missing service is reported with the exact missing
   dependency; the launcher must not race ahead.
4. Once ready, the target launcher starts the firmware's real
   `Z:\sys\bin\menu3.exe` through EKA2L1's guest process loader.
5. The compatibility trace records launch outcome, loader/DLL/ordinal and
   resource failures, CenRep/P&S reads, client-server CreateSession/IPC
   failures, target panic/exit, WindowGroup visibility, and first visible
   Menu surface.
6. Stop at the first decisive failure. A later change may implement only that
   evidenced dependency, under the COMPATBOOT profile, with a regression test.

The exact existing runtime hook and readiness signals must be confirmed during
implementation planning. If a service's readiness cannot be observed
reliably, report that gap rather than treating process existence as readiness.

## Components

| Component | Responsibility in this probe |
| --- | --- |
| CompatBoot profile | Explicitly select COMPATBOOT while preserving the native default. |
| UI barrier | Observe the six required services and produce a bounded ready/timeout result. |
| Target launcher | Start the real firmware Menu3 executable once, after the barrier. |
| CompatTrace | Emit stable `[COMPATBOOT]` markers with target and dependency details. |
| Failure oracle | Classify the first loader, server, resource, state, IPC, visibility, or process failure. |

This first probe does not require a general-purpose StateVirtualizer,
ServiceShimRegistry, or ResourceCompatibility subsystem. Those are future
design options only if Menu3 evidence identifies a specific requirement.

## Diagnostics

Required markers:

- `[COMPATBOOT][MODE] profile=...`
- `[COMPATBOOT][BARRIER_WAIT] service=...`
- `[COMPATBOOT][BARRIER_READY] services=...`
- `[COMPATBOOT][BARRIER_TIMEOUT] missing=...`
- `[COMPATBOOT][TARGET_LAUNCH] path=Z:\sys\bin\menu3.exe result=...`
- `[COMPATBOOT][MISSING_SERVER]`
- `[COMPATBOOT][FIRST_FAILURE] source=... target_uid3=...`
- `[COMPATBOOT][TARGET_VISIBLE]`

Markers should include enough process, UID3, server/property/resource, result,
and timestamp context to identify the earliest blocker. Do not log sensitive
user data. Existing profile-enabled `[NBOOT2]` loader, resource, CenRep/P&S,
IPC, and panic records remain the detailed evidence for those failure classes;
the CompatBoot first-failure envelope correlates them without duplicating their
formats or changing their error handling.

## Non-goals

- Replace or weaken NATIVEBOOT2 as the default path.
- Draw fake Nokia pixels or substitute a host-created Nokia menu.
- Skip the barrier and launch Menu3 immediately on emulator start.
- Change unrelated global P&S/CenRep state or suppress unrelated panics.
- Add speculative broad shims before the first Menu3 failure is observed.
- Claim success from state `109`, a process spawn, or an alive process alone.
- Fix the B85/B89 emulator-exit behavior unless the probe reproduces a distinct
  exit defect; the supplied B89 log shows orderly shutdown.

## Verification and acceptance

### Automated contract and build checks

- The FASTBUILD regression chain continues to pass.
- Contract tests prove COMPATBOOT is opt-in, the native path remains the
  default, the launcher waits for all required barrier services, and Menu3 is
  launched at most once.
- Timeout tests prove a missing/unready service prevents launch and identifies
  the missing service.
- Target path tests prove the launcher selects the real RM-356
  `Z:\sys\bin\menu3.exe` through the guest loader.
- IPA audit confirms required COMPATBOOT markers are present.

### Device evidence ladder

1. **P0:** `menu3.exe` spawns and passes initial loader startup.
2. **P1:** Menu3 creates a WindowGroup/canvas and remains alive.
3. **P2:** The real Menu surface becomes visible.
4. **P3:** Application names/icons render.
5. **P4:** Touch, keyboard, and Back input work.
6. **P5:** Menu launches at least one real Symbian application.

Only P2 or higher proves that the Symbian Menu is visible; the final project
acceptance remains an interactive RM-356 Home/Menu on the iOS device.

## B89 evidence incorporated

- The exact B88 Telephone `CONE 14` predicate arms the B89 one-shot gate.
- SYSSTART's exact global-state write `101 -> 116` is observed as `applied=109`.
- The guest Home screen process continues and performs service requests.
- The supplied B89 runtime log shows `exit_requested` followed by
  `shutdown_done`, consistent with orderly emulator shutdown.
- The log contains Menu3 resource lookups, but no Menu3 process launch marker;
  resource access alone does not prove that Menu3 ran.

## Open implementation-planning checks

- Identify the smallest existing guest-loader call suitable for starting
  Menu3 without host-side execution.
- Establish reliable service-ready signals for all six barrier dependencies.
- Confirm how this app build selects an opt-in COMPATBOOT profile while
  preserving Native Boot as the default.
- Determine which existing logs already expose each failure class and add
  instrumentation only where needed.
- Confirm FASTBUILD manifest/test registration and artifact naming for the
  first COMPATBOOT build.
