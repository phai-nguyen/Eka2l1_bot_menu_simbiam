# NATIVEBOOT2 B38 — EIKCANCELTRACE2

Updated: 2026-09-22
Status: DEVICE-OBSERVED; diagnostic target completed, causal state narrowed further.

## Why B38 exists

B37 WSERVBATCHCOMPLETE1 is DEVICE-OBSERVED. It proved that WindowServer request signaling can be deferred correctly until command-buffer completion:
- all 17 SetNonFading entries moved from signaled_before=1 to signaled_before=0;
- all 17 SetNonFading completions remained unsignaled inside the batch;
- WSERV_BATCH_SIGNAL then signaled once after batch completion.

The causal failure nevertheless remained unchanged:
- 16 EikAppUiServerThread User::Leave(-3);
- 16 access violations / KERN-EXEC 3;
- stable euser.dll PC 0x8029833C (+0x2EF4);
- stable euser.dll LR 0x802ABB29 (+0x166E0).

Ordering also proved the first Leave(-3) occurs before the later batch that dispatches opcode 0x5D SetNonFading. Therefore B38 is diagnostic-only.

## B38 diagnostics

B38 preserves B36/B37 behavior and adds two evidence channels.

WindowServer:
- [NBOOT2][WSERV_BATCH_CMD]
  - command index
  - opcode
  - effective object handle
  - command length
  - completion-written state before the command
  - previous completion result
  - signal state
- [NBOOT2][WSERV_BATCH_RESULT]
  - total commands
  - final opcode
  - final object handle
  - effective completion-written state
  - effective completion result
  - signal state before B37's final flush

ipc_context stores only a diagnostic mirror:
- nboot2_b38_last_completion_result
It is assigned from the same result already written by complete(); it does not participate in control flow.

Direct KErrCancel frame resolution:
- [NBOOT2][EIKDIRECT_FRAME]
- [NBOOT2][EIKDIRECT_CODE16]

These resolve the direct Leave PC and LR against the active codeseg export table and dump a bounded halfword window. This is separate from B35's stack-candidate tracing.

## Preserved behavior

B38 does not change:
- WindowServer command dispatch;
- completion/error values;
- B37 request-signal timing;
- SetNonFading KErrNone behavior;
- Leave/trap behavior;
- FEP behavior;
- SVC table;
- scheduler;
- loader;
- B34 Exit Emulator choreography;
- stock Nokia avkonfep.dll;
- NOJAVA / MANIC3.

## TDD

RED:
- commit: 02773c6cae716fa10959182e721e1c5b1b8558e4
- run: 35742603226
- job: 106795931691
- B29-B37 apply: PASS
- intended failure:
  NATIVEBOOT2-B38-EIKCANCELTRACE2-TEST: FAIL: missing in ipc_context diagnostic state: int nboot2_b38_last_completion_result = 0;

GREEN:
- code commit: 3c2e02ad7dbc29db244973db761f28810afe8e99
- run: 35743121880
- job: 106797710973
- B38 apply: PASS
- B38 contract: PASS
- full regression: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compilation failures: 0
- NOJAVA / MANIC3: PRESERVED

FASTBUILD audit:
- bootstrap: B28_CACHE
- bootstrap restore: 25 s
- patch/regression: 2 s
- CMake build: 163 s
- package: 2 s
- total: 213 s

## Artifact

IPA artifact:
- ID: 10699954176
- artifact ZIP digest: sha256:0dd99aaf99e83c43b9aa2d50f4211e19170ad272ab6cb1659925b0a117e5d311
- expires: 2026-10-06

Unsigned IPA SHA-256:
20da39a745f1fab9f0dc8519ff8177c7deda20dd86e8b1432a4b5ceb28a27d93

Audit artifact:
- ID: 10699939105
- digest: sha256:e3908770b652d3c13f0941db1a0a3cb48c8b001db75d2422d4250365232c54e6

## Device-test target

Install/sign B38 and reproduce the same Nokia 5800 startup path.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Primary analysis:
1. isolate the WindowServer batch immediately before each EIKFAULT_LEAVE;
2. read WSERV_BATCH_CMD to identify its exact opcode/object;
3. read WSERV_BATCH_RESULT to obtain the effective result before B37 final signaling;
4. resolve EIKDIRECT_FRAME for direct PC/LR nearest export ordinals;
5. decode EIKDIRECT_CODE16 around euser +0x2EF4 / +0x166E0;
6. confirm B34 Exit Emulator remains healthy.

Do not implement a behavioral B39 until B38 device evidence identifies the actual KErrCancel origin.


## Device result — B38 DEVICE1

B38 device logs complete the intended diagnostics.

Decisive results:
- all 16 EikAppUiServerThread Leave(-3) events are immediately preceded by a one-command WindowServer batch with opcode 0x16;
- SymbianSource identifies opcode 0x16 as EWsClOpCreateWindow;
- all 16 CreateWindow calls complete successfully with positive handle 0x00060006, so CreateWindow is not the KErrCancel source;
- direct euser LR resolves to ordinal 649 = User::Leave(int);
- avkonfep.dll +0xF104 is proven to be the direct caller return address of User::Leave, because it is the saved LR in the User::Leave frame;
- code immediately before +0xF104 loads a nested field, compares it with zero, forms -3, and calls User::Leave when the field is null;
- LeaveEnd / "Leave trapped by trap handler." is observed before the later fatal fault, so KErrCancel is successfully caught;
- SetNonFading occurs downstream in post-catch WindowServer processing and is not the producer of -3;
- the immediate fatal boundary is now euser.dll +0xAD7C, write address 0x10, with LR euser.dll +0xD9AD and r0/r1 zero.

B38 does not justify changing SVC 0xDF or suppressing KErrCancel. SymbianSource LeaveStart/LeaveEnd semantics match the observed firmware C++-exception Leave variant.

Preferred B39 is diagnostic-only EIKPOSTLEAVEAV1:
resolve the post-catch AV PC/LR/code/stack and safely dereference the AvkonFep caller state around saved caller r4 +0x10 -> +0x24.

Detailed snapshot:
- docs/handoff/history/B38-DEVICE1.md
