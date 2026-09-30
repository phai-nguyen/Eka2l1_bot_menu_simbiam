# NATIVEBOOT2 B59 GSTOREEXITGUARD1 — DEVICE1

Date: 2026-09-24
Status: DEVICE-PASS FOR CLEAN EXIT; GUARD MARKER NOT OBSERVED

## Inputs

- ScreenRecording_09-24-2026 19-06-25_1.mp4
- EKA2L1_Persistent(20260924-121326).log
- EKA2L1(20260924-121326).log
- EKA2L1_Persistent-prev(1).log
- EKA2L1_TakeThis(20260924-121335).log

## Device result

User ran through the normal SIM-present path to the stable Startup white
surface, opened the Emulator menu, selected "Thoát Emulator", and returned
normally without the iOS process crashing.

The recording is ~340.8 s and reproduces the same visual boot checkpoint:
NOKIA -> white Startup surface. Exit near the end returns normally.

Logs complete the shutdown path through:

- os_join_done
- graphics_abort
- graphics_join_begin
- graphics_join_done
- shutdown_threads_done
- state_reset_begin
- state_reset_done
- shutdown_done
- normal_restart_begin

No new Apple .ips crash report was produced in this device test.

## B59 guard observation

No [NBOOT2][GSTORE_EXIT_GUARD] marker appears in the supplied logs.

Therefore:

- B59 satisfies the practical device acceptance condition: clean exit.
- This run does not prove that the guard branch itself executed.
- Do not claim a uniquely proven causal fix from this single run; the prior B58
  crash may have involved timing-sensitive teardown ordering.

Keep B59 in the current chain because it is narrow, build-validated, and this
device run exits cleanly.

## Boot-state result

B58 state tracing remains unchanged:

0x100058F4:1
before=0 requested=1 after=1 set_result=1

No category/key request for StartAnimations=2 is observed.

Next selected diagnostic: B60 STARTUPSTATEWRITER1, adding handle-based integer
writer coverage while preserving B58 category/key tracing.
