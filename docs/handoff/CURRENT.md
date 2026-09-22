# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-23
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active development branch: nativeboot2-current
Latest FASTBUILD1 CI implementation commit: c57838dbbe9f8b0d66fe5c5b79505eafa7b10da3
Latest immutable functional milestone: B41 WSERVMESSAGEWINEXIT1
Latest immutable functional code HEAD: b43e59696d313da97c8845a1a20e78d9b6c762d7
Latest immutable functional branch: nativeboot2-b41-wservmessagewinexit1
Latest device-validated functional milestone: B41 WSERVMESSAGEWINEXIT1
Latest device snapshot: docs/handoff/history/B41-DEVICE1.md
B40 status: DEVICE-VALIDATED — Loader PDD root cause fixed; !EikAppUiServer registers and B39 AV family is gone
B41 status: DEVICE-VALIDATED — Thoát Emulator host crash fixed
B42 status: BUILD-VALIDATED; DEVICE TEST REQUIRED — diagnostic-only SAServer 0x2000000A HWRM ABI probe
FASTBUILD1 status: PROMOTED

## Objective

Boot Nokia 5800 RM-356 firmware as faithfully as possible inside EKA2L1 on iOS, preserving firmware SYSSTART ownership and adding narrowly scoped compatibility fixes only after device evidence.

Primary device-test environment:
- iPhone 12 Pro Max
- iOS 18.7
- Nokia 5800 RM-356 firmware
- Firmware UI language: Vietnamese

## Current baseline

Latest device-validated functional milestone:
B34 = NATIVEBOOT2-B34-FOCUSMUTEXSPLIT1

Immutable B34 branch:
nativeboot2-b34-focusmutexsplit1

Immutable B34 functional commit:
24001e3306070fab2145bc1a4dd326a9fa83587d

Previous immutable functional milestone:
B31 = NATIVEBOOT2-B31-SCHEDREADYMM1

Previous immutable B31 branch:
nativeboot2-b31-schedreadymm1

Previous immutable B31 functional commit:
6ccdd5c1b9101124981315322af5002dac057edc

Latest device-observed diagnostic milestone:
B32 = EIKSRVFAULTDIAG1

B32 device result:
- B30 rooted EiksrvUi load remains healthy;
- B31 stale-ready scheduler guard remains healthy;
- no native host switch_context crash;
- all 16 EikAppUiServerThread Leave(-3) events share the same AknFep stack signature;
- first repeated causal family is AknFep -> User::Leave(KErrCancel) -> euser null write at 0x10 -> KERN-EXEC 3;
- SVC 0xE3 is owned by SYSSTART, not eiksrvs;
- the one eiksrvs SVC 0x2D occurs ~32 seconds before the first access violation and is not selected as causal.

Full B32 device snapshot:
docs/handoff/history/B32-DEVICE1.md

Active device evidence:
B33 EIKCANCELORIGIN1

B33 status:
DEVICE-OBSERVED; COMPLETION-ORIGIN PROBE NEGATIVE; HOST EXIT SELF-DEADLOCK ROOT CAUSE NOW PROVEN

B33 device result:
- EIKCANCEL_HLE: none;
- EIKCANCEL_LLE: only unrelated AknIconSrv/CdlServer KErrCancel completions;
- eiksrvs EIKCANCEL_NOTIFY occurs after EIKFAULT_AV -> KERN-EXEC 3 and is post-fault cleanup;
- the immediate source of AknFep User::Leave(-3) remains unresolved;
- Exit Emulator is accepted but stalls at BRIDGE_EXIT_PHASE os_join_begin;
- the user manually swiped the already-hung app to the iOS Home Screen; B33 did NOT spontaneously crash/eject itself to Home Screen;
- the later FRONTBOARD 0x8BADF00D report reflects the hung app failing to complete lifecycle/background work after that user action;
- B33 reconstructed source proves the Symbian OS thread self-deadlocks on screen_mutex during Wserv teardown.

Exact B33 host deadlock:
window_server_client::~window_server_client()
-> lock scr->screen_mutex
-> objects.clear()
-> window_group::~window_group()
-> screen::update_focus()
-> screen::fire_focus_change_callbacks()
-> lock the same non-recursive screen_mutex again.

Full B33 build snapshot:
docs/handoff/history/B33-EIKCANCELORIGIN1.md

Full corrected B33 device snapshot:
docs/handoff/history/B33-DEVICE1.md

Active functional candidate:
B34 FOCUSMUTEXSPLIT1

Status:
DEVICE-VALIDATED

B34 device result:
- user-triggered Exit Emulator at 12:54:31 reaches os_join_begin at 12:54:31.868;
- os_join_done follows at 12:54:31.891, about 23 ms later;
- shutdown_threads_done, state_reset_done and shutdown_done all complete;
- normal_restart_begin completes;
- normal_restart_done has_device=1 appears at 12:54:32.055;
- therefore the B33 screen_mutex self-deadlock is removed on device;
- no user Home Screen swipe was used to obtain this success.

B34 scope:
- keep std::mutex screen_mutex unchanged;
- add dedicated std::mutex focus_callback_mutex;
- move only fire/add/remove_focus_change_callback() to the dedicated mutex;
- keep Wserv outer teardown locking and objects.clear() unchanged;
- keep redraw/mode callback locking at B33 behavior;
- keep B26 iOS exit choreography unchanged;
- keep all guest/SVC/FEP/loader/scheduler/FBS/CenRep behavior unchanged.

Upstream narrow reference:
EKA2L1 commit 2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d

B34 apply script:
apply_nativeboot2_b34_focusmutexsplit1.py

B34 contract:
test_nativeboot2_b34_focusmutexsplit1.py

TDD RED:
- run: 35691246288
- B28 -> B33 reconstruction PASS
- expected failure:
  missing in screen.h dedicated focus callback mutex: std::mutex focus_callback_mutex;

Authoritative B34 GREEN:
- run: 35691395487
- job: 106628955424
- run HEAD: 24001e3306070fab2145bc1a4dd326a9fa83587d
- functional patch script commit: b332286861becc205de491a67bdea68abb54d441
- manifest commit: b1ac9fd243f58b257a9ee581294a3271f2d6c383
- FASTBUILD1 manifest VALID
- B34 FOCUSMUTEXSPLIT1 PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- packaged Mach-O contains [NBOOT2][FOCUS_MUTEX_SPLIT]
- IPA package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

B34 FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap restore: 35 s
- patch/regression: 1 s
- CMake build: 25 s
- package: 3 s
- total: 83 s
- compile requests: 50
- cache hits: 50
- cache misses: 0
- hit rate: 100%
- compilation failures: 0

B34 IPA SHA-256:
486ed148c18689b9582988df1e30616ab4bb40c18070a7e554078161d20c4c5c

IPA artifact:
- ID: 10679545002
- ZIP digest: sha256:f16a1ba31c6a72ba47ea157a60768ac6ebcc3599bb2e8cc25b286c6278bdd150
- expires: 2026-10-06

Audit artifact:
- ID: 10677634965
- ZIP digest: sha256:3db7b24c1d3d5ff9cd92572ffcdf4bb50afb57069183a8ff6f646cf3b69bbc48
- expires: 2026-10-06

Full B34 snapshot:
docs/handoff/history/B34-FOCUSMUTEXSPLIT1.md

Device validation:
PASSED. Full snapshot:
docs/handoff/history/B34-DEVICE1.md

The B34 host Exit Emulator blocker is closed. Keep the unresolved guest AknFep Leave(-3) investigation separate.


## Active diagnostic candidate — B35 EIKLEAVECALLER1

Status:
DEVICE-OBSERVED; DIAGNOSTIC SUCCESS; B36 FUNCTIONAL FIX NOT YET SELECTED

B35 keeps B34 unchanged and targets only the unresolved guest path:
AknFep -> User::Leave(KErrCancel/-3) -> euser null write 0x10 -> KERN-EXEC 3.

B34 device logs show the same four code candidates on all 16 leaves:
- ws32.dll + 0x370A
- avkonfep.dll + 0xF104
- avkonfep.dll + 0xF16E
- avkonfep.dll + 0x03D8

B35 does NOT restore EKA2L1 avkonfep_general.dll. NativeBoot intentionally inherits MENUUI30 STOCKFEP1/MENUUI36 so the real Nokia 5800 Avkon FEP and touchscreen keyboard remain the guest implementation.

New B35 markers:
- [NBOOT2][EIKCALLSITE]
- [NBOOT2][EIKCODE16]

EIKCALLSITE resolves each existing B32 code candidate against the exact running codeseg export table and logs:
- module/base/offset
- Thumb state
- nearest export ordinal/address
- delta from export to candidate

EIKCODE16 dumps a bounded guest halfword window around each candidate return address so the Thumb call immediately preceding the return can be decoded.

B35 is diagnostic-only:
- Leave/trap behavior unchanged
- IPC completion unchanged
- stock FEP unchanged
- WindowServer unchanged
- CentralRepository/P&S unchanged
- B34 focus mutex split unchanged
- EPOC94 0xAA unmapped, 0xAB message_construct, 0xAC message_kill preserved

TDD RED (re-proven after contract-scope correction):
- run: 35700619104
- job: 106657485855
- B28 -> B34 reconstruction PASS
- expected failure: missing [NBOOT2][EIKCALLSITE]

Authoritative GREEN:
- run: 35700638503
- job: 106657548399
- IPA-producing HEAD: 71f5568e60d8823a39d4a1f29ff093034e3b99d9
- FASTBUILD1 manifest VALID
- B35 apply PASS
- B35 contract PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- Mach-O contains [NBOOT2][EIKCALLSITE]
- Mach-O contains [NBOOT2][EIKCODE16]
- NOJAVA preserved
- MANIC3 preserved

B35 FASTBUILD1:
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

B35 IPA SHA-256:
e4468751091b6abe03004297549a718075f49aa9c0ae965ed83436a2948831f1

IPA artifact:
- ID: 10681812270
- ZIP digest: sha256:65076ba3eece660a97733adbee3221b8a36c625de38206a07ad30f2a8b04e510
- expires: 2026-10-06

Audit artifact:
- ID: 10682081833
- ZIP digest: sha256:08db656b6e72a5d88571d9a5b350fd4e02908ffe5e531d45df5745909371dce8
- expires: 2026-10-06

Full snapshot:
docs/handoff/history/B35-EIKLEAVECALLER1.md

B35 device result:
- EIKCALLSITE/EIKCODE16 succeeded on device;
- the stable ws32.dll + 0x370A frame resolves to nearest export ordinal 206 at 0x8065C74B, delta +0x8;
- the code window is stable and contains 0x225D immediately before the following Thumb call pair, selecting ws32 IPC/service number 0x5D as the next narrow boundary to trace;
- avkonfep.dll + 0xF104 / +0xF16E / +0x03D8 remain stable but do not resolve to a useful nearest export ordinal in the runtime export table;
- B34/B26 Exit Emulator behavior remains healthy: os_join_begin -> os_join_done -> shutdown_done -> normal_restart_done has_device=1;
- full device snapshot: docs/handoff/history/B35-DEVICE1.md.

B36 correction:
- test_nativeboot2_b36_wservnonfading1.py was introduced to test a SetNonFading completion hypothesis;
- run 35728463388 / job 106747812846 passes that contract on the reconstructed B35 baseline without any B36 apply script;
- apply_nativeboot2_b36_wservnonfading1.py does not exist;
- therefore the IPA from run 35728463388 is NOT a functional B36 candidate and should not be device-tested as B36;
- the next step is to trace the ws32 opcode/service 0x5D dispatch/completion path and identify where KErrCancel (-3) is introduced or propagated despite the existing set_non_fading completion.


## Active functional candidate — B36 WSERVHANDLECARRY1

Status:
BUILD-VALIDATED, DEVICE TEST REQUIRED

B36 fixes one generic WindowServer command-buffer protocol mismatch exposed by B35.

Symbian protocol evidence:
- RWsBuffer::DoWrite() sets EWsOpcodeHandle only when the destination handle differs from the previous command;
- CWsClient::CommandBufL() retains the previous destination object when EWsOpcodeHandle is absent.

B35/EKA2L1 mismatch:
- parse_command_buffer() created a fresh ws_cmd for each command;
- when bit 0x8000 was absent, obj_handle was not assigned from the previous command;
- B35 device logs repeatedly showed invalid WindowServer object handles while EikAppUiServerThread initialized.

B36 implementation:
- value-initialize each ws_cmd;
- maintain nboot2_b36_previous_handle per command buffer;
- update it on explicit-handle commands;
- reuse it on implicit-handle commands;
- keep SetNonFading's existing context.complete(epoc::error_none) unchanged.

B36 device markers:
- [NBOOT2][WSERV_HANDLE_CARRY]
- [NBOOT2][WSERV_NONFADING_ENTER]
- [NBOOT2][WSERV_NONFADING_COMPLETE]

Scope preserved:
- stock Nokia avkonfep.dll / touchscreen VKB unchanged;
- no avkonfep_general.dll restoration;
- Leave/trap semantics unchanged;
- B34 focus_callback_mutex split unchanged;
- B26 iOS exit choreography unchanged;
- SYSSTART ownership unchanged;
- native fbserv unchanged;
- EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill unchanged;
- NOJAVA and MANIC3 preserved.

TDD RED:
- run: 35732727339
- job: 106762102647
- B20-B35 reconstruction PASS
- expected failure:
  NATIVEBOOT2-B36-WSERVHANDLECARRY1-TEST: FAIL: missing in command parser: std::uint32_t nboot2_b36_previous_handle = 0;

Authoritative B36 GREEN:
- run: 35732983672
- job: 106762968487
- IPA-producing HEAD: 1ec56f99a6c6e469d6a8e3905aebb3c3cdae6e8a
- B20-B36 apply/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- all three B36 markers present in packaged Mach-O
- IPA package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

B36 FASTBUILD1:
- bootstrap_source=B28_CACHE
- bootstrap restore: 51 s
- patch/regression: 2 s
- CMake build: 35 s
- package: 3 s
- total: 119 s
- compile requests: 50
- cache hits: 48
- cache misses: 2
- hit rate: 96%
- actual compilations: 2
- compilation failures: 0

B36 IPA SHA-256:
d24551d96d8fde57c514b4a745d62a4d413e039f8b79ab2059b6d5e4434728c6

IPA artifact:
- ID: 10696356734
- ZIP digest: sha256:cd0b250769578c9ce823abf785a82ff7bd53640ee76eeecfc6f21dbde500cf27
- expires: 2026-10-06

Audit artifact:
- ID: 10696541481
- ZIP digest: sha256:3a08d01f1695df6d5e3105cdad5f175ec355693598c6b163f72de6d8e63f58ac
- expires: 2026-10-06

Full snapshot:
docs/handoff/history/B36-WSERVHANDLECARRY1.md

Device-test rule:
Sign/install B36, boot the same Nokia 5800 path, let the startup run through the former AknFep/eiksrvs failure window, then use Thoát Emulator normally. Send EKA2L1.log, EKA2L1_Persistent.log and EKA2L1_TakeThis.log. The first acceptance question is whether invalid WindowServer object-handle events and the repeated Leave(-3) family disappear or move later. The B36 markers determine whether opcode 0x5D used an implicit handle and whether SetNonFading entered/completed with KErrNone.

Do not snapshot B36 to an immutable functional branch until device evidence validates the change.



## FASTBUILD1 — promoted development build path

FASTBUILD1 is PROMOTED. B34 FOCUSMUTEXSPLIT1 is now the latest device-validated immutable functional milestone and closes the independently proven host Exit Emulator screen_mutex self-deadlock. B32/B33 diagnostics still preserve the unresolved guest AknFep -> Leave(-3) -> euser null-write -> KERN-EXEC 3 investigation.

Active development branch:
nativeboot2-current

Latest immutable functional milestone:
nativeboot2-b34-focusmutexsplit1

Stable bootstrap:
- milestone: B28 WSERVLIBTYPE1
- key: eka2l1-fastbuild1-bootstrap-b28-nojava-manic3-macos15-v1
- seed run: 35612902115
- fallback: B19 cache -> apply B20-B28
- normal fast workflow does not save the whole upstream tree

Fast workflow:
.github/workflows/build-ios-nativeboot2-current-fast.yml

Manual bootstrap workflow:
.github/workflows/seed-ios-nativeboot2-fastbuild1-bootstrap.yml

sccache:
- mozilla-actions/sccache-action@v0.0.11
- SCCACHE_GHA_ENABLED=true
- SCCACHE_IGNORE_SERVER_IO_ERROR=1
- SCCACHE_BASEDIRS=<upstream>
- C/C++ compiler launchers = sccache

Measured evidence:
- B28 historical baseline: ~197 s
- cold B19 fallback run 35612768609: 614 s
- hot B28-cache run 35614076698: 71 s
- strong one-file probe run 35616222173: 1 request / 1 miss / 1 real compile
- identical probe retry 35616567861: 1 request / 1 hit / 0 miss
- post-probe clean run 35616906674: 56 s
- pre-final-review clean run 35617195868: 69 s with the earlier timer scope
- final corrected-scope hot run 35618944742: 63 s
- final permanent-equivalent probe 35619278590: 1 request / 1 hit / 0 miss / no IPA

Final FASTBUILD1 implementation verification:
- implementation commit: 9381a02b131102ac6f1088ae077411d27f753132
- build run: 35618944742
- bootstrap_source=B28_CACHE
- B20-B28 PASS
- compile requests: 0
- bootstrap restore: 36 s
- CMake build: 1 s
- package: 2 s
- corrected total_seconds: 63 s
- NOJAVA preserved
- MANIC3 preserved
- unsigned IPA SHA-256: b289101c866bfa2a86e8046605d08299833b4dcdd0ea98e69425d78a7f93ff8d
- IPA artifact: 10647737754
- audit artifact: 10647383101

Final static/TDD run:
- 35618944698
- manifest tests: 4/4 PASS
- workflow tests: 9/9 PASS
- manifest VALID

Final acceptance suite:
- run: 35619769274
- combined tests: 13/13 PASS
- manifest VALID
- git diff --check PASS
- B28 workflow blob pin PASS

Permanent probe behavior:
- appends a transient macro plus compile-time-only static_assert to restored svc.cpp
- probe runs do not package/upload IPA
- final verification run 35619278590 produced audit artifact 10647023252 and no IPA artifact

B28 workflow remains byte-for-byte unchanged:
44d1c8aaa7ff5f0ff97271396b8bf771ad125b54

Full benchmark/probe evidence:
docs/handoff/history/FASTBUILD1.md

Development rule from now on:
1. B30/B31 functional work lands on nativeboot2-current.
2. Add the new apply_script|test_script row to ci/fastbuild1_manifest.txt.
3. Build/test/device-test on nativeboot2-current.
4. Snapshot the exact validated commit to an immutable nativeboot2-bXX-* branch.
5. Do not return to sibling milestone branches as the primary development/cache path.

FASTBUILD1 does not change guest behavior. B30 ROOTEDLIBPATH1 is now device-validated for the rooted-no-drive loader blocker: EiksrvUi.dll resolves from Z:\\sys\\bin and loads successfully. The next blocker is a native scheduler crash during later startup.

## Validated milestones

### B25 — FBSSHAREDHEAP1

DEVICE-VALIDATED.

B25 fixed the native/HLE FBS canonical global chunk-name collision.

Healthy runtime markers:
- [NBOOT2][FBS_SHARED_HEAP_HANDOFF]
- shared_guest_owned=true
- shared_renamed=true
- large_guest_owned=true
- large_renamed=true
- [NBOOT2][FBS_SHARED_HEAP_READY]

The old AknCapServer failure:
- PC = 0x000000F0
- r0 = 0x40201598
- KERN-EXEC 3

is no longer the active blocker.

Firmware reaches the NOKIA splash.

### B26 — IOSLIBRARYEXIT1

DEVICE-VALIDATED.

The host-side UIKit UICollectionView crash when choosing Exit Emulator is fixed.

Validated exit sequence:
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

Preserve the B26 exit choreography.

### B27 — WSERVPANIC13TRACE1

DEVICE-TESTED diagnostic milestone.

B27 localized the current Nokia boot blocker.

Observed ordering:
1. !Windowserver registration succeeds.
2. B25 FBS shared-heap handoff succeeds.
3. SVCMISS 0x48.
4. SVCMISS 0x4A.
5. EKDATA.DLL loads:
   - UID3 = 0x100039E0
   - runtime code = 0x807ABDF8
6. SVCMISS 0x63:
   - pc = 0x80297F64
   - lr = 0x802A1CFD
   - r0 = 0x400F0007
7. Symbian leave begins/traps immediately afterward.
8. Wserv reports EWsPanicFailedToInitialise.
9. Wserv self-panics:
   - category = WSERV-INTERNAL
   - reason = 13
10. NearlyIdleKickBack then panics Domino 13 downstream.

B27 Wserv panic:
- PC = 0x80298584
- LR = 0x802A3A39
- SP = 0x00503C70

## Source meaning of WSERV-INTERNAL 13

Public Symbian Window Server source defines:
EWsPanicFailedToInitialise = 13

WSTOP.CPP traps CWsTop::RunServerL(); if it leaves/errors, E32Main panics with EWsPanicFailedToInitialise.

Thus B27 proves Wserv is leaving during RunServerL / InitStaticsL rather than failing in the old FBS crash path.

Reference:
- SymbianSource/oss.FCL.sf.os.graphics
- commit ff133bc50e6158bfb08cc093b0f0055321dcde99
- windowing/windowserver/nonnga/SERVER/WSTOP.CPP
- windowing/windowserver/SERVER/openwfc/panics.h

## B28 — WSERVLIBTYPE1

DEVICE-VALIDATED FOR THE LIBRARYTYPE/WSERV BLOCKER.

B28 implements only EPOC 9.4 SVC 0x63 as the EKA2 LibraryType executive.

External Symbian source confirms:
- RLibrary::Type() creates a TUidType and calls Exec::LibraryType(iHandle, u).
- Exec::LibraryType(TInt, TUidType&) dispatches EExecLibraryType.

B28 implementation:
- ABI:
  LibraryType(handle, TUidType&)
- resolves kernel::library from the guest handle
- reads lib->get_codeseg()->get_uids()
- writes UID1 / UID2 / UID3 into the guest output
- adds runtime marker:
  [NBOOT2][WSERV_LIBRARY_TYPE]
- registers:
  BRIDGE_REGISTER(0x63, library_type)
- preserves:
  BRIDGE_REGISTER(0x64, process_type)

B28 deliberately does NOT implement:
- SVC 0x48
- SVC 0x4A
- SVC 0x50

and does not suppress Wserv panic behavior.

### TDD evidence

Focused RED run:
35605582017

Expected failure:
NATIVEBOOT2-B28-WSERVLIBTYPE1-TEST: FAIL: missing in svc.cpp:
BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)

GREEN/build run:
35606704683

PASS:
- B20
- B21
- B22
- B23
- B24
- B25
- B26
- B27
- B28
- iOS compile/link
- NOJAVA
- MANIC3

## B28 device result

The 2026-09-21 B28 device log validates the narrow fix.

Observed:
- EKDATA.DLL still loads, UID3=0x100039E0.
- [NBOOT2][WSERV_LIBRARY_TYPE] appears:
  handle=0x400F0007 valid=1 output_mapped=1 uid1=0x10000079 uid2=0x1000008D uid3=0x100039E0
- SVCMISS 0x63 is absent.
- WSERV-INTERNAL 13 is absent.
- Domino 13 is absent.
- a later Wserv Leave -5 is trapped rather than fatal.
- startup continues into StarterServer, tzserver, cntsrv and higher UI/application services.
- B26 Exit Emulator remains healthy: shutdown_done -> normal_restart_begin -> normal_restart_done has_device=1.

Conclusion:
B28 removed the B27 causal chain. Wserv is no longer the active boot blocker.

Do not claim full Nokia UI boot from this log alone; the next failure is later in UIKON/AknCap/Eiksrv startup.

## Active blocker after B28 — Central Repository / FEP

The strongest new causal chain is repository 0x10272618, the FEP framework Central Repository.

Symbian source identifies:
- KUidFepFrameworkRepository = 0x10272618
- default FEP keys under 0x1000:
  - 0x1001 DefaultFepId
  - 0x1002 DefaultOnState
  - 0x1004 DefaultOnKeyData
  - 0x1008 DefaultOffKeyData

Eiksrv CEikServAppUiServer::ConstructL() opens this repository, starts an EConcurrentReadWriteTransaction, writes the default FEP state/ID/key data, then commits.

The B28 baseline Central Repository implementation is incompatible with that path:
- TransactionStart is stubbed and does not call set_active(true).
- TransactionCancel is stubbed.
- Set write mode returns KErrNotFound for absent keys unless a transaction is actually active.
- cen_rep_transaction_commit exists in the opcode enum but is not handled/implemented.
- Symbian's actual SetSettingL creates a missing setting and applies fallback metadata/access policy.

The B28 log correlates this directly:
- repo 0x10272618 opens;
- TransactionStart stubbed;
- immediate eiksrvs Leave -1 with centralrepository.dll + eiksrv.dll on stack;
- TransactionCancel stubbed;
- eiksrvs later self-kills reason -1;
- the sequence repeats on restart.
AknCapServer also has Leave -1 paths through centralrepository.dll + cone.dll.

Therefore the preferred B29 direction is a generic Central Repository transaction/Set fix, not a repo/key hardcode.

## B29 — CENREPTX1

DEVICE-VALIDATED FOR THE CENTRAL REPOSITORY/FEP BLOCKER.

Functional commit:
7bceb18a337b0977f0f2f68ea0232748dd848392

Immutable branch:
nativeboot2-b29-cenreptx1

B29 implements the narrow generic Central Repository compatibility required by the B28 Eiksrv/FEP trace:
- registers/routes cen_rep_transaction_commit;
- makes StartTransaction activate state and map Symbian modes 1/2/3;
- stages transactional Set changes with copy-on-write;
- makes Set create a missing key with repository default metadata;
- Commit installs staged changes, persists once, then notifies;
- Cancel discards staged changes;
- fixes transaction-mode decoding so active bits do not contaminate the mode.

B29 does not hardcode repository 0x10272618 or FEP key values and does not modify SVC 0x2D/0x48/0x4A/0x50.

Device evidence from both B29 and B29-DIAG1:
- repo 0x10272618 starts transaction mode=2 successfully;
- all four FEP settings complete without CEN_SET_FAIL;
- commit reports changed=4, key_info=4, completion=0;
- no transaction cancel follows that successful transaction;
- keys created in the earlier B29 run are present in the later DIAG1 run, confirming persistence;
- B28 Wserv remains healthy: no SVCMISS 0x63, WSERV-INTERNAL 13, or Domino 13.

Conclusion:
the Central Repository/FEP blocker is removed.

### Failure exposed after B29

Both device logs then converge on:
1. FEP transaction commits successfully.
2. Fepswitch.exe returns KErrNotFound.
3. Symbian eiksrv.cpp treats Fepswitch KErrNotFound as optional and continues.
4. Eiksrv attempts RLibrary::Load for its UI-specific DLL.
5. EKA2L1 library loading returns KErrNotFound.
6. EikAppUiServerThread leaves -1 and eiksrvs later exits.

Symbian source confirms the load follows the FEP/Fepswitch sequence and propagates the RLibrary load error with User::LeaveIfError.

### B29-DIAG1 result

DEVICE-OBSERVED.

DIAG1 proved:
- no Set/type/descriptor failure occurs in the FEP transaction;
- Commit succeeds;
- the failure is later than CenRep.

Full snapshot:
docs/handoff/history/B29-DIAG1.md

## B29-LOADERDIAG1 — diagnostics only

BUILD-VALIDATED, DEVICE LOG REQUIRED.

Important source discovery:
the exact B28 FASTBUILD bootstrap differs from newer upstream EKA2L1. In the cached lib_manager::load(), drive iteration occurs only for non-rooted requests. A rooted path without a drive falls through to a direct io_->exist(lib_path) lookup; there is no A:..Z: fallback branch and no ROFS staging step in this loader path.

LOADERDIAG1 deliberately preserves this behavior and only instruments it.

Markers:
- [NBOOT2][LDR_LIB_REQUEST]
- [NBOOT2][LDR_LIB_RESULT]
- [NBOOT2][LDR_ROOT_BEGIN]
- [NBOOT2][LDR_ROOT_DIRECT]
- [NBOOT2][LDR_ROOT_MISS]
- [NBOOT2][LDR_OPEN_FAIL]
- [NBOOT2][LDR_FORMAT]
- [NBOOT2][LDR_PARSE_FAIL]
- [NBOOT2][LDR_CODESEG_RESULT]
- [NBOOT2][LDR_DEP_FAIL]

TDD RED:
- run 35661287453
- expected failure: LDR_LIB_REQUEST absent
- B20-B29/DIAG1 passed before the intended failure

Two patcher-only GREEN failures:
- 35661492473: stale exact load() entry anchor
- 35661698478: assumed newer upstream format/parse block
Neither reached compile.

Systematic one-time baseline inspection:
- run 35661849022
- restored exact B28 cache
- proved the actual rooted-path behavior
- temporary inspection workflow removed after use

Final GREEN:
- run 35662229010
- job 106539879024
- build-tested code commit 9aa612714878541ec4b3f7481516bba00b6d52a4
- B29 + DIAG1 + LOADERDIAG1 PASS
- B20-B28 PASS
- compile/link PASS
- binary invariants PASS
- IPA SHA-256 b748c0e009721b37f24e89003fc1a2a0a8e64e158379a633ece78b0e94576d7c

Device result:
- LDR_LIB_REQUEST = 5
- LDR_ROOT_BEGIN = 5
- LDR_ROOT_DIRECT exists=0 = 5
- LDR_ROOT_MISS = 5
- LDR_LIB_RESULT success=0 completion=-1 = 5
- LDR_OPEN_FAIL = 0
- LDR_FORMAT = 0
- LDR_PARSE_FAIL = 0
- LDR_CODESEG_RESULT = 0
- LDR_DEP_FAIL = 0

Every EiksrvUi request is \sys\bin\EiksrvUi.dll with rooted_no_drive=1 and fails before open/parse/dependency loading.

Current upstream EKA2L1 commit 437b29006bd8a0186f4070c9445f43e98e5c7435 contains the exact corresponding fix and describes the bug as drive-less absolute paths being opened verbatim instead of searched across drives.

B30 decision:
ROOTEDLIBPATH1.

Backport only rooted-no-drive drive resolution into lib_manager::load(), reuse existing load_depend_on_drive(), and keep LOADERDIAG1 enabled for the first B30 device test. Do not batch ROM/E32 classification, relocation, dependency, or SVC fixes.

Full snapshot:
docs/handoff/history/B29-LOADERDIAG1.md

## New missing executive observed after the UI failure

SVCMISS 0x2D appears later:
- r0=0xFFFF8001
- r1=0x000000FA

Symbian execs.txt maps 0x2D to:
ThreadSetProcessPriority(thread_handle, TProcessPriority)

0xFA = 250 = EPriorityBackground.

Because this occurs after the first Central Repository/AknCap/Eiksrv failures, it is not the first causal blocker. Keep it as an observed compatibility gap rather than patching it speculatively.

## Other Wserv gaps still under observation

B27 also saw:
- 0x50 during early Wserv startup, strongly consistent with WsRegisterThread.
- 0x48 and 0x4A during InitStaticsL, consistent with Window Server event-hook executive calls.

These remain candidates only.

Current decision rule:
B34 FOCUSMUTEXSPLIT1 is DEVICE-VALIDATED and remains the latest immutable functional milestone. B35 EIKLEAVECALLER1 is DEVICE-OBSERVED and has completed its diagnostic purpose: the stable first ws32 frame resolves to ordinal 206 and service/opcode 0x5D. Do not promote run 35728463388 as B36 because it contains no B36 functional apply patch; its SetNonFading contract passes on the B35 baseline. The next functional or diagnostic B36 work must target the ws32 0x5D dispatch/completion boundary narrowly and prove the source of KErrCancel (-3) before changing guest behavior. Preserve stock Nokia FEP, B34 focus mutex split, B26 Exit Emulator choreography, and all B20-B35 invariants.



## B30 device result — 2026-09-22

B30 ROOTEDLIBPATH1 is DEVICE-VALIDATED for its intended causal boundary.

The first EiksrvUi request now follows:

`LDR_LIB_REQUEST rooted_no_drive=1`
-> `LDR_ROOT_BEGIN`
-> `LDR_ROOT_CANDIDATE candidate=Z:\\sys\\bin\\EiksrvUi.dll exists=1`
-> `LDR_FORMAT ... format=ROM`
-> `LDR_ROOT_RESOLVED success=1`
-> `LDR_LIB_RESULT success=1 completion=0`.

The B29 direct-VFS miss no longer terminates this request.

Startup then progresses for roughly 30 seconds. The supplied video remains on the NOKIA splash before the app exits to the iOS Home Screen.

Late device ordering:
1. AknIconSrv Leave -5 events are trapped.
2. `akncapserver` is forcefully killed with category Domino, reason -33 at 08:47:47.542.
3. SVCMISS 0xE3 appears at 08:47:47.549.
4. Multiple later startup processes are spawned.
5. Host logging stops at 08:47:47.646.
6. iOS crash report timestamp is 08:47:48.

Crash report:
- EXC_BAD_ACCESS / SIGSEGV;
- KERN_INVALID_ADDRESS at 0x0;
- faulting thread: Symbian OS thread;
- `thread_scheduler::switch_context()+232`;
- `kernel_system::reschedule()+460`;
- `system_impl::loop()+576`.

Upstream EKA2L1 commit 437b29006bd8a0186f4070c9445f43e98e5c7435 contains the exact scheduler failure class: a ready thread can outlive its owning process memory model and be passed to `switch_context`. Its narrow fix filters/dequeues ready entries whose owner or memory model is gone before the context switch.

Preferred B31 direction:
SCHEDREADYMM1.

Do not batch SVC 0xE3 into B31. Upstream maps 0xE3 to `Exec::GetModuleNameFromAddress`, so retain it as the next observed guest compatibility gap after the host crash is removed.

Full device snapshot:
docs/handoff/history/B30-DEVICE1.md

## Preserved invariants

Keep:
- firmware SYSSTART as startup owner
- native fbserv startup/rendezvous
- B25 FBS shared-heap handoff
- B24 CBitmapFont/vtable diagnostics
- B23 TFontSpec v2 ABI
- B22 default typeface
- B21 font aliases
- B20 Central Repository ResetAll
- B19 SA language ABI
- EMUHUB1
- B26 safe Exit Emulator path
- B27 Wserv panic diagnostics
- B28 narrow LibraryType implementation
- B29 narrow generic CenRep transaction/Set compatibility
- NOJAVA
- MANIC3

Do not reintroduce:
- host-driven SysStart/Menu launch ownership
- native fbserv suppression
- native FBS heap adoption
- Wserv panic suppression
- speculative multi-SVC batches

## Milestone history

- B19: SALANGABI1
- B20: CENRESETALL1
- B21: FBSFONTALIAS1
- B22: FBSDEFAULTTYPEFACE1
- B23: FBSFONTSPECV2ABI1
- B24: FBSVTABLEABI1
- B25: FBSSHAREDHEAP1 — device validated
- B26: IOSLIBRARYEXIT1 — device validated
- B27: WSERVPANIC13TRACE1 — device trace isolated SVC 0x63 -> leave -> WSERV-INTERNAL 13
- B28: WSERVLIBTYPE1 — device validated; removes missing LibraryType -> WSERV-INTERNAL 13 / Domino 13 blocker
- B29: CENREPTX1 — device validated; immutable branch nativeboot2-b29-cenreptx1
- B29-DIAG1: device-observed; proves CenRep/FEP success and localizes the next failure to library loading
- B29-LOADERDIAG1: device-observed; proves rooted-no-drive direct VFS miss is causal and selects B30 ROOTEDLIBPATH1
- B30: ROOTEDLIBPATH1 — device validated for loader blocker at 58a6178a53f9ddd8f4edbb5b3788d25131b9d4f9; immutable branch nativeboot2-b30-rootedlibpath1; later host scheduler crash exposed
- B31: SCHEDREADYMM1 — device validated for the B30 host scheduler crash at 6ccdd5c1b9101124981315322af5002dac057edc; immutable branch nativeboot2-b31-schedreadymm1; next boundary is repeated EikAppUiServerThread KERN-EXEC 3
- B32: EIKSRVFAULTDIAG1 — device-observed; localized AknFep -> Leave(-3) -> euser null write -> KERN-EXEC 3 and ruled out SVC 0xE3/0x2D as immediate causal targets
- B33: EIKCANCELORIGIN1 — device-observed; LLE/HLE/notify probes do not identify the pre-Leave(-3) origin; Exit Emulator hang plus exact reconstructed source proved a same-thread screen_mutex self-deadlock during Wserv teardown
- B34: FOCUSMUTEXSPLIT1 — DEVICE-VALIDATED; dedicated focus_callback_mutex removes the B33 same-thread screen_mutex teardown deadlock; immutable branch nativeboot2-b34-focusmutexsplit1
- B35: EIKLEAVECALLER1 — DEVICE-OBSERVED; resolves stable ws32.dll+0x370A to export ordinal 206 and selects ws32 service/opcode 0x5D as the next narrow trace boundary; B34 exit remains healthy

Snapshots:
- docs/handoff/history/B25-FBSSHAREDHEAP1.md
- docs/handoff/history/B26-IOSLIBRARYEXIT1.md
- docs/handoff/history/B27-WSERVPANIC13TRACE1.md
- docs/handoff/history/B28-WSERVLIBTYPE1.md
- docs/handoff/history/B29-CENREPTX1.md
- docs/handoff/history/B29-DIAG1.md
- docs/handoff/history/B29-LOADERDIAG1.md
- docs/handoff/history/B30-ROOTEDLIBPATH1.md
- docs/handoff/history/B30-DEVICE1.md
- docs/handoff/history/B31-SCHEDREADYMM1.md
- docs/handoff/history/B31-DEVICE1.md
- docs/handoff/history/B32-EIKSRVFAULTDIAG1.md
- docs/handoff/history/B32-DEVICE1.md
- docs/handoff/history/B33-EIKCANCELORIGIN1.md
- docs/handoff/history/B33-DEVICE1.md
- docs/handoff/history/B34-FOCUSMUTEXSPLIT1.md
- docs/handoff/history/B34-DEVICE1.md
- docs/handoff/history/B35-EIKLEAVECALLER1.md
- docs/handoff/history/B35-DEVICE1.md

## How to resume

Use:

"Read docs/handoff/CURRENT.md from phai-nguyen/Eka2l1_bot_menu_simbiam on nativeboot2-current. B34 FOCUSMUTEXSPLIT1 remains the latest device-validated immutable functional milestone at 24001e3306070fab2145bc1a4dd326a9fa83587d and its Exit Emulator fix must not be undone. B35 EIKLEAVECALLER1 is device-observed: ws32.dll+0x370A resolves to EABI ordinal 206 = RWindowTreeNode::SetNonFading(TBool), opcode 0x5D is in the immediate path, and B35 repeatedly logs invalid WindowServer object handles while EikAppUiServerThread starts. Symbian source proves command-buffer handles are omitted when unchanged and the server must retain the previous destination object. The active candidate is B36 WSERVHANDLECARRY1, GREEN run 35732983672 / job 106762968487 / code HEAD 1ec56f99a6c6e469d6a8e3905aebb3c3cdae6e8a / IPA SHA d24551d96d8fde57c514b4a745d62a4d413e039f8b79ab2059b6d5e4434728c6. B36 value-initializes ws_cmd, carries the previous explicit handle into implicit-handle commands, and adds WSERV_HANDLE_CARRY / WSERV_NONFADING_ENTER / WSERV_NONFADING_COMPLETE markers without changing SetNonFading KErrNone completion. Device-test B36 before promotion or B37. Preserve stock Nokia avkonfep.dll, SYSSTART ownership, native fbserv, B26 exit choreography, B34 focus mutex split, NOJAVA, MANIC3, and EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill."


This file is authoritative unless newer committed device evidence supersedes it.


## Latest override — B37 WSERVBATCHCOMPLETE1

This section supersedes the older B36 resume text above.

B36 WSERVHANDLECARRY1 is now DEVICE-OBSERVED. Device logs confirm:
- implicit WindowServer destination-handle carry is active;
- `WSERV_HANDLE_CARRY`, `WSERV_NONFADING_ENTER`, and `WSERV_NONFADING_COMPLETE` each appear 17 times;
- SetNonFading receives the effective carried handle and still completes `KErrNone`;
- the failing path shows `signaled_before=1` on entry, while EikAppUiServerThread still produces 16 Leave(-3) events.

The active candidate is now **B37 WSERVBATCHCOMPLETE1**.

B37 changes only WindowServer command-buffer request-signal timing:
- completion/result writes remain unchanged;
- request signaling is deferred while a WindowServer batch executes;
- the guest is signaled once after the whole command buffer completes;
- all other HLE services keep the existing immediate-signal behavior.

TDD:
- RED run 35735338725 / job 106771025304: expected failure for missing `defer_request_signal`.
- GREEN run 35735710861 / job 106772280995.
- B37 code HEAD: `dabed3de3d543d1700eca8b3394fead2a40ef94a`.
- IPA SHA-256: `80db395f1f6083c19b25a5b763fd04f43e9276001f3299a31bc3e54c19a5bf3d`.
- compile/link, manifest apply, full regression, binary invariants, packaging and upload: PASS.
- NOJAVA / MANIC3 preserved.

New markers:
- `[NBOOT2][WSERV_BATCH_DEFER_BEGIN]`
- `[NBOOT2][WSERV_BATCH_SIGNAL]`

B37 status: **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Do not create/promote B38 until B37 device logs are reviewed. Preserve stock Nokia `avkonfep.dll`, firmware SYSSTART ownership, native fbserv, B26 Exit Emulator choreography, B34 focus mutex split, B36 handle-carry semantics, and EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill.

Snapshot:
- `docs/handoff/history/B37-WSERVBATCHCOMPLETE1.md`

### Resume from here

Read this latest override first. Install/sign the B37 IPA from GREEN run 35735710861, boot the same Nokia 5800 path as B36, use **Thoát Emulator** normally, and collect `EKA2L1.log`, `EKA2L1_Persistent.log`, and `EKA2L1_TakeThis.log`. The first checks are whether SetNonFading now enters with `signaled_before=0` during deferral, whether `WSERV_BATCH_SIGNAL` occurs once after the batch, and whether the repeated EikAppUiServerThread Leave(-3) chain is removed or changes ordering.


## Latest override — B37 DEVICE1

This section supersedes the earlier B37 device-test-required text.

B37 WSERVBATCHCOMPLETE1 is DEVICE-OBSERVED. Its signaling change works exactly as intended:
- 604 WindowServer batches enter deferral and 604 signal once at batch end;
- all 17 SetNonFading calls now enter with signaled_before=0;
- all 17 SetNonFading completions remain unsignaled inside the batch with signaled_after=0;
- WSERV_BATCH_SIGNAL then reports signaled_after=1.

But the repeated guest failure is unchanged:
- 16 EikAppUiServerThread Leave(-3)
- 16 access violations / KERN-EXEC 3
- stable euser PC 0x8029833C (offset 0x2EF4)
- stable euser LR 0x802ABB29 (offset 0x166E0)
- 58 invalid WindowServer object-handle reports

Ordering matters: the first Leave(-3) occurs before the later 6-command batch that dispatches opcode 0x5D SetNonFading. Symbian source shows RWindowTreeNode::SetNonFading only writes the opcode/data into RWsBuffer; such WindowServer calls are buffered and executed later. Therefore SetNonFading is no longer considered the immediate causal server handler.

B37 is not promoted as a causal functional milestone.

Preferred next step: B38 diagnostic only. Trace the exact WindowServer command opcode/object/completion surrounding the batch immediately before each eiksrvs Leave(-3), and resolve the stable euser PC/LR to nearest export ordinals/code windows. Do not change FEP behavior, completion values, Leave/trap semantics, SVCs, scheduler, loader, B36 handle carry, B37 signal deferral, or B34 exit choreography.

Snapshot:
- docs/handoff/history/B37-DEVICE1.md

Do not implement a behavioral B38 fix until the new diagnostic identifies the real KErrCancel origin.


## Latest override — B38 EIKCANCELTRACE2

This section supersedes the B37 resume target above.

B37 is DEVICE-OBSERVED: request-signal deferral works exactly as designed but does not remove the 16 repeated EikAppUiServerThread Leave(-3) failures. Ordering proves SetNonFading dispatch occurs after the Leave boundary and is no longer treated as the immediate causal handler.

B38 EIKCANCELTRACE2 is now BUILD-VALIDATED and awaiting device logs.

TDD:
- RED commit 02773c6cae716fa10959182e721e1c5b1b8558e4
- RED run 35742603226 / job 106795931691
- intended missing B38 diagnostic-state failure
- GREEN code commit 3c2e02ad7dbc29db244973db761f28810afe8e99
- GREEN run 35743121880 / job 106797710973
- apply/regression/compile/binary/package/upload PASS
- compilation failures 0
- NOJAVA / MANIC3 preserved

B38 adds diagnostic-only:
- [NBOOT2][WSERV_BATCH_CMD]
- [NBOOT2][WSERV_BATCH_RESULT]
- [NBOOT2][EIKDIRECT_FRAME]
- [NBOOT2][EIKDIRECT_CODE16]
- diagnostic mirror nboot2_b38_last_completion_result

B38 does not change WindowServer dispatch, completion values, B37 signaling timing, FEP, Leave/trap, SVCs, scheduler, loader, or B34 exit behavior.

IPA SHA-256:
20da39a745f1fab9f0dc8519ff8177c7deda20dd86e8b1432a4b5ceb28a27d93

Artifact ID:
10699954176

Next action: device-test B38 and send EKA2L1.log, EKA2L1_Persistent.log, and EKA2L1_TakeThis.log. Correlate the batch immediately preceding Leave(-3), then resolve direct euser PC/LR before choosing any B39 behavioral change.

Snapshot:
- docs/handoff/history/B38-EIKCANCELTRACE2.md


## Latest override — B38 DEVICE1

This section supersedes the earlier B38 device-test target.

B38 EIKCANCELTRACE2 is DEVICE-OBSERVED and has completed its diagnostic purpose.

All 16 repeated EikAppUiServerThread Leave(-3) events are preceded by a single WindowServer command:
- opcode 0x16 = EWsClOpCreateWindow
- command length 16
- positive result 393222 = 0x00060006
- CreateWindow therefore succeeds; it is not the source of KErrCancel.

Direct Leave resolution:
- PC euser.dll +0x2EF4 reaches SVC 0xDF LeaveStart path.
- LR euser.dll +0x166E0 resolves to ordinal 649 = User::Leave(int).
- B38 stack layout proves saved caller LR is avkonfep.dll +0xF104.
- code before +0xF104 performs a nested state load via caller r4, compares it to zero, forms -3 and calls User::Leave when null.
- saved caller r4 is stack index 2 = 0x00703A88 for the first observed cycle.

The Leave itself is caught successfully:
"Leave trapped by trap handler." / LeaveEnd occurs before the later WindowServer cleanup/configuration work. Source comparison with SymbianSource us_trp.cpp and scodeseg.cpp matches the __LEAVE_EQUALS_THROW__ LeaveStart/LeaveEnd model. Do not remap SVC 0xDF and do not suppress KErrCancel based on B38.

The later 6-command WindowServer batch on handle 0x00060006 includes opcode 0x5D SetNonFading and completes KErrNone, confirming SetNonFading is downstream.

The immediate fatal boundary is now:
- EikAppUiServerThread write AV at address 0x00000010
- PC 0x802A01C4 = euser.dll +0xAD7C
- LR 0x802A2DF5 = euser.dll +0xD9AD
- r0=0, r1=0

Preferred next step: B39 EIKPOSTLEAVEAV1, diagnostic-only.
B39 should resolve that AV PC/LR to nearest euser exports, dump bounded code/stack context, and safely log the AvkonFep nested state at caller_r4 -> [r4+0x10] -> [+0x24]. This should identify whether the null AvkonFep state or the post-catch cleanup path is the next functional target.

Do not change:
- stock avkonfep.dll / FEP
- KErrCancel or Leave/TRAP
- SVC 0xDF
- B36 handle carry
- B37 signal deferral
- scheduler/loader
- B34 Exit Emulator
- EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill
- NOJAVA / MANIC3

B34 Exit Emulator remains healthy in B38: final os_join approximately 36 ms, shutdown_done and normal_restart_done reached.

Snapshot:
- docs/handoff/history/B38-DEVICE1.md

Do not implement a behavioral B39 fix until B39 diagnostic evidence resolves the post-Leave AV and AvkonFep null state.


## Latest override — B39 EIKPOSTLEAVEAV1

This section supersedes the B38 DEVICE1 resume target above.

B39 EIKPOSTLEAVEAV1 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**. It is diagnostic-only.

B38 established that CreateWindow succeeds, stock AvkonFep intentionally raises KErrCancel because a nested state field is null, the Leave is caught successfully, and the fatal boundary moves to a later euser null write at address 0x10.

B39 adds two read-only evidence channels.

At the KErrCancel boundary:
- `[NBOOT2][EIKFEP_STATE]`
- uses the B38-proven User::Leave frame layout: saved caller r4 at SP+8, saved caller LR at SP+12;
- mapping-checks and logs caller_r4 -> [r4+0x10] -> [[r4+0x10]+0x24].

At the later access violation:
- `[NBOOT2][EIKPOSTLEAVE_AV_FRAME]`
- `[NBOOT2][EIKPOSTLEAVE_AV_CODE16]`
- `[NBOOT2][EIKPOSTLEAVE_AV_STACK]`
- resolves PC/LR against loaded codesegs, reports nearest export ordinal/address/delta, dumps bounded code windows and up to 24 stack words.

TDD:
- canonical RED commit `f382cd9cdd3f39d9f41ec46a714c830897e0739f`
- RED run 35747370629 / job 106812318986
- expected failure: missing `[NBOOT2][EIKFEP_STATE]`
- canonical GREEN code HEAD `7f845581ba32dd59fc5229ee24fa5979ef7cc81e`
- GREEN run 35748481719 / job 106816104243
- workflow conclusion: success
- apply/tests/regressions/compile/link/binary invariants/package/upload: PASS
- compilation failures: 0
- NOJAVA / MANIC3 preserved

IPA:
- artifact ID 10703293386
- artifact ZIP digest `sha256:d87cccf761bb2fcf9f6faebf25f5c852cbb060fd10abbb659aa1421e4b02ab46`
- unsigned IPA SHA-256 `94322fffc3f90e367e32081c2e52cdbdcfec32f47a8fff797447b4e897a85509`
- size 19,950,168 bytes

FASTBUILD audit:
- B28_CACHE
- bootstrap 35 s
- patch/regression 2 s
- CMake build 74 s
- package 3 s
- total 139 s
- sccache hit rate 99.33%

Preserve:
- stock Nokia avkonfep.dll
- firmware SYSSTART ownership
- native fbserv
- B26/B34 Exit Emulator choreography
- B36 implicit WindowServer handle carry
- B37 batch signal deferral
- Leave/TRAP semantics and KErrCancel
- EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill / 0xDF leave_start / 0xE0 leave_end
- NOJAVA / MANIC3

Public/Exa research did not provide an exact Nokia 5800 euser symbol map reliable enough to name +0xAD7C / +0xD9AD, so B39 runtime resolution is intentionally used instead of offset guessing.

### Resume from here

Sign/install B39 and boot the same Nokia 5800 path. Allow the repeated eiksrvs failure path to occur, then use **Thoát Emulator** normally. Do not manually swipe the app away unless it actually hangs.

Collect:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

First analysis must correlate `EIKFEP_STATE` across all Leave(-3) cycles and resolve the later `EIKPOSTLEAVE_AV_FRAME/CODE16/STACK` evidence. Determine whether the post-catch AV is fallout from the same missing AvkonFep state or a separate compatibility defect.

Do not implement behavioral B40 until B39 device evidence identifies the missing state/function.

Snapshot:
- `docs/handoff/history/B39-EIKPOSTLEAVEAV1.md`


## Project state persistence policy

This repository is the durable source of truth for cross-chat/project continuation.

Rules:
- `docs/handoff/CURRENT.md` on `nativeboot2-current` is the authoritative hot state for the next session.
- After every meaningful build result, device-test result, promoted/retired hypothesis, or newly identified blocker, update GitHub before relying on chat history.
- Keep detailed milestone/device evidence under `docs/handoff/history/`; keep the latest resume boundary and next safe action in `CURRENT.md`.
- Record exact branch/commit SHA, GitHub Actions run/job, artifact ID/SHA when applicable, validation status, preserved invariants, and explicit next action.
- Before starting a new behavioral build, read the latest committed `CURRENT.md` and any newer device snapshot. GitHub state takes precedence over conversational recollection if they differ.
- Never mark a diagnostic hypothesis as a functional milestone without device evidence.
- Before moving to a new ChatGPT conversation because the current one is long or unstable, commit the latest meaningful project state to GitHub first.

Current persistence checkpoint:
- active branch: `nativeboot2-current`
- latest device-validated functional milestone: B41 WSERVMESSAGEWINEXIT1
- immutable branch: `nativeboot2-b41-wservmessagewinexit1`
- immutable/final validated code HEAD: `b43e59696d313da97c8845a1a20e78d9b6c762d7`
- B41 GREEN run/job: `35794136142 / 106969339936`
- B41 device snapshot: `docs/handoff/history/B41-DEVICE1.md`
- B41 device result: MessageWin wipeout guard observed twice; Exit Emulator reaches os_join_done, graphics_join_done, shutdown_threads_done, state_reset_done, shutdown_done and normal_restart_done has_device=1
- B40 is also now device-validated: EUART1 completes KErrNone, canonical eiksrvs registers `!EikAppUiServer`, and the B39 repeated EIKFEP/EIKFAULT/KERN-EXEC family disappears
- next gate: continue from the now-healthy System GUI/exit baseline; do not reopen Loader PDD or MessageWin exit unless new device evidence regresses them.


## Latest override — B39 DEVICE1

This section supersedes the earlier B39 device-test-required target.

B39 EIKPOSTLEAVEAV1 is now **DEVICE-OBSERVED; ROOT CAUSE IDENTIFIED**.

B39 diagnostic evidence resolves the repeated post-Leave euser write AV:
- PC `euser.dll +0xAD7C`, nearest export ordinal 1290 = `CServer2::DoConnect(RMessage2 const&)`;
- the faulting instruction is `STR r4,[r0,#0x10]` with `r0=0`;
- SymbianSource `CServer2::DoConnectL` calls `NewSessionL()` and then dereferences the returned session;
- `CEikServAppUiServer::NewSessionL()` returns NULL only when `EikServAppUiSessionFactory()` is absent.

The first canonical eiksrvs instance exposes the earlier causal boundary:
- EiksrvUi.dll loads;
- ViewServer starts and parent continues;
- `c32root.dll` loads;
- immediately afterward B39 logs `Unimplemented IPC call: 0x4 for server: !Loader`;
- that first eiksrvs instance never completes System GUI construction / session-factory installation.

Symbian `CEikServAppUiBase::InitializeL()` proves the exact next call after `StartC32()` is `User::LoadPhysicalDevice("EUART1")`. EKA2L1 loader opcode 4 is `ELoadPhysicalDevice`.

B39's old B28-cache dispatcher logs unknown IPC at warning level and drops the message without completion. Upstream EKA2L1 commit `9f28c76fe0f54f43a39319da5f4042c853505807` documents and fixes that generic historical behavior. The more specific upstream commit `0987745cc0bde96511fce2a4bfefcfd8fbced3dc` adds `Loader::LoadPhysicalDevice`, registers opcode 4, and completes it with `KErrNone` because the physical device is represented by HLE.

Root-cause chain:

`StartC32 -> LoadPhysicalDevice(EUART1) -> !Loader opcode 4 missing -> synchronous IPC dropped -> canonical eiksrvs stalls before SetEikServAppUiSessionFactory -> later/duplicate eiksrvs has factory NULL -> NewSessionL returns NULL -> CServer2::DoConnectL NULL dereference -> KERN-EXEC 3`.

The stable AvkonFep nested NULL / Leave(-3) state is therefore downstream of an already incomplete System GUI startup and is not selected as the first behavioral target.

Preferred next candidate:
**B40 LOADERPDD1**.

B40 must be narrow:
- port only upstream `Loader::LoadPhysicalDevice` behavior from `0987745cc0bde96511fce2a4bfefcfd8fbced3dc`;
- register `ELoadPhysicalDevice` / opcode 4;
- validate the PDD descriptor;
- return `KErrNone` for the HLE-backed PDD;
- add a narrow runtime marker proving `EUART1` entry/completion.

Do not bundle the generic unknown-IPC completion change from `9f28c76f` into B40. Do not alter stock AvkonFep, Leave/TRAP/KErrCancel, CServer2 NULL handling, Eik session-factory behavior, WindowServer, scheduler, SVC mappings, B36/B37 semantics, loader library resolution, or B34 Exit Emulator choreography.

B39 host/iOS result remains healthy: Exit Emulator reaches `os_join_done`, `shutdown_done`, and `normal_restart_done has_device=1`; no iOS-specific root cause is selected.

Full device/root-cause snapshot:
- `docs/handoff/history/B39-DEVICE1.md`

No B40 behavioral code was applied while producing this snapshot.


## Latest override — B40 LOADERPDD1

This section supersedes the B39 DEVICE1 next-candidate target above.

B40 LOADERPDD1 is now **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

B39 proved the first causal startup break is the canonical eiksrvs synchronous
call to `User::LoadPhysicalDevice("EUART1")`, which maps to
`!Loader` opcode 4 / `ELoadPhysicalDevice`. The B28-cache Loader had no
handler, so the historical generic dispatcher logged and dropped the request,
wedging eiksrvs before System GUI session-factory installation.

B40 narrowly ports upstream EKA2L1 commit
`0987745cc0bde96511fce2a4bfefcfd8fbced3dc`:

- adds `Loader::LoadPhysicalDevice`;
- registers opcode 4 / `ELoadPhysicalDevice`;
- validates descriptor argument 1;
- invalid descriptor -> `KErrArgument`;
- valid HLE-backed PDD -> `KErrNone`;
- adds `[NBOOT2][LOADER_PDD]` entry/completion evidence.

B40 deliberately does **not** import generic unknown-IPC completion commit
`9f28c76fe0f54f43a39319da5f4042c853505807`. Generic unknown IPC semantics
remain at the B39 baseline.

TDD / build evidence:

- canonical RED commit: `b17881d811da6f8ba63af165073d3994c84be745`
- RED run/job: `35764848484 / 106871644557`
- expected RED: missing `[NBOOT2][LOADER_PDD]`
- first GREEN attempt `af9f5bbb23b74174c1c3655b3c9f5383ccf353a2` stopped before compile on an over-specific apply-script registration anchor; no IPA produced
- final B40 code HEAD: `adde620f6c2b57bec69268b32a889035e0a3eb51`
- final GREEN run/job: `35765468574 / 106873756994`
- B29-B40 apply/tests: PASS
- full regressions: PASS
- iOS compile/link: PASS
- binary invariants including `[NBOOT2][LOADER_PDD]`: PASS
- IPA package/upload: PASS
- compile requests 149 / hits 147 / misses 2 / compilation failures 0
- NOJAVA / MANIC3 preserved

IPA:

- artifact ID: `10711662557`
- artifact ZIP digest: `sha256:ce9f6e97866cee9ff3ffd41255f3cc4db1b7ce1a6bd8b3f8d15e7864c6eaf378`
- unsigned IPA SHA-256: `782d03a38bd3f87c0b0394b5d8753ec8599f8d8ef23b6d7168f3dc92faf3b5f6`
- expires: 2026-10-06

Audit artifact:

- ID: `10711767320`
- digest: `sha256:2e03559f71c68a3ddad7c2a2eba02e65f63d71b5d3530b92a97453b398ca9cbd`

Preserve:

- stock Nokia `avkonfep.dll`;
- firmware SYSSTART ownership;
- native fbserv;
- B26/B34 Exit Emulator choreography;
- B36 implicit WindowServer handle carry;
- B37 batch signal deferral;
- B38/B39 diagnostics;
- Leave/TRAP and KErrCancel semantics;
- loader rooted-library behavior;
- EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill / 0xDF leave_start / 0xE0 leave_end;
- NOJAVA / MANIC3.

### Resume from here

Sign/install the B40 IPA and boot the same Nokia 5800 RM-356 path. Allow startup
to proceed through the former eiksrvs/Loader boundary, then use **Thoát Emulator**
normally.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

First checks:

1. `[NBOOT2][LOADER_PDD] phase=enter name=EUART1`.
2. `[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0`.
3. canonical eiksrvs proceeds beyond the former opcode-4 stall.
4. healthy `!EikAppUiServer` / session-factory initialization appears, or a later blocker is localized.
5. the repeated B39 CServer2 NULL-session AV family disappears or moves later.
6. B34 Exit Emulator remains healthy.

Do not promote B40 to an immutable functional milestone until device evidence
validates it.

Full snapshot:
- `docs/handoff/history/B40-LOADERPDD1.md`


## Latest override — B41 WSERVMESSAGEWINEXIT1

B40 device evidence validated the Loader PDD fix:
`[NBOOT2][LOADER_PDD] phase=enter name=EUART1` followed by
`phase=complete name=EUART1 result=0`.

A new host-side exit crash was then isolated when **Thoát Emulator** was
selected. The iOS crash report is `EXC_BAD_ACCESS / SIGSEGV` at address
`0x168` on the `Symbian OS thread`. The native stack is:

`screen::need_update_visible_regions <- canvas_base::set_visible <-
messagewin_anim_executor::~messagewin_anim_executor <- anim_dll::~anim_dll <-
window_server_client::~window_server_client <- window_server::disconnect <-
kernel_system::wipeout <- system_impl::~system_impl <- ios::os_thread`.

The bridge exit log stops at `phase=os_join_begin`, proving the host OS thread
dies during WindowServer/kernel wipeout before B34 can reach `os_join_done`.

B41 is now **BUILD-VALIDATED; DEVICE TEST REQUIRED**. It is a narrow
MessageWin-lifetime fix only: MessageWin captures a stable `kernel_system *`
while its canvas is live and, if `wipeout_in_progress()` is true, skips the
destructor's otherwise unnecessary `canvas_->set_visible(true)` call. Normal
MessageWin destruction outside wipeout keeps the original visibility restore.

B41 runtime marker:
- `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout`

TDD/build:
- canonical RED: `92dc4230524d52bb1ca6c42fa0c5077e460870c6`
- RED run/job: `35793893027 / 106968553796`
- implementation: `cfe2fd70f8630f718aab7780062000980273f5b5`
- final GREEN HEAD: `b43e59696d313da97c8845a1a20e78d9b6c762d7`
- GREEN run/job: `35794136142 / 106969339936`
- B29-B41 apply/tests: PASS
- full regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile failures: 0
- NOJAVA / MANIC3 preserved

IPA:
- artifact ID: `10723611386`
- unsigned IPA SHA-256:
  `0f6e4694af7cee6897fe0ebbe6b5e98c3374fa1cdb4f8118305b5b93cc7d172d`
- artifact digest:
  `sha256:d4069d008d0e8d615c8353c1b3236d2ea8aaa815f9d1db1836cafd103a1d2d15`

Preserve all B40 boot behavior, B34 shutdown choreography, B36/B37 WindowServer
semantics, B38/B39 diagnostics, Leave/TRAP behavior, EPOC94 mappings and
NOJAVA/MANIC3.

### Resume from here

Install/sign B41, boot the same Nokia 5800 path, then use **Thoát Emulator**.

Collect the usual three EKA2L1 logs. If iOS still crashes, also collect the new
`.ips`.

Acceptance:
1. B40 Loader PDD still completes `EUART1 result=0`.
2. During exit, B41 emits
   `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout` when relevant.
3. B34 reaches `phase=os_join_done`, then graphics join,
   `shutdown_threads_done` and `state_reset_done`.
4. no host iOS `EXC_BAD_ACCESS` occurs.

Full snapshot:
- `docs/handoff/history/B41-WSERVMESSAGEWINEXIT1.md`


## Latest override — B41 DEVICE1

This section supersedes the B41 device-test-required status above.

B41 WSERVMESSAGEWINEXIT1 is now **DEVICE-VALIDATED** and promoted to the latest
immutable functional milestone.

Device evidence from the 2026-09-23 test on the primary iPhone 12 Pro Max /
iOS 18.7 confirms both B40 and B41:

### B40 boot result is now device-validated

At `05:59:23.443`:

- `[NBOOT2][LOADER_PDD] phase=enter name=EUART1`
- `[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0`

The canonical eiksrvs instance continues beyond the former Loader opcode-4
stall and at `05:59:23.820` registers:

- `[NBOOT2][SERVER_REGISTER] process=eiksrvs[10003a4a]0001 server=!EikAppUiServer ...`

The previous B39 failure family is absent in this run:

- `[NBOOT2][EIKFEP_STATE]`: 0
- `[NBOOT2][EIKFAULT_AV]`: 0
- `[NBOOT2][EIKPOSTLEAVE_AV_FRAME]`: 0
- `EikAppUiServerThread ... KERN-EXEC 3`: 0
- `Unimplemented IPC call: 0x4 for server: !Loader`: 0

Therefore the B39 root-cause chain is closed:
`LoadPhysicalDevice(EUART1)` now completes, System GUI construction reaches
healthy `!EikAppUiServer` registration, and the downstream NULL-session AV
family disappears.

### B41 exit result is device-validated

The user selected **Thoát Emulator** at approximately `06:00:26`.

The B41 guard fires twice at `06:00:26.683`:

- `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout`
- `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout`

The exact shutdown sequence then completes:

- `06:00:26.676 phase=os_join_begin`
- `06:00:26.700 phase=os_join_done`
- `06:00:26.701 phase=graphics_join_done`
- `06:00:26.701 phase=shutdown_threads_done`
- `06:00:26.701 phase=state_reset_done`
- `06:00:26.701 phase=shutdown_done`
- `06:00:26.854 phase=normal_restart_done has_device=1`

The user explicitly confirms that B41 fixes the crash when exiting.

This validates the B41 causal model: during kernel wipeout the MessageWin
executor must not restore visibility through its borrowed canvas pointer.

### Promotion

Immutable functional branch:

- `nativeboot2-b41-wservmessagewinexit1`

Immutable/final validated code HEAD:

- `b43e59696d313da97c8845a1a20e78d9b6c762d7`

Build evidence remains:

- GREEN run/job: `35794136142 / 106969339936`
- B29-B41 apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Device log SHA-256:

- `EKA2L1(2).log`: `6ad6b13f5f8b15f77454aa11012a8f7738a590e0fd28d5bf15175f2017188a1a`
- `EKA2L1_Persistent(2).log`: `d43817c9b10340c5d46328ac335348f88b927a8027d05cfc21595ff34c8beae2`
- `EKA2L1_TakeThis(2).log`: `a09e9b668ae2f50e286d8c4389a7525d2dea4d7f00c2170c0a227b7f408c76e5`

Preserve B40 Loader PDD, B41 MessageWin wipeout guard, B34 exit choreography,
B36 handle carry, B37 batch deferral, stock AvkonFep, Leave/TRAP semantics,
EPOC94 mappings, NOJAVA and MANIC3.

Full device snapshot:
- `docs/handoff/history/B41-DEVICE1.md`


## Latest override — B42 SAHWRMABI1

B41 remains the latest **DEVICE-VALIDATED immutable functional milestone**.

B42 SAHWRMABI1 is now **BUILD-VALIDATED; DEVICE TEST REQUIRED** and is
diagnostic-only.

B41 device evidence exposed the next earlier startup boundary:

- HWRMServer loads Nokia `lightsadaptation.dll`;
- SAServer receives raw function `0x2000000A`;
- the old generic dispatcher logs it as unimplemented and leaves the request
  outstanding;
- about 30 seconds later SYSSTART begins HWRM failure recovery.

Targeted Exa research did not locate a reliable public Nokia/Symbian definition
of the proprietary response ABI for raw function `0x2000000A`. B42 therefore
does not synthesize a response.

B42 registers only the exact raw function and emits:

- `[NBOOT2][SA_HWRM_ABI]`

The marker captures raw/logical/transport function fields, IPC flag, caller
process/thread/session, all four raw arguments, argument types, descriptor
sizes/maxima, descriptor presence and up to 32 bytes per descriptor.

Diagnostic semantic guard:

- no descriptor writes;
- no descriptor resize;
- no `ctx.complete(...)`;
- no B15 pending-event completion;
- returns with the request still outstanding, preserving the historical
  unknown-IPC behavior.

TDD/build:

- RED test-file commit: `b7ac73c07cacb7ba70c17394f936a37c48af733d`
- RED manifest commit: `51eda041a207e9fb7216ffafe412921da545a700`
- RED run/job: `35798200345 / 106982294325`
- expected RED: missing `[NBOOT2][SA_HWRM_ABI]`
- B29-B41 apply/tests before RED: PASS
- B20-B28 regressions before RED: PASS
- B42 code HEAD: `c57838dbbe9f8b0d66fe5c5b79505eafa7b10da3`
- GREEN run/job: `35798478420 / 106983166866`
- manifest validation: PASS
- B29-B42 apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- Mach-O B42 invariant: PASS
- IPA package/upload: PASS
- compile requests 149 / hits 148 / misses 1 / failures 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

`d75133e979e6bbea0ed28dbbb9c4b94f246f7ce8afbb991c2333d8349e7d74c7`

IPA artifact:

- ID: `10724414948`
- ZIP digest:
  `sha256:f111831f2719446addd6fc844f83362d2801b5faac5eecaf1059ba36f45da736`
- expires: 2026-10-06

Audit artifact:

- ID: `10724499913`
- digest:
  `sha256:1d165a183533dca7d95f361a8ba790e6f7282330ccdbe7484af79b2725f88366`

Preserve B40 Loader PDD, B41 MessageWin wipeout guard, B34 exit choreography,
B36 handle carry, B37 batch deferral, stock AvkonFep, firmware SYSSTART
ownership, Leave/TRAP semantics, EPOC94 mappings, NOJAVA and MANIC3.

### Resume from here

Sign/install B42 and boot the same Nokia 5800 RM-356 path. B42 is not expected
to fix HWRM; the approximately 30-second HWRM timeout may remain by design.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

First checks:

1. `[NBOOT2][SA_HWRM_ABI]` appears for raw `0x2000000A`.
2. Caller process/thread/session identifies the HWRM/light-adaptation path.
3. Slot types/sizes/maxima and descriptor previews reveal the real request ABI.
4. The old generic `Unimplemented IPC call: 0x2000000a for server: SAServer`
   is replaced by the B42 marker.
5. B40 `EUART1 result=0` remains intact.
6. B41 Exit Emulator remains healthy.

Use B42 device evidence to decide whether B43 can implement a narrow response.
Do not promote B42 to an immutable functional milestone.

Full snapshot:
- `docs/handoff/history/B42-SAHWRMABI1.md`
