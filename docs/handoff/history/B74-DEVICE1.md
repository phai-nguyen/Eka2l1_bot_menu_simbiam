# NATIVEBOOT2 B74 PHONEUIRESCALLER1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; B74 PROBE PATH-MATCH FAILED; PHONEUI CONE14 REPRODUCED; HOST EXIT CRASH REPRODUCED

## Device inputs

Received:
- EKA2L1(20260925-121823).log
- EKA2L1_Persistent(20260925-121830).log
- EKA2L1_TakeThis(20260925-121749).log
- eka2l1-2026-09-25-190811.ips

Selected route remains:
NORMAL BOOT + SIM PRESENT

## Guest result

B73 evidence remains intact.

Final Telephone sequence:
- 19:07:30.482 Entry/Open of Z:\resource\apps\phoneui.r01
- FileSize/FileSeek/FileRead valid phoneui.r01 structures
- 19:07:30.483 FileSubClose, raw/translated opcode 0x1C
- 19:07:30.484 Telephone self-panic CONE 14

CONE14 register evidence remains:
- UID3 0x100058B3
- r6 = 0x1099B02D
- requested resource owner remains callhandlingui.r01

No callhandlingui.r01 registration/open is observed before the panic.

## B74 diagnostic result

Counts in the device logs:
- [NBOOT2][PHONEUI_RES_CALLER] = 0
- [NBOOT2][PHONEUI_RES_FRAME] = 0
- [NBOOT2][PHONEUI_RES_ID] = 0
- [NBOOT2][PHONEUI_RES_CONTEXT_DONE] = 0

The older B73 [NBOOT2][PHONEUI_FS_FLOW] markers fire normally for the same
Telephone requests, proving the execution reaches the instrumentation region.

The tested crash Mach-O UUID is:
5aa2782d-5e23-3984-86c2-8f1de58fc662

The canonical B74 artifact was downloaded and independently inspected. Its
Mach-O UUID is exactly the same:
5aa2782d-5e23-3984-86c2-8f1de58fc662

Therefore the user tested the correct B74 binary. This is not an IPA mix-up.

## Proven B74 probe defect

The B74 Python patch emitted C++ UTF-16 path literals with single backslashes.

C++ therefore interpreted:
- \r in \resource as carriage return
- \a in \apps as BEL

The B74 binary contains the malformed UTF-16 sequence corresponding to:
z:<CR>esource<BEL>ppsphoneui.r01

while the live FileServer path is:
z:\resource\apps\phoneui.r01

Therefore the exact-path predicate can never become true and the saved-context
probe never executes.

This is a diagnostic implementation bug only. It does not weaken the B73 proof
that phoneui.r01 is valid and callhandlingui.r01 is not registered before
resource 0x1099B02D is requested.

## Host exit crash

B74 reproduces the previously known host teardown crash after Exit Emulator.

Persistent log reaches:
[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin

but does not reach the healthy os_join_done/shutdown_done/normal_restart_done
sequence for this exit.

The .ips proves:
- EXC_BAD_ACCESS / SIGSEGV
- invalid address 0x0000000100000041
- faulting thread: Symbian OS thread
- top frame: eka2l1::ipc_msg::~ipc_msg() + 104
- caller: eka2l1::kernel_system::wipeout() + 1192

This matches the prior B70 ipc_msg teardown-crash class.

Project decision from the user:
do NOT fix this crash in B75. If B75 reproduces the Home-screen crash again,
promote the teardown fix on the next step.

## Next

B75 PHONEUIRESCALLER2:
- correct only the B74 C++ path literals;
- add explicit [NBOOT2][PHONEUI_RES_MATCH2];
- preserve B74 caller/register/stack capture;
- do not register callhandlingui;
- do not suppress CONE14;
- do not force state 102 or ESimUsable;
- do not apply the host teardown fix yet.
