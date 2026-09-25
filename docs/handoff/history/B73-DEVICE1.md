# NATIVEBOOT2 B73 PHONEUIFSFLOW1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; PHONEUI RSC PARSE VALID; MISSING REGISTERED CALLHANDLINGUI RESOURCE PROVEN; CLEAN EXIT

## Inputs

- EKA2L1_Persistent(20260925-110613).log
- EKA2L1(20260925-110612).log
- EKA2L1_Persistent-prev(6).log
- EKA2L1_TakeThis(20260925-110625).log

User-visible result:
- still reaches native Startup failure UI:
  Phone start-up failed. Contact the retailer.
- Exit Emulator returns normally; no iOS host crash.

## Teardown

Clean exit is confirmed again:
- shutdown_threads_done
- shutdown_done
- normal_restart_begin
- fresh run: normal_restart_done has_device=1

This is the third clean-exit build after the isolated B70 ipc_msg crash.
Do not backport teardown-lifetime changes unless the host crash reproduces.

## B73 FileServer flow result

B73 records 398 Telephone FileServer operations.

The final PhoneUI sequence immediately before CONE14 is issued by:
- process: Telephone[100058b3]0002
- UID3: 0x100058B3
- thread: Telephone

Exact sequence:

1. 0x16 Entry z:\resource\apps\phoneui.r01
2. 0x1E FileOpen, raw mode 1
   returned handle = 1114122 / 0x0011000A
3. 0x28 FileSize
4. 0x26 FileSeek
5. 0x22 FileRead, position 0, length 21
6. 0x22 FileRead, position 0x6CE6, length 0x100
7. 0x22 FileRead, position 0x6B04, length 0x1E2
8. 0x22 FileRead, position 0x13, length 0x2E
9. 0x22 FileRead, position 0x41, length 8
10. 0x1C FileSubClose
11. Telephone self-panics CONE 14 within approximately 1 ms

There are no unknown EFsrv opcodes at this boundary.

Opcode mapping from EKA2L1 fs/op.h:
- 0x16 Entry
- 0x1C FileSubClose
- 0x1E FileOpen
- 0x22 FileRead
- 0x26 FileSeek
- 0x28 FileSize
- 0x43 IsFileInRom
- 0x46 ReadFileSection

No 0x43/0x46 is needed in the final phoneui.r01 parse sequence.

## phoneui.r01 parse is internally valid

Matching RM-356 RPKG:
- size: 28134 / 0x6DE6
- index table offset: 27396 / 0x6B04
- resource count: 368
- signature base: 0x4E738000

B73 reads exactly match Symbian RResourceFile parsing:
- 21-byte header at file start;
- complete 738-byte resource offset table
  (369 x uint16) as 0x1E2 + 0x100;
- 46-byte Unicode bit array at offset 0x13;
- 8-byte resource #1/signature record at offset 0x41.

The signature bytes at offset 0x41 are:
04 00 00 00 01 80 73 4E

This carries resource ID/signature 0x4E738001 and confirms the PhoneUI resource
file was parsed successfully before being closed.

Therefore the current CONE14 is not explained by malformed/missing phoneui.r01.

## True requested resource ID

B71 panic context already captured:
- r6 = 0x1099B02D
- stack[4] = 0x1099B02D
- stack[16] = 0x1099B02D

The exact PhoneUIUtils.dll contains the same 32-bit constant and passes it into
cone.dll immediately before the CONE14 path.

RPKG cross-check proves:
- 0x1099B02D belongs to Z:\resource\apps\callhandlingui.r01
- signature base: 0x1099B000
- resource count: 46
- low index: 0x2D / resource 45
- resource 45 exists
- matching localized callhandlingui.r96 also exists

callhandlingui.r01:
- size: 1968
- SHA-256:
  19cfc66a7025993485623c42ffe0f3ef90a35c78bc1058ea80da817edeae3c7a

Critically, the entire B73 boot log contains no callhandlingui.r01 open/entry.
The file exists on drive Z but is not registered before resource lookup.

## Nokia PhoneUI source correlation

SymbianSource/oss.FCL.sf.app.phone:

phoneapp/phoneuiutils/src/cphoneresourceresolverbase.cpp

CPhoneResourceResolverBase::BaseConstructL() explicitly intends to register:

1. phoneui.rsc
2. callhandlingui.rsc
3. phoneuitouch.rsc

using:
- BaflUtils::NearestLanguageFile(...)
- CEikonEnv::AddResourceFileL(...)

The exact RM-356 PhoneUIUtils.dll also contains UTF-16 strings:
- \resource\apps\
- phoneui.rsc
- callhandlingui.rsc

So callhandlingui registration is a real part of the PhoneUI resource model,
not a synthetic compatibility idea.

## CONE source correlation

cdaffara/symbiandump-mw1:
sf/mw/classicui/lafagnosticuifoundation/cone/src/COEMAIN.CPP

CCoeEnv::AddResourceFileL():
- opens resource file;
- confirms signature;
- takes RResourceFile::Offset();
- appends RResourceFile to iResourceFileArray;
- returns offset.

It does not read application payload resources.

CCoeEnv::ResourceFileForId / DoResourceFileForIdL:
- scans iResourceFileArray;
- calls OwnsResourceIdL(aResourceId);
- panics ECoePanicNoResourceFileForId / CONE14 if no registered file owns ID.

This exactly matches observed behavior for 0x1099B02D.

## Proven current causal chain

Telephone / PhoneUIUtils
  -> phoneui.r01 opens and validates
  -> phoneui.r01 closes
  -> callhandlingui.r01 is never opened/registered
  -> PhoneUIUtils requests 0x1099B02D
  -> CONE resource array has no owner for 0x1099B000 namespace
  -> CONE14
  -> Telephone critical app exits reason 14
  -> Starter receives result 14
  -> StartupAdaptation FatalStartupError=117
  -> P&S global state 116
  -> Phone start-up failed UI

SIM P&S still does not reach ESimUsable before this boundary.

## Selected B74

Do NOT fake resource payloads or suppress CONE14.

B74 should identify the exact guest caller/control-flow boundary around the
final phoneui.r01 registration:
- Telephone guest PC/LR/SP/register context for exact phoneui.r01
  Entry/Open/Close operations;
- bounded guest-stack scan resolving PhoneUIUtils / CONE / BAFL candidates;
- exact callhandlingui.r01 open marker if one unexpectedly occurs.

Goal:
determine which PhoneUIUtils/CONE function issued the final phoneui registration
and where guest control goes after FileSubClose, before 0x1099B02D lookup.

Only after this control-flow boundary is proven should a functional B75 restore
the missing callhandlingui resource registration.
