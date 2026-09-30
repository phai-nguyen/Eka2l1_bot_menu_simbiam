# NATIVEBOOT2 B77 PHONEUIRESOLVEREXPORT1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; EXPORT-182 RESOLVED; BASECONSTRUCT FRAME ABSENT; CONE14 UNCHANGED
Selected route: NORMAL BOOT + SIM PRESENT

## Device inputs

- EKA2L1(20260925-143142).log
- EKA2L1_Persistent(20260925-143143).log
- EKA2L1_Persistent-prev(8).log
- EKA2L1_TakeThis(20260925-143204).log

Visible result remains:
Phone start-up failed.
Contact the retailer.

No new host crash was reported.

## B77 marker result

From the B77 TakeThis log:
- PHONEUI_BASECONSTRUCT_EXPORT: 42
- PHONEUI_BASECONSTRUCT_FRAME: 0
- PHONEUI_LITERAL_PTR: 27
- PHONEUI_BASECONSTRUCT_SCAN_DONE: 42
- PHONEUI_RES_MATCH2: 41
- PHONEUI_RES_CALLER: 41
- CONE14_PHONEUI: 1
- callhandlingui.r01 open/registration: 0

Thus the B77 instrumentation itself is working. The zero
PHONEUI_BASECONSTRUCT_FRAME count is evidence, not a failed probe.

## Exact RM-356 export-182 mapping

Loaded PhoneUIUtils.dll:
- runtime base: 0x80ED8DA8
- text size: 0x6298
- code size: 0x6298

EABI ordinal 182:
CPhoneResourceResolverBase::BaseConstructL()

Runtime:
- raw export: 0x80EDA971
- normalized address: 0x80EDA970
- module offset: +0x1BC8
- next export: 0x80EDA99E
- conservative bounded span: 0x2E

The same export mapping is observed at FileServer resource I/O and at CONE14.

No PC/LR/register/stack candidate in the 384-word B77 observation window lands
inside the +0x1BC8..next-export range.

This does NOT prove BaseConstructL never ran earlier. It proves only that it is
not present in these captured FileServer/CONE14 stack windows.

## CONE14 remains unchanged

Telephone still self-panics:
- UID3 0x100058B3
- category CONE
- reason 14
- requested resource in r6: 0x1099B02D

No callhandlingui.r01 open/registration occurs before the panic.

## Pointer correction

B77 confirms:
- +0x5094 = descriptor/literal data
- +0x50B8 = descriptor/literal data

Do not treat them as return addresses.

Observed PhoneUIUtils candidates include:
- FileServer contexts: +0x1B74, +0x1B7C
- CONE14 stack: +0x1BC0, +0x3A38, +0x3B2C, +0x3B4C
- plus the already rejected +0x5094/+0x50B8 literals

Offline inspection of B71/B77 CODE16 windows validates real Thumb BL return
addresses:
- +0x1BC0: callsite +0x1BBC -> decoded target +0x3B2E
- +0x3B4C: callsite +0x3B48 -> decoded target +0x3A28
- +0x3A38: callsite +0x3A34 -> decoded target +0x46C4

+0x3B2C is not itself a validated BL return address.

## Source-side cross-check

Symbian PhoneUI source confirms:
CPhoneResourceResolverBase::BaseConstructL() registers, in order:
1. phoneui
2. callhandlingui
3. phoneuitouch

It calls NearestLanguageFile and AddResourceFileL for each resource.

The PhoneUI EABI export table confirms:
- 181 CPhoneMainResourceResolver::Instance
- 182 CPhoneResourceResolverBase::BaseConstructL
- 307 CPhoneResourceResolverBase::ResolveResourceID
- 308 CPhoneResourceResolverBase::IsTelephonyFeatureSupported

Because ordinal 182 is absent from the captured failing stack while other real
PhoneUIUtils callsites remain, B78 must reconstruct the validated call chain
before any functional callhandlingui injection.

## Host

B76 host fixes remain effective. The B77 logs complete normal shutdown/restart.
Do not reopen host crash work unless a new .ips is produced.
