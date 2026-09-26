# NATIVEBOOT2 B35 EIKLEAVECALLER1 — DEVICE1

Date: 2026-09-22
Branch tested: nativeboot2-current
B35 authoritative IPA-producing HEAD: 71f5568e60d8823a39d4a1f29ff093034e3b99d9
B35 authoritative GREEN run: 35700638503
B35 authoritative GREEN job: 106657548399
Baseline functional milestone: B34 FOCUSMUTEXSPLIT1 (DEVICE-VALIDATED)

## Device logs

- EKA2L1(20260922-121848).log
- EKA2L1_Persistent(20260922-121914).log
- EKA2L1_TakeThis(20260922-121929).log

## Result

B35 is DEVICE-OBSERVED and diagnostically successful.

The B35 EIKCALLSITE/EIKCODE16 instrumentation resolves the stable first ws32 frame seen on the repeated eiksrvs/EikAppUiServerThread Leave(-3) path:

- module: Z:\\Sys\\Bin\\ws32.dll
- base: 0x80659048
- offset: 0x0000370A
- raw return: 0x8065C753
- Thumb: 1
- nearest export ordinal: 206
- nearest export address: 0x8065C74B
- delta: +0x8

The same ws32 callsite repeats across the captured Leave(-3) cycles.

The bounded code window around this export is stable:

- 0x8065C74A: 0xB510
- 0x8065C74C: 0x225D
- 0x8065C74E: 0xF7FC
- 0x8065C750: 0xFF3D
- 0x8065C752: 0xBD10

The immediate 0x225D halfword loads 0x5D into r2 immediately before the following Thumb call pair, making ws32 IPC/service number 0x5D the next narrow boundary to trace.

The avkonfep frames remain stable at:

- avkonfep.dll + 0xF104
- avkonfep.dll + 0xF16E
- avkonfep.dll + 0x03D8

The B35 runtime export-table probe cannot assign a useful nearest ordinal for these avkonfep locations (ordinal=0 / no mapped nearest export), so the ws32 export is currently the stronger actionable boundary.

## Exit Emulator regression

B34 host-exit behavior remains healthy under B35.

Observed normal device exit includes:

- exit_requested
- shutdown_begin
- shutdown_threads_begin
- os_join_begin
- os_join_done
- graphics_join_done
- shutdown_threads_done
- state_reset_done
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

One captured exit reaches os_join_begin at 18:27:02.474 and os_join_done at 18:27:02.496, about 22 ms later.

Therefore B35 did not regress the B34 focus-callback mutex split or B26 iOS exit choreography.

## B36 decision correction

A first B36 hypothesis targeted ws32 SetNonFading completion, based on the ordinal-206/0x5D trace.

The RED contract currently present as test_nativeboot2_b36_wservnonfading1.py checks whether set_non_fading() contains:

    context.complete(epoc::error_none);

However, FASTBUILD1 run 35728463388 passes this contract on the reconstructed B35 baseline without any B36 apply script.

Current repo state at that run:

- HEAD: 8cde7e8cb06eb2404acc78277e6a6dc50b44b832
- run: 35728463388
- job: 106747812846
- conclusion: SUCCESS
- IPA packaged/uploaded
- no apply_nativeboot2_b36_wservnonfading1.py exists
- manifest contains only the B36 regression contract, not a B36 apply row

Conclusion:

The artifact from run 35728463388 is NOT a functional B36 candidate and should not be device-tested as B36. The simple "add KErrNone completion to set_non_fading" hypothesis is already satisfied by the reconstructed baseline and therefore cannot explain the remaining Leave(-3) by itself.

Next work must trace the ws32 opcode/service 0x5D dispatch/completion path and determine where KErrCancel (-3) is introduced or propagated despite the existing set_non_fading completion. Do not batch unrelated SVC/FEP changes.

## Preserved invariants

Keep unchanged:

- firmware SYSSTART ownership
- stock Nokia avkonfep.dll / touchscreen FEP
- B34 focus_callback_mutex split
- B26 iOS Exit Emulator choreography
- B20-B35 compatibility chain
- native fbserv
- NOJAVA
- MANIC3
- EPOC94 0xAA unmapped
- EPOC94 0xAB = message_construct
- EPOC94 0xAC = message_kill
