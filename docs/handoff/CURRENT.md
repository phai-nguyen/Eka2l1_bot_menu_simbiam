# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-21
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active branch: nativeboot2-b25-fbssharedheap1
Current HEAD: d930f4b3e958642e2e5821a15eadded903c9d722

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, keeping firmware SYSSTART as boot owner while using targeted HLE compatibility fixes where required.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

B25 = NATIVEBOOT2-B25-FBSSHAREDHEAP1

Build workflow:
.github/workflows/build-ios-nativeboot2-b25-fbssharedheap1-nojava-manic3.yml

Apply script:
apply_nativeboot2_b25_fbssharedheap1.py

Contract:
test_nativeboot2_b25_fbssharedheap1.py

Successful build run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35591745431

IPA artifact:
EKA2L1-NATIVEBOOT2-B25-FBSSHAREDHEAP1-NOJAVA-MANIC3-IPA

Artifact ID:
10634908262

Unsigned IPA SHA-256:
069676f3e3aa4badd31a53043bc808464fa7ddd54f76ac893e8aa74766c6daff

## TDD evidence

RED run:
35581550088

RED result:
B20-B24 passed, B25 failed because the shared-heap handoff implementation was absent.

GREEN/build run:
35591745431

GREEN result:
- B25 contract PASS
- B24 regression PASS
- B23 regression PASS
- B22 regression PASS
- B21 regression PASS
- B20 regression PASS
- iOS build PASS
- IPA packaging PASS
- IPA artifact upload PASS

The temporary RED workflow was removed after proof.

## Root cause established from B24 logs

Native firmware fbserv created canonical global chunks:

- FbsSharedChunk @ 0x40200000
- FbsLargeChunk @ 0x44200000

Later, HLE FBS created another canonical FbsSharedChunk:

- HLE FbsSharedChunk @ 0x54200000

HLE returned a CBitmapFont offset:

- address_offset = 0x1598
- HLE object address = 0x54201598

The client reconstructed the pointer from the canonical global chunk it had opened:

0x40200000 + 0x1598 = 0x40201598

This exactly matched AknCapServer r0 at the observed crash:

- KERN-EXEC 3
- PC = 0x000000F0
- r0 = 0x40201598

B24 independently proved CBitmapFont ordinal-97 relocation was correct, so the vtable relocation itself was ruled out as the primary cause.

## B25 behavior

B25 modifies fbs_server::initialize_server() only for the FBS shared-heap handoff.

Before HLE creates its canonical FBS chunks:

1. Look up existing FbsSharedChunk and FbsLargeChunk.
2. If an existing chunk is guest-process-owned, rename it:
   - FbsSharedChunk -> FbsSharedChunk.NativeBoot
   - FbsLargeChunk -> FbsLargeChunk.NativeBoot
3. Do not terminate or suppress native fbserv.
4. Preserve native fbserv chunk handles.
5. Let HLE FBS create canonical FbsSharedChunk/FbsLargeChunk as before.
6. Keep HLE chunk allocators unchanged.
7. Do not adopt the native RHeap into HLE.

New runtime markers:

[NBOOT2][FBS_SHARED_HEAP_HANDOFF]
[NBOOT2][FBS_SHARED_HEAP_READY]

## Invariants preserved

B25 must preserve:

- firmware SYSSTART boot ownership
- native fbserv startup/rendezvous
- B24 CBitmapFont vtable diagnostics
- B23 72-byte TFontSpec v2 ABI handling
- B22 system default typeface handling
- B21 font alias handling
- B20 Central Repository ResetAll
- B19 SA language ABI handling
- EMUHUB1 frontend behavior
- NOJAVA
- MANIC3

B25 intentionally does NOT change:

- CBitmapFont vtable contents
- ordinal-97 relocation rules
- TFontSpec decoding beyond B23
- font matcher behavior
- AppServer behavior
- startup ownership
- native fbserv loader policy

## Previous milestones

Relevant chain:

- B19: SALANGABI1
- B20: CENRESETALL1
- B21: FBSFONTALIAS1
- B22: FBSDEFAULTTYPEFACE1
- B23: FBSFONTSPECV2ABI1
- B24: FBSVTABLEABI1
- B25: FBSSHAREDHEAP1

B24 was diagnostic-only for CBitmapFont vtable ABI and established that ordinal-97 relocation matched the canonical codeseg lookup.

## Device test required next

Install the B25 IPA on the iPhone and boot the Nokia 5800 firmware.

Collect full logs, especially:

- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_Persistent-prev.log
- EKA2L1_TakeThis.log

Key questions for B25 device evidence:

1. Are these markers present?
   - [NBOOT2][FBS_SHARED_HEAP_HANDOFF]
   - [NBOOT2][FBS_SHARED_HEAP_READY]

2. Does AknCapServer still terminate with:
   - KERN-EXEC 3
   - PC = 0x000000F0

3. Does r0 still equal:
   - 0x40201598

4. Does FBS_FONT_RETURN now correspond to the same canonical shared heap base seen by the client?

5. Does the boot progress farther into UI/AppServer after the FBS handoff?

## Interpretation rules for next log analysis

If r0 is no longer 0x40201598 and AknCapServer progresses:
- Treat B25 as validating the shared-heap collision hypothesis.
- Identify the next earliest non-downstream failure.

If r0 remains 0x40201598:
- Verify whether guest-owned chunk rename actually occurred.
- Check FBS_SHARED_HEAP_HANDOFF values.
- Check whether RFbsSession opened the chunk before rename and retained an already-open handle.

If AknCapServer crashes at a different PC/r0:
- Treat the new earliest fault as the next root-cause candidate.
- Do not assume B25 failed merely because boot is not complete.

## Known downstream symptoms from B24

These were considered likely cascades after FBS corruption and should not be treated as primary unless they occur before the FBS fault in new logs:

- sysap KERN-EXEC 3
- ailaunch failures
- invalid window handles
- AknIconPrecache2 SCDV panic

## Exit path

The emulator exit/restart path was already observed healthy in prior testing:

- exit_requested
- shutdown_begin
- shutdown_threads_begin
- flags_set
- request_exit
- core_wakeup
- os_join_begin
- os_join_done
- graphics_abort
- graphics_join_begin
- graphics_join_done
- shutdown_threads_done
- state_reset_begin
- state_reset_done
- shutdown_done
- normal_restart_begin
- normal_restart_done

Do not treat normal shutdown markers as a boot failure.

## Working rule for future versions

After each meaningful Bxx build/test:

1. Update docs/handoff/CURRENT.md with the new active branch, HEAD, build run, artifact, SHA, evidence, root cause, and next test.
2. Add a snapshot under docs/handoff/history/.
3. Keep only current, verified hypotheses as active.
4. Explicitly record hypotheses ruled out by device evidence.
5. Keep runtime marker names and exact fault registers where relevant.
6. Do not merge speculative fixes without a RED contract first.

## How to resume in a new ChatGPT conversation

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam and continue the Nokia 5800 NativeBoot project from the current branch. Use GitHub and analyze the newest device logs before making the next patch."

This file is the authoritative project handoff unless newer device evidence or a newer committed handoff supersedes it.
