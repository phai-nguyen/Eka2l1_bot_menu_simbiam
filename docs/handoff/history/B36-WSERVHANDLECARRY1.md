# NATIVEBOOT2 B36 — WSERVHANDLECARRY1

Updated: 2026-09-22
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Development branch: nativeboot2-current
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Code HEAD: 1ec56f99a6c6e469d6a8e3905aebb3c3cdae6e8a

## Why B36 exists

B35 EIKLEAVECALLER1 device logs preserved the repeated eiksrvs/EikAppUiServerThread User::Leave(-3) family and resolved the stable ws32 frame at +0x370A.

B35 evidence:
- ws32.dll base 0x80659048;
- raw return 0x8065C753;
- offset 0x370A;
- Thumb state = 1;
- nearest EABI export ordinal = 206;
- nearest export address = 0x8065C74B;
- delta = 0x8.

SymbianSource oss.FCL.sf.os.graphics identifies EABI ordinal 206 as:
RWindowTreeNode::SetNonFading(TBool).

The B35 halfword window also places opcode 0x5D in the immediate ws32 path.

Separately, the same B35 device log repeatedly reports as EikAppUiServerThread starts:
- Object handle is invalid 335544320 (0x14000000);
- Object handle is invalid 0.

## Protocol root mismatch

Symbian client source RWsBuffer::DoWrite() includes EWsOpcodeHandle (0x8000) only when the destination handle differs from the previous command.

Symbian server source CWsClient::CommandBufL() explicitly retains the previous destination object and reuses it when EWsOpcodeHandle is absent.

The reconstructed EKA2L1 WindowServer parser did not implement that rule. It created a fresh ws_cmd for every buffer entry and assigned obj_handle only when 0x8000 was present. An implicit-handle command therefore consumed an uninitialized/stale host value instead of the previous destination handle.

This is a generic protocol defect, not Nokia-, FEP-, UID-, or RM-356-specific behavior.

## B36 implementation

File changed at runtime reconstruction:
src/emu/services/src/window/window.cpp

B36:
- value-initializes ws_cmd with ws_cmd cmd{};
- creates nboot2_b36_previous_handle = 0 per command buffer;
- updates previous_handle whenever an explicit destination handle is present;
- assigns cmd.obj_handle = previous_handle when the command omits the handle;
- keeps all existing command payload parsing and dispatch order.

For first-device-test correlation, B36 also instruments the already-existing SetNonFading handler in:
src/emu/services/src/window/classes/winuser.cpp

Markers:
- [NBOOT2][WSERV_HANDLE_CARRY]
- [NBOOT2][WSERV_NONFADING_ENTER]
- [NBOOT2][WSERV_NONFADING_COMPLETE]

The existing:
context.complete(epoc::error_none);
is preserved. B36 does not convert KErrCancel, suppress Leave, or alter IPC result semantics.

## Preserved invariants

B36 does not change:
- stock Nokia avkonfep.dll / touchscreen VKB;
- SYSSTART startup ownership;
- native fbserv;
- Central Repository compatibility;
- loader/scheduler fixes;
- B26 iOS exit choreography;
- B34 focus_callback_mutex split;
- B35 EIKCALLSITE/EIKCODE16 diagnostics;
- Leave/trap semantics;
- EPOC94 0xAA unmapped;
- EPOC94 0xAB message_construct;
- EPOC94 0xAC message_kill;
- NOJAVA;
- MANIC3.

## TDD

Earlier trace-only RED:
- run 35732157150
- expected missing WSERV_NONFADING_DISPATCH marker.

Decisive functional RED:
- run 35732727339
- job 106762102647
- B20-B35 reconstruction PASS
- expected failure:
  NATIVEBOOT2-B36-WSERVHANDLECARRY1-TEST: FAIL: missing in command parser: std::uint32_t nboot2_b36_previous_handle = 0;

GREEN:
- run 35732983672
- job 106762968487
- code HEAD 1ec56f99a6c6e469d6a8e3905aebb3c3cdae6e8a
- B20-B36 apply/regression PASS
- iOS compile/link PASS
- binary invariants PASS
- B36 marker strings present in Mach-O
- IPA packaging/upload PASS
- NOJAVA/MANIC3 PASS

## FASTBUILD1

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
- compilations: 2
- compilation failures: 0

## Artifact

Unsigned IPA SHA-256:
d24551d96d8fde57c514b4a745d62a4d413e039f8b79ab2059b6d5e4434728c6

IPA artifact:
- ID 10696356734
- ZIP digest sha256:cd0b250769578c9ce823abf785a82ff7bd53640ee76eeecfc6f21dbde500cf27
- expires 2026-10-06

Audit artifact:
- ID 10696541481
- ZIP digest sha256:3a08d01f1695df6d5e3105cdad5f175ec355693598c6b163f72de6d8e63f58ac
- expires 2026-10-06

## Device acceptance

1. Sign/install B36.
2. Boot the Nokia 5800 path exactly as B35.
3. Let startup pass through the former repeated eiksrvs/AknFep failure window.
4. Use Thoát Emulator normally.
5. Send:
   - EKA2L1.log
   - EKA2L1_Persistent.log
   - EKA2L1_TakeThis.log

Primary acceptance signals:
- invalid WindowServer object handles at EikAppUiServerThread startup disappear or materially change;
- [NBOOT2][WSERV_HANDLE_CARRY] identifies whether opcode 0x5D used an implicit destination;
- [NBOOT2][WSERV_NONFADING_ENTER] and [NBOOT2][WSERV_NONFADING_COMPLETE] prove the corrected object reaches SetNonFading and completes KErrNone;
- repeated User::Leave(-3) disappears, reduces, or moves to a later causal boundary;
- B34 Exit Emulator remains healthy.

Do not create an immutable B36 functional branch until device evidence validates the fix.
