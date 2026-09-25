# EKA2L1 Nokia 5800 NativeBoot — Current Project Handoff

Updated: 2026-09-25
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Active development branch: nativeboot2-current
Latest FASTBUILD1 CI implementation commit: ab4415d0f94b002d01e6ea2035600a2dddc99c1d
Latest immutable functional milestone: B41 WSERVMESSAGEWINEXIT1
Latest immutable functional code HEAD: b43e59696d313da97c8845a1a20e78d9b6c762d7
Latest immutable functional branch: nativeboot2-b41-wservmessagewinexit1
Latest device-validated functional milestone: B41 WSERVMESSAGEWINEXIT1
Latest device snapshot: docs/handoff/history/B41-DEVICE1.md
Latest device diagnostic snapshot: docs/handoff/history/B46-DEVICE1.md
Latest build diagnostic snapshot: docs/handoff/history/B47-AKNSKINTFXSTATE1.md
B40 status: DEVICE-VALIDATED — Loader PDD root cause fixed; !EikAppUiServer registers and B39 AV family is gone
B41 status: DEVICE-VALIDATED — Thoát Emulator host crash fixed
B42 status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — HWRM raw 0x2000000A ABI captured; 30 s timeout proven non-final
B43 status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — akncapserver TfxServer miss -> same-thread Leave(-1) proven twice; provider path still absent
B44 status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — TFX P&S object is initially undefined; HLE AknSkinServer active; native TFX provider startup absent
B45 status: DEVICE-OBSERVED; ROUTE NOT ACTIVATED — guard failed because runtime epoc enum=10 and Z-profile is mounted after services init
B46 status: DEVICE-OBSERVED; ROUTE SUCCESS — guest launches native AknSkinSrv.exe, !AknSkinServer registers, clients bind server_hle=0; TFX provider remains absent
B47 status: BUILD-VALIDATED; DEVICE TEST REQUIRED — diagnostic-only native AknSkin TFX state/Wserv/ECom boundary tracing
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


## Latest override — B42 DEVICE1

B42 SAHWRMABI1 is now **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.
B41 remains the latest immutable functional milestone.

The exact HWRM SAServer ABI is now captured:

```text
[NBOOT2][SA_HWRM_ABI]
raw_func=0x2000000A
logical_func=0xA
transport_bits=0x20000000
ipc_flag=0x924
process=!HWRMServer
thread=!HWRMServer
session=808
types=[4,4,4,4]
sizes=[12,4,12,4]
max=[12,4,12,4]
slot0=[0x00010008,0x2000000A,0x00000000]
slot1=[0x000000F3]
slot2=[0x00010008,0x2000000B,0x00000000]
slot3=[0x00700390]
completion=UNCHANGED_PENDING
```

The request/response-template pairing is structurally consistent with the
already proven SAClient transport shape from B14/B19: slot 0 carries the request
envelope and slot 2 carries a prebuilt response envelope. B42 still does not
assign semantic meaning to slot1 0xF3 or synthesize a slot3 response.

The HWRM stall is now time-proven:

- B42 HWRM request: `07:48:39.975`
- SYSSTART HWRM kill attempt: `07:49:09.972`
- delta: approximately `29.997 s`

Startup nevertheless continues to healthy B40 System GUI registration:

- `07:49:10.977 LOADER_PDD EUART1 result=0`
- `07:49:11.356 !EikAppUiServer registered`

Therefore HWRM is a real 30-second delay/recovery event but not the final boot
stopper in this device run.

A stronger repeated later family is now selected for the next diagnostic:

```text
07:49:10.788 eiksrvs -> MISSING_SERVER TfxServer
07:49:10.971 ViewServerThread -> Leave(-1)

07:49:11.396 akncapserver...0002 -> MISSING_SERVER TfxServer
07:49:11.499 akncapserver -> Leave(-1)
07:49:11.536 akncapserver self-kill reason=-1

07:49:12.183 akncapserver...0003 -> MISSING_SERVER TfxServer
07:49:12.276 akncapserver -> Leave(-1)
07:49:12.308 akncapserver self-kill reason=-1
```

The second akncapserver failure is followed by SYSSTART shutdown handling and
SAServer `0x71` / `EExecuteShutdown`.

Runtime also loads/references transition-effects components:
`akntransitionutils.dll`, `aknlistloadertfx.dll`, and
`alfredserver_reg.rsc`, but no `TfxServer` registration is observed.

B41 exit remains healthy in the same run:

- two `[NBOOT2][WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout`
- `os_join_done`
- `graphics_join_done`
- `shutdown_threads_done`
- `state_reset_done`
- `shutdown_done`
- `normal_restart_done has_device=1`

Preferred next candidate:

**B43 TFXSERVERDIAG1**

Scope should remain diagnostic:
- trace TfxServer server-name/executable/plugin resolution;
- capture CreateSession result/error for eiksrvs and akncapserver;
- resolve the immediate Leave(-1) callsites;
- do not fabricate a TfxServer session yet;
- preserve B42 HWRM pending behavior and all B40/B41 invariants.

Full device snapshot:
- `docs/handoff/history/B42-DEVICE1.md`


## Latest override — B43 TFXSERVERDIAG1

B43 is now **BUILD-VALIDATED; DEVICE TEST REQUIRED**.
B41 remains the latest immutable functional milestone; B42 remains the latest
device-observed diagnostic milestone.

### Scope clarification

B43 is interoperability/emulator startup debugging for Nokia 5800/Symbian
firmware inside EKA2L1. It does not attack networks, bypass access controls,
deploy malware, or access external systems. It only observes the guest
client/server startup chain.

### Why B43

B42 device evidence shows a repeated causal family:

```text
eiksrvs       -> TfxServer missing -> Leave(-1)
akncapserver1 -> TfxServer missing -> Leave(-1) -> self-kill
akncapserver2 -> TfxServer missing -> Leave(-1) -> self-kill
```

The second akncapserver failure is followed by SYSSTART shutdown handling.
B43 therefore instruments this exact path without creating a fake server.

### Runtime markers

- `[NBOOT2][TFX_SESSION]`
- `[NBOOT2][TFX_SESSION_FRAME]`
- `[NBOOT2][TFX_SESSION_STACK]`
- `[NBOOT2][TFX_LEAVE]`
- `[NBOOT2][TFX_RESOLVE]`
- `[NBOOT2][TFX_SERVER_REGISTER]`

The missing-server path still returns `epoc::error_not_found` and logs
`behavior=UNCHANGED_KErrNotFound`.

### Build evidence

- canonical RED run/job: `35809951781 / 107019069011`
- expected RED: missing `[NBOOT2][TFX_SESSION]`
- B29-B42 before RED: PASS
- implementation: `8b3e6eb2c5ee90e88f49cf20037f5b56e5bb61f1`
- intermediate compile run/job: `35810185857 / 107019798922`
- intermediate failure: incomplete `config::state` in loader diagnostics
- final code HEAD: `00362ae8faedd6bda130b32ba39d3f051a02ef68`
- GREEN run/job: `35810358190 / 107020337672`
- B29-B43 apply/tests: PASS
- regressions: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile requests/hits/misses: `149 / 148 / 1`
- compilation failures: `0`
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

`452346807417961e9c6fa85a7f5fc848b76ff65bb95cc861de1656c819be75c8`

IPA artifact:
- ID `10729741855`
- digest
  `sha256:5b8c50e8e38acae1eed2119d935bfa17f4c210c9c65a9a0ea3e8c3093e804010`

### Resume from here

Device-test B43 on the same RM-356 path. Do not expect a boot-progress change;
B43 deliberately preserves `KErrNotFound`.

Send the usual three EKA2L1 logs. Inspect TFX_RESOLVE, TFX_SESSION provenance,
TFX_LEAVE correlation, and any TFX_SERVER_REGISTER event. Preserve B42, B40,
B41, stock AvkonFep, firmware SYSSTART ownership, Wserv behavior, NOJAVA and
MANIC3.

Full snapshot:
- `docs/handoff/history/B43-TFXSERVERDIAG1.md`


## Latest override — B43 DEVICE1

B43 TFXSERVERDIAG1 is now **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.
B41 remains the latest immutable functional milestone.

### Direct akncapserver causal chain is proven

B43 captures three TfxServer session misses. The two akncapserver attempts are
directly correlated on the same guest thread:

```text
09:55:45.437 akncapserver...0002 TfxServer -> KErrNotFound
09:55:45.545 same process/thread -> [TFX_LEAVE] correlated=1 Leave(-1)
09:55:45.575 self-kill reason=-1

09:55:46.202 akncapserver...0003 TfxServer -> KErrNotFound
09:55:46.296 same process/thread -> [TFX_LEAVE] correlated=1 Leave(-1)
09:55:46.327 self-kill reason=-1
```

The gaps are approximately 108 ms and 94 ms.

Both Leave(-1) traces resolve to the same Avkon/AknSkins module/offset pattern,
including:

- `avkon.dll + 0xA73DC / 0xA742C / 0xA741C`
- `AKNSKINS.DLL + 0x164 / 0x384`
- `euser.dll + 0x95B0 / 0x1C83C`

This makes the akncapserver TfxServer failure family deterministic.

The earlier eiksrvs TfxServer miss is **not** same-thread correlated:
CreateSession occurs on `EikAppUiServerThread`, while the subsequent
Leave(-1) is on `ViewServerThread`.

### Provider-resolution result is negative

- `[NBOOT2][TFX_RESOLVE]`: 0
- `[NBOOT2][TFX_SERVER_REGISTER]`: 0
- no runtime `alfredserver.exe` process observed
- no UID `0x10282845` observed

The runtime does load `akntransitionutils.dll` and
`aknlistloadertfx.dll`, and AppArc reads `alfredserver_reg.rsc`, but no
public `TfxServer` endpoint is registered.

### Public-source architecture

Public Symbian source confirms:

- Avkon explicitly searches for server name `TfxServer`;
- AknCapServer is compiled against transition-effects components;
- Alfred server UID3 is `0x10282845` and its registration is background/hidden;
- ALF clients launch Alfred through AppArc on demand;
- Alfred constructs transition effects and loads a TFX ECom plugin;
- `tfxsrvplugin.dll` has DLL UID `0x10282DBA`;
- TFX public UID is `0x10281F7D`;
- the transition server is described as being loaded into Wserv through a
  CAnimDll plugin;
- Alfred's internal TFX client connects to the ALF streamer/bridge endpoint.

Therefore B44 must diagnose the provider-startup chain; it must not assume that
`alfredserver.exe` itself is the public TfxServer process.

### Baseline preservation

- B42 SA_HWRM_ABI still present.
- B40 EUART1 still completes with result 0.
- `!EikAppUiServer` still registers.
- B41 Exit Emulator still reaches `normal_restart_done has_device=1`.

### Next candidate

**B44 ALFTFXSTARTDIAG1**

Trace Alfred UID `0x10282845` AppArc launch, ALF app-server/streamer endpoint
creation, TFX ECom plugin resolution/load (`0x10282DBA`), and the
`0x10281F7D` TFX status path where safely observable.

Keep TfxServer miss semantics unchanged until the missing provider-startup step
is identified.

Full snapshot:
- `docs/handoff/history/B43-DEVICE1.md`


## Latest override — B44 ALFTFXSTARTDIAG1

B44 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.
B41 remains the latest immutable functional milestone. B43 remains the latest
device-observed diagnostic milestone.

### Why B44 changed direction after Deep Research

Primary Symbian/Nokia source shows the highest-information provider path is:

```text
AknSkinSrv
  -> ECom TFX implementation 0x10282DBD / 0x10282DBC
  -> tfxsrvplugin.dll (UID 0x10282DBA)
  -> TFX P&S 0x10207218 / key 0x2
  -> RAlfTfxClient::Open()
  -> CreateSession("alfstreamerserver")
  -> ALF backend
  -> public TfxServer registration
```

The Alfred/AppArc path is observed in parallel:

```text
GetAppInfo(0x10282845)
  -> alfredserver_reg.rsc
  -> process create alfredserver.exe / alfserver.exe
  -> ALF AppServer
```

B44 does not assume either path succeeds.

### Scope clarification

B44 is interoperability/emulator startup diagnostics only. It does not attack
networks, bypass access control, deploy malware, access external systems, or
change guest authorization.

B44 does **not**:
- create/fake TfxServer;
- force-launch Alfred;
- force ECom implementation mapping;
- write the TFX P&S running bit;
- synthesize unknown IPC completion;
- alter B42 HWRM pending behavior.

### One-device-run marker set

- `[NBOOT2][ALF_ROM_ARTIFACT]`
- `[NBOOT2][ALF_APPARC_REG]`
- `[NBOOT2][ALF_APPARC_GETINFO]`
- `[NBOOT2][ALF_PROC_CREATE]`
- `[NBOOT2][TFX_ECOM_RSC]`
- `[NBOOT2][TFX_ECOM_DLL]`
- `[NBOOT2][TFX_PS]`
- `[NBOOT2][TFX_MANIFEST]`
- `[NBOOT2][ALF_SESSION]`
- `[NBOOT2][ALF_SERVER_REGISTER]`

B43 TfxServer/Leave markers remain intact.

### TDD/build

Canonical RED:
- test commit: `ff910c5e8072b27b737b07e376564cce8c5b9db2`
- RED manifest commit: `e177e561a166e6d902c93841f3be98daa2186e5d`
- RED run/job: `35816770777 / 107039852137`
- B29-B43 apply/tests: PASS
- B20-B28 regressions: PASS
- expected failure: missing `[NBOOT2][ALF_SESSION]`

Implementation lineage:
- initial multi-boundary instrumentation: `ffaf8e737e5045560e659cf79f6d7a014858ce8a`
- bounded session patch: `ea545f367dc1cb5005e03888ef83f82e6553b778`
- hardened P&S/AppArc descriptor handling: `3740f53a535e686709e202a91aa43f73ede20771`
- stable category/key P&S probes: `4606b77e338bb663a2973911c74a8d2d803fbb76`
- B28-compatible AppArc diagnostics: `d2875cc4fab1c481cb9cf708f66e80a23823e162`
- branch-independent FileServer probes: `98c0cd66ac0d82d8a780fe005b775588fd76a4ab`
- final implementation: `d9f8e8fabecb3f5af4b28f10413166e6fa07d4f6`
- binary-invariant commit: `b7810836cbb252dcf4232377345e84dfb4037797`

The intermediate failures were patch-contract/anchor mismatches against the
older B28 bootstrap source; no guest-visible functional workaround was added.

### Canonical GREEN

- implementation HEAD: `d9f8e8fabecb3f5af4b28f10413166e6fa07d4f6`
- canonical build HEAD: `b7810836cbb252dcf4232377345e84dfb4037797`
- run/job: `35818238348 / 107044317789`
- FASTBUILD1 manifest: VALID
- B29-B44 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- B44 Mach-O marker invariants: PASS
- IPA package/upload: PASS
- NOJAVA / MANIC3: PRESERVED
- compile requests: 149
- cache hits: 149
- cache misses: 0
- hit rate: 100%
- actual compilations: 0
- compilation failures: 0

Unsigned IPA SHA-256:

`5797d71f39bb790ebbae605459f03ce9d248fd713e8a3def0fa450a51eba2870`

IPA artifact:
- ID: `10732596370`
- size: 19,905,507 bytes
- ZIP digest:
  `sha256:41bbc1cfffac4def2e248ddaf0c4c9702cbc6ad4ff888fae52a0ec9a4619a5cf`
- expires: 2026-10-07

Audit artifact:
- ID: `10732566416`
- digest:
  `sha256:37c73a442c9fb28287b9efcd6a735a652cc21860230f51547103d5d7aa930d28`

Downloaded IPA was re-hashed locally and matches CI exactly.

### Device-test goal

B44 is not expected to boot farther by itself. The purpose is to classify the
missing provider stage in one run.

Test the same RM-356 path, let the B42 ~30 s HWRM delay remain, wait through
the akncapserver/TfxServer window, then use Thoát Emulator normally and send:

- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Read the first missing boundary in this order:

```text
ROM artifact
-> AppArc/ECom request
-> tfxsrvplugin resource/DLL
-> TFX P&S
-> alfstreamerserver
-> Alfred/ALF AppServer
-> TfxServer registration
-> akncapserver session result
```

Do not implement a functional B45 until B44 device evidence identifies the
first missing provider-startup boundary.

Full snapshot:
- `docs/handoff/history/B44-ALFTFXSTARTDIAG1.md`


## Latest device override — B44 DEVICE1

B44 device evidence identifies the first strong provider-startup boundary.

### Log integrity

- `EKA2L1(5).log`
  SHA-256 `f389ad365148cb69bc810db8daa6f363c560ea12a56ef44566a2b4a6820675af`
- `EKA2L1_Persistent(5).log`
  SHA-256 `6b777b8a06c7a16ceae10bb37356c80622e9c7620b59e60299154fd0a8d6adda`
- `EKA2L1_TakeThis(5).log`
  SHA-256 `cf5bae4037dcdd88b291741b4cd0c1ac424bbdf482e9b4676fd618b153f9477c`

### New B44 evidence

At `11:38:05.396` eiksrvs attaches:

```text
category=0x10207218 key=0x2
Property ... has not been defined before
[NBOOT2][TFX_PS] op=attach ...
```

This is stronger than merely observing value zero: EKA2L1's `property_attach`
creates a placeholder property object when no definition exists. Therefore the
first TFX status property access proves **the TFX status property was undefined
before the client attach**.

The same placeholder object is then attached by both akncapserver attempts.

No B44 evidence appears for:
- `tfxsrvplugin.dll`;
- TFX ECom resource/UID `0x10282DBA`;
- `alfstreamerserver` client session;
- Alfred process creation;
- Alfred GetAppInfo UID `0x10282845`;
- final `TfxServer` registration.

However generic AppArc evidence proves the Alfred registration resource exists
and is parsed:
- `Z:\private\10003a3f\apps\alfredserver_reg.rsc` opens successfully twice;
- AppList reports UID `0x10282845` during registry scan.

Thus the registration file is not the first missing artifact.

### HLE AknSkinServer boundary

At `11:38:05.377` the device creates:

```text
AknsSrvSharedMemoryChunk
```

EKA2L1 source shows this exact chunk is created by the HLE
`akn_skin_server::do_initialisation()`.

Upstream EKA2L1 service initialization also creates `akn_skin_server`
unconditionally for this service set, and the HLE server name is
`!AknSkinServer`.

The HLE `do_initialisation()` initializes:
- skin settings;
- icon configuration;
- FBS linkage;
- shared skin chunk;
- semaphore/mutex;
- chunk maintainer;
- active skin merge.

It contains **no ECom TFX provider creation, tfxsrvplugin load, P&S TFX status
definition, RAlfTfxClient startup, Alfred startup, or TfxServer provider
registration**.

Device logs contain no native `aknskinsrv` process start.

This yields the current high-confidence provider boundary:

```text
RM-356 client
  -> !AknSkinServer
  -> EKA2L1 HLE skin implementation
  -> skin data/chunk works
  X native transition-effects provider startup does not occur
  -> TFX P&S remains undefined
  -> no tfxsrvplugin / ALF provider path
  -> TfxServer absent
  -> akncapserver CreateSession returns KErrNotFound
  -> same-thread Leave(-1)
```

Do not yet fake TfxServer or simply force-launch Alfred. The next build should
target this HLE/native skin-provider boundary explicitly.

### B43 causal chain repeats unchanged

- eiksrvs TfxServer miss: `11:38:05.397`
- ViewServerThread Leave(-1): `11:38:05.579` (~182 ms later)
- akncapserver #1 miss: `11:38:06.009`
- correlated Leave(-1): `11:38:06.122` (~113 ms)
- akncapserver #2 miss: `11:38:06.781`
- correlated Leave(-1): `11:38:06.872` (~91 ms)

No `TfxServer` registration occurs.

### Preserved milestones

B42 HWRM:
- ABI marker at `11:37:34.518`;
- SYSSTART kill attempt at `11:38:04.514`;
- delay ~29.996 s.

B40:
- EUART1 PDD enter/complete at `11:38:05.586`;
- `!EikAppUiServer` registers at `11:38:05.945`.

B41:
- two `[WSERV_MESSAGEWIN_EXIT] phase=skip_restore_wipeout` at `11:41:05.395`;
- `shutdown_done` at `11:41:05.413`;
- `normal_restart_done has_device=1` at `11:41:05.532`.

No KERN-EXEC or host access violation is present in the B44 test window.

Full snapshot:
- `docs/handoff/history/B44-DEVICE1.md`


## Latest build override — B45 AKNSKINNTFX1

B45 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.
B41 remains the latest immutable functional milestone.
B44 remains the latest device-observed diagnostic milestone.

### Primary-source finding that justifies B45

Symbian/Nokia source confirms that the native AknSkin server is not merely a
skin-data service. It owns the transition-effects startup path.

`AknSkinSrvMain.mmp`:
- target: `AknSkinSrv.exe`
- target path: `/system/programs`
- UID3: `0x10207114`

`AknSkinSrv.mmp`:
- target: `AKNSKINSRV.dll`
- UID3: `0x10005A35`
- links `ecom.lib` and `ws32.lib`

`RAknsSrvSession::Connect()`:
- first calls `CreateSession("!AknSkinServer")`;
- on `KErrNotFound` / `KErrServerTerminated`, calls `StartServer()`;
- retries the session after server startup.

`StartServer()`:
- `RProcess::Create(KAknSkinSrvExe,...)`;
- Rendezvous;
- Resume;
- WaitForRequest.

Native `CAknsSrv::PrepareMergedSkinContentUnprotectedL()`:
- merges skin/wallpaper state;
- then calls `StartTransitionSrvL(tfxServerRunning)`.

`LoadTfxSrvPluginL()`:
- ECom controller implementation `0x10282DBD`;
- ECom server implementation `0x10282DBC`.

Therefore the B44 HLE/native boundary is source-confirmed.

### B45 behavior

For **native_phone_boot + EPOC9.4 only**, B45 checks for a native ROM server
image:

- `z:\sys\bin\aknskinsrv.exe`
- legacy `z:\system\programs\aknskinsrv.exe`

If either exists, B45 does **not** pre-create EKA2L1's HLE
`akn_skin_server`. This intentionally restores the guest-visible
`KErrNotFound` expected by the stock client so that **the guest client itself**
may execute its normal `StartServer()` path.

If no native image exists, or outside native_phone_boot/EPOC9.4, HLE behavior is
unchanged.

B45 does not directly launch AknSkinSrv.exe from host code.

### B45 markers

- `[NBOOT2][AKNSKIN_ROUTE]`
  - `phase=hle_skip`
  - `phase=hle_keep`
- `[NBOOT2][AKNSKIN_SESSION]`
  - request / lookup / missing / found
  - reports `server_hle`
- `[NBOOT2][AKNSKIN_NATIVE_PROC]`
  - guest process-create request/result
- `[NBOOT2][AKNSKIN_NATIVE_REGISTER]`
  - native `!AknSkinServer` registration
- `[NBOOT2][AKNSKIN_ROM]`
  - native EXE/DLL existence snapshot
  - expected EXE UID3 `0x10207114`
  - expected DLL UID3 `0x10005A35`

All B44 ALF/TFX probes remain present, so one device run can show whether the
native AknSkin route reaches TFX ECom, P&S, ALF, and TfxServer.

### Semantic guard

B45 does not:
- fabricate TfxServer;
- force-run Alfred;
- synthesize ECom resolution;
- define/set TFX P&S on behalf of the guest;
- synthesize unknown IPC completion;
- alter B42 HWRM behavior;
- alter non-native-phone-boot modes;
- alter non-EPOC9.4 service routing;
- remove HLE if native AknSkinSrv image is absent.

### TDD/build

RED:
- test contract: `2c19fac5446e8e3fddf37a991094a927e184e23d`
- RED manifest: `760df37fe003a3899b778c456c253a7aad67ce4c`
- RED run/job: `35820882559 / 107052262345`
- B29-B44: PASS
- B20-B28 regressions: PASS
- expected fail: missing `[NBOOT2][AKNSKIN_ROUTE]`

Implementation:
- initial: `b6873465a60f3d6eb1fe17e6e60efb99219274bc`
- manifest activation: `6cdd56945ae6a0910c24ab6c253a2c8f2a8d1962`
- final route-anchor/UID fix:
  `512f30981971f340dd45d2828754856782076122`

Binary invariant commit:
- `956b3f4df2354af31c5ca017fd3b004f58b13b5e`

Canonical GREEN:
- run/job: `35821489397 / 107054091391`
- B29-B45 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- B45 Mach-O marker invariants: PASS
- IPA package/upload: PASS
- compile requests: 149
- cache hits: 149
- cache misses: 0
- hit rate: 100%
- actual compilations: 0
- compilation failures: 0

Unsigned IPA SHA-256:

`0a4f794ab29943d97cf5613ade8558852a482c07ca3931a07513adc5e7d361e6`

IPA artifact:
- ID: `10733511496`
- size: 19,908,996 bytes
- ZIP digest:
  `sha256:f4d9da039f28db8038ba9e9f71f7442279c0096090beac77fa561f5b8c7e120b`

Audit artifact:
- ID: `10733377076`
- digest:
  `sha256:6586fdedc31ef93aab938353fbb5e2ec4c4dd8d0afacc64c5a8b4ad8a0e44917`

Local artifact re-hash matches CI exactly.

### Device-test expectations

B45 can behave very differently from B44 because HLE AknSkinServer may no
longer intercept the first client.

The most valuable outcomes are:

1. `AKNSKIN_ROUTE phase=hle_skip` and ROM artifact exists.
2. First `AKNSKIN_SESSION phase=missing`.
3. `AKNSKIN_NATIVE_PROC phase=request/result success=1`.
4. `AKNSKIN_NATIVE_REGISTER server=!AknSkinServer`.
5. Subsequent AknSkin sessions show `server_hle=0`.
6. B44 markers begin appearing:
   - `TFX_ECOM_RSC`
   - `TFX_ECOM_DLL`
   - `TFX_PS`
   - `ALF_SESSION`
   - `TfxServer` registration.

If native server startup fails before registration, B45 still gives the exact
new blocker via Loader/process/Leave traces. Do not add a fallback shim until
that device evidence is read.

Full snapshot:
- `docs/handoff/history/B45-AKNSKINNTFX1.md`


## Latest device override — B45 DEVICE1

B45 device test did **not** exercise the intended native AknSkinServer route.

### Log integrity

- `EKA2L1(6).log`
  SHA-256 `bf0c6b1c37fd932454f87ba527448018094547c38d7ed92b9fe5cda3fca1bbd4`
- `EKA2L1_Persistent(6).log`
  SHA-256 `178854edd9bd874fd3aa19d92e7a417af3d0b1f784afe469e2cb3e0cc108283b`
- `EKA2L1_TakeThis(6).log`
  SHA-256 `d3b45ea360bc86afa853c3fb3195123b584c83e6c20f4dac70072aa91230ddb7`

### First failure: EPOC-version guard mismatch

At native-mode service initialization:

```text
[NBOOT2][AKNSKIN_ROUTE]
phase=hle_keep
epoc=10
native_phone_boot=1
exe_sysbin=0
exe_legacy=0
```

Current EKA2L1 `epocver` ordering makes integer 10 equal
`epoc93fp1`; `epoc94` is a later enum value. Therefore B45's exact
`== epocver::epoc94` guard is false on the current RM-356 runtime even though
this firmware path otherwise uses the project's S60v5 compatibility behavior.

Do not reuse this enum equality as the B46 RM-356 discriminator.

### Second failure: ROM existence was checked before Z-profile mount

Chronology:

```text
15:05:08.361 ROM profile selected
15:05:08.367 SYM.ROM mapped
15:05:08.368 initialize HLE services
15:05:08.368 B45 checks Z:\sys\bin\aknskinsrv.exe -> exists=0
15:05:08.369 active RM-356 profile announced
15:05:08.369 Z profile mount announced
```

Thus B45 performs the `io_system::exist()` test one initialization step too
early for the extracted Z-profile overlay.

Historical firmware-install logs already prove this RM-356 package contains:

- `Z:\sys\bin\aknskinsrv.exe`
- `Z:\sys\bin\aknskinsrv.dll`

So B45's `exists=0` must not be interpreted as the firmware lacking the
native skin server.

### Consequence

HLE `!AknSkinServer` remains active.

Observed native-mode sessions:

```text
eiksrvs      -> !AknSkinServer found=1 server_hle=1
akncapserver -> !AknSkinServer found=1 server_hle=1
akncapserver -> !AknSkinServer found=1 server_hle=1
AknIconSrv   -> !AknSkinServer found=1 server_hle=1
```

There is no:
- `AKNSKIN_SESSION phase=missing`;
- `AKNSKIN_NATIVE_PROC`;
- `AKNSKIN_NATIVE_REGISTER`.

Therefore the stock `RAknsSrvSession::Connect()->StartServer()` route was
never reached.

### B44 failure family repeats unchanged

TFX status P&S is again undefined before first attach.

No:
- `TFX_ECOM_RSC`;
- `TFX_ECOM_DLL`;
- `ALF_SESSION`;
- `ALF_SERVER_REGISTER`;
- `TfxServer` registration.

The two akncapserver causal chains remain:

- first TfxServer miss -> correlated Leave(-1): ~106 ms;
- second TfxServer miss -> correlated Leave(-1): ~99 ms.

### Preserved milestones

B42:
- HWRM raw `0x2000000A` marker remains;
- SYSSTART kill attempt follows ~29.996 s later.

B40:
- `EUART1` PDD enter/complete result 0;
- `!EikAppUiServer` registers successfully.

B41:
- two MessageWin wipeout guards;
- `os_join_done`;
- `graphics_join_done`;
- `shutdown_threads_done`;
- `state_reset_done`;
- `shutdown_done`;
- `normal_restart_done has_device=1`.

No `KERN-EXEC`, `EXC_BAD_ACCESS`, or host access-violation marker appears
in this device window.

### B46 direction

Do not change TFX/ALF semantics yet.

B46 should fix **route selection timing**, not the native server itself:

1. Do not use `epocver::epoc94` equality as the RM-356 gate.
2. Do not test the extracted Z-profile before it is mounted.
3. Use an RM-356/native-phone-boot discriminator available before HLE service
   creation, or move the route decision to a point after profile mount but
   before `akn_skin_server` is registered.
4. Preserve a fallback path for non-RM-356/non-native modes.
5. Keep all B44/B45 provenance markers so the first real native-start attempt
   captures process creation and registration.

Working name:
`NATIVEBOOT2-B46-AKNSKINROUTE2`.

Full snapshot:
- `docs/handoff/history/B45-DEVICE1.md`


## Latest build override — B46 AKNSKINROUTE2

B46 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.
B41 remains the latest immutable functional milestone.
B45 DEVICE1 remains the latest device-observed diagnostic milestone until B46
device logs arrive.

### Why B46 exists

B45 device logs proved its native AknSkin route never activated because:
- runtime reported enum integer 10 instead of matching exact `epocver::epoc94`;
- B45 checked `Z:\sys\bin\aknskinsrv.exe` before the RM-356 Z-profile
  overlay was mounted, so the result was a false `exists=0`.

Historical firmware extraction logs independently prove the RM-356 package
contains both `aknskinsrv.exe` and `aknskinsrv.dll`.

### B46 route

B46 uses device-manager metadata already available before HLE service creation:

```text
current_device = sys->get_device_manager()->get_current()
firmware_code starts with rm-356 / RM-356
native_phone_boot == true
```

If both conditions hold, EKA2L1 does **not** pre-create HLE
`akn_skin_server`.

All other devices and non-native-phone-boot modes retain the HLE.

B45's epoc94 and pre-mount Z probes remain in the binary as diagnostics only;
they no longer gate the route.

### New marker

`[NBOOT2][AKNSKIN_ROUTE2]`

Expected native RM-356 line:

```text
decision=skip_hle
firmware_code=<RM-356 profile>
native_phone_boot=1
behavior=GUEST_NATIVE_ROUTE
```

B45 markers remain:
- `AKNSKIN_ROUTE`
- `AKNSKIN_SESSION`
- `AKNSKIN_NATIVE_PROC`
- `AKNSKIN_NATIVE_REGISTER`
- `AKNSKIN_ROM`

B44 TFX/ALF diagnostics also remain.

### Semantic guard

B46 does not:
- change the global Symbian/EPOC version;
- fake `TfxServer`;
- directly launch `AknSkinSrv.exe`;
- force Alfred;
- synthesize ECom success;
- define/set TFX P&S for the guest;
- complete unknown IPC;
- alter B42 HWRM behavior.

The stock guest client must still decide whether to call its own
`StartServer()` after receiving the real `KErrNotFound`.

### TDD/build

Canonical RED:
- test commit: `c2e6477a3bbf9424a3e7dc33d0191f7ba3506517`
- RED manifest: `79120778aa07de6a8e727d6ae39735ee717b88cc`
- run/job: `35840641091 / 107114600500`
- B29-B45: PASS
- B20-B28 regressions: PASS
- expected fail:
  `missing in B46 route marker: [NBOOT2][AKNSKIN_ROUTE2]`

Implementation:
- route2 implementation: `e38c0b38211d0cf19b19eba3fdbfc739ccddcd10`
- manifest activation: `abb40f03b0a12bf64d51b91e139466d732fceafc`
- binary invariant: `fc15de9e3c3e324142e33088990ca6ce25f27403`

Canonical GREEN:
- run/job: `35841200270 / 107116409392`
- FASTBUILD1 manifest: VALID
- B29-B46 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS compile/link: PASS
- B46 Mach-O marker invariant: PASS
- IPA package/upload: PASS
- compile requests: 149
- cache hits: 149
- cache misses: 0
- hit rate: 100%
- actual compilations: 0
- compilation failures: 0

Unsigned IPA SHA-256:

`a536852b1c4f916e0b99e6a97aa36a315f434578e3830ce8c67824e9a0aaeab9`

IPA artifact:
- ID: `10740833931`
- size: 19,912,068 bytes
- ZIP digest:
  `sha256:af91c0905dcd8d0e6026e3347ed00453c11da118a2c39dfc47f9f4065125fef7`

Audit artifact:
- ID: `10740769226`
- digest:
  `sha256:31bf2b832b768291a8ebae26b3ccd53ff7cd8ffbbdcc6de976b7a3bd335edbe1`

Downloaded IPA was re-hashed locally and matches CI exactly.

### Device-test acceptance

The first success criterion is **not** that the phone boots farther.

The critical sequence is:

```text
AKNSKIN_ROUTE2 decision=skip_hle
-> AKNSKIN_SESSION phase=missing for !AknSkinServer
-> AKNSKIN_NATIVE_PROC phase=request for aknskinsrv.exe
```

Then classify the first new boundary:

- native process result success/failure;
- `AKNSKIN_NATIVE_REGISTER`;
- subsequent skin session `server_hle=0`;
- TFX ECom/P&S/ALF/TfxServer activity.

If B46 reaches a new crash or Leave before registration, preserve that exact
evidence; do not add fallback behavior until it is analyzed.

Full snapshot:
- `docs/handoff/history/B46-AKNSKINROUTE2.md`


## Latest device override — B46 DEVICE1

B46 **successfully crossed the HLE/native AknSkin boundary**.

### Log integrity

- `EKA2L1(7).log`
  SHA-256 `15c5bff3997ee62c0332dc8ed0c0514c59ab6227cec06b6eb3009103ba10c902`
- `EKA2L1_Persistent(7).log`
  SHA-256 `802f308e0b562baa96319802bf62e25970962b1a31aac26c95a9a8fa4af4e132`
- `EKA2L1_TakeThis(7).log`
  SHA-256 `3be362dba20e5c07b96fb03f359aea149c5b9a8c845f4d359fe62428693dcb20`

### Native route: fully validated

At `16:24:00.897`:

```text
[AKNSKIN_ROUTE2] decision=skip_hle
firmware_code=RM-356
model=5800 XpressMusic
native_phone_boot=1
behavior=GUEST_NATIVE_ROUTE
```

At `16:24:32.583`, eiksrvs receives the intended real missing-server result:

```text
AKNSKIN_SESSION lookup found=0 server_hle=-1
AKNSKIN_SESSION missing result=-1
```

The stock guest immediately executes its own startup path:

```text
Trying to summon: AknSkinSrv.exe
AKNSKIN_NATIVE_PROC phase=request
path=Z:\System\Programs\AknSkinSrv.exe
```

At `16:24:32.591`:

```text
AKNSKIN_NATIVE_PROC phase=result
success=1
spawned=AknSkinSrv[10207114]0001
uid3=0x10207114
```

At `16:24:32.592`:

```text
AKNSKIN_NATIVE_REGISTER
process=AknSkinSrv[10207114]0001
server=!AknSkinServer
process_hle=0
```

At `16:24:32.995`, eiksrvs retries successfully:

```text
AKNSKIN_SESSION found server_hle=0
```

Later akncapserver, Home screen, aknnfysrv, AknIconSrv and other clients also
bind to the native server with `server_hle=0`.

This validates the full B46 acceptance chain.

### TFX provider is still absent

Despite a working native AknSkinSrv:

- `TFX_ECOM_RSC`: 0
- `TFX_ECOM_DLL`: 0
- `ALF_SESSION`: 0
- `ALF_SERVER_REGISTER`: 0
- `TFX_SERVER_REGISTER`: 0

The TFX status P&S `0x10207218 / 0x2` remains undefined:
`find_get` returns `KErrNotFound`.

The first post-native-route TfxServer request still fails at
`16:24:33.010`.

Therefore HLE AknSkin interception was a real missing startup path, but **not
the only blocker before TFX activation**.

### CenRep 0x1028583D is not yet the root cause

At `16:24:35.088`, native AknSkinSrv opens CenRep UID `0x1028583D`;
EKA2L1 reports it missing and AknSkinSrv performs `Leave(-1)`.

However:
- the leave is trapped by the guest trap handler;
- the native `!AknSkinServer` remains registered afterward;
- later clients continue binding to `server_hle=0`;
- AknSkinSrv still has live async requests during emulator teardown.

EKA2L1's own HLE skin implementation names this UID `ICON_CAPTION_UID` and
treats its absence as optional.

Therefore do **not** synthesize repository `0x1028583D` yet.

### Source-guided next TFX boundary

Primary Symbian source identifies the exact gate before the ECom TFX provider:

```text
KCRUidThemes             = 0x102818E8
KThemesTransitionEffects = 0x00000009
```

`CAknsSrvSettings::TransitionFxState()`:

```cpp
TInt value = KMaxTInt;
TInt err = iThemesRepository->Get(KThemesTransitionEffects, value);
if (err)
    return KMaxTInt;
return value;
```

Then `CAknsSrv::StartTransitionSrvL()` only calls
`LoadTfxSrvPluginL()` when:

```text
TransitionFxState() != KMaxTInt
```

The B46 firmware definitely contains
`Z:\private\10202BE9\102818E8.txt`, and B46 successfully opens repo
`0x102818E8`; the unknown part is now the **key 0x9 result/value**.

If key 0x9 returns an error or `KMaxTInt`, native AknSkinSrv intentionally
skips TFX ECom, exactly matching the observed absence of
`tfxsrvplugin.dll`.

If key 0x9 is enabled, the next boundary is before/during
`iWsSession.Connect()` or ECom implementation creation.

### B47 candidate

Preferred next milestone:

`NATIVEBOOT2-B47-AKNSKINTFXSTATE1`

Diagnostic-only goals:
1. trace native AknSkinSrv CenRep open/get for UID `0x102818E8`, key `0x9`;
2. capture Get result and integer value;
3. trace AknSkinSrv Wserv session attempt immediately before the TFX path;
4. trace native ECom CreateImplementation requests for
   `0x10282DBD` and `0x10282DBC`;
5. preserve all B46 routing and B44 TFX/ALF markers.

Do not change CenRep values, do not force TFX enabled, and do not synthesize an
ECom implementation until device evidence identifies the first missing stage.

### Preserved milestones

B42:
- SA_HWRM_ABI at `16:24:01.803`;
- SYSSTART HWRM kill failure at `16:24:31.801`;
- ~29.998 s delay remains.

B40:
- EUART1 PDD enter/complete result 0 at `16:24:33.303`;
- `!EikAppUiServer` registers at `16:24:33.677`.

B41:
- teardown reaches `shutdown_done` at `16:27:02.198`;
- `normal_restart_done has_device=1` at `16:27:02.297`.

No KERN-EXEC, EXC_BAD_ACCESS, or host access-violation family is present.

Full snapshot:
- `docs/handoff/history/B46-DEVICE1.md`


## Latest build override — B47 AKNSKINTFXSTATE1

B47 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.
B41 remains the immutable functional baseline.
B46 DEVICE1 remains the latest device-observed diagnostic milestone until B47
device logs arrive.

### Scope clarification

This work is interoperability/emulator startup debugging for Nokia 5800/Symbian
firmware inside EKA2L1 on iOS. It observes guest CenRep, Wserv, ECom and server
lifecycle behavior only. It does not attack external systems, bypass access
controls, deploy malware, or access third-party data.

### Purpose

B46 proved that the stock guest launches native `AknSkinSrv.exe`, native
`!AknSkinServer` registers, and clients bind with `server_hle=0`, but TFX
still does not start.

Symbian source identifies the next gate:

```text
KCRUidThemes             = 0x102818E8
KThemesTransitionEffects = 0x00000009
```

B47 is diagnostic-only and records whether native AknSkinSrv crosses this gate.

### New markers

- `[NBOOT2][AKNSKIN_TFX_STATE]`
  - native AknSkinSrv CenRep GetInt for repo `0x102818E8`, key `0x9`;
  - logs request, result, returned integer and whether the value equals
    `KMaxTInt`.
- `[NBOOT2][AKNSKIN_TFX_WSERV]`
  - native AknSkinSrv CreateSession to `!Windowserver`;
  - logs request and lookup result only.
- `[NBOOT2][AKNSKIN_TFX_ECOM]`
  - all native AknSkinSrv IPC sent to `!ecomserver`;
  - logs raw function, argument types/raw values and literal presence for
    `0x10282DBD` / `0x10282DBC`.

All markers are `behavior=OBSERVE_ONLY`.

### Semantic guard

B47 does not:
- modify CenRep values;
- force `KThemesTransitionEffects`;
- change Wserv result;
- change ECom IPC function/arguments/result;
- fake TfxServer;
- define TFX P&S;
- force Alfred;
- change global EPOC version;
- alter B42 HWRM behavior.

### TDD/build chronology

Canonical RED:
- contract commit: `4dff83fde398150a534e4f9bb4f641ac3a6635c0`
- pair wiring: `7eb4787e075a72215aa4ce55f217b761f9b8249d`
- run/job: `35847386001 / 107136721921`
- B29-B46 PASS;
- B47 fails only because `[NBOOT2][AKNSKIN_TFX_STATE]` is absent.

Implementation lineage:
- `08ff6f5c86ecdcd518663686cdf902aae27579d1` diagnostic implementation;
- `39e624f97944dd071a89c02c8fb9d52964f4a6d3` ECom probe anchor fix;
- `f53298c978c5808aa66c70a84c5d2aca788c0d34` UID annotation;
- `5cbfba2b7330bb34e7afadafde534df4351543e8` test boundary fix;
- `db1b7258b7808a2b3e04bddd22d9252d5eac6adc` assignment-vs-comparison test fix;
- `ab4415d0f94b002d01e6ea2035600a2dddc99c1d` compile support include.

Intermediate compile failure:
- run `35853924882`;
- single failure: `repo.cpp` used `kernel::process::name()` with only a
  forward declaration;
- fixed only by including `kernel/process.h`.

Canonical GREEN:
- build HEAD: `cc7d53ebb99f0ea754ffc432f9221586bef13fcc`
- run/job: `35854365057 / 107159241200`
- FASTBUILD1 manifest VALID
- B29-B47 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- B47 Mach-O invariants PASS
- IPA package/upload PASS
- compile requests: 149
- cache hits: 149
- cache misses: 0
- hit rate: 100%
- compilation failures: 0

Unsigned IPA SHA-256:

`ae3a0b0e467c19d30277274355c3eb537fdcd75becd55f2f2e463dbca1b27885`

IPA artifact:
- ID: `10746604288`
- GitHub ZIP size: 19,913,636 bytes
- ZIP digest:
  `sha256:cd5f8842f473c4244281de3430ff72ced4eec2f4490a27a912fa4e2598557adc`

Audit artifact:
- ID: `10746932579`
- digest:
  `sha256:7747fcb0e01ea2088f6181ff6420bffeab24eb37234724c67a340ccdcf6ac06e`

Downloaded artifact ZIP and extracted IPA were re-hashed locally and match CI.

### Device acceptance

Test the same RM-356 path as B46 and send:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

Primary classification:

```text
AKNSKIN_TFX_STATE request/result
        ↓
if result error or value == KMaxTInt
    native AknSkinSrv intentionally skips TFX provider
else
    expect AKNSKIN_TFX_WSERV
        ↓
    expect AKNSKIN_TFX_ECOM
        ↓
    inspect TFX_ECOM_RSC / TFX_ECOM_DLL / ALF / TfxServer
```

Do not select B48 until the first missing stage is device-proven.

Full snapshot:
- `docs/handoff/history/B47-AKNSKINTFXSTATE1.md`


## Conversation handoff — 2026-09-23 evening

The current chat is intentionally being closed because it has become very
long. Continue from this section in a new conversation.

### Current code/build state

Active branch:
`nativeboot2-current`

Current branch HEAD before this handoff:
`08cf7062a4ffdbdac7bb39f898e4d926632dbe08`

Latest implementation:
`ab4415d0f94b002d01e6ea2035600a2dddc99c1d`

B47 binary-invariant HEAD:
`cc7d53ebb99f0ea754ffc432f9221586bef13fcc`

B47 canonical GREEN:
- run `35854365057`
- job `107159241200`
- B29-B47 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- B47 Mach-O marker invariants PASS
- IPA package/upload PASS
- compile requests/hits/misses `149/149/0`
- compilation failures `0`

B47 unsigned IPA SHA-256:
`ae3a0b0e467c19d30277274355c3eb537fdcd75becd55f2f2e463dbca1b27885`

B47 IPA artifact:
- ID `10746604288`
- ZIP digest
  `sha256:cd5f8842f473c4244281de3430ff72ced4eec2f4490a27a912fa4e2598557adc`

B47 status:
**BUILD-VALIDATED; DEVICE TEST REQUIRED**

Full build snapshot:
`docs/handoff/history/B47-AKNSKINTFXSTATE1.md`

### What B47 must prove on device

B46 already proved the stock guest path:
- RM-356 native route skips HLE AknSkinServer;
- guest receives real KErrNotFound for `!AknSkinServer`;
- guest launches `AknSkinSrv.exe`;
- UID3 `0x10207114`;
- native `!AknSkinServer` registers;
- clients bind with `server_hle=0`.

B47 is diagnostic-only and adds:

```text
[NBOOT2][AKNSKIN_TFX_STATE]
[NBOOT2][AKNSKIN_TFX_WSERV]
[NBOOT2][AKNSKIN_TFX_ECOM]
```

Primary decision tree:

```text
native AknSkinSrv
 -> CenRep 0x102818E8 / key 0x00000009
    -> if error or KMaxTInt: TFX suppressed at Themes settings gate
    -> otherwise:
         -> AknSkinSrv -> !Windowserver
         -> AknSkinSrv -> !ecomserver
         -> inspect 0x10282DBD / 0x10282DBC
         -> inspect tfxsrvplugin / ALF / TfxServer
```

Do not implement B48 behavior until B47 device logs identify the first missing
stage.

Expected device logs:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

### Internet Archive / Exa firmware research

Archive item:
`https://archive.org/details/Nokia_BB5_firmwares`

The item contains eight large Nokia 5800 RM-356 ZIP archives, roughly 30 GB
total. Internet Archive currently restricts direct automated inspection of the
ZIP central directories, so exact mapping from firmware package name to
`part1..part8` has not yet been proven.

Exa confirmed old Nokia firmware catalogs listing these exact package names:

```text
RM-356_APAC_40.0.005_v12.0.exe
RM-356_APAC_50.0.005_v13.0.exe
RM-356_APAC_51.0.006_v14.0.exe
RM-356_APAC_52.0.007_v15.0.exe
RM-356_EMEA_40.0.005_v12.0.exe
RM-356_EMEA_50.0.005_...
```

Exa also found a FoneFun index with later APAC V50 package revisions including:
- `RM-356 APAC 50.0.005 v13.05.exe`
- `v13.06.exe`
- `v13.07.exe`
- `v13.08.exe`
- `v13.09.exe`

Therefore APAC V40/V50 definitely existed, but the exact Internet Archive part
containing the base `v12.0` / `v13.0` package has not yet been located.

### Firmware packages the user already downloaded

Visible in iOS Downloads screenshots:

```text
RM-356_APAC_52.0.007_v15.0      ~154.4 MB
RM-356_EMEA_50.0.005_v13.0      ~174.3 MB
RM-356_EMEA_40.0.005_v12.0      ~170.3 MB
RM-356_EMEA_31.0.101_v9.44      ~21 MB
RM-356_EMEA_31.0.101_v9.45      ~113.4 MB
RM-356_EMEA_31.0.101_v9.46      ~92.4 MB
```

For the current B47/B48 comparison, the most important already-downloaded
package is:
`RM-356_APAC_52.0.007_v15.0`.

The EMEA V40/V50 packages are still useful controls for common system binaries
and TFX/ALF/ECom components.

If APAC V40/V50 cannot be found easily, do **not** block the project on them.

### Files/components to extract from control firmware

Primary comparison set:

```text
private\10202BE9\102818E8.txt
sys\bin\AknSkinSrv.exe
sys\bin\AknSkinSrv.dll
tfxsrvplugin.dll
akntransitionutils.dll
aknlistloadertfx.dll
alfredserver*
ALF/UI Accelerator resources
ECom registration resources/SPI
```

For package-level mapping, VPL is useful:
`RM356_<productcode>_<version>_*.vpl`

Preferred Vietnam product codes when available:
- `0573800` Vietnam Black
- `0559962` Vietnam Blue
- `0559676` Vietnam Red
- `0591831` Vietnam Gun/Black

### Immediate next actions in the new conversation

1. If B47 device logs are available, analyze them first.
2. If firmware package files are uploaded first, extract and compare V52/V50/V40
   against the current V60 baseline.
3. Continue Exa/web research only as needed to locate APAC V40/V50 archive
   position; do not require them before progressing.
4. Keep all project state updates in GitHub `docs/handoff/CURRENT.md` and
   history snapshots.


## Firmware research override — 2026-09-23 late evening

A dedicated RM-356 research checkpoint was added after the B47 handoff:

`docs/handoff/history/RM356-FIRMWARE-RESEARCH-2026-09-23.md`

Commit:
`25c27e6f25a7122555eb92a0eaaf0850bb346ebd`

New externally corroborated facts:

- Internet Archive exposes the Nokia 5800 set as
  `5800 RM-356_part1.zip` through `part8.zip`; part1-part7 are about
  4.0-4.1 GB and part8 about 1.5 GB.
- Exact installer-to-part mapping is still unproven because automated
  archive-internal ZIP directory fetches return HTTP 403.
- APAC V40/V50/V51/V52 package families are independently confirmed by old
  Nokia firmware catalogs and support-server release logs.
- `RM-356_APAC_52.0.007_v15.0.exe` is independently confirmed and remains the
  preferred already-downloaded control firmware.
- Vietnam product codes are corroborated as:
  `0573800` Black, `0559962` Blue, `0559676` Red,
  `0591831` Gun/Black.
- Symbian firmware references identify
  `private\\10202BE9\\102818E8.txt` key `0x9` as the theme-effects
  control:
  `0x7FFFFFFF` = disabled, `0x8` = enabled by default; one reference
  describes `0` as automatic.

B47 interpretation is now sharper:

- if native AknSkinSrv reads repo `0x102818E8` key `0x9` as an error or
  `0x7FFFFFFF/KMaxTInt`, the missing TFX ECom/ALF/TfxServer chain is
  firmware-selected behavior and must not be synthesized;
- if the value is non-KMaxTInt, continue to the already-instrumented native
  WindowServer then ECom boundary.

B47 remains:
**BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Do not choose B48 behavior before B47 device evidence.


### RM-356 probe tooling

A reproducible extracted-firmware comparison tool is now available:

- `tools/rm356_firmware_probe.py`
- `test_rm356_firmware_probe.py`

Latest tool/test commits:
- `5f8d6ccecc6cbdba5d3c0dd04eb699120d8e099b`
- `58dcd1bbcb5ebff36837f06e0c2b803fb1d8df39`

Research snapshot with full rationale:
`docs/handoff/history/RM356-FIRMWARE-RESEARCH-2026-09-23.md`

Synthetic probe validation covers UTF-8 and BOM-less UTF-16 CenRep input plus
component SHA-256 comparison. Runtime B47 semantics remain unchanged.


## V60 firmware authority override — 2026-09-23

The exact device-test RM-356 V60 pair is now verified.

RPKG:
- raw size `134,540,934` bytes
- SHA-256 `bc41496abc8d4c87de976b65cadfb922b4dfd9583a0dbcf35b7e4bff23eb008f`
- version resources identify `RM-356 60.0.003`, Nokia 5800 XpressMusic,
  Symbian OS 9.4
- `Z:\\private\\10202BE9\\102818E8.txt` key `0x9` is exactly
  `0x7fffffff`
- ECom SPI contains both `0x10282DBC` and `0x10282DBD`

Corrected device-test ROM:
- size `41,283,584` bytes
- SHA-256
  `b4328dfa555d73e14a4bab2de46bbec702970e4b63c8ce878da589fa6b64c444`
- valid EKA2 ROM burn tree with 2,161 files
- contains AknSkinSrv plus core TFX binaries
- eight checked AknSkin/TFX binaries are byte-identical between ROM and RPKG

Interpretation:
the V60 firmware contains the TFX code and registrations while the stock
Themes repository selects `KMaxTInt` at key `0x9`. If B47 device logs show
the same read result/value, skipping provider startup is stock behavior.
Do not fake TFX/ECom/ALF. B47 device evidence remains the final runtime check
before selecting any B48 behavior.

Full evidence:
`docs/handoff/history/RM356-FIRMWARE-RESEARCH-2026-09-23.md`.


## Latest device override — B47 DEVICE1

B47 is now **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Device logs:
- `EKA2L1(8).log`
- `EKA2L1_Persistent(8).log`
- `EKA2L1_TakeThis(8).log`

Full snapshot:
`docs/handoff/history/B47-DEVICE1.md`

### Decisive result

Native `AknSkinSrv[10207114]` reads:

```
repo=0x102818E8
key=0x00000009
result=0
value_valid=1
value=0x7FFFFFFF
enabled=0
suppressed=1
```

This exactly matches the extracted stock RM-356 V60 firmware value.

Native AknSkinSrv can reach `!Windowserver`:

```
AKNSKIN_TFX_WSERV phase=lookup found=1 server_hle=1
```

B47 also observes 22 AknSkinSrv IPC sends to `!ecomserver`, but all have:

```
literal_controller=0
literal_server=0
```

No target TFX interface request is observed for `0x10282DBD` or
`0x10282DBC`.

No runtime `TFX_ECOM_RSC`, `TFX_ECOM_DLL`, `ALF_SESSION`,
`ALF_SERVER_REGISTER` or `TFX_SERVER_REGISTER` marker appears.

The stock V60 firmware contains the TFX binaries and both ECom registrations,
so the runtime absence is now explained by the stock Themes gate rather than
missing firmware content or an EKA2L1 routing failure.

### Consequence

Do not:
- force key `0x9`;
- fake `TfxServer`;
- synthesize ECom implementation success;
- force ALF/Alfred;
- choose a B48 TFX-enablement workaround.

The AknSkin/TFX hypothesis is closed as stock behavior.

### Preserved milestones

- B46 native AknSkin route remains healthy and clients bind
  `!AknSkinServer` with `server_hle=0`.
- B40 `EUART1` completes with result 0 and `!EikAppUiServer` registers.
- no `KERN-EXEC 3`, `EIKFAULT_AV`, access violation or
  `EXC_BAD_ACCESS` family appears in the current TakeThis log.
- B41 Exit Emulator remains healthy:
  `os_join_begin -> os_join_done` in about 46 ms, then
  `shutdown_done -> normal_restart_done has_device=1`.

### Next-boundary note

The log proceeds into native Home screen theme infrastructure.

`xnthemeserver` is launched by Home screen and successfully registers, but
there are repeated trapped `Leave(-5)` events correlated with FileServer
opcode `0x27` while theme cache files under
`C:\Private\10207254\themes\sources\` are accessed.

This is a candidate for the next diagnostic only, not yet a proven root cause:
the server remains alive through teardown. Do not patch FileServer semantics
until the visual state and the first blocking call are correlated.

B48 remains **NOT SELECTED** pending that next-boundary classification.


## Latest build override — B48 XNTHEMEPOST1

B48 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

B47 remains closed as stock behavior:
native AknSkinSrv reads `0x102818E8:0x9 = 0x7FFFFFFF/KMaxTInt`, matching the
real RM-356 V60 firmware and intentionally suppressing TFX startup.

### Why B48

The first post-B47 candidate is native Home screen theme traffic through
`xnthemeserver[10207254]`.

B47 logs show:
- xnthemeserver launches and registers;
- it remains alive through teardown;
- repeated trapped `Leave(-5)` events occur near historical FileServer
  `0x27` observations.

Current FileServer ABI authority identifies hex `0x27` as decimal 39:
`fs_msg_file_flush`.

The old correlation does not prove FileFlush returns -5, so B48 only observes
the exact request/completion boundary.

### New B48 markers

- `[NBOOT2][XNTHEME_IPC]`
  - `phase=send`: caller/process/UID3/thread, xnthemeserver function/opcode,
    sync mode and raw arguments;
  - `phase=complete`: native xnthemeserver exact completion result to any
    client, including Home screen.
- `[NBOOT2][XNTHEME_FSFLUSH]`
  - xnthemeserver FileFlush handle/path;
  - actual `vfs_file->flush()` result;
  - exact unchanged FileServer completion.

### Semantic guard

B48 does not change:
- xnthemeserver IPC behavior;
- completion values;
- FileFlush behavior;
- MENUUI13 FS-DIRUID1;
- B47 CenRep/TFX state;
- TfxServer/ECom/ALF;
- WindowServer.

### Canonical GREEN

Implementation lineage:
- initial B48: `c47a3ca4a81836a0d2c500ff618d176756943c41`
- baseline-marker location fix:
  `650fe61bf88292dff23b0781bfd7a3a5dabac194`
- corrected test:
  `174e00388a0aef1a02e07bb44b55b5f0488ca75e`

Canonical run/job:
- run `35879560705`
- job `107244189576`
- build HEAD `174e00388a0aef1a02e07bb44b55b5f0488ca75e`

Result:
- FASTBUILD1 manifest VALID
- B29-B48 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- B48 binary invariants PASS
- IPA package/upload PASS
- compile requests/hits/misses `149/147/2`
- actual compilations `2`
- compilation failures `0`
- NOJAVA/MANIC3 preserved

Unsigned IPA SHA-256:

`4b5c59119ceb5940cdefca8c52a3bd7545861511896659b3302c38e44b504a32`

IPA artifact:
- ID `10759779669`
- ZIP digest
  `sha256:f98d14ddb4f8f9b6b350d91d70ef9194717acc0382e6955d75897c196ec34c24`

Audit artifact:
- ID `10759379488`
- digest
  `sha256:03bc38b5504014e0a70215b3ea998718670152e6144784a429ac44da8f3169a7`

Full snapshot:
`docs/handoff/history/B48-XNTHEMEPOST1.md`

### Device acceptance

Use the exact same V60 RM-356 pair as B47 and send:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

Primary classification:

```
XNTHEME_IPC send
 -> XNTHEME_FSFLUSH enter/result (if opcode 0x27 occurs)
 -> XNTHEME_IPC complete exact result
```

If FileFlush reports `flush_ok=1 completion=0`, close the old FS27 hypothesis
and move beyond theme storage. If FileFlush or xnthemeserver completion is
nonzero, correlate the exact request/result with the subsequent guest Leave
before selecting any functional fix.


## Latest device override — B48 XNTHEMEPOST1 DEVICE1

B48 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:
`docs/handoff/history/B48-DEVICE1.md`

### Decisive result

B47 stock RM-356 V60 TFX suppression remains preserved:

```
repo=0x102818E8
key=0x00000009
result=0
value=0x7FFFFFFF
enabled=0
suppressed=1
```

Native `xnthemeserver[10207254]` launches, registers, and remains alive through
normal emulator teardown.

B48 captured **40** xnthemeserver FileServer `FileFlush` operations. Every
one completed:

```
flush_ok=1
completion=0
behavior=OBSERVE_ONLY
```

This includes the previously suspicious cache files:

```
C:\Private\10207254\themes\sources\hdrcache.dat
C:\Private\10207254\themes\sources\cleanupfiles.dat
```

Therefore FileServer opcode hex `0x27` / decimal 39
(`fs_msg_file_flush`) is not the source of the recurring
`Leave(-5)`.

There are 37 trapped `Leave(-5)` events in xnthemeserver, but they occur
guest-side after successful FileFlush completions and are trapped while the
server continues processing. Do not synthesize `-5` from FileFlush and do
not suppress these guest leaves.

Observed Home screen -> xnthemeserver completions are non-negative:

- function `-1` -> result `0`
- function `9` -> result `18`
- function `3` -> result `4`
- function `4` -> result `6`
- function `13` -> result `22`

Home screen progresses to:

```
SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_EVENTREADY_ARM
```

No `KERN-EXEC`, `EIKFAULT_AV`, `EXC_BAD_ACCESS` or host access
violation is present.

Exit Emulator remains healthy:

```
22:42:09.732 os_join_begin
22:42:09.776 os_join_done
```

about 44 ms, followed by `normal_restart_done has_device=1`.

### Next-boundary candidate

After Home screen reaches event-loop setup, the only negative WindowServer
batch result currently observed is `op=0x2B result=-1` three times.

The pinned WindowServer opcode table maps decimal 43 / hex `0x2B` to
`ws_cl_op_find_window_group_identifier`.

This is only a candidate boundary. A window-group lookup miss can be normal,
so do not patch it without correlating the actual B48 visual device state.

Four later `RM356_FS_UNKNOWN opcode=80` observations map to
`fs_msg_notify_disk_space`; they are also not proven blockers.

### Consequence

The old theme-cache / FileFlush hypothesis is closed.

Do not:
- alter FileFlush results;
- change MENUUI13 FS-DIRUID1;
- reopen or force TFX;
- fake xnthemeserver completions;
- patch WindowServer `0x2B` from the lookup miss alone.

B49 functional behavior is **NOT SELECTED** until the visible B48 screen state
is correlated. Request one screenshot or short screen recording from the B48
test before selecting the next diagnostic boundary.


## B48 visual authority / device-test protocol

B48 screen recording confirms the emulator does not remain black.

Visual sequence:
- black display for about 35 seconds;
- Nokia white startup screen appears at about 36 seconds;
- blue `NOKIA` logo remains static until the user exits after roughly
  3 minutes 45 seconds.

This overlaps the log interval in which xnthemeserver succeeds and Home screen
reaches `INPUT_EVENTREADY_ARM`.

Interpretation:
the renderer can present the Nokia boot surface, but the presentation/focus
chain never replaces that surface with the native Home screen.

B49 is therefore selected as a **diagnostic-only post-logo WindowServer
group/focus/activation trace**.

For every future device-tested build, request:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- a screen recording of the full test

The user has confirmed they can record every build. Use video/log timestamp
correlation before selecting a functional fix.


## Latest build override — B49 POSTLOGOWSERV1

B49 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

B48 video authority:
- black display until about 35.2 seconds;
- Nokia boot surface then appears;
- blue Nokia logo remains static through the rest of the ~228 second test;
- Exit Emulator remains normal.

B48 logs already prove theme FileFlush is healthy. Therefore B49 moves to the
post-logo WindowServer group/focus boundary.

### B49 markers

- `[NBOOT2][POSTLOGO_WG_FIND]`
- `[NBOOT2][POSTLOGO_WG_CREATE]`
- `[NBOOT2][POSTLOGO_WG_ORDINAL]`
- `[NBOOT2][POSTLOGO_FOCUS]`

The trace records which process creates/searches WindowGroups, wildcard lookup
patterns/results, ordinal movement, and old/new/final focus selection.

No WindowServer result, z-order request, focus policy, FileServer behavior,
TFX state, or theme result is changed.

### Canonical GREEN

- run `35886788765`
- job `107268855673`
- build HEAD `58cb44733ad6b8cd5bd0543687532a70852cf326`
- FASTBUILD1 manifest VALID
- B29-B49 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`

Unsigned IPA SHA-256:

`ab22067d9be0f28a802cfc2ff0356790e43c04ca8fb34847bdccaef7271dd17b`

IPA artifact:
- ID `10763560496`
- ZIP digest
  `sha256:df69213c6a9310b323124c46d9b0572a871c9c96c37c9e9381b5361318241f9c`

Full snapshot:
`docs/handoff/history/B49-POSTLOGOWSERV1.md`

### Device acceptance

Use the same RM-356 V60 pair and provide:
- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

The device decision is whether Home screen creates/owns a WindowGroup that
ever reaches final focus ahead of the Nokia startup group. Do not force focus
or patch op `0x2B` until B49 device evidence identifies the exact caller,
pattern, target group and focus transition.


## Latest device override — B49 POSTLOGOWSERV1 DEVICE1

B49 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:
`docs/handoff/history/B49-DEVICE1.md`

B49 video/log correlation proves:

```
splashscreen[100059de]
 -> creates WindowGroup object 0x00030003
 -> focus group id=3
 -> group becomes S60SplashScreenGroup
 -> Nokia logo appears at the same timestamp
```

Startup then creates a focus-requesting group with client handle
`0x008000C0`, and Home screen/ailaunch creates another focus-requesting
group with client handle `0x007007E8`.

Home screen is successfully discoverable by UID, so its WindowGroup is not
missing.

At 23:22:07.655:

```
WSERV_BATCH_CMD op=0x6 obj_handle=0x00030003
```

The object is the splash WindowGroup. Window opcode `0x06` is
`EWsWinOpSetOrdinalPositionPri`.

Focus changes immediately:

```
S60SplashScreenGroup (id=3)
 -> Startup (id=61)
```

Splashscreen exits normally 12 ms later.

The full B49 recording remains visually pixel-identical to the Nokia startup
surface after this focus handoff and splash exit. Therefore successful focus
handoff alone does not replace the displayed splash pixels.

Startup remains focus throughout normal runtime. Home screen only becomes
focus during emulator teardown, after Exit Emulator has already been
requested.

Do not force Home screen focus yet.

## Latest build override — B50 POSTLOGOCANVAS1

B50 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

B50 classifies whether the post-logo failure is before or after normal
WindowServer canvas presentation.

New markers:

- `[NBOOT2][POSTLOGO_ORDERPRI]`
- `[NBOOT2][POSTLOGO_RECEIVEFOCUS]`
- `[NBOOT2][POSTLOGO_CANVAS_CREATE]`
- `[NBOOT2][POSTLOGO_CANVAS_ACTIVATE]`
- `[NBOOT2][POSTLOGO_CANVAS_VISIBLE]`
- `[NBOOT2][POSTLOGO_WG_DESTROY]`

The trace is limited to:

- splashscreen `0x100059DE`
- Startup `0x100058F4`
- Home screen `0x102750F0`

B50 does not force focus, visibility, activation, z-order, redraw or framebuffer
clearing. B49 behavior remains unchanged.

### Canonical GREEN

- run `35891253078` / run number 143
- job `107283982581`
- build HEAD `0445b52ba14d0c1b45ad79ed9d627c697d745be7`
- FASTBUILD1 manifest VALID
- B29-B50 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses `149/145/4`
- actual compilations `4`
- compilation failures `0`
- NOJAVA / MANIC3 preserved

FASTBUILD audit:
- B28 cache bootstrap
- bootstrap 37 s
- patch/regression 3 s
- build 82 s
- package 2 s
- total 151 s

Unsigned IPA:

- size `19,988,067` bytes
- SHA-256
  `0d46c081142116b472bedf41dc0620e8eff3601714947bb03ff013e93e1cda4c`

GitHub IPA artifact:
- ID `10765615710`
- digest
  `sha256:fbe1ba7e2272104058df0675142f65218559075e9c054005e1e14dbb6248052c`

Full build snapshot:
`docs/handoff/history/B50-POSTLOGOCANVAS1.md`

### B50 device acceptance

Use the same RM-356 V60 pair and provide:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

Decision:

```
splash/Startup/Home group state
 -> canvas create
 -> SetVisible
 -> Activate
 -> physically_seen
 -> splash destruction
 -> displayed frame
```

If Startup/Home canvases become active + visible + physically seen while the
video still retains stale Nokia pixels after splash destruction, the next
boundary moves into WindowServer redraw/compositor/framebuffer invalidation.
Do not clear the framebuffer or force Home focus before that evidence.


## Latest device override — B50 POSTLOGOCANVAS1 DEVICE1

B50 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:

`docs/handoff/history/B50-DEVICE1.md`

B50 proves the post-logo failure is later than simple WindowServer
group/canvas creation and activation:

- Startup group 63 exists and has visible/active canvases;
- Home screen group 75 exists and has many canvases, including visible/active
  canvases;
- splash priority drops from 1001 to -1000;
- focus changes from splash group 3 to Startup group 63;
- the splash WindowGroup is destroyed;
- visible-region recomputation is pending;
- the full device recording nevertheless remains on the same Nokia startup
  pixels.

Therefore do not force Home focus and do not reopen FileFlush/TFX hypotheses.
The next boundary is WindowServer redraw/composition -> iOS host presentation.

## Latest build override — B51 DIRECTSCREEN1

B51 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B51-DIRECTSCREEN1.md`

Corrected B51 build HEAD:

`f5a5e5b2a37a0cd94a31cb0ad73cc134a19bdfc7`

Canonical FASTBUILD:

- run ID `35902306523`
- run number `150`
- B29-B51 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- `DIRECTSCREEN_PRESENT` retained in Mach-O
- `DIRECTSCREEN_REDRAW` retained in Mach-O
- IPA package/upload PASS
- NOJAVA / MANIC3 preserved

Unsigned IPA:

- size `19,989,478` bytes
- SHA-256
  `c9113a51d3a8d7ad90e3d2270dcd0c350fa82ec812bf629045b81dfac2b6f4f9`

Library path:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B51-DIRECTSCREEN1-unsigned.ipa`

B51 traces:

- `[NBOOT2][DIRECTSCREEN_REDRAW]` around the real
  `screen::redraw(driver)` path for splash/Startup/Home focus groups;
- `[NBOOT2][DIRECTSCREEN_PRESENT]` in the actual B28/current iOS
  `state.cpp` redraw callback.

The host-present probe draws a tiny moving four-phase colored square directly
on host bitmap 0 after `launcher_->draw(screen_texture)` and before the
existing present. It does not modify guest screen texture, focus, z-order,
activation, visibility, or redraw scheduling.

Device-test rule:

- use the same RM-356 V60 runtime pair;
- record the full test;
- send `EKA2L1.log`, `EKA2L1_Persistent.log`,
  `EKA2L1_TakeThis.log`, and the full screen recording;
- let the test continue past Nokia splash demotion/destruction before using
  Exit Emulator.

Decision:

- moving marker + stale Nokia => host present is alive; investigate guest
  `screen_texture`/composition;
- marker/present stops => redraw-to-present scheduling is the missing stage;
- redraw continues with `performed=0` => compositor emits no drawable guest
  content;
- redraw `performed=1` + moving marker + stale Nokia => inspect actual
  `screen_texture` writes/tree traversal next.


## Latest device override — B51 DIRECTSCREEN1 DEVICE1

B51 is **DEVICE-OBSERVED; VISUAL DIAGNOSTIC SUCCESS**, with one important
qualification: the test ended before the natural ~120 s splash handoff seen in
B49/B50.

Full snapshot:

`docs/handoff/history/B51-DEVICE1.md`

Observed:

- 170 `DIRECTSCREEN_REDRAW phase=enter`;
- 170 `DIRECTSCREEN_REDRAW phase=result`;
- all 170 redraw results have `performed=1`;
- 170 `DIRECTSCREEN_PRESENT` events;
- the host-only marker moves one-for-one with those present events;
- last redraw/present is at 05:05:10.422;
- after that the visual marker freezes exactly as designed.

The user reported the 15x15 host marker was too small and difficult to see.
In the 510x1108 recording it is only about 7x7 pixels.

The B51 run exits at 05:06:24.425, only about 80 s after the first splash
redraw/present. The splash destruction immediately after that is teardown
caused by Exit Emulator, not the natural boot handoff.

Therefore B51 proves the initial WindowServer compositor and iOS host present
path are alive, but does not yet prove what happens when the natural splash
demotion occurs.

## Latest build override — B52 REDRAWSCHED1

B52 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B52-REDRAWSCHED1.md`

B52 preserves B51 and adds:

- `[NBOOT2][REDRAW_SCHED]` tracing across
  `schedule -> schedule_scans -> idle_callback -> scan_for_redraw ->
  invoke_due_animation -> screen::redraw`;
- enlarged host marker: `72x72` pixels instead of `15x15`;
- marker moved to y=128 for visibility.

B52 is diagnostic-only. It does not force redraw, present, focus, z-order,
visibility, activation, guest screen-texture writes, or framebuffer clearing.

### Canonical GREEN

- run ID `35928441761`
- run number `152`
- job `107409037256`
- HEAD `2461ee8a5747a07f1aacbc58790a7021de134b4e`
- B29-B52 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- `REDRAW_SCHED` retained in Mach-O
- IPA package/upload PASS
- NOJAVA / MANIC3 preserved
- compile requests/hits/misses `149/147/2`
- actual compilations `2`
- compilation failures `0`

Unsigned IPA:

- size `19,991,158` bytes
- SHA-256
  `f391d2114b4142bb7282d224d2d8d07a30a239045d46e9984234b316955ed40a`

Library path:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B52-REDRAWSCHED1-unsigned.ipa`

### B52 device-test rule

Use the same RM-356 V60 pair.

After the Nokia logo first appears, leave the emulator running for at least
**150 seconds** before pressing Exit Emulator. B49/B50 show the natural splash
handoff around ~120 s, so the B51 ~80 s run was too short.

Send:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`
- full screen recording

Decision boundary:

```
natural splash demotion
 -> redraw schedule request
 -> scan callback
 -> due animation invoke
 -> screen::redraw
 -> iOS redraw callback
 -> host present
```

Do not implement a scheduler workaround before B52 device evidence identifies
the first missing phase.


## Latest device override — B52 REDRAWSCHED1 DEVICE1

B52 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:

`docs/handoff/history/B52-DEVICE1.md`

The natural splash handoff is now proven to reach host presentation.

At 06:09:02.083:

```
splash requested_priority 1001 -> -1000
REDRAW_SCHED schedule_enter
REDRAW_SCHED scan_arm
REDRAW_SCHED schedule_done
focus: S60SplashScreenGroup id=3 -> Startup id=61
```

Splash is destroyed normally at 06:09:02.095 with
`redraw_region_pending=1`.

The iOS host then presents four additional frames:

```
06:09:02.085 frame=171
06:09:02.093 frame=172
06:09:02.104 frame=173
06:09:02.117 frame=174
```

The enlarged marker advances across those presents, but the central Nokia
pixels remain effectively pixel-identical before/after the transition and for
the rest of the run.

Therefore scheduler delivery / host present is no longer the unresolved
boundary.

B52 also revealed an instrumentation limitation: Startup WindowGroup IDs vary
between runs. B52 inherited id=63 but the B52 device run uses Startup id=61.
Missing post-focus REDRAW_SCHED/DIRECTSCREEN_REDRAW markers therefore cannot be
interpreted as missing execution. The host presents prove that redraw callbacks
occur.

Source observation:

`screen::redraw(builder, true)` clears the color buffer only if
`FLAG_SERVER_REDRAW_PENDING` is set.

The B52 handoff presents report `screen_flags=0x00000002`, i.e. the
server-redraw-pending bit 0x8 is not set. This is a candidate explanation for
stale Nokia pixels, not yet a functional conclusion.

## Latest build override — B53 COMPOSITORTREE1

B53 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B53-COMPOSITORTREE1.md`

B53 uses WindowGroup name/UID matching instead of unstable run-specific object
IDs and adds:

- `[NBOOT2][COMPOSITOR_FRAME]`
- `[NBOOT2][COMPOSITOR_GROUP]`
- `[NBOOT2][COMPOSITOR_CANVAS]`

It records:

- conditional color-clear state;
- top-level group ordering;
- canvas visibility / physical visibility;
- absolute rectangles;
- per-canvas exact `draw()` result;
- total client / visible / physically-visible / drawn canvas counts.

B53 does not change the B28 compositor's conditional color clear or traversal.

### Canonical GREEN

- run ID `35933740025`
- run number `155`
- job `107425985727`
- HEAD `332040435ef6318902e23732cf1c6ec4369a72f6`
- B29-B53 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- NOJAVA / MANIC3 preserved
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`

Unsigned IPA:

- size `19,996,831` bytes
- SHA-256
  `d4c126540b7a12bef9569fd60f0f8db1ce74f4d12a6d23a83e90d626ace707a5`

Library path:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B53-COMPOSITORTREE1-unsigned.ipa`

### B53 device-test rule

Use the same RM-356 V60 pair and keep the emulator running at least
**150 seconds after the Nokia logo appears**.

Send the same 3 logs + full recording.

Primary question:

```
natural Splash -> Startup handoff
 -> compositor frame
 -> color_clear ?
 -> group order
 -> physical visibility
 -> per-canvas draw result
 -> host present
```

Do not add a forced clear until B53 proves whether Startup/Home frames fail to
cover the stale splash pixels.


## Latest device override — B53 COMPOSITORTREE1 DEVICE1

B53 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:

`docs/handoff/history/B53-DEVICE1.md`

The natural Splash -> Startup transition is fully captured.

At 07:36:42.166 focus changes to Startup group 63
(name contains `100058f4 Startup`).

B53 captures four immediate Startup compositor frames 173-176. Every frame has:

- `server_redraw_pending=0`
- `client_redraw_pending=0`
- `color_clear=0`
- visible-region recalculation performed
- one physically-visible canvas
- one `draw_result=1`

The only physically-visible/drawn canvas is Startup
`0x100058F4`, handle `0x00807AA8`, full-screen
`[0,0,360,640]`.

Home screen exists behind Startup but is not physically visible in those
frames.

The splash WindowGroup is absent from the traced post-focus group chain.

The iOS host presents the Startup frames, but the video remains pixel-identical
to the Nokia splash.

An exact B28-source inspection then establishes that
`redraw_msg_canvas::draw()` returns true for a physically-visible, non-zero
window even when both SERVER and CLIENT redraw-pending flags are zero. In that
state `draw_result=1` can occur without any pixel-writing command.

Therefore B53 narrows the stale-pixel mechanism to retained color in
`screen_texture`.

## Latest build override — B54 TRANSITIONCLEAR1

B54 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B54-TRANSITIONCLEAR1.md`

B54 is a controlled experiment, not a permanent fix.

At the first primary-screen edge into Startup `0x100058F4`, only when normal
`FLAG_SERVER_REDRAW_PENDING` is absent, B54 adds the color-buffer bit to the
existing compositor clear call.

Marker:

`[NBOOT2][TRANSITION_CLEAR]`

No extra clear command is added. B54 does not force redraw, present, focus,
z-order, visibility, activation, or scheduler timing.

### Canonical GREEN

- run ID `35940100239`
- run number `156`
- job `107445895276`
- HEAD `4f8629aa182b1de8d1c952733bfa49a6e1fc1040`
- B29-B54 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- NOJAVA / MANIC3 preserved
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`

Unsigned IPA:

- size `19,996,203` bytes
- SHA-256
  `e22acd144bac8fc9f455df176fc650d708aa38ce27ba4fde8caaf4aa4c5f27b7`

Library path:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B54-TRANSITIONCLEAR1-unsigned.ipa`

### B54 device-test rule

Use the same RM-356 pair and run at least **150 seconds after Nokia first
appears**.

Send 3 logs + full video.

Classification:

- Nokia disappears to black/blank:
  stale screen_texture retention confirmed; Startup provides no useful pixels.
- real UI appears:
  retained splash was the blocking presentation artifact.
- Nokia remains even with TRANSITION_CLEAR and host present:
  reject the screen_texture color-retention hypothesis and inspect another
  surface/render path.


## Latest device override — B54 TRANSITIONCLEAR1 DEVICE1

B54 is **DEVICE-OBSERVED; CONTROLLED EXPERIMENT SUCCESS**.

Full snapshot:

`docs/handoff/history/B54-DEVICE1.md`

B54 proves the retained Nokia image is stale guest color-buffer content.

At the natural Splash -> Startup transition:

```
08:35:49.576 TRANSITION_CLEAR frame=173
focus=Startup 0x100058F4
server_redraw_pending=0
action=ADD_COLOR_BIT_TO_EXISTING_CLEAR
```

The same frame reports:

```
color_clear=1
server_redraw_pending=0
client_redraw_pending=0
```

The B54 video changes from the white Nokia splash to black at approximately the
same instant. Full-frame mean brightness drops from ~205.9 at t=154.3 s to
~2.5 at t=154.4 s and remains black afterward.

Therefore the old Nokia pixels were retained in the guest screen texture and
the one-shot clear removes them successfully.

Startup remains focus and its full-screen 360x640 canvas remains physically
visible with `draw_result=1`, but no Startup pixels replace black.

Active B28 `redraw_msg_canvas::draw()` only emits stored redraw content when
`FLAG_SERVER_REDRAW_PENDING` is set, or queued client content when
`FLAG_CLIENT_REDRAW_PENDING` is set. At the B54 transition both are zero, so
`draw_result=1` does not guarantee any pixel-writing command.

## Latest selected milestone — B55 STARTUPREPLAY1

B55 is a controlled functional experiment selected directly from B54.

At the exact same proven one-shot Startup-focus edge, B55 sets:

`FLAG_SERVER_REDRAW_PENDING`

for that compositor pass.

This uses the existing B28 WindowServer path to replay stored redraw segments
for the physically visible Startup canvas. B55 does not force a new redraw,
present, focus, z-order, visibility or activation.

New markers:

- `[NBOOT2][STARTUP_REPLAY]`
- `[NBOOT2][STARTUP_REPLAY_CANVAS]`

The canvas marker records stored segment count and drawable segment count.

Implementation commit:

`14fd6f27fee6940173fa07401389709c7ded524a`

FASTBUILD run:

`35946065875`

Status at handoff update: build in progress; apply/regression stage PASS and iOS
target compilation underway.


## Latest build override — B55 STARTUPREPLAY1

B55 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

B54 DEVICE1 proved that the one-shot Startup transition clear removes the stale
Nokia pixels: the display changes to black at the natural Splash -> Startup
handoff. Therefore retained splash color in guest `screen_texture` is
confirmed.

B55 targets the next missing stage: replaying Startup's stored redraw content.
At the same one-shot Startup-focus edge, B55 sets
`FLAG_SERVER_REDRAW_PENDING` for that compositor pass so the existing B28
`redraw_msg_canvas::draw()` path can replay stored redraw segments.

Markers:
- `[NBOOT2][STARTUP_REPLAY]`
- `[NBOOT2][STARTUP_REPLAY_CANVAS]`

No extra redraw, present, focus, z-order, visibility, activation, or timer is
introduced.

### Canonical GREEN

- run ID `35946065875`
- run number `157`
- job `107464155547`
- HEAD `14fd6f27fee6940173fa07401389709c7ded524a`
- B29-B55 apply/tests PASS
- B20-B28 regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- NOJAVA / MANIC3 preserved
- compile requests/hits/misses `149/147/2`
- actual compilations `2`
- compilation failures `0`

Unsigned IPA:
- size `20,000,520` bytes
- SHA-256
  `8dbeb5361570be9dd28fad1d9f8269411f79484514e4d91c17c492d6abcac578`

Library path:

`/Eka2l1 Boot menu/EKA2L1-NATIVEBOOT2-B55-STARTUPREPLAY1-unsigned.ipa`

### Next-chat device test

Use the same RM-356 V60 pair. Keep the emulator running through the natural
~120 s Splash -> Startup transition.

Primary acceptance:
- if Startup pixels/UI appear after the transition: replay path is confirmed;
- if the screen remains black: inspect STARTUP_REPLAY_CANVAS segment counts and
  actual drawable stored content, then move to the next narrow replay/content
  boundary.

Send 3 logs + full video.


## Latest device override — B55 STARTUPREPLAY1 DEVICE1

B55 is **DEVICE-OBSERVED; CONTROLLED EXPERIMENT SUCCESS**.

Full snapshot:

`docs/handoff/history/B55-DEVICE1.md`

At the natural Splash -> Startup transition, B55 sets
`FLAG_SERVER_REDRAW_PENDING` exactly once. The Startup 0x100058F4 full-screen
canvas owns one stored non-pending segment. The B55 video advances from the
Nokia-logo splash to a stable blank white guest surface at the same transition,
where B54 previously became black.

This proves the Startup replay changes real guest output. However B55's
`drawable_segments=1` field counts segment state, not actual pixel-writing
commands, so the exact stored GDI content remains unresolved.

## Latest build override — B56 STARTUPGDICMD1

B56 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B56-STARTUPGDICMD1.md`

B56 is diagnostic-only and adds:

- `[NBOOT2][STARTUP_GDI_SEGMENT]`
- `[NBOOT2][STARTUP_GDI_CMD]`
- `[NBOOT2][STARTUP_GDI_DETAIL]`

It enumerates the exact stored GDI command stream replayed by the visible
Startup canvas and records bounded geometry/color/bitmap/text/texture details.
B55 behavior is unchanged.

Canonical GREEN:

- run `35955643932` / run number 162
- job `107493277047`
- HEAD `1c0d14f9ab5a890f409a407d9075ea08ec14ac89`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `8f935d4a06ccb019ac97f0df3607c3ab90993ab352d0c8bcbf25944d16ef414a`
- IPA artifact `10790611306`
- audit artifact `10790198741`

Device test: use the same RM-356 V60 path through the natural Splash -> Startup
handoff and send the 3 logs plus recording. The next change must be selected
from the exact Startup stored opcodes; do not force Home focus/redraw/timers.


## Latest device override — B56 STARTUPGDICMD1 DEVICE1

B56 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:

`docs/handoff/history/B56-DEVICE1.md`

The visible Startup 0x100058F4 canvas replays one REDRAW segment containing five
commands in exact order:

- CLIP_SINGLE [0,0,360,640]
- DRAW_BITMAP BLIT, source [0,0,360,640], destination auto-sized full-screen
- CLIP_SINGLE [0,0,360,640]
- DRAW_RECT [0,0,360,640] RGBA 255,255,255,255
- DRAW_RECT [0,0,360,640] RGBA 255,255,255,255

Therefore the B55/B56 white screen is real stored Startup content: two opaque
white full-screen rectangles are replayed after the bitmap.

The target canvas is created at 11:40:05.217 and becomes visible through the
natural replay at 11:42:01.492, about 116.3 s later. The firmware opens
`z:\\resource\\apps\\startup.mbm` near canvas creation, but B56 does not yet
prove that file owns the BLIT.

## Latest build override — B57 STARTUPGDIORIGIN1

B57 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B57-STARTUPGDIORIGIN1.md`

B57 adds diagnostic-only marker:

`[NBOOT2][STARTUP_GDI_ORIGIN]`

It traces the record-time guest GC source of the B56 command stream, including
GDI_BLT, CLEAR, CLEAR_RECT, DRAW_RECT and brush state, with process/thread,
guest GC opcode, canvas/group identity and bounded geometry/state.

Canonical GREEN:

- run `35957525692` / run number 163
- job `107498900591`
- HEAD `de2d65ce0333f7b5335e0b1f6ca7f6aaa4730ee0`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `803c02aa2db4bb49454329452d57e1da37a519e979f6954a71d6edc4b9e7b6fd`
- IPA artifact `10791615213`
- audit artifact `10790719138`

Next device question: identify exactly which guest operations record the
full-screen bitmap and the two opaque white rectangles, and whether any later
Startup draw attempts target the same canvas before the natural handoff.


## Latest device override — B57 STARTUPGDIORIGIN1 DEVICE1

B57 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS**.

Full snapshot:

`docs/handoff/history/B57-DEVICE1.md`

The Startup 0x100058F4 process itself records the entire B56 white waiting
frame at 13:57:39.894 on canvas 0x00807AA8:

- SET_BRUSH_STYLE
- GDI_BLT full-screen from FBS handle 0x8A
- CLEAR_RECT full-screen with 0xFFFFFFFF
- SET_BRUSH_STYLE
- SET_BRUSH_COLOR 0xFFFFFFFF
- CLEAR full-screen with 0xFFFFFFFF

No later STARTUP_GDI_ORIGIN event targets that visible canvas before the
natural handoff ~116 s later. Therefore the white screen is a genuine guest
Startup waiting frame, not host/compositor-generated output.

Startup also defines integer P&S category/key 0x100058F4:1. Official Startup
source identifies this as KPSStartupAppState: 1=Wait, 2=StartAnimations,
3=Finished.

## Latest build override — B58 STARTUPSTATEPS1

B58 is **BUILD-VALIDATED; DEVICE TEST REQUIRED; DIAGNOSTIC ONLY**.

Full snapshot:

`docs/handoff/history/B58-STARTUPSTATEPS1.md`

B58 build-time classification proves the current B28-derived baseline already
uses the correct category/key integer setter:

`baseline_setter=SET_INT_ALREADY_PRESENT`

Thus the older binary-template setter bug is not present in this project
baseline and B58 changes no P&S behavior.

B58 adds only:

`[NBOOT2][STARTUP_STATE_PS]`

around the existing set_int path for category 0x100058F4 key 1, logging
before/requested/after and set result.

Canonical GREEN:

- run `35969142523` / run number 168
- job `107534490446`
- HEAD `9a7a47a37d95c3d4ddecc29e26f5edbcd3c4037e`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `49ff189c66556f77184041edf341a2ba1fbad72803eb98e084e7fc1bb18dfe8f`
- IPA artifact `10795800813`
- audit artifact `10795451320`

Next device question: does 100058F4:1 successfully enter Wait=1, and does any
component later advance it to StartAnimations=2? Do not patch TfxServer,
ClearRedrawStore, focus or redraw ordering until this synchronization state is
observed.


## Real-device RM-356 visual oracle — 2026-09-24

Full reference:

`docs/handoff/history/REAL5800-BOOT-REFERENCE-2026-09-24.md`

User supplied a real Nokia 5800 normal-boot recording plus a no-SIM screenshot.

The real visual chain is now an acceptance oracle:

power-on -> white/NOKIA -> Nokia hands/welcome animation -> first-boot
date/time UI when applicable -> S60 Idle/home.

When no SIM is installed, the real RM-356 presents a continue-without-SIM /
offline-mode question. The user's real-device observation is that Yes continues
boot and No powers the phone off.

B55-B57's blank white Startup surface is therefore a legitimate intermediate
phase but not completion. Future builds must progress beyond white to the
no-SIM query and/or welcome animation, then ultimately first-boot UI / Idle.

Use the real RM-356 behavior as authoritative when it differs from generic open
Symbian Startup source.


## Boot-path decision — SIM present / normal startup

Project direction confirmed by user: NATIVEBOOT2 will target the **normal Nokia 5800 RM-356 boot path with a SIM present**.

This is now the primary acceptance path.

The no-SIM/offline-mode branch remains only as a real-device reference and must
not drive the next implementation decisions.

Primary expected visual/state sequence:

power-on
 -> Nokia splash
 -> Startup white transition surface
 -> welcome/Nokia-hands animation
 -> operator/startup continuation when configured
 -> first-boot/RTC UI only when genuinely required
 -> S60 Idle/home screen

For the main test path, an offline/no-SIM confirmation dialog is **not**
expected and must not be synthesized.

B58/B59 selection rules under the SIM-present baseline:

- First verify KPSStartupAppState progresses from Wait=1 to
  StartAnimations=2.
- If state 2 never appears, trace the normal critical-block / Starter
  synchronization component responsible for advancing Startup.
- If state 2 appears but the screen remains white, trace the Startup property
  subscription callback into WaitingStartupAnimationStartL() and
  DoStartupShowWelcomeAnimationL(), then the startup animation controller/assets.
- Do not force the offline query, no-SIM state, Home focus, or a synthetic
  animation.


## Latest device override — B58 STARTUPSTATEPS1 DEVICE1

B58 is **DEVICE-OBSERVED; STATE READBACK SUCCESS; EXIT CRASH OBSERVED**.

Full snapshot:

`docs/handoff/history/B58-DEVICE1.md`

Startup state marker proves category/key integer P&S works:

`0x100058F4:1 before=0 requested=1 after=1 set_result=1`

No category/key request for StartAnimations=2 appears in this run. The visible
result remains Nokia splash -> stable Startup white surface.

The supplied Apple .ips attributes the exit crash to host teardown:

`gdi_store_command_segment::~gdi_store_command_segment`
 -> `redraw_msg_canvas::~redraw_msg_canvas`
 -> `window_server_client::~window_server_client`
 -> `window_server::disconnect`
 -> `kernel_system::wipeout`

Exception is EXC_BAD_ACCESS / SIGSEGV at address 0x18 on the Symbian OS thread.

## Latest build override — B59 GSTOREEXITGUARD1

B59 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B59-GSTOREEXITGUARD1.md`

B59 changes only redraw-store teardown. It avoids unsafe final deref of retained
FBS font/bitmap refs when the object has ref_count==1 and owner==nullptr, and
adds:

`[NBOOT2][GSTORE_EXIT_GUARD]`

B58 Startup-state diagnostics remain unchanged.

Canonical GREEN:

- run `35995597677` / run number 169
- job `107619640241`
- HEAD `656303d83d23efaf2a877a3ce2e69eb60ad9b652`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `e77367744136b20ece0e0d93eca34ca0540b29b496f09d2fd5f6af26a76c191f`
- IPA artifact `10806605340`
- audit artifact `10806047606`

Next: device-test clean exit on B59. Once teardown is stable, add a separate
Startup-state writer probe covering the handle-based integer P&S setter so the
normal SIM-present path can identify who should advance 0x100058F4:1 from
Wait=1 to StartAnimations=2.


## Latest device override — B59 GSTOREEXITGUARD1 DEVICE1

B59 is **DEVICE-PASS FOR CLEAN EXIT**.

Full snapshot:

`docs/handoff/history/B59-DEVICE1.md`

The user reproduced NOKIA -> Startup white, selected `Thoát Emulator`, and
returned normally without an iOS process crash. Logs complete the shutdown path
through graphics join, state reset and shutdown_done.

No `[NBOOT2][GSTORE_EXIT_GUARD]` marker appears in this run, so clean exit is
device-confirmed but the guard branch is not independently proven to be the
unique causal fix.

Boot state remains:

`0x100058F4:1 0 -> 1`

with no category/key StartAnimations=2 write observed.

## Latest build override — B60 STARTUPSTATEWRITER1

B60 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B60-STARTUPSTATEWRITER1.md`

B60 adds diagnostic-only handle-based writer marker:

`[NBOOT2][STARTUP_STATE_HANDLE]`

for Startup state property 0x100058F4:1. Existing B58 category/key tracing and
B59 exit guard remain active.

Canonical GREEN:

- run `35999937174` / run number 178
- job `107633834377`
- HEAD `5a51e6a749e8d7fa357f7a747cc0156db55322c9`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `e456da3b8a8269666b3a0e1f92be7b74440512e1b5e50b804950b4ee36e86295`
- IPA artifact `10808270519`
- audit artifact `10807427655`

Next device question: does any handle-based writer advance Startup state to
StartAnimations=2? If neither P&S write path does, move upstream to the
SSM/Starter command-list writer responsible for publishing value 2.


## Visual note — B58/B59 top debug marker phase

Re-review of the device videos against the logs resolves the yellow/cyan
difference exactly.

The coloured square is the B51+ iOS host-only DIRECTSCREEN_PRESENT diagnostic
marker. Every present frame rotates through four phases/positions:

- phase 0 -> marker [24,128,72,72]
- phase 1 -> marker [120,128,72,72]
- phase 2 -> marker [216,128,72,72]
- phase 3 -> marker [312,128,72,72]

The video colours map to those four phases (magenta/cyan/yellow/green).

B58:
- total DIRECTSCREEN_PRESENT count: 175
- final present: frame 174, phase 2, marker [216,128,72,72]
- therefore the frozen host marker is yellow

B59:
- total DIRECTSCREEN_PRESENT count: 174
- final present: frame 173, phase 1, marker [120,128,72,72]
- therefore the frozen host marker is cyan

This is not a new boot-state signal. It is simply the modulo-4 debug marker
left visible by the final host present before the guest stalls on the white
Startup surface.

Boot semantics are unchanged between B58 and B59:
- Startup state remains 0 -> Wait(1)
- same 5-command Startup white redraw store is replayed
- Startup still requests missing TfxServer after handoff
- Home screen exists in the compositor tree but is not physically visible
- no observed StartAnimations(2)

B59's confirmed progress is clean teardown/exit only.


## Latest device override — B60 STARTUPSTATEWRITER1 DEVICE1

B60 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS; NO NEW VISUAL BOOT CHECKPOINT;
EXIT CRASH REPRODUCED**.

Full snapshot:

`docs/handoff/history/B60-DEVICE1.md`

B60 confirms:

- category/key Startup state still writes `0 -> Wait(1)`;
- zero `[NBOOT2][STARTUP_STATE_HANDLE]` events target 0x100058F4:1;
- therefore neither observed integer P&S writer path publishes
  `StartAnimations(2)`;
- visual output remains NOKIA -> stable blank-white Startup surface;
- Startup still requests missing TfxServer after handoff.

This closes the handle-writer ambiguity from B58/B59. The next boot boundary is
upstream SSM/Starter command-list execution responsible for publishing value 2.

B60 also reproduces the exit crash. Shutdown stops at `os_join_begin`, and the
Apple .ips again faults in
`gdi_store_command_segment::~gdi_store_command_segment()` during
`kernel_system::wipeout()`, with EXC_BAD_ACCESS at 0x18.

No `[NBOOT2][GSTORE_EXIT_GUARD]` marker fires. B59's narrow ownerless-final-ref
guard is therefore not a complete fix; its clean B59 exit was timing-dependent.

Temporary focus transfer to Home screen at 20:03:03 occurs only while Startup's
WindowGroup is destroyed during wipeout and is NOT a new boot checkpoint.


## Latest build override — B61 GSTOREWIPEOUT2

B61 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B61-GSTOREWIPEOUT2.md`

B61 strengthens the B59 teardown fix only during `kernel_system::wipeout()`.

All redraw-store segments, including direct `pending_segment_`, capture the
kernel pointer. During wipeout their destructor returns before touching any
retained FBS font/bitmap pointer and logs:

`[NBOOT2][GSTORE_WIPEOUT_GUARD]`

Normal-runtime refcount/deref behavior and all guest boot behavior remain
unchanged.

Canonical GREEN:

- run `36007760773` / run number 180
- job `107660254711`
- HEAD `24e84ad10c53e85216343728699f2af2ffc09f27`
- compile requests/hits/misses `149/110/39`
- actual compilations `39`
- compilation failures `0`
- IPA SHA-256
  `f07178925ea6b92e063d74856daf3a9e10a02f5cf477c27305042a30cc0910b1`
- IPA artifact `10811377565`
- audit artifact `10811596815`

Next device test: boot to white, choose `Thoát Emulator`, verify that the app
returns normally and does not generate a new iOS .ips crash. After clean-exit
validation, return to the boot blocker upstream of StartAnimations=2.


## Latest device override — B61 GSTOREWIPEOUT2 DEVICE1

B61 is **DEVICE-PASS FOR CLEAN EXIT; WIPEOUT GUARD CONFIRMED; NO NEW BOOT CHECKPOINT**.

Full snapshot:

`docs/handoff/history/B61-DEVICE1.md`

This was a **clean install**, not installed over B60.

The guest boot remains NOKIA -> stable blank-white Startup surface. Startup P&S
still writes only `0x100058F4:1 = Wait(1)`; no handle-based writer and no
StartAnimations=2 are observed.

The teardown result is now strong:

- `[NBOOT2][GSTORE_WIPEOUT_GUARD]` fires 27 times during final wipeout;
- guarded segments include nonzero retained references, including
  `font_refs=0 bitmap_refs=1` and `font_refs=1 bitmap_refs=4`;
- shutdown reaches `os_join_done`, `graphics_join_done`,
  `state_reset_done`, `shutdown_done`;
- user returns normally to EKA2L1 UI;
- no new iOS .ips crash is produced.

This is materially stronger evidence than B59's clean exit because B61's guard
is confirmed to execute on retained-FBS segments in the same teardown path that
crashed B58/B60.

B61 teardown track is accepted. Keep B61 in the chain.

Next boot boundary: trace System Starter / startup-policy / command-list
execution responsible for publishing `EStartupAppStateStartAnimations = 2`
on the normal SIM-present RM-356 path.


## Latest build override — B62 STARTERGLOBALSTATE1

B62 is **BUILD-VALIDATED; DEVICE TEST REQUIRED** and should be **installed over
B61**.

Full snapshot:

`docs/handoff/history/B62-STARTERGLOBALSTATE1.md`

B62 moves upstream from Startup's private Wait=1 property and traces the Starter
critical-phase property:

`KPSGlobalSystemState = 0x101F8766:0x41`

New diagnostic marker:

`[NBOOT2][STARTER_GLOBAL_STATE]`

It covers category/key Get, category/key Set, and handle-based integer Set with
before/requested/after values plus process/thread identity. It changes no P&S
value.

Nokia/Symbian Startup source uses this property to decide whether Starter's
critical phase has ended. Important values are 100..104 for the early startup
sequence, with 104 = CriticalPhaseOK; normal SIM-present terminal states include
109 = NormalRfOn and 110 = NormalRfOff.

Canonical GREEN:

- run `36016936055` / run number 181
- job `107691773271`
- HEAD `bc8da2307427095d20bfd5d21c7b5b67fe958b8c`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `d4800eec71e1d353ecfcb28fec2a73823f8bd06af706cada10cd3ddd3e36fb11`
- IPA artifact `10814674270`
- audit artifact `10814927913`

Device test: install B62 over B61, run normal SIM-present boot through NOKIA ->
white, then send logs. The key decision is the final value and writer of
0x101F8766:0x41.


## Latest device override — B62 STARTERGLOBALSTATE1 DEVICE1

B62 is **DEVICE-OBSERVED; DIAGNOSTIC SUCCESS; GLOBAL STARTUP STATE STALL IDENTIFIED**.

Full snapshot:

`docs/handoff/history/B62-DEVICE1.md`

Clean-install B62 proves `KPSGlobalSystemState 0x101F8766:0x41` follows:

- `0 -> 100` by `SYSSTART / StarterServer`
- `100 -> 101` by `SYSSTART / StarterServer`
- then no further write

Startup, AknCapServer and Home screen all later read `101`.

Thus Starter is stuck at `ESwStateStartingCriticalApps = 101`; it never reaches
102/103/104, so Startup's critical block never completes and private
`KPSStartupAppState` remains `Wait=1`.

Immediately around the 100 -> 101 edge:
- two SYSSTART LocaleData files are absent;
- StarterServer hits SVC miss `0xE3`;
- state 101 is still successfully published;
- a single SAServer IPC `0x67` is unimplemented immediately afterward.

These are candidates, not yet proven causes. Because 0x67 occurs directly after
the transition and its caller/ABI are not logged, the recommended next
diagnostic is an exact SAServer 0x67 probe that preserves current
KErrNotSupported behavior.

B61 wipeout guard remains device-confirmed and shutdown completes cleanly.


## Latest build override — B63 SASELFTESTABI1

B63 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B63-SASELFTESTABI1.md`

B62 proved Starter stalls at `StartingCriticalApps=101`. The first
unimplemented SAServer request immediately after that transition is opcode
`0x67`.

Public Symbian source identifies `0x67 / 103` as
`StartupAdaptation::EExecuteSelftests`, with response type
`TResponsePckg (TInt)`. This is the adaptation self-test boundary preceding
`SelfTestOK=102`.

B63 registers only exact opcode 0x67 and logs:

`[NBOOT2][SA_SELFTEST_ABI]`

including caller process/thread/session and full 4-slot IPC ABI. It deliberately
preserves `KErrNotSupported`; no state or descriptor is modified.

Canonical GREEN:

- run `36022003611` / run number 182
- job `107708966701`
- HEAD `68cf65b983850f614f046158db278ebd6feb3eac`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `89528414195d1b93d1aabcb2b342c8a262ce93c547a08ca45fc200415339f59b`
- IPA artifact `10816504737`
- audit artifact `10817586261`

Next device decision: if the RM-356 0x67 request matches the standard
TResponsePckg envelope, implement a narrow self-test success response and test
whether Starter advances `101 -> 102`.


## Latest device override — B63 SASELFTESTABI1 DEVICE1

B63 is **DEVICE-OBSERVED; ABI PROVEN; FAILURE PATH IDENTIFIED**.

Full snapshot:

`docs/handoff/history/B63-DEVICE1.md`

Exact SAServer `0x67` is confirmed as
`StartupAdaptation::EExecuteSelftests`, sent by `SYSSTART / StarterServer`.

RM-356 ABI:

- types `[4,6,4,4]`
- sizes `[12,0,12,0]`
- max `[12,0,12,16]`
- slot 2 template `[0x00010004,0x01000067,txn]`
- slot 3 writable response buffer

B63 returns `KErrNotSupported (-5)`. Starter subsequently publishes:

`101 StartingCriticalApps -> 117 FatalStartupError`.

Thus the self-test boundary is causal and the next correct behavior is to
return the documented TResponsePckg/TInt success envelope, not to force state
102 directly.

B63 also later exposes the Home screen after Splash drops: Home group 76 gains
focus and its 360x640 canvas is `physically_seen=1 draw_result=1`. This is
useful compositor evidence but is NOT normal boot progress because it occurs
on the FatalStartupError path.

B61 clean-exit protection remains healthy.

## Selected next build — B64 SASELFTESTRESPONSE1

B64 narrowly implements EExecuteSelftests success using the proven RM-356 SA
transport:

- echo slot-2 12-byte response envelope;
- write TInt(KErrNone) to slot 3;
- complete KErrNone;
- no direct P&S state injection.

Primary acceptance is Starter `101 -> 102 SelfTestOK` without transition to
117.


## Latest build override — B64 SASELFTESTRESPONSE1

B64 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B64-SASELFTESTRESPONSE1.md`

B64 implements the now-proven RM-356 response for
`StartupAdaptation::EExecuteSelftests / SAServer 0x67`:

- echo the 12-byte slot-2 response envelope;
- write `TInt(KErrNone)` to slot 3;
- complete `KErrNone`;
- no direct global-state or Startup-state injection.

New marker:

`[NBOOT2][SA_SELFTEST_RESPONSE]`

Canonical GREEN:

- run `36064120244` / run number 184
- job `107849736732`
- HEAD `8e5bf9c24b6f3583e34e76ed4d03c8363abbb711`
- compile requests/hits/misses `149/148/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `400849d5f2109f4857881b98979d3d4a5740f97480f9d91079027685de450372`
- IPA artifact `10835737543`
- audit artifact `10835867300`

Primary device question: does valid self-test success move Starter
`101 StartingCriticalApps -> 102 SelfTestOK` without entering
`117 FatalStartupError`?


## Latest device override — B64 SASELFTESTRESPONSE1 DEVICE1

B64 is **DEVICE-OBSERVED; SELFTEST RESPONSE PASS; FATAL PATH REMOVED; STARTER STILL STUCK AT 101**.

Full snapshot:

`docs/handoff/history/B64-DEVICE1.md`

B64's exact RM-356 EExecuteSelftests response succeeds:

- template copied from slot 2;
- header write succeeds;
- slot-3 TInt payload write succeeds with KErrNone;
- RMessage completes KErrNone.

The B63 `101 -> 117 FatalStartupError` transition disappears completely.
However Starter publishes no new global state after
`101 StartingCriticalApps`; later AknCapServer, Startup and Home screen all
continue reading 101.

Startup private state remains `Wait=1`; there is still no
`StartAnimations=2`.

Video remains NOKIA -> blank-white Startup, with no Nokia hands, RTC/date-time
or visible S60 Home/Menu before exit. Home receives focus only during teardown
after Startup is destroyed, which is not boot progress.

B61 wipeout protection remains healthy and shutdown completes normally.

The blocker is now inside the remaining StartingCriticalApps work rather than
the self-test transport itself.

## Latest build override — B65 STARTERRENDEZVOUS1

B65 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B65-STARTERRENDEZVOUS1.md`

B65 adds diagnostic-only `[NBOOT2][STARTER_RENDEZVOUS]` tracing to SYSSTART
UID3 `0x100059C9` process rendezvous/logon operations. It identifies the
target process for each arm/queue/completion/cancel event while preserving all
existing process semantics.

Canonical GREEN:

- run `36069095793` / run number 185
- job `107865597224`
- build HEAD `b9ef9ad46cd9092586b0d4254b81aa454f0228d6`
- compile requests/hits/misses `150/149/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `9dc349c9674a0059fa9566a8eb3c9a61910b56e609151e2536fce7503d7a990f`
- IPA artifact `10837880606`
- audit artifact `10837930432`

Recommended test: install B65 over B64 for the cleanest A/B comparison, run
through NOKIA -> white for 2-3 minutes, then send logs. The key result is the
exact critical-app rendezvous target that remains unresolved while global state
stays at 101.


## Latest device override — B65 STARTERRENDEZVOUS1 DEVICE1

B65 is **DEVICE-OBSERVED; RENDEZVOUS TARGETS RESOLVED; NO POST-101 PROCESS-WAIT BLOCKER FOUND**.

Full snapshot:

`docs/handoff/history/B65-DEVICE1.md`

The global state remains `100 -> 101`; B64 self-test success remains healthy
and Startup remains `Wait=1`.

B65 resolves the process-wait ambiguity:

- HWRMServer is armed before state 101 and cancelled after ~30 s, but Starter
  continues and later publishes 101, so this is not the active post-101
  blocker.
- profilesettingsmonitor is armed after state 101 and completes with reason 0.
- no other new SYSSTART process-rendezvous arm remains unresolved after 101.

Do not patch profilesettingsmonitor/HWRM/cntsrv/dbrecovery based on this run.

The investigation now moves to the real RM-356 Starter policy/configuration
rather than guessing from generic startup order.

## Latest build override — B66 STARTERSCRIPTDUMP1

B66 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B66-STARTERSCRIPTDUMP1.md`

B66 adds read-only `[NBOOT2][STARTER_SCRIPT_DUMP]` capture for:

- `Z:\private\100059C9\ScriptInit.txt`
- `Z:\private\100059C9\script0.txt`
- `Z:\private\100059C9\script1.txt`
- `C:\private\100059C9\plg_script*.txt`

It uses a separate read-only VFS handle, capped at 65536 raw bytes, and does
not alter the guest file cursor or startup state.

Canonical GREEN:

- run `36071875735` / run number 191
- job `107874453544`
- build HEAD `c28fe41d9646ee1e6d3144a91efb0c98d9a2ce64`
- compile requests/hits/misses `150/149/1`
- actual compilations `1`
- compilation failures `0`
- IPA SHA-256
  `91146a96cd7a37a94021971b89f8a6c7458a77647b9e73be30d50dbb97053ef3`
- IPA artifact `10838543339`
- audit artifact `10838548231`

Recommended test: install B66 over B65, run through NOKIA -> white for 2-3
minutes, exit normally, and send all logs. Video is only needed if visual
behavior changes.


## Latest device override — B66 STARTERSCRIPTDUMP1 DEVICE1

B66 is **DEVICE-OBSERVED; SCRIPT CAPTURE SUCCESS; TEXT SCRIPTS RULED OUT AS THE 101 -> 102 POLICY SOURCE**.

Full snapshot:

`docs/handoff/history/B66-DEVICE1.md`

B66 captures ScriptInit.txt and generated plg_script1..4.txt completely. Their
contents are file-system initialisation (MD/CD/CP: metadata DBs, bookmarks,
certificates and media/RAM-drive directories), not the ordered critical-app
state policy. Neither script0.txt nor script1.txt is opened in this boot.

Starter remains:

- global state `0 -> 100 -> 101`;
- B64 EExecuteSelftests response remains KErrNone;
- no state 102 and no FatalStartupError 117.

The decisive new observation is that SYSSTART opens
`Z:\\resource\\starter_arm.RSC` at 06:50:10.709, before global state 100.
This is the next exact RM-356 Starter policy artifact to capture.

B61 teardown remains healthy: 27 GSTORE_WIPEOUT_GUARD events and the Persistent
log reaches `normal_restart_done has_device=1`.

## Latest build override — B67 STARTERSSCDUMP1

B67 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B67-STARTERSSCDUMP1.md`

B67 adds diagnostic-only:

`[NBOOT2][STARTER_SSC_DUMP]`

for exact `Z:\\resource\\starter_arm.RSC`. It uses a separate
`READ_MODE | BIN_MODE` VFS handle and emits the raw resource as uppercase HEX
in 512-byte chunks, capped at 262144 bytes. It changes no guest file cursor,
P&S state, IPC response, process/rendezvous, graphics or teardown semantics.

Canonical GREEN:

- run `36076676081` / run number 196
- job `107889315577`
- HEAD `7515a78766a72c03b308c67fee9f03b51d5ef692`
- manifest/apply/contract/regression PASS
- iOS compile/link + binary invariants PASS
- compile requests/hits/misses `150/149/1`
- compilation failures `0`
- IPA SHA-256
  `13c83e3cd126178c91e461ba672a4365a4ff3ca4981dbe87a1e57318cd80caec`
- IPA artifact `10840189166`
- audit artifact `10840243716`

Next: install B67 over B66, boot normally, exit normally and send all three
logs. Video is needed only if visual behavior changes. Acceptance is a complete
STARTER_SSC_DUMP begin/data/end sequence with captured==raw_size and
truncated=false. Reconstruct/decode the real SSC before selecting any B68
functional change; do not force state 102 directly.


## Firmware-policy override — RM-356 SYM.RPKG STARTER MAP

The user supplied the matching `SYM.RPKG`. It has now been parsed directly.

Full snapshot:

`docs/handoff/history/RM356-RPKG-STARTER-MAP1.md`

Key result:

- RPKG contains 8030 Z-drive entries.
- Exact `Z:\\resource\\Starter_Arm.rsc` extracted:
  SHA-256 `d29b88c93023f201e0b647e248036049ea4fce87acdb511d3e1450b491a05d92`.
- The normal-mode StartingCriticalApps command list is resolved as RID6:
  `ailaunch -> startup -> sysap -> phoneui -> clknitzmdls -> conditional touchscreen/plugin -> profilesettingsmonitor`.
- B66 device execution matches this list.
- `profilesettingsmonitor` is the final process item and successfully
  rendezvouses at 06:50:48.282.
- After that completion SYSSTART makes no global-state request for 102 and emits
  no further StarterServer activity until teardown.

Therefore the current blocker boundary is no longer an unknown critical app or
process-rendezvous dependency. It is the Starter state-machine continuation /
async-request wakeup path after the final RID6 WaitForStart completion.

B67 remains useful only as a device-side byte-for-byte VFS verification. The
firmware resource itself is already available from the matching RPKG.

Do not force state 102. The next diagnostic should trace whether StarterServer
is actually resumed after the final profilesettingsmonitor rendezvous and which
request/wait object or first operation follows that wakeup.


## Latest build override — B68 STARTERWAKE1

B68 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B68-STARTERWAKE1.md`

RM-356 RPKG analysis resolved the normal StartingCriticalApps list as RID6.
The final process item is `profilesettingsmonitor.exe`, and B66 DEVICE1 proves
it rendezvouses successfully with reason 0. Starter nevertheless never requests
global state 102.

B68 is diagnostic-only and traces the exact continuation boundary with:

- `[NBOOT2][STARTER_WAKE]`
- `[NBOOT2][STARTER_NOTIFY_WAKE]`
- `[NBOOT2][STARTER_WAIT_ANY]`
- `[NBOOT2][STARTER_SCHED]`
- `[NBOOT2][STARTER_SVC]`

The recurring SYSSTART KErrCancel on request status `0x00700364` is not treated
as causal by itself because the same pattern follows earlier successful
WaitForStart cycles. B68 compares request count/thread state and proves whether
StarterServer is signaled, scheduled, resumes guest code, and which SVC/wait
comes next.

B68 does not modify request results, signal counts, scheduler behavior,
rendezvous behavior, SAServer responses, P&S state, graphics or teardown. It
does not force state 102.

Canonical GREEN:

- run `36081287241` / run number 206
- job `107903597467`
- build HEAD `4f4f03648498c2511e35d941fbc2d003adbfbe99`
- manifest/apply/contract/regression PASS
- iOS compile/link + binary invariants PASS
- compile requests/hits/misses `150/145/5`
- cache hit rate `96.67%`
- compilation failures `0`
- IPA SHA-256
  `45809eea0e6bce81b2822ebeaca2021330791b378c9b65e7930454f1f5ab0e57`
- IPA artifact `10841699589`
- audit artifact `10841769277`
- NOJAVA / MANIC3 preserved

Next: install B68 over B67 if B67 was installed, otherwise over B66. Boot
normally through NOKIA -> blank-white Startup, exit normally and send the three
logs. Video is needed only if visible behavior changes.

Primary DEVICE1 decision is whether the final profilesettingsmonitor rendezvous
differs from earlier successful WaitForStart cycles at notify -> wait ->
scheduler -> first resumed SVC.


## Latest device override — B68 STARTERWAKE1 DEVICE1

B68 is **DEVICE-OBSERVED; FINAL RID6 WAKE/SCHEDULER PATH PASS; ALARM OPCODE 0x0C IDENTIFIED AS NEXT BLOCKER**.

Full snapshot:

`docs/handoff/history/B68-DEVICE1.md`

The final RM-356 RID6 process `profilesettingsmonitor.exe` completes
rendezvous with reason 0. Its request status changes request_count `-1 -> 0`,
StarterServer becomes runnable, the scheduler selects SYSSTART/StarterServer,
and guest code resumes immediately.

Therefore do not patch profilesettingsmonitor, notify signaling, the request
semaphore or scheduler based on this run.

Starter continues past the final WaitForStart and then reaches:

`Unimplemented opcode for Alarm server 0xC`

Immediately afterward it blocks in WaitForAnyRequest. A later KErrNone
completion wakes Starter once, Starter resumes at SVC 0x800000, then calls
WaitForAnyRequest again and remains blocked until exit.

Global state remains `0 -> 100 -> 101`; B64 self-test remains KErrNone and
B61 teardown remains healthy.

Current EKA2L1 upstream identifies Alarm opcode 12 / 0x0C as
`EASShdOpCodeGetAlarmIdList`. Upstream commit
`127823a47b76c7edd50ef8e0b52ddb9b71a18782` adds the missing response for
opcodes 9/11/12. This exact upstream fix is selected for B69.

## Latest build override — B69 ALARMIDLIST1

B69 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:

`docs/handoff/history/B69-ALARMIDLIST1.md`

B69 narrowly backports EKA2L1 upstream commit
`127823a47b76c7edd50ef8e0b52ddb9b71a18782` for Alarm ID-list requests.

It adds:
- Alarm opcode 9 = GetAlarmIdListForCategory
- Alarm opcode 12 / 0x0C = GetAlarmIdList
- shared serializer/completion for opcodes 9/11/12
- marker `[NBOOT2][ALARM_ID_LIST]`

The request now serializes the current (empty) alarm ID list, writes transfer
size to descriptor slot 1 and completes KErrNone instead of remaining
unanswered.

No global-state injection, scheduler change, rendezvous change or SAServer
change is made.

Canonical GREEN:

- run `36094691714` / run number 209
- job `107944359982`
- build HEAD `7902d36459ddc3d6aea09e11ecd120f8ded27e11`
- manifest/apply/contract/regression PASS
- iOS compile/link + binary invariants PASS
- compile requests/hits/misses `150/148/2`
- cache hit rate `98.67%`
- compilation failures `0`
- IPA SHA-256
  `dede20f7b4392d236c0fc71d0b57ec5150de791bf6beca896baf2b073e18ac58`
- IPA artifact `10846748557`
- audit artifact `10846684036`
- NOJAVA / MANIC3 preserved

Next: install B69 over B68 and boot normally. Acceptance is
`[NBOOT2][ALARM_ID_LIST] opcode=0xC ... completion=KErrNone`, disappearance
of the old unimplemented-opcode log, and evidence that Starter advances beyond
the former post-0xC wait. Check whether global state moves beyond 101; otherwise
take the first new post-0xC blocker as the next evidence.


## Latest device override — B69 ALARMIDLIST1 DEVICE1

B69 is **DEVICE-OBSERVED; ALARM 0x0C FIX PASS; STARTER ADVANCES; CURRENT PATH SELECTS SHUTDOWN DIRECTLY FROM STATE 101**.

Full snapshots:

- `docs/handoff/history/B69-DEVICE1.md`
- `docs/handoff/history/RM356-NORMAL-SIM-BOOT-MAP1.md`

Device/video result:

- B69 handles Alarm opcode `0xB` and `0xC` with
  `[NBOOT2][ALARM_ID_LIST] ... completion=KErrNone`.
- the old `Unimplemented opcode for Alarm server 0xC` line is gone.
- Starter advances beyond the exact B68 durable wait.
- request status `0x007008D4` later completes KErrNone and wakes
  StarterServer.
- after that wake, SYSSTART issues SAServer `EGlobalStateChange / 0x64`
  with input `0x74 = 116`.
- IMPORTANT: StartupAdaptation::TGlobalState uses
  `116 = ShuttingDown, 117 = FatalStartupError`, while the P&S
  TPSGlobalSystemState enum uses
  `116 = FatalStartupError, 117 = ShuttingDown`.
- SYSSTART then publishes P&S global state `101 -> 117`, so both operations
  mean **ShuttingDown**. B69 does not prove a FatalStartupError transition.

Video shows black -> white NOKIA logo at about 35 seconds; the NOKIA splash then
remains static through the rest of the ~327.8 s recording. No hands animation,
date/time or Home/Menu appears.

The intended RM-356 ENormal + usable-SIM path derived from ROM/RPKG and Nokia
startup APIs is:

`100 StartingUiServices -> 101 StartingCriticalApps -> 102 SelfTestOK ->
103 SecurityCheck -> SIM security/ESimUsable -> 104 CriticalPhaseOK ->
109 NormalRfOn`

(or 110 NormalRfOff for an offline selection).

Current B69 exits this path at state 101 before state 102 and before the SIM
security state machine is entered.

Next exact evidence boundary:
identify the source/ABI/payload of SYSSTART async request status
`0x007008D4`, which completes just before Starter selects
StartupAdaptation state 116 = ShuttingDown. B70 should also trace SIM P&S keys
0x31/0x32/0x33 and SAServer commands 0x65/0x66/0x68/0x6C/0x6D. Do not force
state 102, fake ESimUsable or suppress shutdown before this request is
identified.


## Latest build override — B70 SIMPATHPROVENANCE1

B70 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Selected project route:
**NORMAL BOOT + SIM PRESENT**.

Full snapshots:

- `docs/handoff/history/RM356-NORMAL-SIM-BOOT-MAP1.md`
- `docs/handoff/history/B70-SIMPATHPROVENANCE1.md`

B69 proves Alarm 0x0C is fixed but the firmware still exits state 101 by
selecting ShuttingDown before state 102/SIM security.

B70 is diagnostic-only and adds:

- `[NBOOT2][STARTER_IPC_ARM]`
  for every SYSSTART SendReceive, including server/function/request_status;
- `[NBOOT2][STARTER_ASYNC_ARM]`
  for stable B28 property-subscription provenance;
- `[NBOOT2][SIM_PS]`
  for Startup SIM P&S keys 0x31/0x32/0x33.

Primary target is guest request status `0x007008D4`.

B70 deliberately does not instrument legacy timer internals because the B28
bootstrap timer implementation differs materially from current upstream.
Existing B68 SVC/notify/wakeup markers remain available for correlation.

B70 does not force:
- state 102;
- ESimUsable;
- SIM owned/changed;
- any IPC result/property value.

Canonical GREEN:

- run `36099148918` / run number 219
- job `107957715459`
- build HEAD `44e7cedeeae5e2d487b53a1032c51f634400b325`
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- compile requests/hits/misses `151/150/1`
- cache hit rate `99.34%`
- compilation failures `0`
- IPA SHA-256
  `6e04a5e37a77a6f255c3560faef846650daa20a85e8225c4540d4984e137ad3f`
- IPA artifact `10849100731`
- audit artifact `10848921007`
- NOJAVA / MANIC3 preserved

Next device test: install B70 over B69, run the same normal boot through the
NOKIA plateau, exit normally and send EKA2L1.log, EKA2L1_Persistent.log and
EKA2L1_TakeThis.log. Video only if visible behavior changes.

First B70 DEVICE1 question:
does `request_status=0x007008D4` appear in STARTER_IPC_ARM or
STARTER_ASYNC_ARM? If yes, its exact server/function or property becomes the
B71 evidence target.

Also determine whether SIM P&S keys are touched and whether SAServer reaches
0x65/0x68/0x6C/0x6D. Do not synthesize SIM success before this evidence.


## Latest build override — B71 PHONEUICONE14RES1

B71 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshots:
- `docs/handoff/history/B70-DEVICE1.md`
- `docs/handoff/history/B71-PHONEUICONE14RES1.md`

B70 DEVICE1 is closed; no repeat is required.

Proven first-fatal chain:

`Telephone[0x100058B3] opens phoneui.r01 -> CONE 14
-> Starter result 14 -> global state 101 -> 116
-> native Phone start-up failed UI`.

Authoritative Symbian Classic UI defines CONE 14 as
`ECoePanicNoResourceFileForId`.

Canonical B71 traces only this exact Telephone/PhoneUI failure and adds:

- `[NBOOT2][CONE14_PHONEUI]`
- `[NBOOT2][CONE14_FRAME]`
- `[NBOOT2][CONE14_STACK]`
- `[NBOOT2][CONE14_CODE16]`
- `[NBOOT2][CONE14_FP]`
- `[NBOOT2][CONE14_SUMMARY]`
- `[NBOOT2][PHONEUI_RSC_DUMP]`

It scans 128 stack words, resolves code candidates, dumps bounded callsite code,
and captures the exact
`z:\resource\apps\phoneui.r01`
through a separate read-only VFS handle.

Important evidence rule:
canonical B71 uses `resource_range_assumption=NONE`.
Do not use the earlier unverified 0x4E738xxx resource-range draft as evidence.
Decode the exact B71 PHONEUI_RSC_DUMP bytes first.

B71 does not force SIM/state 102, suppress CONE14, rewrite Starter result 14,
or alter resource/SAServer/P&S/rendezvous behavior.

Canonical GREEN:

- run `36107741479` / #224
- job `107984034152`
- build HEAD `e5a6c3a55d448cbdc56e8b3a16b397451d84ebe4`
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- compile requests/hits/misses `151/149/2`
- cache hit rate `98.68%`
- compilation failures `0`
- IPA SHA-256
  `de93877fb12c33e1b35840a4dd108c5ebd2f1b6fc104812753e630d269aef9cc`
- IPA artifact `10851856967`
- audit artifact `10851452716`
- NOJAVA / MANIC3 preserved

Next device test:
install B71 over B70, run normal Emulator boot, and wait until the same
Phone start-up failed UI appears. Leave that screen stable for 5-10 seconds,
then exit normally and send the three EKA2L1 logs. Video only if visible
behavior differs.

B72 must be selected from the exact B71 resource bytes plus caller
stack/module evidence. Do not synthesize SIM success or suppress Telephone
panic.



## Parallel exit-crash track — B70 host teardown

A separate B70 issue is now recorded:

`docs/handoff/history/B70-EXIT-IPCMSG-CRASH1.md`

Symptom:
after choosing Emulator exit, the iOS app can crash to the iPhone Home screen.

The supplied .ips proves this is a host teardown crash:
- EXC_BAD_ACCESS / SIGSEGV
- invalid address `0x0000000100000041`
- faulting thread: `Symbian OS thread`
- top frame: `eka2l1::ipc_msg::~ipc_msg() + 104`
- caller: `eka2l1::kernel_system::wipeout()`
- lifecycle queue simultaneously waits in `shutdown_threads()`

This is independent of the B71 PhoneUI CONE14 guest failure.

Current upstream commit
`437b29006bd8a0186f4070c9445f43e98e5c7435`
contains explicit IPC-message lifetime and teardown-order fixes matching this
crash class. Do not apply them to B71 pre-emptively.

B71 DEVICE1 should also repeat the same Exit Emulator action. If the iOS host
crash reproduces, B72 should use the .ips stack + upstream teardown fix as the
separate host-exit target while preserving B71 PhoneUI diagnostics. If B71
exits cleanly, do not introduce an unnecessary teardown patch.


## Latest device override — B71 PHONEUICONE14RES1 DEVICE1

B71 is **DEVICE-OBSERVED; CONE14 REPRODUCED; PANIC STACK CAPTURED; B70 EXIT CRASH NOT REPRODUCED**.

Full snapshot:
- `docs/handoff/history/B71-DEVICE1.md`

Key results:

- Telephone UID3 `0x100058B3` again self-panics `CONE 14`.
- panic PC/LR resolve to `euser.dll`; the captured stack contains real frames
  in `bafl.dll`, `cone.dll` and `PhoneUIUtils.dll`.
- 128 stack words were scanned.
- no register/stack value matches `0x4E738xxx`;
  `stack_candidates=0`.
- therefore the logical PhoneUI resource ID has already been consumed before
  the final panic path; do not keep widening the thread_kill stack probe.

Matching SYM.RPKG was re-checked:
- `phoneui.r01` size 28134;
- index table offset 27396;
- 368 resources, signature base `0x4E738000`.
- PhoneUIUtils.dll contains five aligned PhoneUI resource IDs
  `0x160,0x00A,0x019,0x156,0x0C9`; all five records exist.
- phoneui.exe contains `0xE2`; that record also exists.

This weakens the simple "missing record in RPKG" hypothesis and moves the
investigation toward CONE/BAFL resource registration/signature/lookup routing.

State path in B71:
- P&S 0 -> 100 -> 101 -> 116.
- after Telephone panic, Starter completion result=14 at
  request_status `0x00701684`.
- SAServer 0x64 input is `0x75 = 117`.
- here the dual enums agree semantically on **FatalStartupError**:
  StartupAdaptation 117 -> P&S 116.

SIM keys remain initialized at 100; no ESimUsable is observed before the
Telephone failure.

Exit result:
the user exited through the game-menu/Emulator exit path and the iOS app did
NOT crash. Logs reach `shutdown_threads_done`, `shutdown_done`,
`normal_restart_begin`, then a fresh log records
`normal_restart_done has_device=1`.

Therefore the B70 `ipc_msg::~ipc_msg()` host crash is not reproduced on B71.
Do not apply the proposed teardown backport as B72 without another
reproduction.

Selected next diagnostic:
B72 PHONEUIRSCIO1 traces Telephone read/seek activity for exactly
`Z:\resource\apps\phoneui.r01`, so the exact matching RPKG index table can
map the last pre-CONE14 access back to a resource record or prove the lookup
fails before record access.


## Latest build override — B72 PHONEUIRSCIO1

B72 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- `docs/handoff/history/B72-PHONEUIRSCIO1.md`

B71 DEVICE1 proved:
- Telephone CONE14 still reproduces;
- panic stack reaches bafl.dll, cone.dll and PhoneUIUtils.dll;
- no 0x4E738xxx resource ID survives at thread_kill;
- all known PhoneUIUtils/phoneui.exe PhoneUI resource constants found in the
  matching binaries map to records that actually exist in phoneui.r01;
- B70 host exit crash does NOT reproduce on B71; clean exit reaches
  normal_restart_done has_device=1.

Therefore B72 does not patch teardown and does not patch SIM.

B72 traces Telephone-only I/O for exactly:
`Z:\resource\apps\phoneui.r01`

Markers:
- `[NBOOT2][PHONEUI_RSC_READ]`
- `[NBOOT2][PHONEUI_RSC_SEEK]`

The matching RPKG geometry is embedded in the diagnostic context:
- size 28134
- resource index table offset 27396
- 368 resources
- signature base 0x4E738000

After DEVICE1, read/seek offsets can be mapped exactly against the RPKG index
table to identify the final resource lookup before CONE14 or prove failure
happens before resource-data access.

Canonical GREEN:
- run `36117855635` / #227
- job `108016063287`
- build HEAD `dd76bf33827e56f1731f45810885410d1405d6d4`
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses `151/150/1`
- cache hit rate `99.34%`
- compilation failures `0`
- IPA SHA-256
  `ef4bb8c5c32c958a6e2a2531524a661eb3e222e12e23535682886094d625c03e`
- IPA artifact `10855129639`
- audit artifact `10856435156`
- NOJAVA / MANIC3 preserved

Next:
install B72 over B71, reproduce the same startup failure, wait 5-10 seconds,
exit through the same game-menu/Emulator path, and send the three standard logs
plus Persistent-prev if present. Video only if visible behavior changes.

Also report whether Exit Emulator remains clean or the host crash returns.


## Latest device override — B72 PHONEUIRSCIO1 DEVICE1

B72 is **DEVICE-OBSERVED; PHONEUI RSC OPEN PROVEN; ZERO READ/SEEK MARKERS; CLEAN EXIT**.

Full snapshot:
- `docs/handoff/history/B72-DEVICE1.md`

Key evidence:
- phoneui.r01 is opened four times.
- final open: `17:24:53.938`, handle `1114122`.
- Telephone CONE14: `17:24:53.939`, about 1 ms later.
- `[NBOOT2][PHONEUI_RSC_READ]` count = 0.
- `[NBOOT2][PHONEUI_RSC_SEEK]` count = 0.
- no Unknown FSServer opcode occurs at that boundary.

Therefore the CONE14 path does not pass through the B72
`fs_server_client::file_read/file_seek` instrumentation after the observed
open. The next layer must identify caller/open ownership and alternate
FileServer opcodes / ReadFileSection, or prove failure is above EFsrv in
CONE/BAFL registration/search.

Exit Emulator is clean again:
`shutdown_threads_done -> shutdown_done -> normal_restart_begin ->
normal_restart_done has_device=1`.

Do not patch the old B70 ipc_msg teardown crash unless it reproduces again.

## Latest build override — B73 PHONEUIFSFLOW1

B73 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- `docs/handoff/history/B73-PHONEUIFSFLOW1.md`

B73 adds diagnostic-only:
- `[NBOOT2][PHONEUI_FS_FLOW]`: every Telephone FileServer request with raw
  and translated opcode, argument types/raw args, and arg3 file-path
  resolution.
- `[NBOOT2][PHONEUI_RSC_OPEN]`: exact phoneui.r01 caller process/UID/thread,
  handle and open mode.
- `[NBOOT2][PHONEUI_READ_SECTION]`: Telephone direct ReadFileSection path.

B72 read/seek probes remain preserved.

No FileServer/resource/SIM/Starter behavior is changed.

Canonical GREEN:
- run `36125160546` / #237
- job `108039473244`
- build HEAD `80e46d162bb17ccc71b325e830607d49f625aed4`
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses `151/149/2`
- cache hit rate `98.68%`
- compilation failures `0`
- IPA SHA-256
  `c36cfe695a0c4fc5475b197fa7a30c26036a076c277d5f9d302db4997c67ad0e`
- IPA artifact `10859887042`
- audit artifact `10858947250`
- NOJAVA / MANIC3 preserved

Next:
install B73 over B72, reproduce the same startup-failure boundary, wait 5-10
seconds, exit via game-menu/Emulator, and send the standard logs plus
Persistent-prev if present. Video only if visible behavior changes.


## Latest device override — B73 PHONEUIFSFLOW1 DEVICE1

B73 is **DEVICE-OBSERVED; PHONEUI RSC PARSE VALID; CALLHANDLING RESOURCE REGISTRATION MISSING; CLEAN EXIT**.

Full snapshot:
- `docs/handoff/history/B73-DEVICE1.md`

Proven sequence:
- Telephone itself opens/parses `Z:\resource\apps\phoneui.r01`.
- final FileServer sequence is
  Entry -> FileOpen -> FileSize -> FileSeek -> FileRead header/index/signature
  -> FileSubClose.
- the reads exactly match the valid phoneui.r01 resource structure.
- Telephone then panics CONE14.

The actual requested resource ID at panic is `0x1099B02D`.
Matching RM-356 RPKG proves it belongs to
`Z:\resource\apps\callhandlingui.r01`, resource index 0x2D/45.
That resource and file both exist.

B73 contains no callhandlingui.r01 open/entry before panic.

Nokia PhoneUI source shows `CPhoneResourceResolverBase::BaseConstructL()`
intends to register phoneui.rsc, callhandlingui.rsc, then phoneuitouch.rsc via
`CEikonEnv::AddResourceFileL()`.

CONE source shows `DoResourceFileForIdL()` panics CONE14 when no registered
resource file owns the requested ID.

Thus the first proven fatal resource blocker is:
**callhandlingui.r01 exists on Z but is not registered before
PhoneUIUtils requests 0x1099B02D.**

Exit Emulator remains clean; do not revive the B70 teardown patch unless the
host crash reproduces.

## Latest build override — B74 PHONEUIRESCALLER1

B74 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- `docs/handoff/history/B74-PHONEUIRESCALLER1.md`

B74 is diagnostic-only and captures saved Telephone guest context for
phoneui.r01/callhandlingui.r01 FileServer operations:

- `[NBOOT2][PHONEUI_RES_CALLER]`
  PC/LR/SP/CPSR + r0-r12;
- `[NBOOT2][PHONEUI_RES_FRAME]`
  96-word stack scan tagging exact RM-356 PhoneUIUtils.dll and cone.dll
  runtime addresses;
- `[NBOOT2][PHONEUI_RES_ID]`
  flags resource `0x1099B02D`;
- `[NBOOT2][PHONEUI_RES_CONTEXT_DONE]`.

Goal:
identify the exact guest caller/control-flow boundary after the final
phoneui.r01 registration and before the missing callhandlingui registration.
Only after this evidence should B75 restore registration.

Canonical GREEN:
- run `36130192940` / #241
- job `108055433959`
- build HEAD `7cc9a50d1c08992e70ef8ca1da2e9d6086e9f676`
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses `151/150/1`
- cache hit rate `99.34%`
- compilation failures `0`
- IPA SHA-256
  `e0eb3594ac099661ca31bf64bb3763459a33a5fb03d3418e2fc99e92ee9657e5`
- IPA artifact `10861787477`
- audit artifact `10861787485`
- NOJAVA / MANIC3 preserved

Next:
install B74 over B73, reproduce startup failure, wait 5-10 seconds, exit via
game-menu/Emulator and send standard logs plus Persistent-prev if present.
Video only if visible behavior changes.


## New-chat checkpoint — B74

For a fresh conversation, start with:
`docs/handoff/NEWCHAT-B74-2026-09-25.md`

This compact checkpoint points to the full B73 DEVICE1 and B74 build evidence and must be treated as the latest continuation point. Do not re-investigate B65-B73.


## Latest device override — B74 PHONEUIRESCALLER1 DEVICE1

B74 is **DEVICE-OBSERVED; PROBE PATH-MATCH DEFECT PROVEN; CONE14 REPRODUCED; HOST EXIT CRASH REPRODUCED**.

Full snapshot:
- docs/handoff/history/B74-DEVICE1.md

B74 guest behavior is unchanged from B73:
final phoneui.r01 parse/FileSubClose is immediately followed by Telephone
CONE14 with r6=0x1099B02D, and no callhandlingui.r01 registration/open occurs.

None of the B74 PHONEUI_RES_* markers fired. This was not an IPA mix-up:
the supplied .ips slice UUID and canonical B74 artifact Mach-O UUID both equal
5aa2782d-5e23-3984-86c2-8f1de58fc662.

The B74 apply script emitted single-backslash C++ path literals. In the binary,
\r and \a became control characters, so the exact path predicate could never
match z:\resource\apps\phoneui.r01.

B74 also reproduces the known host teardown crash:
EXC_BAD_ACCESS/SIGSEGV at 0x0000000100000041 on Symbian OS thread,
ipc_msg::~ipc_msg()+104 -> kernel_system::wipeout()+1192.

Per user decision, do not fix that crash in B75. Fix it only if B75 reproduces
the Home-screen crash again.

## Latest build override — B75 PHONEUIRESCALLER2

B75 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- docs/handoff/history/B75-PHONEUIRESCALLER2.md

B75 is diagnostic-only:
- corrects B74 escaped C++ path literals;
- adds [NBOOT2][PHONEUI_RES_MATCH2];
- preserves B74 caller/register/stack capture;
- does not register callhandlingui;
- does not alter CONE14/SIM/state/Starter;
- does not apply the host teardown fix.

Canonical GREEN:
- run 36134635918 / #242
- job 108069661366
- build HEAD a461caf279ee0bdb426ca0b9148fcc93a11262c7
- manifest/apply/contract/regression PASS
- iOS compile/link PASS
- binary invariants PASS, including PHONEUI_RES_CALLER and PHONEUI_RES_MATCH2
- package/upload PASS
- compile requests/hits/misses 151/150/1
- cache hit rate 99.34%
- compilation failures 0
- IPA SHA-256 781d3aec89ad6739af29564081e9c59d16a2b6dc7894cbd422dee47cd32822e4
- IPA artifact 10862314528
- audit artifact 10862144734
- NOJAVA / MANIC3 preserved

Next:
install B75 over B74 and repeat the normal boot. The first acceptance question
is whether PHONEUI_RES_MATCH2 and PHONEUI_RES_CALLER now fire at the final
phoneui.r01 boundary. Only then select the resource-registration fix.

If B75 again exits by crashing to iOS Home with ipc_msg::~ipc_msg() ->
kernel_system::wipeout(), promote the deferred teardown fix on the next step.

## New-chat checkpoint — B75

For a fresh conversation, start with:
docs/handoff/NEWCHAT-B75-2026-09-25.md

Do not re-investigate B65-B73.


## Latest device override — B75 PHONEUIRESCALLER2 DEVICE1

B75 is **DEVICE-OBSERVED; CALLER PROBE PASS; PHONEUI RESOURCE-INIT CHAIN NARROWED; NEW HOST GAMEMENU CRASH PROVEN**.

Full snapshot:
- docs/handoff/history/B75-DEVICE1.md

B75 records 41 PHONEUI_RES_MATCH2/CALLER contexts and 43 PhoneUI module-frame
hits. The critical Telephone path repeatedly carries PhoneUIUtils.dll +0x5094
while phoneui.r01 is being processed, and the same +0x5094 appears again in
the later CONE14 stack. CONE14 still has r6=0x1099B02D and no
callhandlingui.r01 registration/open occurs first.

Thus B75 successfully bridges the valid phoneui.r01 initialization path to the
fatal PhoneUIUtils/CONE call chain.

The B75 Home crash is a separate host issue. The user only pressed the
three-dot button. The .ips faults on the iOS main thread:
onMenuController -> presentGameMenu -> GameMenuView::showInView ->
UIButton::titleLabel -> UIButtonLegacyVisualProvider -> UILabel.
It is not the B70/B74 ipc_msg teardown crash.

## Latest build override — B76 GAMEMENUSAFETITLE1

B76 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- docs/handoff/history/B76-GAMEMENUSAFETITLE1.md

B76 changes only host GameMenuView title rendering:
UIButton is retained as the hit target, but option text is rendered by a plain
UILabel child. The crash-path calls setTitle/setTitleColor/titleLabel are
removed.

Runtime marker:
[NBOOT2][GAMEMENU_SAFE_TITLE]

Canonical GREEN:
- run 36139803235 / #244
- job 108086557161
- functional HEAD 2bb392ac7cf4b18384d15344f149543036ba6c41
- compile requests/hits/misses 152/151/1
- cache hit rate 99.34%
- compilation failures 0
- IPA SHA-256 eb68fd326ac856331611c5162575f797110ab0683f843b5659b0523d7e38aa99
- IPA artifact 10866436282
- audit artifact 10866436293
- Mach-O UUID B52D1C26-0C93-3833-8E88-E4B40E66AEA5
- NOJAVA / MANIC3 preserved

Device test order:
three-dot -> Cancel -> three-dot -> Exit Emulator.

If the menu now works but Exit Emulator produces ipc_msg::~ipc_msg() ->
kernel_system::wipeout(), promote the deferred teardown fix next.

Guest resource work remains paused only for this host validation. Resume from
PhoneUIUtils +0x5094 after B76 DEVICE1.

## New-chat checkpoint — B76

Start a fresh chat with:
docs/handoff/NEWCHAT-B76-2026-09-25.md


## Latest device override — B76 GAMEMENUSAFETITLE1 DEVICE1

B76 is **DEVICE-PASS; HOST GAME MENU STABLE; EXIT EMULATOR CLEAN**.

Full snapshot:
- docs/handoff/history/B76-DEVICE1.md

Device test proves:
- three-dot menu can be opened repeatedly;
- Cancel can be used repeatedly;
- no Home crash;
- Exit Emulator completes normally;
- no .ips;
- host log reaches BRIDGE_EXIT_PHASE normal_restart_done has_device=1.

Do not reopen B75 UIButtonLegacyVisualProvider or B70/B74 ipc_msg teardown
tracks unless a future build reproduces a crash.

Guest Telephone still panics CONE14 with r6=0x1099B02D.

Diagnostic correction:
PhoneUIUtils +0x5094/+0x50B8 are descriptor/literal data, not proven executing
frames. Real Thumb candidates in the CONE14 stack include +0x1BC0, +0x3A38,
+0x3B2C and +0x3B4C.

## Latest build override — B77 PHONEUIRESOLVEREXPORT1

B77 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- docs/handoff/history/B77-PHONEUIRESOLVEREXPORT1.md

B77 resolves the exact loaded RM-356 PhoneUIUtils export ordinal 182,
CPhoneResourceResolverBase::BaseConstructL(), and correlates its bounded
runtime range at both phoneui.r01 FileServer IPC and CONE14.

Markers:
- [NBOOT2][PHONEUI_BASECONSTRUCT_EXPORT]
- [NBOOT2][PHONEUI_BASECONSTRUCT_FRAME]
- [NBOOT2][PHONEUI_LITERAL_PTR]
- [NBOOT2][PHONEUI_BASECONSTRUCT_SCAN_DONE]

B77 is diagnostic-only and preserves B76 host fixes.

Canonical GREEN:
- run 36143687408 / #246
- job 108099418515
- functional HEAD 930a94e2fe366d39894a1a81d2ce69608ca933b5
- compile requests/hits/misses 152/150/2
- cache hit rate 98.68%
- compilation failures 0
- IPA SHA-256 b6301ef32c19744064b2843fea2ee3d036b0ee921b0c9d056db11140d1567ffc
- IPA artifact 10868711638
- audit artifact 10868996503
- Mach-O UUID 6348A9D9-F972-31D5-8782-E5E54339224D
- NOJAVA / MANIC3 preserved

Next:
install B77 over B76, boot to the same Phone startup failure, wait 5-10 s,
verify three-dot menu remains safe, Exit Emulator normally, send standard
logs.

B78 is chosen only after B77 DEVICE1 proves whether ordinal 182 is actually on
the failing resource-init path.

## New-chat checkpoint — B77

Start a fresh chat with:
docs/handoff/NEWCHAT-B77-2026-09-25.md


## Latest device override — B77 PHONEUIRESOLVEREXPORT1 DEVICE1

B77 is **DEVICE-OBSERVED; EXPORT-182 RESOLVED; BASECONSTRUCT FRAME ABSENT; CONE14 UNCHANGED**.

Full snapshot:
- docs/handoff/history/B77-DEVICE1.md

B77 resolves PhoneUIUtils ordinal 182 exactly:
CPhoneResourceResolverBase::BaseConstructL
- runtime +0x1BC8
- next export +0x1BF6 relative equivalent
- bounded span 0x2E

However PHONEUI_BASECONSTRUCT_FRAME count is zero in all 384-word FileServer
and CONE14 scans.

CONE14 remains reason 14 with r6=0x1099B02D.
No callhandlingui.r01 open/registration occurs.

+0x5094/+0x50B8 are descriptor/literal data.

Instruction-window validation identifies real Thumb BL return candidates:
- +0x1BC0 -> target +0x3B2E
- +0x3B4C -> target +0x3A28
- +0x3A38 -> target +0x46C4

Host shutdown/restart remains clean.

## Latest build override — B78 PHONEUICALLCHAIN1

B78 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- docs/handoff/history/B78-PHONEUICALLCHAIN1.md

B78 no longer treats arbitrary in-image pointers as callers. It validates
Thumb BL/BLX callsites, decodes BL targets, and maps return/target addresses to
PhoneUIUtils export ownership.

Markers:
- [NBOOT2][PHONEUI_RESOLVER_EXPORT_MAP]
- [NBOOT2][PHONEUI_CALLSITE]

Key runtime exports explicitly mapped:
181 Instance
182 BaseConstructL
307 ResolveResourceID
308 IsTelephonyFeatureSupported

Diagnostic-only; B76 host fixes and B77 diagnostics are preserved.

Canonical GREEN:
- run 36148877670 / #247
- job 108116800815
- functional HEAD d652d10cd68661274900734af79c1ef62ce8fbe4
- compile requests/hits/misses 152/150/2
- cache hit 98.68%
- compilation failures 0
- IPA SHA-256 42b454f7c2cdfb28e0fb646b2c16f1c451c13a9d62bef3bc2ed50ba11b1a6002
- IPA artifact 10870706328
- audit artifact 10870628680
- Mach-O UUID ABB63FE7-BA91-3DB6-9A61-C1595754B938
- NOJAVA / MANIC3 preserved

Next:
install B78 over B77, boot to current Phone startup failure, wait 5-10 s, exit
normally and send standard logs.

B79 is selected only from B78 validated call-chain evidence.

## New-chat checkpoint — B78

Start a fresh chat with:
docs/handoff/NEWCHAT-B78-2026-09-25.md


## Latest device override — B78 PHONEUICALLCHAIN1 DEVICE1

B78 is **DEVICE-OBSERVED; REAL CALLSITES PROVEN; BLX TARGETS UNRESOLVED**.

Full snapshot:
- docs/handoff/history/B78-DEVICE1.md

B78 proves 13 real Thumb BL/BLX callsites.

FileServer deep-stack:
- +0x1B70 BLX, B78 target unresolved
- +0x1B78 BLX, B78 target unresolved

CONE14 near-stack:
- +0x3A34 BLX, B78 target unresolved
- +0x3B48 BL -> +0x3A28
- +0x1BBC BL -> +0x3B2E

CONE14 remains reason 14 / r6=0x1099B02D.
No callhandlingui.r01 registration/open occurs.

Host normal restart remains clean.

## Latest build override — B79 PHONEUICALLCHAIN2

B79 is **BUILD-VALIDATED; DEVICE TEST REQUIRED**.

Full snapshot:
- docs/handoff/history/B79-PHONEUICALLCHAIN2.md

B79 adds architecture-correct Thumb BLX target decoding plus stack locality.

Validated B78 vectors:
- +0x1B70 F002 EDC0 -> +0x4274
- +0x1B78 F002 ED8C -> +0x41AC
- +0x3A34 F000 EE46 -> +0x4350

Markers:
- [NBOOT2][PHONEUI_BLX_TARGET]
- [NBOOT2][PHONEUI_CALLCHAIN_EDGE]

Diagnostic-only; no guest or host behavior changes.

Canonical GREEN:
- run 36151562614 / #248
- job 108125827530
- functional HEAD ab66e3d33fc39b2a0f2fe326971056e72cdf0f0d
- compile requests/hits/misses 152/150/2
- cache hit 98.68%
- compilation failures 0
- IPA SHA-256 eb62a6e7a49438ee8cce42dfba04bc494efece657de34667c5bf48c06c0f8f90
- IPA artifact 10871089877
- audit artifact 10871269583
- Mach-O UUID 462E23A0-2CCC-3C5A-B7BA-0D19D1BF0AD6
- NOJAVA / MANIC3 preserved

Next:
install B79, boot to current Phone startup failure, wait 5-10 s, exit normally,
send standard logs.

B80 is selected only from B79 DEVICE1 call-chain evidence.

## New-chat checkpoint — B79

Start a fresh chat with:
docs/handoff/NEWCHAT-B79-2026-09-25.md
