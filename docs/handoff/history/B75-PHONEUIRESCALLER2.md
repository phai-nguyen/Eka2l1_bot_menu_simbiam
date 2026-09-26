# NATIVEBOOT2 B75 PHONEUIRESCALLER2

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Why B75

B74 DEVICE1 reached the exact same final phoneui.r01 FileServer boundary and
CONE14, but none of the B74 PHONEUI_RES_* markers fired.

Artifact/IPS UUID comparison proves the correct B74 binary was tested.

Root cause is a B74 diagnostic path-literal bug:
single backslashes in generated C++ turned \r and \a into control characters,
so the exact phoneui/callhandling path predicate could never match.

## B75 change

B75 is diagnostic-only.

It:
- rewrites the B74 C++ path literals to correctly escaped Symbian paths:
  - z:\\resource\\apps\\phoneui.r01
  - z:\\resource\\apps\\callhandlingui.r01
- adds [NBOOT2][PHONEUI_RES_MATCH2] immediately after an exact path match;
- preserves:
  - [NBOOT2][PHONEUI_RES_CALLER]
  - [NBOOT2][PHONEUI_RES_FRAME]
  - [NBOOT2][PHONEUI_RES_ID]
  - [NBOOT2][PHONEUI_RES_CONTEXT_DONE]
  - bounded 96-word stack scan.

It does NOT:
- register callhandlingui.r01;
- inject or merge resource data;
- alter FileServer results/data/cursors;
- suppress CONE14;
- force state 102;
- force ESimUsable;
- modify Starter/SAServer/P&S;
- apply the ipc_msg teardown fix.

## CI strengthening

The FAST workflow now requires the packaged Mach-O to contain:
- [NBOOT2][PHONEUI_RES_CALLER]
- [NBOOT2][PHONEUI_RES_MATCH2]

This closes the earlier gap where the source contract could pass without a
milestone-specific packaged-binary invariant.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36134635918
- run number: 242
- job ID: 108069661366
- build HEAD: a461caf279ee0bdb426ca0b9148fcc93a11262c7
- manifest/apply/contract/regression: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 151
- cache hits: 150
- cache misses: 1
- cache hit rate: 99.34%
- compilations: 1
- compilation failures: 0
- bootstrap source: B28_CACHE
- total build audit seconds: 193
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:
781d3aec89ad6739af29564081e9c59d16a2b6dc7894cbd422dee47cd32822e4

IPA artifact:
- ID: 10862314528
- ZIP digest:
  sha256:31f1c22fc9cfea10598ce313fc377d39793de361044c1a04de1b43e5f0b6923c
- expires: 2026-10-09

Audit artifact:
- ID: 10862144734
- ZIP digest:
  sha256:87252ca3f4a0550f17353f20b2f064fda5596cca071f8b0d1fdddf59d7c8ce41

Packaged Mach-O UUID:
2d8931fd-e4fc-3b1d-91ed-e4acf3c9462e

## DEVICE1 instructions

Install B75 over B74.

Run normal Emulator boot until:
- the same Phone start-up failed screen, or
- visible behavior changes.

If the same screen appears:
- leave it stable 5-10 seconds;
- Exit Emulator through the same game-menu / Emulator exit path.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
- Persistent-prev if produced
- .ips if the app crashes to iOS Home

Video only if visible startup behavior changes.

## Acceptance

Primary:
- [NBOOT2][PHONEUI_RES_MATCH2] must fire.
- [NBOOT2][PHONEUI_RES_CALLER] must fire around final phoneui.r01 operations.
- correlate final FileSubClose with PHONEUI_RES_FRAME/ID and later CONE14.

Resource-fix decision:
only after B75 captures the exact PhoneUIUtils/CONE control-flow boundary should
the next build restore the missing callhandlingui registration.

Host-exit decision:
if B75 again crashes to Home with the ipc_msg::~ipc_msg() teardown signature,
apply the host teardown fix on the next step as explicitly requested by the
user. If B75 exits cleanly, keep the teardown patch deferred.
