# NATIVEBOOT2 B74 PHONEUIRESCALLER1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## B73 DEVICE1 conclusion

B73 DEVICE1 closes the FileServer/resource-file diagnosis.

Visible result:
- Phone start-up failed. Contact the retailer.
- Exit Emulator returns cleanly.

Exact final phoneui.r01 sequence from Telephone UID3 0x100058B3:

- Entry
- FileOpen
- FileSize
- FileSeek
- FileRead header/index/signature structures
- FileSubClose
- CONE14

The reads exactly match a valid Symbian resource-file parse:
- file size 28134
- index table offset 27396 / 0x6B04
- resource count 368
- 21-byte header
- complete 738-byte offset table
- 46-byte Unicode-bit array
- resource/signature record at 0x41

Thus phoneui.r01 is valid and successfully parsed.

The actual resource ID present at panic is:
- 0x1099B02D

Matching RM-356 RPKG proves:
- owner: Z:\resource\apps\callhandlingui.r01
- signature base: 0x1099B000
- resource index: 0x2D / 45
- resource exists
- resource file exists
- matching localized callhandlingui.r96 exists

B73 boot contains no callhandlingui.r01 entry/open.

Nokia PhoneUI source confirms CPhoneResourceResolverBase::BaseConstructL()
intends to register:
1. phoneui.rsc
2. callhandlingui.rsc
3. phoneuitouch.rsc

CONE source confirms DoResourceFileForIdL() panics when no resource file in the
registered array owns the requested ID.

Therefore the proven current failure is:
callhandlingui resource exists on Z but is not registered before PhoneUIUtils
requests 0x1099B02D.

## Why B74

The remaining question is control flow, not file contents:

Which exact guest function performs the final phoneui.r01 registration, and
where does execution go after it returns instead of opening/registering
callhandlingui.r01?

B74 observes the saved Telephone guest CPU context at FileServer operations for:
- Z:\resource\apps\phoneui.r01
- Z:\resource\apps\callhandlingui.r01

## B74 markers

[NBOOT2][PHONEUI_RES_CALLER]

Records:
- path/kind
- FileServer opcode
- saved guest PC/LR/SP/CPSR
- r0-r12

[NBOOT2][PHONEUI_RES_FRAME]

Scans up to 96 guest stack words and tags addresses inside exact RM-356:
- PhoneUIUtils.dll
  runtime 0x80ED8DA8..0x80EDF03F
- cone.dll
  runtime 0x806E8E68..0x806F4377

This should identify the PhoneUIUtils return/caller offsets active during the
final resource registration close.

[NBOOT2][PHONEUI_RES_ID]

Flags 0x1099B02D if it is already live in register/stack context at the
FileServer boundary.

[NBOOT2][PHONEUI_RES_CONTEXT_DONE]

Marks each completed bounded context capture.

## Behavior contract

B74 is diagnostic-only.

It does NOT:
- register callhandlingui.r01;
- inject or merge resource data;
- alter FileServer results/cursors/data;
- suppress CONE14;
- force state 102;
- force ESimUsable;
- alter Starter/SAServer/P&S/scheduler/graphics/teardown.

B61/B64/B68/B69/B70/B71/B72/B73 preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36130192940
- run number: 241
- job ID: 108055433959
- build HEAD: 7cc9a50d1c08992e70ef8ca1da2e9d6086e9f676
- manifest: VALID
- B74 apply: PASS
- B74 contract: PASS
- full regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 151
- cache hits: 150
- cache misses: 1
- cache hit rate: 99.34%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

e0eb3594ac099661ca31bf64bb3763459a33a5fb03d3418e2fc99e92ee9657e5

IPA artifact:
- ID: 10861787477
- ZIP digest:
  sha256:b12773cf74941a6a4c41ad776d699b5b204519a8ce9efc8b0ef5cc543d6e44b7
- size: 19979827 bytes
- expires: 2026-10-09

Audit artifact:
- ID: 10861787485
- ZIP digest:
  sha256:9c2bdee0fc0c4c3b48da0ed300e6c27f56b2e006794404ac3569b0ee7abd8af5

## DEVICE1 instructions

Install B74 over B73.

Run normal Emulator boot until:
- same Phone start-up failed screen, or
- visible behavior changes.

If the same screen appears:
- wait 5-10 seconds;
- exit using the game-menu / Emulator exit path.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
- Persistent-prev if produced

Video only if visible behavior differs.

Also report whether Exit Emulator remains clean.

## B75 decision

Correlate the final phoneui.r01 FileSubClose context with:
- PHONEUI_RES_CALLER
- PHONEUI_RES_FRAME
- PHONEUI_RES_ID
- later CONE14 stack

If the stack identifies a PhoneUIUtils caller corresponding to
CPhoneResourceResolverBase::BaseConstructL or an equivalent exact-firmware
resource-initialization routine, B75 can restore the missing callhandlingui
registration at that proven boundary.

If the final phoneui registration belongs to a different caller, trace that
caller instead of assuming the public BaseConstructL sequence.

Do not implement a functional registration workaround until B74 proves this
boundary.
