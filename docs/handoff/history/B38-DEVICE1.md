# NATIVEBOOT2 B38 DEVICE1 — EIKCANCELTRACE2

Updated: 2026-09-22
Status: DEVICE-OBSERVED; B38 diagnostics completed their purpose. No B38 behavioral promotion.

## Device logs

Supplied:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Persistent/TakeThis contain the decisive startup trace.

Primary marker counts in the persistent log:
- WSERV_BATCH_CMD: 855
- WSERV_BATCH_RESULT: 588
- EIKDIRECT_FRAME: 32
- EIKDIRECT_CODE16: 416
- EikAppUiServerThread EIKFAULT_LEAVE(-3): 16
- WSERV_NONFADING_ENTER: 17
- Object handle is invalid: 58
- EIKFAULT_AV logged before shutdown: 10

The repeated Leave family remains deterministic.

## WindowServer command immediately before all 16 Leave(-3) events

Every one of the 16 cycles has the same structure immediately before Leave:

- one-command WindowServer batch
- opcode: 0x16
- cmd_len: 16
- object/session handle varies with the eiksrvs instance
- completion_written=1
- last_result=393222 = 0x00060006
- batch then signals
- EikAppUiServerThread executes User::Leave(-3)

Observed session handles:
0x0000097D, 0x00000976, 0x00000997, 0x000009B1,
0x00000A3C, 0x00000A35, 0x00000A43, 0x00000A5F,
0x00000ABD, 0x00000AC4, 0x00000AED, 0x00000B05,
0x00000B65, 0x00000B6C, 0x00000BAD, 0x00000B95.

SymbianSource graphics source identifies TWsClientOpcodes 0x16 as:
EWsClOpCreateWindow.

The corresponding client source RWindowBase::construct() does:
- WriteReplyWs(..., EWsClOpCreateWindow)
- if return < 0, return the error
- otherwise assign the positive return value to iWsHandle
- return KErrNone

Therefore 0x00060006 is a successful newly created WindowServer object handle, not KErrCancel and not a WindowServer error.

Conclusion:
the WindowServer CreateWindow request immediately before Leave succeeds. It is not the producer of -3.

## Direct User::Leave path

All 16 Leave events resolve identically:

PC:
- raw: 0x8029833C
- module: euser.dll
- base: 0x80295448
- offset: +0x2EF4
- nearby machine code contains SVC 0xDF followed by BX LR

LR:
- raw: 0x802ABB29
- module: euser.dll
- offset: +0x166E0
- nearest EABI export ordinal: 649
- nearest export address: 0x802ABB1F
- delta: 0xA

SymbianSource kernelhwsrv eabi/euseru.def maps ordinal 649 to:
User::Leave(int).

The firmware implementation matches the C++-exception Leave variant:
- User::Leave calls Exec::LeaveStart
- obtains/calls the trap handler Leave method
- throws XLeaveException
- the TRAP catch retrieves the reason and Exec::LeaveEnd is called

EKA2L1's leave_start/leave_end structure matches the corresponding SymbianSource ExecHandler::LeaveStart/LeaveEnd model closely enough that B38 does not justify changing SVC 0xDF semantics.

Runtime ordering confirms this:
- EIKFAULT_LEAVE(-3)
- "Leave trapped by trap handler." / leave_end
- later WindowServer cleanup/config batch
- only then the euser access violation

Therefore the Leave itself is successfully caught. Do not suppress KErrCancel and do not remap SVC 0xDF based on B38.

## Direct AvkonFep caller

At the User::Leave entry:
- current SP = 0x00404B18
- User::Leave prologue saves caller r4 and LR before its local stack allocation
- saved caller r4 is therefore at current SP + 8 = stack index 2
- saved caller LR is at current SP + 12 = stack index 3

B38 stack evidence:
- stack index 2 = 0x00703A88 (caller r4)
- stack index 3 = 0x7680F105
- avkonfep.dll base = 0x76800000
- direct caller return offset = +0xF104

Thus avkonfep.dll +0xF104 is the direct caller return address of User::Leave, not merely a contextual stack candidate.

Code immediately before that return:
- +0xF0F6: ldr r0,[r4,#0x10]
- +0xF0F8: ldr r0,[r0,#0x24]
- +0xF0FA: cmp r0,#0
- +0xF0FC: conditional branch over Leave path when nonzero
- +0xF0FE: forms -3 from zero
- +0xF100: call User::Leave
- return address: +0xF104

Equivalent observed logic:
if ((*(*(r4 + 0x10) + 0x24)) == 0)
    User::Leave(KErrCancel);

This is the first direct proof that stock AvkonFep intentionally raises KErrCancel because a nested state field is null.

Do not patch or replace stock avkonfep.dll. The next task is to identify why this state is null under emulation.

## What happens after the caught Leave

After LeaveEnd/catch, a six-command WindowServer batch operates on the newly created object handle 0x00060006.

Observed sequence:
- op 0x1
- op 0x6
- op 0x1
- op 0x1
- op 0x5D SetNonFading
- op 0x0
- batch result KErrNone

This confirms SetNonFading is downstream of the Leave and is not its producer.

After that post-catch path, EikAppUiServerThread hits:
- write address: 0x00000010
- PC: 0x802A01C4 = euser.dll +0xAD7C
- LR: 0x802A2DF5 = euser.dll +0xD9AD
- r0=0
- r1=0

This post-Leave access violation is now the immediate fatal boundary. B38 did not resolve its nearest export/code window.

## Exit Emulator

B34 remains healthy in this run.

Final user exit:
- os_join_begin 22:01:23.363
- os_join_done 22:01:23.399
- about 36 ms
- shutdown_done follows
- normal_restart_done has_device=1

## Source corroboration

SymbianSource sources used:
- oss.FCL.sf.os.graphics / windowing/windowserver/SERVER/w32cmd.h
- oss.FCL.sf.os.graphics / windowing/windowserver/nonnga/CLIENT/RWINDOW.CPP
- oss.FCL.sf.os.kernelhwsrv / kernel/eka/eabi/euseru.def
- oss.FCL.sf.os.kernelhwsrv / kernel/eka/euser/us_trp.cpp
- oss.FCL.sf.os.kernelhwsrv / kernel/eka/kernel/scodeseg.cpp
- oss.FCL.sf.os.kernelhwsrv / kernel/eka/euser/epoc/arm/uc_trp.cia

Exa was also used to locate/cross-check Symbian Leave/TRAP and FEP documentation.

## B38 conclusion

B38 closes the earlier ambiguity:
1. CreateWindow succeeds and returns 0x60006.
2. SetNonFading is downstream.
3. Stock AvkonFep directly and intentionally calls User::Leave(KErrCancel) because a nested state field is null.
4. The Leave is caught; LeaveEnd is observed.
5. The immediate fatal boundary is a later euser null write at +0xAD7C.

B38 remains diagnostic-only and is not promoted to an immutable functional branch.

## Preferred B39 — EIKPOSTLEAVEAV1, diagnostic-only

Before any behavioral fix, B39 should:
1. resolve the EIKFAULT_AV PC/LR against the active euser export table;
2. dump bounded code windows and stack candidates at the post-Leave AV;
3. at the KErrCancel Leave boundary, recover the saved caller r4 and log:
   - caller_r4
   - *(caller_r4 + 0x10)
   - *(*(caller_r4 + 0x10) + 0x24)
   when safely mapped;
4. correlate those values with the newly created WindowServer handle and post-catch cleanup path.

B39 must not:
- suppress KErrCancel;
- change Leave/Trap or SVC 0xDF;
- change FEP;
- replace stock avkonfep.dll;
- change WindowServer completion/signal semantics;
- alter B34 exit behavior;
- batch unrelated SVC fixes.

The goal is to name the null AvkonFep state and resolve the exact post-catch euser fault before changing guest behavior.
