# NATIVEBOOT2 B71 PHONEUICONE14RES1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## B70 DEVICE1 evidence

B70 DEVICE1 is sufficient; no repeat is required.

Visible behavior advances to the native fatal UI:

`Phone start-up failed. Contact the retailer.`

Exact causal boundary:

- 14:07:49.074 Telephone opens
  `z:\resource\apps\phoneui.r01`;
- 14:07:49.075 Telephone / UID3 0x100058B3 panics
  `CONE 14`;
- 14:07:49.077 StarterServer receives result 14;
- 14:07:49.086 SYSSTART writes global state 101 -> 116.

Host exit begins only at 14:09:05.786, so the user did not terminate the run
too early for this diagnosis.

SIM P&S 0x101F8766 keys 0x31/0x32/0x33 remain at their observed value 100 in
the critical interval. The normal SIM security sequence is not reached.

The previous absolute request address 0x007008D4 is not present in this run.
The fatal waiter is at 0x00701684. Cross-build absolute guest addresses are not
used as stable identities.

## Meaning of CONE 14

Authoritative Symbian Classic UI source defines:

`ECoePanicNoResourceFileForId = 14`

CCoeEnv::ResourceFileForId / DoResourceFileForIdL use this panic when no loaded
resource file owns the requested resource ID.

Therefore the immediate blocker is PhoneUI/CONE resource ownership, not a
proven SIM-adaptation failure.

## Canonical B71 scope

B71 is diagnostic-only and targets the proven Telephone/PhoneUI panic.

Markers:

- `[NBOOT2][CONE14_PHONEUI]`
- `[NBOOT2][CONE14_FRAME]`
- `[NBOOT2][CONE14_STACK]`
- `[NBOOT2][CONE14_CODE16]`
- `[NBOOT2][CONE14_FP]`
- `[NBOOT2][CONE14_SUMMARY]`
- `[NBOOT2][PHONEUI_RSC_DUMP]`

It captures:

- r0-r12, PC/LR/SP/FP/CPSR;
- up to 128 raw guest stack words;
- code-candidate module/base/offset resolution;
- bounded code16 windows around CONE/Phone/euser-related frames;
- a bounded frame-pointer neighborhood;
- exact `z:\resource\apps\phoneui.r01` bytes in 512-byte uppercase HEX
  chunks through a separate read-only VFS handle.

PhoneUI RSC capture cap: 262144 bytes.

## Evidence discipline correction

An earlier B71 draft attempted to tag a presumed PhoneUI resource-ID
base/range. That range was not present in the supplied B70 logs and is not
required for diagnosis.

Canonical B71 #224 explicitly uses:

`resource_range_assumption=NONE`

The resource signature/index/range will be decoded from the exact captured
phoneui.r01 bytes before B72 is selected.

## Behavior contract

B71 does NOT:

- suppress CONE14;
- rewrite the panic reason/category;
- alter Starter result 14;
- force state 102 or block state 116;
- synthesize ESimUsable;
- alter KPSSimStatus/KPSSimOwned/KPSSimChanged;
- alter SAServer responses;
- modify resource bytes or the guest EFsrv cursor;
- alter scheduler/rendezvous behavior.

B61/B64/B67/B68/B69/B70 remain preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36107741479
- run number: 224
- job ID: 107984034152
- build HEAD: e5a6c3a55d448cbdc56e8b3a16b397451d84ebe4
- manifest: VALID
- B71 apply: PASS
- B71 contract: PASS
- regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- IPA package/upload: PASS
- compile requests: 151
- cache hits: 149
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

`de93877fb12c33e1b35840a4dd108c5ebd2f1b6fc104812753e630d269aef9cc`

IPA artifact:

- ID: 10851856967
- size: 19971406 bytes
- ZIP digest:
  `sha256:d7fabedd3f65be490119e71c1fbfffee859b111546bfacc4b2931746c05ec0df`
- expires: 2026-10-09

Audit artifact:

- ID: 10851452716
- ZIP digest:
  `sha256:032e9a325096574b7a2fe4b535da7aaf18eab7de41d596512038a609716eb9b8`

## DEVICE1 instructions

Install B71 over B70 and run the same normal Emulator boot.

When the same Phone start-up failed screen appears, leave it stable for about
5-10 seconds. The diagnostic markers fire at the panic itself, so waiting
longer is unnecessary.

Then exit normally and send:

- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log

Video is needed only if visible behavior differs from B70.

## B72 decision rule

First reconstruct `phoneui.r01` from `PHONEUI_RSC_DUMP` and decode its real
resource signature/index table.

Then correlate that data with:

- raw register/stack values;
- resolved CONE/PhoneUI frames;
- code16 windows around the exact callers.

B72 may implement a narrow compatibility fix only after the requested resource
ID and the reason CCoeEnv fails to associate it with a loaded resource file are
proven.

Do not fix B72 by suppressing CONE14 or forcing SIM/startup state.
