# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-21
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active branch: nativeboot2-b27-wservpanic13trace1
Device-tested code HEAD: b1b1ed38a5481a73b20df252ee1048929f8aad6b

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, preserving firmware SYSSTART ownership and applying narrowly scoped compatibility fixes only after device evidence.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

B27 = NATIVEBOOT2-B27-WSERVPANIC13TRACE1

Branch:
nativeboot2-b27-wservpanic13trace1

Build workflow:
.github/workflows/build-ios-nativeboot2-b27-wservpanic13trace1-nojava-manic3.yml

Apply script:
apply_nativeboot2_b27_wservpanic13trace1.py

Contract:
test_nativeboot2_b27_wservpanic13trace1.py

Successful build run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35600785179

Unsigned IPA:
EKA2L1-NATIVEBOOT2-B27-WSERVPANIC13TRACE1-NOJAVA-MANIC3-unsigned.ipa

IPA SHA-256:
37dd617b50a383b1a473da04df46c162ff878d1cb9d9897f9dc565420206d67f

IPA artifact ID:
10639335895

Audit artifact ID:
10639365871

## Validated milestones

### B25 — FBSSHAREDHEAP1

DEVICE-VALIDATED.

B25 fixed the canonical native/HLE FBS global chunk collision.

Runtime markers remain healthy:
- [NBOOT2][FBS_SHARED_HEAP_HANDOFF]
- shared_guest_owned=true
- shared_renamed=true
- large_guest_owned=true
- large_renamed=true
- [NBOOT2][FBS_SHARED_HEAP_READY] success

The old AknCapServer crash:
- PC = 0x000000F0
- r0 = 0x40201598
- KERN-EXEC 3

is no longer the active blocker.

Firmware reaches the NOKIA splash.

### B26 — IOSLIBRARYEXIT1

DEVICE-VALIDATED.

The UIKit UICollectionView crash when choosing Exit Emulator is fixed.

Latest B27 device logs still show the safe exit/restart path:
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

Do not modify the B26 exit choreography unless new evidence requires it.

### B27 — WSERVPANIC13TRACE1

DEVICE-TESTED diagnostic milestone.

B27 captured the exact native Window Server failure.

Immediately before Wserv dies:

1. !Windowserver registration succeeds.
2. B25 FBS shared-heap handoff succeeds.
3. V5 SVCMISS 0x48 occurs.
4. V5 SVCMISS 0x4A occurs.
5. EKDATA.DLL loads:
   - UID3 = 0x100039E0
   - runtime code = 0x807ABDF8
6. V5 SVCMISS 0x63 occurs:
   - pc = 0x80297F64
   - lr = 0x802A1CFD
   - r0 = 0x400F0007
7. Leave starts immediately afterward.
8. Wserv reports:
   EWsPanicFailedToInitialise
9. Wserv self-panics:
   - category = WSERV-INTERNAL
   - reason = 13

B27 panic context:
- PC = 0x80298584
- LR = 0x802A3A39
- SP = 0x00503C70
- PC/LR resolve into euser.dll

ewsrv stack candidates:
- ewsrv.exe + 0x1D4C8
- ewsrv.exe + 0x159B2
- ewsrv.exe + 0x1D938
- ewsrv.exe + 0x159FC

NearlyIdleKickBack then panics with Domino 13. Treat Domino 13 as downstream of Wserv unless new evidence reverses ordering.

## Exact meaning of WSERV-INTERNAL 13

Public Symbian Window Server source defines:
EWsPanicFailedToInitialise = 13

In non-NGA WSTOP.CPP, E32Main traps CWsTop::RunServerL(); if that returns a leave/error, it panics with EWsPanicFailedToInitialise.

Therefore the active blocker is now localized:
CWsTop::RunServerL / InitStaticsL leaves during native Window Server initialization.

Reference source:
- SymbianSource/oss.FCL.sf.os.graphics
- commit ff133bc50e6158bfb08cc093b0f0055321dcde99
- windowing/windowserver/nonnga/SERVER/WSTOP.CPP
- windowing/windowserver/SERVER/openwfc/panics.h

## Identification of missing SVC 0x63

This is the strongest B27 result.

Symbian executive source declares:
Exec::LibraryType(TInt, TUidType&) -> EExecLibraryType

The EKA2L1 frozen EPOC 9.4 table has:
- ProcessType at SVC 0x64
- no SVC registration at 0x63

The corresponding executive ordering places LibraryType directly before ProcessType.

Runtime independently confirms the interpretation:
- EKDATA.DLL loads successfully.
- immediately after load, SVC 0x63 is called.
- r0 = 0x400F0007 is handle-shaped and is consistent with an RLibrary handle.
- EKA2L1 does not dispatch the call.
- a Symbian leave begins immediately afterward.
- RunServerL then emerges with an error and Wserv converts it to EWsPanicFailedToInitialise.

Primary root-cause candidate for the next patch:
missing EPOC 9.4 LibraryType executive ABI/semantics at SVC 0x63.

## Other missing Wserv executive calls

B27 also exposes:
- SVC 0x50 during Wserv E32Main startup. Runtime/source ordering strongly identifies this as WsRegisterThread.
- SVC 0x48 and 0x4A during InitStaticsL. They align with Window Server event-hook executive calls in the corresponding Symbian executive sequence.

These remain real compatibility gaps.

However, do NOT batch-fix them in the next build unless required.

The narrow causal sequence currently observed is:
EKDATA.DLL load
-> SVCMISS 0x63
-> leave
-> EWsPanicFailedToInitialise
-> WSERV-INTERNAL 13
-> Domino 13 downstream

## B28 proposed target

Name:
NATIVEBOOT2-B28-WSERVLIBTYPE1

Scope:
Implement the missing EPOC 9.4 LibraryType executive call at SVC 0x63 only.

Required behavior:
- ABI: LibraryType(handle, TUidType&)
- resolve the RLibrary/kernel library handle
- return UID1/UID2/UID3 of its loaded codeseg/library
- preserve error/invalid-handle behavior consistent with Symbian/EKA2L1 conventions
- add:
  [NBOOT2][WSERV_LIBRARY_TYPE]
  handle=...
  uid1=...
  uid2=...
  uid3=...
- no Wserv panic suppression
- no fake success
- no changes to 0x48/0x4A/0x50 in the same patch
- preserve B20-B27 regression chain

B28 success criteria on device:
1. EKDATA.DLL still loads.
2. SVCMISS 0x63 disappears.
3. [NBOOT2][WSERV_LIBRARY_TYPE] confirms the library UID type.
4. EWsPanicFailedToInitialise either disappears or moves to a later, newly observable cause.
5. Boot progresses beyond current NOKIA-splash blocker if 0x63 was the final initialization failure.

## Preserved invariants

Keep:
- firmware SYSSTART boot ownership
- native fbserv startup/rendezvous
- B25 FBS shared-heap handoff
- B24 vtable diagnostics
- B23 TFontSpec v2 ABI
- B22 default typeface
- B21 font aliases
- B20 Central Repository ResetAll
- B19 SA language ABI
- EMUHUB1
- B26 safe Exit Emulator path
- B27 Wserv diagnostic markers
- NOJAVA
- MANIC3

Do not reintroduce:
- host-driven SysStart/Menu startup ownership
- native fbserv suppression
- native FBS heap adoption
- Wserv panic suppression
- speculative multi-SVC fixes

## Milestone history

- B19: SALANGABI1
- B20: CENRESETALL1
- B21: FBSFONTALIAS1
- B22: FBSDEFAULTTYPEFACE1
- B23: FBSFONTSPECV2ABI1
- B24: FBSVTABLEABI1
- B25: FBSSHAREDHEAP1 — device validated
- B26: IOSLIBRARYEXIT1 — device validated
- B27: WSERVPANIC13TRACE1 — device trace isolated RunServerL initialization failure and SVC 0x63

Snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md
- docs/handoff/history/B27-WSERVPANIC13TRACE1.md

## How to resume

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam. Continue from B27. B25/B26 are device-validated. B27 shows EKDATA.DLL -> missing EPOC94 SVC 0x63 LibraryType -> leave -> EWsPanicFailedToInitialise. Validate and implement the narrow B28 WSERVLIBTYPE1 fix before touching other Wserv SVCs."

This file is authoritative unless newer committed device evidence supersedes it.
