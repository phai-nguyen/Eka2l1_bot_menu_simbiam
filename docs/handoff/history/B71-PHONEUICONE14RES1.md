# NATIVEBOOT2 B71 PHONEUICONE14RES1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## B70 DEVICE1 blocker

B70 is sufficient; no repeat is required.

Visible result:
- NOKIA logo appears;
- native Startup UI then displays:
  `Phone start-up failed. Contact the retailer.`
- the error remains stable for more than one minute in the supplied recording.

Exact chain:
- SYSSTART state 0 -> 100 -> 101;
- Telephone[0x100058B3] opens Z:\\resource\\apps\\phoneui.r01;
- Telephone self-panics CONE 14;
- Starter receives result=14 at request_status=0x00701684;
- Starter sends SAServer function 0x64;
- SYSSTART writes global state 101 -> 116;
- native startup-failure UI is shown.

SIM P&S 0x101F8766 keys 0x31/0x32/0x33 remain at 100 in the proven interval.
There is no evidence yet for KPSSimStatus=ESimUsable.

The old B69 diagnostic address 0x007008D4 does not occur in this B70 run.

## Why CONE14 matters

The official Symbian CONE panic table defines panic 14 as the environment being
unable to find the specified resource in any resource file.

The matching RM-356 SYM.RPKG proves:
- Z:\\resource\\apps\\phoneui.r01 exists;
- size: 28134 bytes;
- SHA-256:
  05c419086de5710d361f7d8c910ef5284006b5ee879cb0acb448b8090a7ce9a1
- resource signature base: 0x4E738000;
- resource count: 368;
- expected user-resource index range: 0x001..0x170.

Therefore the immediate blocker is a PhoneUI/CONE resource lookup failure, not
simple file absence and not yet a proven SIM-adaptation failure.

## B71 scope

B71 is diagnostic-only and runs only when all are true:
- target process UID3 = 0x100058B3 (Telephone);
- caller thread kills itself;
- panic reason = 14;
- panic category = CONE.

Markers:
- [NBOOT2][CONE14_PHONEUI]
- [NBOOT2][CONE14_FRAME]
- [NBOOT2][CONE14_STACK]
- [NBOOT2][CONE14_RESID_CANDIDATE]
- [NBOOT2][CONE14_SUMMARY]

It captures:
- r0-r12, SP, LR, PC, CPSR;
- PC/LR module + relocated offset;
- up to 128 guest stack words;
- code-segment candidates from stack values;
- explicit candidate tagging for 0x4E738xxx PhoneUI resource IDs;
- whether each candidate index falls within the actual R01 range 0x001..0x170.

B71 does NOT:
- suppress CONE14;
- alter reason/category;
- ignore the Telephone critical-app failure;
- force state 102;
- force ESimUsable;
- alter Starter/SAServer/rendezvous/P&S/scheduler behavior;
- inject or replace a resource.

B61/B64/B68/B69/B70 remain preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36107522682
- run number: 222
- job ID: 107983353265
- build HEAD: 0b1ba9911c1ec09d163921b92d6ba4600e8e7f02
- manifest: VALID
- B71 apply: PASS
- B71 contract: PASS
- full regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile requests: 151
- cache hits: 150
- cache misses: 1
- cache hit rate: 99.34%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

ef5f92ce12387ee9e4a80d71ac5514945fe193b9d69f5ba7ca7c49508f870678

IPA artifact:
- ID: 10851761787
- ZIP digest:
  sha256:11d056717d59751e22b174fd5fe404d8ac2a7c92aa50b8652b156fadc57552bd
- size: 19969881 bytes
- expires: 2026-10-09

Audit artifact:
- ID: 10851357336
- ZIP digest:
  sha256:73a6ad996289ba84fb7391b60e5dce69ad7e06862738a291913c35184fc3f3ac

## DEVICE1 instructions

Install B71 over B70 and run the same Emulator normal-boot path.

It is enough to wait until:
- NOKIA logo appears;
- then either the same Phone start-up failed screen appears, or visible behavior
  changes.

Once the failure screen has been stable for about 5-10 seconds, exit normally.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Video is only needed if visible behavior differs from B70.

## B72 decision rule

First inspect [NBOOT2][CONE14_RESID_CANDIDATE] and all
[NBOOT2][CONE14_STACK] rows with phoneui_res_base=1.

If a missing resource ID beyond the actual R01/R96 range is proven, map the
caller module/offset and determine why the binary/resource package versions are
mismatched.

If an in-range resource ID is present but lookup still fails, investigate
resource offset/signature ownership and CONE resource-file registration order.

If no 0x4E738xxx ID survives to the panic stack, use the resolved CONE14 stack
modules/offsets to place the next probe earlier at the exact resource-read call.

Do not fix B72 by forcing SIM state or suppressing Telephone panic.
