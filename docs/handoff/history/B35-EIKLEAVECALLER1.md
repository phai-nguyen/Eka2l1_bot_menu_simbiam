# B35 EIKLEAVECALLER1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE LOG REQUIRED
Baseline: B34 FOCUSMUTEXSPLIT1 DEVICE-VALIDATED
Active branch: nativeboot2-current

## Why B35 exists

B34 closes the host Exit Emulator deadlock but intentionally does not change
the repeated guest UI failure.

B34 device evidence still shows 16 identical KErrCancel leaves in:
- process: eiksrvs[10003a4a]0001
- thread: EikAppUiServerThread
- leave: -3
- trap: 0x007001FC
- PC: euser.dll + 0x2EF4
- LR: euser.dll + 0x166E0

Every one of those B32 stack captures has the same four code candidates:
- ws32.dll + 0x370A
- avkonfep.dll + 0xF104
- avkonfep.dll + 0xF16E
- avkonfep.dll + 0x03D8

The first leave occurs immediately after stock AknFep initialization:
- AknFepUiAvkonPlugin.dll loads;
- z:\resource\fep\aknfep.r01 opens;
- CenRep 0x101F8780 opens;
- P&S 0x101F876e:0x4 attaches;
- CenRep 0x101F877C opens;
- CenRep 0x10282DF0 opens;
- User::Leave(-3) follows.

B33 completion probes do not identify the preceding KErrCancel source:
- EIKCANCEL_HLE: none;
- EIKCANCEL_LLE: unrelated AknIconSrv/CdlServer;
- eiksrvs EIKCANCEL_NOTIFY: post-fault cleanup.

## Stock Nokia FEP must remain

Upstream EKA2L1 includes a host-bridged replacement:
assets/patch/avkonfep_general.dll.

However, this project intentionally stopped that replacement at MENUUI30
STOCKFEP1 because the goal is the real Nokia 5800 touchscreen FEP/VKB.

MENUUI30 and later MENUUI31-36 device work proved:
- stock Nokia avkonfep.dll can run;
- the real Nokia touchscreen keyboard appears;
- PenInput layout activation reaches the guest stack;
- later patches improved raw input, KeySound, asynchronous raw-event delivery,
  and focus.

NativeBoot is descended from the MENUUI36 baseline. B35 therefore does NOT
restore avkonfep_general.dll and does not replace stock FEP behavior.

## B35 diagnostic design

B35 extends only the existing B32 KErrCancel stack candidate logger in
src/emu/kernel/src/svc.cpp.

New markers:
- [NBOOT2][EIKCALLSITE]
- [NBOOT2][EIKCODE16]

For every B32 code candidate, EIKCALLSITE reports:
- stack index;
- raw return address;
- module/base/offset;
- Thumb bit;
- nearest preceding code export ordinal from the exact relocated codeseg;
- nearest export address;
- delta from that export to the candidate.

It uses codeseg::get_export_table(process*) from the running guest itself.
No RM-356 symbol map or module/offset hardcode is required.

EIKCODE16 dumps a bounded code window:
- relative_halfword -8 through +4;
- guest address;
- 16-bit code halfword.

For Thumb return addresses this captures the call instruction immediately
before the return site and enough surrounding context to decode the caller.

## Scope

B35 is diagnostic-only.

It does NOT change:
- stock Nokia FEP;
- WindowServer behavior;
- CenRep behavior;
- P&S behavior;
- IPC completion;
- request signaling;
- Leave/trap semantics;
- guest exception behavior;
- B34 focus_callback_mutex;
- B26 Exit Emulator choreography;
- SVC registration.

EPOC94 remains:
- 0xAA unmapped
- 0xAB message_construct
- 0xAC message_kill

## TDD RED

Original RED:
- run: 35700027336
- B28 -> B34 reconstruction: PASS
- expected B35 failure:
  missing [NBOOT2][EIKCALLSITE]

After narrowing the no-hardcode contract to the B35 block, RED was re-proven:
- run: 35700619104
- job: 106657485855
- B28 -> B34 reconstruction: PASS
- expected B35 failure:
  NATIVEBOOT2-B35-EIKLEAVECALLER1-TEST: FAIL:
  missing in B35 callsite marker: [NBOOT2][EIKCALLSITE]

## GREEN

Authoritative GREEN:
- run: 35700638503
- job: 106657548399
- HEAD: 71f5568e60d8823a39d4a1f29ff093034e3b99d9

Verification:
- FASTBUILD1 manifest VALID
- B35 apply PASS
- B35 contract PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- Mach-O contains [NBOOT2][EIKCALLSITE]
- Mach-O contains [NBOOT2][EIKCODE16]
- IPA package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap restore: 30 s
- patch/regression: 1 s
- CMake build: 82 s
- package: 4 s
- total: 143 s
- compile requests: 50
- cache hits: 49
- cache misses: 1
- hit rate: 98%
- actual compilations: 1
- compilation failures: 0

Unsigned IPA SHA-256:
e4468751091b6abe03004297549a718075f49aa9c0ae965ed83436a2948831f1

IPA artifact:
- ID: 10681812270
- ZIP digest:
  sha256:65076ba3eece660a97733adbee3221b8a36c625de38206a07ad30f2a8b04e510
- expires: 2026-10-06

Audit artifact:
- ID: 10682081833
- ZIP digest:
  sha256:08db656b6e72a5d88571d9a5b350fd4e02908ffe5e531d45df5745909371dce8
- expires: 2026-10-06

The downloaded IPA was independently hashed after extraction and matches the
CI SHA-256 exactly.

## Device test

B35 is not a functional fix and should not be promoted as an immutable
functional milestone.

Test:
1. sign/install B35;
2. boot the Nokia 5800 path exactly as B34;
3. allow the repeated eiksrvs/AknFep failure to occur;
4. use Thoát Emulator normally (B34 should remain healthy);
5. send EKA2L1.log, EKA2L1_Persistent.log, and EKA2L1_TakeThis.log.

Primary B35 acceptance is diagnostic:
- EIKCALLSITE must appear for the stable ws32/avkonfep stack candidates;
- EIKCODE16 must provide mapped halfwords around them;
- nearest export ordinal + code window should identify the immediate guest API
  or call instruction responsible for the KErrCancel leave path.

Only after that evidence should a B36 functional compatibility change be
selected.
