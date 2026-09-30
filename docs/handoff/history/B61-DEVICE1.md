# NATIVEBOOT2 B61 GSTOREWIPEOUT2 — DEVICE1

Date: 2026-09-24
Status: DEVICE-PASS FOR CLEAN EXIT; WIPEOUT GUARD CONFIRMED; NO NEW BOOT CHECKPOINT
Install mode: CLEAN INSTALL (B60 removed / not installed over B60)

## Inputs

- EKA2L1_Persistent(20260924-144239).log
- EKA2L1(20260924-144239).log
- EKA2L1_Persistent-prev(2).log
- EKA2L1_TakeThis(20260924-144242).log
- ScreenRecording_09-24-2026 21-32-44_1.mp4

## Visual result

Video duration: ~427.6 s.

Observed path:

- emulator/device startup UI
- black
- NOKIA splash on white
- natural Splash -> Startup handoff
- stable blank-white Startup surface
- user opens Emulator/game menu near the end
- user selects "Thoát Emulator"
- returns normally to EKA2L1 UI

No iOS process crash occurs.

No Nokia hands/welcome animation, RTC UI, or S60 Idle becomes visible before exit.
Therefore B61 does not add a new Nokia boot visual checkpoint.

## Startup-state result

Startup property remains:

0x100058F4:1
before=0 requested=1 after=1 set_result=1

No [NBOOT2][STARTUP_STATE_HANDLE] event targets this property.
No requested=2 / after=2 / StartAnimations marker appears.

Thus B61 preserves the B60 diagnostic conclusion:
StartAnimations=2 is not being published through either observed integer P&S
writer path.

## Natural handoff

At 21:35:45.551-552:

- focus becomes Startup group id 63
- TRANSITION_CLEAR frame=173
- STARTUP_REPLAY frame=173
- Startup full-screen canvas 0x00807AA8 is replayed

Stored Startup content remains the same B56/B57 waiting frame.

Startup subsequently requests TfxServer and receives KErrNotFound, matching
earlier builds.

## B61 teardown guard — confirmed on device

At final exit beginning 21:39:49.466, B61 enters kernel wipeout and
[NBOOT2][GSTORE_WIPEOUT_GUARD] fires 27 times.

Crucially, some guarded segments contain retained FBS objects, including:

- font_refs=0 bitmap_refs=1
- font_refs=1 bitmap_refs=4

with action:

SKIP_ALL_FBS_DEREF_WIPEOUT

This directly exercises the B61 shutdown-only protection before retained FBS
objects are touched.

Shutdown then completes:

- os_join_done
- graphics_join_done
- shutdown_threads_done
- state_reset_done
- shutdown_done
- normal_restart_begin

No Apple .ips crash is produced.

Because this was a clean install and the B61 marker actually fired on segments
with retained FBS references, the device evidence for B61's teardown fix is
substantially stronger than B59's timing-dependent clean exit.

## Host debug marker

B61 has 176 DIRECTSCREEN_PRESENT events. Final present is frame 175 / phase 3,
so the rotating host diagnostic square freezes in the phase-3/green state.

This is host overlay state only, not Nokia boot progress.

## Decision

B61 teardown track: PASS on DEVICE1.

Next boot work should no longer target graphics or P&S setter coverage.
Move upstream to the System Starter / startup-policy / command-list path that
should publish KPSStartupAppState StartAnimations=2 on the normal SIM-present
RM-356 path.

Keep B61 wipeout protection in the chain while continuing boot diagnostics.
