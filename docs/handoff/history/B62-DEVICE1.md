# NATIVEBOOT2 B62 STARTERGLOBALSTATE1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS; GLOBAL STARTUP STATE STALL IDENTIFIED
Install mode: CLEAN INSTALL

## Inputs

- EKA2L1(20260924-152630).log
- EKA2L1_Persistent(20260924-152637).log
- EKA2L1_TakeThis(20260924-152637).log

## Primary result

B62 resolves the System Starter critical-phase state.

Observed KPSGlobalSystemState sequence:

- 22:13:48.154
  0 -> 100
  writer: SYSSTART[100059c9] / StarterServer
  state: ESwStateStartingUiServices

- 22:14:20.950
  100 -> 101
  writer: SYSSTART[100059c9] / StarterServer
  state: ESwStateStartingCriticalApps

No further SET to 102, 103, 104 or any terminal state is observed.

Readers later see exactly 101:

- akncapserver at 22:14:21.526
- Startup at 22:14:22.429 and 22:14:22.431
- Home screen at 22:14:24.518

Therefore System Starter itself is stalled at StartingCriticalApps=101.

This is upstream of Startup's private Wait=1 state and explains why Startup
does not consider Starter's critical phase complete.

## Startup private state remains unchanged

Startup still defines/writes:

0x100058F4:1
0 -> Wait(1)

No [STARTUP_STATE_HANDLE] write to this target is observed.
No StartAnimations(2) publication is observed.

## Boundary immediately around transition to 101

Immediately before/after the 100 -> 101 transition, the log records:

- missing C:\private\100059C9\LocaleData\LocaleData.D01
- missing C:\private\100059C9\LocaleData\CommonData.D00
- StarterServer SVC miss 0xE3
- SA response func 0x64 succeeds
- transition 100 -> 101 succeeds
- SAServer IPC 0x67 is unimplemented
- ailaunch.exe is then spawned

These are candidate boundaries only. B62 does not prove which one prevents the
later 101 -> 102 transition.

The SVC 0xE3 miss occurs before state 101 and StarterServer continues to set
101, so it is not an immediate fatal boundary.

The single unimplemented SAServer IPC 0x67 occurs immediately after state 101
and is a stronger next diagnostic target, but caller/ABI/result handling must be
captured before changing behavior.

## Later Starter behavior

StarterServer receives additional rendezvous/cancel activity, including a
rendezvous at 22:14:25.086, but never publishes another global-state value.

## Visual/renderer state

Natural Splash -> Startup handoff still occurs at frame 173. Startup becomes
focus and the known white waiting-frame redraw store is replayed.

No evidence in B62 indicates a new graphical blocker.

## Exit stability

B61 wipeout protection remains active.

During final exit:
- [GSTORE_WIPEOUT_GUARD] fires on retained FBS refs including
  font_refs=1 bitmap_refs=4;
- os_join_done is reached;
- graphics_join_done is reached;
- state_reset_done is reached;
- shutdown_done / normal_restart_begin are reached.

No teardown regression is observed.

## Decision

Next diagnostic should focus on the first unimplemented dependency around
StartingCriticalApps=101, without forcing state progression.

Recommended B63:

- exact SAServer opcode 0x67 ABI/caller probe;
- preserve current KErrNotSupported behavior;
- correlate its requester with StarterServer / critical-app startup;
- keep SVC 0xE3 unchanged but retain its existing diagnostic evidence.

Do not inject state 102/103/104 and do not force StartAnimations=2.
