# NATIVEBOOT2 B71 PHONEUICONE14RES1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; CONE14 REPRODUCED; PANIC STACK CAPTURED; EXIT CRASH NOT REPRODUCED

## Inputs

Device logs:
- EKA2L1_Persistent(20260925-091111).log
- EKA2L1(20260925-091114).log
- EKA2L1_Persistent-prev(4).log
- EKA2L1_TakeThis(20260925-091117).log

## Startup state

Observed P&S global state:
- 0 -> 100 at 16:08:25.276
- 100 -> 101 at 16:08:58.145
- 101 -> 116 at 16:09:01.907

SIM P&S initialization remains:
- 0x101F8766:0x31 KPSSimStatus = 100
- 0x101F8766:0x32 KPSSimOwned = 100
- 0x101F8766:0x33 KPSSimChanged = 100

VPbkSimServer later reads KPSSimStatus=100.
No ESimUsable=101 transition is observed before the failure.

## Exact Telephone failure

At 16:09:01.895 Telephone[0x100058B3] self-panics:

- category: CONE
- reason: 14
- PC: 0x80298584
- LR: 0x802A3A39
- SP: 0x005041C0

Registers:
- r0 = 0xFFFF8001
- r1 = 0x00000002
- r2 = 0x0000000E
- r3 = 0x005041C4
- r4 = 0x00000004
- r5 = 0x0000000E
- r6 = 0x1099B02D
- r7 = 0x00812398
- r8-r12 = 0

PC/LR resolve to euser.dll:
- PC offset 0x313C
- LR offset 0xE5F0

The stack proves the resource-failure call chain includes:
- bafl.dll
- cone.dll
- PhoneUIUtils.dll
- centralrepository.dll
- VPbkCntModel.dll
- VPbkEng.dll
- ecom.dll

Notable PhoneUIUtils return/frame offsets captured:
- 0x1BC0
- 0x3A38
- 0x3B2C
- 0x3B4C
- 0x5094
- 0x50B8

## B71 resource-ID result

No register and none of the 128 scanned stack words contains a
0x4E738xxx PhoneUI resource ID.

B71 summary:
- phoneui_signature_base=0x4E738000
- phoneui_resource_count=368
- expected_last_index=0x170
- stack_candidates=0
- stack_words_scanned=128

Therefore the requested resource ID has already been consumed before the final
User::Panic/thread_kill path. B72 must observe the resource lookup earlier,
not widen the final panic stack further.

## Direct SYM.RPKG cross-check

The matching RPKG remains available and was parsed again.

phoneui.r01:
- size 28134
- index table offset 27396
- 368 resources
- resource signature base 0x4E738000
- SHA-256:
  05c419086de5710d361f7d8c910ef5284006b5ee879cb0acb448b8090a7ce9a1

PhoneUIUtils.dll contains these aligned 0x4E738xxx constants:
- 0x4E738160
- 0x4E73800A
- 0x4E738019
- 0x4E738156
- 0x4E7380C9

All five resource indexes exist in phoneui.r01.

phoneui.exe contains:
- 0x4E7380E2

Resource 0xE2 also exists.

This substantially weakens the simple hypothesis that the firmware package is
missing the requested PhoneUI record. The stronger hypotheses are now:
- resource-file registration/signature/search ownership;
- lookup routing in CONE/BAFL;
- or a different resource file/ID consumed before panic.

## Starter consequence

Immediately after the Telephone panic:
- Starter notify completes result=14
- request_status=0x00701684
- request_count -1 -> 0
- StarterServer resumes

SAServer function 0x64 then receives input 0x75 (117), and SYSSTART publishes
P&S global state 116.

For the dual enum mapping:
- StartupAdaptation state 117 = FatalStartupError
- P&S global state 116 = FatalStartupError

Therefore B71 is a proven FatalStartupError path caused by Telephone CONE14.
This differs from the earlier B69 direct-shutdown path.

## Exit Emulator result

The user exited through the game-menu/Emulator exit path and the iOS app did
NOT crash.

Teardown evidence:
- shutdown_threads_done reached
- shutdown_done reached
- normal_restart_begin reached
- a fresh log then records:
  normal_restart_done has_device=1

Therefore the B70 host crash in ipc_msg::~ipc_msg() is NOT reproduced on B71.
Do not apply the proposed IPC teardown backport as B72 without another
reproduction.

The B70 exit crash remains a separate historical observation only.

## Next diagnostic

B72 PHONEUIRSCIO1 should trace Telephone reads/seeks against exactly:
Z:\resource\apps\phoneui.r01

For each access record:
- file handle
- read/seek position
- requested and actual length
- file cursor before/after
- function flags

The exact RPKG resource index table can then map the last access before
CONE14 back to a resource index or prove lookup fails before record access.

Do not force SIM state, state 102, or suppress Telephone panic.
