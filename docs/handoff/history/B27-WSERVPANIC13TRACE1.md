# B27 WSERVPANIC13TRACE1 — Device Evidence Snapshot

Date: 2026-09-21
Branch: nativeboot2-b27-wservpanic13trace1
Device-tested code HEAD: b1b1ed38a5481a73b20df252ee1048929f8aad6b

## Build

Workflow run: 35600785179
Status: SUCCESS

IPA artifact:
- name: EKA2L1-NATIVEBOOT2-B27-WSERVPANIC13TRACE1-NOJAVA-MANIC3-IPA
- artifact ID: 10639335895
- artifact ZIP digest: sha256:305aae4ce51cd14b9afd3938cfc3cef2ae4f42da7d214e5f28016da0e6cbe046

Unsigned IPA:
- file: EKA2L1-NATIVEBOOT2-B27-WSERVPANIC13TRACE1-NOJAVA-MANIC3-unsigned.ipa
- SHA-256: 37dd617b50a383b1a473da04df46c162ff878d1cb9d9897f9dc565420206d67f

Audit artifact:
- artifact ID: 10639365871
- artifact ZIP digest: sha256:1ce2e34a320772c9e198ca79b7bb32a8226d835bb5245688eb8b7b4e755ec7e8

Build regression:
- B27 WSERVPANIC13TRACE1 contract PASS
- B26 IOSLIBRARYEXIT1 PASS
- B25 FBSSHAREDHEAP1 PASS
- B20-B24 regression chain PASS
- iOS build/package PASS

## Device input

User supplied:
- Log b27.zip
  - EKA2L1.log
  - EKA2L1_Persistent.log
  - EKA2L1_TakeThis.log

## B27 result: exact Wserv failure captured

Immediately before the Window Server startup panic:

1. Native !Windowserver registration succeeds.
2. B25 FBS handoff succeeds.
3. Missing EPOC 9.4 executive calls appear:
   - SVC 0x48
   - SVC 0x4A
4. EKDATA.DLL loads successfully:
   - UID3 = 0x100039E0
   - runtime code = 0x807ABDF8
5. Missing SVC 0x63 occurs:
   - pc = 0x80297F64
   - lr = 0x802A1CFD
   - r0 = 0x400F0007
6. A leave is immediately started/trapped.
7. Wserv reports:
   - EWsPanicFailedToInitialise
   - wstop.cpp line 967
8. B27 captures self-panic:
   - category = WSERV-INTERNAL
   - reason = 13
   - PC = 0x80298584
   - LR = 0x802A3A39
   - SP = 0x00503C70

B27 stack candidates resolve into ewsrv.exe:
- ewsrv + 0x1D4C8
- ewsrv + 0x159B2
- ewsrv + 0x1D938
- ewsrv + 0x159FC

Domino 13 on NearlyIdleKickBack follows the Wserv panic and is treated as downstream.

## Exact Symbian source meaning

Public Symbian Window Server source defines:
- EWsPanicFailedToInitialise = 13

In non-NGA WSTOP.CPP, E32Main does:
- TRAP(err, CWsTop::RunServerL())
- if err != KErrNone: WS_PANIC_ALWAYS(EWsPanicFailedToInitialise)

Therefore WSERV-INTERNAL 13 here means CWsTop::RunServerL / InitStaticsL left during Window Server initialization.

Relevant public source:
- SymbianSource/oss.FCL.sf.os.graphics
- commit ff133bc50e6158bfb08cc093b0f0055321dcde99
- windowing/windowserver/nonnga/SERVER/WSTOP.CPP
- windowing/windowserver/SERVER/openwfc/panics.h

## SVC 0x63 identification

Public Symbian executive declarations show:
- Exec::LibraryType(TInt, TUidType&) -> EExecLibraryType
- generic executive enum places EExecLibraryType immediately before EExecProcessType.

EKA2L1's frozen EPOC 9.4 SVC table:
- has ProcessType at 0x64
- does not register 0x63

This identifies B27's missing SVC 0x63 as the EPOC 9.4 LibraryType executive call.

Runtime ordering independently supports this:
- EKDATA.DLL is loaded
- SVC 0x63 is invoked with r0 = 0x400F0007, a library handle-shaped value
- the leave begins immediately after the missing call.

Primary B28 candidate:
NATIVEBOOT2-B28-WSERVLIBTYPE1

Implement the EPOC 9.4 LibraryType ABI at SVC 0x63 and return the loaded RLibrary UID type.

Do not batch-fix other missing SVCs yet.

## Other missing Wserv SVCs

B27 also sees:
- 0x50 during early Wserv E32Main startup. Source ordering and executive tables identify this as WsRegisterThread.
- 0x48 and 0x4A later during startup. They align with Window Server event-hook executive calls (CaptureEventHook / RequestEvent in the corresponding executive sequence).

They remain candidates, but neither is immediately followed by the startup leave. SVC 0x63 is the first narrow fix target because the observed causal chain is:
EKDATA load -> SVCMISS 0x63 -> Leave -> EWsPanicFailedToInitialise.

## Preserved validation

B25 still reports:
- shared_guest_owned=true
- shared_renamed=true
- large_guest_owned=true
- large_renamed=true
- FBS_SHARED_HEAP_READY success

B26 exit path still completes:
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

## Next step

For B28:
1. Add a RED contract requiring EPOC 9.4 SVC 0x63 LibraryType.
2. Implement only correct LibraryType ABI/semantics.
3. Add marker:
   [NBOOT2][WSERV_LIBRARY_TYPE]
   with handle + UID1/UID2/UID3.
4. Preserve B20-B27 regression tests.
5. Device-test whether:
   - SVCMISS 0x63 disappears;
   - EWsPanicFailedToInitialise disappears or moves later;
   - firmware advances beyond NOKIA splash.
